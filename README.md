# InputHandler Library

A lightweight Python library for creating interactive command-line interfaces with custom command registration and input handling. It supports threaded input processing and includes enhanced logging with color-coded output.

## Features

- Command registration system with descriptions
- Threaded or non-threaded input handling
- Colored logging with support for debug mode
- Built-in `help`, `debug`, and `exit` commands
- Error handling for missing or invalid command arguments
- NEW: Register commands with decorators

## Installation

`pip install cli_ih`

## Quick Start

```python
from cli_ih import InputHandler

def greet(args):
    print(f"Hello, {' '.join(args)}!")

handler = InputHandler(cursor="> ")
# NEW
@handler.command(name="add", description="Performs the `+` operator on the first 2 arguments.") # The name param will use the func name if its not provided
def add(args):
    print(int(args[0])+int(args[1]))

handler.register_command("greet", greet, "Greets the user. Usage: greet [name]")
handler.start()

# Now type commands like:
# > greet world
# Hello, world!
# > add 1 2
# 3
# > help
# Available commands:
#   help: Displays all the available commands
#   debug: If a logger is present changes the logging level to DEBUG.
#   exit: Exits the Input Handler irreversibly.
#   add: Performs the `+` operator on the first 2 arguments.
#   greet: Greets the user. Usage: greet [name]
#
# > debug
# > exit
```

## New Async client
```python
import asyncio
from cli_ih import AsyncInputHandler

print(cli_ih.__version__)

handler = AsyncInputHandler(cursor="> ")

@handler.command(name="greet", description="Greets the user. Usage: greet [name]")
async def greet(name, *args):
    await asyncio.sleep(1)
    print(f"Hello, {name}{" " if args else ""}{' '.join(args)}!")
# NEW
@handler.command(name="add", description="Performs the `+` operator on the first 2 arguments.")
async def add(a, b):
    print(a+b)

asyncio.run(handler.start())
```

## Additional Info

- You can provide a valid logger `logger=logger` to the `InputHandler` to enable logging (this will be removed soon)
- You can provide the `thread_mode` param to the `InputHandler` class to set if it shoud run in a thread or no.
(If you are using the `cli-ih` module on its own without any other background task set `thread_mode=False` to false)
- You can also provide a `cursor` param to the `InputHandler` class to set the cli cursor (default cusor is empty)
