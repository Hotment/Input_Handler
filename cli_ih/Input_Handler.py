from typing import Callable
import logging

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

    def register_command(self, name: str, func: Callable, description: str = ""):
        """Registers a command with its associated function."""
        if not description:
            description = "A command"
        if ' ' in name:
            raise SyntaxError("Command name must not have spaces")
        self.commands[name] = {"cmd": func, "description": description}

    def command(self, *, name: str, description: str = ""):
        """Registers a command with its associated function as a decorator."""
        def decorator(func):
            self.register_command(name, func, description)
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
                if callable(func):
                    #if str(inspect.signature(func)) == "()":
                        #raise MissingParameter(f"Command '{name}' must accept an 'args' parameter")
                    try:
                        func(args)
                    except TypeError as e:
                        self.__error(f"Error calling command '{name}': {e}")
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
        def help(args):
            str_out = "Available commands:\n"
            for command, data in self.commands.items():
                str_out += f"  {command}: {data['description']}\n"
            print(str_out)

        @self.command(name="debug", description="If a logger is present changes the logging level to DEBUG.")
        def debug_mode(args):
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
        def exit_thread(args):
            raise HandlerClosed("Handler was closed with exit command.")
        # self.register_command("help", help, "Displays all the available commands")
        # self.register_command("debug", debug_mode, "Changes the logging level to DEBUG.")
        # self.register_command("exit", exit_thread, "Exits the Input Handler irreversibly.")