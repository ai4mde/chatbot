import importlib.metadata

try:
    __version__ = importlib.metadata.version("chatback")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.7.0"  # fallback version 