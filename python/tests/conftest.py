# Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).
# Makes python/oracle/ (capture.py) and python/tests/ (helpers) importable.
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for path in (HERE, HERE.parent / "oracle"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
