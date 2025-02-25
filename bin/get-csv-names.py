#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.store import get_data


def main():
    # Get the data
    data = get_data()

    # Extract and print names as comma-separated list
    names = [item["Name"] for item in data]
    print(",".join(names))


if __name__ == "__main__":
    main()
