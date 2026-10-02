# Progress Log

## Ralph Loop 0001 Status
- **Started**: 2026-10-02
- **Target**: 18 items
- **Current**: 2/18 SOLVED

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
