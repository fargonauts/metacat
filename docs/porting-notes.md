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
inside procedures it can differ). Inside a procedure, `(append s1 s2)` → 2 1 (item 07,
groups.ss's `get-local-density`). There is no simple rule; each port of a
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

## The engine's module structure (item 04)
**Decision: one engine module, `racket/engine.rkt`, that `include`s the
ported files, `racket/engine/*.rktl`, in the load order of `metacat.ss`.**
compat.rkt (syntactic-sugar.ss and Chez built-ins) and utilities.rkt
(utilities.ss) stay separate modules that the engine requires, since they
need nothing from later files.

Why, against the alternative of one module per file plus a shared-state
module:
- The original's 44 files are loaded into one global top level. Definitions
  refer to each other across files in both directions (coderack.ss names
  the codelet procedures of eleven later files; descriptions.ss calls
  `make-workspace-structure`, `contains?`, `temp-adjusted-probability`, ...;
  those files call `*coderack*` back). Racket forbids cyclic module
  dependencies, so per-file modules would need every forward reference
  rewritten as an indirection (parameters, boxes, late-bound hooks): about
  4,000 `tell` call sites are fine, but hundreds of direct calls would change.
- Files `set!` each other's globals (`*temperature*`, `*codelet-count*`, the
  mode switches, the window globals, `*workspace*`, ...). An importer cannot
  `set!` a module variable; a shared-state module would turn each into a
  getter/setter pair, changing code all over the model.
- Inside one module, the semantics are those of Chez's top level loaded in
  order: any procedure body may refer to any definition, module-level
  expressions run in load order, and a reference to a not-yet-defined
  variable at load time fails in both. Each `.rktl` stays a line-for-line
  copy of its `.ss` file, which keeps diffs against the original small.
- Cost: compiling the engine compiles all included files together (under
  a second now; `raco make` caches it), and the files are not separately
  testable modules. The differential batteries test them through the
  engine's exports instead.

Mechanics:
- **`racket/engine-lang.rkt`** is the engine's module language: racket/base
  whose `#%module-begin` partially expands each form and wraps expressions
  (not definitions, requires, provides) in `void`, so that values such as the
  `'done` of `define-codelet-procedure*` are discarded as at Chez's top
  level instead of printed. `include` splices through `begin`, which it
  handles form by form.
- **`racket/engine/pending.rktl`** defines stand-ins for names that the
  ported files refer to but whose files are not ported yet (procedures that
  raise "not ported yet"; variables holding `#f`), grouped by original file,
  including the graphics constants coderack.ss refers to. Each later item
  deletes the names of the files it ports; forgetting to is a duplicate
  definition, which Racket rejects at compile time. Nothing there is used at
  load time.
- **`set-global!`** (exported by engine.rkt) is how anything outside the
  engine (tests, the future CLI and GUI) sets an engine global:
  `(set-global! '*temperature* 50)`. It is a `case` over an explicit list of
  names; each item adds the globals of the files it ports that are set from
  outside. Reading works through the normal exports
  (`(provide (all-defined-out))`), which see the current value of a mutated
  variable. Listing a variable there also makes it mutable, so Racket does
  not inline it as a constant.
- Note for tests: a fresh namespace instantiates its own copy of the engine,
  so the battery runner takes `set-global!` from inside the battery's
  namespace (`racket/tests/diff-runner.rkt`).

Per-file notes:
- **constants.ss**: only the probability distributions
  (`make-probability-distribution` and the five
  `%...-translation-temperature-threshold-distribution%`) are model
  constants; the window sizes, colours, fonts and titles wait for the GUI
  items. The colours and fonts coderack.ss refers to (`urgency-color`, the
  codelet-type graphics methods) are stand-ins in pending.rktl.
- **setup.ss**: the globals and the user commands are ported unchanged;
  `setup` and `enable-resizing` create and arrange the windows, so they move
  to the GUI layer (racket/gui/), which will install its windows with
  `set-global!`.
- **coderack.ss**: unchanged except that `(define *codelet-types*
  (codelet-type-list* ...))` becomes `(define-codelet-type-list*
  *codelet-types* ...)`, which also defines each codelet type as a
  module-level variable (`breaker`, `rule-scout`, ...) in the same order of
  `make-codelet-type` calls. The coderack draws only through
  `stochastic-pick-by-method` (bin choice weighted by urgency sums; deletion
  weighted by `get-removal-weight`), `random` (codelet within a bin) and
  `random-pick` (excess deferred codelets); no call has two effectful
  arguments, so evaluation order does not matter here.
- **descriptions.ss**: unchanged. `make-description`'s two-binding `let`
  is evaluated right to left by Chez (make-workspace-structure first) and
  left to right by Racket; both bindings are free of side effects (to be
  confirmed when workspace-structures.ss is ported). The description codelets
  need the Workspace and Slipnet; they are checked by the golden traces once
  those are ported.
- **Chez `case`**: Chez accepts a single datum as a clause key,
  `(case x (rule-scout ...))`, meaning `((rule-scout) ...)`; coderack.ss
  uses this. compat.rkt now exports a `case` that wraps such keys. Chez
  compares keys with `eqv?`, Racket with `equal?`; the model's keys are
  symbols and numbers, where they agree.
- **Codelet types and the Coderack window.** As in the oracle, a codelet's
  `run` tells its type's private `coderack-window` `set-last-codelet-type`
  whatever the graphics switches say; that window is `#f` until
  `set-graphics-parameters`. The headless driver (item for run.ss/cli.rkt)
  must install a null window in every codelet type, as
  `install-headless-windows!` does in the oracle prelude.

**Tests** (`racket/tests/coderack-diff-test.rkt`, battery
`tests/diff/coderack-battery.scm`, 43 tests): the setup.ss defaults; the
urgency table (7 bins × 101 temperatures); `urgency-name` and bin selection
for integer, rational and flonum urgencies; bin urgencies at every
temperature; codelet-type lists and graphics labels; posting with time
stamps, bin indices and codelet order; `choose-codelet` over 8 seeds × 7
temperatures with the generator state after every choice; emptying the
coderack; overflow deletion (with and without proposed structures, which
are reported to the Workspace); removal weights; deferred posting below,
at and above the size limit; clamp/unclamp, adjust/set/reset urgencies and
choosing while clamped; codelet accessors, `run` and `fizzle`; printing;
`post-codelet-probability`, `num-of-codelets-to-post`,
`bottom-up-urgency`, `add-bottom-up-codelets` and `add-top-down-codelets`
with fake Workspace, Themespace, Trace and top-down slipnodes; the threshold
distributions; the setup.ss commands; `descriptions-equal?` and
`description-member?`. The battery helpers moved to `tests/diff/helpers.scm`,
which both runners load first.

## The Slipnet and images (item 05)

- **slipnet.ss**: unchanged except that `(define *slipnet-nodes*
  (slipnet-node-list* ...))` becomes `(define-slipnet-node-list*
  *slipnet-nodes* ...)`, which also defines each `plato-...` node as a
  module-level variable, in the same order of `make-slipnode` calls. The
  link macros (`lateral-link*`, ...) name each new link only as a top-level
  value (`a-b-link`, via `establish-link`'s `define-top-level-value`) and
  message it with `(top-level-value 'a-b-link)`; no other file refers to a
  link by its name. The module-level code (top-down codelet types, intrinsic
  link lengths, descriptor predicates, the 202 links) runs at load time as in
  the original, after coderack.rktl has defined the codelet types.
- **images.ss**: unchanged.
- **Stand-ins** (engine/pending.rktl) that these files need until their
  files are ported: `%update-cycle-length%` (run.ss's constant 15, which
  slipnode `reset` uses for the decay rate; it is a value, not `#f`),
  `make-letter` (workspace-objects.ss), `make-group` (groups.ss),
  `make-group-pexp` (group-graphics.ss), `monitor-slipnode-activation-change`
  (trace.ss). `monitor-slipnode-activation-change` and
  `temp-adjusted-probability` are in `set-global!`'s list so that the battery
  can replace them by logging fakes in both runners (Chez:
  `set-top-level-value!`, as the original refers to them as top-level
  variables). `*top-down-slipnodes*` is now defined by slipnet.rktl and stays
  settable.
- **Random draws and order.** The Slipnet draws in
  `update-slipnet-activations` (one `stochastic-if*` per partially active
  node, in `*slipnet-nodes*` order: a jump to full activation with
  probability (a/100)^3), in `get-similar-property-links` (one `prob?` per
  property link), in `apply-slippages` (coattail slippages) and in
  `attempt-to-post-top-down-codelets` (`stochastic-if*` per codelet type).
  No call has two effectful arguments. Activation arithmetic is exact
  (`rate-of-decay` = 1 − depth/100, spread = round(assoc/100 × activation)
  with utilities.ss's exact `round`), so "the last bit" is exact equality.
- **Order in images.** `replace-all` and `tell-all` use `map` with side
  effects, and an operation can escape midway through its `fail`
  continuation, leaving the images it already changed changed. Which ones
  depends on the order in which `map` applies its procedure, so compat.rkt's
  Chez-order `map` matters here. The battery's `replace-all-fail` case
  catches it (a left-to-right `for-each` in `replace-all` fails it).

**Tests** (`racket/tests/slipnet-diff-test.rkt`, battery
`tests/diff/slipnet-battery.scm`, 48 tests, run by Chez and Racket with
identical output, about 1.1 MB): the initial slipnet as loaded (every node's
names, depth, activation, link lengths, category/instance relations; every
link list of every node with type, ends, label, length and degrees of
association; 202 links; nodes and links as top-level values; printing);
`get-label`, `linked?`, `related?`, `slip-linked?` over all 59 × 59 pairs;
`relationship-between`, `get-related-node` for 8 relations, `inverse`, the
platonic predicates and numbers; descriptor predicates over fake workspace
objects; reset; every activation message, with the monitor calls; decay and
spread from each node alone; **20 calls of `update-slipnet-activations`**
from 8 fixed states (with/without clamped nodes, unfrozen after 10 updates,
with fake themes spreading activation) recording all activations, frozen
flags and the generator state after every update, plus 15 seeds and the
start-of-run state; similar property links, `apply-slippages` (coattail
slippages, also with Opposite fully active) and top-down codelet posting over
several seeds; and images: 8 letter/group images × 29 operations (each
followed by copy, leaf walk, postorder walk, state, reset), swapped
image/state round trip, printing, string images over a fake string × 13
operations, `change-length-first?`, `enumerate-letter`.

## The Workspace, its objects and strings, and the formulas (item 06)

- **Ported unchanged**: `workspace.ss`, `workspace-objects.ss`,
  `workspace-structures.ss`, `workspace-strings.ss`,
  `workspace-structure-formulas.ss` and `formulas.ss` → `racket/engine/*.rktl`,
  included by engine.rkt after descriptions.rktl in metacat.ss's order
  (bonds/groups/bridges/breakers, concept-mappings.ss and run.ss, which come
  between them in the original, are not ported yet). No line of model code
  changed. `(define *workspace* (make-workspace))` runs at load time, as in
  the original.
- **`tanh`** (workspace.ss, the mapping strength of a maximal mapping):
  racket/base has none, and racket/math's is computed in Racket and may
  differ from Chez's in the last bit. compat.rkt takes Chez's own primitive
  through `(vm-primitive 'tanh)` (Racket CS runs on Chez Scheme; its Chez is
  10.3, the oracle's 10.0; the battery checks 500+ arguments bit for bit).
- **`*temperature-clamped?*` has no definition in the original.** formulas.ss
  reads it, answers.ss and trace.ss `set!` it, and run.ss's `init-mcat`
  creates it with `(set! *temperature-clamped?* #f)` on Chez's top level.
  A Racket module needs a definition: engine/pending.rktl defines it (`#f`)
  under run.ss, and the run.ss item must move it there.
- **Stand-ins added** (engine/pending.rktl), all called only inside procedure
  bodies: `same-bond-category?`, `same-bond-direction?`,
  `opposite-bond-category?`, `opposite-bond-direction?` (bonds.ss);
  `same-group-category?`, `same-group-direction?` (groups.ss);
  `bridge-between?`, `equivalent-workspace-objects?`, `rule-describable-bridge?`
  (bridges.ss); `break-bridge` (breakers.ss); `verbatim-clause?` (rules.ss);
  `full-workspace-object-name` (trace.ss, used by workspace objects' `print`);
  `group-graphics`, `bridge-graphics`; and `*EEG*` (eeg-graphics.ss), which the
  Workspace's `initialize` messages. Removed: `*workspace*`, `%proposed%`,
  `%evaluated%`, `%built%`, `make-letter`, `make-workspace-structure`,
  `temp-adjusted-probability`.
- **`set-global!`** now also lists the workspace.ss string globals
  (`*initial-string*` … `*all-strings*`, which run.ss's `init-workspace`
  sets), `*temperature-clamped?*`, `*EEG*` and `contains?`.
- **Random draws and order.** These files draw only through `stochastic-pick`
  (`choose-object`, `choose-...-neighbor`, `choose-description-for-rule`,
  `wins-fight?`), `stochastic-pick-by-method`, `random-pick`
  (`get-random-letter`), a probability distribution (`get-num-of-bonds-to-scan`)
  and `~` (`rough-num-of-objects`). No call has two effectful arguments, and
  `wins-fight?` updates the challenger's strength before the defender's in a
  body, not in an argument list. Building the initial workspace draws nothing
  (the checks below confirm the generator state is untouched).
- **The initial workspace at the start of a run.** `init-mcat` activates each
  letter's *descriptors* fully, but not the description *types*
  (`relevant?` = `fully-active?` of the type), so every raw importance is 0
  and every object of a string gets relative importance round(100/n). The
  saliences at the start therefore come from unhappiness alone.
- **Testing infrastructure fix: stale compiled engine.** The differential
  runner (`racket/tests/diff-runner.rkt`) requires the engine into a fresh
  namespace. The default load handler only compares engine.rkt's own date with
  its `.zo`, so after editing an included `.rktl` the battery silently ran the
  old engine (found because no mutation in this item made the battery fail).
  The runner now loads through the compilation manager, whose handler must be
  created inside the new namespace (it skips modules of other module
  registries). Note also that the compilation manager compares timestamps in
  whole seconds: a source edited in the same second as the last compile is
  not recompiled, so mutation scripts must wait a second around each edit.
  The mutation checks of items 04 and 05 were made with `raco make` between
  edits, so they stand.

**Tests**:
- `racket/tests/workspace-diff-test.rkt`, battery
  `tests/diff/workspace-battery.scm` (77 tests, about 0.7 MB of output, identical
  under Chez and Racket), with `tests/diff/workspace-dump.scm`:
  - **for every problem in `tests/problems.txt`** (read at run time; 36
    problems, 109 problem × seed pairs), the initial workspace built as
    `init-mcat` builds it (`b:init-problem`, a copy of the Workspace part of
    run.ss under `b:` names), for each seed: every string (names, type,
    length, object capacity, letter categories, image letters, average
    unhappiness) and every letter (id, positions, letter category, each
    description with its proposal level, strength and time stamp, raw and
    relative importance, intra/inter/average unhappiness and salience, bonds,
    bridges, group, image), the workspace averages and mapping strengths,
    all slipnet activations, the EEG messages, and the generator state after;
  - live queries on 10 problems of every shape (3 or 4 strings, lengths 1–7):
    relevant and distinguishing descriptions, descriptions for rules, concept
    patterns, descriptor and type tests for all nodes, neighbours, positions,
    relevance of bond categories and directions, `spanning-group-possible?`,
    `description-type-support`/`descriptor-support`, reference objects,
    rule possibilities, translation-threshold distribution, `update-temperature`,
    and seeded choices (objects, neighbours, descriptions, bonds to scan,
    rough counts) under 4 seed/temperature pairs;
  - objects with fake bonds, groups and bridges (every branch of the
    unhappiness and salience formulas, a clamped salience), fully active
    description types (raw importance, the 2/3 factor in a group), strings
    with fake bonds and groups (tables, edge vectors, coincident groups,
    storage expansion and the Workspace's bridge reallocation), Workspace
    bridges and rules with fakes, maximal mappings (the tanh branch), workspace
    structures (strength, weakness, age, proposal levels), `wins-fight?` and
    `wins-all-fights?` over 15 seeds and 4 temperatures, `temp-adjusted-probability`
    and `temp-adjusted-values` over 11 temperatures, the group probability
    formulas, and `tanh`.
  - Stand-ins in both runners: `*themespace*` (no active themes, as at the
    start of a run), `*EEG*` (logs its messages), `contains?` (groups.ss's own
    definition).
- `chez_scheme/oracle/tests/workspace-init-check.ss` (Chez only): for every
  problem and its first seed, the dump after `b:init-problem` equals the dump
  after the original's real `init-mcat` (with the real Themespace, EEG and
  `contains?`), and `b:init-problem` draws nothing. This is what makes the
  battery's copy of run.ss trustworthy until run.ss is ported.

## Bonds, groups and concept mappings (item 07)

**Changes**: `bonds.ss`, `groups.ss` and `concept-mappings.ss` →
`racket/engine/bonds.rktl`, `groups.rktl`, `concept-mappings.rktl`, included
by engine.rkt in metacat.ss's load order (bonds and groups after
descriptions.rktl, concept mappings after workspace-strings.rktl). One line
of model code changed:
- **groups.ss, a group's `get-local-density`**: `(append (neighbors self
  'choose-left-neighbor) (neighbors self 'choose-right-neighbor))`. Both
  arguments draw: `choose-left-neighbor`/`choose-right-neighbor` pick at
  random when a letter and a group are both neighbours. Chez evaluates
  `append`'s second argument first (checked: `(append (show 'L) (show 'R))`
  inside a procedure prints `RL`), so the port binds the right neighbours
  first in a `let*`, marked `port:`. Found by the harness below: `abc abd
  iijjkk` seed 3 left the oracle at the update after codelet 735, where the
  slipnet's jump draws were shifted by one. The 400-codelet runs never
  reached it, the 2000-codelet run did. This is the only call in the three
  files with two drawing arguments; the others (`let` with two
  `descriptor-support`s, `append` of incompatible bridges, `cons` of
  neighbours) have at most one.
- **`group-graphics`** (group-graphics.ss) is now an engine procedure,
  verbatim, in `racket/engine/group-graphics.rktl`: group-builder calls
  `(group-graphics 'erase proposed-group)` ungated when it consolidates
  sameness groups, so a headless run needs it. It only sends messages to
  `*workspace-window*` (`caching-on`, `flush`, and `draw-group`/`erase-group`
  for drawn groups). The rest of group-graphics.ss waits for the Workspace
  panel.

**Stand-ins** (engine/pending.rktl). Removed: `same-bond-*`,
`opposite-bond-*`, `same-group-*`, `contains?`, `make-group`,
`group-graphics`. Added: `incompatible-horizontal-CMs?`,
`incompatible-vertical-CMs?` (bridges.ss; `break-bridge` moved under
bridges.ss too, where it is defined); `monitor-new-groups` (trace.ss);
`outline-box`, `arrowhead` (general-graphics.ss); `draw-group-grope`,
`%small-group-arrowhead-length%`, `%group-arrowhead-angle%`
(group-graphics.ss); `%group-letter-category-font%` and
`%relevant-group-length-font%`, which the original never defines
(workspace-graphics.ss creates them by `set!`); and `same-direction?`, which
the original never defines either (bonds.ss's `bonds-equal?`, itself never
called, refers to it): it raises as Chez would. All these are read only in
graphics-gated code or in procedures not called yet.

**`set-global!`** also lists `monitor-new-groups` (the harness records its
calls); `contains?` stays (workspace-battery.scm still replaces it).

**Concept mappings** are made in these files only inside
`get-incompatible-bridge` (bonds and groups), which needs a bridge; with no
bridges they are never made during a run, so the battery tests them
directly. Bridges (item 08) will exercise them in runs.

**Tests**:
- **The codelet-level differential harness**: `racket/tests/codelet-diff-test.rkt`,
  battery `tests/diff/codelet-battery.scm`, harness
  `tests/diff/codelet-harness.scm`. `b:run-codelets` is a copy of run.ss's
  `run-mcat` loop (`step-mcat`, unclamping, re-posting on an empty
  Coderack, `update-everything` every 15 codelets) with only the bond and
  group codelet types enabled: initial codelets are bottom-up bond scouts
  only, bottom-up posting covers `bottom-up-bond-scout` and
  `group-scout:whole-string`, `*top-down-slipnodes*` holds only the 8 bond
  and group nodes, self-watching is off, and `update-everything` leaves out
  rules, the Trace's snag/clamp periods and the Themespace. The trace has
  one line per codelet (type, urgency, time stamp, generator state,
  structures built and broken with strengths, Workspace-window messages,
  `monitor-slipnode-activation-change` and `monitor-new-groups` calls,
  numbers of proposed structures) and per update (temperature, every
  activation, Coderack size, generator state; every object of the
  Workspace every 4th update). The Racket test compares the lines one by one
  and reports the first difference with its problem, seed and codelet.
  Runs: all 109 problem × seed pairs of tests/problems.txt for 400
  codelets, plus 7 runs of 2000 codelets on problems where group-builder
  consolidates sameness groups (the ungated `group-graphics` path); about
  60,000 lines. The test also checks that all 10 enabled codelet types run,
  that bonds and groups are built and broken, and that `group-graphics` is
  called.
- Concept mappings, in the same battery: every message of a mapping
  (names, link, predicates, degree of association, depth, strength,
  slippability, concept pattern, symmetric mapping, `CMs-equal?`) for every
  pair of instances of each of the 9 slipnet categories, and for every pair
  of same-type descriptions of initial and target objects (letters and
  groups) after 600 codelets of 5 problems, with `remove-duplicate-CMs` and
  the activations left by `activate-descriptions`/`activate-label`.
- Exploration, not in the gate: the same harness for **2000 codelets on all
  109 runs** (218,000 codelets, 90 MB of trace) is byte-identical under Chez
  and Racket (Chez about 33 s, Racket about 58 s).

## Bridges and breakers (item 08)

**Changes**: `bridges.ss` and `breakers.ss` → `racket/engine/bridges.rktl` and
`breakers.rktl`, verbatim apart from the GPL header's "Ported to Racket"
lines, included by engine.rkt right after groups.rktl (metacat.ss's load
order). No model line changed.

**Evaluation order, audited**: the draws in these files are
`stochastic-pick` of the bridge type, `choose-object`,
`stochastic-pick-by-method`, `stochastic-if*`, `random-pick`,
`wins-fight?`/`wins-all-fights?`, and, through bridge-builder,
`build-group`/`break-group`/`break-bond`. Every one sits in a `let*`, a
sequence or an `and`/`or`; no call or `let` has two drawing arguments.
`propose-group` (draws) is reached only from `propose-singleton-group` and
`try-to-propose-singleton-group`, which nothing calls. Calls whose arguments
are evaluated in a different order in Racket (`append` in
`get-incompatible-bridges`, the `let`s of `bridge-builder` and `breaker`)
have no side effects.

**Stand-ins** (engine/pending.rktl). Removed: `bridge-between?`,
`incompatible-horizontal-CMs?`, `incompatible-vertical-CMs?`, `break-bridge`
(now defined by bridges.rktl). `equivalent-workspace-objects?` (trace.ss) and
`rule-describable-bridge?` (rules.ss) had been listed under bridges.ss by
mistake and moved to their files. Added:
- themes.ss: `check-descriptions`, `conflicts-with-theme?`,
  `supported-by-theme?` as raising stand-ins (only called with an active
  theme); and **early verbatim copies** of `bridge-type->theme-type`,
  `descriptions-affect-themespace?`, `ignore-descriptions?`, `beta` and
  `bridge-theme-compatibility-sigmoid`. Every bridge calls the first when it
  is made, the sigmoid when its strength is updated, and bridge-builder the
  second; they are pure (no draws, no state), so copying them early changes
  nothing. Item 10 deletes the copies when it ports themes.ss.
- trace.ss: `monitor-new-concept-mappings` (called by every `build-bridge`),
  `entries`; justify.ss: `remove-whole/single-concept-mappings` (both only
  used by `supports-theme-pattern?`, i.e. memory.ss);
- bridge-graphics.ss: `draw-bridge-grope`, `new-bridge-label-number`
  (graphics-gated).

**`set-global!`** also lists `monitor-new-concept-mappings`.

**Tests**:
- `racket/tests/bridge-diff-test.rkt`, battery `tests/diff/bridge-battery.scm`,
  on the item 07 harness (`tests/diff/codelet-harness.scm`) with its new
  `b:bridges?` setting (`b:enable-bridges!`):
  - initial codelets as run.ss posts them (bottom-up bond and bridge scouts,
    interleaved);
  - bottom-up types: those of `*bottom-up-codelet-types*` except rule-scout,
    answer-finder, answer-justifier, progress-watcher and jootser, i.e. bond
    scout, whole-string group scout, both bridge scouts, the description scout
    and the breaker;
  - `*top-down-slipnodes*` as in the original (the bond/group nodes plus
    StrPosCtgy, AlphaPosCtgy and Length, whose top-down codelets are
    description scouts), so descriptions.ss's codelets now run too;
  - a fake Themespace with no active theme that records bridge-builder's
    boosts (`add-theme-if-possible`, answering #f, and
    `update-dominant-themes`) and a null Themespace window recording
    `update-graphics`.
  The trace adds, to item 07's: every built bridge (type, objects, flipped
  groups, proposal level, strength, time stamp, concept mappings, bond
  concept mappings, symmetric slippages), proposed top and vertical bridges,
  the number of descriptions of every object, and
  `monitor-new-concept-mappings` calls. Runs: all 109 problem × seed pairs for
  **1000 codelets** (item 07: 400), about 116,000 lines, 48 MB. The test
  checks that the bridge, description and breaker codelets all run, that top,
  vertical and bottom (justify) bridges are built and bridges broken, that
  the breaker breaks structures, that a bridge with a flipped group is built,
  and that the monitor and Themespace boosts are called.
- With `b:bridges?` off, the item 07 battery's traces are unchanged (bridges
  only add an empty list to its structures).
- Also in the battery, **bridges examined directly** (`b:bridge-matrix`, 9
  runs of 1500 codelets): after the run, a fresh bridge for every pair of
  initial × modified objects (horizontal) and initial × target objects
  (vertical), with its concept mappings and their strengths, internal
  coherence, internal and external strength, incompatible bridges and bond,
  `reverse-direction-orientation?`, `letter-category-mappable-objects?`,
  `singleton-letter-factor`; `direction-incompatible-bridges` for every pair
  of directed groups under both direction mappings; and every pair of built
  bridges of a type (incompatible, supporting, CM-list incompatibility,
  enclosing). Nothing there draws.
- Tests-first: the battery ran under Chez before the Racket test existed (one
  harness bug found there: `b:structures` passed the bridges list to `apply
  append` as its last argument). With HEAD's engine.rkt and pending.rktl
  (no port) the Racket test fails: `set-global!: not a settable engine
  global: monitor-new-concept-mappings`. With the port, all lines agreed on
  the first run; no model line had to change.
- Mutation checks (each restored, 1 s pauses around edits; compared with the
  saved Chez output):

  | Mutation | Lines differing |
  | --- | --- |
  | horizontal CM-count factor 1.2 → 1.3 | 78165 |
  | vertical CM-count factor 1.2 → 1.3 | 2590 |
  | horizontal internal-coherence factor 2.5 → 2.0 | 0 (strengths clip at 100) |
  | singleton-letter factor 0.1 → 0.2 | 621 |
  | horizontal external strength halved | 69537 |
  | vertical external strength halved | 78746 |
  | bridge-scout type weights without `100-` | 116216 |
  | important-object scout by salience | error (caught) |
  | bridge-evaluator without `1-` | 110334 |
  | bridge vs bond fight weights 3:2 → 2:3 | 2739 |
  | build-bridge without symmetric slippages | 8130 |
  | direction partition `< >` → `< <`, `> <` → `> >` | 0 (equivalent here, below) |
  | direction-incompatible: `remq-elements` dropped | 21185 |
  | horizontal incompatible-CMs label test dropped | 1 (only the bridge matrix) |
  | vertical mappable: `slip-linked?` dropped | 73813 |
  | breaker temperature test inverted | 56231 |
  | breaker group×bond probability → bond only | 80 |
  | breaker picks first structure | 59618 |

  The partition mutations are equivalent on these runs: `partition` inserts
  from the end of the list, and a group's subobject bridges come in string
  order, so the second predicate is never consulted. The coherence factor
  multiplies strengths that already exceed 100 with either value.
- Exploration, not in the gate: the bridges harness for **3000 codelets on
  all 109 runs** (327,000 codelets, 349,055 lines, 151 MB) is byte-identical
  under Chez and Racket (Chez 77 s, Racket 135 s): 2160 bridges built, 105
  structures broken by the breaker, 6 bridges with flipped groups.
- The goldens still can't be compared: real runs post rule-scout,
  answer-finder and self-watching codelets (and draw for their posting
  probabilities) from the first update on.
