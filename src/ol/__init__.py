"""Ollama REPL wrapper package."""

__version__ = "0.1.11"

from .init import initialize_ol

# Run initialization when package is imported
initialize_ol() 