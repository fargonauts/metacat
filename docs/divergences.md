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
