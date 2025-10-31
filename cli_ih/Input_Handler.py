from typing import Callable
import logging, warnings

class HandlerClosed(Exception): ...
class MissingParameter(Exception): ...

class InputHandler:
    def __init__(self, thread_mode = True, cursor = "", *, logger: logging.Logger | None = None, register_defaults: bool = True):
        self.commands = {}
        self.is_running = False
        self.thread_mode = thread_mode
        self.cursor = f"{cursor.strip()} "
        self.thread = None
        self.global_logger = logger if logger else None
        self.logger = logger.getChild("InputHandler") if logger else None
        self.register_defaults = register_defaults
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

    def __register_cmd(self, name: str, func: Callable, description: str = "", legacy=False):
        name = name.lower()
        if not description:
            description = "A command"
        if ' ' in name:
            raise SyntaxError("Command name must not have spaces")
        if name in self.commands:
            raise SyntaxError(f"Command '{name}' is already registered. If theese commands have a different case and they need to stay the same, downgrade the package version to 0.5.x")
        self.commands[name] = {"cmd": func, "description": description, "legacy": legacy}

    def register_command(self, name: str, func: Callable, description: str = ""):
        """Registers a command with its associated function."""
        warnings.warn("Registering commands with `register_command` is deprecated, and will be removed in the next big update.", DeprecationWarning, 2)
        self.__register_cmd(name, func, description, legacy=True)

    def command(self, *, name: str = "", description: str = ""):
        """Registers a command with its associated function as a decorator."""
        def decorator(func: Callable):
            lname = name
            if not lname:
                lname = func.__name__
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
                    if is_legacy:
                        try:
                            sig = inspect.signature(func)
                            sig.bind(args)
                        except TypeError as e:
                            self.__warning(f"Argument error for legacy command '{name}': {e}")
                            return
                        
                        try:
                            warnings.warn("This way of running commands id Deprecated. And should be changed to the new decorator way.", DeprecationWarning, 2)
                            func(args)
                        except HandlerClosed as e:
                            raise e
                        except Exception as e:
                            self.__exeption(f"An error occurred in legacy command '{name}'", e)
                    else:
                        try:
                            sig = inspect.signature(func)
                            sig.bind(*args) 
                        except TypeError as e:
                            self.__warning(f"Argument error for command '{name}': {e}")
                            return
                        try:
                            func(*args)
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
                    user_input = input(self.cursor).strip()
                    if not user_input:
                        continue

                    cmdargs = user_input.split(' ')
                    command_name = cmdargs[0]
                    args = cmdargs[1:]
                    if command_name in self.commands:
                        _run_command(self.commands, command_name, args)
                    else:
                        self.__warning(f"Unknown command: '{command_name}'")
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