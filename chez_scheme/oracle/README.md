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
  `Stopped:` says why the run ended: `suspend`, `cap` or `halt` (the
  original called `report-error-and-halt`). `--trace FILE` also writes the
  JSON-lines trace (`docs/trace-format.md`) without changing the run.
  The port's `racket racket/cli.rkt` takes the same arguments and prints the
  same output; `racket/tests/golden-test.rkt` and `cli-test.rkt` run this
  script live to check it.
- `trace.ss` is the trace instrumentation: it wraps top-level procedures
  (`build-bond`, `break-group`, `update-temperature`, …), forwards
  `*coderack*` and `*workspace*` through closures that note codelets and
  rules, and records the Temporal Trace's events from the Trace window.
- `make-golden.ss` writes `tests/golden/*.jsonl`, one trace per problem and
  seed in `tests/problems.txt`, running them in parallel; with `--check`
  it regenerates into a temporary directory and compares byte for byte.

      scheme --script chez_scheme/oracle/make-golden.ss            # rewrite the goldens
      scheme --script chez_scheme/oracle/make-golden.ss --check    # compare only

- `validate-trace.py FILE... [--require ev,...]` checks trace structure.
- `diff-eval.ss FILE ...` evaluates differential batteries with the
  original loaded: each FILE in turn, normally `tests/diff/helpers.scm` (the
  shared helpers) and then a battery such as `tests/diff/utilities-battery.scm`
  or `tests/diff/coderack-battery.scm`, `tests/diff/slipnet-battery.scm` or
  `tests/diff/workspace-battery.scm` (which loads `tests/diff/workspace-dump.scm`) or
  `tests/diff/codelet-battery.scm` (the codelet-level harness of item 07, which loads
  `tests/diff/codelet-harness.scm`) or `tests/diff/bridge-battery.scm` (the same
  harness with bridges, descriptions and the breaker enabled, item 08) or
  `tests/diff/rule-battery.scm` (the same harness with rules and answers too, up to
  each run's first answer, with fakes for the Trace and Memory, item 09). It prints one canonical result per
  `(test NAME EXPR)` form and defines `b:set-global!` (`set-top-level-value!`)
  for batteries that set the original's globals. The Racket side is
  `racket/tests/diff-runner.rkt`, used by `utilities-diff-test.rkt`
  (compat.rkt + utilities.rkt) and `coderack-diff-test.rkt`, `slipnet-diff-test.rkt`,
  `workspace-diff-test.rkt`, `codelet-diff-test.rkt`, `bridge-diff-test.rkt` and
  `rule-diff-test.rkt`
  (+ engine.rkt).

      scheme --script chez_scheme/oracle/diff-eval.ss tests/diff/helpers.scm tests/diff/utilities-battery.scm
- `tests/` holds Chez checks; `tests/run-tests.sh` runs each one with
  `scheme --script` from the repository root, and a check fails by exiting
  non-zero: `reader-check.ss`, `rng-check.ss` (the RNG specification),
  `headless-run-check.ss` (4 problems × 3 seeds reach an answer, twice with
  identical output), `demo-replay-check.ss` (documented demo runs replay),
  `trace-check.ss` (traces are valid, reproducible and do not change the
  run), `golden-check.ss` (`make-golden.ss --check`, and every golden is
  valid), `workspace-init-check.ss` (the battery's copy of init-mcat's
  Workspace steps builds the same initial workspace as the real `init-mcat`,
  for every problem in `tests/problems.txt`).
