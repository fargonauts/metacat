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
- **Status:** won't fix (it's the original's behaviour). The port halts at the same
  codelet: since iteration 11 (item 10) racket/tests/golden-test.rkt compares this run's
  whole trace, `halt` event included.

### `caddr` of `#f` in `transcribe-to-english`
- **Seen:** iteration 3 (item 02), `abc ccbbaa ijk` seed 3.
- **What:** a Chez error in `transcribe-to-english` (rules.ss), called from `make-rule`.
  Under the SWL REPL it would abandon the run.
- **Evidence:** `scheme --script chez_scheme/oracle/run.ss abc ccbbaa ijk --seed 3` exits 1
  with a backtrace.
- **Status:** open. The golden set uses seed 4 instead. Nobody knows whether it happened
  under 1999-era Chez, where argument evaluation order may have differed.
- **Update (iteration 11, item 10):** the port crashes at the same point, raising
  `caddr: contract violation ... given: #f`, after the same 1062 trace lines.
  racket/tests/golden-test.rkt runs the oracle on this problem and checks both.

### `bonds-equal?` calls `same-direction?`, which nothing defines
- **Seen:** iteration 8 (item 07), compiling bonds.ss.
- **What:** bonds.ss's `bonds-equal?` ends with `(same-direction? bond1 bond2)`; no file
  defines `same-direction?` (bonds.ss has `same-bond-direction?`). Chez's top level
  compiles the reference and would raise "variable same-direction? is not bound" if
  `bonds-equal?` were ever called; nothing calls it.
- **Evidence:** `grep -n "same-direction?" chez_scheme/original/*.ss` (one hit);
  racket/tests/engine-test.rkt checks the port's stand-in raises.
- **Status:** won't fix (latent). engine/pending.rktl defines a stand-in that raises.

### `complement-codelet-pattern` is never defined
- **Seen:** iteration 11 (item 10), compiling trace.ss.
- **What:** the Temporal Trace answers `get-complement-codelet-pattern` with the variable
  `complement-codelet-pattern`, which no file defines (trace.ss has the procedure
  `get-complement-codelet-pattern`, a different thing). Nothing sends that message, so
  Chez never notices.
- **Evidence:** `grep -n "complement-codelet-pattern" chez_scheme/original/*.ss`.
- **Status:** won't fix (latent). engine/pending.rktl makes it an identifier macro that
  raises "variable complement-codelet-pattern is not bound", as Chez would.

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

### `letter-category-mappable-objects?` compares a group with itself
- **Seen:** iteration 9 (item 08), reading bridges.ss.
- **What:** for two groups, the test is `(related? (tell object1 'get-group-category)
  (tell object1 'get-group-category))`: `object1` twice, so it is always true and any
  two groups (that have letter-category descriptions) may be mapped on LettCtgy. The
  intent was surely `object2` in the second place. The other three cases are fine.
- **Evidence:** bridges.ss line 1521; called by `horizontal-mappable-descriptions?`
  for every horizontal bridge's LettCtgy description pair.
- **Status:** won't fix (ported verbatim; the goldens depend on it).

### `init-env`'s default font is a bare SWL font, which `draw-text` cannot `tell`
- **Seen:** iteration 13 (item 12), rendering the SGL fixture.
- **What:** sgl-interpreter.ss's `init-env` binds `font` to `(swl-font sans-serif 10)`,
  an SWL `<font>` instance. The viewport's `draw-text` asks the font for its size with
  `(tell font 'get-pixel-size text)`, which only works for the closures `make-fixed-font`
  and `make-mfont` return. So a `(text ...)` drawn without a `(font ...)` binding in an
  enclosing `let-sgl` fails, unless SWL instances happen to be applicable (not checked:
  SWL is not available).
- **Evidence:** `racket/tests/sgl-test.rkt` (`check-exn` on `(draw! vp '(text "x"))`):
  the port fails with "application: not a procedure" on the `swl-font%` object.
- **Status:** open, latent. Every panel seen so far binds a font before drawing text;
  items 13–14 will show whether any panel relies on the default. Ported verbatim.

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

### Chez evaluates `append`'s second argument first
- **Seen:** iteration 8 (item 07): the codelet harness, `abc abd iijjkk` seed 3, the
  update after codelet 735 (only in a 2000-codelet run; the 400-codelet runs pass).
- **What:** a group's `get-local-density` (groups.ss) computes
  `(append (neighbors self 'choose-left-neighbor) (neighbors self 'choose-right-neighbor))`,
  and both calls can draw. Chez evaluates the right one first; Racket the left one. The
  port drew one number early, which surfaced as different slipnodes jumping to full
  activation in the next `update-slipnet-activations`.
- **Evidence:** `(define (show x) (display x) (list x))` then
  `((lambda () (append (show 'L) (show 'R))))` prints `RL` under `scheme --script`;
  racket/tests/codelet-diff-test.rkt (the `codelets-long-iijjkk-3` run).
- **Status:** worked around (groups.rktl binds the right neighbours first, marked `port:`).

### `tanh` is not in racket/base
- **Seen:** iteration 7 (item 06), compiling workspace.ss.
- **What:** Chez has `tanh` built in; Racket has it only in racket/math, which computes
  it in Racket code and can differ from libm in the last bit.
- **Status:** worked around: compat.rkt uses Chez's own primitive through
  `ffi/unsafe/vm`'s `vm-primitive` (Racket CS's Chez is 10.3; the battery checks 500+
  values bit for bit against Chez 10.0).

### `go` is the one place the original re-enters a continuation
- **Seen:** iteration 12 (item 11), porting run.ss.
- **What:** `break` and `quiet-break` capture a continuation with `continuation-point*`
  (a full `call/cc` in syntactic-sugar.ss) and then `(reset)` to the REPL; `go` resumes
  the run by calling that continuation after the REPL has moved on. Every other use of
  `continuation-point*` only escapes upwards, which is why compat.rkt implements it with
  `call/ec` (item 03). With `call/ec`, `go` would jump into a dead escape continuation.
- **Evidence:** racket/tests/run-test.rkt stops a run at codelets 150, 300 and 450 with
  the engine's own `break` and resumes it with `go`; the generator state, codelet count
  and temperature equal those of the same run never stopped.
- **Status:** worked around: run.rktl's `break` and `quiet-break` use Racket's `call/cc`
  directly (marked `port:`). Racket's full continuations reach up to the nearest prompt,
  so the caller of `run-mcat` and of `go` must each install one
  (`call-with-continuation-prompt`), and the reset handler must be set, not
  parameterized: a parameterization is part of the captured continuation, so `go` would
  bring back the first caller's dead escape. The GUI item has to respect both.

### racket/draw's unsmoothed 1-pixel lines include their end point; Tk's don't
- **Seen:** iteration 13 (item 12), the SGL fixture's dashes and polypoints.
- **What:** with smoothing `'unsmoothed`, `draw-line` with a 1-pixel pen from x=2 to
  x=8 paints 7 pixels, and a zero-length line paints one. X11 (and so Tk) draws a
  butt-capped line of width 1 from p to q over the pixels before q: 6 pixels, so a
  Tk dash "- " is 6 on, 6 off, and Tk's polypoints (lines one pixel long) are single
  pixels. Pens of width 3 already paint exactly 6. Also, `make-font #:smoothing
  'smoothed` gives subpixel (coloured) antialiasing on this desktop; `'partly-smoothed`
  is the greyscale one.
- **Evidence:** racket/tests/sgl-test.rkt checks the dash pixels along a line (fails
  with `(1 1 1 1 1 1 1 0 …)` without the fix).
- **Status:** worked around in racket/gui/sgl.rkt: a thin run (a whole path, or one
  dash) stops one pixel step short of its last point; fonts use `'partly-smoothed`.

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

### The Memory outlives a run
- **Seen:** iteration 11 (item 10), running several goldens in one Racket process.
- **What:** `init-mcat` clears the Memory's activations and highlights, not its answers
  and snags, so a second problem in the same session starts with the first problem's
  answers in the Memory (that is the point of the Memory in the GUI: answers from earlier
  runs). Running the goldens one after another in one engine gave different traces from
  the second run on (the first difference being a stale codelet count). The oracle runs
  every golden in a fresh Chez process.
- **Evidence:** racket/tests/golden-test.rkt gives each run a fresh engine (a new
  namespace); without that, only the first run matches.
- **Status:** explained; not a bug. Any batch runner (item 11's CLI, tests) must start
  each golden run with a fresh engine, or clear the Memory, to reproduce the oracle.

### Trace events and the EEG reach into graphics files
- **Seen:** iteration 11 (item 10).
- **What:**
  - Every group event's print name, which is in the trace (`"name":"[a-b-c]"`), is made
    by `group-event-pexp-text-string` from trace-graphics.ss.
  - The Temporal Trace's `display-workspace-state` sets `*fg-color*` and
    `%bridge-label-background-color%`, globals of general-graphics.ss and constants.ss.
  - workspace.ss's `initialize` sends `initialize` to `*EEG*`, an object defined only in
    eeg-graphics.ss; headless runs never read it.
- **Evidence:** `grep -n "group-event-pexp-text-string\|\*EEG\*" chez_scheme/original/*.ss`.
- **Status:** worked around: engine/pending.rktl has an early verbatim copy of
  `group-event-pexp-text-string` (pure); racket/tests/golden-harness.rkt gives a null
  `*EEG*`. The GUI items move them back.

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
- **Update (iteration 12, item 11):** run.ss does the same with
  `*initial-slipnode-unclamp-time*`: `run-mcat` compares the codelet count with it,
  `init-mcat` and `clamp-initial-slipnodes` `set!` it, and no file defines it. Racket
  rejected run.rktl at compile time ("unbound identifier"). engine/pending.rktl now
  defines both, as never-defined names (not pending on any item).

### Fonts the model reads but nothing defines
- **Seen:** iteration 8 (item 07), compiling groups.ss.
- **What:** groups.ss's `set-graphics-parameters` reads `%group-letter-category-font%`
  and `%relevant-group-length-font%`, which exist only once the Workspace window's
  initialisation `set!`s them (workspace-graphics.ss). Like `*temperature-clamped?*`,
  they rely on Chez's top level accepting `set!` of an unbound variable.
- **Status:** worked around: engine/pending.rktl defines them as `#f`; the Workspace
  panel item must define them.

### Concept mappings are only made through bridges
- **Seen:** iteration 8 (item 07).
- **What:** bonds.ss and groups.ss make concept mappings only in
  `get-incompatible-bridge`, which returns early without a bridge. With bridge codelets
  disabled, a run never makes one, so the codelet harness cannot exercise
  concept-mappings.ss; its battery tests the mappings directly.
- **Status:** explained. Since item 08, bridges make them in runs, and
  tests/diff/bridge-battery.scm checks them (`new-cms` events, each bridge's mappings).

### Bridges call themes.ss on every bridge
- **Seen:** iteration 9 (item 08).
- **What:** although bridges.ss loads before themes.ss, every bridge calls themes.ss's
  `bridge-type->theme-type` when it is made, `bridge-theme-compatibility-sigmoid` (via
  `get-thematic-compatibility`) whenever its strength is updated, and bridge-builder's
  `boost-themespace-activations` calls `descriptions-affect-themespace?` and messages
  `*themespace*` and `*themespace-window*` for every bridge built (the window message
  is not gated by `%workspace-graphics%`; the oracle's null window absorbs it). With no
  active theme the strength only depends on `(weighted-average '() '())` = 0 and
  sigmoid(0) = 0. Building a bridge also calls trace.ss's
  `monitor-new-concept-mappings`.
- **Evidence:** bridges.ss lines 42, 270–313, 1352, 1416; tests/diff/bridge-battery.scm
  records the boost calls (`add-theme`, `update-dominant-themes`, `themespace-window
  update-graphics`) and the monitor calls (`new-cms`).
- **Status:** worked around: engine/pending.rktl has early verbatim copies of the four
  pure themes.ss helpers (item 10 moves them back); `monitor-new-concept-mappings` is a
  settable stand-in until trace.ss is ported.

### Dead code in bridges.ss
- **Seen:** iteration 9 (item 08).
- **What:** `propose-singleton-group` and `try-to-propose-singleton-group` are never
  called (the comment in `build-bridge` describing singleton-group proposals has no code
  under it). `calculate-external-strength` computes `(round (* (min 100 total-support)))`,
  a one-argument `*`, harmless.
- **Status:** not a bug; ported verbatim.

### Rules and answers lean on later files and on a REPL abbreviation
- **Seen:** iteration 10 (item 09).
- **What:** rules.ss and answers.ss load before themes.ss, trace.ss and the graphics
  files, yet the model reaches into them on every rule and answer:
  - `make-rule` calls `transcribe-to-english`, which calls general-graphics.ss's
    `find-next-space-position`;
  - `set-translated-rule-information` calls the Workspace's `get-real-object`, which
    calls trace.ss's `equivalent-workspace-objects?`;
  - answers.ss's theme phrases compare a theme's relation with `diff`. That is one of
    themes.ss's REPL abbreviations (`top`, `len`, `iden`, … for typing commands such as
    `(set-themes top lcat same 100)`), and it is `#f`, the "different" relation;
  - the slippage log's `get-highlight-color` reads four constants.ss colours.
  Also, `process-snag` clamps the temperature (`*temperature-clamped?*`), and only the
  Trace's `undo-snag-condition` (or a clamp's undo) unclamps it. Without a working Trace,
  every run after its first snag stays at temperature 100 and never posts an
  answer-finder.
- **Evidence:** rules.ss line 1739, workspace.ss line 407 (`get-real-object`),
  answers.ss lines 373–394 and 902 (`theme-abstractness`), trace.ss lines 188–196; `tests/diff/rule-battery.scm` (its fake Trace ends
  snag periods for this reason).
- **Status:** worked around. engine/pending.rktl has early verbatim copies of the pure
  definitions (`find-next-space-position`, `equivalent-workspace-objects?`, `diff`),
  which items 10 and 12 move back; the colours are `#f` stand-ins until the GUI items.

### Rules are never removed
- **Seen:** iteration 10 (item 09).
- **What:** the Workspace understands `delete-rule`, but nothing sends it. The breaker
  leaves rules out of its candidates (`filter-out rule?`, breakers.ss line 26), so every
  rule built during a run stays in the Workspace until the next problem.
- **Evidence:** `grep -n "'delete-rule" chez_scheme/original/*.ss` finds nothing;
  `tests/diff/rule-battery.scm`'s traces contain no broken rule in 109 runs.
- **Status:** not a bug, apparently by design; ported verbatim.

### Erasing draws: the canvas only grows until a `clear`
- **Seen:** iteration 13 (item 12), porting sgl-interpreter.ss.
- **What:** `(erase color pexp)` and `erase!` don't delete anything: they draw pexp
  again in the erase colour, as new Tk items tagged `eraser`. A window that erases and
  redraws (the Workspace's structures, the Coderack's bars) keeps adding items until the
  next `(clear)` or `delete`. The tag `eraser` also replaces the caller's tag.
- **Evidence:** tests/diff/sgl-battery.scm's `erase-*` tests (all items carry
  `'eraser`); racket/gui/sgl.rkt's viewport keeps them in its display list.
- **Status:** not a bug; ported verbatim. If long runs in the GUI get slow, this is the
  first place to look.

## 🛸 UFO sightings

(none yet)
