"""The main window: one QMainWindow for every panel of Metacat.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026).  Item 01 of loop0003 made the window;
item 04 the splitter tree of docs/qt-gui-plan.md 2.2, which holds the panes of
the Qt hosts (metacat/qt/hosts.py):

    rows (vertical)       60% / 31% / 9% of the height
    ├── top               Temperature | Workspace | Coderack | Vertical Themes | Commentary
    ├── middle            Slipnet | themes (vertical: Top / Bottom Themes) | Episodic Memory
    └── bottom (vertical) Temporal Trace | EEG (hidden)

Fixed splitters, not docks (the owner's decision): the panes stay where they
are; the handles resize them.  Until the user drags a handle, the default sizes
follow the window's size (`default_sizes`).  A 50 ms timer brings every pane's
scene up to date with its canvas (`sync`).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QSplitter, QToolBar

TITLE = "Metacat"
DEFAULT_SIZE = (1920, 1010)     # a maximised window on a 1920x1080 screen (the minimum)
HANDLE = 4                      # the splitter handles' width
SYNC_INTERVAL = 50              # ms between scene updates (racket/gui's refresh)

# Tk's aspect ratios of the unscrollable windows: (w+2):(h+2) of their default
# canvas sizes, as make-resizable sets them (docs/qt-gui-plan.md 1.1)
ASPECT = {"workspace": (802, 602), "coderack": (232, 600), "vertical-themes": (162, 592),
          "temperature": (72, 177), "slipnet": (652, 311), "themes": (602, 142)}

# the panes, in the Windows menu's order (docs/qt-gui-plan.md 2.3)
PANES = ["workspace", "slipnet", "coderack", "temperature", "trace", "commentary", "memory",
         "top-themes", "bottom-themes", "vertical-themes", "EEG"]

# the panes of each splitter, in order (a name that is not a pane is a splitter)
TREE = {
    "rows": ["top", "middle", "bottom"],
    "top": ["temperature", "workspace", "coderack", "vertical-themes", "commentary"],
    "middle": ["slipnet", "themes", "memory"],
    "themes": ["top-themes", "bottom-themes"],
    "bottom": ["trace", "EEG"],
}
VERTICAL = ("rows", "themes", "bottom")
STRETCHY = ("commentary", "memory", "trace")     # they take the extra space
HIDDEN_AT_START = ("EEG",)
MIN_REST = 200                  # the Commentary's and the Memory's default minimum


def _shrink(fixed, room):
    """fixed widths scaled down to add up to room (the first one takes the
    rounding)"""
    total = sum(fixed)
    scaled = [w * room // total for w in fixed]
    scaled[1 if len(scaled) > 1 else 0] += room - sum(scaled)
    return scaled


def _row(fixed, width):
    """a row of fixed-aspect widths and one rest pane, in width pixels"""
    if width - sum(fixed) < MIN_REST:
        fixed = _shrink(fixed, max(0, width - MIN_REST))
    return fixed + [width - sum(fixed)]


def default_sizes(width, height, handle=HANDLE):
    """docs/qt-gui-plan.md 2.2: each splitter's sizes for a central area of
    width x height pixels"""
    def ratio(name, h):
        a, b = ASPECT[name]
        return round(h * a / b)
    avail = height - 2 * handle
    bottom = max(50, round(0.09 * avail))
    top = round(0.60 * avail)
    middle = avail - top - bottom
    temperature = max(60, round(0.06 * width))
    top_row = _row([temperature, ratio("workspace", top), ratio("coderack", top),
                    ratio("vertical-themes", top)], width - 4 * handle)
    theme_h = (middle - handle) // 2
    middle_row = _row([ratio("slipnet", middle), ratio("themes", (middle - handle) / 2)],
                      width - 2 * handle)
    return {"rows": [top, middle, bottom],
            "top": top_row,
            "middle": middle_row,
            "themes": [theme_h, middle - handle - theme_h],
            "bottom": [bottom, bottom]}


class MainWindow(QMainWindow):
    """port: Metacat's windows, in one"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.splitters = {}
        for name in TREE:
            sp = QSplitter(Qt.Vertical if name in VERTICAL else Qt.Horizontal)
            sp.setObjectName(name)
            sp.setHandleWidth(HANDLE)
            sp.setChildrenCollapsible(False)
            sp.splitterMoved.connect(self._handle_dragged)
            self.splitters[name] = sp
        for name in ("top", "middle", "bottom"):
            self.splitters["rows"].addWidget(self.splitters[name])
        self.setCentralWidget(self.splitters["rows"])
        self.panes = {}
        self.hosts = {}
        self.control_panel = None
        self.bridge = None
        self.default_layout = True    # until the user drags a handle
        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(SYNC_INTERVAL)
        self.sync_timer.timeout.connect(self.sync)
        self.sync_timer.start()
        self.resize(*DEFAULT_SIZE)

    def place_windows(self, windows):
        """the graphics windows (views.attach_views's dict, by name) as panes"""
        from metacat.objects import tell
        self.place_hosts({name: tell(w, "get-toplevel") for name, w in windows.items()})

    def place_hosts(self, hosts):
        """the Qt hosts (by window name) in the splitter tree"""
        self.hosts = {name: hosts[name] for name in PANES}
        self.panes = {name: host.pane for name, host in self.hosts.items()}
        for parent, children in TREE.items():
            if parent == "rows":
                continue
            sp = self.splitters[parent]
            for child in children:
                widget = self.splitters.get(child) or self.panes[child]
                sp.addWidget(widget)
                sp.setStretchFactor(sp.indexOf(widget), 1 if child in STRETCHY else 0)
        self.splitters["middle"].setStretchFactor(1, 0)
        for name, pane in self.panes.items():
            pane.setMinimumSize(120 if name in ("commentary", "memory") else 40, 40)
        self.panes["temperature"].v_align = "top"
        for name in HIDDEN_AT_START:
            self.hosts[name].hide_window()
            self.panes[name].hide()
        for name, pane in self.panes.items():
            if name not in HIDDEN_AT_START:
                pane.show()
        self.apply_default_layout()

    def place_control_panel(self, control_panel, bridge):
        """the control panel's strip above the panes (a fixed tool bar, so the
        central widget stays the splitter tree), its menus in the menu bar;
        when the engine parks, every pane is brought up to date at once"""
        from metacat.objects import tell
        self.control_panel, self.bridge = control_panel, bridge
        widgets = tell(control_panel, "get-widgets")
        bar = QToolBar("Control panel")
        bar.setObjectName("control-strip-bar")
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.toggleViewAction().setEnabled(False)
        bar.addWidget(widgets["frame"])
        self.addToolBar(Qt.TopToolBarArea, bar)
        self.menuBar().addMenu(widgets["options-menu"])
        control_panel.parked_hook = self.sync

    def apply_default_layout(self):
        c = self.centralWidget()
        sizes = default_sizes(c.width(), c.height(), HANDLE)
        for name, s in sizes.items():
            self.splitters[name].setSizes(s)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.default_layout and self.panes:
            self.apply_default_layout()

    def _handle_dragged(self, pos, index):
        self.default_layout = False

    def splitter_sizes(self):
        return {name: sp.sizes() for name, sp in self.splitters.items()}

    def sync(self):
        """every pane's scene and view up to date with its canvas (GUI thread),
        the canvas commands held at the paint gate meanwhile"""
        from metacat.qt.canvas import PAINT_GATE
        with PAINT_GATE:
            for host in self.hosts.values():
                host.sync()
