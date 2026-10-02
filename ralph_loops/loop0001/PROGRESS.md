# Progress Log

## Ralph Loop 0001 Status
- **Started**: 2026-10-02
- **Target**: 18 items
- **Current**: 5/18 SOLVED

---

## Iteration 1 — 2026-10-02 20:34
Item 00 (Toolchain and skeleton): **SOLVED**.

### Completed
- Toolchain present: Racket v8.18 [cs] (`/usr/bin/racket`, `raco`), `racket/gui/base`
  loads; Chez Scheme Version 10.0.0 as both `scheme` and `chezscheme`.
- Skeleton: `racket/info.rkt` (collection `metacat`), stub `racket/main.rkt` (GPL
  header + "ported to Racket" line; provides `metacat-version` and `main`; does not
  require racket/gui yet, `racket racket/main.rkt` prints a not-implemented message),
  `chez_scheme/oracle/README.md`, `docs/porting-notes.md`, `docs/divergences.md`.
- `tests/run-tests.sh`: `set -euo pipefail`; runs `raco test racket/`, then every
  `chez_scheme/oracle/tests/*.ss` with `scheme --script` (falls back to `chezscheme`),
  stops at the first failure, and fails if no Chez check exists. Checked that a
  temporary `(exit 1)` check makes it exit 1.
- Tests written first: `racket/tests/skeleton-test.rkt` (requires `../main.rkt`,
  checks `metacat-version` = "1.2" and `main` is a procedure) and
  `chez_scheme/oracle/tests/reader-check.ss` (Chez version is 10; the Chez reader
  reads every one of the 45 `.ss` files in `chez_scheme/original/`: 1454 top-level
  forms). Before the skeleton existed, `run-tests.sh` failed with
  "cannot open module file ... racket/main.rkt"; the Chez check checks the
  environment and the original, not new code, so it passed from the start.
- `docs/code-map.md`: one paragraph per file in `chez_scheme/original/` (load order,
  definitions, dependencies computed by identifier matching, line counts, SWL use),
  plus general facts for the port: the `tell`/`record-case` object system, every
  RNG entry point and the files that draw, `sort` uses (Chez `(sort pred list)`,
  stable), no hashtables, redefined exact `round`/`floor`/…
- Findings recorded there: besides the files TASK.md lists, toolkit calls also occur
  in `utilities.ss` (`pause` = `thread-sleep`), `workspace-graphics.ss`
  (`thread-break *repl-thread*`) and `theme-graphics.ss` (one `send vp`).
  TASK.md's `weighted-pick` does not exist; the original calls it `stochastic-pick`.
  `constants.ss` also draws (a probability-distribution object). `metacat.ss`
  needs `*platform*`, `*metacat-directory*`, `*file-dialog-directory*` defined
  (commented out in the distribution), so the oracle prelude must provide them.
- `python3 ralph_loops/loop0001/gate.py`: GATE PASSED.

### Blockers
- None.

### Next
- Item 01 in iterations.md.

---

## Iteration 2 — 2026-10-02 20:52
Item 01 (The original, headless, under Chez 10): **SOLVED**.

### Completed
- `chez_scheme/oracle/prelude.ss`: loads `chez_scheme/original/metacat.ss`
  unmodified (all 44 files) under `scheme --script`. Provides `extend-syntax`
  as a `syntax-case` macro (fenders and `with` evaluated at expansion time
  after substitution), empty `swl:oop`…`swl:threads` modules, inert
  `make`/`create`/`send`/`define-class`, `swl:tcl-eval`, `swl:font-families`,
  screen size, no-op threads and message queues, `*platform*`,
  `*metacat-directory*`, `*file-dialog-directory*`, an unbuffered muteable
  stdout (load chatter hidden; syntactic-sugar.ss's `printf` captures the port
  at load time), strict null windows for a headless run, and an error handler
  that prints a backtrace with source positions.
- `chez_scheme/oracle/run.ss INITIAL MODIFIED TARGET [ANSWER] [--seed N]
  [--max-codelets K] [--keep-going]`: graphics switches off, `init-mcat` then
  `run-mcat` as the Control Panel does; prints `Comment:` lines (the original
  Commentary window drawing on a recording text window), `Answer:` lines
  (answer, quality, codelet count, temperature) and a summary. Stops at the
  first answer/give-up (where the original pauses for Go) unless
  `--keep-going`; `--max-codelets` is the original's own `*break-time*`.
  Justify runs (4 strings) work. A run takes about 1 s.
- **Randomness plan** (`docs/trace-format.md`): keep Chez 10's own
  `random`/`random-seed`, with no PRNG swap. Read from the Chez v10.0.0 C source
  (`c/prim5.c`, `c/number.c`): a 32-bit LCG `S := S*72931 + 90763387 mod 2^32`;
  integers take the high halves of 2 (or 4) steps, `mod n`; flonums build a
  52-bit mantissa from 4 steps. Specified exactly, so item 03 can port it.
  (Chez 10's `make-pseudo-random-generator` is MRG32k3a like Racket's, but
  that is a different generator from the global `random`.)
- **Finding 1, the demo seeds DO replay**, contrary to the expectation in
  TASK.md/iterations.md: misc1 (mmmrrj at 7794), misc2 (abd at 1126), misc4
  (b at 453, y at 945), misc5 (flz, dlz, hlz at 1721) and the commented-out
  misc9 (dyz at 2257) come out exactly as `demos.ss` documents. misc3 and the
  "not used" misc6–8 do not. run1–8/fig5.x still need comparing against the
  dissertation (item 12).
- **Finding 2, evaluation order**: Chez does not evaluate arguments left to
  right (`(f (show 1) (show 2) (show 3))` prints `312`, `let` goes right to
  left, inlined `+`/`cons` go left to right). Racket goes left to right, so
  every multi-argument site with draws or other side effects must be ported
  in Chez's order. Recorded in trace-format.md and porting-notes.md.
- **Finding 3, model state tied to the graphics** (porting-notes.md): codelet
  types hold a private Coderack-window reference that every codelet `run`
  messages; memory descriptions call icon procedures installed by the Memory
  window; `group-graphics 'erase` is called ungated (groups.ss:727). Lists
  every window message a headless run sends.
- Tests, all in `tests/run-tests.sh` (Chez part about 25 s):
  - `chez_scheme/oracle/tests/headless-run-check.ss`: `abc abd xyz`,
    `abc abd ijk`, `eqe qeq abbbc`, `abc abd mrrjjj` × seeds 1, 2, 3 all
    reach an answer (xyz/xyd/yyz, ijd/ijl/ijl, baaaq/qeeeq/qbbbq,
    mrrjjk/mrrjjk/mrrjjjj), and each run repeated gives byte-identical
    output.
  - `chez_scheme/oracle/tests/rng-check.ss`: the spec, written in exact
    arithmetic, matches Chez's `random`/`random-seed` draw for draw and
    state for state; checked that changing a constant or the mantissa mask
    makes it fail (43551 and 7175 failures).
  - `chez_scheme/oracle/tests/demo-replay-check.ss`: the 5 demo runs above.
- Tests-first, honestly: I spiked the prelude first (to find out what loading
  needed) and wrote the checks before `run.ss` was finished. Checked that
  `headless-run-check.ss` fails without `run.ss` (12 failures: "failed for
  chez_scheme/oracle/run.ss: no such file or directory"), and that
  `demo-replay-check.ss` failed at first on misc5/misc9 because of the
  codelet cap semantics (the answer at count K is found by codelet K+1),
  which is now documented in run.ss. The RNG check tests a specification
  against Chez itself, so it passed as soon as the spec was right.
- `chez_scheme/oracle/README.md` updated. `python3 ralph_loops/loop0001/gate.py`:
  GATE PASSED. `chez_scheme/original/` untouched.

### Blockers
- None.

### Next
- Item 02 (traces and golden files). Notes for it: instrument by wrapping
  top-level procedures after `load-metacat` (as run.ss does with
  `abstract-answer-description`, `break`); codelet runs can be seen by
  wrapping each codelet type's procedure or `step-mcat`; the demo seeds
  replay, so `demos.ss` problems with their own seeds are good golden
  candidates. Watch for null-window errors on new problems: the null windows
  are strict on purpose, and any new message must be checked to be a command
  before it is allowed.

---

## Iteration 3 — 2026-10-02 21:09
Item 02 (Traces and golden files): **SOLVED**.

### Completed
- `chez_scheme/oracle/trace.ss`: JSON-lines trace instrumentation, entirely
  from outside the original. It wraps top-level procedures after loading
  (`build-bond/-group/-bridge/-description`, `break-bond/-group/-bridge`,
  `update-temperature`, `update-slipnet-activations`,
  `abstract-answer-description`, `report-error-and-halt`). It forwards
  `*coderack*` (to see each `choose-codelet`) and `*workspace*` (to see
  `add-rule`) through closures that pass the original object as `self`, and
  records Temporal Trace events from the Trace window plus commentary from
  the Commentary hook. Twelve event types: start, codelet (type, urgency,
  posted, rng state), build/break (bond, group, bridge, description, rule),
  temperature, slipnet (all activations every 15 codelets plus rng state),
  themes (when changed), event (answer/snag/clamp/rule/group/
  concept-mapping/concept-activation), answer, comment, halt, end.
- `run.ss --trace FILE`; the summary now also prints `Stopped: suspend|cap|halt`.
- `docs/trace-format.md`: the format, down to field order, string escapes
  and number formatting (exact rationals as `"n/d"`, Chez flonum syntax),
  how `t` counts codelets, what is deliberately left out, and the golden set.
- `tests/problems.txt`: 36 problems, 109 runs. These are the 25 problems of
  `demos.ss` with their documented seeds plus small seeds (3–5 per problem;
  misc3–5 with `keep-going`), and 11 classic problems from the dissertation
  (picked by how often the dissertation text names them) with seeds 1–3.
  Caps are 10000 (17000 for eqe-aaabaaa). Each run takes 1–8 s.
- `chez_scheme/oracle/make-golden.ss` writes `tests/golden/*.jsonl` (one
  fresh Chez process per run, `nproc` in parallel, about 13 s here).
  `--check` regenerates into /tmp and compares byte for byte, and reports
  missing or extra files. Goldens are written and committed: 109 files,
  40 MB uncompressed, 4.8 MB gzipped.
- `chez_scheme/oracle/validate-trace.py`: a structural checker for traces
  (fields and order, types, start/end, one codelet line per codelet,
  activation count, required event types). The Racket port can reuse it.
- Tests written first, and seen failing before the code:
  `chez_scheme/oracle/tests/trace-check.ss` (4 runs, including a justify run
  and a keep-going run: tracing does not change the stdout, the trace is
  valid and has the required event types, and it is byte-identical when
  repeated). Before the code it failed with run.ss's usage error on
  `--trace`. `chez_scheme/oracle/tests/golden-check.ss` (`make-golden.ss
  --check` plus validation of every golden) failed with "make-golden.ss:
  no such file or directory". I also checked that the checks catch
  breakage: one changed rng value in a golden gives "differs: ...
  line 100", an extra golden file gives "1 of 109 do not match", and
  deleting a line gives "codelet event 149 has t = 150". Each golden was
  restored afterwards (`cmp` identical).
- Findings (in porting-notes.md):
  1. the original itself fails on some runs. `eqe qeq abbba aaabaaa`
     seed 3 calls `report-error-and-halt` at codelet 4004, and `(reset)`
     makes `--script` exit 255. run.ss now ends the run like `break`
     (Stopped: halt), and that run is in the golden set. `abc ccbbaa ijk`
     seed 3 raises a Chez error (`caddr` of `#f` in `transcribe-to-english`);
     the set avoids it by using seed 4.
  2. Urgencies are often exact rationals (3601 codelet lines), so the port
     must keep Chez's exact arithmetic.
  3. run4's documented seed (abc abd xyz dyz) gives up without an answer in
     the oracle, as misc3 already did.
- `python3 ralph_loops/loop0001/gate.py`: GATE PASSED (about 48 s).
  `chez_scheme/original/` untouched.

### Blockers
- None.

### Next
- Item 03 in iterations.md. For the equivalence runs: the Racket port should
  write the same trace (trace-format.md) and compare it byte for byte with
  `tests/golden/`. The `rng` fields on codelet and slipnet lines show the
  first codelet whose draws diverge. Emit exact rationals as `"n/d"`, and
  reproduce the `halt` path of `report-error-and-halt`.

---

## Iteration 4 — 2026-10-02 21:41
Item 03 (The compatibility layer): **SOLVED**.

### Completed
- `racket/compat.rkt` covers syntactic-sugar.ss and the Chez built-ins
  Metacat relies on:
  - Chez 10's `random`/`random-seed` (the LCG of trace-format.md, bit for
    bit, including the 4-step path for ranges above 2^32−1);
  - one-armed `if`;
  - `map` in Chez's application order (pairs from the end for 1–2 lists,
    last to first for 3+);
  - `for-each` returning the last value;
  - `sort` with Chez's argument order and Chez 10's own algorithm (list
    merge below 25 elements, which sorts the second half first; Shivers's
    vector merge above);
  - all-occurrence `remq`/`remv`/`remove`, `1+`, `-1+`;
  - a table of top-level values (`define-top-level-value`, `top-level-value`, …);
  - Chez's printer: `number->string` (flonum layout rule from s/print.ss),
    `display`, `write` (symbol/char/string escapes), `format`, `fprintf`,
    `printf`, `newline`, `error`;
  - `record-case`, `reset`/`reset-handler`, `collect`, `real-time`;
  - the definitions of syntactic-sugar.ss and all 22 macros, plus
    module-level forms `define-slipnet-node-list*` and
    `define-codelet-type-list*`.
- `racket/utilities.rkt`: utilities.ss line for line on top of compat. The
  only changes are marked `port:`: the `scheme-round` family via `only-in`,
  `ask` with `peek-char`, `eval` → `top-level-value`, `pause` → `sleep`,
  and `pairwise-map` in Chez's evaluation order.
- Differential tests: `tests/diff/utilities-battery.scm` (196 tests). It
  covers every utility, including the random ones (`prob?`, `~`,
  `random-pick`, `stochastic-pick` (TASK.md's weighted-pick),
  `stochastic-pick-by-method`, `weighted-index`, `stochastic-select`,
  `weighted-select`, `stochastic-filter`, `bounded-random-partition`,
  `randomize`) over 15 seeds each, with the generator state afterwards. It
  also checks the call order of every higher-order utility through logging
  procedures, `sort` results and predicate-call sequences, flonum printing
  (literals plus 350 random doubles across magnitudes), `format ~a/~s` on
  every kind of datum, and every macro (slipnet and coderack macros against
  logging stand-ins).
  - Chez side: `chez_scheme/oracle/diff-eval.ss` loads the whole original
    through prelude.ss and evaluates the battery.
  - Racket side: `racket/tests/utilities-diff-test.rkt` evaluates it in
    racket/base + compat + utilities, runs Chez, and compares line for line.
  - The battery takes about 1.5 s in all.
- `racket/tests/compat-test.rkt` (32 checks) covers what the battery cannot
  express: known-answer RNG values from Chez, the module-level definers,
  `fizzle` across modules, keyword matching by name, `record-case` hygiene,
  `reset`/`report-error-and-halt`, `error` messages, and `mcat`'s
  expansion-time token check.
- Tests-first, honestly: the battery and `diff-eval.ss` were written and
  run against Chez before compat.rkt existed. The Racket runner came
  after a first draft of compat/utilities. Its first run failed:
  - one-armed `if` is a syntax error in Racket;
  - after that fix, 15 tests failed. Chez's `for-each` returns the last
    value (for* loops pass it on), `for*` evaluates its bounds left to
    right, `append` in `pairwise-map` evaluates the recursive call first,
    and Chez's sort sorts the second half first. Two tests were artifacts
    of Racket interning literal strings and flonums (now noted, and the
    tests use computed values).

  Each was fixed until all 196 agree. Mutation checks, each restored
  afterwards: changing the LCG multiplier fails 20 tests; changing the
  map order fails 10 or more (RNG and order tests); moving the flonum
  exponent threshold fails 2; changing a symbol-escape rule fails 1.
  compat-test.rkt was written after the code.
- Findings, in `docs/porting-notes.md` (new item 03 section):
  - Chez's argument evaluation order depends on the call's shape (a table
    of observations), and cp0 inlines `map` over literal lists in an order
    of its own;
  - Racket's `call/cc` misbehaved inside rackunit, so `continuation-point*`
    uses `call/ec` (the original only escapes upwards);
  - `(ascending-index-list 0)` loops forever in the original;
  - pairs are immutable (only rule-graphics.ss:77 mutates one);
  - module-level expression values get printed by Racket, so engine
    modules must discard them.
- `chez_scheme/oracle/README.md` documents `diff-eval.ss`.
- `python3 ralph_loops/loop0001/gate.py`: GATE PASSED.
  `chez_scheme/original/` untouched.

### Blockers
- None.

### Next
- Item 04 in iterations.md. Notes for the engine port:
  - require `compat.rkt` and `utilities.rkt`;
  - Racket forbids `set!` on imported variables and module cycles, and
    the original's 44 files are mutually recursive with globals set! across
    files, so one engine module that `include`s the ported files in load
    order (or a module language whose module-begin also voids top-level
    expression values) is probably the simplest faithful structure;
  - every call with two or more effectful arguments needs Chez's order,
    checked against the goldens;
  - slipnet.ss should use `define-slipnet-node-list*`, and rules.ss must
    register `format-slipnode` as a top-level value.

---

## Iteration 5 — 2026-10-02 21:58
Item 04 (Constants, setup, coderack, descriptions): **SOLVED**.

### Completed
- **Engine organisation, decided and written up** (porting-notes.md, "The
  engine's module structure"): one module, `racket/engine.rkt`, that
  `include`s the ported files `racket/engine/*.rktl` in metacat.ss's load
  order, after requiring compat.rkt and utilities.rkt. Reasons: the original's
  files refer to each other in both directions and `set!` each other's
  globals; Racket forbids module cycles and `set!` on imports, and one module
  gives exactly the semantics of Chez's top level loaded in order while each
  `.rktl` stays a line-for-line copy of its `.ss`.
  - `racket/engine-lang.rkt`: the engine's module language, racket/base
    whose `#%module-begin` wraps module-level expressions in `void` (Chez's
    top level drops their values; racket/base would print them).
  - `racket/engine/pending.rktl`: stand-ins, grouped by original file, for
    names whose files are not ported yet (procedures raise "not ported yet",
    variables are `#f`), including the graphics constants coderack.ss names.
    Later items delete their names there; a leftover is a duplicate
    definition and fails to compile.
  - `set-global!` (exported): sets a listed engine global from outside
    (tests, future CLI and GUI), since importers cannot `set!`.
- Ported: `constants.ss` (only the probability distributions; colours, fonts,
  window sizes and titles wait for the GUI items), `setup.ss` (globals and
  user commands; `setup`/`enable-resizing` create windows and move to the
  GUI layer), `coderack.ss` (unchanged but for `define-codelet-type-list*`),
  `descriptions.ss` (unchanged). GPL headers kept, "Ported to Racket" lines
  added.
- compat.rkt: Chez's `case`, which accepts a single datum as a clause key
  (`(rule-scout ...)` in coderack.ss); Racket rejected it at compile time.
  Covered by a new differential test in utilities-battery.scm (now 197).
- Tests:
  - `tests/diff/coderack-battery.scm` (43 tests) +
    `racket/tests/coderack-diff-test.rkt`: the same battery under Chez with
    the original loaded and under Racket with the engine; outputs must agree
    line for line (about 0.9 MB of output). Covers the urgency table, bin
    selection for integer/rational/flonum urgencies, bin urgencies at every
    temperature, posting (time stamps, bin indices, list order),
    `choose-codelet` over 8 seeds × 7 temperatures with the RNG state after
    every choice, overflow deletion (incl. proposed structures reported to
    the Workspace), removal weights, deferred posting below/at/above the
    limit, clamping and urgency adjustment, codelet `run`/`fizzle`, printing,
    `post-codelet-probability`/`num-of-codelets-to-post`/`bottom-up-urgency`,
    `add-bottom-up-codelets` and `add-top-down-codelets` with fake
    Workspace/Themespace/Trace/slipnodes, the threshold distributions, the
    setup.ss commands, and the description helpers.
  - `racket/tests/engine-test.rkt` (11 checks, written after the code):
    loading prints nothing, `set-global!` works and rejects unlisted names,
    codelet types are module variables and top-level values, pending
    stand-ins raise, and loading the engine declares no racket/gui or
    racket/draw module.
  - Infrastructure: the battery helpers moved to `tests/diff/helpers.scm`;
    `diff-eval.ss` takes several files and defines `b:set-global!`; the
    Racket runner is now `racket/tests/diff-runner.rkt`, shared by both
    differential tests.
- Tests-first, honestly: the battery was written and run under Chez before
  any engine code existed (one battery bug found there: a codelet argument
  must be an object). Before the engine compiled, the Racket test could not
  run at all (Racket rejected Chez's single-datum `case` clause). The first
  Racket run after porting failed most checks, because the battery's
  namespace had its own engine instance, so `set-global!` changed another
  copy (a runner bug). Once that was fixed, one test still failed because of
  a battery bug: `map` over a literal `(list ...)`, which Chez's cp0 inlines
  in its own order. Both were fixed, and then all 43 tests agreed with no change
  to the ported model code. Mutation checks on coderack.rktl, each restored:
  reversing the in-bin pick fails 3 tests, changing the urgency exponent 17,
  the removal weight 1, the deferred-excess pick 1, the bin's list order 12.
- `python3 ralph_loops/loop0001/gate.py`: GATE PASSED. `chez_scheme/original/`
  untouched.

### Blockers
- None. The description codelets (`bottom-up-description-scout`, …,
  `propose-description`, `build-description`) and `make-description` need
  the Workspace, workspace structures, formulas and Slipnet, so only the
  helpers `descriptions-equal?`/`description-member?` are tested now. The rest
  will be checked by the golden traces once those files are ported.

### Next
- Item 05 in iterations.md. Notes:
  - add each ported file as an `include` in engine.rkt, in load order, and
    delete its names from `engine/pending.rktl`;
  - add globals that are set from outside to `set-global!`'s list;
  - single-datum `case` clauses now work; other Chez-isms may still appear
    at compile time;
  - the headless driver must give every codelet type a null Coderack window
    (`set-graphics-parameters`), as the oracle prelude does, or `run` fails
    on `#f`;
  - new differential batteries can reuse `diff-runner.rkt` with fakes for
    the parts not ported yet, as coderack-battery.scm does.
