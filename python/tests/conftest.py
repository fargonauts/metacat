# Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).
# Makes python/oracle/ (capture.py) and python/tests/ (helpers) importable.
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for path in (HERE, HERE.parent / "oracle"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


# --- Qt (loop0003): a headless QApplication and a screenshot helper ----------
# PySide6 is optional: these fixtures import it only when a test asks for them,
# and every test_qt_*.py starts with pytest.importorskip("PySide6...").

import pytest  # noqa: E402

SCREENSHOTS = HERE / "screenshots-qt"     # grab()'s pictures (not committed)


def pytest_collection_modifyitems(session, config, items):
    """the test_qt_*.py files run last: the QApplication starts a thread, and
    forking a multi-threaded process (golden_harness, the extra seeds) may
    deadlock (Python warns: "use of fork() may lead to deadlocks")"""
    items.sort(key=lambda item: item.path.name.startswith("test_qt_"))


@pytest.fixture(scope="session")
def qapp():
    """The QApplication of the session, offscreen: never a window on the real
    screen.  At the end, every window is closed and the application quits."""
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.pop("WAYLAND_DISPLAY", None)
    pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(["metacat-tests"])
    yield app
    app.closeAllWindows()
    app.processEvents()
    app.quit()


@pytest.fixture
def grab(qapp, request):
    """grab(widget, name) -> the path of a PNG of the widget, in
    tests/screenshots-qt/<test name>/<name>.png, for inspection."""
    from metacat.qt.grab import grab_png

    def take(widget, name):
        qapp.processEvents()
        return grab_png(widget, SCREENSHOTS / request.node.name / (name + ".png"))
    return take
