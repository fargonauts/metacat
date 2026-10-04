"""Window hosts: SWL's <toplevel> with its <frame> or <scrollframe> (item 14).

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026), after racket/gui/views.rkt's window-host%.

general-graphics.ss's make-graphics-window creates a <toplevel>, a <frame> or
<scrollframe> in it, and a <viewport> (an SWL <canvas>) in that.  Here one
"window host" stands for the toplevel and its frame, and gives the viewport its
canvas (`make_canvas`): any object with tcl(*args), get_background_color() and
set_background_color_bang(color), as swl.TkCanvas has.

- `OffscreenHost` (the default): keeps the title and geometry, has no
  scrollbars, and its canvas (`OffscreenCanvas`) executes nothing but counts
  the items created on it.  Text is measured by `OffscreenHiddenCanvas`, a
  fixed metric (python/oracle/sgl-tcl.ss's), installed as fonts.ss's
  *hidden-canvas* by `install_offscreen_fonts`.  Runs with offscreen views
  draw everything the original draws, without Tk.
- `TkHost`: a tkinter Toplevel and Canvas (for pictures under Xvfb, and the
  GUI of item 15), made by `tk_host_maker(root)`.

`set_window_host_maker(maker)` chooses which one make-graphics-window gets.
This module does not import tkinter at import time.
"""
from __future__ import annotations

from fractions import Fraction

from metacat import chez


class OffscreenCanvas:
    """port: an SWL <canvas> that draws nothing.  It counts the items created
    on it (`items`) and the commands it got (`commands`)."""

    def __init__(self, background):
        self.background = background
        self.items = 0
        self.commands = 0

    def tcl(self, *args):
        self.commands += 1
        if args and args[0] == "create":
            self.items += 1
            return chez.String(str(self.items))
        return chez.String("")

    def get_background_color(self):
        return self.background

    def set_background_color_bang(self, color):
        self.background = color


def offscreen_metric(string, font):
    """python/oracle/sgl-tcl.ss's $metric: the bbox of a text item, from the
    font's size and style alone (no Tk)."""
    size, style = font.size, font.style
    px = -size if size < 0 else chez.exact_round(Fraction(size * 4, 3))
    cw = (3 * px) // 5 + 1 + (1 if "bold" in style else 0)
    w = cw * len(string)
    h = px + px // 4 + 2
    return [1, 2, 1 + w, 2 + h]


class OffscreenHiddenCanvas(OffscreenCanvas):
    """port: fonts.ss's *hidden-canvas* without Tk: bbox answers
    offscreen_metric for the last text item created."""

    def __init__(self):
        super().__init__(False)
        self.last_text = None

    def tcl(self, *args):
        if args and args[0] == "create":
            opts = dict(zip(args[4::2], args[5::2]))
            self.last_text = (str(opts["-text"]), opts["-font"])
            return chez.String("1")
        if args and args[0] == "bbox":
            return offscreen_metric(*self.last_text)
        return chez.String("")


def install_offscreen_fonts():
    """fonts.ss's create-mcat-logo, offscreen: a hidden canvas with the fixed
    metric, and the scrollbar sizes of a Tk 8.6 scrollbar on X11.  Then
    fonts.load() with a fixed family list, so that the faces do not depend on
    the machine."""
    from metacat.gui import fonts
    if not fonts.g_hidden_canvas:
        fonts.g_hidden_canvas = OffscreenHiddenCanvas()
    if not fonts.g_scrollbar_width:
        fonts.g_scrollbar_width = 15
        fonts.g_scrollbar_height = 15
    fonts.load(["times", "helvetica", "courier"])


class OffscreenHost:
    """port: SWL's <toplevel> and <frame>/<scrollframe> of make-graphics-window,
    offscreen (racket/gui/views.rkt's window-host%)."""

    def __init__(self, scrolling, destroy_action):
        self.scrolling = scrolling
        self.destroy_action = destroy_action
        self.title = ""
        self.geometry = "+0+0"
        self.canvas = None
        self.width = 0
        self.height = 0

    def make_canvas(self, visible_w, visible_h, bg_color):
        """the <viewport>'s canvas, visible_w x visible_h pixels"""
        self.width, self.height = visible_w, visible_h
        self.canvas = OffscreenCanvas(bg_color)
        return self.canvas

    def set_scroll_region_bang(self, x1, y1, x2, y2):
        return None

    def set_title_bang(self, title):
        self.title = title

    def get_title(self):
        return self.title

    def set_geometry_bang(self, g):
        self.geometry = g

    def get_geometry(self):
        i = self.geometry.find("+")
        return "%sx%s%s" % (self.get_width(), self.get_height(),
                            self.geometry[i:] if i >= 0 else "+0+0")

    def get_width(self):
        return 2 + self.width

    def get_height(self):
        return 2 + self.height

    def set_resizable_bang(self, w, h):
        return None

    def set_min_size_bang(self, w, h):
        return None

    def set_aspect_ratio_bounds_bang(self, a, b):
        return None

    def get_scrollbar(self, orientation):
        """the frame's scrollbar of this orientation, or False"""
        return False

    def set_vertical_view(self, fraction):
        """scroll the canvas so that this fraction of it is above the view"""
        return None

    def raise_(self):
        return None

    def lower(self):
        return None

    def destroy(self):
        return None


class TkHost(OffscreenHost):
    """port: a tkinter Toplevel and Canvas (scrollbars as the scrolling asks)."""

    def __init__(self, root, scrolling, destroy_action):
        super().__init__(scrolling, destroy_action)
        import tkinter
        self.root = root
        self.top = tkinter.Toplevel(root)
        self.top.title("")
        self.top.resizable(False, False)
        self.widget = None
        self.scrollbars = {}

    def make_canvas(self, visible_w, visible_h, bg_color):
        import tkinter
        from metacat.gui import swl
        self.width, self.height = visible_w, visible_h
        self.widget = tkinter.Canvas(self.top, width=visible_w, height=visible_h,
                                     highlightthickness=0, borderwidth=0)
        if self.scrolling in ("vertical", "both"):
            sb = tkinter.Scrollbar(self.top, orient="vertical", command=self.widget.yview)
            self.widget.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            self.scrollbars["vertical"] = sb
        if self.scrolling in ("horizontal", "both"):
            sb = tkinter.Scrollbar(self.top, orient="horizontal", command=self.widget.xview)
            self.widget.configure(xscrollcommand=sb.set)
            sb.pack(side="bottom", fill="x")
            self.scrollbars["horizontal"] = sb
        self.widget.pack(expand=True, fill="both")
        self.canvas = swl.TkCanvas(self.widget, background=bg_color)
        return self.canvas

    def set_scroll_region_bang(self, x1, y1, x2, y2):
        from metacat.gui import swl
        self.widget.configure(scrollregion=tuple(swl.tcl_word(v) for v in (x1, y1, x2, y2)))

    def set_title_bang(self, title):
        self.title = title
        self.top.title(str(title))

    def set_geometry_bang(self, g):
        self.geometry = g
        self.top.geometry(g)

    def get_width(self):
        return self.top.winfo_width()

    def get_height(self):
        return self.top.winfo_height()

    def set_resizable_bang(self, w, h):
        self.top.resizable(bool(w), bool(h))

    def set_min_size_bang(self, w, h):
        self.top.minsize(w, h)

    def get_scrollbar(self, orientation):
        return self.scrollbars.get(orientation, False)

    def set_vertical_view(self, fraction):
        self.widget.yview_moveto(fraction)

    def raise_(self):
        self.top.lift()

    def lower(self):
        self.top.lower()

    def destroy(self):
        self.top.destroy()


def tk_host_maker(root):
    """A window host maker for set_window_host_maker: Tk windows under root."""
    return lambda scrolling, destroy_action: TkHost(root, scrolling, destroy_action)


_maker = OffscreenHost


def set_window_host_maker(maker):
    """port: choose the hosts make-graphics-window gets (maker(scrolling,
    destroy_action)); OffscreenHost by default."""
    global _maker
    _maker = maker


def make_window_host(scrolling, destroy_action):
    """port: SWL's (create <toplevel> ...) and its frame, for make-graphics-window"""
    return _maker(scrolling, destroy_action)
