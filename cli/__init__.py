"""
LastAgent CLI

Command-line interface for LastAgent operations.
This module re-exports the main CLI app for backwards compatibility.
"""

from cli.app import app
from cli.__main__ import main

__all__ = ["app", "main"]
