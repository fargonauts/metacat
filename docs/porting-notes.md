# Porting notes

Every place where the Racket port renames, restructures or modernises the
original (because Racket forces it), and every iteration-order or RNG subtlety
found while porting. One entry per change: original file and definition, what
the port does instead, and why.

## Layout
- The port lives in `racket/` (engine modules directly in the folder, GUI in
  `racket/gui/`). `racket/main.rkt` is the GUI entry point and `racket/cli.rkt`
  the headless one. Chez-isms are collected in `racket/compat.rkt`.

## The headless oracle (item 01)
How `chez_scheme/oracle/prelude.ss` gets the unmodified original to run under
Chez 10 without SWL, and what that reveals for the port.

- **Loading.** `metacat.ss` is loaded as is. The prelude defines the three
  settings it insists on (`*platform*`, `*metacat-directory*`,
  `*file-dialog-directory*`), empty modules `swl:oop` … `swl:threads` for its
  `import`s, and `extend-syntax` as a `syntax-case` macro. Fenders and `with`
  bindings refer to pattern variables as quoted data (`'formal`,
  `'(token ...)`), so after substitution they are evaluated with `eval` at
  expansion time; `with` results get the lexical context of the macro use
  (they name top-level variables such as `plato-a`, `a-b-link`). The port
  replaces all 22 macros with `syntax-rules`/`syntax-case` (item 03); the
  only fenders are the `for*` shape tests and `mcat`'s token check.
- **SWL stand-ins.** `make`/`create` build inert records, `send` ignores
  everything except `get-actual-values` on fonts (fonts.ss reads the size
  back at load time), `define-class` (sgl-interpreter.ss's `<viewport>`) is
  skipped, `swl:font-families`, `swl:screen-width`, threads and message
  queues are no-ops. None of this runs after loading except through windows.
- **Windows.** The oracle never calls `(setup)`. The window globals of
  `setup.ss` get null objects that accept only the messages a headless run
  sends and raise an error on any other, so a display query whose answer
  could feed back into the model cannot pass silently. The graphics
  switches `%workspace-graphics%`, `%slipnet-graphics%`, `%coderack-graphics%`
  are turned off. Messages still sent with the display off (in 12 runs of
  4000 codelets, 4 problems × 3 seeds, `--keep-going`):
  `*workspace-window*` garbage-collect, caching-on, flush (from
  `group-graphics 'erase`, called ungated at groups.ss:727);
  `*themespace-window*` erase-all-themes, update-thematic-pressure,
  update-graphics, set-theme-graphics-parameters-and-draw, garbage-collect;
  `*memory-window*` add-memory-icon, draw; `*trace-window*` initialize,
  add-event; `*temperature-window*` initialize, update-graphics;
  `*EEG-window*` initialize; `*slipnet-window*`, `*coderack-window*` clear;
  `*control-panel*` set-verbose-step-mode. All are commands whose results
  are ignored. The port's headless graphics interface must accept the same.
- **Model state set by the graphics.** Two places where the model calls
  something that only a window installs, even with the display off:
  1. each codelet type's private `coderack-window` (coderack.ss), set by
     `set-graphics-parameters` from coderack-graphics.ss; a codelet's `run`
     always sends it `set-last-codelet-type`. The oracle installs a null
     window in every codelet type.
  2. answer and snag descriptions in memory.ss call the icon-drawing
     procedure `get-normal-icon-pexp` that the Memory window's
     `add-memory-icon` gives them (memory-graphics.ss), e.g. in
     `update-activation`. The headless memory window gives them one that
     draws nothing.
  The reverse also exists: some graphics-gated code sets model-object
  state, e.g. `set-shrunk-singleton?` on groups (groups.ss, under
  `%workspace-graphics%`). Item 12+ must check that such state never feeds
  back into the run, or a GUI run would differ from a headless one.
- **Run control.** `break`/`quiet-break` (run.ss) wait at the REPL for
  `(go)`. `chez_scheme/oracle/run.ss` rebinds both top-level variables after
  loading: by default the run ends at the first `suspend` (answer or give-up);
  with `--keep-going` they return at once, which is what `(go)` amounts to
  (the break continuation returns `'ignore`). `--max-codelets K` is the
  original's own `*break-time*` (`runtil`). Answers are reported by wrapping
  `abstract-answer-description`, which `report-new-answer` calls once per
  answer; commentary is the original Commentary window (`make-comment-window`)
  drawing on a recording text window.
- **Output port.** syntactic-sugar.ss redefines `printf`/`newline` to write
  to the `current-output-port` captured at load time, so the prelude
  installs an unbuffered forwarding port first, muted while loading (hides
  "Metacat loaded…") and live afterwards.
- **Evaluation order** and the **RNG**: see `trace-format.md`. Chez does
  not evaluate call arguments left to right (`(f a b c)` evaluates c, a, b
  in the observed case); every site where that changes the order of random
  draws or other side effects must be ported with an explicit order.

## Traces (item 02)
- **Instrumentation from outside.** `chez_scheme/oracle/trace.ss` wraps
  top-level procedures with `set!` after loading (`build-bond`,
  `break-bond`, `build-group`, `break-group`, `build-bridge`,
  `break-bridge`, `build-description`, `update-temperature`,
  `update-slipnet-activations`, `abstract-answer-description`,
  `report-error-and-halt`); callers reach them through their top-level
  bindings, including the recursive `break-group`. Codelet procedures
  cannot be wrapped that way (`define-codelet-procedure*` hands the
  procedure to its codelet type at load time), so codelets are seen by
  forwarding `*coderack*`'s `choose-codelet`, and rules by forwarding
  `*workspace*`'s `add-rule`. The forwarding closures pass the original
  object as `self`. Note that top-down codelets receive `*workspace*` as
  their scope argument (slipnet.ss), so they hold the forwarder; only
  `tell` is ever applied to it. The port has no need for any of this: it
  emits the same events from the same places directly (through a trace
  hook that a run without tracing leaves empty).
- **Exact rationals.** Codelet urgencies are often exact non-integer
  rationals (`(* (% conceptual-depth) activation)` and friends: 3601 of the
  golden codelet lines, e.g. `102/5`). Racket's numeric tower keeps them
  exact as Chez does; the port must not introduce flonums where Chez has
  exact arithmetic, and the trace writes them as `"n/d"` strings.
- **The original fails on some runs.** Two kinds, both in the model, with
  the display off and no tracing:
  1. `report-error-and-halt` (an object gets a message it does not
     understand) prints `Ooops: ...` and calls `(reset)`; under the SWL
     REPL this abandons the run, under `scheme --script` it exits 255.
     Seen on `eqe qeq abbba aaabaaa` seed 3 at codelet 4004
     (`answer-justifier` sends `get-constituent-objects` to a letter).
     run.ss prints the same message and ends the run (`Stopped: halt`);
     the trace has a `halt` event. The golden set includes this run, so
     the port must halt at the same point.
  2. A Chez error: `abc ccbbaa ijk` seed 3, `caddr` of `#f` in
     `transcribe-to-english` (rules.ss), called from `make-rule`. Under
     the SWL REPL this too would abandon the run. The golden set avoids it
     (seed 4 instead); the oracle exits 1 with a backtrace. Whether these
     happened under the 1999 Chez is unknown (a different argument
     evaluation order could change the path).
- **Seeds that do not replay.** Besides misc3 (item 01), run4
  (`abc abd xyz dyz` 2836825623, documented answer dyz) gives up without
  an answer at codelet 3228 in the oracle. It is kept in the golden set:
  the golden records what the oracle does.
