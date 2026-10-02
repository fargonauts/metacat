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

## 🛸 UFO sightings

(none yet)
