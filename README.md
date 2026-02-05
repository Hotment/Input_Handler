# InputHandler Library

A lightweight Python library for creating interactive command-line interfaces with custom command registration, input handling, and clean log output. It supports synchronous and asynchronous modes, threaded input processing, and enhanced logging.

## Features

- **Command Registration**: Register commands with decorators and descriptions.
- **Threaded Input**: Non-blocking input handling by default.
- **Safe Printing**: Logs appear above the input line, preserving your typed text and cursor position.
- **Command History**: Navigate recent commands with Up/Down arrow keys.
- **Sync & Async**: Support for both synchronous and asynchronous (asyncio) applications.
- **Colored Logging**: Built-in support for colored log messages.

## Installation

`pip install cli_ih`

## Quick Start (Synchronous)

```python
from cli_ih import InputHandler, safe_print

handler = InputHandler(cursor="> ")

# Use safe_print instead of print to keep the input line clean!
@handler.command(name="greet", description="Greets the user.")
def greet(name):
    safe_print(f"Hello, {name}!")

@handler.command(name="add", description="Adds two numbers.")
def add(a, b):
    safe_print(int(a) + int(b))

handler.start()

# Using safe_print allows you to print logs in the background 
# without messing up the user's current input line.
```

## Async Client Example

The `AsyncInputHandler` integrates with `asyncio`. The `start()` method is non-blocking when `thread_mode=True` (default).

```python
import asyncio
from cli_ih import AsyncInputHandler, safe_print

handler = AsyncInputHandler(cursor="Async> ")

@handler.command(name="greet", description="Greets the user asynchronously.")
async def greet(name):
    await asyncio.sleep(1)
    safe_print(f"Hello, {name}")

@handler.command(name="add", description="Adds two numbers.")
async def add(a, b):
    safe_print(int(a) + int(b))

# Start the handler (runs in a separate thread by default)
handler.start()

# Keep the main thread alive or run your main event loop
async def main():
    while handler.is_running:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Considerations

### Safe Printing
Always use `from cli_ih import safe_print` for outputting text to the console. This utility automatically detects the active input handler and ensures that your log message is printed *above* the current input line, preserving the user's cursor and any text they are currently typing.

```python
from cli_ih import safe_print

# Good
safe_print("Log message")

# Avoid (might disrupt input line)
print("Log message")
```

### Thread Mode
Both `InputHandler` and `AsyncInputHandler` accept a `thread_mode` parameter (default `True`).
- `thread_mode=True`: The input loop runs in a separate thread. `start()` returns immediately.
- `thread_mode=False`: The input loop runs in the current thread. `start()` blocks until exit.

### Command History
Use the **Up** and **Down** arrow keys to cycle through your previously entered commands, just like in a standard terminal.