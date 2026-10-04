# Progress Log

## Ralph Loop 0003 Status
- **Started**: (not started)
- **Target**: 12 items
- **Current**: 1/12 SOLVED

---

## Iteration 1 — 2026-10-04 15:29:35
### Completed
- (driver) session ended with outcome `error` without marking the item
### Blockers
- see session_it01.log
### Next
- revisit or re-open this item

---

## Iteration 2 — 2026-10-04 16:02:02
Item **01 Skeleton and test harness**: SOLVED.

### Completed
- **Tests first, and they failed first.** `python/tests/test_qt_skeleton.py` and
  `python/tests/test_tk_canvas_inventory.py` were written before any code. First run:
  the inventory test failed at collection (`ModuleNotFoundError: tk_canvas_inventory`);
  the skeleton test gave 7 failed, 1 error, 2 passed (no `metacat.qt`, no `qt` extra,
  `run-tests.sh` not wired; the skip test failed with a pytest-qt `INTERNALERROR`, see
  below). `test_qt_tests_run_after_the_others` was added later, also failing first.
- **`python/metacat/qt/`**: `__init__.py` (`has_pyside6()`, no Qt import),
  `__main__.py` and `app.py` (`python3 -m metacat.qt [--quit-after MS]`), `mainwindow.py`
  (an empty `QMainWindow` titled Metacat, 1366×768), `grab.py` (`grab_png(widget, path)`:
  `QWidget.grab()` to a PNG). Screenshot of the empty window inspected (plain grey, the
  right size).
- **Harness**: `pyproject.toml` has the `qt = ["PySide6>=6.5"]` extra and the
  `metacat.qt` package (test_install.py updated); conftest.py has the session `qapp`
  fixture (forces `QT_QPA_PLATFORM=offscreen`, closes all windows and quits at the end)
  and `grab(widget, name)` (PNGs in `python/tests/screenshots-qt/`, git-ignored). Every
  `test_qt_*.py` starts with `pytest.importorskip("PySide6...")`; a test runs a fresh
  pytest with PySide6 hidden and checks that every Qt file is skipped, and another checks
  the guard convention. `run-tests.sh` exports `QT_QPA_PLATFORM=offscreen`, unsets
  `WAYLAND_DISPLAY`, and has `--qt` (Qt tests only). Qt tests sit in the normal tiers
  (fast unless marked slow).
- **Two environment fixes, both logged in `docs/anomalies_and_quirks.md`:**
  - pytest-qt (installed on this machine) aborts all of pytest when no Qt binding
    imports. `addopts = "-p no:pytest-qt"` in pyproject.toml; `-p no:pytestqt` silently
    does nothing;
  - the offscreen `QApplication` starts a thread, and later test files fork (32
    "fork() may lead to deadlocks" warnings in the first gate run). conftest.py now runs
    the `test_qt_*.py` files last; the second gate run had no warnings.
- **The Tk canvas command inventory**, `python/tests/data/tk-canvas-commands.json`, made
  by `python/tests/tk_canvas_inventory.py` from three parts:
  - code: `ast` scan of every `tcl_eval`, `swl_tcl_eval` and `.tcl` call in
    `python/metacat/`. A computed command outside the three known forwarders is an error;
  - fixtures: both `sgl-tcl` streams (636 lines);
  - runs: recording canvases (and a recording hidden canvas) in run7 and
    `abc abd xyz wyz` seed 1 with every view attached (120,344 commands, 3.3 s).

  It lists 14 commands: create rectangle, line, oval, arc, polygon and text with their
  options; delete, move, itemconfigure (`-state`, `-tags`), bbox, raise and scale (only
  in the fixtures, never in a run), and canvasx/canvasy (code only). It also lists the
  enumerated values (anchor s/nw, style arc/pieslice, state hidden/normal, dash
  ""/"- "/". "), the target forms, the 22 tag words (always single words) and the
  canvas methods. The fast tests compare the code and fixture parts with the committed
  list, and a synthetic panel module that sends `create window`, `itemconfigure -fill`
  or `lower` is caught. The slow tests compare the runs part and the whole list. Summary
  table added to `docs/qt-gui-plan.md` 2.6.
- `python/tests/README.md`: rows for both test files and the helper, the Qt fixtures,
  `--qt`, and the new totals (1439 tests: 1014 fast, 425 slow).
- Gate: `python3 ralph_loops/loop0003/gate.py`: GATE PASSED (1439 passed in 8:01, no
  warnings; racket/ unchanged).

### Blockers
- None for item 01.
- Item 00 is still marked `[!]` because session 1 lost its API connection while running
  the gate. Its deliverables were committed (`docs/qt-gui-plan.md`,
  `tk-gui-inventory.json`, `tk_gui_inventory.py`, `test_tk_gui_inventory.py`), and their
  tests pass in this iteration's full gate. A later session (or the owner) can re-check
  it and mark it `[x]`; this session left it alone.

### Next
- Item 02, the Qt canvas: implement exactly the commands in `tk-canvas-commands.json`
  (display list first, then the scene), and test it against tkinter by replaying the
  `sgl-tcl` streams.
