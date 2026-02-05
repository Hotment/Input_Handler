from typing import Callable, Any
from .exceptions import HandlerClosed
from .utils import safe_print as print, register_handler, SafeLogger
import logging, sys, threading, warnings, inspect, shutil, msvcrt

class InputHandler:
    def __init__(self, thread_mode = True, cursor = "", *, logger: logging.Logger | None = None, register_defaults: bool = True):
        register_handler(self)
        self.commands = {}
        self.is_running = False
        self.thread_mode = thread_mode
        self.cursor = f"{cursor.strip()} " if cursor else ""
        self.thread = None
        self.global_logger = logger if logger else SafeLogger()
        self.logger = logger.getChild("InputHandler") if logger else self.global_logger
        self.register_defaults = register_defaults
        self.print_lock = threading.Lock()
        self.input_buffer = ""
        self.processing_command = False
        self.history = []
        self.history_index = 0
        
        if self.register_defaults:
            self.register_default_commands()
        else:
            self.__warning("The default commands are disabled in the current instance.")

    def get_logger(self):
        return self.logger
    
    def __debug(self, msg: str):
        self.logger.debug(msg)
    
    def __info(self, msg: str):
        self.logger.info(msg)

    def __warning(self, msg: str):
        self.logger.warning(msg)

    def __error(self, msg: str):
        self.logger.error(msg)
    
    def __exeption(self, msg: str, e: Exception):
        self.logger.exception(f"{msg}: {e}")

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
        """Starts the input handler loop in a separate thread if thread mode is enabled."""
        import threading, inspect
        self.is_running = True

        def _run_command(commands: dict, name: str, args: list):
            """Executes a command from the command dictionary if it exists."""
            command = commands.get(name)
            if command:
                func = command.get("cmd")
                is_legacy = command.get("legacy", False)
                if callable(func):
                    sig = inspect.signature(func)
                    has_var_args = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())

                    if has_var_args:
                        final_args = args
                    else:
                        params = [p for p in sig.parameters.values() if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY)]
                        final_args = args[:len(params)]

                    if is_legacy:
                        try:
                            sig.bind(final_args)
                        except TypeError as e:
                            self.__warning(f"Argument error for legacy command '{name}': {e}")
                            return
                        
                        try:
                            warnings.warn("This way of running commands id Deprecated. And should be changed to the new decorator way.", DeprecationWarning, 2)
                            func(final_args)
                        except HandlerClosed as e:
                            raise e
                        except Exception as e:
                            self.__exeption(f"An error occurred in legacy command '{name}'", e)
                    else:
                        try:
                            sig.bind(*final_args) 
                        except TypeError as e:
                            self.__warning(f"Argument error for command '{name}': {e}")
                            return
                        try:
                            func(*final_args)
                        except HandlerClosed as e:
                            raise e
                        except Exception as e:
                            self.__exeption(f"An error occurred in command '{name}'", e)
                else:
                    raise ValueError(f"The command '{name}' is not callable.")
            else:
                self.__warning(f"Command '{name}' not found.")


        def _thread():
            """Continuously listens for user input and processes commands."""
            while self.is_running:
                try:
                    with self.print_lock:
                        sys.stdout.write(self.cursor)
                        sys.stdout.flush()
                        
                    while self.is_running:
                        if msvcrt.kbhit():
                            char = msvcrt.getwch()
                            
                            if char == '\xe0' or char == '\x00':
                                try:
                                    scancode = msvcrt.getwch()
                                    if scancode == 'H':
                                        if self.history_index > 0:
                                            self.history_index -= 1
                                            self.input_buffer = self.history[self.history_index]
                                            with self.print_lock:
                                                sys.stdout.write('\r' + ' ' * (shutil.get_terminal_size().columns - 1) + '\r')
                                                sys.stdout.write(self.cursor + self.input_buffer)
                                                sys.stdout.flush()
                                        
                                    elif scancode == 'P':
                                        if self.history_index < len(self.history):
                                            self.history_index += 1
                                            
                                        if self.history_index == len(self.history):
                                            self.input_buffer = ""
                                        else:
                                            self.input_buffer = self.history[self.history_index]
                                            
                                        with self.print_lock:
                                            sys.stdout.write('\r' + ' ' * (shutil.get_terminal_size().columns - 1) + '\r')
                                            sys.stdout.write(self.cursor + self.input_buffer)
                                            sys.stdout.flush()
                                except Exception:
                                    pass

                            elif char == '\r':
                                with self.print_lock:
                                    sys.stdout.write('\n')
                                    sys.stdout.flush()
                                text = self.input_buffer
                                self.input_buffer = ""
                                
                                if text:
                                    if not self.history or self.history[-1] != text:
                                        self.history.append(text)
                                    self.history_index = len(self.history)
                                    
                                    self.processing_command = True
                                    cmdargs = text.split(' ')
                                    command_name = cmdargs[0].lower()
                                    args = cmdargs[1:]
                                    if command_name in self.commands:
                                        _run_command(self.commands, command_name, args)
                                    else:
                                        self.__warning(f"Unknown command: '{command_name}'")
                                    self.processing_command = False
                                
                                break
                                    
                            elif char == '\x08':
                                if len(self.input_buffer) > 0:
                                    self.input_buffer = self.input_buffer[:-1]
                                    with self.print_lock:
                                        sys.stdout.write('\b \b')
                                        sys.stdout.flush()
                            
                            elif char == '\x03':
                                self.__error("Input interrupted.")
                                self.is_running = False
                                return
                            
                            else:
                                if char.isprintable():
                                    self.input_buffer += char
                                    with self.print_lock:
                                        sys.stdout.write(char)
                                        sys.stdout.flush()
                        else:
                            import time
                            time.sleep(0.01)

                except HandlerClosed:
                    self.__info("Input Handler exited.")
                    break
                except Exception as e:
                    self.__exeption("Input loop error", e)
                    break
            self.is_running = False
        if self.thread_mode:
            self.thread = threading.Thread(target=_thread, daemon=True)
            self.thread.start()
        else:
            _thread()

    def register_default_commands(self):
        @self.command(name="help", description="Displays all the available commands")
        def help():
            str_out = "Available commands:\n"
            for command, data in self.commands.items():
                str_out += f"  {command}: {data['description']}\n"
            print(str_out)

        @self.command(name="debug", description="If a logger is present changes the logging level to DEBUG.")
        def debug_mode():
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
        def exit_thread():
            raise HandlerClosed("Handler was closed with exit command.")