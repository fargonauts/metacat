# Progress Log

## Ralph Loop 0002 Status
- **Started**: 2026-10-03
- **Target**: 18 items
- **Current**: 5/18 SOLVED

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


---

## Iteration 3 — 2026-10-03 19:05

### Completed
Item 02, `chez.py`: **SOLVED**.
- **Vectors from Chez.** `python/oracle/batteries/chez-battery.scm` (new, 63 tests) holds
  the vectors that the frozen `tests/diff/` batteries lack. `capture.py` now also finds
  batteries in `python/oracle/batteries/`; a local battery's own file joins its `SOURCES`,
  so the other ten batteries' `SOURCES` are unchanged. It is captured into
  `python/fixtures/chez/` (1.9 MB) through the same unedited diff-eval.ss, and the slow
  re-capture freshness test covers it. Contents:
  - the generator: the value of every draw and the state after it (15 seeds × 54
    arguments, including the 4-step path for n > 2^32 − 1), a 1,500-draw Metacat-like
    run from seed 3852097033, and the bad seeds and arguments;
  - arithmetic: `+ - * / max min` over 12 × 12 exact, inexact, signed-zero and infinite
    operands, called both as procedure values and as inlined primitives (they agree);
    n-ary and unary forms, `quotient`/`remainder`/`modulo`, the predicates, `1+`/`-1+`;
  - rounding: Chez's own (`#%round` …) and utilities.ss's exact versions;
  - `exact->inexact` on 400 random ratnums;
  - `sqrt`/`exp`/`log`/`tanh` on 237 exact and 161 flonum arguments, `tanh` on the 601
    mapping strengths, and `expt` as a 23 × 23 table, 40 extra cases and the model's
    own shapes;
  - the printer: `number->string` on 3,000 doubles from random bits, 300 per decade,
    5,240 near ties and the edge cases; `write`/`display` of every character, string and
    symbol code point below 256 and a few beyond; symbol specials; `display`, `write`,
    `~a` and `~s` on nested data and quote abbreviations; `format` errors; `printf`;
  - lists: `map` with 1–4 lists up to 31 elements and length mismatches, `for-each` and
    `andmap`/`ormap` values, `sort` results and predicate-call logs up to 150 elements
    (`<`, `<=`, `>`), on pairs and presorted lists; `remq`/`remv`/`remove`,
    `memq`…`assoc`, `eqv?`/`equal?`;
  - top-level values.
- **Tests first.** `python/tests/test_chez.py` (62 tests covering all 63 fixtures, plus `scheme_canon.py`:
  helpers.scm's `b:canon`/`b:num` for Python values). It rebuilds each battery
  expression in Python, in the same order of draws (Chez's `map` where the battery uses
  `map`), and compares canonical text with the fixture. Besides the new fixtures, it
  covers the Chez-level tests of the utilities battery: `rng-*`, `map*-order`,
  `for-each*`, `andmap`/`ormap-order`, `sort-*`, `number->string-*`, `format-*`,
  `printf-output`, `remq`/`remv`/`remove`, `1+` and `rounding`. I wrote the tests before
  `chez.py` existed and ran them: collection failed with `ImportError: cannot import name
  'chez'`, so every test failed. The capture script came first. Its first run showed
  two battery mistakes, which I fixed in the battery, not in the fixtures: a `b:seeded`
  result used as a list, and literal bad `format` strings, which become compile-time
  warnings that diff-eval reports as ERROR.
- **`python/metacat/chez.py`.** The first version passed 55 of 60. What the Chez vectors
  then taught (all now in `docs/anomalies_and_quirks.md`):
  - Chez prints a double that lies exactly halfway between the two shortest digit
    strings with the **upper** one; Python's `repr` rounds half to even
    (1586243275893042.25 → `…423e15` vs `…422e15`). `_flonum_digits` corrects `repr`.
    I added the `number->string-ties` test so the rule is pinned (17 ties among 5,240).
  - In symbols, Chez writes non-ASCII characters that aren't R6RS constituents as
    `\xHH;` (U+0080–U+00A0, «, », soft hyphen, U+2028/9, U+FEFF). racket/compat.rkt
    writes them as is, which is harmless for the model.
  - `expt`: only a `1/2` power is an exact root (`(expt 8 1/3)` → `2.0`); exact base 1 → `1`;
    exact base 0 → `0` for positive powers, `1.0` for `0.0`, an error for negative ones;
    `0.0` to a negative power → `+inf.0`; negative base to a non-integer power →
    `exp(p log b)`, bit-equal to Chez. I added `expt-extra` after these findings.
  - Exact 0 is the identity of `+` and `-`: `(+ 0 -0.0)` → `-0.0`, `(- 0 0.0)` → `-0.0`
    (Python: `0.0`). This corrects the plan's "`+` and `-` agree".
  - `set-top-level-value!` binds an unbound name in Chez (Racket raised).
  - Python raises where Chez gives infinities (`1/0.0`, `0.0**-1`, `math.log(0.0)`,
    `round(inf)`).
  - Confirmed equal: `math.tanh`, `math.exp`, `math.log`, `math.sqrt`, `**` (libm `pow`)
    and `float(Fraction)` are bit-equal to Chez on every vector.
  Representations: symbols and Scheme strings are `str`. `chez.String` and `chez.Char`
  mark a string or character only where `write` must tell it from a symbol;
  `chez.Pair` is a pair with a non-list cdr; `chez.Vector` is a vector that must print
  `#(...)`; `None` is void and prints `#<void>`.
- **Mutation checks** (each applied to chez.py, run, then restored; `cmp` confirmed):
  all 22 caught.

  | Mutation | Failing |
  |---|---|
  | LCG multiplier 72931 → 72933 | 17 |
  | float draw takes 3 bits of s1, not 4 | 11 |
  | int draw takes the low half of s2 | 10 |
  | exact 0 × flonum gives `0.0` | 3 |
  | `(+ 0 x)` through Python | 2 |
  | `max` without inexact contagion | 2 |
  | one-list `map` left to right | 6 |
  | list merge sort: first half first | 2 |
  | `sorted()` for 25+ elements | 3 |
  | `remq` removes the first occurrence only | 1 |
  | `for-each` returns void | 2 |
  | printer without the tie rule (plain `repr`) | 3 |
  | exponent written `e+21` | 10 |
  | positional layout up to e = 10 | 7 |
  | `write` abbreviates `(quote x)` | 2 |
  | every non-ASCII symbol character as is | 1 |
  | `round` half away from zero | 2 |
  | flonum^int by repeated multiplication | 2 |
  | `tanh` from `exp` | 1 |
  | `set-top-level-value!` raises when unbound | 1 |
  | `(eqv? 0.0 -0.0)` true | 2 |
  | `float(Fraction)` as `float(n)/float(d)` | 1 |

- Speed, for item 12: `random(1.0)` 0.61 µs, `random(7)` 0.30 µs, `map_` over 10
  elements 0.53 µs, `sort` of 10 elements 2.5 µs, `mul(Fraction, int)` 2.3 µs,
  `div(37, 100)` 0.66 µs, `number_to_string` 4.8 µs.
- Docs: `docs/python-translation-plan.md` corrected. `+`/`-` at signed zeros, `expt`,
  the printer's ties, `None` printing `#<void>` (the plan said "nothing visible"), the
  `String`/`Char`/`Pair`/`Vector` representations, and `set_top_level_value_bang`.
  `python/README.md` covers the local batteries and chez.py. `test_fixtures.py` now
  expects 10 frozen batteries plus `chez`.
- `python3 ralph_loops/loop0002/gate.py`: GATE PASSED (163 tests, 53 s).

### Blockers
None. Out of scope, by design: Chez's exact complex numbers (`1+2i`) have no Python
counterpart and never occur in Metacat. The two fixture values that contain one are
taken as is (`scheme_canon.Raw`), and `sqrt` of a negative perfect square raises
`NotImplementedError`. `random` of a bignum range (beyond 2^60 − 1) is also
unsupported, since Metacat never draws one. Procedures print as `#<procedure>`, without
Chez's names.

### Next
Item 03: `objects.py` (candidate C3), `sugar.py` and `utilities.py`, against all 197
utilities tests. Use `chez.map_` for `tell-all` and every `map` with effects, and
`chez.sort`/`chez.remq`. Bind `utilities.round_` etc. to `chez.exact_round`…`exact_truncate`
(they already pass the `rounding` fixture). Use `chez.add1`/`sub1` for `1+`/`-1+`, and
`chez.format_`/`printf`. Use `chez.mul`/`div`/`max_`/`min_` wherever an operand can be a
flonum, `chez.expt`/`sqrt`/`exp`/`tanh` everywhere. `scheme_canon.canon` replaces the
prototype tests' minimal canon. Move `name_mapping.py` into `metacat/names.py`.

---

## Iteration 4 — 2026-10-03 19:28

### Completed
Item 03, objects, sugar and utilities: **SOLVED**.
- **Tests first.** `python/tests/test_utilities.py` has one case for each of the 197 tests
  of `tests/diff/utilities-battery.scm`. `CASES` maps each test name to a Python
  rebuild of the battery expression, with the same order of draws and effects, and
  compares its `b:canon` text with the frozen fixture (`ERROR` fixtures must raise
  `chez.SchemeError`). `test_every_battery_test_is_translated` checks that the names
  equal the MANIFEST's 197. The battery's own definitions (`make-fake`, the stand-ins
  for `make-slipnode`, `establish-link`, `make-codelet-type`, `*coderack*`,
  `*control-panel*`, `%verbose%`) are translated in the test. `engine_module(...)` puts
  them on `metacat.setup`/`slipnet`/`coderack`: on the real module once it exists, on a
  temporary one until then. I wrote the whole file, with the API it expects, before any
  of the three modules existed. Run: collection failed with `ImportError: cannot import
  name 'objects' from 'metacat'`, so all 197 cases failed. Structural tests are in the
  same file: every `define` of utilities.ss and syntactic-sugar.ss, and each of the 22
  extend-syntax forms, has its mapped Python function; every public function's docstring
  names its origin; there are no tkinter imports; `self` is the receiver through
  delegation; forwarders; `report_error_and_halt` can be replaced; an escape is caught
  only by its own `continuation-point*`, and fails after the form returns.
- **Code.**
  - `python/metacat/objects.py`: candidate C3 (`SchemeObject`, `@message`, `tell`,
    `delegate(self, msg, args, *parents)`, `delegate_to_all`, `tell_all`,
    `base_object`, `Lambda`, `Forwarder`, `procedure_p`, `INVALID`, `Reset`).
  - `python/metacat/sugar.py`: every extend-syntax form as a function, with thunks for
    delayed bodies. `stochastic_if_star` draws exactly one `(random 1.0)`, before the
    probability. A form with several patterns is one function per pattern. Free names
    are read from the engine modules at call time.
  - `python/metacat/utilities.py`: utilities.ss function for function, in the file's
    order.
  - `name_mapping.py` moved into the package as `python/metacat/names.py`; the test
    helper keeps only `original_names()`.
  - `chez.py` additions: `ExactComplex`, `make_rectangular`/`real_part`/`imag_part`
    (exact `3+4i`, needed by `coord`), `make_vector`, `string_to_number`, `atan`.
    `scheme_canon` prints `ExactComplex`.

  After the first full write, all 197 cases passed on the first run. The two
  non-fixture tests that failed were wrong expectations in my own tests:
  - the no-GUI check grepped the source text, and the module docstring says "never
    imports tkinter" (it now walks the AST, as test_chez.py does);
  - the delegation test expected a parent *without* an `else` clause to answer invalid.
    It answers void, as in Chez, and the test now checks both kinds.
- **Mutation checks** (`/tmp/mutate.py`, not kept; each mutation applied to the module,
  then the file run, then restored). 40 mutations, all caught except one equivalent
  mutant:

  | Mutation | Failing |
  |---|---|
  | pairwise-map: map before the recursion | 3 |
  | cross-product: l1 first to last | 6 |
  | partition: insert first to last | 2 |
  | bounded-random-partition: insert in pick order | 2 |
  | tell-all left to right | 1 |
  | delegate passes the parent as self | 1 |
  | delegate-to-all left to right | 1 |
  | `~` draws the sign first | 1 |
  | `prob?` with `>=` | 1 (after utilities-extra, below; 0 before) |
  | `exists?` by Python truthiness | 1 |
  | remove-duplicates keeps the first | 2 |
  | weighted-index with `<=` | 1 |
  | average with Python `/` | 2 |
  | log10 without the 1e-15 nudge | 2 |
  | round-to-100ths with Python `round` | 1 |
  | all-same? by `==` | 1 |
  | map-leaves maps `'()` as a list | 1 |
  | flatmap / select-extreme map left to right | 1 / 1 |
  | sort-by-method with `sorted()` | 1 |
  | stochastic-pick without `exact->inexact` | 2 |
  | `sgn` 0 → 0 | 3 |
  | make-table default 0 | 2 |
  | rotate counterclockwise | 2 |
  | `event?` returns `#t` | 1 |
  | stochastic-if*: probability before the coin | 1 |
  | stochastic-if* with `<=` | 1 |
  | for* from/to exclusive | hangs (`(ascending-index-list 0)`, the faithful loop): caught by timeout |
  | for* returns void | 3 |
  | repeat* times returns a value | 1 |
  | continuation-point* catches any escape | 1 |
  | fizzle not reset | 1 |
  | say ignores `%verbose%` | 1 |
  | mcat without its fender | 3 |
  | link: label before length | 1 |
  | valid-number? accepts 0 | 2 |
  | tell does not halt on invalid | 2 |
  | make-rectangular keeps an exact 0 imaginary part | 1 |
  | select-extreme `assv` → `assoc` | 0: equivalent (both compare numbers by `eqv?`) |

  To kill the `prob?` survivor I added a local battery,
  `python/oracle/batteries/utilities-extra-battery.scm` (4 tests: `prob?-ties`,
  `stochastic-if*-ties`, `select-extreme-ties`, `misc`). It is captured into
  `python/fixtures/utilities-extra/` through the unedited diff-eval.ss and covered by the
  slow re-capture test. Unlike the 197, it was written *after* the code, and its Python
  cases passed at once. `test_fixtures.py` now expects the local batteries `chez` and
  `utilities-extra`.
- **Evaluation-order audit** of utilities.ss and syntactic-sugar.ss (calls or `let`s with
  two effectful parts):
  - `pairwise-map`'s `append`: the recursion first (fixture);
  - `stochastic-if*`: the coin, then the probability;
  - `for*` from/to: `exp1`, then `exp2`;
  - `~`: the size (`let`), then the sign;
  - `cross-product-filter-map`/`-map-filter`, `map-leaves` and `filter-map`: `cons` goes
    left to right; the recursion on the rest of l1 comes first (fixtures);
  - `partition`/`bounded-random-partition`: every pick, then the inserts in reverse;
  - `tell-all`, `delegate-to-all`, `flatmap`, `select-extreme`, `adjacency-map` and
    `weighted-average`: `chez.map_` order;
  - `sort-by-method`: two `tell`s as one predicate's arguments. Python goes left to right;
    they are pure for every sort key in the model (noted in the docstring).

  Every site carries a `# chez:` or `# 1.2:` comment (20 in the three modules).
- **Re-grep that the plan asked for** (`symbol?`, `string?`, `eq?` on string literals,
  `~s`). New finding: the graphics (`string?` in sgl-interpreter.ss:386/398/432,
  general-graphics.ss:418, fonts.ss:93, gui.ss:363) and rules.ss:269
  (`filter-out symbol?`) do tell strings from symbols. I logged it as an open hidden
  coupling, so the items for those files keep the distinction. No `eq?` on a string
  literal; `~s` only in run.ss's `no-prompt` error and fonts.ss's debugging.
- **Docs.**
  - `docs/anomalies_and_quirks.md`: three new entries: Python interns only
    identifier-like string constants (so `INVALID` must be one shared object; checked
    with two modules), Python's `complex` can't hold Chez's exact complex numbers, and
    the strings-vs-symbols coupling above.
  - `docs/python-translation-plan.md`: a new "As built (item 03)" subsection with the
    objects/sugar/utilities API decisions; the Names section points to `metacat/names.py`.
  - `python/README.md`: the new modules.
- Speed (for item 12): `tell` 135 ns, delegated once 247 ns, twice 367 ns, child+parent
  creation 111 ns, `prob_p` 0.64 µs, `stochastic_if_star` 0.75 µs.
- `python3 ralph_loops/loop0002/gate.py`: GATE PASSED (379 tests, 36 s).

### Blockers
None. Deliberately left for later items:
- arithmetic on `ExactComplex` and complex coordinates (`magnitude`, `+` on coords);
  the graphics need it;
- `ask` (the REPL prompt; no run uses it) is translated minimally: symbols and numbers on
  one line, not a full Scheme reader.

### Next
Item 04 onwards: model modules import `from metacat.utilities import tell, prob_p, ...`
and `from metacat import sugar`, and always call `sugar.fizzle()` qualified. setup.py
must define `p_verbose` and `g_control_panel`, coderack.py `g_coderack` and
`make_codelet_type`, slipnet.py `make_slipnode` and `establish_link` (sugar reads them
there). `slipnet_node_list_star(specs, module=slipnet)` and
`codelet_type_list_star(specs, module=coderack)` also set the module attributes.
Objects return `objects.INVALID` (never a spelled-out string) from `otherwise`. Run
drivers replace `objects.report_error_and_halt`.

---

## Iteration 5 — 2026-10-03 20:19

### Completed
Item 04, constants, setup, coderack and descriptions: **SOLVED**.
- **Tests first.** `python/tests/test_coderack.py` has one case for each of the 43 tests of
  `tests/diff/coderack-battery.scm`. Each case rebuilds the battery expression in Python
  with the same order of draws and effects. Every battery `map` is `chez.map_`, since
  several of them reset and post inside the map. Each case compares its `b:canon` text with
  the frozen fixture. The battery's fakes are translated in the test: the logging window,
  workspace, themespace, trace, top-down nodes, proposed structures, descriptions and the
  settings alists. So are its top-level forms between tests (installing the fakes before
  `urgency-value-table`, resetting the modes before `threshold-distributions`), and they
  run before the test they precede. The cases run in the battery's order in one engine,
  as the battery does. Globals of modules not translated yet (`*workspace*`, `*themespace*`,
  `*trace*`, `*top-down-slipnodes*`, run.ss's `*display-mode?*`/`*step-mode?*`/
  `%step-cycles%`) are stand-ins from `tests/engine_stubs.py`. That file is
  `engine_module`, moved out of test_utilities.py, which now imports it. Other tests check
  that:
  - every model `define` of the four files has its Python name;
  - the codelet types are module attributes and top-level values;
  - the four description types have procedures;
  - `set_global` rejects unknown names;
  - docstrings name their origin;
  - no module imports tkinter.

  I wrote the file before any of the modules existed and ran it: collection failed with
  `ImportError: cannot import name 'engine' from 'metacat'`, so every case failed.
- **Code** (all new):
  - `metacat/constants.py`: the threshold distributions;
  - `metacat/view_globals.py`: the colours, fonts and speed settings the model reads, `#f`
    until the views set them, as in racket/engine/view-globals.rktl;
  - `metacat/setup.py`: the globals and user commands (`setup` and `enable-resizing` are
    the GUI's, item 15);
  - `metacat/coderack.py`: codelet types, codelets (a `Codelet` class that keeps its type's
    closure as `owner`), bins, the coderack, posting probabilities and counts, bottom-up
    and top-down posting. `load()` makes `*codelet-types*` through
    `sugar.codelet_type_list_star(..., module=coderack)`, then the three type lists and
    `*coderack*`;
  - `metacat/descriptions.py`: `make-description`, the four codelet procedures (installed
    by `load()`), `propose-`/`build-description`, `descriptions-equal?`,
    `description-member?`;
  - `metacat/engine.py`: `LOAD_ORDER` (metacat.ss's order), `load()` (each module's
    `load()`, once) and `set_global`/`get_global` by Scheme name.

  After the first write, the 43 cases (50 tests) passed on the first run. The only failure
  was in the test itself (`manifest()` returns a tuple).
- **Mutation checks** (`/tmp/mut/mutate*.py`, not kept; each mutation applied, the test
  file run with `-x`, then the file restored; `git status` confirmed it was clean). 37
  mutations; all caught except the equivalent ones:

  | Mutation | Result |
  |---|---|
  | bin add-codelet appends instead of consing | caught |
  | choose-random-codelet picks a wrong index | caught |
  | remove-codelet without the swap | caught |
  | choose-codelet over the bins reversed | caught |
  | delete-codelets over the codelet list reversed | 4 failing |
  | `get-coderack-bin` `>= 100` → `> 100` | 17 failing |
  | post's overflow test `=` → `>` | 2 |
  | deferred `>= 100` → `> 100` | 1 |
  | excess deferred codelets not random-picked | 1 |
  | add-deferred-codelet appends | 4 |
  | rule-scout probability exact 1/2 instead of 0.5 | 2 |
  | jootser probability 0.25 | 2 |
  | jootser bottom-up urgency | 3 |
  | thematic count `floor` instead of `round` | 1 |
  | `post-codelet-probability`'s missing else gives 0 instead of void | 2 |
  | unclamp without reset-urgencies | 2 |
  | time stamp `*codelet-count*` + 1 | caught |
  | plural label on the first line | 1 |
  | codelet print without `round` | 2 |
  | "(scope is ...)" for one argument | 1 |
  | description counted as a proposed structure | 2 |
  | top-down slipnodes not told | caught |
  | delete-codelets does not decrease the count | 4 |
  | a distribution weight changed | 1 |
  | verbose-on's test inverted | 1 |
  | `blank-window` given a symbol instead of a string | 1 |
  | `%eliza-mode%` default `#f` | 1 |
  | descriptions-equal? ignores the descriptor | 2 |
  | description-member? returns the element | 1 |
  | **adjust-urgency with Python `min`/`max`** | **0 at first**: see below |
  | urgency table with an exact exponent `/15` | 0: equivalent (same rounded table) |
  | `get-coderack-bin` `<= 0` → `< 0` | 0: equivalent (urgency 0 maps to bin 0 either way) |
  | bottom-up posting `coin <= p`, p evaluated first | 0: equivalent (no draw in p; ties need coin = p exactly) |
  | clamp always re-applies | 0: equivalent headless (same urgencies) |
  | `initialize` returns `'done` literally | 0: equivalent |

  To kill the `min`/`max` survivor I added a local battery,
  `python/oracle/batteries/coderack-extra-battery.scm` (2 tests:
  `adjust-urgency-clipping`, with flonum and exact urgencies pushed past 0 and 100 by nine
  deltas, and `clamp-exactness`, clamping at 90 then 90.0). It is captured into
  `python/fixtures/coderack-extra/` through the unedited diff-eval.ss and covered by the
  slow re-capture test. Unlike the 43, it was written *after* the code; its Python cases
  passed at once, and the mutant now fails. `test_fixtures.py` now expects the local
  batteries `chez`, `coderack-extra` and `utilities-extra`.
- **Evaluation order.** No call or `let` in coderack.ss, setup.ss or constants.ss has two
  effectful parts (as porting-notes.md says for the Racket port). The draws are
  `stochastic-pick-by-method` (bins by urgency sum, deletion by removal weight), `random`
  (the codelet in a bin), `random-pick` (excess deferred codelets) and `stochastic-if*`
  in the posting loops. Those loops draw the coin before the probability, with a
  `# chez:` comment. descriptions.ss's `make-description` `let` is pure, and its comment
  says so. Racket's notes call that let right to left; item 02 measured left to right in
  a test lambda. The order doesn't matter here.
- **Docs.**
  - `docs/anomalies_and_quirks.md`: two Python traps. Python's `bool` is an `int`
    (`100 - False` is 100 where Chez raises), so arithmetic on values that may be `#f` goes
    through `chez.sub`… And pytest's diff of multi-MB strings takes minutes, so the battery
    asserts report the first differing character instead.
  - `docs/python-translation-plan.md`: a new "As built (item 04)" subsection.
  - `python/README.md`: the new modules.
- Speed (for item 12): choose-codelet + post on a coderack of 99 codelets: 31 µs; post into
  a full coderack, which deletes one codelet by removal weight: 275 µs.
- `python3 ralph_loops/loop0002/gate.py`: GATE PASSED (435 tests, 33 s).

### Blockers
None. Left for later items, by design:
- descriptions.py's `make-description`, its codelets, `propose-description` and
  `build-description` are translated but not yet run: they need the Workspace, Slipnet,
  formulas and themes. The workspace and codelet batteries (items 06–07) pin them.
- The codelet types' graphics methods (`highlight`, `draw-graphics`,
  `update-bar-graphics`, `draw-codelet-count`) are translated but call
  `general_graphics.solid_box` and the coderack window. The panels item (14) tests them.
- Every codelet type's coderack window is `#f` until `set-graphics-parameters`, as in the
  original. The headless driver (items 10–11) must install a null window in each,
  as the oracle prelude's `install-headless-windows!` does.

### Next
Item 05, slipnet and images: `slipnet.py` and `images.py`, each with a `load()` that
builds the nodes (`sugar.slipnet_node_list_star(specs, module=slipnet)`), the links and
`*top-down-slipnodes*`. engine.py calls them in metacat.ss's order. Its test should take
the battery's stand-ins from `tests/engine_stubs.py` and call `engine.load()` once.
`engine.set_global` finds any module in `LOAD_ORDER` that exists, stand-ins included.
Reach modules that don't exist yet through `_metacat.<module>` at call time.
