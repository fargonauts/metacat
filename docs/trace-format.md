# Trace format and randomness

This file specifies what the Racket port must reproduce bit for bit to be
compared with the Chez Scheme oracle. Item 01 settles the randomness plan
(below). Item 02 adds the JSON-lines trace format.

## Randomness plan (item 01)

**Decision: the oracle uses Chez Scheme 10's own `random` and `random-seed`,
unmodified, and the port reimplements them exactly.** No PRNG is swapped into
the oracle. The generator is a 32-bit linear congruential generator, simple
to reproduce in Racket with exact integers; `chez_scheme/oracle/tests/rng-check.ss`
checks this specification against Chez's built-ins, draw for draw and seed for
seed (11 seeds × 19 arguments × 200 draws, plus 2000 interleaved integer/float
draws), and it fails if a constant or bit field is changed.

Source: Chez Scheme v10.0.0, `c/prim5.c` (`s_fxrandom`, `s_flrandom`,
`s_random_seed`, `s_set_random_seed`), `c/number.c` (`S_random_double`) and
`s/5_3.ss` (`random`, `random-seed`). The comment there says the formula is
"based on Knuth". Note that Chez 10's `make-pseudo-random-generator` objects
(MRG32k3a, the same as Racket's) are a *different* generator from the global
`random`; Metacat uses only the global one, and Racket's `random` must not be
used for it.

### State
One unsigned 32-bit integer `S` (per thread in Chez; Metacat is single-threaded).

    step(S) = (S * 72931 + 90763387) mod 2^32

Each call of `step` replaces `S` with the new value; "the next value" below
means: perform `step` and take the new `S`.

### `(random-seed)` and `(random-seed n)`
`(random-seed)` returns `S`. `(random-seed n)` sets `S := n`; `n` must be an
exact integer with 1 ≤ n ≤ 2^32 − 1 (0 is rejected). The initial state of a
fresh Chez process is irrelevant: Metacat always seeds (`init-mcat`).

### `(random n)`, exact positive fixnum `n`
    s1 = next value; s2 = next value
    t  = floor(s1 / 2^16) + (s2 AND #xFFFF0000)     ; high halves of s1 and s2
    if n <= 2^32 - 1:  result = t mod n              ; 2 steps
    else:              s3 = next; s4 = next          ; 4 steps
                       t = (t * 2^16 + floor(s3 / 2^16)) mod 2^64
                       t = (t * 2^16 + floor(s4 / 2^16)) mod 2^64
                       result = t mod n
(`t` lives in a 64-bit `uptr`, hence the `mod 2^64`.) Bignum `n` (beyond
`most-positive-fixnum`) loops over fixnum draws; Metacat never draws with
such an `n` and the port need not support it.

### `(random x)`, positive flonum `x`
    s1, s2, s3, s4 = the next four values               ; 4 steps
    M = (floor(s1/2^16) mod 16) * 2^48 + floor(s2/2^16) * 2^32
        + floor(s3/2^16) * 2^16 + floor(s4/2^16)        ; 52-bit mantissa
    result = (1.M - 1.0) * x  =  fl*(M / 2^52, x)
The C code builds the double `1.M` (exponent 0) and subtracts 1.0, which is
exact, so the result is the flonum `M/2^52` (exactly representable) times
`x` with one IEEE multiplication. `(random 1.0)` is `M/2^52` exactly.

### What Metacat draws
`(random 1.0)` in `stochastic-if*`, `prob?`, `stochastic-pick` and friends;
`(random n)` with small `n` in `random-pick` etc.; `(random-seed seed)` in
`init-mcat`. Without a seed the Control Panel calls `randomize`
(seed from `(real-time)`) and then reads `(random-seed)`; `run.ss` does the
same when `--seed` is omitted, so such runs are not reproducible.

### The demo seeds replay
TASK.md and item 01 expected the seeds in `demos.ss`, chosen under the
1999-era Chez generator, not to replay. They do: the generator above appears
unchanged since then, and `chez_scheme/oracle/tests/demo-replay-check.ss`
confirms that five documented runs come out exactly as the comments in
`demos.ss` say (answer and time step): misc1 (justifies mmmrrj, 7794 steps),
misc2 (justifies abd, 1126), misc4 (b at 453, then y at 945), misc5 (flz, dlz,
then hlz at 1721) and the commented-out misc9 (dyz at 2257). misc3 does not
replay exactly (documented: kji 1240, kkkjjjiii 1470, kkjjii 1485; oracle:
kkjjii 1240, kkkjjjiii 1264, kkjjii 1280, kji 1317), nor do the "not used"
misc6–misc8. The dissertation's Chapter 5 runs (run1–run8, fig5.x) have not
been compared yet; that needs the dissertation's figures (item 12).

### Evaluation order: the other half of reproducing the draws
Reproducing the generator is not enough: the *order* of draws must match.
Chez does not evaluate procedure-call arguments left to right. Observed under
`scheme --script` (which is how the oracle loads the original):

    (f (show 1) (show 2) (show 3))   prints 312   ; user procedure, 3 args
    (list (show 1) (show 2) (show 3)) prints 312
    (let ((a (show 1)) (b (show 2))) ...) prints 21
    ((lambda (x y) x) (show 1) (show 2)) prints 21
    (+ (show 1) (show 2))             prints 12   ; inlined primitive
    (cons (show 1) (show 2))          prints 12

Racket evaluates left to right. Wherever the original has two or more
argument (or `let`-binding) expressions that draw random numbers or have
other order-dependent side effects (posting codelets, building structures,
trace events), the port must spell out Chez's order explicitly, and the
golden traces are the check. Each such site goes in `porting-notes.md`.

## Trace format (item 02)

Not yet specified.
