# Progress Log

## Ralph Loop 0002 Status
- **Started**: 2026-10-03
- **Target**: 18 items
- **Current**: 2/18 SOLVED

---

## Iteration 1 — 2026-10-03 18:45

### Completed
Item 00, skeleton and fixture pipeline: **SOLVED**.
- `python/` skeleton: `pyproject.toml` (package `metacat`, no runtime dependencies, `test`
  extra = pytest, a `slow` marker, `pythonpath = ["."]`), a stub `metacat/__init__.py`
  with the GPL and "translated to Python" lines, `README.md`, and `run-tests.sh` (`pytest -x`).
  Tiers: `bash python/run-tests.sh` is the full tier and is what the gate runs (about 55 s
  today). `--fast` skips `@pytest.mark.slow` tests (under a second).
- `python/oracle/capture.py BATTERY... | --all [--out DIR]` runs
  `chez_scheme/oracle/diff-eval.ss` (unedited) on `tests/diff/helpers.scm`, then
  `sgl-chez-setup.ss` for sgl (the Racket runner's `#:chez-setup`), then the battery,
  from the repo root. It splits the output per test and writes
  `python/fixtures/<battery>/{MANIFEST, NNN-NAME.txt, SOURCES}`. The split doesn't guess
  where a multi-line value ends: the test names, in order, come from Chez's reader
  (`python/oracle/list-tests.ss`, new, read-only). Before writing anything, the capture
  checks that joining the pieces again gives Chez's output byte for byte, and it fails on
  a non-zero exit or any stderr output. With `--all`, the ten batteries run in parallel.
- Captured all 10 batteries: 604 tests (bridge 46, codelet 59, coderack 43, graphics 48,
  panels 36, rule 50, sgl 48, slipnet 47, utilities 197, workspace 75). That's 168 MB
  of text (rule 94 MB, bridge 47 MB, codelet 23 MB, the largest file 4 MB) and about
  13 MB gzipped, so git's packs stay small. I kept plain text so the fixtures stay
  readable and diffable.
- `python/tests/chez_fixtures.py`: the loader for later items, `chez(battery, test)` →
  Chez's text. `python/tests/scheme_forms.py` is a minimal Scheme datum scanner that
  counts a battery's `(test ...)` forms independently of Chez.
- `python/tests/test_fixtures.py` (37 tests):
  - the fixture count per battery equals the battery's test count, as read by the Python
    scanner and compared with MANIFEST and the file names;
  - the split/join round trip on every battery, plus synthetic multi-line and malformed
    cases;
  - file and battery naming;
  - the scanner on comments, `#;`, strings and characters;
  - `SOURCES` unchanged: sha256 of diff-eval.ss, prelude.ss, list-tests.ss and every
    `tests/diff/` file, plus the Chez version. This is the fast freshness check.
  - **slow** `test_recapture_is_byte_identical`: re-captures every battery into a
    tmpdir and compares the files byte for byte. It takes about 53 s and runs in the
    full tier, so it runs in the gate.
- Test-first: I wrote the tests before any fixture existed and ran them against an
  empty `fixtures/`: 33 failed, 3 passed (only the pure-function ones passed). The
  capture script was written in the same step as the tests, not before them. After
  capturing, all 37 pass. A first run of the multi-line split test also caught a wrong
  expectation in the test itself. A name list that skips a test can still parse when the
  skipped record looks like part of a value. That ambiguity is why the names come from
  Chez's reader. I fixed the test case.
- A separate manual Chez run made earlier gave a rule output identical to the joined
  fixtures, and the slow re-capture matches too: the batteries are deterministic.
- `python3 ralph_loops/loop0002/gate.py`: GATE PASSED.

### Blockers
None.

### Next
Item 01: the translation plan (`docs/python-translation-plan.md`) and the
object-system prototype with its micro-benchmark. Later items load expected values with
`from chez_fixtures import chez`. If new Chez-side setup is needed for a fixture, add a
capture script under `python/oracle/` instead of editing `tests/diff/`, which is frozen.

---

## Iteration 2 — 2026-10-03 18:43

### Completed
Item 01, the translation plan: **SOLVED**.
- `docs/python-translation-plan.md`, the counterpart of numbo's translation audit. I read
  compat.rkt, utilities.rkt, every `port:` comment and the six docs first. It records:
  - every Chez semantic the engine depends on and its Python strategy:
    - numbers: `Fraction` normalised to `int`, `chez.div`/`mul`/`max_`/`min_`/
      `sqrt`/`exp`/`log`/`expt`, the PRNG, rounding, the flonum printer;
    - evaluation-order sites with file and line (groups.ss:368–370, utilities.ss:690
      `pairwise-map`, run.ss:234, `for*`, `stochastic-if*`, `~`, `wins-fight?`);
    - `map`, `sort`, `remq`, `for-each`, `eq?`, truthiness, symbols vs strings,
      one-armed `if`, `case`, `record-case`, top-level values and `eval`;
    - continuations: escapes become exceptions; `break`/`go` becomes an exception
      headless and a blocked engine thread in the GUI;
    - printing.
  - the object representation, with the benchmark (below);
  - the module structure: one module per `.ss` file, definitions only at import time,
    and a `load()` per module called in metacat.ss's order by `engine.py`. In-file
    references are unqualified; cross-module references are always qualified
    (`setup.g_temperature`); `chez`/`objects`/`sugar`/`utilities` are imported
    directly. `engine.set_global` takes Scheme names. Goldens run in workers forked
    after load.
  - the name mapping;
  - the order of the work and nine risks, ranked. Truthiness comes first: it's new
    in Python, and Racket didn't have it.
- New Chez facts, checked under `scheme --script`:
  - `(* 0 1.5)` → `0` and `(/ 0 2.5)` → `0` (exact);
  - `(max 3 2.0)` → `3.0`;
  - `(exp 0)` → `1`, `(log 1)` → `0` and `(expt 0.0 0)` → `1`;
  - a 2-binding `let` inside a lambda evaluates left to right (`12`), unlike the
    documented top-level `21`. Logged in anomalies_and_quirks.md as an update to the
    evaluation-order entry.
- `python/oracle/count-calls.ss` (new) runs the unedited oracle run.ss with `tell` and
  `delegate` wrapped. About 1,000 `tell`s per codelet, 12–17% of them delegated:
  2,242,151 over the 2,170 codelets of abc abd xyz seed 3852097033. Output unchanged
  (wyz at 2170).
- Prototypes and tests:
  - `python/tests/object_prototypes.py`: candidates A (closure + if/elif), B (closure +
    dict of closures), C/C2/C3 (class per object with a message dict and the original
    `(self, msg, *args)` protocol) and D (Python inheritance), plus `bench()`.
    `python3 python/tests/object_prototypes.py` prints the table that is in the plan.
  - **Decision: C3.** About 173 ns per message wherever it sits in the record-case,
    297 ns delegated once, and 146 ns to create a child + parent. A costs 507 ns for
    the 40th message; B costs 4.4 µs to create an object; D can't delegate to
    separate objects.
  - `test_object_prototype.py` (32 tests). A, B, C and C3 are checked against the Chez
    fixtures of utilities-battery.scm's `tell`, `tell-args`, `tell-alias`,
    `tell-invalid`, `base-object`, `delegate`, `delegate-to-all`(`-order`,
    `-invalid`), `tell-all-order` and `record-case-no-else`, with a minimal `b:canon`.
    Other tests cover self through delegation and forwarders, the `chez_map1` order,
    and every candidate answering the benchmark object alike. The micro-benchmark
    asserts only the orderings the decision rests on, with wide margins, and prints
    the table.
  - `python/tests/name_mapping.py` + `test_name_mapping.py` (29 tests). The mapping is
    valid, non-reserved and injective on all of the original's 1,309 names (defines,
    extend-syntax forms, codelet types, slipnodes), with 25 pinned examples.
- Tests-first, honestly: here the prototypes *are* the code under test, so they were
  written together with their tests. What the tests caught while being written:
  - D failed the halt path ('ChildD' isn't callable);
  - the self-through-delegation test hit the original's own infinite recursion (an
    object without `object-type` that gets a bad message), and now delegates to
    `base-object`;
  - a wrong expectation (`plato-LetterCtgy` isn't a name; the nodes are
    `plato-letter-category`);
  - the first version of the self test covered only C. A `delegate_c3` mutation passed,
    so the test now runs for C and C3.
  Mutation checks, all restored afterwards:

  | Mutation | Tests failing |
  | --- | --- |
  | `tell-all` left to right | 4 |
  | `delegate` (C) passing the parent as self | 1 |
  | `delegate_c3` passing the parent as self | 1 |
  | `tell` not halting | 7 |
  | `otherwise` without `else` returning invalid | 1 |

- `python3 ralph_loops/loop0002/gate.py`: GATE PASSED (98 tests, 45 s).

### Blockers
None.

### Next
Item 02, `chez.py`. The plan's "Numbers" and "Lists" tables list what it needs. Capture
the extra vectors (exact zero products, contagion, exact sqrt/exp/log/expt,
`float(Fraction)` rounding, `math.tanh` against Chez) with a script in `python/oracle/`.
`object_prototypes.chez_map1` is a first `map_` to promote. Item 03 builds `objects.py`
from candidate C3 and moves `name_mapping.py` into the package as `metacat/names.py`.

