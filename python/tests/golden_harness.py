"""A full headless run, traced in the golden format (test helper, loop0002 item 10).

Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).

The counterpart of racket/headless.rkt (racket/tests/golden-harness.rkt in the
Racket port's item 10) and of the oracle's prelude.ss, trace.ss and run.ss:
- `install_headless_windows()`: prelude.ss's install-headless-windows!, with the
  Racket port's headless Commentary window (commentary-graphics.ss's
  make-comment-window logic without the text window);
- the JSON-lines writer and the trace wrappers of chez_scheme/oracle/trace.ss,
  installed by setting the engine's module attributes (the engine reads them at
  call time, as the original reads its top-level bindings);
- `run_problem(strings, seed, cap, keep_going)`: chez_scheme/oracle/run.ss's
  driver around golden_run.py (run.ss's run loop, registered as metacat.run).

A run changes the engine for good (the Memory and the codelet count outlive it,
anomalies: "The Memory outlives a run"), and the oracle runs each golden in a
fresh process; so run each problem in a fresh fork of a process where
`prepare()` has run (`run_in_fork`).  Item 11 moves the driver and the trace
writer into the package.
"""
from __future__ import annotations

import io
import multiprocessing
import os
import re
import sys
from contextlib import redirect_stdout
from fractions import Fraction

import metacat as _metacat
from metacat import chez, engine, objects, setup
from metacat.objects import Lambda, SchemeObject, tell

import golden_run

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_DIR = os.path.join(ROOT, "tests", "golden")
PROBLEMS_FILE = os.path.join(ROOT, "tests", "problems.txt")

NULL = object()            # the trace's 'null


class _Obj(list):
    """trace.ss: (json-object (key . value) ...), keys in the order given."""


# ---------------------------------------------------------------------------
# JSON output (trace.ss: json-string, json-number, json-write)

def _json_string(s, out):
    out.append('"')
    for c in s:
        if c == '"':
            out.append('\\"')
        elif c == "\\":
            out.append("\\\\")
        elif c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        elif c < " ":
            out.append("\\u%04X" % ord(c))
        else:
            out.append(c)
    out.append('"')


def _json_number(x, out):
    if isinstance(x, int):
        out.append(str(x))
    elif isinstance(x, Fraction):
        _json_string("%d/%d" % (x.numerator, x.denominator), out)
    elif isinstance(x, float) and x == x and x not in (float("inf"), float("-inf")):
        out.append(chez.number_to_string(x).split("|")[0])
    else:
        _json_string(chez.number_to_string(x), out)


def json_write(v, out):
    """trace.ss: json-write (out is a list of string pieces)"""
    if v is True:
        out.append("true")
    elif v is False:
        out.append("false")
    elif v is NULL:
        out.append("null")
    elif isinstance(v, str):
        _json_string(v, out)
    elif isinstance(v, (int, Fraction, float)):
        _json_number(v, out)
    elif isinstance(v, _Obj):
        out.append("{")
        for i, (k, val) in enumerate(v):
            if i:
                out.append(",")
            _json_string(k, out)
            out.append(":")
            json_write(val, out)
        out.append("}")
    elif isinstance(v, (list, tuple)):
        out.append("[")
        for i, x in enumerate(v):
            if i:
                out.append(",")
            json_write(x, out)
        out.append("]")
    else:
        raise chez.SchemeError("trace", "cannot write ~s as JSON", v)


TRACE: list | None = None          # the trace's pieces; None: no trace


def emit(ev, *fields):
    """trace.ss: emit"""
    if TRACE is not None:
        json_write(_Obj([("t", setup.g_codelet_count), ("ev", ev)] + list(fields)), TRACE)
        TRACE.append("\n")


# ---------------------------------------------------------------------------
# Names of model objects (trace.ss: $name, $string-of, $structure-fields)

def name(x):
    """trace.ss: $name"""
    if x is False:
        return NULL
    if isinstance(x, (str, int, Fraction, float)):
        return x
    if callable(x):
        t = tell(x, "object-type")
        if t == "slipnode":
            return tell(x, "get-short-name")
        if t in ("letter", "group"):
            n = tell(x, "ascii-name")
            return NULL if n is False else n
        if t == "workspace-string":
            return tell(x, "generic-name")
        if t == "concept-mapping":
            return tell(x, "print-name")
        return "<%s>" % chez.display_string(t)
    return chez.display_string(x)


def string_of(obj):
    """trace.ss: $string-of"""
    return tell(tell(obj, "get-string"), "generic-name")


def names(xs):
    # chez: map over pure getters; the order is not observable
    return [name(x) for x in xs]


def structure_fields(s):
    """trace.ss: $structure-fields"""
    t = tell(s, "object-type")
    if t == "bond":
        return [("string", string_of(s)),
                ("from", name(tell(s, "get-from-object"))),
                ("to", name(tell(s, "get-to-object"))),
                ("category", name(tell(s, "get-bond-category"))),
                ("direction", name(tell(s, "get-direction"))),
                ("facet", name(tell(s, "get-bond-facet")))]
    if t == "group":
        return [("string", string_of(s)),
                ("name", name(s)),
                ("category", name(tell(s, "get-group-category"))),
                ("direction", name(tell(s, "get-direction"))),
                ("facet", name(tell(s, "get-bond-facet"))),
                ("objects", names(tell(s, "get-constituent-objects")))]
    if t == "bridge":
        return [("type", tell(s, "get-bridge-type")),
                ("object1", name(tell(s, "get-object1"))),
                ("object2", name(tell(s, "get-object2"))),
                ("mappings", names(tell(s, "get-all-concept-mappings")))]
    if t == "description":
        obj = tell(s, "get-object")
        return [("string", string_of(obj)),
                ("object", name(obj)),
                ("type", name(tell(s, "get-description-type"))),
                ("descriptor", name(tell(s, "get-descriptor")))]
    if t == "rule":
        return [("type", tell(s, "get-rule-type")),
                ("english", list(tell(s, "get-english-transcription")))]
    return [("object", name(s))]


def emit_structure(ev, kind, s, *extra):
    """trace.ss: emit-structure"""
    emit(ev, ("kind", kind), *structure_fields(s), *extra)


# ---------------------------------------------------------------------------
# Headless windows (prelude.ss: install-headless-windows!)

def make_null_window(wname, messages):
    """prelude.ss: make-null-window"""
    def fn(self, msg, *args):
        if msg in messages:
            return "done"
        raise chez.SchemeError("headless-window", "~s received unexpected message ~s",
                               wname, msg)
    return Lambda(fn)


class HeadlessCommentWindow(SchemeObject):
    """commentary-graphics.ss: make-comment-window's closure, with its text window
    replaced by the oracle's recording text window (prelude.ss), as the Racket
    port's headless.rkt has it: each add-comment draws one paragraph, the eliza
    or the non-eliza one, and the trace records it."""

    def __init__(this):
        this.eliza_paragraphs = []
        this.non_eliza_paragraphs = []

    def otherwise(this, self, msg, args):
        if msg == "object-type":
            return "comment-window"
        if msg == "new-problem":
            initial_sym, modified_sym, target_sym, answer_sym = args
            f = chez.format_
            if setup.p_justify_mode is not False:
                lines1 = [f('Let\'s see... "~a" changes to "~a", and', initial_sym, modified_sym),
                          f(' "~a" changes to "~a".  Hmm...', target_sym, answer_sym)]
                lines2 = [f('Beginning justify run:  "~a" changes to "~a", and',
                            initial_sym, modified_sym),
                          f(' "~a" changes to "~a"...', target_sym, answer_sym)]
            else:
                lines1 = [f('Okay, if "~a" changes to "~a", what', initial_sym, modified_sym),
                          f(' does "~a" change to?  Hmm...', target_sym)]
                lines2 = [f('Beginning run:  If "~a" changes to "~a", what',
                            initial_sym, modified_sym),
                          f(' does "~a" change to?', target_sym)]
            tell(self, "add-comment", lines1, lines2)
            return "done"
        if msg == "add-comment":
            lines1, lines2 = args
            paragraph1 = "".join(lines1)
            paragraph2 = "".join(lines2)
            this.eliza_paragraphs = [1, paragraph1] + this.eliza_paragraphs
            this.non_eliza_paragraphs = [1, paragraph2] + this.non_eliza_paragraphs
            paragraph = paragraph1 if setup.p_eliza_mode is not False else paragraph2
            # the oracle's $commentary-hook, set by run.ss and wrapped by trace.ss
            emit("comment", ("text", paragraph))
            chez.printf("Comment: ~a~%", paragraph)
            return "done"
        if msg == "clear":
            this.eliza_paragraphs = []
            this.non_eliza_paragraphs = []
            return "done"
        if msg == "initialize":
            tell(self, "clear")
            return "done"
        raise chez.SchemeError("headless-window",
                               "comment window received unexpected message ~s", msg)


VERBOSE = False


def _memory_window_fn(self, msg, *args):
    # add-memory-icon gives each answer or snag description its icon drawing
    # procedures (memory-graphics.ss), which memory.ss calls even when nothing
    # is displayed; here they draw nothing.
    if msg == "add-memory-icon":
        tell(args[0], "set-graphics-info", lambda activation: "no-icon", "no-icon")
        return "done"
    if msg == "draw":
        return "done"
    raise chez.SchemeError("headless-window", "~s received unexpected message ~s",
                           "memory", msg)


def _control_panel_fn(self, msg, *args):
    if msg == "set-verbose-step-mode":
        # as in gui.ss, with the verbose checkbox off unless --verbose
        setup.p_verbose = args[0] if args[0] is not False else VERBOSE
        return "done"
    raise chez.SchemeError("headless-window",
                           "control panel received unexpected message ~s", msg)


def install_headless_windows():
    """prelude.ss: install-headless-windows!"""
    s = engine.set_global
    s("%workspace-graphics%", False)
    s("%slipnet-graphics%", False)
    s("%coderack-graphics%", False)
    s("*workspace-window*", make_null_window("workspace", ("garbage-collect", "caching-on",
                                                           "flush")))
    s("*slipnet-window*", make_null_window("slipnet", ("clear",)))
    s("*coderack-window*", make_null_window("coderack", ("clear",)))
    s("*themespace-window*", make_null_window(
        "themespace", ("erase-all-themes", "update-thematic-pressure", "update-graphics",
                       "set-theme-graphics-parameters-and-draw", "garbage-collect")))
    s("*top-themes-window*", make_null_window("top-themes", ()))
    s("*bottom-themes-window*", make_null_window("bottom-themes", ()))
    s("*vertical-themes-window*", make_null_window("vertical-themes", ()))
    s("*memory-window*", Lambda(_memory_window_fn))
    s("*trace-window*", make_null_window("trace", ("initialize", "add-event")))
    s("*temperature-window*", make_null_window("temperature", ("initialize",
                                                               "update-graphics")))
    s("*EEG-window*", make_null_window("EEG", ("initialize",)))
    # Each codelet type keeps its own reference to the Coderack window, set by the
    # window (coderack-graphics.ss); a codelet's 'run tells it
    # 'set-last-codelet-type whatever the graphics switches say.
    coderack_graphics = make_null_window("coderack-graphics", ("set-last-codelet-type",))
    for t in _metacat.coderack.g_codelet_types:
        tell(t, "set-graphics-parameters", coderack_graphics,
             False, False, False, False, False, False, False, False)
    s("*control-panel*", Lambda(_control_panel_fn))
    s("*comment-window*", HeadlessCommentWindow())


# ---------------------------------------------------------------------------
# The trace wrappers (trace.ss: install-trace!) and the driver (run.ss)

class StopRun(Exception):
    """run.ss's stop-run continuation, called with the reason."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class _Wrapped(SchemeObject):
    """trace.ss's (lambda msg ... (apply original original (cdr msg))): self inside
    stays the original object."""

    def __init__(this, original, before=None, after=None):
        this.original = original
        this.before = before
        this.after = after

    def otherwise(this, self, msg, args):
        if this.before:
            this.before(msg, args)
        result = this.original(this.original, msg, *args)
        if this.after:
            this.after(msg, result)
        return result


ANSWERS: list = []
LAST_THEMES = [None]
KEEP_GOING = [False]


def _codelet_chosen(msg, result):
    if msg == "choose-codelet":
        emit("codelet",
             ("type", tell(result, "get-codelet-type-name")),
             ("urgency", tell(result, "get-relative-urgency")),
             ("posted", tell(result, "get-time-stamp")),
             ("rng", chez.random_seed()))


def _rule_added(msg, args):
    if msg == "add-rule":
        emit_structure("build", "rule", args[0])


def install_trace():
    """chez_scheme/oracle/trace.ss's install-trace! and run.ss's own wrappers."""
    m = _metacat
    m.coderack.g_coderack = _Wrapped(m.coderack.g_coderack, after=_codelet_chosen)

    o_build_bond, o_break_bond = m.bonds.build_bond, m.bonds.break_bond
    o_build_group, o_break_group = m.groups.build_group, m.groups.break_group
    o_build_bridge, o_break_bridge = m.bridges.build_bridge, m.bridges.break_bridge
    o_build_description = m.descriptions.build_description

    def build_bond(bond):
        emit_structure("build", "bond", bond)
        return o_build_bond(bond)

    def break_bond(bond):
        emit_structure("break", "bond", bond)
        return o_break_bond(bond)

    def build_group(group, flipped_p):
        emit_structure("build", "group", group, ("flipped", flipped_p))
        return o_build_group(group, flipped_p)

    def break_group(group):
        emit_structure("break", "group", group)
        return o_break_group(group)

    def build_bridge(orientation, bridge):
        emit_structure("build", "bridge", bridge)
        return o_build_bridge(orientation, bridge)

    def break_bridge(bridge):
        emit_structure("break", "bridge", bridge)
        return o_break_bridge(bridge)

    def build_description(d):
        emit_structure("build", "description", d)
        return o_build_description(d)

    m.bonds.build_bond, m.bonds.break_bond = build_bond, break_bond
    m.groups.build_group, m.groups.break_group = build_group, break_group
    m.bridges.build_bridge, m.bridges.break_bridge = build_bridge, break_bridge
    m.descriptions.build_description = build_description
    m.workspace.g_workspace = _Wrapped(m.workspace.g_workspace, before=_rule_added)

    o_update_temperature = m.formulas.update_temperature

    def update_temperature():
        o_update_temperature()
        emit("temperature", ("value", setup.g_temperature),
             ("clamped", m.run.g_temperature_clamped_p))

    m.formulas.update_temperature = update_temperature

    o_update_slipnet_activations = m.slipnet.update_slipnet_activations

    def update_slipnet_activations():
        o_update_slipnet_activations()
        emit("slipnet",
             ("activations", [tell(n, "get-activation") for n in m.slipnet.g_slipnet_nodes]),
             ("rng", chez.random_seed()))
        state = tell(m.themes.g_themespace, "get-complete-state")
        fields = [("active", list(state[1])),
                  ("themes", [[info[0], name(info[1]), name(info[2]), info[3], info[4]]
                              for info in state[2]])]
        if fields != LAST_THEMES[0]:
            LAST_THEMES[0] = fields
            emit("themes", *fields)

    m.slipnet.update_slipnet_activations = update_slipnet_activations

    window = setup.g_trace_window

    def trace_window_fn(self, msg, *args):
        if msg == "add-event":
            event = args[0]
            emit("event",
                 ("type", tell(event, "get-type")),
                 ("number", tell(event, "get-event-number")),
                 ("name", tell(event, "print-name")),
                 ("time", tell(event, "get-time")),
                 ("temperature", tell(event, "get-temperature")))
        return window(self, msg, *args)

    setup.g_trace_window = Lambda(trace_window_fn)

    o_abstract_answer_description = m.memory.abstract_answer_description

    def abstract_answer_description(answer_event):
        answer = tell(tell(answer_event, "get-answer-string"), "print-name")
        quality = tell(answer_event, "get-quality")
        emit("answer", ("answer", answer), ("quality", quality),
             ("temperature", setup.g_temperature))
        ANSWERS.append(answer)
        chez.printf("Answer: ~a  quality ~a  codelet ~a  temperature ~a~%",
                    answer, quality, setup.g_codelet_count, setup.g_temperature)
        return o_abstract_answer_description(answer_event)

    m.memory.abstract_answer_description = abstract_answer_description

    def report_error_and_halt(message, obj):
        emit("halt", ("message", message[1]), ("object", tell(obj, "object-type")))
        chez.printf('Ooops: bad message "~a" sent to object of type ~a~%',
                    message[1], tell(obj, "object-type"))
        raise StopRun("halt")

    objects.report_error_and_halt = report_error_and_halt


def headless_break():
    """chez_scheme/oracle/run.ss: headless-break"""
    run = golden_run
    run.g_running_p = False
    at_cap = run.g_break_time is not False and run.g_break_time == setup.g_codelet_count
    if KEEP_GOING[0] and not at_cap:
        run.g_running_p = True
        return "ignore"
    raise StopRun("cap" if at_cap else "suspend")


_prepared = False


def prepare():
    """Load the engine, register golden_run as metacat.run, install the headless
    windows and the trace wrappers.  Once per process (fork after it)."""
    global _prepared
    if _prepared:
        return
    _prepared = True
    sys.modules["metacat.run"] = golden_run
    _metacat.run = golden_run
    engine.load()
    install_headless_windows()
    # eeg-graphics.ss's *EEG*: workspace.ss's initialize tells it 'initialize; the
    # rest is gated by %workspace-graphics%
    if "metacat.eeg_graphics" not in sys.modules:
        import types
        eeg = types.ModuleType("metacat.eeg_graphics")
        eeg.g_EEG = make_null_window("EEG", ("initialize",))
        sys.modules["metacat.eeg_graphics"] = eeg
        _metacat.eeg_graphics = eeg
    install_trace()
    golden_run.break_ = headless_break
    golden_run.quiet_break = headless_break


def run_problem(strings, seed, cap, keep_going, trace=True):
    """chez_scheme/oracle/run.ss's driver: returns (reason, trace text, stdout).
    An error of the run propagates, with the partial trace in its
    `partial_trace` attribute."""
    global TRACE
    prepare()
    TRACE = [] if trace else None
    ANSWERS.clear()
    LAST_THEMES[0] = None
    KEEP_GOING[0] = keep_going
    out = io.StringIO()
    with redirect_stdout(out):
        emit("start", ("format", 1),
             ("problem", list(strings) + ([NULL] if len(strings) == 3 else [])),
             ("seed", seed), ("max_codelets", NULL if cap is False else cap),
             ("keep_going", keep_going),
             ("slipnodes", names(_metacat.slipnet.g_slipnet_nodes)))
        initial, modified, target = strings[:3]
        answer = strings[3] if len(strings) == 4 else False
        setup.p_justify_mode = answer is not False
        chez.printf("Problem: ~a -> ~a; ~a -> ~a  seed ~a~%",
                    initial, modified, target, "?" if answer is False else answer, seed)
        try:
            golden_run.init_mcat(initial, modified, target, answer, seed)
            golden_run.g_break_time = cap
            golden_run.run_mcat()
        except StopRun as stop:
            reason = stop.reason
        except BaseException as e:
            e.partial_trace = "".join(TRACE) if TRACE is not None else None
            e.stdout = out.getvalue()
            raise
        emit("end", ("reason", reason), ("temperature", setup.g_temperature),
             ("answers", list(ANSWERS)), ("rng", chez.random_seed()))
        chez.printf("Stopped: ~a~%", reason)
        chez.printf("Codelets: ~a~%", setup.g_codelet_count)
        chez.printf("Temperature: ~a~%", setup.g_temperature)
        chez.printf("Answers: ~a~%", "none" if not ANSWERS else list(ANSWERS))
    text = "".join(TRACE) if TRACE is not None else None
    TRACE = None
    return reason, text, out.getvalue()


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
