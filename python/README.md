# Metacat 1.2 in Python

A test-driven translation of James B. Marshall's Metacat 1.2 (Chez Scheme) to Python,
standard library only, with a tkinter GUI. GPL v2 or later, like Metacat itself. The
goal and rules are in `ralph_loops/loop0002/TASK.md`; the work items are in
`ralph_loops/loop0002/iterations.md`.

## Tests

```bash
bash python/run-tests.sh          # full tier (what the gate runs): every test
bash python/run-tests.sh --fast   # fast tier: skips tests marked @pytest.mark.slow
```

Tests marked `slow` need Chez Scheme or take long (fixture re-capture, golden runs).

## Chez fixtures

Every expected value comes from Chez. `tests/diff/*-battery.scm` are the differential
batteries written for the Racket port; `oracle/capture.py` runs each one under Chez
Scheme 10 with the whole original loaded (`chez_scheme/oracle/diff-eval.ss`) and writes
its output, split per test, to `fixtures/<battery>/`. Vectors those frozen batteries lack
come from the port's own batteries in `oracle/batteries/` (`chez-battery.scm`: the
generator state after every draw, exactness, libm bits, the printer, `sort` and `map`
orders), captured the same way:

```bash
python3 python/oracle/capture.py --all        # every battery, in parallel (about a minute)
python3 python/oracle/capture.py utilities    # one battery
python3 python/oracle/capture.py chez         # python/oracle/batteries/chez-battery.scm
```

- `MANIFEST`: the test names in order (from Chez's reader, `oracle/list-tests.ss`);
- `NNN-NAME.txt`: what Chez printed after `NAME => ` for test number NNN (other
  characters in NAME are written `%XX`);
- `SOURCES`: the Chez version and sha256 of every input to the capture.

In a test, `from chez_fixtures import chez` and then `chez("utilities", "prob?")`.
Never edit fixtures by hand, and never re-capture them to make a broken port pass.
`tests/test_fixtures.py` checks them: one fixture per test, the split/join round trip,
unchanged `SOURCES` (fast), and a byte-identical re-capture (slow).

## Modules

- `metacat/chez.py`: the Chez Scheme 10 built-ins the original relies on: the global
  `random`/`random-seed`, exact arithmetic (`add`, `mul`, `div`, `max_`, `expt`, ...),
  rounding, `map_` (Chez's order), `for_each`, `sort` (Chez's merge sort), `remq` and
  friends, `eq_p`/`eqv_p`/`equal_p`, the top-level value table, and the printer
  (`number_to_string`, `display`, `write`, `format_`, `printf`), `make_rectangular`
  (with `ExactComplex`). Tests: `tests/test_chez.py`.
- `metacat/objects.py`: Metacat's objects (record-case closures as `SchemeObject`
  subclasses with `@message` methods), `tell`, `delegate`, `delegate_to_all`,
  `tell_all`, `base_object`, `Lambda`, `Forwarder`, `INVALID`, `Reset`.
- `metacat/sugar.py`: syntactic-sugar.ss, every extend-syntax form as a function.
- `metacat/utilities.py`: utilities.ss, function for function.
- `metacat/names.py`: the Scheme → Python name mapping.

  Tests: `tests/test_utilities.py`, every test of `tests/diff/utilities-battery.scm` plus
  `oracle/batteries/utilities-extra-battery.scm` (ties, `select-extreme` ties, a few
  mixed-exactness cases).
- `metacat/engine.py`: metacat.ss's load order. `engine.load()` calls each translated
  module's `load()` once (the top-level defines that need other engine modules);
  `engine.set_global("*temperature*", 50)` sets a global by its Scheme name.
- `metacat/constants.py`: constants.ss's model part (the threshold distributions).
- `metacat/view_globals.py`: the colours, fonts and speed settings the model reads,
  `#f` until the views set them (racket/engine/view-globals.rktl).
- `metacat/setup.py`: setup.ss's globals and user commands.
- `metacat/coderack.py`: coderack.ss (codelet types, codelets, bins, the coderack,
  bottom-up and top-down posting); `load()` makes the codelet types and `*coderack*`.
- `metacat/descriptions.py`: descriptions.ss; `load()` gives the four description
  codelet types their procedures.

  Tests: `tests/test_coderack.py`, every test of `tests/diff/coderack-battery.scm` plus
  `oracle/batteries/coderack-extra-battery.scm` (urgency clipping with flonums, clamp
  exactness). Globals of modules not translated yet are stand-ins
  (`tests/engine_stubs.py`).
- `metacat/slipnet.py`: slipnet.ss (slipnodes, links, activation spreading and decay,
  `update-slipnet-activations`); `load()` builds the 59 nodes, their codelet types,
  descriptor predicates and the 202 links.
- `metacat/images.py`: images.ss (letter, group and string images for rule application).

  Tests: `tests/test_slipnet.py`, every test of `tests/diff/slipnet-battery.scm` (the
  initial slipnet, 20 updates from fixed states to the last bit, images) plus
  `oracle/batteries/slipnet-extra-battery.scm` (`replace-all` stopped midway, `extend`'s
  length-first order, `number->platonic-number` bounds).
- `metacat/workspace.py`: workspace.ss (the Workspace: strings, bridge tables, rules,
  averages and mapping strengths, `unrelated?`/`ungrouped?`/`unmapped?`); `load()` makes
  `*workspace*`.
- `metacat/workspace_objects.py`: workspace-objects.ss (letters and the workspace-object
  closure that letters and groups delegate to).
- `metacat/workspace_strings.py`: workspace-strings.ss (strings, their bond and group
  tables, storage expansion, relevance, reference objects).
- `metacat/workspace_structures.py`: workspace-structures.ss (structure strength,
  `wins-fight?`).
- `metacat/workspace_structure_formulas.py` and `metacat/formulas.py`: the group
  probabilities and supports; temperature-adjusted probabilities and values, the
  translation threshold distribution, `update-temperature`.

  Tests: `tests/test_workspace.py`, every test of `tests/diff/workspace-battery.scm`
  (with `tests/diff/workspace-dump.scm`: the initial workspace of every problem of
  `tests/problems.txt` for each seed, live queries, fakes for bonds, groups, bridges and
  rules) plus `oracle/batteries/workspace-extra-battery.scm` (a group's vertical bridge,
  relevant descriptions, neighbours among groups, relevance with bonds, the bond-density
  and activity boundaries).
- `metacat/bonds.py`: bonds.ss (bonds, the bond scouts, evaluator and builder,
  `build-bond`/`break-bond`, the bond predicates).
- `metacat/groups.py`: groups.ss (groups, which delegate to a workspace object and a
  workspace structure; the group scouts, evaluator and builder, `propose-group`,
  `build-group`/`break-group`, `contains?`).
- `metacat/concept_mappings.py`: concept-mappings.ss (concept mappings, `CMs-equal?`,
  `remove-duplicate-CMs`).
- `metacat/group_graphics.py`: only `group-graphics` from group-graphics.ss, which
  group-builder calls even with graphics off; the rest comes with the panels.

  Tests: `tests/test_codelets.py`, every test of `tests/diff/codelet-battery.scm` through
  `tests/codelet_harness.py` (the Python `tests/diff/codelet-harness.scm`): 400-codelet
  traces of every problem and seed of `tests/problems.txt`, seven 2000-codelet runs, and
  the concept mappings of every slipnet category and of real descriptions. The full
  battery runs in a fork pool and is in the slow tier; the fast tier runs the first seed
  of problem 0. `oracle/batteries/codelet-extra-battery.scm` adds local densities and
  supports (rounded, not floored) and group-builder flipping several bonds in map's order.
- `metacat/bridges.py`: bridges.ss (horizontal and vertical bridges, which share their
  common clauses in a private base class; the bridge scouts, evaluator and builder,
  `propose-bridge`, `build-bridge`/`break-bridge`, the incompatibility and support
  predicates).
- `metacat/breakers.py`: breakers.ss (the breaker codelet).

  Tests: `tests/test_bridges.py`, every test of `tests/diff/bridge-battery.scm` through the
  harness with the bridges setting on (`codelet_harness.enable_bridges`): 1000-codelet
  traces of every problem and seed, and nine bridge matrices. Slow tier, fork pool (about
  14 s on 32 cores); the fast tier runs the first 300 codelets of problem 0.
  `oracle/batteries/bridge-extra-battery.scm` adds a coherent vertical bridge whose internal
  strength stays under 100. The harness's fake Themespace and recording monitors are the
  battery's own fakes; the themes.ss helpers that bridges call are themes.py's since item 10.
- `metacat/rules.py`: rules.ss (rules, change descriptions, the rule scout, evaluator and
  builder, rule abstraction, application and quality, and the English transcription,
  including the `caddr`-of-`#f` crash).
- `metacat/answers.py`: answers.ss (answer-finder, answers and snags with their
  commentary, the slippage log, rule translation, and answer descriptions).

  Tests: `tests/test_rules.py`, every test of `tests/diff/rule-battery.scm` through the
  harness with bridges and rules on (`codelet_harness.RULES`): traces up to the first answer
  of every problem and seed, the first-answers summary and twelve rule matrices. Slow tier,
  fork pool (about 38 s on 32 cores); the fast tier runs the first 300 codelets of
  problem 0. rule-battery.scm's fakes (Trace, Memory, events, Commentary, suspend) are
  the battery's own; `find-next-space-position`, `equivalent-workspace-objects?` and `diff`
  are the engine's since item 10. `oracle/batteries/rule-extra-battery.scm` pins
  `transcribe-to-english` on hand-made clauses, the crash included, and rules' quality
  values.
- `metacat/themes.py`: themes.ss (the Themespace, theme clusters and themes, the
  thematic-bridge-scout codelet, the REPL abbreviations such as `diff`).
- `metacat/justify.py`: justify.ss (the answer-justifier codelet, rule-clause comparison,
  theme patterns to clamp).
- `metacat/trace.py`: trace.ss (the Temporal Trace: events, snag and clamp periods, the
  monitors and importance thresholds, theme and codelet patterns). This is the translation
  of trace.ss; the golden-trace writer is a separate module (item 11).
- `metacat/jootsing.py`: jootsing.ss (the jootser and progress-watcher codelets).
- `metacat/memory.py`: memory.ss (the Memory, answer and snag descriptions, reminding).
- `metacat/general_graphics.py`, `metacat/theme_graphics.py`, `metacat/trace_graphics.py`:
  only the pure helpers the model needs (`find-next-space-position`, `relation-name`,
  `group-event-pexp-text-string`); the panels item adds the rest of each file.

  Tests: `tests/test_golden.py`, the 109 golden traces of `tests/golden/`, byte for byte,
  through the package's headless driver (below); `tests/golden_harness.py` reads
  `tests/problems.txt` and runs each golden in a fresh fork of a fresh process (about
  35 s on 32 cores, 6 min of CPU; slow tier). The fast tier runs `a b z` seed 1 (1000
  codelets). The slow tier also runs the oracle live on `abc ccbbaa ijk` seed 3, the
  original's crash, and compares the 1062 trace lines before it.
  `oracle/batteries/trace-extra-battery.scm` reaches what the goldens don't: concept
  mapping importances near the 65 threshold, a group of strength 99 and partly active
  themes spreading to the Slipnet.
- `metacat/run.py`: run.ss (init-mcat, run-mcat, update-everything, and the REPL commands
  `ss`, `runtil`, `break`, `go`, `rerun`). `run.toplevel(thunk)` runs one command the way
  the REPL does: a break parks the run's thread and returns, `go` resumes it.
- `metacat/headless.py`: the oracle's headless windows (prelude.ss) and its run.ss driver
  (`run_problem`), which prints the Problem line, commentary, answers and summary.
- `metacat/trace_writer.py`: the JSON-lines trace (docs/trace-format.md), written by
  wrappers installed as the oracle's trace.ss installs them (trace.py is trace.ss, the
  Temporal Trace).
- `metacat/__main__.py`: `python3 -m metacat INITIAL MODIFIED TARGET [ANSWER] [--seed N]
  [--max-codelets K] [--keep-going] [--trace FILE] [--verbose]`, with the oracle run.ss's
  arguments, output and exit codes (0, 2 for bad arguments, 1 when the original crashes).

  Tests: `tests/test_cli.py` runs the CLI and the live oracle side by side on
  racket/tests/cli-test.rkt's cases (an answer, no cap, a cap, justify, keep-going,
  verbose, the halt run, the crash run, twelve bad argument lists, `--trace`, a clock
  seed) and requires the same stdout and exit code (slow tier, about 6 s in parallel).
  `tests/test_run.py` runs `tests/run_scenarios.py` in fresh processes: a run stopped at
  150, 300 and 450 and resumed with `go` is the run never stopped, step mode, a break
  inside a codelet (suspend at an answer) resumed to the oracle's `--keep-going` state.
  `oracle/bench_runs.py` times every golden run in Python and in the oracle
  (docs/python-run-times.md).

Extra seeds and speed (item 12):
- `oracle/capture_extra_seeds.py` runs tests/extra-seeds.py's 720 runs (20 non-golden
  seeds per problem line of tests/problems.txt, the seeds the Racket port was audited on)
  in the unedited oracle and freezes each run's exit code, stdout, first stderr line and
  trace hash into `fixtures/extra-seeds/` (the traces themselves would be about 300 MB).
  `tests/test_extra_seeds.py` runs the 720 through the package's driver, each in a fresh
  fork, and requires the same five things (slow tier: about 2 min on 32 cores, plus 1.5
  min to re-capture the oracle's side and compare it byte for byte).
- `oracle/bench_speed.py [DIR ...]` measures the CPU time of five fixed runs, interleaving
  the repetitions across copies of `python/`; docs/python-run-times.md records each
  speed-up (marked `speed (item 12)` in the code) and its gain.

The SGL interpreter on tkinter (item 13):
- `metacat/gui/sgl.py`: sgl-interpreter.ss. `draw_bang`, `erase_bang`, `draw_exp`, the
  environment (`lookup`, `extend`, `init_env`), and `Viewport`, the original's
  `<viewport>`. Its methods send the original's Tcl commands, argument for argument, to
  a window: `swl.TkCanvas(tkinter_canvas)` on screen, a recording window in the tests.
- `metacat/gui/fonts.py`: fonts.ss (`swl_font`, `make_mfont`, `make_fixed_font`,
  `select_face`, `create_mcat_logo`). Text is measured on the hidden Tk canvas, as in
  the original. Call `fonts.load()` and then `sgl.load()` once Tk is up.
- `metacat/gui/colors.py`: `swl_color`, `*color-names*` and the common colours (`Rgb`).
- `metacat/gui/swl.py`: `swl_tcl_eval`, `tcl_word` (Scheme values to Tcl words) and
  `TkCanvas`.

  Tests: `tests/test_sgl.py`.
  - Every test of `tests/diff/sgl-battery.scm`.
  - The Tcl command stream of `oracle/sgl-fixture.scm` (every SGL form, the tag
    operations, degenerate shapes), compared command for command with
    `fixtures/sgl-tcl/`. `python3 python/oracle/capture_sgl_tcl.py` captures that
    stream from the unedited original through `oracle/sgl-tcl.ss`, which records
    `swl:tcl-eval`.
  - Fonts, colours and the viewport's mouse handling.
  - Slow tier: the fixture rendered on a real Canvas under `xvfb-run`
    (`tests/render_sgl_fixture.py OUT.png --check`, which grabs the window and checks
    pixels; `tests/snapshots/sgl-fixture.png` is one rendering).
