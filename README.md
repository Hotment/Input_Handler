# InputHandler Library

A lightweight Python library for creating interactive command-line interfaces with custom command registration and input handling. It supports threaded input processing and includes enhanced logging with color-coded output.

## Features

- Command registration system with descriptions
- Threaded or non-threaded input handling
- Colored logging with support for debug mode
- Built-in `help`, `debug`, and `exit` commands
- Error handling for missing or invalid command arguments

## Installation

`pip install cli_ih`

## Quick Start

```python
from cli_ih import InputHandler

def greet(args):
    print(f"Hello, {' '.join(args)}!")

handler = InputHandler()
handler.register_command("greet", greet, "Greets the user. Usage: greet [name]")
handler.start()

# Now type commands like:
# > greet world
# > help
# > debug
# > exit
```

## Additional Info

- You can also import the `logging` module from `cli-ih` to use the same config as the module
- You can provide the `thread_mode` param to the `InputHandler` class to set if it shoud run in a thread or no.
(If you are using the `cli-ih` module on its own without any other background task set `thread_mode=False` to false)
- You can also provide a `cursor` param to the `InputHandler` class to set the cli cursor (default cusor is empty)