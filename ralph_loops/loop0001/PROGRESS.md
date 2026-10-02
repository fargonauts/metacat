# Progress Log

## Ralph Loop 0001 Status
- **Started**: 2026-10-02
- **Target**: 18 items
- **Current**: 1/18 SOLVED

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
