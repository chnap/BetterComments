#!/usr/bin/env python3
"""Run BetterComments directly from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
PACKAGE_ROOT = SOURCE_ROOT / "bettercomments"

# Let local imports treat this required script as the source package shim.
__path__ = [str(PACKAGE_ROOT)]
__version__ = "0.1.0"


def _run() -> int:
    source_path = str(SOURCE_ROOT)
    if source_path in sys.path:
        sys.path.remove(source_path)
    sys.path.insert(0, source_path)

    from bettercomments.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
