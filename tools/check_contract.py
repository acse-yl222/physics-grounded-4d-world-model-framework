#!/usr/bin/env python3
"""Repository CLI compatibility entrypoint for the shared contract validator."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common.contract import main, validate

__all__ = ["main", "validate"]  # tests/test_contract.py loads this file and calls validate.

if __name__ == "__main__":
    sys.exit(main())
