"""The Qt GUI program: the QApplication and the main window.  `python3 -m
metacat.qt` runs `main`.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026).  Item 01 of loop0003 made the window;
item 04 put the panels in it (`setup`, setup.ss's window part on Qt hosts);
item 05 the engine thread and the run controls (the control strip); item 06
the menus and dialogs (docs/qt-gui-plan.md).
"""
from __future__ import annotations

import argparse
import sys


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="python3 -m metacat.qt",
                                     description="Metacat in one window (Qt).")
    parser.add_argument("--quit-after", type=int, metavar="MS", default=None,
                        help="close the window and quit after MS milliseconds")
    parser.add_argument("--screenshot", metavar="PNG", default=None,
                        help="with --quit-after: grab the window into PNG before quitting")
    return parser.parse_args(argv)


def setup(window):
    """setup.ss: setup, on Qt hosts in window's panes (GUI thread): the Qt
    fonts and hosts, the engine and the graphics files loaded, every window
    made as views.attach_views makes them and placed in its pane, the control
    panel (metacat/qt/controls.py) in the window's control strip, the engine
    thread (metacat/qt/engine_bridge.py), then enable-resizing (each panel
    redraws at its pane's size).  Returns the windows by name."""
    from metacat import engine
    from metacat import setup as S
    from metacat.gui import app as gui_app
    from metacat.gui import views
    from metacat.qt import controls, hosts
    from metacat.qt.engine_bridge import EngineBridge
    hosts.install()
    engine.load()
    views.load_views()
    windows = views.attach_views()
    window.place_windows(windows)
    bridge = EngineBridge()
    S.g_control_panel = controls.make_control_panel(bridge.invoker)
    window.place_control_panel(S.g_control_panel, bridge)
    gui_app.enable_resizing()
    return windows


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
    setup(window)
    window.show()
    print(window.windowTitle(), flush=True)
    print("Panes: " + " ".join(name for name, pane in window.panes.items()
                               if pane.isVisibleTo(window)), flush=True)
    if args.quit_after is not None:
        def finish():
            # one callback, so that the grab always comes before the close
            if args.screenshot:
                from metacat.qt.grab import grab_png
                window.sync()
                grab_png(window, args.screenshot)
            window.close()
            app.quit()
        QTimer.singleShot(args.quit_after, finish)
    status = app.exec()
    if window.bridge is not None and window.bridge.busy():
        # port: the engine thread is a daemon in the middle of a run; leave
        # without waiting for it (closing the original's control panel exited)
        import os
        sys.stdout.flush()
        os._exit(status)
    return status
