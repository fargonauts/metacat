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
