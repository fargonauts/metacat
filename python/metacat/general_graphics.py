"""general-graphics.ss: the drawing helpers shared by the panels (the engine's part).

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Metacat is based on Copycat, which was originally written in Common Lisp
by Melanie Mitchell.  Translated to Python (2026) from general-graphics.ss, with
racket/engine/general-graphics.rktl as a worked translation.

Only find-next-space-position is translated here, because the model calls it:
rules.ss's transcribe-to-english breaks every rule's English into lines with it,
and the English is in the golden traces (the Racket port's item 10 made the same
early copy).  The rest of general-graphics.ss (boxes, arrowheads, windows) is
translated in the panels item; coderack.py and groups.py read those names
through the package only with the graphics switches on.  Never imports tkinter.
"""
from __future__ import annotations


def find_next_space_position(s, i):
    """general-graphics.ss: find-next-space-position"""
    # Scheme's tail recursion as a loop
    while True:
        if i >= len(s):
            return len(s)
        if s[i] == " ":
            return i
        i += 1
