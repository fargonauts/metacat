"""The Qt GUI program: the QApplication and the main window.  `python3 -m
metacat.qt` runs `main`.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026).  Item 01 of loop0003: the window is empty;
the panels, the control strip and the menus come in items 04-06
(docs/qt-gui-plan.md).
"""
from __future__ import annotations

import argparse
import sys


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="python3 -m metacat.qt",
                                     description="Metacat in one window (Qt).")
    parser.add_argument("--quit-after", type=int, metavar="MS", default=None,
                        help="close the window and quit after MS milliseconds")
    return parser.parse_args(argv)


def main(argv=None):
    """port: the program.  Prints the window's title once it is shown."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    from metacat import qt
    if not qt.has_pyside6():
        print("The Qt GUI needs PySide6: pip install -e 'python[qt]'", file=sys.stderr)
        return 1
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from metacat.qt.mainwindow import MainWindow
    app = QApplication.instance() or QApplication(["metacat"])
    window = MainWindow()
    window.show()
    print(window.windowTitle(), flush=True)
    if args.quit_after is not None:
        QTimer.singleShot(args.quit_after, window.close)
        QTimer.singleShot(args.quit_after, app.quit)
    return app.exec()
