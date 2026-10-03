# Follow-ups for a second loop

Written by the final audit of loop0001 (item 17, 2026-10-03). Loop0001 made a faithful,
line-for-line port: it reproduces the oracle event for event on the 109 golden runs and
on 720 runs with other seeds (docs/extra-seeds.md). Nothing below is needed for that.
These are the things loop0001 deliberately left alone ("faithful first, idiomatic later"),
plus what the audit noticed. Each item should keep the golden and extra-seed equivalence
unless it says otherwise; anything that changes a run is a divergence and goes in
docs/divergences.md.

## Safety net to keep first

- **Keep the oracle and the goldens as the regression net for every clean-up.** Before
  a refactor, run `bash tests/run-tests.sh` and `python3 tests/extra-seeds.py`. Consider
  putting a short extra-seed run (`--seeds 2`, about 15 s) in the gate, so that
  refactoring has more than the 109 golden runs behind it.
- **Gate time** is about 10 minutes, most of it the differential batteries
  (bridge-diff-test.rkt about 85 s, rule-diff-test.rkt about 2.7 min), views-test.rkt
  (about 70 s) and dist-test.rkt (a 70 MB build). Now that the goldens cover full runs,
  the codelet-level harness batteries (items 07–09) could run with smaller caps, or
  move to a slower nightly tier.

## Idiomatic clean-up

- **Module structure.** The engine is one module that `include`s 37 `.rktl` files
  (porting-notes.md, item 04), because the original's files are mutually recursive and
  `set!` each other's globals. A second loop could split it into real modules along the
  dependency graph in docs/code-map.md, with explicit exports, and replace `set-global!`
  (a whitelist of globals that outside code may set) with parameters or explicit hooks.
- **Objects.** About 4,000 `(tell obj 'msg ...)` call sites dispatch on closures through
  `record-case` (utilities.ss). Racket structs or `racket/class` would give arity
  checking and error messages that name the method. Do this file by file, keeping the
  goldens green.
- **Chez evaluation order.** Each call site where two arguments draw random numbers was
  ported as an explicit `let*` in Chez's order (`port:` marks, porting-notes.md tables).
  Idiomatic code should keep that order explicit, never relying on argument order.
  compat's right-to-left `map` and Chez's `sort` algorithm are needed for equivalence and
  should stay in one place, with comments.
- **engine/pending.rktl** now holds only the four names the original never defines
  (`*temperature-clamped?*`, `*initial-slipnode-unclamp-time*`, `same-direction?`,
  `complement-codelet-pattern`). The first two belong with run.ss's globals and the last
  two can go, along with their dead callers. Then delete the file.
- **Graphics split.** Parts of the graphics files live in the engine (pexp builders,
  `group-event-pexp-text-string`, `relation-name`, the EEG) because the model calls them
  (porting-notes.md, items 13–14). A cleaner boundary is a view-observer interface: the
  model emits events, views subscribe. That would also remove view-globals.rktl's
  `#f` colours and fonts from the engine.
- **compat.rkt** reimplements Chez's printer (`format`, `number->string` for flonums),
  `random`, `sort` and `record-case`. Keep the parts that matter for equivalence (RNG,
  sort, flonum printing in traces). The rest could become plain Racket once the callers
  stop depending on Chez's exact output.
- **Dead and latent code in the original** (docs/anomalies_and_quirks.md): the
  never-called singleton-group proposers, `bonds-equal?`, `get-complement-codelet-pattern`,
  `init-env`'s untellable default font, the Memory's dead first-icon spacing.
- **Divergence candidates, each needing a decision and a divergences.md entry.** These
  are suspected bugs in the original, ported faithfully. Fixing any of them changes runs
  and needs new goldens produced from a deliberately patched oracle, never by hand:
  - `letter-category-mappable-objects?` compares object1's group category with itself
    (always true);
  - a string image's `new-alpha-position-category` sends `new-start-letter`;
  - `answer-justifier` sends `get-constituent-objects` to a letter (the
    `report-error-and-halt` runs, e.g. `eqe qeq abbba aaabaaa` seeds 3 and 3401132640);
  - `transcribe-to-english` crashes on `abc ccbbaa ijk` seed 3 (`caddr` of `#f`).

## Performance

- Per codelet the port is about **2× slower** than Chez (docs/run-times.md: ≈200 vs
  ≈97 ms per 1000 codelets). Nothing was optimised. Profile first (`raco profile`
  on `racket/cli.rkt`). Likely costs:
  - closure-and-`record-case` message dispatch on every `tell`;
  - exact rational arithmetic, which equivalence requires;
  - the compat wrappers (`map` in Chez's order, `sort`);
  - list-based tables (the original has no hash tables).
- Splitting the engine into real modules (see above) is a readability change first. One
  big module does not stop Racket's compiler from inlining (it may even help), so
  measure before restructuring for speed.
- The GUI repaints a whole window's display list on change (racket/gui/gui.rkt's 50 ms
  tick). Long runs make long display lists, because erasing adds items
  (anomalies). Pruning covered items, or a backing bitmap per window, would keep long
  GUI runs fast.
- Each golden or extra-seed run needs a fresh engine because the Memory outlives a run
  (anomalies). A `reset-engine!` that rebuilds the global state would make batch runs
  cheaper than one process or namespace per run.

## New features

- **Batch statistics**: run a problem over N seeds and report the answer distribution,
  mean quality, codelets and final temperature (as in the dissertation's Chapter 5
  tables and Copycat's answer bar charts). tests/extra-seeds.py already computes most of
  this from traces; a `cli.rkt --batch N` would make it a feature.
- **Save and load runs**: the trace format (docs/trace-format.md) is complete enough to
  replay a run's events in the GUI without re-running the model, and a problem plus
  seed reproduces a run exactly.
- **Packaging** for macOS and Windows (only Linux is built and tested;
  make-dist.sh and dist-test.rkt are Linux-specific), and HiDPI scaling of the windows
  (fonts are sized at a fixed 96 dpi).
- **GUI**: native widget colours (racket/gui cannot set them), window placement
  remembered across runs, an automated test of the theme edit mode (Clamp theme pattern,
  ported but only compiled), and a single-window layout as an alternative to eleven
  frames.
- **Problems beyond the letter-string domain** belong to a different project; the
  docs/robotone_numbo_metacat_* notes compare Metacat with its FARG relatives.
