import shutil
import sys

_HANDLER = None

def register_handler(handler):
    global _HANDLER
    _HANDLER = handler

def safe_print(msg: str, cursor: str | None = None, input_buffer: str | None = None):
    """
    Prints a message safely while preserving the current input buffer and cursor.
    This ensures logs appear above the input line appropriately.
    """
    if cursor is None and input_buffer is None and _HANDLER is not None:
        lock = None
        try:
            # Try to acquire lock if available to prevent race conditions
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
        # Fallback or explicit arguments
        _do_safe_print(msg, cursor or "", input_buffer or "")

def _do_safe_print(msg: str, cursor: str, input_buffer: str):
    try:
        columns = shutil.get_terminal_size().columns
    except:
        columns = 80
            
    # Clear line
    sys.stdout.write('\r' + ' ' * (columns - 1) + '\r')
    # Print message
    sys.stdout.write(f"{msg}\n")
    # Reprint cursor and buffer
    sys.stdout.write(f"{cursor}{input_buffer}")
    sys.stdout.flush()