#!/usr/bin/env python3
"""
LastAgent CLI Entry Point

This module provides the main entry point for the LastAgent CLI.
Run with: lastagent or python -m cli
"""

from cli.app import app


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
