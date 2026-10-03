# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A faithful port of James B. Marshall's **Metacat 1.2** (Chez Scheme + the dead SWL/Tk GUI
toolkit; home page <https://science.slc.edu/~jmarshall/metacat/>) to Racket CS with a
`racket/gui` interface. The original runs headless under Chez Scheme 10 as an **oracle**;
the port must reproduce its seeded runs event for event. GPL v2 or later.

## Commands

```bash
bash tests/run-tests.sh                    # every test: raco test racket/, then each chez_scheme/oracle/tests/*.ss
raco test racket/tests/skeleton-test.rkt   # one Racket test file
scheme --script chez_scheme/oracle/tests/reader-check.ss   # one Chez check (fails by exiting non-zero)
python3 ralph_loops/loop0001/gate.py       # the regression gate: original untouched + run-tests.sh
racket racket/main.rkt                     # GUI entry point (control panel + windows)
env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s "-screen 0 1920x1200x24" raco test racket/gui-tests/*.rkt   # GUI tests, never on the real screen
racket racket/cli.rkt abc abd xyz --seed 7 # headless entry point (same output as the oracle's run.ss)
scheme --script chez_scheme/oracle/run.ss abc abd xyz --seed N --max-codelets K   # the original, headless (loop item 01)
```

Toolchain: Racket 8.18 [cs] (`racket`, `raco`), Chez Scheme 10.0.0 (`scheme` or `chezscheme`).

## Hard rules

- **Never edit `chez_scheme/original/`.** It is Metacat 1.2 exactly as distributed. The gate
  compares its git tree hash with `9f072c0:Metacat` (the import commit) and rejects
  uncommitted edits or untracked files there. All adaptation of the original happens from
  outside, in `chez_scheme/oracle/prelude.ss` (SWL stubs, `extend-syntax`, config vars,
  instrumentation by wrapping top-level procedures after loading).
- **`tests/golden/` is produced only by the oracle**: never hand-edit it, and never
  regenerate it to make a failing port pass.
- **Engine modules in `racket/` never require `racket/gui`.** GUI code lives in
  `racket/gui/` and only observes; attaching views must not change a run (no RNG draws,
  no state changes).
- When the port must differ from the original, record it in `docs/divergences.md`; record
  renames and restructurings that Racket forced, plus RNG and ordering subtleties, in
  `docs/porting-notes.md`.
- Log every bug, oddity or unexplained behaviour (in the original, Chez, Racket or the port)
  in `docs/anomalies_and_quirks.md`, using its entry format.

## Architecture (the original, which the port mirrors)

`docs/code-map.md` has one paragraph per original file in load order. Read it before
porting a file. The cross-file picture:

- **Load order** is in `chez_scheme/original/metacat.ss`: 44 files `load`ed into one global
  top-level, with mutually recursive definitions across files. Model files come first,
  then `sgl-interpreter.ss`, the `*-graphics.ss` panels, `demos.ss` and `gui.ss`.
- **Objects** are closures dispatching on a message via `record-case`. Callers write
  `(tell obj 'msg args...)`, about 4,000 call sites. Inheritance is `delegate` to a
  parent object. All of this is in `utilities.ss`.
- **Macros**: all 22 `extend-syntax` forms are in `syntactic-sugar.ss`. They include the
  slipnet definition language (`category-link*`, `lateral-sliplink*`, …) and the
  coderack forms (`post-codelet*`, `define-codelet-procedure*`). Chez 10 doesn't ship
  `extend-syntax`; the port rewrites them as `syntax-rules` in `racket/compat.rkt`.
- **Randomness is the crux of equivalence.** Every draw goes through Chez
  `random`/`random-seed`, via the helpers in `utilities.ss` (`prob?`, `random-pick`,
  `stochastic-pick`, `stochastic-select`, …), `stochastic-if*`, `wins-fight?`, and
  `random-seed` in `init-mcat` (`run.ss`). The port must make the same draws in the same
  order, with bit-identical `(random 1.0)` doubles. The chosen PRNG plan is in
  `docs/trace-format.md`.
- **Ordering**: there are no hash tables; "tables" are vectors of vectors and alists.
  Chez `sort` takes `(sort pred list)` and is stable; Racket's takes `(sort list pred)`.
  `utilities.ss` redefines `round`/`floor`/`ceiling`/`truncate` to return exact integers.
- **Graphics** funnel through `sgl-interpreter.ss`, a symbolic drawing language
  (`rectangle`, `arc`, `text`, `let-sgl` with origin/colour/font, …) that Marshall
  rendered onto Tk canvases. The port renders the same language on `racket/draw`.
  The rest of the toolkit use (`swl:`, `send`, `make <class>`, SWL threads) is mostly
  in `gui.ss`, `general-graphics.ss` and `fonts.ss`; see code-map.md for the stragglers.

## Repo layout

`chez_scheme/original/` (read-only source), `chez_scheme/oracle/` (headless harness and
its checks in `tests/`), `racket/` (the port: `info.rkt` names collection `metacat`;
`compat.rkt` for Chez-isms; `gui/`; `tests/`), `tests/` (`run-tests.sh`, `golden/`,
`problems.txt`), `docs/`, `ralph_loops/`.

## Ralph loop

The work is driven by `ralph_loops/loop0001/loop.py`, which runs one fresh `claude -p`
session per unchecked item in `iterations.md`. It may be running in the background
(`cat ralph_loops/loop0001/status.json`, `tail ralph_loops/loop0001/loop.log`). After
each session the driver runs the gate, allows up to three fix sessions, then commits
and **pushes to origin** (`git@github.com:fargonauts/metacat.git`). Inside a loop
session, don't commit or push yourself. Runtime knobs (pause, stop, caps, push) are in
`knobs.json`, re-read every iteration. `TASK.md` is the loop's immutable goal;
`PROGRESS.md` is the per-iteration log.
