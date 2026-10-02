# Metacat, in modern Scheme

A port of **Metacat**, James B. Marshall's model of analogy-making and self-watching
perception, to [Racket](https://racket-lang.org) with a native GUI (`racket/gui`).

Metacat solves letter-string analogy problems ("if `abc` changes to `abd`, what does `xyz`
change to?"). It is the successor to Melanie Mitchell and Douglas Hofstadter's
**Copycat**: besides building an interpretation of a problem, it keeps a trace of its own
processing, notices when it is going in circles, "jumps out of the system", and can compare
and explain its answers. See Marshall's
[Metacat page](https://science.slc.edu/~jmarshall/metacat/) and his
[dissertation](https://science.slc.edu/~jmarshall/metacat/dissertation.pdf).

The original Metacat 1.2 (2020) is written in Chez Scheme, with a GUI built on the Scheme
Widget Library (SWL), which is no longer maintained. Today the only easy way to run it is a
VirtualBox 5.2 image. This project makes it run on a current Racket, on Linux, macOS and
Windows.

> **Status:** in progress. The port is being built by an automated loop of fresh
> Claude Code sessions, one work item at a time; see
> [`ralph_loops/loop0001/`](ralph_loops/loop0001/) for the plan
> ([`iterations.md`](ralph_loops/loop0001/iterations.md)) and the log
> ([`PROGRESS.md`](ralph_loops/loop0001/PROGRESS.md)).

## How the port is checked

The aim is a *faithful* port, not a reinterpretation:

1. **The original is kept unchanged** in `chez_scheme/original/`. A gate checks its git
   tree hash against the import commit on every iteration.
2. **The original runs headless as an oracle.** `chez_scheme/oracle/` loads those
   files, unmodified, into Chez Scheme 10, with stubs in place of the SWL GUI. It
   records seeded runs as golden traces in `tests/golden/`.
3. **The Racket port must reproduce them event for event:** every codelet run,
   structure built or broken, temperature, answer and line of commentary. The same
   seed gives the same run in both.
4. **The GUI only watches.** The engine in `racket/` never depends on the GUI, and
   attaching the views must not change a run.

## Layout

```
chez_scheme/original/   Metacat 1.2 by James B. Marshall, as distributed (read-only)
chez_scheme/oracle/     headless harness for the original under Chez Scheme 10
racket/                 the Racket port: engine, CLI, and racket/gui/ views
tests/                  run-tests.sh, golden traces, the problem × seed list
docs/                   code map, porting notes, divergences, trace format
ralph_loops/            the loop driver, tasks and progress logs
```

## Requirements

- Racket 8.x (CS), including `racket/gui`
- Chez Scheme 10 (only needed to run the oracle and the equivalence tests)

On Ubuntu: `sudo apt install racket chezscheme`.

## Running

Once the corresponding loop items are done:

```bash
racket racket/main.rkt                       # the GUI
racket racket/cli.rkt abc abd xyz --seed 7   # headless: answers and commentary
bash tests/run-tests.sh                      # all tests, including equivalence with the original
```

## The Ralph loop

`ralph_loops/loop0001/loop.py` runs one fresh `claude -p` session per item in
`iterations.md`. After each session it runs the gate (`gate.py`). If that fails, it
gives Claude up to three attempts to fix it. Then it commits and pushes. If the gate is
still red after those attempts, the code changes are reverted and only the notes are
kept. Settings such as pause, stop, the time cap and push are in `knobs.json`, which is
re-read every iteration. See [`ralph_loops/ralph_loop_guide.md`](ralph_loops/ralph_loop_guide.md).

```bash
cd ralph_loops/loop0001
nohup python3 loop.py 30 &     # up to 30 iterations
tail -f loop.log               # one line per event
cat status.json                # what is running now
```

## Credits and license

Metacat is © 1999, 2003 James B. Marshall (version 1.2 released 2020), based on Copycat, originally written in Common
Lisp by Melanie Mitchell. Both the original and this port are free software under the
GNU General Public License, version 2 or later; see
[`chez_scheme/original/LICENSE`](chez_scheme/original/LICENSE).
