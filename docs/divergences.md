# Divergences from the original

Where the Racket port deliberately behaves differently from Metacat 1.2 in
`chez_scheme/original/`. Without an entry here, the original is right.
Each entry: what differs, where, why, and how the oracle/tests account for it.

## Drawing: Tk's canvas is emulated on racket/draw (item 12)
- **What:** the original drew its SGL pictures as Tk 8.x canvas items, measured text
  with Tk on the logo window's hidden canvas, and sized fonts at the screen's resolution.
  racket/gui/sgl.rkt records the same canvas items (checked against the original by
  tests/diff/sgl-battery.scm) but paints them itself on a racket/draw `dc<%>`, and
  racket/gui/fonts.rkt measures text with racket/draw on a private bitmap dc, with
  point sizes converted at a fixed 96 dpi. So:
  - pixels differ from a Tk screenshot: the faces are whatever fontconfig gives for
    `times`/`helvetica`, text widths and heights come from Pango (Tk's text bbox may be
    a pixel or two larger), arcs and dashed curves are drawn by Cairo (dashed curves
    are flattened first), and line ends follow X11's rule only approximately;
  - `get-pixel-size` works without `(create-mcat-logo)`, where the original raised
    "need to run (create-mcat-logo) first";
  - a font's `get-actual-values` reports the requested face (not the face fontconfig
    picks), and a pixel size as points at 96 dpi.
- **Why:** Tk is not available to Racket; racket/draw is the target the item names.
  Fixed 96 dpi keeps offscreen renderings (and the snapshot test) independent of the
  display.
- **Tests:** none of this reaches the model: the engine never measures text (the golden
  runs are headless). racket/tests/sgl-test.rkt pins the rendering with a pixel snapshot.

## Windows: offscreen hosts, aliased text, full-speed settings (item 13)
- **What:**
  - general-graphics.ss's `make-graphics-window` made a Tk toplevel with a frame or
    scrollframe around the viewport. racket/gui/views.rkt makes a *window host* instead
    (`make-window-host`): offscreen by default (it keeps the title and geometry and has
    no scrollbars), replaced by on-screen hosts once the control panel exists (item 15,
    `set-window-host-maker!`). `reposition-vertical-scrollbar` scrolls the viewport
    itself, rather than waiting for a Tk scrollbar to appear.
  - Text is drawn aliased (`'unsmoothed`). Item 12 used greyscale antialiasing.
  - `attach-views!` (and item 13's `attach-workspace-view!`) set gui.ss's speed settings
    as at full speed with no flashing (`%num-of-flashes%` 1, `%flash-pause%` 0,
    `%snag-pause%` 0, `%codelet-highlight-pause%` 0, `%text-scroll-pause%` 0). The
    original set them from the speed slider when the control panel was made; with the
    control panel (item 15) the slider sets them as in the original.
- **Why:**
  - Hosts: racket/gui is not available to engine-side tests, and pictures of the views
    must be possible without a display.
  - Aliased text: the graphics erase by drawing the same text again in the background
    colour. Over antialiased text that leaves grey fringes (seen in the first renders
    of item 13: a ghost "?" where the answer is drawn, smears after concept mappings
    that switched font). X11's core fonts, which the dissertation's screenshots show,
    were aliased, so overpainting erased them exactly.
  - Speed settings: no control panel yet. The pauses only make the program wait, and
    with `%flash-pause%` 0 a flash draws nothing.
- **Tests:** racket/tests/views-test.rkt (item 13's workspace-view-test.rkt) runs all 109
  golden runs with every window attached (item 14) and requires identical traces; its pixel snapshots and
  racket/tests/sgl-test.rkt's pin the rendering.

## The control panel and windows on racket/gui (item 15)
- **What:**
  - gui.ss's widgets are racket/gui's (racket/gui/gui.rktl). The actions, the control
    panel object's messages and their effects, and the window controllers are the
    original's. These differ:
    - racket/gui gives no colours to panels, buttons or menu items, and no fonts to
      menu items. The control panel keeps its fonts and the labels' colours. The
      command line's run mode is "running..." on a green field (the original:
      green bold italic on black). Highlighted menu items (the last demo, the
      commentary font) are checked items.
    - Help and Clear Memory were commands in SWL's menu bar; racket/gui's menu bar only
      holds menus, so they are in a Help menu and a Memory menu.
    - `display-error` and the input dialogs' "Invalid input!" turn red for 700 ms on a
      timer instead of `(pause 700)` in the event thread.
    - Dialogs are frames, not modal; their `destroy` runs the destroy-request handler,
      as SWL's did.
    - The speed slider's initial value sets the speed when the panel is made (Tk's scale
      command did it).
  - An error in the model, which stopped the original at the REPL with the panel still
    in run mode, returns the panel to input mode and shows "Error: ..." in it.
  - Windows are tiled on the screen (racket/gui/gui.rkt's `arrange-windows!`); the
    original left placement to the window manager. Aspect-ratio bounds are not enforced
    (racket/gui has none); resizing still goes through the original resize handler and
    listener.
  - `create-mcat-logo` measures nothing: scrollbars are Tk's X11 size (15 pixels), and
    fonts measure on a private bitmap (item 12).
  - The REPL thread is an engine thread that runs the thunks the control panel hands it
    with `thread-break`. There is no REPL: `racket racket/main.rkt` opens the windows as
    `(setup)` did.
- **Why:** racket/gui's widget set; a display-free test suite for everything else.
- **Tests:** racket/gui-tests/control-panel-test.rkt drives the panel's own widgets on
  Xvfb. Its full, stepped, stopped and resumed, breakpointed and reset runs all end at
  the golden's codelet count and generator state.

## Entry points: a command line, a headless CLI and a standalone program (items 11, 15–16)
- **What:** the original was used from the Chez/SWL REPL: `(setup)` opened the windows,
  and `(run ...)`/`(mcat ...)` or the control panel ran problems. The port has no REPL.
  - `racket racket/main.rkt [SCALE]` does what `(setup)` did.
  - `racket racket/cli.rkt INITIAL MODIFIED TARGET [ANSWER] [--seed N] [--max-codelets K]
    [--keep-going] [--trace FILE] [--verbose]` runs a problem headless. It is the port's
    counterpart of the oracle's `chez_scheme/oracle/run.ss`, which is not part of the
    original either. It prints the commentary, answers and a summary, and the run ends
    where the original would wait for Go, unless `--keep-going`.
  - The standalone `metacat` program (make-dist.sh) opens the GUI with no arguments or a
    scale, and is the CLI otherwise.
- **Why:** there is no SWL REPL to type into; batch runs and tests need a program.
- **Tests:** racket/tests/cli-test.rkt (the CLI against the oracle's run.ss, output and
  exit codes, including `--verbose`), racket/gui-tests/dist-test.rkt (the standalone
  program), racket/gui-tests/control-panel-test.rkt (the GUI).

## Python Qt GUI: the Tk canvas on a QGraphicsScene (loop0003 item 02)
- **What:** in the Qt GUI (`python3 -m metacat.qt`), the panels' Tk canvas commands are not
  run by Tk. `python/metacat/qt/displaylist.py` keeps Tk 8.6's display list itself: ids,
  stacking, tags, options, `move`, `scale`, `raise`/`lower`, `itemconfigure`, and `bbox`
  with Tk's rules. `python/metacat/qt/canvas.py` paints each item on a `QGraphicsScene`
  as X11 would: corners rounded to whole pixels, Tk's pen widths and dash patterns,
  butt caps, no antialiasing except for text. So:
  - pixels differ from the tkinter GUI's: Qt rasterises wide lines, arcs and dash phases
    a little differently (X11's jog in wide diagonal lines is gone), and text is drawn
    by Qt;
  - text extents come from Qt's metrics of the same fontconfig faces. The widths agree
    within a pixel, but the heights are up to 5 pixels taller (item 03 maps the fonts);
  - colour words are read as Tk 8.6 reads them (`gray` is `#808080`), but the panels
    only send `#rrggbb`.
- **Why:** the single-window GUI is Qt; Tk can't draw into it.
- **Tests:** `python/tests/test_qt_canvas.py` replays every `sgl-tcl` stream and a
  synthetic one into the Qt canvas and into a tkinter Canvas (reference
  `python/tests/data/tk-display-lists.json`). With Tk's text metrics, every item, option,
  tag, coordinate and `bbox` answer is identical; with Qt's fonts, only text extents
  differ, by 5 pixels at most. The SGL fixture drawn on the Qt canvas passes
  `render_sgl_fixture.py`'s pixel checks, and 97.7% of its pixels match the tkinter
  picture.
