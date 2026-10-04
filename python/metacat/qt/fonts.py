"""Tk font words as QFonts, and the text metrics the Qt canvas lays out with.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026), for loop0003 item 02.

A Tk font word is (face size style...), as ``swl.tcl_word`` makes it from an SWL
font, or the same as a Tcl list string.  A negative size is in pixels; a
positive one in points at Tk's fixed 96 dpi (the GUIs fix Tk's scaling), so
pixel size round(size * 96 / 72), whatever the screen.  The styles are bold,
italic, underline and overstrike (normal and roman are the defaults).  The
canvas measures and draws with the same QFont.  Item 03 completes the mapping
(family lists, Tk's own metrics).
"""
from __future__ import annotations

import threading

from PySide6.QtGui import QFont, QFontMetrics

from metacat.qt.displaylist import split_list

DEFAULT_FONT = ("helvetica", -12)       # Tk's TkDefaultFont on X11, near enough

_fonts = {}
_lock = threading.Lock()


def font_words(font):
    words = split_list(font)
    if not words or words == ["TkDefaultFont"]:
        words = [str(w) for w in DEFAULT_FONT]
    return words


def qfont(font):
    """port: Tk_GetFont: the QFont of a Tk font word (cached)"""
    key = tuple(font_words(font))
    with _lock:
        f = _fonts.get(key)
        if f is None:
            f = QFont(key[0])
            size = int(float(key[1])) if len(key) > 1 else -12
            f.setPixelSize(-size if size < 0 else max(1, round(size * 96 / 72)))
            styles = set(key[2:])
            f.setBold("bold" in styles)
            f.setItalic("italic" in styles)
            f.setUnderline("underline" in styles)
            f.setStrikeOut("overstrike" in styles)
            f.setHintingPreference(QFont.PreferFullHinting)
            _fonts[key] = f
        return f


class QtMetrics:
    """The measurer of the display list: whole pixels, as Tk measures, from the
    QFont the canvas draws with (cached per font and string)."""

    def __init__(self):
        self._metrics = {}
        self._widths = {}

    def _fm(self, font):
        key = tuple(font_words(font))
        fm = self._metrics.get(key)
        if fm is None:
            fm = self._metrics[key] = QFontMetrics(qfont(font))
        return key, fm

    def text_width(self, font, line):
        key, fm = self._fm(font)
        w = self._widths.get((key, line))
        if w is None:
            w = self._widths[(key, line)] = fm.horizontalAdvance(line)
        return w

    def linespace(self, font):
        _, fm = self._fm(font)
        return fm.ascent() + fm.descent()

    def ascent(self, font):
        return self._fm(font)[1].ascent()


_metrics = None


def metrics():
    """the shared QtMetrics"""
    global _metrics
    if _metrics is None:
        _metrics = QtMetrics()
    return _metrics
