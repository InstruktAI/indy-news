#!/usr/bin/env python
from api.store import get_data

if __name__ == "__main__":
    print("Updating database...")
    data = get_data(force=True)
    print(f"Updated database with {len(data)} entries")
