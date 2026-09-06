"""Make scripts/ importable so the pure helpers can be tested directly.

The scripts are standalone CLIs, not a package — they live outside any
importable path, so the suite prepends scripts/ to sys.path.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
