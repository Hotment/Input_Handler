from .client import InputHandler
from .asyncClient import AsyncInputHandler
from .utils import safe_print
import importlib.metadata

try:
    __version__ = importlib.metadata.version("cli-ih")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"