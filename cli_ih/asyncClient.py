from typing import Coroutine, Callable, Any
from .exceptions import HandlerClosed
from .utils import safe_print as print, register_handler
import logging, warnings, asyncio, inspect, threading, sys, shutil, msvcrt

class AsyncInputHandler:
    def __init__(self, cursor = "", thread_mode: bool = True, *, logger: logging.Logger | None = None, register_defaults: bool = True):
        register_handler(self)
        self.commands = {}
        self.is_running = False
        self.thread_mode = thread_mode
        self.cursor = f"{cursor.strip()} " if cursor else ""
        self.global_logger = logger if logger else None
        self.logger = logger.getChild("InputHandler") if logger else None
        self.register_defaults = register_defaults
        self.print_lock = threading.Lock()
        self.input_buffer = ""
        self.processing_command = False
        
        if self.register_defaults:
            self.register_default_commands()
        else:
            self.__warning("The default commands are disabled in the current instance.")

    def get_logger(self):
        return self.logger
    
    def __debug(self, msg: str):
        if self.logger:
            self.logger.debug(msg)
        else:
            print(f"[DEBUG]: {msg}")
    
    def __info(self, msg: str):
        if self.logger:
            self.logger.info(msg)
        else:
            print(f"[INFO]: {msg}")

    def __warning(self, msg: str):
        if self.logger:
            self.logger.warning(msg)
        else:
            print(f"[WARNING]: {msg}")

    def __error(self, msg: str):
        if self.logger:
            self.logger.error(msg)
        else:
            print(f"[ERROR]: {msg}")
    
    def __exeption(self, msg: str, e: Exception):
        if self.logger:
            self.logger.exception(f"{msg}: {e}")
        else:
            print(f"[EXEPTION]: {msg}: {e}")

    def __register_cmd(self, name: str, func: Callable[..., Any], description: str = "", legacy=False):
        name = name.lower()
        if not description:
            description = "A command"
        if ' ' in name:
            raise SyntaxError("Command name must not have spaces")
        if name in self.commands:
            raise SyntaxError(f"Command '{name}' is already registered. If theese commands have a different case and they need to stay the same, downgrade the package version to 0.5.x")
        self.commands[name] = {"cmd": func, "description": description, "legacy": legacy}

    def register_command(self, name: str, func: Callable[..., Any], description: str = ""):
        """(DEPRECATED) Registers a command with its associated function."""
        warnings.warn("Registering commands with `register_command` is deprecated, and should not be used.", DeprecationWarning, 2)
        self.__register_cmd(name, func, description, legacy=True)

    def command(self, *, name: str = "", description: str = ""):
        """Registers a command with its associated function as a decorator."""
        def decorator(func: Callable[..., Any]):
            lname = name or func.__name__
            self.__register_cmd(lname, func, description)
            return func
        return decorator

    def start(self):
        """Starts the input handler loop. Runs in a thread if thread_mode is True, otherwise blocks."""
        self.is_running = True
        if self.thread_mode:
            thread = threading.Thread(target=self._start_thread, daemon=True)
            thread.start()
        else:
            self._start_thread()

    def _start_thread(self):
        asyncio.run(self._run())

    async def _run(self):
        """Starts the input handler loop in a separate thread if thread mode is enabled."""
        loop = asyncio.get_running_loop()
        input_queue = asyncio.Queue()

        def _input_worker():
            # Initial prompt
            with self.print_lock:
                sys.stdout.write(self.cursor)
                sys.stdout.flush()

            while self.is_running:
                try:
                    if msvcrt.kbhit():
                        char = msvcrt.getwch()
                        
                        if char == '\r': # Enter
                            with self.print_lock:
                                sys.stdout.write('\n')
                                sys.stdout.flush()
                            text = self.input_buffer
                            self.input_buffer = ""
                            loop.call_soon_threadsafe(input_queue.put_nowait, text)
                                
                        elif char == '\x08': # Backspace
                            if len(self.input_buffer) > 0:
                                self.input_buffer = self.input_buffer[:-1]
                                with self.print_lock:
                                    sys.stdout.write('\b \b')
                                    sys.stdout.flush()
                        
                        elif char == '\x03': # Ctrl+C
                            loop.call_soon_threadsafe(input_queue.put_nowait, KeyboardInterrupt)
                            break
                        
                        else:
                            # Verify printable
                            if char.isprintable():
                                self.input_buffer += char
                                with self.print_lock:
                                    sys.stdout.write(char)
                                    sys.stdout.flush()
                    else:
                        pass
                        # Small sleep to prevent high CPU usage, 
                        # but we are in a dedicated thread so it's fine-ish, 
                        # actually explicit sleep is good.
                        import time
                        time.sleep(0.01)

                except Exception:
                    break
        
        thread = threading.Thread(target=_input_worker, daemon=True)
        thread.start()

        async def _run_command(commands: dict, name: str, args: list):
            """Executes a command from the command dictionary if it exists."""
            command = commands.get(name)
            if not command:
                self.__warning(f"Command '{name}' not found.")
                return

            func = command.get("cmd")
            is_legacy = command.get("legacy", False)

            if not callable(func):
                raise ValueError(f"The command '{name}' is not callable.")

            try:
                sig = inspect.signature(func)
                has_var_args = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
                if has_var_args:
                    final_args = args
                else:
                    params = [p for p in sig.parameters.values() if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY)]
                    final_args = args[:len(params)]
                if is_legacy:
                    sig.bind(final_args)
                else:
                    sig.bind(*final_args)
            except TypeError as e:
                self.__warning(f"Argument error for {"legacy " if is_legacy else ""}command '{name}': {e}")
                return

            try:
                if is_legacy:
                    warnings.warn("This way of running commands id Deprecated. And should be changed to the new decorator way.", DeprecationWarning, 2)
                    if inspect.iscoroutinefunction(func):
                        await func(final_args)
                    else:
                        await asyncio.to_thread(func, final_args)
                else:
                    if inspect.iscoroutinefunction(func):
                        await func(*final_args)
                    else:
                        await asyncio.to_thread(func, *final_args)

            except HandlerClosed as e:
                raise e
            except Exception as e:
                self.__exeption(f"An error occurred in command '{name}'", e)

        while self.is_running:
            try:
                try:
                    user_input = await asyncio.wait_for(input_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                if user_input is EOFError:
                    self.__error("Input ended unexpectedly.")
                    break
                
                if not user_input:
                    continue

                self.processing_command = True
                cmdargs = user_input.split(' ')
                command_name = cmdargs[0].lower()
                args = cmdargs[1:]
                if command_name in self.commands:
                    await _run_command(self.commands, command_name, args)
                else:
                    self.__warning(f"Unknown command: '{command_name}'")
                self.processing_command = False
                
                # Reprompt after command execution
                with self.print_lock:
                    sys.stdout.write(self.cursor)
                    sys.stdout.flush()
                
            except EOFError:
                self.__error("Input ended unexpectedly.")
                break
            except KeyboardInterrupt:
                self.__error("Input interrupted.")
                break
            except HandlerClosed:
                self.__info("Input Handler exited.")
                break
        self.is_running = False

    def register_default_commands(self):
        @self.command(name="help", description="Displays all the available commands")
        async def help(*args):
            str_out = "Available commands:\n"
            for command, data in self.commands.items():
                str_out += f"  {command}: {data['description']}\n"
            print(str_out)

        @self.command(name="debug", description="If a logger is present changes the logging level to DEBUG.")
        async def debug_mode(*args):
            logger = self.global_logger
            if not logger:
                return self.__warning("No logger defined for this InputHandler instance.")

            if logger.getEffectiveLevel() == logging.DEBUG:
                new_level = logging.INFO
                message = "Debug mode is now off"
            else: 
                new_level = logging.DEBUG
                message = "Debug mode is now on"

            logger.setLevel(new_level)

            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(new_level)
            self.__info(message)

        @self.command(name="exit", description="Exits the Input Handler irreversibly.")
        async def exit_thread(*args):
            raise HandlerClosed("Handler was closed with exit command.")