#!/usr/bin/env python
"""
Railway bot starter script.
This script ensures PYTHONPATH is set correctly and imports the bot module.
"""
from __future__ import annotations

from pathlib import Path
import sys

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import and run the bot
from telegram_interface.bot import main

if __name__ == "__main__":
    main()
