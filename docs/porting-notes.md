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

## The compatibility layer (item 03)
`racket/compat.rkt` (syntactic-sugar.ss plus Chez built-ins) and
`racket/utilities.rkt` (utilities.ss, line for line). Engine modules require
both; their bindings shadow racket/base's. Everything below is checked
against Chez by `racket/tests/utilities-diff-test.rkt`, which evaluates
`tests/diff/utilities-battery.scm` (196 tests) both under Chez with the
whole original loaded (`chez_scheme/oracle/diff-eval.ss`) and in Racket, and
compares the outputs line for line.

**Shadowed or added built-ins** (each reproduces Chez 10):
- `random`, `random-seed`: Chez's generator (trace-format.md). Racket's
  `random` is never used. Bignum ranges above 2^60−1 are rejected (Metacat
  never draws with them).
- `if`: one-armed `(if test then)` is legal in Chez and common in the
  original; compat's `if` adds `(void)` as the missing arm.
- `map`: **Chez's application order.** For one or two lists Chez's library
  map applies the procedure to pairs of elements from the end towards the
  front (7 elements: 7 5 6 3 4 1 2); for three or more lists, last to
  first. Racket goes first to last. This matters wherever the mapped
  procedure draws random numbers or has other effects (`tell-all`,
  `delegate-to-all`, …).
  *Caveat for porting call sites:* Chez's compiler inlines `map` when a
  list argument is a literal `(list …)` or a quoted list of at most four
  elements, and the inlined order is the compiler's (observed: 3 2 1 for a
  quoted 3-element list in one context, 1 2 3 in another). Such sites with
  side-effecting procedures must be checked against the goldens.
- `for-each`: Chez returns the value of the last application (void for an
  empty list); the original's `for*` loops pass that value on.
- `sort`: `(sort pred list)` with Chez 10's own algorithm (s/5_6.ss):
  below 25 elements a top-down list merge sort that sorts the *second* half
  first, otherwise Shivers's opportunistic vector merge sort. The battery
  compares results for non-strict predicates (`<=`, `>=`) and the sequence
  of predicate calls, both of which differ from Racket's `sort`.
- `remq`, `remv`, `remove`: remove *every* occurrence (Racket's `remq` and
  `remove` remove only the first). The model calls `remq` about 50 times.
- `1+`, `-1+`.
- `number->string`, `display`, `write`, `format`, `fprintf`, and
  syntactic-sugar.ss's `printf`/`newline`: Chez's printer. Flonums are
  positional when the exponent of the leading digit is in (−4, 10) and
  `d.ddde<exp>` otherwise (`1e-4`, `1e10`, `1.234567890125e11`,
  `1000000000.0`), with Chez's `|n` precision suffix on subnormals.
  `display` abbreviates `(quote x)` as `'x`, `write` does not. Symbols are
  written with Chez's `\xHH;` escapes (`\x31;+`, `a\x20;b`), characters with
  Chez's names (`#\nul`, `#\delete`), strings with Chez's escapes.
  Procedures print as `#<procedure name>` (Chez also prints source
  positions for anonymous ones; not reproduced, the model never prints
  procedures). Directives: `~a ~s ~% ~n ~~`, the only ones Metacat uses.
  `printf` writes to the current output port at the time of the call, where
  syntactic-sugar.ss captured the port current when it was loaded.
- `error`: Chez's `(error who format-string arg …)`, `who` may be `#f`.
- `record-case`: dispatches with `case` on `(car exp)`, binds the formals
  with `apply`.
- `reset`/`reset-handler`: Chez's `(reset)` abandons the computation (the
  REPL's reset handler; under `--script` the process exits 255). compat's
  default handler raises a `metacat-reset` value, for the run loop to catch;
  `report-error-and-halt` reaches it through `tell`.
- `collect` (a no-op: the original calls `(collect 4)` between runs),
  `real-time` (milliseconds, only used by `randomize`).
- **Top-level values.** `define-top-level-value`, `set-top-level-value!`,
  `top-level-value`, `top-level-bound?` work on one table, because Racket
  modules have no global environment. The original creates top-level
  variables at run time from computed names (`establish-link` in slipnet.ss
  names each link `a-b-link`), and utilities.ss's
  `symbol->letter-categories` reads `plato-a` etc. with `eval`; the port
  reads them with `top-level-value`. `reveal-obj` (a debugging aid) calls
  `format-slipnode` (rules.ss) through `(top-level-value 'format-slipnode)`,
  so the rules port must register it there.

**The 22 macros.** Written with `syntax-case` rather than `syntax-rules`
where they must build identifiers (`plato-` + name, `a-b-link`) or check
fenders. Differences forced by Racket:
- extend-syntax keywords (`each in from to do times forever until -->
  <--> length: label: all-lengths: conceptual-depth: urgency:`) are matched
  by name, so a local variable called `from` or `to` does not break `for*`.
- Names that the original resolves in the global top level where the macro
  is used (`tell`, `*coderack*`, `*control-panel*`, `%verbose%`,
  `say-object`, `print`, `make-slipnode`, `establish-link`,
  `make-codelet-type`, `rotate-90-degrees-clockwise`, the `plato-` nodes)
  get the lexical context of the macro keyword, so they refer to the
  engine's bindings at the use site. compat itself does not depend on
  utilities (it keeps a private copy of `ascending-index-list`).
- `slipnet-node-list*` and `codelet-type-list*` are used as expressions in
  `(define *slipnet-nodes* (slipnet-node-list* …))`, and define a global
  per node or type. The expression forms register top-level values only;
  the module-level forms `(define-slipnet-node-list* *slipnet-nodes* …)` and
  `(define-codelet-type-list* *codelet-types* …)` also define each name as a
  module-level variable, in the same order of `make-slipnode` calls. The
  link macros look the new link up with `top-level-value`.
- `fizzle` is a compat variable; codelets set it through `set-fizzle!`,
  since Racket forbids `set!` on an imported variable.
- `continuation-point*` uses `call/ec`. The original uses `call/cc` only in
  this macro, and only to escape upwards (`return`, `fizzle`, `fail`);
  Racket's full `call/cc` captures up to the nearest prompt and misbehaved
  inside rackunit checks. A late jump now raises an error instead of
  re-entering.
- `for*` from/to evaluates the bounds first `exp1`, then `exp2`, as the
  oracle does.
- At module level, Racket prints the value of an expression form (e.g. the
  `'done` returned by `define-codelet-procedure*` or a link macro); the
  engine modules must discard those values (e.g. a module language that
  wraps top-level expressions in `void`).

**utilities.rkt** is utilities.ss with these changes (marked `port:`):
`scheme-round` etc. come from `(only-in racket/base [round scheme-round])`
rather than `(define scheme-round round)`, because a module-level
`(define round …)` shadows the import for the whole module; `ask` peeks the
first character (no `unread-char`) and gets a `clear-input-port`;
`symbol->letter-categories` and `reveal-obj` use `top-level-value` (above);
`pause` uses `sleep`; and **`pairwise-map` evaluates its recursive call
before the `map`**, as Chez evaluates `(append (map …) (pairwise-map …))`.

**Evaluation order, more observations.** Under `scheme --script`, Chez's
order of argument evaluation depends on the shape of the call:
`(g s1 s2 s3 s4)` → 3 4 1 2, `(g s1 s2 s3 4)` → 3 1 2, `(g s1 2 s3 s4)`
→ 3 4 1, `(g 1 s2 3 s4)` → 4 2, `(g s1 s2 3 4)` → 1 2,
`(+ s1 s2 s3)` → 3 1 2, `(cons s1 s2)` → 1 2, `(list s1 s2 s3 s4)` → 1 2 3 4,
a 2-binding `let` → 2 1 but a 3-binding `let` → 1 2 3 (all at top level;
inside procedures it can differ). There is no simple rule; each port of a
call with two or more effectful arguments is checked against the oracle,
by a logging test or by the goldens.

**Other Chez/Racket differences to watch for in the engine:**
- Racket interns literal strings and flonums (`read-syntax`), so two
  literals `"a"` or `1.5` are `eq?` in Racket but not in Chez. Values
  computed at run time behave alike. `memq`/`eq?` on string or flonum
  literals in the model must be checked when ported.
- Pairs are immutable in Racket. The model never mutates pairs; only
  rule-graphics.ss:77 (`set-car!` on a picture expression) does, and the GUI
  port must restructure it.
- `(ascending-index-list 0)` loops forever in the original (so does
  `for-each-vector-element*` on an empty vector); the port keeps this.
- An object that does not understand `object-type` sends
  `report-error-and-halt` into infinite recursion, in both.
- Chez reads `0+1.0i` as `0.0+1.0i`; Racket keeps an exact zero real part.
  Only the graphics use complex numbers (`coord`).
