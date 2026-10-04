"""The main window: one QMainWindow for every panel of Metacat.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026).  Item 01 of loop0003: an empty window
titled Metacat.  The splitter tree of docs/qt-gui-plan.md (2.2) comes in item 04.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget

TITLE = "Metacat"
DEFAULT_SIZE = (1366, 768)      # the laptop screen of TASK.md; item 08 picks by screen


class MainWindow(QMainWindow):
    """port: Metacat's windows, in one"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setCentralWidget(QWidget(self))
        self.resize(*DEFAULT_SIZE)
