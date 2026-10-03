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
- **Update (iteration 15, item 14):** all panels are ported and every `text` they draw
  has a `font` binding around it; 109 golden runs with every window attached and 48
  pictures never reach the default.

### `relation-names-pexp` is never defined (theme-graphics.ss)
- **Seen:** iteration 15 (item 14), compiling theme-graphics.ss in Racket.
- **What:** a theme panel (`make-panel`) answers `get-relation-names-pexp` with
  `relation-names-pexp`, but its variable is `relation-names-pexps` (plural). Chez
  compiles the reference to an unbound top-level variable; Racket rejects the module.
  Nothing sends `get-relation-names-pexp`.
- **Evidence:** `grep -n "relation-names-pexp\b" chez_scheme/original/theme-graphics.ss`
  (line 510).
- **Status:** worked around, latent. racket/gui/theme-graphics.rktl defines
  `relation-names-pexp` as an identifier macro that raises Chez's error ("variable
  relation-names-pexp is not bound"), as engine/pending.rktl does for
  `complement-codelet-pattern`.

### The Memory window's first icon spacing is dead code
- **Seen:** iteration 15 (item 14), a mutation check.
- **What:** `new-memory-window` computes `memory-icon-spacing` (and `next-y`) in its
  `let*`, but `make-memory-window` always sends `initialize` next, which recomputes both
  with the same formula. Changing the first one changes nothing.
- **Evidence:** memory-graphics.ss lines 82–86 and 119–122; the mutation table in
  porting-notes.md, item 14.
- **Status:** not a bug (harmless redundancy); ported verbatim.

## 🌀 Anomalies

### Most documented demo seeds replay exactly; a few don't
- **Seen:** iteration 2 (item 01). Revised in iteration 17 (item 16), which compared every
  demo with the dissertation's Chapter 5.
- **What:** the seeds in `demos.ss` were chosen by Marshall around 1999–2003. Under Chez 10
  most of them still give the same answers at the same codelet counts:
  - misc1: mmmrrj at 7794
  - misc2: abd at 1126
  - misc4: b at 453, y at 945
  - misc5: flz, dlz, hlz at 1721
  - misc9: dyz at 2257
  - Run 2: mrrkkk at 1747
  - Run 3: uyz at 3163
  - Run 4: no answer; it gives up at 3228. Item 01 listed run4 as not replaying because
    demos.ss names the answer dyz, but the dissertation's Run 4 never finds the rule
    either, and a Jootser ends it at 3228 (p. 226). So it does replay.
  - Run 5: gives up at 4493
  - Run 7: wyz at 2170
  - Figs. 5.7/5.8: ijll at 1172, hjkk at 733

  These don't reproduce:
  - misc3, and the "not used" misc6–8;
  - Run 6: aaabccc at 5976, where the dissertation gives up at 6196;
  - Run 8: qeeeq at 1013, where the dissertation never answers and a Jootser ends the run
    at 5933;
  - fig5.5-bottom: qxeeq, where the figure shows qeeq;
  - the eqe-qeeeq demo: it answers qcccb;
  - fig5.11: xyd, where the dissertation shows yyz. The dissertation says that run
    continues the one in Fig. 4.12, so a seed alone can't reproduce it.

  Also, fig5.4-bottom (seed 175910650) and fig5.5-bottom (seed 4109591222) both stop at
  codelet 2899, with different traces and different answers (qeeq and qxeeq). This looks
  like a coincidence.
- **Evidence:** `chez_scheme/oracle/tests/demo-replay-check.ss` (the original);
  `racket/tests/demos-test.rkt` (the port); the table in `docs/demos.md`; the goldens of
  every demo seed.
- **Status:** open. Chez's global `random` has evidently been the same 32-bit LCG for
  decades, and the replaying runs include long ones (misc1 runs 7794 codelets), so most of
  the program's draws are unchanged. The misses could come from code changes between the
  dissertation (1999) and version 1.2, from changes in Chez's argument evaluation order,
  or from a lost setting.

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
- **Update (loop0002, item 01):** a 2-binding `let` *inside a lambda* went left to right
  under `scheme --script`: `((lambda () (let ((a (show 1)) (b (show 2))) 0)))` prints
  `12`, while the documented top-level `let` prints `21`. In the same script, a 3-argument
  call printed `312` both at top level and inside a lambda. The order depends on context,
  so a site can't be read off a rule; docs/python-translation-plan.md lists the known
  sites, which Python (left to right, like Racket) must order by hand.

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
- **Update (iteration 14, item 13):** the same trap across modules. headless.rkt's
  `run-problem` gained a keyword argument, but `raco test racket/` and plain `racket`
  (cli-test.rkt runs `racket racket/cli.rkt`) loaded the old `cli_rkt.zo`, compiled
  against the old headless.rkt: "instantiate-linklet: mismatch; reference to a variable
  that is not exported". The gate failed with 39 failures in cli-test.rkt.
  tests/run-tests.sh now runs `raco make` on every module of racket/ before
  `raco test`. A mutation restored in the same second as the mutated compile also left
  one stale `.zo` (bridge-graphics.rktl); the mutation script now waits before
  restoring too.

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
  dash) stops one pixel step short of its last point; fonts used `'partly-smoothed`
  until item 13, and are `'unsmoothed` since (see "Erasing antialiased text leaves
  fringes").

### Chez's `record-case` ignores extra arguments; the port's raised
- **Seen:** iteration 14 (item 13), the first run with the Workspace window attached.
- **What:** the Temporal Trace (trace.ss lines 442 and 473–478) sends the Workspace
  window `(draw-string-letters string 'answer)`, with a tag the window's method
  `(draw-string-letters (string) ...)` doesn't take. Chez's `record-case` binds the
  formals with `car`/`cdr` (`(expand '(record-case r [(a) (x) x]))` shows it), so the
  extra argument is ignored and too few arguments raise "car: () is not a pair". compat's
  `record-case` applied a `lambda`, which raised an arity error at the first answer of
  every run once workspace graphics were on.
- **Evidence:** racket/tests/compat-test.rkt (extra, missing and rest arguments);
  without the fix, racket/tests/workspace-view-test.rkt (now views-test.rkt) fails on every run that reaches
  an answer.
- **Status:** worked around. compat's `record-case` binds as Chez does (item 13).

### The graphics erase text by overpainting, which leaves fringes around antialiased text
- **Seen:** iteration 14 (item 13), the first renders of the Workspace window.
- **What:** to erase, the original draws the same pexp again in the background colour.
  Over antialiased text this leaves grey fringes: a ghost "?" where the answer's letters
  went, and smears after concept mappings whose font changed from irrelevant (italic) to
  relevant (bold italic).
- **Evidence:** set `#:smoothing 'partly-smoothed` in racket/gui/fonts.rkt and run
  `racket racket/tests/views-harness.rkt mrrjjj-answer /tmp/a.png`.
- **Status:** worked around. Text is drawn aliased, as X11's core fonts drew it in the
  dissertation's screenshots (divergences.md).

### Image-mode text boxes are narrower than italic glyphs
- **Seen:** iteration 14 (item 13), the bridge labels (yellow boxes) in 4× crops.
- **What:** `draw-text` sizes an image-mode text's background box from the text's
  width. Italic digits overhang it by a pixel or two on the right.
- **Evidence:** the snapshots in racket/tests/snapshots/workspace-*.png.
- **Status:** not a bug, as far as anyone can tell: Tk sized the box the same way. Item 12
  ported sgl-interpreter.ss's arithmetic verbatim. Kept.

### GTK ignores Xvfb when `WAYLAND_DISPLAY` is set
- **Seen:** iteration 16 (item 15), the first GUI runs under `xvfb-run`.
- **What:** the owner's session is Wayland (`WAYLAND_DISPLAY=wayland-0`). GTK prefers
  Wayland over `DISPLAY`, so `xvfb-run racket ...` opened the windows on the owner's
  screen instead of the virtual display. The root window of Xvfb had no children and a
  screen grab was black. Three short scratch runs (a few seconds each) showed windows on
  the owner's screen before this was noticed.
- **Evidence:** `env | grep WAYLAND`; `xwininfo -root -tree` inside `xvfb-run` lists no
  windows unless `WAYLAND_DISPLAY` is unset.
- **Status:** worked around. Every GUI run uses
  `env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a ...` (tests/run-tests.sh,
  tests/gui-screenshot.rkt's header), and racket/gui-tests/control-panel-test.rkt
  refuses to run while `WAYLAND_DISPLAY` is set.

### A racket/gui canvas's `on-size` does not see its scrollbars
- **Seen:** iteration 16 (item 15), the Commentary window.
- **What:** showing a manual scrollbar shrinks a canvas's client area, but `on-size`
  reports the whole canvas, so no resize happened. The Commentary's first paragraph ran
  under its vertical scrollbar. Also, a canvas's minimum client size counts only the
  scrollbars shown when it is set.
- **Evidence:** the screenshot steps in PROGRESS.md (iteration 16).
- **Status:** worked around in racket/gui/gui.rkt's `screen-host%`: the refresh tick
  compares the client size with the viewport's, and `set-resizable!` shows the
  scrollbars and sets the minimum size again before the window becomes resizable.

### The SWL message-queue stand-in deadlocked the GUI thread
- **Seen:** iteration 16 (item 15), the first on-screen run.
- **What:** views.rkt's stand-in for SWL's `thread-receive-msg` took the semaphore and
  the message in two steps. When the resize listener thread ran between them, the
  resize handler (in the GUI thread, inside `critical-section`) saw a waiting message,
  waited on the semaphore, and blocked forever.
- **Evidence:** a GUI run hung with a backtrace in `thread-receive-msg` under
  `critical-section`.
- **Status:** explained and fixed: a receive is now atomic, and `critical-section` runs
  in Racket's atomic mode.

### `dynamic-require` of a runtime path breaks under `raco exe`
- **Seen:** iteration 17 (item 16), building the standalone program.
- **What:** racket/main.rkt loaded the GUI with `(dynamic-require gui-path 'setup)`, where
  `gui-path` came from `define-runtime-path`. That works with `racket`, but `raco exe` does
  not embed a module that is only reached that way. The distributed `metacat` then exits
  with status 1 as soon as it opens the GUI. Headless runs were not affected, because they
  never reach that module.
- **Evidence:** with HEAD's racket/main.rkt, `racket/gui-tests/dist-test.rkt` fails 2 of 3
  checks ("the GUI is still up": actual 1).
- **Status:** worked around. main.rkt and racket/metacat.rkt use `lazy-require`, which
  registers the module with `raco exe` and still loads racket/gui only when the GUI starts.

### A process in a bubblewrap sandbox outlives its killed `bwrap`
- **Seen:** iteration 17 (item 16), in the first version of dist-test.rkt.
- **What:** killing `bwrap` left the sandboxed GUI running, re-parented to the session.
  It kept the test's stdout pipe open, so the test hung on reading it.
- **Evidence:** `ps` showed `/opt/metacat/bin/../lib/plt/gracketcs-8.18 ...` with parent
  4284 (the session) after the test had killed bwrap.
- **Status:** worked around. The test passes `--die-with-parent --unshare-pid` to bwrap.

### Chez's printer rounds a halfway last digit up; Python's `repr` rounds it to even
- **Seen:** loop0002 iteration 3 (item 02), `number->string-bits` and `-decades` in
  python/oracle/batteries/chez-battery.scm.
- **What:** both print the shortest digits that read back to the double. When the double
  lies exactly halfway between the two shortest candidates, Chez takes the upper one and
  Python the even one: 1586243275893042.25 prints as `1.5862432758930423e15` in Chez and
  `1.5862432758930422e15` in Python (`repr`), and 71684848459136.625 as `...136.63` and
  `...136.62`. Racket happened to agree with Chez on every value its tests printed.
- **Evidence:** `python/fixtures/chez/*number-%3Estring-ties.txt` (17 ties among 5,240 doubles);
  `python3 -c "print(repr(1586243275893042.25))"`.
- **Status:** worked around. `chez._flonum_digits` starts from `repr` and moves a halfway
  last digit up, keeping it if it still reads back. `test_number_to_string_ties`.

### Chez writes non-ASCII symbol characters as `\xHH;` unless they are R6RS constituents
- **Seen:** loop0002 iteration 3 (item 02), `write-symbols`.
- **What:** in a symbol, `write` prints a character above 127 as is only if its Unicode
  category is Lu, Ll, Lt, Lm, Lo, Mn, Nl, No, Pd, Pc, Po, Sc, Sm, Sk, So or Co (plus Nd,
  Mc, Me after the first character). U+0080–U+00A0, U+00AB `«`, U+00AD, U+00BB `»`,
  U+2028, U+2029 and U+FEFF become `\x80;` and so on. racket/compat.rkt writes every
  non-ASCII character as is. The model's symbols are ASCII, so it never mattered.
- **Evidence:** `python/fixtures/chez/042-write-symbols.txt`.
- **Status:** worked around in chez.py (`unicodedata.category`). Racket's difference
  is harmless and left alone (racket/ is frozen).

### Exact 0 is the identity of `+` and `-`: `(+ 0 -0.0)` is `-0.0`
- **Seen:** loop0002 iteration 3 (item 02), `arith-add`, `arith-sub`, `arith-nary`.
- **What:** Chez returns the other operand when one is exact 0. So `(+ 0 -0.0)` is
  `-0.0`, `(- 0 0.0)` is `-0.0` (negation), and `(max 0 -0.0)` and `(min 0 -0.0)` are
  `-0.0`. Python gives `0.0` for `0 + -0.0` and `0 - 0.0`. With `(* 0 x)` and `(/ 0 x)`
  (exact 0 for any flonum `x`, even `+inf.0` or `0.0`), this is where Python's mixed
  arithmetic differs from Chez's.
- **Evidence:** `python/fixtures/chez/004-arith-add.txt` and the other `arith-*` tables;
  the `-inline` variants agree with the procedure calls.
- **Status:** worked around: `chez.add`/`sub`/`mul`/`div`/`max_`/`min_`. Only the sign
  of a zero changes, and that only shows when it's printed or divided by.

### Chez's `expt`: exact roots only for 1/2, exact results for exact 0 and 1 bases
- **Seen:** loop0002 iteration 3 (item 02), `expt-table`, `expt-extra`, `expt-model`.
- **What:** an exact 0 power gives exact `1` (`(expt 0.0 0)` → `1`). An exact base to an
  exact integer power is exact. A power of `1/2` is `sqrt` (`(expt 4 1/2)` → `2`), but
  other exact roots are inexact (`(expt 8 1/3)` → `2.0`, `(expt 4 3/2)` → `8.0`). An exact
  1 base gives exact `1` for any power. An exact 0 base gives exact `0` for a positive
  power (`(expt 0 0.95)` → `0`), `1.0` for `0.0`, and an error for a negative power.
  `(expt 0.0 -1)` is `+inf.0`, where Python raises `ZeroDivisionError`. A negative base to
  a non-integer power is `exp(p log b)` (complex). Otherwise it's libm's `pow`, as Python's
  `**` (`(expt 1.1 27)`, not repeated multiplication).
- **Evidence:** `python/fixtures/chez/*expt*`.
- **Status:** explained; chez.py's `expt` follows it. The model's `(expt strength 0.95)`
  meets the exact-0 case whenever a strength is 0.

### `set-top-level-value!` binds an unbound name in Chez
- **Seen:** loop0002 iteration 3 (item 02), `top-level-values`.
- **What:** in Chez's interaction environment, `(set-top-level-value! 'x 4)` of an
  unbound `x` binds it, while `top-level-value` of an unbound name raises.
  racket/compat.rkt raises for both. The model only sets names it has defined.
- **Status:** explained; chez.py does as Chez.

### A bad literal `format` string makes Chez's compiler warn, which fails a whole battery test
- **Seen:** loop0002 iteration 3 (item 02), writing chez-battery.scm.
- **What:** `(format "~a")`, `(format "x" 1)` and `(format "~q" 1)` with literal strings
  draw "Warning in compile: too few arguments for control string", even inside a handler.
  diff-eval.ss's handler sees the warning condition and prints `ERROR` for the test.
  Called through a variable (`c:format`), they raise at run time as expected.
- **Status:** worked around in the battery.

### Python raises where IEEE arithmetic (and Chez) give an infinity
- **Seen:** loop0002 iteration 3 (item 02).
- **What:** `1 / 0.0`, `0.0 ** -1`, `math.log(0.0)` and `float(10**400)` raise in
  Python. Chez gives `+inf.0`, `+inf.0`, `-inf.0` and `+inf.0`. `math.exp(1000)` raises
  `OverflowError`. Also `round(math.inf)` raises, where Chez's `round` returns `+inf.0`.
- **Status:** worked around in chez.py (`div`, `expt`, `log`, `inexact`, `exp`, `round_`).
  Plain Python operators on model floats must not meet these cases.

### Python interns only identifier-like string constants, so `'invalid-message-indicator` needs one shared object
- **Seen:** loop0002 iteration 4 (item 03), writing objects.py.
- **What:** two modules that each write the literal `"invalid-message-indicator"` get two
  different objects: `a.X is b.Y` is `False`. Python interns string constants
  automatically only when they look like identifiers, and the hyphens rule that out. The
  same goes for a symbol built at run time (`"-".join(...)`). `tell` and `delegate` test
  the indicator with `is`, so a producer that spells it out would not halt where Chez
  halts.
- **Evidence:** `python3 -c 'import a, b; print(a.X is b.Y)'` with the literal in a.py and
  b.py prints `False`.
- **Status:** worked around: every producer uses `objects.INVALID` (a `sys.intern`ed
  constant), and other symbols are compared with `==`, never `is`
  (docs/python-translation-plan.md, "eq? and identity").

### Python's `complex` cannot hold Chez's exact complex numbers
- **Seen:** loop0002 iteration 4 (item 03), utilities battery `coords`.
- **What:** `(coord 3 4)` (`make-rectangular`) is the exact `3+4i` in Chez, and
  `(x-coord c)` gives back the exact 3. Python's `complex` holds two floats. Also,
  `(make-rectangular 1.5 0)` is the real `1.5` (an exact zero imaginary part vanishes),
  `(make-rectangular 1 2.0)` is `1.0+2.0i`, and `(imag-part 1.5)` is the exact `0`.
- **Evidence:** fixtures `coords` and `number->string-exact` of the utilities battery.
- **Status:** worked around: `chez.ExactComplex` and `chez.make_rectangular`,
  `real_part`, `imag_part`, printed by `number_to_string`. Arithmetic on coordinates
  (the graphics: `magnitude`, `+` on coords) isn't there yet; the graphics items add it.

## 🔗 Hidden couplings

### The graphics and rules.ss tell strings from symbols
- **Seen:** loop0002 iteration 4 (item 03), the grep that docs/python-translation-plan.md
  asked item 03 to repeat.
- **What:** the plan makes symbols and Scheme strings both Python `str`, because the model
  never tells them apart. It does in a few places. `string?` picks strings out in
  sgl-interpreter.ss:386, 398 and 432, general-graphics.ss:418, fonts.ss:93 and gui.ss:363
  (text versus symbolic arguments, colour names versus colour objects, font faces).
  rules.ss:269 runs `(filter-out symbol? (flatten rule-clauses))`, so a string in a
  rule clause would survive where a symbol is dropped. `symbol?` at answers.ss:140,
  themes.ss:595, trace.ss:83, justify.ss:242/245 and gui.ss:743/749 only tells a symbol
  from a list or a number, which `str` handles. There is still no `eq?` on a string
  literal, and `~s` is only used in run.ss's `no-prompt` error and fonts.ss's debugging
  output.
- **Status:** open. The items that translate those files must keep the distinction there:
  `chez.String` for the strings those tests see, or an explicit tag.

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
- **Update (iteration 15, item 14):** the engine now has these parts of the graphics
  files, verbatim: `group-event-pexp-text-string` (engine/trace-graphics.rktl),
  `relation-name` (engine/theme-graphics.rktl, used by trace.ss's `print-pattern`) and
  the EEG object with `%EEG-table%` (engine/eeg-graphics.rktl). The early copies and the
  null `*EEG*` are gone: headless runs use the real EEG, as the oracle does. The EEG
  records values only when `%workspace-graphics%` is on, and the goldens with views
  attached show that recording changes nothing.

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
- **Update (iteration 18, item 17):** still so. engine/pending.rktl now holds only the
  original's never-defined names (these two, `same-direction?`,
  `complement-codelet-pattern`); every file is ported.

### Fonts the model reads but nothing defines
- **Seen:** iteration 8 (item 07), compiling groups.ss.
- **What:** groups.ss's `set-graphics-parameters` reads `%group-letter-category-font%`
  and `%relevant-group-length-font%`, which exist only once the Workspace window's
  initialisation `set!`s them (workspace-graphics.ss). Like `*temperature-clamped?*`,
  they rely on Chez's top level accepting `set!` of an unbound variable.
- **Status:** worked around: engine/pending.rktl defines them as `#f`; the Workspace
  panel item must define them.
- **Update (iteration 18, item 17):** since item 13 they are view globals,
  `#f` in engine/view-globals.rktl until views.rkt's workspace-graphics.rktl `set!`s
  them through `set-global!`.

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
- **Update (iteration 18, item 17):** done in item 10: the helpers are in
  engine/themes.rktl and `monitor-new-concept-mappings` in engine/trace.rktl, the
  original's own definitions; pending.rktl has neither.

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
- **Update (iteration 18, item 17):** done: `diff` and `equivalent-workspace-objects?`
  are in engine/themes.rktl and engine/trace.rktl (item 10), `find-next-space-position`
  in engine/general-graphics.rktl (item 13), and the colours are view globals
  (engine/view-globals.rktl), installed by racket/gui/views.rkt.

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

### Workspace graphics write graphics state into model objects, but draw no random numbers
- **Seen:** iteration 14 (item 13).
- **What:** with `%workspace-graphics%` on, the model calls the graphics files directly.
  Groups compute their graphics coordinates (`set-graphics-parameters`), and bridges
  number their labels (`new-bridge-label-number`) and set concept-mapping pexps.
  Images store group pexps (images.ss line 207). Answers lay out the translated string
  (`init-translated-string-graphics`). The Memory makes answer-description pexps
  through the Trace (`make-answer-description-pexp`, which draws on the Workspace window
  in cache mode and takes the cached pexp back). The EEG records values each update.
  Groups and bridges also keep a `drawn?` flag that only the graphics set. A run could
  diverge if any of this drew from the generator or changed what the model reads.
- **Evidence:** racket/tests/views-test.rkt (workspace-view-test.rkt in item 13): all 109
  golden runs give identical traces with the Workspace window attached, and a mutation that makes `bridge-graphics`
  draw one random number makes them differ.
- **Status:** explained: none of it draws or feeds back into the model's choices. The
  ported graphics are verbatim, so this also holds for the original.
- **Update (iteration 15, item 14):** the same holds with every window attached and every
  graphics switch on. The Slipnet, Coderack, Temperature and EEG windows redraw at every
  update. The Coderack window recomputes the selection probabilities, and the codelet
  types keep its slot pexps. Themes keep their panel. Trace events and Memory answers
  keep their icons and bounding boxes. All 109 traces stay identical, and a mutation
  that makes the Slipnet window's `update-graphics` draw one random number changes
  all 109.

### `update-rule-pexps!` mutates pexps shared with the rules
- **Seen:** iteration 14 (item 13), porting rule-graphics.ss.
- **What:** on a resize, the Workspace window recomputes the rule pexps inside each
  answer and snag description in the Memory, in place with `set-car!`. Those
  `(rule ...)` cells are shared with the rules' own pexps, which the window recomputes
  just before with `initialize-rule-graphics`, so in the original both end up new.
- **Evidence:** rule-graphics.ss line 77; workspace-graphics.ss `update-rule-pexps`.
- **Status:** worked around. Racket's pairs are immutable, so the port's
  `update-rule-pexps!` returns an updated copy and the window stores it in the
  description. tests/diff/graphics-battery.scm checks the result against the
  original's mutated pexp.

### One resize queue for every window
- **Seen:** iteration 16 (item 15), at setup.
- **What:** general-graphics.ss's resize handler drops a waiting resize from the single
  `*resize-message-queue*` before queueing its own, whichever window the waiting one
  was for. When several windows get a configure at once, only the last one redraws.
  Under Tk this happened only during user drags. In the port, every scrolling window
  got one at startup as its scrollbars appeared, and the Commentary kept its creation
  width and scroll position.
- **Evidence:** eprintf in the handler and listener showed 5 handler calls and 2 thunks.
- **Status:** worked around: scrollbars are shown before the windows become resizable,
  so the frames grow around them and the windows keep their sizes. The original's
  queue is unchanged.

### Verbose mode reached an unregistered `format-slipnode` (port bug, fixed)
- **Seen:** iteration 18 (item 17), auditing porting-notes.md against the code.
- **What:** utilities.ss's `reveal-obj` names slipnodes with rules.ss's
  `format-slipnode`. utilities.rkt is a module loaded before the engine, so it looks the
  name up with `(top-level-value 'format-slipnode)`. Item 03's notes said the rules port
  must register it, and item 09 didn't. The only caller is jootsing.ss, inside a
  `vprintf`: `(reveal entry)`, evaluated only when `%verbose%` is on. So the 109 goldens,
  which run with verbose mode off, never reached it, but a jootser in the GUI with
  Options > Verbose mode on (or in verbose step mode) would have raised "not a top-level
  value" in the port, where the original prints `(<stringpos> <identity>) entry: ...`.
  No test had ever turned verbose mode on.
- **Evidence:** `racket racket/cli.rkt a b z --seed 1 --max-codelets 1000 --keep-going
  --verbose` against the oracle's run.ss with the same arguments (racket/tests/cli-test.rkt);
  the `reveal-slipnodes` test in tests/diff/slipnet-battery.scm. Both failed before the
  fix.
- **Status:** explained and fixed: racket/engine.rkt registers `format-slipnode` after
  including rules.rktl (marked `port:`). Verbose output of all 109 golden runs (1.55
  million lines; 10 runs reach the `reveal` line) is now byte-identical to the oracle's.
  Both run.ss and cli.rkt got a `--verbose` option for this.

### racket/draw imports a racket/gui module
- **Seen:** iteration 18 (item 17), writing racket/tests/no-gui-test.rkt.
- **What:** walking the transitive imports of racket/gui/sgl.rkt finds
  `racket/gui/dynamic`, imported by racket/draw's PostScript dc. It is a small module in
  the base collection that only asks whether racket/gui is loaded; it does not load it.
- **Evidence:** racket/tests/no-gui-test.rkt (it exempts that one module).
- **Status:** not a bug. The engine and the headless driver reach neither racket/gui nor
  racket/draw; the views modules reach racket/draw and, through it, only that module.

## 🛸 UFO sightings

(none yet)
