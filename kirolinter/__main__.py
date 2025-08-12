#!/usr/bin/env python3
"""
KiroLinter main entry point.

This allows the package to be run as a module:
    python -m kirolinter
"""

from .cli import cli

if __name__ == "__main__":
    cli()