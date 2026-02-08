import shutil
import sys
import threading
import os
import logging

_HANDLER = None

def register_handler(handler):
    global _HANDLER
    _HANDLER = handler

class SafeLogger:
    """A dummy logger that uses safe_print to output logs to the console."""
    def __init__(self):
        self.handlers = []
        self.name = "SafeLogger"

    def debug(self, msg: str):
        safe_print(f"[DEBUG]: {msg}")

    def info(self, msg: str):
        safe_print(f"[INFO]: {msg}")

    def warning(self, msg: str):
        safe_print(f"[WARNING]: {msg}")

    def error(self, msg: str):
        safe_print(f"[ERROR]: {msg}")
        
    def critical(self, msg: str):
        safe_print(f"[CRITICAL]: {msg}")

    def exception(self, msg: str):
        safe_print(f"[EXCEPTION]: {msg}")

    def log(self, level, msg: str):
        safe_print(f"[LOG {level}]: {msg}")
    
    def getChild(self, name):
        return self
    
    def setLevel(self, level):
        pass

    def getEffectiveLevel(self):
        return 0

class CLILoggingHandler(logging.Handler):
    """
    A logging handler that uses safe_print to output logs to the console,
    preserving the current input line.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            safe_print(msg)
        except Exception:
            self.handleError(record)


def wrap_logger_handlers(logger: logging.Logger):
    """
    Automatically replaces StreamHandlers in the logger with CLILoggingHandler
    to ensure safe printing in the CLI environment.
    """
    if not logger:
        return

    for h in list(logger.handlers):
        if isinstance(h, logging.StreamHandler) and not isinstance(h, CLILoggingHandler):
            if h.stream in (sys.stdout, sys.stderr):
                new_h = CLILoggingHandler()
                new_h.setLevel(h.level)
                new_h.setFormatter(h.formatter)
                
                logger.removeHandler(h)
                logger.addHandler(new_h)

def install_global_patch():
    """
    Patches the root logger and all existing loggers to use CLILoggingHandler.
    """
    wrap_logger_handlers(logging.getLogger())

    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            wrap_logger_handlers(logger)

def safe_print(msg: object, cursor: str | None = None, input_buffer: str | None = None):
    """
    Prints a message safely while preserving the current input buffer and cursor.
    This ensures logs appear above the input line appropriately.
    """
    try:
        msg = str(msg)
    except:
        msg = "<Unprintable Object>"

    if cursor is None and input_buffer is None and _HANDLER is not None:
        lock: threading.Lock | None = None
        try:
            lock = getattr(_HANDLER, "print_lock", None)
            if lock:
                lock.acquire()
            
            cursor = str(getattr(_HANDLER, "cursor", ""))
            input_buffer = str(getattr(_HANDLER, "input_buffer", ""))
            processing_command = getattr(_HANDLER, "processing_command", False)
            
            if processing_command:
                cursor = ""
                input_buffer = ""
            
            _do_safe_print(msg, cursor, input_buffer)
        finally:
            if lock:
                lock.release()
    else:
        _do_safe_print(msg, str(cursor or ""), str(input_buffer or ""))

def _do_safe_print(msg: str, cursor: str, input_buffer: str):
    is_ptero = os.environ.get('P_SERVER_UUID') or os.environ.get('CLI_IH_FORCE_FALLBACK')
    handler_in_fallback_mode = False
    
    if _HANDLER is not None:
        raw_mode = getattr(_HANDLER, "using_raw_mode_active", None)
        if raw_mode is False:
            handler_in_fallback_mode = True

    if is_ptero or not sys.stdout.isatty() or handler_in_fallback_mode:
        sys.stdout.write(f"{msg}\n")
        sys.stdout.flush()
        return

    try:
        columns = shutil.get_terminal_size().columns
    except:
        columns = 80
            
    sys.stdout.write('\r' + ' ' * (columns - 1) + '\r')
    sys.stdout.write(f"{msg}\n")
    sys.stdout.write(f"{cursor}{input_buffer}")
    sys.stdout.flush()