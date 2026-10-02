# Chez Scheme oracle

Headless harness that runs the unmodified Metacat 1.2 source in
`../original/` under Chez Scheme 10, to produce golden traces for the Racket
port (`tests/golden/`).

- `prelude.ss` makes `../original/metacat.ss` load and run without SWL:
  `extend-syntax` (syntax-case), stub `swl:*` modules, inert widgets, no-op
  threads, the configuration variables, null windows for a headless run, and
  an error handler that prints a backtrace. It does not touch the random
  number generator: the oracle uses Chez 10's own `random`, which the port
  reproduces (`docs/trace-format.md`).
- `run.ss` runs one problem:

      scheme --script chez_scheme/oracle/run.ss abc abd xyz --seed 7 --max-codelets 20000
      scheme --script chez_scheme/oracle/run.ss abc abd xyz wyz --seed 5     # justify run
      scheme --script chez_scheme/oracle/run.ss abc abd xyz --seed 1 --max-codelets 4000 --keep-going

  It prints the commentary as it is written (`Comment:`), each answer
  (`Answer: X  quality Q  codelet N  temperature T`) and a summary. The run
  ends at the first answer (where the original pauses for Go) unless
  `--keep-going` is given. The original's console messages ("Type (go) or
  click on the Workspace to continue...", "Codelets run: N") are printed too.
- `tests/` holds Chez checks; `tests/run-tests.sh` runs each one with
  `scheme --script` from the repository root, and a check fails by exiting
  non-zero: `reader-check.ss`, `rng-check.ss` (the RNG specification),
  `headless-run-check.ss` (4 problems × 3 seeds reach an answer, twice with
  identical output), `demo-replay-check.ss` (documented demo runs replay).
