#!/usr/bin/env python3
"""Regression gate for loop0001. Exit 0 = green.

1. Metacat/ (the original 1.2 source) is byte-for-byte unchanged since the
   import commit, and has no untracked files.
2. tests/run-tests.sh, once item 00 has created it, passes. It is the single
   entry point for every test in the repo (Chez oracle checks, raco test, the
   Racket-vs-Chez equivalence runs, the GUI render checks).

Run from anywhere: python3 ralph_loops/loop0001/gate.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPORT_COMMIT = "9f072c0"
RUN_TESTS = REPO / "tests" / "run-tests.sh"


def step(name: str, cmd: list[str]) -> bool:
    print(f"== {name}: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=REPO)
    print(f"== {name}: {'ok' if proc.returncode == 0 else 'FAILED'}", flush=True)
    return proc.returncode == 0


def original_untouched() -> bool:
    diff = subprocess.run(["git", "diff", "--quiet", IMPORT_COMMIT, "--", "Metacat"],
                          cwd=REPO).returncode
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "Metacat"],
                               cwd=REPO, capture_output=True, text=True).stdout.strip()
    if diff != 0:
        print("Metacat/ differs from the import commit; the original must not be edited")
    if untracked:
        print("untracked files in Metacat/:\n" + untracked)
    ok = diff == 0 and not untracked
    print(f"== original untouched: {'ok' if ok else 'FAILED'}", flush=True)
    return ok


def main() -> int:
    ok = original_untouched()
    if RUN_TESTS.exists():
        ok = step("tests", ["bash", str(RUN_TESTS)]) and ok
    else:
        print("== tests: tests/run-tests.sh does not exist yet (item 00 creates it)")
    print("GATE " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
