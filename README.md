# Metacat, in modern Scheme

A faithful port of **Metacat 1.2**, James B. Marshall's model of analogy-making and
self-watching perception, to [Racket](https://racket-lang.org), with a native GUI built on
`racket/gui`.

**Metacat home page:** <https://science.slc.edu/~jmarshall/metacat/>

![Metacat after answering wyz to "abc → abd; xyz → ?" (Run 7 of Marshall's dissertation)](docs/screenshots/run7-wyz.png)

## What Metacat is

Metacat solves letter-string analogy problems: *if `abc` changes to `abd`, what does `xyz`
change to?* It builds its interpretation of a problem out of many small, partly random
actions (*codelets*). They notice bonds between letters, group letters, map one string onto
another, describe the change as a rule, and apply the rule to the target string. A
network of concepts (the *Slipnet*) decides what seems relevant, and a *temperature*
measures how coherent the current interpretation is.

Metacat is the successor to **Copycat**, by Melanie Mitchell and Douglas Hofstadter
(Mitchell's Copycat was written in Common Lisp). Metacat adds self-watching. It keeps a
*Temporal Trace* of its own processing, notices when it keeps hitting the same snag, "jumps
out of the system" by clamping a pattern of concepts, remembers its answers in an *Episodic
Memory*, compares answers, and justifies an answer it is given. It says what it is doing in
a running *Commentary*. All of this is described in Marshall's dissertation,
[*Metacat: A Self-Watching Cognitive Architecture for Analogy-Making and High-Level
Perception*](https://science.slc.edu/~jmarshall/metacat/dissertation.pdf) (Indiana
University, 1999).

The original Metacat 1.2 (released 2020) is written in Chez Scheme, with a GUI built on the
Scheme Widget Library (SWL), which is no longer maintained. Today the only easy way to run
the original is a VirtualBox image. This port runs on a current Racket.

## Credits and license

Metacat is © 1999, 2003 **James B. Marshall**. It is based on **Copycat**, originally
written in Common Lisp by **Melanie Mitchell**, from the Fluid Analogies Research Group of
Douglas Hofstadter. The Racket port keeps Marshall's copyright headers on every ported file
and adds a "Ported to Racket" line.

Both the original and this port are free software under the **GNU General Public License,
version 2 or later**; see [`chez_scheme/original/LICENSE`](chez_scheme/original/LICENSE).
Metacat comes with no warranty.

## Running it

Requirements: Racket 8.x (CS) with `racket/gui` (on Ubuntu: `sudo apt install racket`).
Chez Scheme 10 (`sudo apt install chezscheme`) is needed only to run the original and the
equivalence tests.

**The GUI:**

```bash
racket racket/main.rkt          # or: racket racket/main.rkt 1.5  (scale the windows)
```

The control panel and the windows open: Workspace, Slipnet, Coderack, Temperature, Temporal
Trace, Commentary, Episodic Memory, and the Top, Bottom and Vertical Themes. Type a problem
in the control panel's command line and press Enter:

- `abc abd xyz` asks what `xyz` changes to.
- `abc abd xyz 7` does the same with random seed 7, so the run can be replayed.
- `abc abd xyz wyz` asks Metacat to *justify* the answer `wyz`.

Then press **Go** to run, **Step** to run one step (the step interval is under Options),
**Stop** to interrupt, and **Reset** to start the problem again. When Metacat finds an
answer it stops; Go (or a click on the Workspace) makes it look for another. The **Demos**
menu loads the runs of Marshall's dissertation, with their seeds (see the caveat in
[`docs/demos.md`](docs/demos.md)). **Help** shows the original's help text.

**Headless**, the same run without windows prints the commentary and the answers:

```bash
racket racket/cli.rkt abc abd xyz --seed 7
racket racket/cli.rkt INITIAL MODIFIED TARGET [ANSWER] [--seed N] [--max-codelets K] [--keep-going] [--trace FILE]
```

A run stops at its first answer, as the GUI does, unless `--keep-going` is given.
`--trace FILE` writes a JSON-lines trace of every codelet, structure, temperature, theme and
event ([`docs/trace-format.md`](docs/trace-format.md)).

**The standalone program** doesn't need Racket installed:

```bash
bash make-dist.sh                      # builds build/metacat/ (raco exe + raco distribute)
build/metacat/bin/metacat              # the GUI
build/metacat/bin/metacat abc abd xyz  # headless, with the CLI's arguments
```

Copy the `build/metacat/` directory anywhere. It holds `bin/metacat`, the Racket runtime
it needs in `lib/`, this README and the license.

<p>
<img src="docs/screenshots/mrrjjj-513-workspace.png" width="49%"
     alt="The Workspace of abc → abd; mrrjjj → ? after 513 codelets">
<img src="docs/screenshots/run7-workspace.png" width="49%"
     alt="The Workspace with the answer wyz, both rules and the crossed bridges">
</p>

*Left: `abc → abd; mrrjjj → ?`, seed 1, after 513 codelets: bonds, groups and bridges
under construction. Right: Run 7's answer `wyz`, with its top rule (red), its bottom rule
(blue) and the crossed bridges that map `a`–`z` and `c`–`x`.*

## How the port is checked: an oracle

The aim is a *faithful* port, not a reinterpretation. Given the same seed, the port makes the
same run as the original: the same codelets in the same order, the same structures, the
same temperature, the same answers and the same commentary.

1. **The original is kept unchanged** in `chez_scheme/original/`. A gate checks its git
   tree hash against the import commit on every change.
2. **The original runs headless as an oracle.** [`chez_scheme/oracle/`](chez_scheme/oracle/)
   loads those 44 files, unmodified, into Chez Scheme 10 through a prelude. The prelude
   stubs out SWL, provides the old `extend-syntax` macros, and instruments the program by
   wrapping its top-level procedures from outside. `scheme --script chez_scheme/oracle/run.ss
   abc abd xyz --seed 7` is the original's own headless run.
3. **Golden traces.** The oracle recorded 109 seeded runs of 36 problems (`tests/problems.txt`,
   including every demo of the dissertation) as traces in `tests/golden/`. These traces are
   only ever produced by the oracle.
4. **The port reproduces them event for event.** All 109 traces match byte for byte, and so
   does the printed output. This needs Chez's random-number generator (bit for bit), Chez's
   order of evaluating arguments where it matters, its `sort`, its exact arithmetic and its
   number printing. Smaller differential tests compare the port with the original file by
   file (utilities, coderack, slipnet, workspace, bonds and groups, bridges, rules, the SGL
   drawing language and the panels' graphics).
5. **The GUI only watches.** The engine in `racket/` never depends on `racket/gui`. With
   every window attached, the 109 golden runs still match.

What the port does differently, and why, is in [`docs/divergences.md`](docs/divergences.md)
(drawing on racket/draw instead of Tk, the control panel's widgets). Porting decisions are
in [`docs/porting-notes.md`](docs/porting-notes.md). Bugs and oddities found in the original
along the way are in [`docs/anomalies_and_quirks.md`](docs/anomalies_and_quirks.md).

```bash
bash tests/run-tests.sh            # every test (about 9 minutes): the Racket tests,
                                   # the GUI tests on a virtual display (xvfb-run),
                                   # and the Chez oracle checks
python3 ralph_loops/loop0001/gate.py   # the same, plus the check that the original is untouched
```

The GUI tests need `xvfb-run` (Xvfb), `xwininfo` (x11-utils) and, optionally, `bwrap`
(bubblewrap), which runs the standalone program in a sandbox without Racket.

## Layout

```
chez_scheme/original/   Metacat 1.2 by James B. Marshall, as distributed (read-only)
chez_scheme/oracle/     the headless harness that runs the original under Chez Scheme 10
racket/                 the port: compat.rkt (Chez-isms), engine.rkt + engine/*.rktl
                        (the model, one file per original file), headless.rkt, cli.rkt,
                        main.rkt and metacat.rkt (entry points), gui/ (the windows)
tests/                  run-tests.sh, golden traces, the problem × seed list, batteries
docs/                   code map, porting notes, divergences, anomalies, trace format,
                        demos, run times, the dissertation and its figures (reference/)
ralph_loops/            the loop driver, its plan and progress log
make-dist.sh            builds the standalone program
```

## How it was made

The port was built by a "Ralph loop" (`ralph_loops/loop0001/loop.py`), which runs one fresh
Claude Code session per work item in [`iterations.md`](ralph_loops/loop0001/iterations.md).
After each session it runs the gate, then commits and pushes. Each session's work is logged
in [`PROGRESS.md`](ralph_loops/loop0001/PROGRESS.md), and
[`ralph_loops/ralph_loop_guide.md`](ralph_loops/ralph_loop_guide.md) describes the method.
