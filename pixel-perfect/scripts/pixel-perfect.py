#!/usr/bin/env python3
"""Run the bundled pixel-perfect CLI.

Usage examples:
    python scripts/pixel-perfect.py inspect --reference proposals/ui.png --project-root .
    python scripts/pixel-perfect.py render --reference proposals/ui.png --output .artifacts/candidate.png
    python scripts/pixel-perfect.py compare --reference proposals/ui.png --candidate .artifacts/candidate.png
    python scripts/pixel-perfect.py verify --reference proposals/ui.png --url http://localhost:3000
"""

from __future__ import annotations

from pixel_perfect.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
