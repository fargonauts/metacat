# Progress Log

## Ralph Loop 0003 Status
- **Started**: (not started)
- **Target**: 12 items
- **Current**: 3/12 SOLVED

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

---

## Iteration 3 — 2026-10-04 16:41:46
Item **02 The Qt canvas**: SOLVED.

### Completed
- **Tests first, and they failed first.** `python/tests/test_qt_canvas.py` and its helper
  `python/tests/canvas_streams.py` were written before any code. The tkinter reference
  `python/tests/data/tk-display-lists.json` was generated, then the first run gave
  `12 failed, 2 passed` (`ModuleNotFoundError: metacat.qt.canvas`). After the first
  implementation, the exact comparison failed on Tk's polygon bbox rule (see below), and
  then on a wrong expectation in my own scene test (it forgot the paint margin).
- **The reference** (`canvas_streams.py`, under `xvfb-run`, under a second): the two
  `sgl-tcl` fixture streams (parsed directly, because the test reader can't read
  `\x2D;`), and a synthetic stream that reaches what the fixtures don't. That covers
  arrows (first, last, both), `-smooth`, `-justify` with multi-line text, all nine
  anchors, `lower`, `raise` above an item, ids as targets, tag lists, `scale` (negative
  too), `move all`, hidden, disabled and fill-less items, colour forms (`#abc`,
  `#123456789`, CamelCase names), and 160 random arcs, rectangles, ovals, lines and
  polygons at fractional coordinates. Each stream is replayed into tkinter Canvases. The
  dump records the display list through `find all`, `type`, `coords`, `itemcget` (every
  option of the item's kind), `gettags` and `bbox`, plus the answers of every `create`,
  `bbox` and `canvasx`/`canvasy`, and Tk's own text metrics (`font measure`, `font
  metrics -linespace`).
- **`python/metacat/qt/displaylist.py`** (no Qt): Tk 8.6's display list, with ids that
  are never reused, the stacking order, tag/id/`all` searches, `create` with Tk's
  defaults and option checks (errors as `TclError`), `delete`, `move`, `scale`,
  `raise`/`lower` (Tk's RelinkItems), `itemconfigure`, `bbox` with Tk's per-kind rules
  (rect/oval bloat, arc end points and quadrants, line and polygon fudge, arrowheads,
  text anchors with ROUND and the cursor fudge), `canvasx`/`canvasy`, and the queries
  above. Colour words are read as Tk 8.6 reads them. Arc angles are normalised, and
  rectangle/oval/arc corners are sorted. One `RLock` covers each command, so any thread
  may draw. The display list records dirty ids and a "restacked" flag for the scene.
- **`python/metacat/qt/canvas.py`**: `QtCanvas`, with `tcl` (answers shaped like
  `swl.TkCanvas`'s), `get_background_color`, `set_background_color_bang`, `set_origin`,
  and `sync()`, which runs on the GUI thread and applies the changes to the
  `QGraphicsScene`. `TkItem` paints each kind as X11 does: rounded corners, Tk's pen
  widths and DashConvert patterns, butt caps, round joins on lines and polygons, pies and
  chords, arrowheads, Tk's spline for `-smooth`, and justified multi-line text. There
  is no antialiasing except on text. **`python/metacat/qt/fonts.py`**: Tk font word →
  `QFont` (negative size = pixels, positive = points at 96 dpi, styles), and
  `QtMetrics`, which measures with the same `QFont`. This is a first mapping; item 03
  completes it.
- **Results:**
  - with Tk's text metrics, the Qt display list is **identical** to Tk's for all three
    streams (ids, order, kinds, coordinates, every option, tags, every bbox, `bbox all`,
    every answer);
  - with Qt's fonts, only text extents differ: widths by 1 px at most, heights by 5 px
    at most (tolerance 6);
  - every inventoried command and option is accepted, and the Tk errors are raised;
  - 8 threads drawing at once produce 1600 unique ids;
  - the scene follows the display list: z order after `raise`, hidden items, delete,
    move, background.
- **Pictures, inspected:** `sgl-fixture.scm` drawn through `metacat/gui/sgl.py` onto the Qt
  canvas, with text measured on a Qt hidden canvas, passes all 16 of
  `render_sgl_fixture.py`'s pixel checks. 97.7% of its pixels match
  `docs/screenshots/panels/sgl-fixture-python.png` within 24 levels. I looked at it next
  to the tkinter one, at 3× zoom on rectangles, arcs, dashes and the "erase" cell. The
  differences are antialiased text a pixel lower (Qt's taller metrics), dash phase,
  slightly rounder 2-px circles, and X11's jog in the 5-px diagonal line, which Qt draws
  straight. Committed as `docs/screenshots/panels/sgl-fixture-qt.png`, with a section in
  `docs/screenshots/README.md`. The frozen v1 stream replayed into the Qt canvas passes
  the same pixel checks.
- **Logged** in `docs/anomalies_and_quirks.md`:
  - Tk 8.6 gives five colour names web values (TIP 403), and reads `#abc` as `#aabbcc`;
  - Tk 8.6.13's measured bbox rules: a polygon's outline adds `(int)(width+1)/2`;
    `canvasx` rounds to a whole pixel; a text without fill has no bbox;
  - Qt's font metrics are taller than Xft's for the same faces (open, item 03);
  - X11's jog in wide lines.

  `docs/divergences.md` has a new "Python Qt GUI" section, and `docs/qt-gui-plan.md` 2.6
  an "As built" paragraph: dirty ids instead of a journal, so one update per changed
  item per sync.
- `tk_canvas_inventory.py`: `metacat/qt/canvas.py`'s `tcl` added to `FORWARDERS`. It is a
  canvas that passes on what it's given. `python/tests/README.md`: rows for
  `test_qt_canvas.py` and `canvas_streams.py`, and new totals (1454: 1028 fast, 426
  slow).
- Gate: `python3 ralph_loops/loop0003/gate.py`: GATE PASSED (1454 passed in 7:37, no
  warnings; racket/ unchanged).

### Blockers
- None for item 02. Item 00 is still `[!]` from session 1 (its deliverables exist and
  their tests pass; see iteration 2).

### Next
- Item 03, fonts and colours: make Qt's text metrics match Tk's (the heights: Qt
  `ascent+descent` 15 against Tk's linespace 12 for 11-px Helvetica), then tighten
  `TEXT_TOLERANCE` in `test_qt_canvas.py`. Check the tiny Coderack labels. The colour
  reading is already in `displaylist.color_rgb`.
- Item 04 will need `QtCanvas.sync()` called on a timer (item 05 batches it) and
  `set_origin` from the view's scroll position.


---

## Iteration 4 — 2026-10-04 17:08:35
Item **03 Fonts and colours**: SOLVED.

### Completed
- **Tests first, and they failed first.** `python/tests/test_qt_fonts.py` and its Tk
  reference were written before any code. First run: `40 failed, 24 passed` (no
  `metacat.qt.fontspec`, no `families`/`install`/`descent`, Qt's heights too tall, the
  canvas accepting `-font {helvetica -11 heavy}`). Three of my own expectations were then
  wrong and were corrected, not loosened silently: `bbox` answers a list; Tk and Qt widths
  differ by up to 6 pixels for 22-pixel bold Helvetica (now 97% exact, 98% within 1, all
  within 6); antialiased 1-pixel stems straddle two columns, so the thin-letter test
  counts local minima.
- **The reference**: `python/tests/tk_fonts_colors.py` under Xvfb writes
  `python/tests/data/tk-fonts-colors.json`: Tk's ascent, descent, linespace, actual family
  and the widths of 8 samples for 252 font words (Helvetica, Times, Courier; −5…−30 pixels
  and 8…24 points; 4 styles), and `winfo rgb` of all 752 colour names of `colors.py`. Its
  slow test regenerates it and compares.
- **Finding: the tkinter GUI's Tk has no Xft.** Anaconda's `libtk8.6.so` links libX11
  only; Tk draws X core fonts, which the X server rasterises from
  `/usr/share/fonts/X11/Type1` as 1-bit bitmaps, and their ascent/descent are glyph-ink
  extents.
- **`python/metacat/qt/fontspec.py`** (no Qt): Tk 8.6's ParseFontNameObj: list form with
  any style words or style lists (later weight/slant wins, case-sensitive), the `-family
  -size -weight -slant -underline -overstrike` form, Tk's named fonts as Helvetica −12,
  size 0 = default, points → `(int)(pt·96/72+0.5)` pixels, and Tk's error messages. The
  display list now checks `-font` with it (an item with a bad font isn't created).
- **`python/metacat/qt/fonts.py`** completed: `qfont` from the spec; `QtMetrics` measures
  widths with `horizontalAdvance` and takes ascent/descent from the ink of the font's
  printable Latin-1 glyphs (`QRawFont.boundingRect`, rounded up), as X's core fonts do.
  Linespace is now within 3 px of Tk's for all 252 fonts (within 1 for 79%), ascent within
  1 for all; before, Qt's OS/2 win ascent made it up to 7 px taller. `families()` (Qt's
  families lower-cased, ` [foundry]` stripped, plus fonts.ss's preferred faces that
  fontconfig maps onto a real face rather than its fallback) and `install()` (fonts.ss
  picks faces from them and measures on a `HiddenCanvas`, a `QtCanvas` that drops its
  change records at each `delete`). Here: serif `times new roman` (Liberation Serif),
  sans-serif `helvetica` (Nimbus Sans), fancy `palatino linotype` (P052).
- **Measurement consistency** tested: a text item's `bbox` = measured width + Tk's cursor
  pixel by the linespace; `horizontalAdvance` of the drawing `QFont` equals the
  measurer's width; the drawn ink lies inside the bbox and fills it but the side
  bearings; `FixedFont get-pixel-size` after `install()` gives the Qt numbers.
- **Colours**: all 752 names read as Tk reads them (the 5 TIP 403 names differ from
  `colors.py`, as logged in item 02), upper case too; every `Rgb` of `colors.py`,
  `constants.py` and `*color-names*` round-trips through `swl.tcl_word`; the scene paints
  the exact RGB.
- **`TEXT_TOLERANCE` in `test_qt_canvas.py` tightened from 6 to 2** (fails at 1).
- **The UFO answered.** `python/tests/render_small_text.py` draws the Coderack's labels at
  5–11 px with Tk and with Qt: `docs/screenshots/panels/small-text-tk.png` and
  `small-text-qt.png` (inspected). The default Coderack is 598 px high, so the labels are
  8 px; Tk's core fonts drop the `i`s and `l`s at 8, 9 and 10 px (not 7 or 11); Qt draws
  every letter at the same widths. Test:
  `test_tiny_coderack_labels_keep_their_thin_letters`. The SGL fixture picture
  re-rendered and inspected: 97.8% of pixels match the tkinter one (was 97.7%);
  `docs/screenshots/panels/sgl-fixture-qt.png` updated.
- **Docs**: `docs/anomalies_and_quirks.md`: the UFO entry explained; "Qt's metrics taller"
  explained and worked around; new entries for the 22-px width differences (two hinters)
  and Qt's foundry-suffixed family names and alias resolution (Anaconda's `fc-match`
  answers KaTeX_AMS for everything). `docs/divergences.md` (Python Qt GUI): ink metrics,
  antialiased text, and the faces (Liberation Serif for serif where tkinter uses Nimbus
  Roman). `docs/qt-gui-plan.md` 2.6 "As built (item 03)". `docs/screenshots/README.md`:
  small-text section. `python/tests/README.md`: rows for the new test, reference script
  and render script; totals 1518 (1091 fast, 427 slow).
- Gate: `python3 ralph_loops/loop0003/gate.py`: GATE PASSED (1518 passed in 7:37; racket/
  unchanged).

### Blockers
- None for item 03. Item 00 is still `[!]` from session 1 (deliverables exist and pass;
  see iteration 2).

### Next
- Item 04 (the Qt host): call `fonts.install()` when the Qt GUI starts (before the
  panels select their fonts), call `QtCanvas.sync()` on a timer, and set `set_origin`
  from each view's scroll position. The Logo's scrollbar sizes still need Qt values
  (`QStyle.PM_ScrollBarExtent`).
