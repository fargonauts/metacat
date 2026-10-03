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
  - `attach-workspace-view!` sets gui.ss's speed settings as at full speed with no
    flashing (`%flash-pause%` 0, `%snag-pause%` 0, `%num-of-flashes%` 1). The original
    set them from the speed slider when the control panel was made.
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
- **Tests:** racket/tests/workspace-view-test.rkt runs all 109 golden runs with the
  Workspace window attached and requires identical traces; its pixel snapshots and
  racket/tests/sgl-test.rkt's pin the rendering.
