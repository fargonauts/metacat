# Anomalies and quirks

A field log of bugs, anomalies, UFO sightings and strange things found in Metacat, in Chez
Scheme, or in the port. Anything surprising goes here, even if it turns out to be nothing.
The other docs have narrower jobs: `porting-notes.md` records how the port copes with each
of these, and `divergences.md` records where the port deliberately behaves differently.

**Entry format:** a short title, then:
- **Seen:** where and when, with the item or iteration and the problem, seed and codelet if any.
- **What:** what happens, with exact output if short.
- **Evidence:** how to reproduce it (a command, a test, a golden file).
- **Status:** `open` · `explained` · `worked around` · `won't fix` · `not a bug`, plus a line of explanation.

Kinds: 🐛 bug in the original · 🌀 anomaly (behaviour nobody can explain yet) ·
⚙️ Chez/Racket quirk · 🔗 hidden coupling · 🛸 unexplained / UFO.

---

## 🐛 Bugs in the original

### `report-error-and-halt` in `answer-justifier`
- **Seen:** iteration 3 (item 02), `eqe qeq abbba aaabaaa` seed 3, codelet 4004.
- **What:** `answer-justifier` sends `get-constituent-objects` to a letter, which doesn't
  understand it. The original prints `Ooops: ...` and calls `(reset)`, which under SWL
  abandons the run and under `scheme --script` exits 255.
- **Evidence:** `tests/golden/` contains this run, ending in a `halt` event;
  `chez_scheme/oracle/run.ss eqe qeq abbba aaabaaa --seed 3` prints `Stopped: halt`.
- **Status:** won't fix (it's the original's behaviour). The port must halt at the same
  codelet.

### `caddr` of `#f` in `transcribe-to-english`
- **Seen:** iteration 3 (item 02), `abc ccbbaa ijk` seed 3.
- **What:** a Chez error in `transcribe-to-english` (rules.ss), called from `make-rule`.
  Under the SWL REPL it would abandon the run.
- **Evidence:** `scheme --script chez_scheme/oracle/run.ss abc ccbbaa ijk --seed 3` exits 1
  with a backtrace.
- **Status:** open. The golden set uses seed 4 instead. Nobody knows whether it happened
  under 1999-era Chez, where argument evaluation order may have differed.

### A string image's `new-alpha-position-category` sends `new-start-letter`
- **Seen:** iteration 6 (item 05), reading images.ss and checking it under Chez.
- **What:** `make-string-image` answers `new-alpha-position-category` by sending each
  sub-image `new-start-letter` with the same argument (a copy-paste of the
  `new-start-letter` clause just above it). A letter image takes a non-relation argument
  as its new letter, so applying "alphabetic position → first" to a whole string makes
  every letter image's start letter the node `AlphaPos:first` itself:
  `abc` generates `(plato-alphabetic-first plato-alphabetic-first plato-alphabetic-first)`.
  `transform-image` (rules.ss:1384) sends this message for
  `plato-alphabetic-position-category` transforms, so a rule whose clause changes a whole
  string's alphabetic position would reach it.
- **Evidence:** in `tests/diff/slipnet-battery.scm`, apply
  `(tell si 'new-alpha-position-category plato-alphabetic-first fail)` to a string image
  of `abc`; the battery's `string-image-operations` test covers the message with a
  relation argument.
- **Status:** open (suspected bug, faithfully ported). Whether any golden run reaches it is
  not known yet; rules.ss (item 06) will tell.

### Latent errors: `relationship-between` of fewer than two nodes; printing a group image without a direction
- **Seen:** iteration 6 (item 05), differential battery.
- **What:** `(relationship-between (list plato-a))` takes `(1st '())` (adjacency-map gives
  no relations, and `all-same?` of `'()` is true); `(relationship-between '())` takes
  `(rest '())`. Both are Chez errors. Separately, `'print` on a group image whose direction
  is `#f` (a sameness group) sends `get-lowercase-name` to `#f`.
- **Evidence:** tests `relationship-between-one`, `relationship-between-none` in
  `tests/diff/slipnet-battery.scm` print `ERROR` under Chez and Racket alike.
- **Status:** won't fix. images.ss only calls `relationship-between` on two or more
  sub-images, and `print` is a debugging aid.

## 🌀 Anomalies

### Most documented demo seeds replay exactly; a few don't
- **Seen:** iteration 2 (item 01).
- **What:** the seeds in `demos.ss` were chosen by Marshall around 1999–2003. These still
  reproduce under Chez 10, with the same answers at the same codelet counts:
  - misc1: mmmrrj at 7794
  - misc2: abd at 1126
  - misc4: b at 453, y at 945
  - misc5: flz, dlz, hlz at 1721
  - misc9: dyz at 2257

  These don't reproduce:
  - misc3
  - the "not used" misc6–8
  - run4 (`abc abd xyz dyz` 2836825623; documented answer dyz): it gives up without an
    answer at codelet 3228
- **Evidence:** `chez_scheme/oracle/tests/demo-replay-check.ss`.
- **Status:** open. Chez's global `random` has evidently been the same 32-bit LCG for
  decades. Why the few misses? It could be the evaluation-order changes below, a different
  original version, or a lost setting.

### A string image's `reset` forgets its original direction
- **Seen:** iteration 6 (item 05).
- **What:** `make-string-image` takes a direction, but `reset` always sets it to
  `plato-right`, so a string image made with `plato-left` generates its letters reversed
  until the first reset, and in order afterwards.
- **Evidence:** battery test `string-image-left` (and `string-image-operations`).
- **Status:** not a bug. The only caller, workspace-strings.ss:30, makes every string
  image with `plato-right`.


### Every raw importance is 0 at the start of a run
- **Seen:** iteration 7 (item 06), dumping the initial workspace of every problem.
- **What:** `init-mcat` sets each letter's descriptors (`a`, `letter`, `leftmost`, ...) to
  full activation, but a description counts toward raw importance only if it is
  `relevant?`, which tests the description *type* (`LetterCtgy`, `StringPos`, ...). The
  types start inactive, so every raw importance is 0, every object in a string gets the
  same relative importance (33 in `abc`, 17 in `mrrjjj`), and the initial saliences come
  from unhappiness alone. Importance only starts to matter once the types become active.
- **Evidence:** battery tests `ws-problem-*` in `tests/diff/workspace-battery.scm`
  (`(importance 0 33)` for each letter of `abc`); `workspace-init-check.ss` checks the
  same dump after the real `init-mcat`.
- **Status:** explained (the original's behaviour, ported as is). Whether Marshall meant
  it is not known; the comment in run.ss only says `set-activation` avoids trace events.

## ⚙️ Chez / Racket quirks

### Chez doesn't evaluate arguments left to right
- **Seen:** iteration 2 (item 01).
- **What:** `(f (show 1) (show 2) (show 3))` prints `312`. `let` goes right to left, while
  inlined `+` and `cons` go left to right. Racket always goes left to right.
- **Status:** worked around. Every call site where argument order changes the order of
  random draws must be ported in Chez's order (`porting-notes.md`, `trace-format.md`).

### Chez's `map` applies its procedure in a strange order
- **Seen:** iteration 4 (item 03).
- **What:** for one or two lists, the library `map` goes from the end towards the front in
  pairs (7 elements: 7 5 6 3 4 1 2). For three or more lists it goes last to first. When
  the compiler inlines `map` on a literal or short quoted list, the order is the
  compiler's: 3 2 1 in one context, 1 2 3 in another.
- **Status:** worked around in `racket/compat.rkt` for the library case. The inlined cases
  are open; they must be checked against the goldens site by site.

### `sort`, `remq`, `for-each` and one-armed `if` differ between Chez and Racket
- **Seen:** iteration 4 (item 03).
- **What:**
  - `sort`: Chez takes `(sort pred list)` with its own merge sort, which sorts the second
    half first and gives different results with `<=`/`>=`.
  - `remq`/`remove`: Chez removes every occurrence; Racket removes only the first.
  - `for-each`: Chez returns the last application's value.
  - `if`: Chez allows a one-armed `(if test then)`.
- **Status:** worked around in `racket/compat.rkt`. The differential battery in
  `tests/diff/` checks each one against Chez.

### A raw `.zo` load ignores changes to included files; the compilation manager counts whole seconds
- **Seen:** iteration 7 (item 06), mutation checks on the ported workspace files.
- **What:** the differential runner requires engine.rkt into a fresh namespace. The
  default load handler uses `compiled/engine_rkt.zo` if it isn't older than engine.rkt
  itself, so after an edit to an included `engine/*.rktl` the battery ran the old engine
  and every mutation passed. Two more traps: the compilation manager's load handler skips
  modules whose namespace has a different module registry from the one it was created in,
  so it has to be created inside the new namespace; and it compares timestamps in whole
  seconds, so a file edited in the same second as the last compile isn't recompiled.
- **Evidence:** before the fix, changing `(list 70 30)` in formulas.rktl left
  `raco test racket/tests/workspace-diff-test.rkt` green until `raco make racket/engine.rkt`;
  after it, 2 tests fail.
- **Status:** worked around in `racket/tests/diff-runner.rkt` (compilation manager,
  created inside the namespace). Mutation scripts wait one second around each edit.

### `tanh` is not in racket/base
- **Seen:** iteration 7 (item 06), compiling workspace.ss.
- **What:** Chez has `tanh` built in; Racket has it only in racket/math, which computes
  it in Racket code and can differ from libm in the last bit.
- **Status:** worked around: compat.rkt uses Chez's own primitive through
  `ffi/unsafe/vm`'s `vm-primitive` (Racket CS's Chez is 10.3; the battery checks 500+
  values bit for bit against Chez 10.0).

## 🔗 Hidden couplings

### Model state that only a window can provide
- **Seen:** iteration 2 (item 01).
- **What:**
  - Every codelet's `run` sends `set-last-codelet-type` to a coderack window that only
    coderack-graphics.ss installs.
  - Memory descriptions call `get-normal-icon-pexp`, which only the Memory window provides.
  - `group-graphics 'erase` is called even with graphics off (groups.ss:727).
  - The reverse also happens: graphics-gated code sets model state, e.g.
    `set-shrunk-singleton?` on groups.
- **Status:** worked around in the oracle with null windows that reject unknown messages.
  It's open for the GUI items, which must show that a GUI run equals a headless run.

### Urgencies are exact rationals
- **Seen:** iteration 3 (item 02).
- **What:** 3601 of the golden codelet lines carry urgencies like `102/5`, from
  `(* (% conceptual-depth) activation)`. One stray flonum in the port would change the
  codelet choices.
- **Status:** explained. The port keeps exact arithmetic; the trace writes `"n/d"`.

### `*temperature-clamped?*` is never defined
- **Seen:** iteration 7 (item 06), compiling formulas.ss.
- **What:** formulas.ss's `update-temperature` reads `*temperature-clamped?*`, and
  answers.ss and trace.ss `set!` it, but no file defines it. It exists only because
  run.ss's `init-mcat` does `(set! *temperature-clamped?* #f)`, which Chez's top level
  allows for an unbound variable. Calling `update-temperature` before the first
  `init-mcat` would raise "variable not bound".
- **Status:** worked around: engine/pending.rktl defines it as `#f` (porting-notes.md,
  item 06); the run.ss item should keep a definition.

## 🛸 UFO sightings

(none yet)
