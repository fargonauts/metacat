# Translating Metacat 1.2 to Python: the plan

Loop0002, item 01, 2026-10-03. This is the counterpart of numbo's
`docs/python_translation_audit.md`: what the translation has to reproduce, how Python
will do it, and in which order. Items 02–17 of `ralph_loops/loop0002/iterations.md`
follow it. If an item finds a decision here wrong, it fixes this file and says so in
PROGRESS.md.

Sources read: `racket/compat.rkt` and `racket/utilities.rkt` in full, every `port:`
comment in `racket/engine/*.rktl` and `racket/engine.rkt`, `docs/code-map.md`,
`docs/trace-format.md`, `docs/porting-notes.md`, `docs/anomalies_and_quirks.md`,
`docs/divergences.md`, `docs/follow-ups.md`, and the original itself (counts below come
from `chez_scheme/original/`).

Prototypes and measurements made for this item:
- `python/tests/object_prototypes.py` and `test_object_prototype.py`: four object
  representations (six variants), checked against the Chez fixtures of
  utilities-battery.scm's object tests, plus the micro-benchmark;
- `python/tests/name_mapping.py` and `test_name_mapping.py`: the name mapping, checked
  on every name the original defines;
- `python/oracle/count-calls.ss`: counts `tell` and `delegate` calls in a real oracle run.

## Verdict

**Feasible, mechanical in most places, and testable all the way down.** The hard
problems were solved by the Racket port (loop0001): the PRNG, Chez's `map` and `sort`
orders, the evaluation-order sites, the printer, and the model/graphics couplings. Each
has a reference implementation in `racket/compat.rkt` and a Chez fixture in
`python/fixtures/`. What is new in Python:

1. **Truthiness.** In Scheme only `#f` is false. Python also treats `0`, `0.0`,
   `Fraction(0)`, `[]` and `""` as false. This is the biggest new risk; see "Booleans
   and truthiness".
2. **Arithmetic contagion.** Python has `int`, `Fraction` and `float`, but its `/`,
   `max`, `min`, `sqrt`, `exp`, `**` and `0 * x` don't follow Chez's exactness rules.
3. **No first-class continuations.** Escapes become exceptions. The one re-entrant use
   (`break`/`go`) becomes a blocked engine thread in the GUI and an exception headless.
4. **Speed.** Chez makes about 1,000 `tell` calls per codelet. Dispatch alone costs
   about 0.2 ms per codelet in Python, so a codelet will cost a few milliseconds, 20–50×
   Chez. The goldens have to run in parallel.
5. **Modules.** Python modules can be circular, and later files can assign to a
   module's globals. Load order still has to be imposed by hand.

Size: 21,700 non-blank, non-comment lines of Scheme. About 14,600 are the model
(utilities to memory.ss plus run.ss), 4,900 the SGL interpreter and panels, and 1,200
demos and gui.ss.

| Files | Lines | Item |
|---|---:|---|
| syntactic-sugar.ss, utilities.ss | 877 | 03 |
| constants.ss, setup.ss, coderack.ss, descriptions.ss | 1,856 | 04 |
| slipnet.ss, images.ss | 1,003 | 05 |
| workspace*.ss, formulas.ss | 1,870 | 06 |
| bonds.ss, groups.ss, concept-mappings.ss | 1,573 | 07 |
| bridges.ss, breakers.ss | 1,507 | 08 |
| rules.ss, answers.ss | 2,952 | 09 |
| themes.ss, justify.ss, trace.ss, jootsing.ss, memory.ss | 3,590 | 10 |
| run.ss | 288 | 11 |
| sgl-interpreter.ss, fonts.ss | 508 | 13 |
| general-graphics.ss and the 12 other *-graphics.ss | 4,396 | 14 (some engine parts earlier, as in Racket) |
| demos.ss, gui.ss | 1,177 | 15 |

## The Chez semantics the engine depends on

Each row gives the Python strategy and the module that implements it. `chez.py` is item 02;
`objects.py`, `sugar.py` and `utilities.py` are item 03. The tests are the Chez fixtures
(`python/fixtures/utilities/` and others), plus small capture scripts in `python/oracle/`
where a battery has no vector.

### Numbers

| Chez | Python | Notes |
|---|---|---|
| exact integer | `int` | bignums never occur in the model, but `int` is unbounded anyway |
| exact non-integer rational (`102/5`) | `fractions.Fraction` | **always normalised**: a result with denominator 1 becomes `int` (`chez.norm`), because `Fraction(2, 1)` is not an `int` for `integer?`-style tests, `random`, indexing or trace printing |
| flonum | `float` | |
| `(/ a b)` on exact numbers | `chez.div(a, b)`, giving `int` or `Fraction` | **never Python `/`** on values that are exact in Chez: `/` makes a float, and a float urgency changes codelet choices. `%` (utilities.ss: `(/ n 100)`) is the most common case |
| `(* 0 x)` with flonum `x` | `chez.mul` | Chez gives **exact 0** (checked: `(* 0 1.5)` → `0`, `(/ 0 2.5)` → `0`), Python gives `0.0`. Use `chez.mul`/`chez.div` wherever one operand can be a flonum. *Item 02 correction:* `+` and `-` differ too, at signed zeros only: exact 0 is their identity, so `(+ 0 -0.0)` and `(- 0 0.0)` are `-0.0` where Python gives `0.0` (`chez.add`/`chez.sub`; anomalies_and_quirks.md) |
| `max`, `min` | `chez.max_`, `chez.min_` | inexact contagion: `(max 3 2.0)` → `3.0`, `(min 1 2.0)` → `1.0`; Python keeps the `int` |
| `sqrt`, `exp`, `log`, `expt` | `chez.sqrt` etc. | exact in, exact out where the result is exact: `(sqrt 16)` → `4`, `(sqrt 1/4)` → `1/2`, `(exp 0)` → `1`, `(log 1)` → `0`, `(expt 1/2 2)` → `1/4`, `(expt 0.0 0)` → `1` (exact!). Otherwise IEEE doubles from libm (`math.sqrt` etc.), bit-equal on item 02's vectors. *Item 02:* `expt` has more rules: only a `1/2` power is an exact root (`(expt 8 1/3)` → `2.0`), an exact 1 base gives `1`, an exact 0 base gives `0` for a positive power, and `(expt 0.0 -1)` is `+inf.0` (anomalies_and_quirks.md) |
| `tanh` | `math.tanh` | workspace.ss's mapping strengths; Racket took Chez's own primitive, item 02 checked `math.tanh` against Chez bit for bit on about 1,100 arguments (`tanh-*` fixtures): equal |
| `exact->inexact` of a ratnum | `chez.inexact` (`float(Fraction)`) | correctly rounded in both; equal on item 02's 400 random ratnums |
| utilities.ss `round`, `floor`, `ceiling`, `truncate` (exact results) | `round_` (Python `round`: half to even, returns `int`), `math.floor`, `math.ceil`, `math.trunc` | Chez's `round` is half to even too (`(round 5/2)` → `2`, `(round 7/2)` → `4`, `(round 2.5)` → `2.0`) |
| `=`, `<`, … | Python operators | mixed exact/inexact comparisons are exact in both |
| `eqv?`/`equal?` on numbers | `chez.eqv_p`, `chez.equal_p` | `(equal? 2 2.0)` is `#f` but Python's `2 == 2.0` is `True`, and likewise `Fraction(1, 2) == 0.5`. Only where a list compared with `equal?` can hold numbers of mixed exactness (memory.ss, rules.ss, justify.ss sites) |
| `1+`, `-1+`, `add1`, `sub1` | `add1`, `sub1` | |
| `random`, `random-seed` | `chez.random`, `chez.random_seed` | the 32-bit LCG of trace-format.md; `(random 1.0)` is `M/2^52` exactly; one module-level state. Must accept an `int` only (normalise Fractions first) |
| flonum printing | `chez.number_to_string` | shortest round-trip digits (Python's `repr` gives the same digits **except at exact ties, where Chez rounds the last digit up and Python to even**, item 02), laid out Chez's way: positional when the leading digit's exponent e is in (−4, 10), else `d.ddde<exp>` with no `+` and no exponent padding. So `1e21`, `1e-7`, `1.234567890125e11`, `1000000000.0`. Python's `repr` writes `1e+21`, `1e-07`, `123456789012.5` |
| ratnum printing | `str(Fraction)` | `"102/5"`, `"-1/2"`, as Chez; normalised ints print as ints |

Only 84 flonum literals appear in the model files (formulas.ss, bridges.ss and rules.ss
have 12 each). Everything else stays exact, so most arithmetic is `int` and `Fraction`.
That makes it safe *and* slow (see Risks).

### Evaluation order

Chez evaluates call arguments and `let` bindings in an order that depends on the shape of
the call (porting-notes.md, item 03). At top level, `(f a b c)` evaluates c, a, b;
`(list ...)` is left to right; a 2-binding `let` is right to left. Inside a procedure,
`(append a b)` evaluates b first. This item's own check also found a 2-binding `let`
inside a lambda that went *left to right* (`12`), unlike the top-level case. There is
no rule. **Python is left to right everywhere.** Wherever two or more arguments or
bindings have order-dependent side effects (random draws, posting codelets, building
structures, trace events, output), the translation spells out Chez's order as
sequential statements and marks the site `# chez: evaluation order`.

The sites, from the Racket port's per-file audits (porting-notes.md, items 04–11) and
`racket/compat.rkt`:

| Site (original) | What | Python |
|---|---|---|
| groups.ss:368–370, a group's `get-local-density` | `(append (neighbors self 'choose-left-neighbor) (neighbors self 'choose-right-neighbor))`; both draw | compute the **right** neighbours first (racket/engine/groups.rktl:371, `port:`). Found by a 2000-codelet harness run (`abc abd iijjkk` seed 3, codelet 735) |
| utilities.ss:690–700, `pairwise-map` | `(append (map ...) (pairwise-map (rest l)))` | the **recursive call first**, then the `map` (racket/utilities.rkt:720) |
| run.ss:234–239, `init-workspace` | a 4-binding `let` making the strings | last to first, as Racket does (run.rktl:229). It draws nothing, so it's equivalent, but keep the order |
| syntactic-sugar.ss:82, `for*` from/to | the bounds | `exp1` then `exp2` |
| syntactic-sugar.ss:121, `stochastic-if*` | the coin and the probability | **draw `(random 1.0)` first**, then evaluate `prob`: the probability expression may itself draw or read state |
| utilities.ss:400, `~` | `(random ...)` in a `let`, then `(prob? 0.5)` in the body | sequential already |
| workspace-structures.ss:70, `wins-fight?` | challenger's strength updated before the defender's | a body sequence, already ordered |
| descriptions.ss `make-description`, bridges.ss `get-incompatible-bridges`, `bridge-builder`, `breaker`, rules.ss `(list 'intrinsic (list od) (map ...))` | several arguments, at most one with effects | no change needed (audited in Racket items 04, 08, 09) |

Every other draw sits in a `let*`, a body, an `and`/`or`/`cond`, or a `map`/`filter`
whose order `chez.py` reproduces. The goldens (109 runs) and the extra seeds (720 runs)
showed no other site in Racket, which evaluates left to right like Python. So these
tables are complete for runs that reach the same code. Each item still re-audits its
files: for every call or `let` with two effectful subexpressions, it records the site in
the item's PROGRESS entry.

### Lists, `map`, `sort`, `remq`, `for-each`

| Chez | Python |
|---|---|
| proper list | Python `list`, **never mutated after construction** (the model never mutates pairs; only rule-graphics.ss:77 has a `set-car!`, which the Racket port turned into a copy). `cons` onto a list → `[x] + ls`; `cdr` loops → index loops (lists are short: strings ≤ 7 letters, coderack ≤ 100) |
| vector, table (vector of vectors) | Python `list` (fixed length), list of lists |
| dotted pair | none found in the model's data (the `(cons ...)` sites, 126, are audited per file); a non-list `cdr` is a `chez.Pair(car, cdr)` (item 02; not a tuple, since `*args` tuples are lists) |
| `map` (1 or 2 lists) | `chez.map_`: applies f to pairs from the end towards the front (7 elements: 7 5 6 3 4 1 2); 3+ lists last to first. Used **everywhere** `map` appears with a procedure that has effects (`tell-all`, `delegate-to-all`, images.ss's `replace-all`, themes.ss's `pick-positive-theme`, `filter`-like helpers); plain list comprehensions only where the function is pure. Chez also inlines `map` over literal lists in an order of its own; Racket used the library order at every site and matched all goldens, so Python does the same |
| `for-each` | a `for` loop; `chez.for_each` where its value (the last application's, `None` for `'()`) is used (the `for*` forms pass it on) |
| `andmap`, `ormap` | first to last, stopping early (battery `andmap-order`, `ormap-order`) |
| `sort` | `chez.sort(pred, ls)`: Chez 10's merge sort (below 25 elements a top-down list merge sort that sorts the second half first, else Shivers's vector merge sort), with Chez's sequence of predicate calls. **Never `sorted()`**: the predicates are `<`/`>` on keys with ties (`sort-by-method 'get-age <`), and stability alone doesn't give Chez's order for non-strict predicates. Sites: utilities.ss `sort-wrt-order`, `sort-by-method`; rules.ss:926, 1292, 1344; workspace.ss:188, themes.ss:508 and others through `sort-by-method` |
| `remq`, `remv`, `remove` | remove **every** occurrence; `remq` by `chez.eq_p` (53 sites) |
| `memq`, `assq` | by `chez.eq_p` |
| `list-index`, `list-tail`, `append` | utilities.ss's own definitions, translated |

### `eq?` and identity

`eq?` (469 sites in the model) becomes:
- `is` when either operand is a model object, a slipnode, a list, `#f`/`#t`, or `'()`
  compared by identity (`null?` is `len(x) == 0`, `not x` only where `x` is known to be a
  list);
- `==` when the operands are symbols (Python `str`, not reliably interned) or fixnums.

`chez.eq_p(a, b)` (`a is b`, or both are `str`, or both are non-bool `int`, and they
are equal) is the version for `memq`, `assq`, `remq` and calls where the operand types
vary. Model objects never define `__eq__`, so `==` on them is identity too. Python
lists and tuples compare by content, so a list is never compared with `==` where Scheme
used `eq?`.

### Booleans and truthiness

`#f` → `False`, `#t` → `True`, unspecified value (`void`) → `None`, `'()` → `[]`.

**In Scheme only `#f` is false.** `0`, `'()`, `""` and `0.0` are true. Python's `if x`,
`x or y`, `x and y`, `not x`, `filter(None, ...)` and `any`/`all` treat them as false.
Rules:
- `(if x ...)`, `cond`, `when`, `unless`, `and`, `or`, `not`, `exists?`, `compress`:
  use Python truthiness **only** when `x` is known to be a boolean, or an object or
  `#f`. Model objects are always truthy (they don't define `__bool__` or `__len__`).
  Otherwise write `x is not False` / `x is False`.
- `(or a b)` as a *value* (it returns `a`) → `a if a is not False else b`, unless `a`
  is boolean or object-or-`#f`.
- Numbers, lists and strings are never tested with plain `if`.
- `exists?` is `x is not False`.

Every site where a value could be `0` or `'()` gets a `# chez: #f only` comment. Item
03's utilities tests and the batteries catch most slips. A slip shows up as a codelet
taking a different branch, which the traces locate.

### Symbols, strings and characters

The model uses `symbol?` only to tell a symbol from a *list* (answers.ss:140,
themes.ss:595, trace.ss:83, justify.ss:242, 245), never from a string. It never prints
with `write`/`~s`; the only `~s` is in run.ss's `no-prompt` error and in fonts.ss's
debugging. It never compares a string with `eq?`. So:
- **symbols are Python `str`** (`'bond` → `"bond"`), and so are Scheme strings.
  `string->symbol` and `symbol->string` are the identity. `symbol_p(x)` is
  `isinstance(x, str)`, which is all the model's tests need.
- characters are 1-character `str` (only `symbol->letter-categories` and the string
  utilities use them).
- *Item 02:* where the printer's `write` (`~s`) must tell them apart, a Scheme string is a
  `chez.String` and a character a `chez.Char` (both `str` subclasses). A plain `str` is
  written as a symbol. A vector that must print as `#(...)` is a `chez.Vector` (a `list`
  subclass). `display` prints all of these alike.
- `INVALID = sys.intern("invalid-message-indicator")` is compared with `is`, so every
  producer uses the constant.
- The test canonicaliser (helpers.scm's `b:canon`) prints `'sym` and `"str"`
  differently. Python tests either know which fields are strings or accept both
  spellings for a `str`. That costs nothing, since the model never relies on the
  distinction.

Risk: a future site that does rely on it. Item 03 greps for `symbol?`, `string?`, `eq?`
on string literals and `~s` again and records the result.

### One-armed `if`, `case`, `record-case`

- `(if test then)` (common) → `if test: then`. As a *value* it is `None` when false. The
  `for*` forms and `delegate` pass such values on, so keep `None`.
- `case` with single datums (`(case x (rule-scout ...))`, coderack.ss:474, 523) →
  `if x == "rule-scout"`, or `in (...)` for a list of keys. Chez compares with `eqv?`;
  the keys are symbols and small integers, for which `==` agrees.
- `record-case` on data (trace.ss events) → `if`/`elif` on `ls[0]`, binding the formals
  **as Chez does: with car/cdr, so extra arguments are ignored and too few raise**
  (anomalies: "Chez's record-case ignores extra arguments"). On objects, see "Objects".

### Top-level values created at run time, and `eval`

`chez.py` keeps one table, as racket/compat.rkt does:
`define_top_level_value(name, value)`, `top_level_value(name)`,
`set_top_level_value_bang(name, value)` (binds an unbound name, as Chez does in its interaction environment; Racket raised. Item 02 fixture), `top_level_bound_p(name)`. An unbound `top_level_value` raises `chez.UnboundVariable`.
Users:
- slipnet.ss:371, `establish-link`, defines each of the 202 links as `a-b-link`; the link
  macros then message it through `top_level_value`;
- `slipnet-node-list*` and `codelet-type-list*` (syntactic-sugar.ss:149, 236) define each
  `plato-...` node and codelet type. In Python they are also module attributes
  (`slipnet.plato_a`, `coderack.bottom_up_bond_scout`), made in the same order of
  `make-slipnode`/`make-codelet-type` calls. This is the Racket port's
  `define-slipnet-node-list*`;
- utilities.ss:240, `symbol->letter-categories`, the original's only `eval` (of
  `plato-a` etc.) → `top_level_value("plato-a")`;
- `reveal-obj` (utilities.ss) reads `format-slipnode` (rules.ss) as a top-level value.
  rules.py must register it; Racket item 09 missed this and item 17 fixed it.

Names the original never defines but `set!`s or reads (`*temperature-clamped?*`,
`*initial-slipnode-unclamp-time*`, read before any `set!`; `same-direction?`,
`complement-codelet-pattern`, never defined; anomalies) are defined in their natural
module as Racket's `pending.rktl` does: the first two `False`, the last two raising
`UnboundVariable` as Chez would.

### Continuations

- **`continuation-point*`** (15 sites: bonds.ss:90, groups.ss:295, 860, utilities.ss:75,
  86, rules.ss:1267, answers.ss:1283, justify.ss:184, 261, run.ss:100, 114, 148, and the
  codelet wrapper of `define-codelet-procedure*`) only ever escapes upwards, except at
  run.ss:100/114. → `sugar.continuation_point(body)`: `body` receives an escape
  procedure that raises a private `_Escape(token, value)`. The form catches only its own
  token and returns the value. An escape after the form has returned raises an error,
  as with call/ec. `fizzle` (the escape of the running codelet, a global set by every
  codelet) is `sugar.fizzle`, set through the codelet wrapper.
- **`break`/`quiet-break`/`go`** (run.ss:97–133) are the one re-entrant use: `break` can
  be reached from deep inside a codelet (answers.ss:81, 92 call `suspend`, which calls
  `break`), and `go` resumes the rest of that codelet. Python can't capture that.
  - **headless** (CLI, goldens): as the oracle's run.ss does, `break` is replaced by a
    driver procedure that ends the run by raising `StopRun(reason)`, or returns at once
    with `--keep-going`.
  - **GUI** (item 15): the engine runs in a worker thread, and `break` blocks it on a
    `threading.Event` until `go` (from the control panel) sets it. The code after the
    break point then continues, as the continuation would. `*interrupt?*` and the step
    mode are flags the GUI thread sets. Views are called on the engine thread and must
    only queue drawing for Tk's thread (`after` polling), so they can't change the run.
  - `reset` (Chez's REPL abort) → `raise Reset()`; `report-error-and-halt` reaches it.
- **Python recursion depth.** The model recurses over short lists, and `remq`-style
  helpers are written as loops. The engine sets `sys.setrecursionlimit(10000)` as a
  margin. The known infinite recursion (an object without `object-type` sent a bad
  message: report-error-and-halt recurses forever, in the original too) shows up as a
  `RecursionError`. The prototype test hit it while it was being written.

### Printing

`chez.display`, `chez.write`, `chez.format_` (`~a ~s ~% ~n ~~`, either case; others raise),
`chez.printf` and `newline` as in compat.rkt §4: `display` abbreviates `(quote x)` as
`'x` and `write` doesn't; symbols are written with Chez's `\xHH;` escapes; characters
and strings are written with Chez's names and escapes; `#<void>`; Python lists print as
Scheme lists, `True`/`False` as `#t`/`#f`, `None` as `#<void>` (item 02 correction;
fixture `format-void`). Symbols with non-ASCII characters outside R6RS's constituent
categories are written with `\xHH;` (item 02). Never `str()`/`repr()` a number where Chez prints it. The trace writer
(trace-format.md) has its own JSON rules: exact rationals as `"n/d"` strings, flonums
through `number_to_string`.

`printf` writes to the *current* `sys.stdout` at call time (syntactic-sugar.ss captured
the port at load time; the Racket port does the same as Python here).

## Objects

### The original

`(lambda msg (let ((self (1st msg))) (record-case (rest msg) clause ... (else
(delegate msg parent ...)))))`: 72 `record-case` forms (52 in the model; a few dispatch
on data, not messages), 4,243
`tell` sites (3,161 in the model), 60 `delegate` uses. `(tell obj 'm a)` applies `obj`
to `(obj m a)` and halts on `'invalid-message-indicator`. `delegate` passes the same
message, **self included**, to each parent in turn. So a parent's code that does
`(tell self ...)` talks to the child, and the parent's closure variables are its own.
Parents are separate objects: a bond's `workspace-structure`, a group's
`workspace-object` and `workspace-structure` (two parents, in that order), graphics
windows delegating to a `graphics-window`, fonts to a `font`. Several objects end with
`(delegate msg base-object)`, the root that knows only `object-type`. An object without
an `else` clause returns void for an unknown message, which `tell` does **not** treat as
an error. Objects are procedures, and `procedure?` tells them from other values
(`print`, `say-object`, `slipnode?`). The trace instrumentation replaces `*coderack*`
and `*workspace*` with forwarders `(lambda msg (apply original original (cdr msg)))`.

### How often

`python/oracle/count-calls.ss` runs the unedited oracle with `tell` and `delegate`
wrapped:

| Run | Codelets | `tell` | per codelet | `delegate` (falls through) |
|---|---:|---:|---:|---:|
| abc abd xyz, seed 3852097033 | 2,170 | 2,242,151 | 1,033 | 275,578 (12%) |
| abc abd mrrjjj, seed 1 | 1,250 | 1,353,867 | 1,083 | 199,956 (15%) |
| eqe qeq abbba, seed 2 | 988 | 830,331 | 840 | 108,192 (13%) |
| abc abd iijjkk, seed 3 | 4,204 | 4,960,867 | 1,180 | 867,794 (17%) |

About **1,000 messages per codelet**, one in six going through `delegate`.

### Candidates and the micro-benchmark

`python3 python/tests/object_prototypes.py` (Python 3.12.13, this machine; ns per
operation, minimum of 5 repeats). The test object has 40 messages and delegates to a
parent with 15, which delegates to `base-object` (bond → workspace-structure →
base-object):

| Candidate | 1st message | 20th of 40 | 40th of 40 | delegated (parent's 8th) | delegated twice (`object-type` at the root) | create child + parent |
|---|---:|---:|---:|---:|---:|---:|
| A closure + `if`/`elif` chain (literal record-case) | 149 | 336 | 507 | 709 | 756 | 190 |
| B closure + dict of inner closures | 227 | 228 | 229 | 386 | 449 | 4,389 |
| C class per object, dict of messages, instance callable as `(self, msg, *args)` | 266 | 263 | 264 | 474 | 581 | 145 |
| C2 = C, `tell` looks up the dict itself | 157 | 157 | 158 | 644 | 742 | 145 |
| **C3 = C, every object a `SchemeObject`; `tell` and `delegate` look up the dict** | **173** | **172** | **173** | **297** | **396** | **146** |
| D Python inheritance, `tell` = `getattr` by mangled name | 147 | 146 | 148 | 149 | 141 | 110 |
| (a plain method call `obj.get_m20()`) | | 28 | | | | |

- **A** is the most literal, but its cost grows with the message's position: the
  largest record-cases have 92 clauses (workspace-objects.ss), 91 (workspace-strings.ss)
  and 72 (bridges.ss).
- **B** makes one closure per message for every object: 30× C's creation cost, and
  the model creates many short-lived objects (descriptions, proposed structures,
  images).
- **D** is the fastest, but it merges a parent's state into the child. It can't
  express delegation to a separate, existing object (windows, fonts, the battery's
  `delegate` test), and child and parent variables with the same name collide
  (`string` in both a bond and its workspace-structure). It changes the structure the
  plan wants to keep side by side.
- **C3 keeps the original's protocol exactly and costs about 0.2 µs per message**: at
  1,000 messages per codelet that is about 0.2 ms per codelet. A would cost about twice
  that.

All of A, B, C and C3 pass the same Chez-fixture tests (`tell`, `tell-args`,
`tell-alias`, `tell-invalid`, `base-object`, `delegate`, `delegate-to-all`,
`delegate-to-all-order`, `delegate-to-all-invalid`, `tell-all-order`,
`record-case-no-else`) and the self-through-delegation and forwarder checks.
Mutations caught: a left-to-right `tell-all` (4 failures), `delegate` passing the
parent instead of `self` (C and C3, 1 each), `tell` not halting (7), a missing `else`
returning invalid (1).

### Decision: C3

```python
class Bond(SchemeObject):
    """bonds.ss: make-bond (the closure's variables are attributes of `this`)."""
    __slots__ = ("workspace_structure", "from_object", "to_object", "bond_category", ...)

    def __init__(this, from_object, to_object, bond_category, bond_facet,
                 from_object_descriptor, to_object_descriptor):
        this.workspace_structure = make_workspace_structure()   # the let*, in order
        ...

    @message("object-type")
    def object_type(this, self):
        return "bond"

    @message("get-string")
    def get_string(this, self):
        return this.string

    def otherwise(this, self, msg, args):                      # (else (delegate msg ...))
        return delegate(self, msg, args, this.workspace_structure)


def make_bond(from_object, to_object, bond_category, bond_facet,
              from_object_descriptor, to_object_descriptor):
    """bonds.ss: make-bond"""
    return Bond(from_object, to_object, bond_category, bond_facet,
                from_object_descriptor, to_object_descriptor)
```

- `objects.py` (item 03): `SchemeObject` (`__slots__`, `MESSAGES` built by
  `__init_subclass__` from `@message(name, ...)` methods, `__call__(this, self, msg,
  *args)` for the protocol, `otherwise` returning `None` like a record-case without
  `else`), `message`, `tell`, `delegate`, `delegate_to_all`, `tell_all`, `BASE_OBJECT`,
  `Forwarder`, `INVALID`, `procedure_p` (`callable`). `tell(obj, msg, *args)` stays a
  plain function, so it can be passed to `map` and `sort-by-method`.
- `this` is the object whose closure it is; `self` is the receiver from the message.
  The method signature `(this, self, *formals)` keeps both visible. A `set!` of a
  closure variable is `this.x = ...`.
- **Messages keep their Scheme names as strings** (`tell(bond, "get-string")`), so the
  4,000 call sites read like the original, `sort-by-method` and `tell-all` take message
  names as data, and `Ooops: bad message "..."` and the trace's `halt` event print them
  unchanged. The Python method names follow the name mapping.
- `record-case` clauses with several keys (`((alias1 alias2) () ...)`) list all the
  names in `@message`. Rest formals `(a . more)` become `*more` (a tuple: convert with
  `list()` where the list escapes).
- **Arity.** Chez's record-case ignores extra arguments and raises on missing ones;
  Python raises on both. The one known extra-argument site (trace.ss:442, 473–478,
  `draw-string-letters` with a tag, graphics only) gets an `*_ignored` parameter and a
  `# chez:` comment. Item 14 checks for others with the panels battery.
- Construction follows the closure's `let`/`let*` order exactly. Some `make-...` bodies
  create parents or draw before the `lambda`.
- Objects with nested `record-case` (coderack.ss:267) dispatch in a method body.

Item 12 may speed up dispatch further (local aliases of `tell` in hot loops, caching the
parent's table), keeping every trace identical.

### As built (item 03)

`python/metacat/objects.py` is C3, with these details fixed by the utilities battery:
- `delegate(self, msg, args, *parents)` and `delegate_to_all(self, msg, args, *objects)`
  take the message split into its parts, as they are called from `otherwise(this, self,
  msg, args)`. `delegate` passes `self` on; `delegate_to_all` gives each object itself
  as self and runs in `chez.map_` order. A parent whose record-case has no `else`
  answers void (`None`), which `delegate` returns as an answer, as in Chez.
- `Lambda(fn)` wraps a plain `(lambda msg ...)` object, `fn(self, msg, *args)`, for
  stand-ins and objects that dispatch by hand. `Forwarder`, `base_object` (also
  `BASE_OBJECT`), `procedure_p` (`callable`), `Reset` and `INVALID` are as planned.
- `MESSAGES` also collects `@message` methods from SchemeObject base classes, so a Python
  subclass may share clauses. Delegation to a separate object is still `delegate`.
- `tell` calls `report_error_and_halt` through the module global, so a run's driver
  replaces `objects.report_error_and_halt` (run.ss's `set!`). utilities.py re-exports the
  object procedures, but replacing them there would not reach `tell`.
- Measured (this machine): `tell` 135 ns, delegated once 247 ns, twice 367 ns, creating
  a child and its parent 111 ns.

`python/metacat/sugar.py` makes every extend-syntax form a function:
- bodies the macro would delay are thunks (`stochastic_if_star(prob_thunk, exps_thunk)`
  draws the coin, then calls `prob_thunk`; `if_star`; `repeat_star_*`;
  `continuation_point_star(body)` passes the escape to `body`);
- a form with several patterns is one function per pattern: `for_star(f, *lists)` and
  `for_star_from_to(lo, hi, f)` (the caller evaluates `lo` then `hi`),
  `repeat_star_times`/`_forever`/`_until`, `category_links_star(instances, c, len)` and
  `instance_links_star(c, instances, len)` for the `all-lengths:` forms, keyword
  arguments `length=`, `label=` and `two_way=` for `lateral-link*` and
  `lateral-sliplink*`;
- `mcat`'s validity test is a fender in the original, so bad tokens raise
  `chez.SchemeError` (a syntax error) without telling the control panel;
- the names a macro leaves free are read at call time from the engine module that
  defines them: `metacat.setup.p_verbose` and `.g_control_panel`,
  `metacat.coderack.g_coderack` and `.make_codelet_type`,
  `metacat.slipnet.make_slipnode` and `.establish_link`. Those modules don't exist yet;
  tests provide them with `engine_module(...)` in test_utilities.py, which patches the real
  module once it exists;
- `slipnet_node_list_star(specs, module=None)` and `codelet_type_list_star(specs,
  module=None)` define top-level values, and also module attributes (through
  `names.scheme_to_python`) when given the module;
- `define_codelet_procedure_star(name, proc)` looks the codelet type up as a top-level
  value and sets `sugar.fizzle` while the codelet runs. Codelet code calls
  `sugar.fizzle()`, always qualified;
- in model code, `for*`, `if*` and `stochastic-if*` are usually written inline
  (`for x in l:`; `coin = chez.random(1.0)` then `if coin < p:`). The functions are for
  sites that use the form's value.

`python/metacat/utilities.py` has one function per definition, under the mapped name
(`1st` → `first`, `~` → `rough`, `filter` → `filter_` ...); a test checks that every
`define` of utilities.ss and syntactic-sugar.ss has its Python name. Vectors and tables
are `chez.Vector`. `coord` is `chez.make_rectangular`, which needs `chez.ExactComplex` for
exact coordinates (anomalies entry); coordinate arithmetic is left to the graphics
items. `(ascending-index-list 0)` loops forever, as in the original and the Racket port.

**Strings vs symbols, re-checked (item 03).** The graphics (`string?` in
sgl-interpreter.ss, general-graphics.ss, fonts.ss, gui.ss) and rules.ss:269
(`filter-out symbol?`) *do* tell strings from symbols. The items that translate those
files must keep the distinction there (anomalies: "The graphics and rules.ss tell strings
from symbols").

### As built (item 04)

- **`engine.py`** has metacat.ss's load order (`LOAD_ORDER`, Python module names).
  `load()` imports the modules translated so far and calls their `load()`, once per
  process. `set_global(name, value)` / `get_global(name)` map the Scheme name through
  `names.scheme_to_python` to the first module of the load order (plus `view_globals`)
  that defines it, and raise `chez.SchemeError` otherwise.
- **References to files not translated yet** go through the package at call time:
  `import metacat as _metacat`, then `_metacat.workspace.g_workspace`,
  `_metacat.run.g_display_mode_p`, `_metacat.groups.contains_p`. Once such a module exists
  this still works (engine.py imports it); later items may switch a module to
  `from metacat import workspace` when the target exists. Tests provide the globals of
  missing modules with `tests/engine_stubs.engine_module`.
- **`view_globals.py`** mirrors racket/engine/view-globals.rktl: the colours and fonts the
  model reads (`urgency-color`, the codelet types' graphics methods, trace events), the
  speed settings and `restore-current-state`, all `#f` (or raising) until the views set
  them. constants.py keeps only the model's part of constants.ss.
- **setup.py**: `setup` and `enable-resizing` are the GUI's (item 15). Other modules read
  and assign the globals qualified (`setup.g_temperature`).
- **coderack.py**: the codelet closure that make-codelet makes is the `Codelet` class. It
  shares variables with its codelet type's closure (count, selection probability,
  procedure, window), so it keeps that object as `owner` and the message's receiver as
  `codelet_type`. Codelet lists are rebuilt on every cons and `remq`, never mutated, so a
  list handed out stays as it was. `case` without `else` returns `None` (void), as the
  battery's `post-codelet-probability` rows show. `load()` makes `*codelet-types*` with
  `codelet_type_list_star(..., module=coderack)`, whose labels are `chez.String`s (the
  graphics tell strings from symbols), then the three type lists and `*coderack*`.
- **descriptions.py**: `load()` runs the four `define-codelet-procedure*` forms.
- **Arithmetic on values that may be `#f`** goes through `chez.add`/`sub`/`mul`, since
  Python's `bool` is an `int` (anomalies entry).

## Names

`python/metacat/names.py` (`scheme_to_python`; moved into the package by item 03) maps every name the
original defines (about 1,300) to a valid, non-reserved Python identifier, and
`test_name_mapping.py` checks that the mapping is injective on all of them.

| Scheme | Python | Example |
|---|---|---|
| `-` | `_` | `make-bond` → `make_bond` |
| `?` | `_p` | `foo-bar?` → `foo_bar_p`, `CMs-equal?` → `CMs_equal_p` |
| `!` | `_bang` | `vector-increment!` → `vector_increment_bang` |
| `->` | `_to_` | `bridge-type->theme-type` → `bridge_type_to_theme_type` |
| `*x*` (global variable) | `g_x` | `*temperature*` → `g_temperature`, `*EEG*` → `g_EEG` |
| `%x%` (parameter: tunable constants and switches) | `p_x` | `%verbose%` → `p_verbose` |
| `=x=` (colour) | `c_x` | `=white=` → `c_white` |
| trailing `*` (the extend-syntax forms) | `_star` | `stochastic-if*` → `stochastic_if_star` (item 03 decides which of them become functions and which become statements) |
| `:` | `__` | `group-scout:whole-string` → `group_scout__whole_string` |
| `/` | `_or_` | `ObjCtgy/Length-change?` → `ObjCtgy_or_Length_change_p` |
| `.` | `_` | `fig5.10` → `fig5_10` |
| Python keyword or builtin | trailing `_` | `break` → `break_`, `print` → `print_`, `round` → `round_`, `filter` → `filter_`, `sum` → `sum_` |
| case | kept | `plato-a` → `plato_a` |
| exceptions | fixed table | `1st` … `8th` → `first` … `eighth`; `1-`, `10-`, `100-` → `one_minus`, `ten_minus`, `hundred_minus`; `100*` → `times_100`; `%`, `20%`, `40%`, `80%` → `percent`, `percent_20`, …; `^2`, `^3` → `square`, `cube`; `~` → `rough`; `?` (themes.ss's help) → `theme_help`; `180/pi`, `pi/180` → `degrees_per_radian`, `radians_per_degree` |

Locals and parameters follow the same rules. Message names stay Scheme strings (above).
Module names: `workspace-strings.ss` → `workspace_strings.py`. Every function's
docstring starts with its origin (`"""bonds.ss: bond-builder"""`).

## The global top level and Python modules

The original loads 44 files into one top level (metacat.ss's order). Definitions refer
to each other across files in both directions (coderack.ss names the codelet procedures
of eleven later files; descriptions.ss calls back into later files). Files also `set!`
each other's globals: 27 globals are assigned outside their defining file (`*temperature*`
by answers.ss, formulas.ss and run.ss; the workspace strings by run.ss; the mode switches
by gui.ss; `*fg-color*` by four graphics files; ...). Drivers and tests replace about 150
more from outside (the trace wrappers `build-bond`, `break-group`, … and the fakes of
the batteries; Racket's `set-global!` list in racket/engine.rkt).

Racket had to include everything into one module. Python can do better:

1. **One module per `.ss` file** (`metacat/bonds.py` for bonds.ss), one function per
   definition, in the original's order within the file.
2. **Definitions only at import time.** A module's top level holds `def`s, classes and
   constants that need nothing from another engine module except `chez`, `objects`,
   `sugar` and `utilities`. Every top-level `define` whose value needs another module
   (building the slipnet's nodes and 202 links, the codelet types, `*workspace*`,
   `*themespace*`, `*trace*`, `*memory*`, ...) is computed
   in the module's `load()` function, which assigns the module global. So modules can
   import each other freely, cycles included (`from metacat import bonds, groups` at
   the top; Python ≥ 3.7 resolves partially initialised submodules).
3. **Load order is explicit**: `metacat/engine.py` imports every engine module, then
   `load()` calls each module's `load()` in metacat.ss's order (syntactic-sugar,
   utilities, constants, setup, coderack, descriptions, bonds, groups, bridges,
   breakers, workspace, workspace-objects, workspace-structures, workspace-strings,
   concept-mappings, workspace-structure-formulas, run, formulas, slipnet, images, rules,
   answers, themes, justify, trace, jootsing, memory, then the engine parts of the
   graphics files, demos). A reference to a later module during load fails, as in Chez.
4. **References.** Inside a module, names are used unqualified. Module globals are
   looked up at call time, so `setattr(bonds, "build_bond", wrapper)` reaches in-file
   callers too. **Across modules, always qualified**: `bonds.build_bond(...)`,
   `setup.g_temperature`. `chez`, `objects`, `sugar` and `utilities` are the exception:
   their names are imported directly (`from metacat.utilities import tell, prob_p, ...`)
   because nothing rebinds them. Never `from metacat.bonds import build_bond`, which
   copies the binding and silently defeats wrappers and `set!`.
5. **Assignment.** `(set! *temperature* 50)` in formulas.ss → `setup.g_temperature = 50`.
   Drivers and tests use `engine.set_global("*temperature*", 50)`, which maps the Scheme
   name to its defining module and attribute and raises if there is none. This is
   Racket's `set-global!` without the whitelist: Python modules allow `setattr`, and
   the check stops typos.
6. **A fresh engine per run.** The Memory and counters outlive a run (anomalies), and
   the oracle runs every golden in a fresh process. The Python golden runner loads the
   engine once, then forks one worker per run (`multiprocessing` with the `fork` start
   method), so every run starts from the state right after load.
7. **Engine modules never import tkinter.** Graphics code the model calls (group-graphics'
   `erase`, `group-event-pexp-text-string`, `relation-name`, the EEG object, rule pexps)
   is translated into engine modules that build data and send messages to window
   objects. The headless windows (null objects accepting the oracle's message list,
   porting-notes.md item 01) live in `headless.py`. A test walks the imports of every
   engine module (as racket/tests/no-gui-test.rkt does).

## Python-specific traps to log

These go into `docs/anomalies_and_quirks.md` when the code meets them:
- `dict` order is insertion order. Dicts serve only for dispatch and the top-level
  table, never for an order the model observes.
- `float.__repr__` differs from Chez's printer (above), and `str(Fraction(4, 2))` is
  `"2"` but its type isn't `int`.
- `bool` is a subclass of `int`: `True == 1`, `isinstance(True, int)`. `chez.eq_p` and
  the printer check `bool` first.
- Default recursion limit 1000.
- `round` on a `float` returns `int` (good). `round(x, n)` is never used; utilities.ss's
  `round-to-10ths` etc. are translated literally.
- Tuple vs list from `*args`.

## Order of the work

As in `iterations.md`, with these notes:

1. **02 `chez.py`**: PRNG, numbers (norm, div, mul, max/min, sqrt/exp/log/expt, tanh
   check), printer, `map_`, `sort`, `remq` family, `eq_p`/`equal_p`, `for_each`, top-level
   table, `UnboundVariable`. Capture scripts for vectors the utilities battery lacks:
   exact-zero products, contagion, exact sqrt/exp/log/expt, `float(Fraction)` rounding,
   evaluation-order probes for the record.
2. **03 `objects.py`, `sugar.py`, `utilities.py`**: C3 from the prototype; the 22 macros
   as functions (`stochastic_if_star(prob_thunk, body_thunk)` draws first), decorators
   (`define_codelet_procedure_star`) or explicit loops (`for*`, `repeat*`); the name
   mapping moves to `metacat/names.py`. All 197 utilities tests.
3. **04–10** the model, battery by battery, each through `engine.load()` and a Python
   version of the battery's harness (`tests/diff/codelet-harness.scm` → a pytest helper
   module). Each item: fixture tests first and failing, then the translation, an
   evaluation-order audit of its files, then `# chez:`/`# 1.2:` comments.
4. **11** run.ss, `trace.py`, `headless.py`, the CLI, and the 109 goldens in parallel.
   From here on the goldens are in the gate's tier.
5. **12** the 720 extra seeds, then profiling. Expected hot spots: `tell`, `Fraction`
   arithmetic, `chez.map_`, list copying.
6. **13–15** SGL on `tkinter.Canvas` (fixture: the oracle's `swl:tcl-eval` stream),
   panels as views, the control panel with the engine on a worker thread (the `break`
   design above), all under `xvfb-run`.
7. **16–17** packaging, README, final audit.

## Risks, ranked

1. **Truthiness** (new in Python). `0`, `Fraction(0)`, `[]` and `""` are false in Python
   and true in Scheme. A slip quietly takes the other branch. Mitigation: the rules
   above, `# chez: #f only` comments, and the batteries, which exercise branches with
   zero activations and empty lists. The traces show a slip within one codelet.
2. **Exactness.** A float where Chez is exact (Python `/`, `math.sqrt` of a perfect
   square, `0 * float`, `max` contagion) changes urgencies and probabilities. Mitigation:
   `chez.div`/`mul`/`max_`, a `Fraction` normalisation helper, and item 02's vectors.
   The trace prints urgencies as `"n/d"`, so a stray float shows up at once
   (`20.4` instead of `"102/5"`).
3. **Speed.** About 1,000 messages per codelet, plus `Fraction` arithmetic. Projection:
   2–5 ms per codelet, so 5–25 s for a typical golden and up to about 85 s for the
   17,000-codelet `eqe qeq abbba aaabaaa` run. On 32 cores the 109 goldens (273,000
   codelets) take about 1–2 minutes and the 720 extra seeds (2.15 M codelets) about
   5–10 minutes, which is too slow for every gate. Mitigation: a fork-after-load worker
   pool, a fast tier per item, the full golden suite in the gate from item 11, and the
   extra seeds in a slow tier. Item 12 measures and decides.
4. **Evaluation order.** Python is uniformly left to right, which removes Racket's
   surprises but keeps Chez's. The known sites are listed above. Unknown ones show up as
   an `rng` mismatch in a trace. Mitigation: per-item audits, and the codelet-level
   harness batteries, which have long runs (2000–3000 codelets) that reached
   groups.ss's site where 400-codelet runs didn't.
5. **`map`/`sort` order with side effects.** One shared `chez.map_` and `chez.sort`,
   never `map()`/`sorted()` where effects or ties exist. The utilities battery pins
   both, predicate calls included.
6. **Module load order and globals.** A `from x import y` of a rebindable name, or
   cross-module work at import time, breaks the wrappers or the load order silently.
   Mitigation: the rules above, plus a test that imports each engine module alone (no
   cross-module calls at import time) and an AST check that engine modules don't
   `from`-import names from each other.
7. **The `break`/`go` resume** in the GUI (threads), and the views' thread discipline.
   Mitigation: item 15's control-panel test runs stop/resume runs to the golden's
   codelet count and generator state, as Racket's did.
8. **Symbols as `str`.** Safe for the model as audited. A later site that needs the
   distinction would need a `Symbol` type. Low.
9. **Faithful bugs.** The `report-error-and-halt` runs, the `caddr` crash of `abc ccbbaa
   ijk` seed 3, the recursion when `object-type` is missing, the latent errors in the
   anomalies file. Python must crash or halt at the same codelet, with the same output.
   The goldens and cli tests include the halt and the crash. Python's exception for the
   crash is a `TypeError`/`IndexError` where Chez says `caddr`, so the CLI maps it to the
   oracle's exit code 1 and stdout; stderr text may differ (as in Racket).

## What makes it easier than it looks

- The oracle, 109 goldens, 720 extra-seed results, and 604 frozen battery fixtures
  already exist. Every expected value is one file read away (`chez("battery", "test")`).
- The Racket port is a line-for-line, golden-equivalent translation of the same files.
  Where a Scheme form is unclear, the `.rktl` next to it shows a working reading.
- No hash tables, no threads, no `eval` beyond one name lookup, and only 8 direct
  `random` calls plus the utilities.ss helpers.
