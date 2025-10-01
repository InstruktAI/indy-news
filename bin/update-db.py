#!/usr/bin/env python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.store import get_data

if __name__ == "__main__":
    print("Updating database...")
    data = get_data(force=True)
    print(f"Updated database with {len(data)} entries")
