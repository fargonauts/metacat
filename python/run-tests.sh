#!/usr/bin/env bash
# The single entry point for the Python port's tests; the gate
# (ralph_loops/loop0002/gate.py) runs it with no arguments.
#
#   bash python/run-tests.sh          # full tier: every test, including the ones
#                                     # marked slow (Chez re-captures, the 109
#                                     # golden runs, the CLI against the live oracle,
#                                     # the 720 extra-seed runs and their oracle
#                                     # re-capture, the 109 goldens with every
#                                     # view attached, the panels drawn on Tk and
#                                     # the SGL fixture drawn on Tk, the GUI
#                                     # driven through its widgets (drive_gui.py)
#                                     # under xvfb-run, never on the real screen);
#                                     # about 7 min on 32 idle cores
#   bash python/run-tests.sh --fast   # fast tier: skips tests marked slow (about
#                                     # 10 s); for iterating on the code
#
# Any other arguments are passed to pytest.  Stops at the first failure (-x).
set -euo pipefail
cd "$(dirname "$0")"
args=()
if [[ "${1:-}" == "--fast" ]]; then
  args+=(-m "not slow")
  shift
fi
exec python3 -m pytest -x -q "${args[@]}" "$@"
