from typing import Callable
import logging

class HandlerClosed(Exception): ...
class MissingParameter(Exception): ...

class CustomFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels."""

    LEVEL_COLORS = {
        logging.DEBUG: "\033[34m",
        logging.INFO: "\033[0m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[37;41m"
    }

    def format(self, record):
        log_color = self.LEVEL_COLORS.get(record.levelno, "\033[0m")
        log_message = super().format(record)
        return f"{log_color}{log_message}\033[0m"

def setup_logging():
    log_format = '[%(asctime)s | %(levelname)s]: %(message)s'
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter(log_format))
    logging.basicConfig(level=logging.INFO, handlers=[handler], datefmt='%B %d %H:%M:%S')

class InputHandler:
    #logging.basicConfig(level=logging.INFO, format='[%(asctime)s | %(levelname)s]: %(message)s', datefmt='%B %d %H:%M:%S')
    def __init__(self, thread_mode = True, cursor = ""):
        self.commands = {}
        self.is_running = False
        self.thread_mode = thread_mode
        self.cursor = f"{cursor.strip()} "
        self.thread = None
        self.register_default_commands()

    def register_command(self, name: str, func: Callable, description: str = ""):
        """Registers a command with its associated function."""
        if not description:
            description = "A command"
        if ' ' in name:
            raise SyntaxError("Command name must not have spaces")
        self.commands[name] = {"cmd": func, "description": description}

    def start(self):
        """Starts the input handler loop in a separate thread if thread mode is enabled."""
        import threading, inspect
        self.is_running = True

        def run_command(commands: dict, name: str, args: list):
            """Executes a command from the command dictionary if it exists."""
            command = commands.get(name)
            if command:
                func = command.get("cmd")
                if callable(func):
                    if str(inspect.signature(func)) == "()":
                        raise MissingParameter(f"Command '{name}' must accept an 'args' parameter")
                    try:
                        func(args)
                    except Exception as e:
                        raise e
                else:
                    raise ValueError(f"The command '{name}' is not callable.")
            else:
                logging.warning(f"Command '{name}' not found.")


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
                        run_command(self.commands, command_name, args)
                    else:
                        logging.warning(f"Unknown command: '{command_name}'")
                except EOFError:
                    logging.error("Input ended unexpectedly.")
                    break
                except KeyboardInterrupt:
                    logging.error("Input interrupted.")
                    break
                except HandlerClosed:
                    logging.info("Input Handler exited.")
                    break
            self.is_running = False
        if self.thread_mode:
            self.thread = threading.Thread(target=_thread, daemon=True)
            self.thread.start()
        else:
            _thread()

    def register_default_commands(self):
        def help(commands):
            str_out = ""
            for command in commands:
                str_out += f"{command}: {commands[command]['description']}\n"
            print(str_out)

        def debug_mode(args):
            logger = logging.getLogger() 
            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.setLevel(logging.INFO)
                logging.info("Debug mode is now off")
            else: 
                logger.setLevel(logging.DEBUG)
                logging.debug("Debug mode is now on")

        def exit_thread(args):
            raise HandlerClosed
        self.register_command("help", lambda args: help(self.commands), "Displays all the available commands")
        self.register_command("debug", debug_mode, "Changes the logging level to DEBUG.")
        self.register_command("exit", exit_thread, "Exits the Input Handler irreversibly.")
setup_logging()