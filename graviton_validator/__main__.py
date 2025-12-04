#!/usr/bin/env python3
"""
Entry point for running graviton_validator as a module.
"""

import sys
import os

# Add the parent directory to the path so we can import the main script
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from graviton_validator import main

if __name__ == '__main__':
    sys.exit(main())