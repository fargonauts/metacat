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
  (`number_to_string`, `display`, `write`, `format_`, `printf`). Tests:
  `tests/test_chez.py`.
