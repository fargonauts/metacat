"""Golden runs in parallel (test helper; loop0002 items 10 and 11).

Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).

The run itself is the package's: metacat/headless.py (the oracle's prelude.ss
headless windows and run.ss driver) around metacat/run.py, with the trace written
by metacat/trace_writer.py.  This helper reads tests/problems.txt as
make-golden.ss does and runs problems in parallel.  A run changes the engine for
good (the Memory and the codelet count outlive it, anomalies: "The Memory outlives
a run"), and the oracle runs each golden in a fresh process; so each problem runs
in a fresh fork of a process where `headless.prepare()` has run (`run_in_forks`),
and that process is itself fresh (`run_in_fresh_process`).
"""
from __future__ import annotations

import io
import multiprocessing
import os
import re
import sys
from contextlib import redirect_stdout

from metacat import headless

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_DIR = os.path.join(ROOT, "tests", "golden")
PROBLEMS_FILE = os.path.join(ROOT, "tests", "problems.txt")


def prepare():
    headless.prepare()


def run_problem(strings, seed, cap, keep_going, trace=True):
    """The oracle run.ss's run: returns (reason, trace text, stdout).  An error of
    the run propagates, with the partial trace in its `partial_trace` attribute and
    the output in `stdout`."""
    port = io.StringIO() if trace else None
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            reason, _answers = headless.run_problem(strings, seed, cap, keep_going, port)
    except BaseException as e:
        e.partial_trace = port.getvalue() if port is not None else None
        e.stdout = out.getvalue()
        raise
    return reason, (port.getvalue() if port is not None else None), out.getvalue()


# ---------------------------------------------------------------------------
# tests/problems.txt (make-golden.ss's reading of it)

def golden_file_name(strings, seed):
    return "%s_%s.jsonl" % ("-".join(strings), seed)


def golden_runs(path=PROBLEMS_FILE):
    """Every golden run: (file name, strings, seed, cap, keep-going?)."""
    runs = []
    with open(path) as f:
        for line in f:
            line = re.sub(r"#.*$", "", line.rstrip("\n"))
            if not line.split():
                continue
            fields = [x.split() for x in line.split("|")]
            strings = fields[0]
            cap = int(fields[2][0])
            keep = len(fields) == 4 and fields[3] == ["keep-going"]
            for seed in fields[1]:
                runs.append((golden_file_name(strings, int(seed)), strings, int(seed), cap, keep))
    return runs


def golden_text(file_name):
    with open(os.path.join(GOLDEN_DIR, file_name)) as f:
        return f.read()


def _run_one(args):
    strings, seed, cap, keep = args
    try:
        reason, text, stdout = run_problem(strings, seed, cap, keep)
        return ("ok", reason, text, stdout)
    except BaseException as e:   # noqa: BLE001 - reported to the parent
        return ("error", "%s: %s" % (type(e).__name__, e),
                getattr(e, "partial_trace", None), getattr(e, "stdout", None))


def run_in_forks(jobs, processes=None):
    """Run each (strings, seed, cap, keep-going?) in a fresh fork of this process
    (after prepare()), in parallel; results in order."""
    prepare()
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(processes or min(32, os.cpu_count() or 1), maxtasksperchild=1) as pool:
        return pool.map(_run_one, jobs, chunksize=1)


def run_in_fresh_process(jobs, processes=None):
    """run_in_forks in a new Python process, so that neither the test session's
    engine (which other test files change and restore) nor the runs affect each
    other: each run starts from a freshly loaded engine, as each golden starts in a
    fresh Chez process."""
    import pickle
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    code = ("import sys, pickle; sys.path[:0] = %r; import golden_harness as g; "
            "jobs, n = pickle.load(sys.stdin.buffer); "
            "open(sys.argv[1], 'wb').write(pickle.dumps(g.run_in_forks(jobs, n)))"
            % ([here, os.path.dirname(here)],))
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        result = os.path.join(tmp, "results.pickle")
        proc = subprocess.run([sys.executable, "-c", code, result],
                              input=pickle.dumps((jobs, processes)),
                              capture_output=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError("golden runner failed:\n" + proc.stderr.decode())
        with open(result, "rb") as f:
            return pickle.load(f)


def first_difference(expected, actual):
    """The first differing line (1-based) of two traces, with both lines."""
    e, a = expected.splitlines(), actual.splitlines()
    for i, (x, y) in enumerate(zip(e, a)):
        if x != y:
            return i + 1, x, y
    if len(e) != len(a):
        i = min(len(e), len(a))
        return i + 1, e[i] if i < len(e) else None, a[i] if i < len(a) else None
    return None
