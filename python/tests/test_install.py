"""Packaging: a clean checkout, `pip install -e python` and the `metacat` command
(loop0002 item 16).

Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).

Fast tier: pyproject.toml declares the `metacat` and `metacat-gui` commands, ships
the gui subpackage and the help text, and the help text shipped is the original's.

Slow tier, each in a temporary directory, never in the checkout:
- a clean copy of python/ (git's files, without the fixtures and tests) runs
  `python3 -m metacat abc abd xyz --seed 3852097033 --max-codelets 10000
  --trace FILE` with no PYTHONPATH:
  the stdout is the live oracle's and the trace is the golden, byte for byte;
  `python3 -m metacat.gui` opens its windows under xvfb-run;
- a fresh venv with `pip install -e` of that copy: the `metacat` command, run from
  another directory, gives the same stdout and trace;
- a fresh venv with a regular install: the same, plus the gui subpackage and the
  help text are in site-packages and `metacat-gui` opens its windows.

The venvs see the system site-packages only for setuptools, so that pip builds
offline (--no-build-isolation --no-index); nothing else of the system is used.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PYTHON_DIR = Path(__file__).resolve().parent.parent
ROOT = PYTHON_DIR.parent
GOLDEN = ROOT / "tests" / "golden" / "abc-abd-xyz_3852097033.jsonl"
ARGS = ["abc", "abd", "xyz", "--seed", "3852097033", "--max-codelets", "10000"]  # the golden's


def pyproject():
    return tomllib.loads((PYTHON_DIR / "pyproject.toml").read_text())


def test_commands_declared():
    scripts = pyproject()["project"]["scripts"]
    assert scripts == {"metacat": "metacat.__main__:main",
                       "metacat-gui": "metacat.gui.app:main"}


def test_entry_points_take_no_arguments():
    """console scripts call main() with no arguments: both read sys.argv"""
    import inspect
    from metacat import __main__ as cli
    from metacat.gui import app
    for f in (cli.main, app.main):
        assert all(p.default is not inspect.Parameter.empty
                   for p in inspect.signature(f).parameters.values())


def test_packages_and_data_declared():
    data = pyproject()["tool"]["setuptools"]
    assert set(data["packages"]) == {"metacat", "metacat.gui"}
    assert "help.txt" in data["package-data"]["metacat.gui"]


def test_help_text_is_the_originals():
    from metacat.gui import gui
    assert gui.HELP_FILE.parent == PYTHON_DIR / "metacat" / "gui"
    assert gui.HELP_FILE.read_bytes() == \
        (ROOT / "chez_scheme" / "original" / "help.txt").read_bytes()


def test_no_package_file_reads_outside_the_package():
    """the package must run without the rest of the checkout"""
    for path in (PYTHON_DIR / "metacat").rglob("*.py"):
        text = path.read_text()
        assert "parents[" not in text, path
        assert '"chez_scheme"' not in text, path


# ------------------------------------------------------------------
# slow: a clean checkout and fresh venvs

def clean_env():
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def clean_copy(dest):
    """python/ as a clean checkout has it (tracked and untracked-but-not-ignored
    files), without fixtures/ and tests/, which the package doesn't need"""
    files = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z", "python"],
        cwd=ROOT, capture_output=True, check=True).stdout.decode().split("\0")
    for f in files:
        if not f or f.startswith(("python/fixtures/", "python/tests/")):
            continue
        src = ROOT / f
        if not src.is_file():
            continue
        target = dest / f
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest / "python"


@pytest.fixture(scope="module")
def oracle_stdout():
    scheme = shutil.which("scheme") or shutil.which("chezscheme")
    p = subprocess.run([scheme, "--script", "chez_scheme/oracle/run.ss", *ARGS], cwd=ROOT,
                       capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=600)
    assert p.returncode == 0, p.stderr
    return p.stdout


def check_run(cmd, cwd, tmp, oracle_stdout):
    trace = tmp / "trace.jsonl"
    p = subprocess.run([*cmd, *ARGS, "--trace", str(trace)], cwd=cwd, env=clean_env(),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=600)
    assert p.returncode == 0, p.stderr
    assert p.stdout == oracle_stdout
    assert trace.read_bytes() == GOLDEN.read_bytes()


def check_gui_opens(cmd, cwd):
    """the GUI prints its banner under xvfb-run, then is stopped (it would wait in
    Tk's main loop for ever)"""
    xvfb = shutil.which("xvfb-run")
    assert xvfb, "xvfb-run is needed"
    env = clean_env()
    env.pop("WAYLAND_DISPLAY", None)
    p = subprocess.Popen([xvfb, "-a", "-s", "-screen 0 1920x1200x24", *cmd], cwd=cwd,
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, text=True, start_new_session=True)
    try:
        lines = []
        for line in p.stdout:
            lines.append(line)
            if "Initializing windows...done" in line:
                break
        else:
            pytest.fail("no banner; stdout %r, stderr %r" % (lines, p.stderr.read()))
        assert p.poll() is None, "the GUI exited"
    finally:
        os.killpg(p.pid, 15)
        p.wait(timeout=30)


def venv_with(tmp, *pip_args):
    venv = tmp / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
                   check=True, env=clean_env())
    subprocess.run([str(venv / "bin" / "pip"), "install", "--no-build-isolation",
                    "--no-index", "--no-deps", "-q", *pip_args],
                   check=True, env=clean_env(), cwd=tmp, capture_output=True)
    return venv


def where_is_metacat(venv, cwd):
    return Path(subprocess.run(
        [str(venv / "bin" / "python"), "-c", "import metacat; print(metacat.__file__)"],
        cwd=cwd, env=clean_env(), capture_output=True, text=True, check=True)
        .stdout.strip()).resolve()


@pytest.mark.slow
def test_clean_checkout_cli(tmp_path, oracle_stdout):
    py = clean_copy(tmp_path / "checkout")
    assert not (tmp_path / "checkout" / "chez_scheme").exists()
    check_run(["python3", "-m", "metacat"], py, tmp_path, oracle_stdout)


@pytest.mark.slow
def test_clean_checkout_gui(tmp_path):
    py = clean_copy(tmp_path / "checkout")
    check_gui_opens(["python3", "-m", "metacat.gui"], py)


@pytest.mark.slow
def test_editable_install(tmp_path, oracle_stdout):
    py = clean_copy(tmp_path / "checkout")
    venv = venv_with(tmp_path, "-e", str(py))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert where_is_metacat(venv, elsewhere) == (py / "metacat" / "__init__.py").resolve()
    check_run([str(venv / "bin" / "metacat")], elsewhere, tmp_path, oracle_stdout)


@pytest.mark.slow
def test_regular_install(tmp_path, oracle_stdout):
    py = clean_copy(tmp_path / "checkout")
    venv = venv_with(tmp_path, str(py))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    pkg = where_is_metacat(venv, elsewhere).parent
    assert pkg.is_relative_to(venv)
    assert (pkg / "gui" / "app.py").is_file()
    assert (pkg / "gui" / "help.txt").read_bytes() == \
        (ROOT / "chez_scheme" / "original" / "help.txt").read_bytes()
    check_run([str(venv / "bin" / "metacat")], elsewhere, tmp_path, oracle_stdout)
    check_gui_opens([str(venv / "bin" / "metacat-gui")], elsewhere)
