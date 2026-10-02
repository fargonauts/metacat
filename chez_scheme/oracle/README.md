# Chez Scheme oracle

Headless harness that runs the unmodified Metacat 1.2 source in
`../original/` under Chez Scheme 10, to produce golden traces for the Racket
port (`tests/golden/`). Planned contents (later items): the SWL stub prelude,
an `extend-syntax` implementation, the portable PRNG specified in
`docs/trace-format.md`, trace instrumentation, and the golden-trace generator.

`tests/` holds Chez checks; `tests/run-tests.sh` runs each one with
`scheme --script` from the repository root, and a check fails by exiting
non-zero.
