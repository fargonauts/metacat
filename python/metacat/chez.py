"""Chez Scheme 10 semantics that Metacat 1.2 relies on.

Metacat is copyright (c) 1999, 2003 by James B. Marshall; this translation is free
software under the GNU General Public License, version 2 or later, like Metacat
itself.  Translated to Python (2026) from the Chez Scheme built-ins that the
original (chez_scheme/original/) uses, with racket/compat.rkt as a worked
translation.  Every behaviour here is pinned by a Chez fixture: see
python/tests/test_chez.py, python/oracle/batteries/chez-battery.scm and
docs/python-translation-plan.md.

Sections:
  1. data representations (symbols, strings, characters, pairs, vectors, void)
  2. errors
  3. the global random number generator (docs/trace-format.md)
  4. numbers: exactness, contagion, rounding, sqrt/exp/log/tanh/expt
  5. lists: map (Chez's order), for-each, andmap, ormap, sort (Chez's algorithm),
     remq/remv/remove, memq.../assq..., eq?/eqv?/equal?
  6. top-level values
  7. printing: number->string, display, write, format, printf, newline

The engine never imports tkinter; this module imports only the standard library.
"""
from __future__ import annotations

import math
import sys
import unicodedata
from fractions import Fraction

__all__ = [
    "String", "Char", "Pair", "Vector",
    "SchemeError", "UnboundVariable", "error",
    "random", "random_seed",
    "norm", "add", "sub", "mul", "div", "max_", "min_", "abs_", "quotient", "remainder", "modulo",
    "exact_p", "inexact_p", "integer_p", "rational_p", "number_p", "zero_p", "positive_p",
    "negative_p", "add1", "sub1", "exact", "inexact", "round_", "floor_", "ceiling", "truncate",
    "exact_round", "exact_floor", "exact_ceiling", "exact_truncate",
    "sqrt", "exp", "log", "tanh", "expt",
    "map_", "for_each", "andmap", "ormap", "sort", "remq", "remv", "remove",
    "memq", "memv", "member", "assq", "assv", "assoc", "eq_p", "eqv_p", "equal_p",
    "TOP_LEVEL", "define_top_level_value", "top_level_value", "set_top_level_value_bang",
    "top_level_bound_p",
    "number_to_string", "display", "write", "format_", "fprintf", "printf", "newline",
    "display_string", "write_string",
]

# ---------------------------------------------------------------------------
# 1. Data representations
#
# A Scheme symbol is a plain Python str ('bond -> "bond").  The model never
# needs to tell a symbol from a string (docs/python-translation-plan.md), so
# Scheme strings are plain str too, except where `write` (~s) must print one
# with quotes: there the value is a String.  Characters are 1-character str;
# Char marks one for `write`.  A proper list is a Python list (or tuple); a
# pair whose cdr is not a list is a Pair; a vector is a Python list, or a
# Vector where it must print as #(...).  #t/#f are True/False, '() is [],
# and the unspecified value (void) is None.


class String(str):
    """A Scheme string, where the printer must tell it from a symbol."""
    __slots__ = ()


class Char(str):
    """A Scheme character, where the printer must tell it from a symbol."""
    __slots__ = ()


class Pair:
    """A pair whose cdr is not a proper list: (car . cdr)."""
    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __repr__(self):
        return f"Pair({self.car!r}, {self.cdr!r})"


class Vector(list):
    """A Scheme vector, where the printer must tell it from a list."""
    __slots__ = ()


def _is_exact(x) -> bool:
    t = type(x)
    return t is int or t is Fraction


def _is_number(x) -> bool:
    t = type(x)
    return t is int or t is float or t is Fraction or t is complex


# ---------------------------------------------------------------------------
# 2. Errors


class SchemeError(Exception):
    """A Chez error condition: (error who message irritant ...)."""

    def __init__(self, who, message, *irritants):
        self.who = who
        self.message = message
        self.irritants = irritants
        text = message
        try:
            text = format_(message, *irritants)
        except SchemeError:
            pass
        super().__init__(f"{who}: {text}" if who is not None and who is not False else text)


class UnboundVariable(SchemeError):
    """Chez's "variable x is not bound"."""

    def __init__(self, name):
        super().__init__(None, "variable ~a is not bound", name)
        self.name = name


def error(who, message, *irritants):
    """Chez: error.  Raises; who is a symbol, a string or #f."""
    raise SchemeError(who, message, *irritants)


# ---------------------------------------------------------------------------
# 3. The random number generator
#
# Chez 10's global generator (docs/trace-format.md): one 32-bit state S,
# S := S*72931 + 90763387 mod 2^32.  Python's own random is never used.

_S = 1
_MOST_POSITIVE_FIXNUM = (1 << 60) - 1
_TWO_POW_MINUS_52 = 2.220446049250313e-16


def random_seed(n=None):
    """Chez: random-seed.  With no argument, the state; with one, set it
    (an exact integer from 1 to 2^32 - 1)."""
    global _S
    if n is None:
        return _S
    if type(n) is Fraction and n.denominator == 1:
        n = n.numerator
    if type(n) is not int or not 1 <= n <= 0xFFFFFFFF:
        raise SchemeError("random-seed", "invalid argument ~s", n)
    _S = n
    return None


def random(x):
    """Chez: random.  An exact positive integer n gives an integer in [0, n);
    a positive flonum x gives M/2^52 * x, M a 52-bit draw."""
    global _S
    t = type(x)
    if t is float:
        if not x > 0.0:
            raise SchemeError("random", "invalid argument ~s", x)
        s1 = (_S * 72931 + 90763387) & 0xFFFFFFFF
        s2 = (s1 * 72931 + 90763387) & 0xFFFFFFFF
        s3 = (s2 * 72931 + 90763387) & 0xFFFFFFFF
        s4 = (s3 * 72931 + 90763387) & 0xFFFFFFFF
        _S = s4
        m = ((((s1 >> 16) & 15) << 48) | ((s2 >> 16) << 32) | ((s3 >> 16) << 16) | (s4 >> 16))
        # m/2^52 is exact as a double, so this rounds once, as Chez does
        return (m * _TWO_POW_MINUS_52) * x
    if t is Fraction and x.denominator == 1:
        x = x.numerator
        t = int
    if t is not int or x <= 0:
        raise SchemeError("random", "invalid argument ~s", x)
    if x > _MOST_POSITIVE_FIXNUM:
        raise NotImplementedError("random: bignum ranges are not supported")   # never drawn
    s1 = (_S * 72931 + 90763387) & 0xFFFFFFFF
    s2 = (s1 * 72931 + 90763387) & 0xFFFFFFFF
    v = (s1 >> 16) + (s2 & 0xFFFF0000)
    if x <= 0xFFFFFFFF:
        _S = s2
        return v % x
    s3 = (s2 * 72931 + 90763387) & 0xFFFFFFFF
    s4 = (s3 * 72931 + 90763387) & 0xFFFFFFFF
    _S = s4
    v = ((v << 16) + (s3 >> 16)) & 0xFFFFFFFFFFFFFFFF
    v = ((v << 16) + (s4 >> 16)) & 0xFFFFFFFFFFFFFFFF
    return v % x


# ---------------------------------------------------------------------------
# 4. Numbers
#
# Exact integers are int, exact non-integers Fraction (always normalised:
# a Fraction with denominator 1 becomes an int), flonums float.  Python's
# operators differ from Chez's in exactness: exact 0 times a flonum is exact
# 0 in Chez, exact 0 plus or minus a flonum keeps the flonum's sign
# ((+ 0 -0.0) is -0.0), max/min are inexact if either argument is, and an
# exact quotient is never a float.  Use these wherever an operand may be a
# flonum or a quotient is exact.


def norm(x):
    """A Fraction with denominator 1 as an int; anything else unchanged."""
    if type(x) is Fraction and x.denominator == 1:
        return x.numerator
    return x


def _check(x, who):
    if not _is_number(x):
        raise SchemeError(who, "~s is not a number", x)


def _add2(a, b):
    if type(a) is int and a == 0:           # exact 0 is the identity: (+ 0 -0.0) is -0.0
        _check(b, "+")
        return b
    if type(b) is int and b == 0:
        _check(a, "+")
        return a
    _check(a, "+")
    _check(b, "+")
    r = a + b
    return r.numerator if type(r) is Fraction and r.denominator == 1 else r


def add(*xs):
    """Chez: +"""
    r = 0
    for x in xs:
        r = _add2(r, x)
    return r


def _sub2(a, b):
    _check(a, "-")
    _check(b, "-")
    if type(b) is int and b == 0:
        return a
    if type(a) is int and a == 0:           # (- 0 0.0) is -0.0
        return -b
    r = a - b
    return r.numerator if type(r) is Fraction and r.denominator == 1 else r


def sub(a, *more):
    """Chez: -"""
    if not more:
        _check(a, "-")
        return -a
    for b in more:
        a = _sub2(a, b)
    return a


def _mul2(a, b):
    _check(a, "*")
    _check(b, "*")
    if (type(a) is int and a == 0) or (type(b) is int and b == 0):
        return 0                            # exact 0 annihilates, even a flonum
    r = a * b
    return r.numerator if type(r) is Fraction and r.denominator == 1 else r


def mul(*xs):
    """Chez: *"""
    r = 1
    for x in xs:
        r = _mul2(r, x)
    return r


def _div2(a, b):
    _check(a, "/")
    _check(b, "/")
    if type(b) is int and b == 0:
        raise SchemeError("/", "undefined for ~s", 0)
    if type(a) is int and a == 0:
        return 0                            # (/ 0 2.5) and (/ 0 0.0) are exact 0
    if _is_exact(a) and _is_exact(b):
        r = Fraction(a, b) if type(a) is int and type(b) is int else Fraction(a) / b
        return r.numerator if r.denominator == 1 else r
    if type(b) is complex or type(a) is complex:
        return a / b
    fa, fb = float(a), float(b)
    if fb == 0.0:                           # IEEE division by a signed zero
        if fa == 0.0 or fa != fa:
            return math.nan
        return math.copysign(math.inf, fa) * math.copysign(1.0, fb)
    return fa / fb if type(a) is not float or type(b) is not float else a / b


def div(a, *more):
    """Chez: /"""
    if not more:
        return _div2(1, a)
    for b in more:
        a = _div2(a, b)
    return a


def _max2(a, b):
    r = a if a > b else b
    if type(a) is float or type(b) is float:
        return float(r)
    return r


def _min2(a, b):
    r = a if a < b else b
    if type(a) is float or type(b) is float:
        return float(r)
    return r


def max_(a, *more):
    """Chez: max (inexact if any argument is)"""
    _check(a, "max")
    for b in more:
        _check(b, "max")
        a = _max2(a, b)
    return a


def min_(a, *more):
    """Chez: min (inexact if any argument is)"""
    _check(a, "min")
    for b in more:
        _check(b, "min")
        a = _min2(a, b)
    return a


def abs_(x):
    """Chez: abs"""
    _check(x, "abs")
    return abs(x)


def quotient(a, b):
    """Chez: quotient (truncates)"""
    if b == 0:
        raise SchemeError("quotient", "undefined for ~s", 0)
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def remainder(a, b):
    """Chez: remainder (sign of the dividend)"""
    return a - b * quotient(a, b)


def modulo(a, b):
    """Chez: modulo (sign of the divisor, as Python's %)"""
    if b == 0:
        raise SchemeError("modulo", "undefined for ~s", 0)
    return a % b


def number_p(x) -> bool:
    return _is_number(x)


def exact_p(x) -> bool:
    _check(x, "exact?")
    return _is_exact(x)


def inexact_p(x) -> bool:
    _check(x, "inexact?")
    return not _is_exact(x)


def integer_p(x) -> bool:
    t = type(x)
    if t is int:
        return True
    if t is Fraction:
        return x.denominator == 1
    if t is float:
        return math.isfinite(x) and x == math.floor(x)
    return False


def rational_p(x) -> bool:
    t = type(x)
    return t is int or t is Fraction or (t is float and math.isfinite(x))


def zero_p(x) -> bool:
    _check(x, "zero?")
    return x == 0


def positive_p(x) -> bool:
    return x > 0


def negative_p(x) -> bool:
    return x < 0


def add1(x):
    """Chez: 1+, add1"""
    return _add2(x, 1)


def sub1(x):
    """Chez: -1+, sub1"""
    return _sub2(x, 1)


def exact(x):
    """Chez: inexact->exact"""
    if type(x) is float:
        if not math.isfinite(x):
            raise SchemeError("inexact->exact", "no exact representation for ~s", x)
        return norm(Fraction(x))
    _check(x, "inexact->exact")
    return x


def inexact(x):
    """Chez: exact->inexact (correctly rounded, as Python's float())"""
    t = type(x)
    if t is float or t is complex:
        return x
    _check(x, "exact->inexact")
    try:
        return float(x)
    except OverflowError:
        return math.inf if x > 0 else -math.inf


def _flround(f, x):
    """A Chez rounding primitive on a flonum: a flonum, the sign of zero kept."""
    if not math.isfinite(x):
        return x
    r = float(f(x))
    return math.copysign(r, x) if r == 0.0 else r


def round_(x):
    """Chez: round (half to even; a flonum stays a flonum)"""
    if type(x) is float:
        return _flround(round, x)
    _check(x, "round")
    return norm(round(x)) if type(x) is Fraction else x


def floor_(x):
    """Chez: floor"""
    if type(x) is float:
        return _flround(math.floor, x)
    _check(x, "floor")
    return math.floor(x)


def ceiling(x):
    """Chez: ceiling"""
    if type(x) is float:
        return _flround(math.ceil, x)
    _check(x, "ceiling")
    return math.ceil(x)


def truncate(x):
    """Chez: truncate"""
    if type(x) is float:
        return _flround(math.trunc, x)
    _check(x, "truncate")
    return math.trunc(x)


def exact_round(x):
    """utilities.ss: round, (inexact->exact (scheme-round n))"""
    return exact(round_(x))


def exact_floor(x):
    """utilities.ss: floor"""
    return exact(floor_(x))


def exact_ceiling(x):
    """utilities.ss: ceiling"""
    return exact(ceiling(x))


def exact_truncate(x):
    """utilities.ss: truncate"""
    return exact(truncate(x))


def _exact_sqrt(x):
    """The exact square root of a non-negative exact x, or None."""
    n, d = x.numerator, x.denominator
    rn, rd = math.isqrt(n), math.isqrt(d)
    if rn * rn == n and rd * rd == d:
        return rn if rd == 1 else Fraction(rn, rd)
    return None


def sqrt(x):
    """Chez: sqrt (exact for exact perfect squares; a negative argument gives
    an imaginary result with an inexact 0.0 real part)"""
    t = type(x)
    if t is float:
        if x < 0.0:
            return complex(0.0, math.sqrt(-x))
        return math.sqrt(x)
    _check(x, "sqrt")
    if t is complex:
        import cmath
        return cmath.sqrt(x)
    if x < 0:
        if _exact_sqrt(-x) is not None:
            raise NotImplementedError("sqrt of a negative perfect square (an exact complex in Chez)")
        return complex(0.0, math.sqrt(inexact(-x)))
    r = _exact_sqrt(x)
    if r is not None:
        return r
    return math.sqrt(inexact(x))


def _flexpt(b: float, p: float):
    """A flonum power as Chez computes it: libm's pow, an infinity for a zero
    base and a negative power, exp(p log b) for a negative base and a
    non-integer power."""
    if b == 0.0 and p < 0.0:
        odd = p == math.floor(p) and math.fmod(p, 2.0) != 0.0
        return math.copysign(math.inf, b) if odd else math.inf
    if b < 0.0 and p != math.floor(p):
        import cmath
        return cmath.exp(p * cmath.log(b))
    try:
        return b ** p
    except OverflowError:
        return math.inf


def expt(b, p):
    """Chez: expt.  An exact 0 power gives exact 1; an exact integer power of
    an exact base is exact; a power of 1/2 is sqrt; an exact 1 base gives 1 and
    an exact 0 base gives 0 (an error for a negative power); otherwise flonums
    (docs/python-translation-plan.md, fixtures expt-table, expt-extra)."""
    _check(b, "expt")
    _check(p, "expt")
    tp = type(p)
    if tp is int:
        if p == 0:
            return 1
        if _is_exact(b):
            if b == 0 and p < 0:
                raise SchemeError("expt", "undefined for values ~s and ~s", b, p)
            r = b ** p if p > 0 else Fraction(b) ** p
            return r.numerator if type(r) is Fraction and r.denominator == 1 else r
        if type(b) is complex:
            return b ** p
        return _flexpt(b, float(p))
    if tp is Fraction and p == Fraction(1, 2):
        return sqrt(b)
    if _is_exact(b):
        if b == 1:
            return 1
        if b == 0:
            if p > 0:
                return 0
            if tp is float and p == 0.0:
                return 1.0
            raise SchemeError("expt", "undefined for values ~s and ~s", b, p)
    return _flexpt(inexact(b), inexact(p))


def exp(x):
    """Chez: exp ((exp 0) is exact 1)"""
    if type(x) is int and x == 0:
        return 1
    _check(x, "exp")
    try:
        return math.exp(inexact(x))
    except OverflowError:
        return math.inf


def log(x):
    """Chez: log ((log 1) is exact 0; (log 0) is an error)"""
    t = type(x)
    if t is int and x == 1:
        return 0
    _check(x, "log")
    if _is_exact(x) and x == 0:
        raise SchemeError("log", "undefined for ~s", 0)
    f = inexact(x)
    if f == 0.0:
        return -math.inf
    if f < 0.0 or f != f:
        import cmath
        return cmath.log(f) if f < 0.0 else f
    if f == math.inf:
        return f
    return math.log(f)


def tanh(x):
    """Chez: tanh ((tanh 0) is exact 0)"""
    if type(x) is int and x == 0:
        return 0
    _check(x, "tanh")
    return math.tanh(inexact(x))


# ---------------------------------------------------------------------------
# 5. Lists


def _length_error(who, lists):
    raise SchemeError(who, "lists ~s are not all the same length", list(lists))


def map_(f, *lists):
    """Chez: map, in Chez's order of application.  One or two lists: pairs of
    elements from the end of the list towards the front (an odd last element
    alone, first), e.g. 7 5 6 3 4 1 2; three or more lists: last to first."""
    if len(lists) == 1:
        ls = lists[0]
        n = len(ls)
        out = [None] * n
        i = n - 2
        if n % 2 == 1:
            out[n - 1] = f(ls[n - 1])
            i = n - 3
        while i >= 0:
            out[i] = f(ls[i])
            out[i + 1] = f(ls[i + 1])
            i -= 2
        return out
    if len(lists) == 2:
        l1, l2 = lists
        n = len(l1)
        if len(l2) != n:
            _length_error("map", lists)
        out = [None] * n
        i = n - 2
        if n % 2 == 1:
            out[n - 1] = f(l1[n - 1], l2[n - 1])
            i = n - 3
        while i >= 0:
            out[i] = f(l1[i], l2[i])
            out[i + 1] = f(l1[i + 1], l2[i + 1])
            i -= 2
        return out
    if not lists:
        raise SchemeError("map", "no lists")
    n = len(lists[0])
    if any(len(ls) != n for ls in lists):
        _length_error("map", lists)
    out = [None] * n
    for i in range(n - 1, -1, -1):
        out[i] = f(*[ls[i] for ls in lists])
    return out


def for_each(f, *lists):
    """Chez: for-each, first to last; its value is the last application's
    (void for empty lists), which the for* forms pass on."""
    r = None
    if len(lists) == 1:
        for x in lists[0]:
            r = f(x)
        return r
    n = len(lists[0])
    if any(len(ls) != n for ls in lists):
        _length_error("for-each", lists)
    for i in range(n):
        r = f(*[ls[i] for ls in lists])
    return r


def andmap(f, *lists):
    """Chez: andmap, first to last, stopping at the first #f; the last value."""
    r = True
    n = len(lists[0])
    for i in range(n):
        r = f(*[ls[i] for ls in lists])
        if r is False:
            return False
    return r


def ormap(f, *lists):
    """Chez: ormap, first to last; the first value that is not #f."""
    n = len(lists[0])
    for i in range(n):
        r = f(*[ls[i] for ls in lists])
        if r is not False:
            return r
    return False


def sort(pred, ls):
    """Chez: (sort pred list), Chez 10's own algorithm (s/5_6.ss), so that
    predicates that are not strict orders, and the sequence of predicate calls,
    are as in Chez: below 25 elements a top-down list merge sort that sorts the
    second half first, otherwise Olin Shivers's vector merge sort.  Returns a
    new list."""
    n = len(ls)
    if n < 25:
        if n <= 1:
            return list(ls)
        return _dolsort(pred, list(ls), 0, n)
    v = list(ls)
    return _dovsort(pred, v, n)


def _dolsort(pred, ls, start, n):
    if n == 1:
        return [ls[start]]
    if n == 2:
        x, y = ls[start], ls[start + 1]
        return [y, x] if pred(y, x) is not False else [x, y]
    i = n >> 1
    b = _dolsort(pred, ls, start + i, n - i)     # the second half first
    a = _dolsort(pred, ls, start, i)
    return _dolmerge(pred, a, b)


def _dolmerge(pred, a, b):
    out = []
    i = j = 0
    na, nb = len(a), len(b)
    while i < na and j < nb:
        if pred(b[j], a[i]) is not False:
            out.append(b[j])
            j += 1
        else:
            out.append(a[i])
            i += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out


def _vmerge(pred, target, v1, v2, l, len1, len2):
    """Merge v1[l, l+len1) and v2[l+len1, l+len1+len2) into target[l, ...)."""
    r1 = l + len1
    r2 = r1 + len2
    i, j, k = l, l, r1
    x, y = v1[l], v2[r1]
    while True:
        if pred(y, x) is not False:
            k += 1
            target[i] = y
            if k < r2:
                i += 1
                y = v2[k]
            else:
                _vblit(v1, j, target, i + 1, r1)
                return
        else:
            j += 1
            target[i] = x
            if j < r1:
                i += 1
                x = v1[j]
            else:
                if v2 is not target:
                    _vblit(v2, k, target, i + 1, r2)
                return


def _vblit(fromv, j, tov, i, n):
    while True:
        tov[i] = fromv[j]
        j += 1
        if j == n:
            return
        i += 1


def _getrun(pred, v, l, r):
    i = l + 1
    x = v[l]
    while True:
        if i == r:
            return i - l
        y = v[i]
        if pred(y, x) is not False:
            return i - l
        i += 1
        x = y


def _dovsort(pred, v0, n):
    temp0 = [None] * n

    def recur(l, want):
        pfxlen = _getrun(pred, v0, l, n)
        v, temp = v0, temp0
        while not (pfxlen >= want or pfxlen == n - l):
            outlen, outvec = recur(l + pfxlen, pfxlen)
            _vmerge(pred, temp, v, outvec, l, pfxlen, outlen)
            pfxlen, v, temp = pfxlen + outlen, temp, v
        return pfxlen, v

    _, out = recur(0, n)
    return list(out)


def eq_p(a, b) -> bool:
    """Chez: eq?  Symbols (str), characters, fixnums, booleans and '() by value
    or identity as Chez's immediates; everything else by identity."""
    if a is b:
        return True
    ta, tb = type(a), type(b)
    if ta is not tb:
        return False
    if ta is str or ta is Char or ta is int:
        return a == b
    if ta is list and not a and not b:
        return True
    return False


def eqv_p(a, b) -> bool:
    """Chez: eqv?  eq?, or numbers of the same exactness and value (flonums
    bit for bit: (eqv? 0.0 -0.0) is #f, (eqv? +nan.0 +nan.0) is #t)."""
    if eq_p(a, b):
        return True
    ta, tb = type(a), type(b)
    if ta is not tb:
        return False
    if ta is Fraction:
        return a == b
    if ta is float:
        if a != a:
            return b != b
        return a == b and math.copysign(1.0, a) == math.copysign(1.0, b)
    if ta is complex:
        return eqv_p(a.real, b.real) and eqv_p(a.imag, b.imag)
    return False


def _as_pair(x):
    """(car, cdr) of a non-empty list or a Pair, else None."""
    if type(x) is Pair:
        return x.car, x.cdr
    if isinstance(x, (list, tuple)) and not isinstance(x, Vector) and x:
        return x[0], x[1:]
    return None


def equal_p(a, b) -> bool:
    """Chez: equal?  eqv?, or strings, pairs and vectors with equal contents."""
    if eqv_p(a, b):
        return True
    ta, tb = type(a), type(b)
    if ta is String and tb is String:
        return str.__eq__(a, b)
    if ta is Vector and tb is Vector:
        return len(a) == len(b) and all(equal_p(x, y) for x, y in zip(a, b))
    if isinstance(a, (list, tuple, Pair)) and isinstance(b, (list, tuple, Pair)) \
            and ta is not Vector and tb is not Vector:
        if (ta is list or ta is tuple) and (tb is list or tb is tuple):
            return len(a) == len(b) and all(equal_p(x, y) for x, y in zip(a, b))
        pa, pb = _as_pair(a), _as_pair(b)
        if pa is None or pb is None:
            return pa is None and pb is None and not a and not b
        return equal_p(pa[0], pb[0]) and equal_p(pa[1], pb[1])
    return False


def remq(x, ls):
    """Chez: remq (removes every occurrence)"""
    return [y for y in ls if not eq_p(y, x)]


def remv(x, ls):
    """Chez: remv (removes every occurrence)"""
    return [y for y in ls if not eqv_p(y, x)]


def remove(x, ls):
    """Chez: remove (removes every occurrence)"""
    return [y for y in ls if not equal_p(y, x)]


def _mem(same, x, ls):
    for i, y in enumerate(ls):
        if same(x, y):
            return ls[i:]
    return False


def memq(x, ls):
    """Chez: memq (the tail, or #f)"""
    return _mem(eq_p, x, ls)


def memv(x, ls):
    """Chez: memv"""
    return _mem(eqv_p, x, ls)


def member(x, ls):
    """Chez: member"""
    return _mem(equal_p, x, ls)


def _car(p):
    return p.car if type(p) is Pair else p[0]


def _ass(same, x, alist):
    for p in alist:
        if same(x, _car(p)):
            return p
    return False


def assq(x, alist):
    """Chez: assq (the entry, or #f)"""
    return _ass(eq_p, x, alist)


def assv(x, alist):
    """Chez: assv"""
    return _ass(eqv_p, x, alist)


def assoc(x, alist):
    """Chez: assoc"""
    return _ass(equal_p, x, alist)


# ---------------------------------------------------------------------------
# 6. Top-level values
#
# The original creates global variables from computed names (slipnet.ss's
# establish-link, the slipnet and codelet macros) and looks names up with eval
# (utilities.ss's symbol->letter-categories).  They live in one table, keyed
# by Scheme name.

TOP_LEVEL: dict = {}


def define_top_level_value(name, value):
    """Chez: define-top-level-value"""
    TOP_LEVEL[name] = value


def set_top_level_value_bang(name, value):
    """Chez: set-top-level-value!  In Chez's interaction environment an
    unbound name is bound, not an error (fixture top-level-values)."""
    TOP_LEVEL[name] = value


def top_level_value(name):
    """Chez: top-level-value"""
    try:
        return TOP_LEVEL[name]
    except KeyError:
        raise UnboundVariable(name) from None


def top_level_bound_p(name) -> bool:
    """Chez: top-level-bound?"""
    return name in TOP_LEVEL


# ---------------------------------------------------------------------------
# 7. Printing, as Chez Scheme 10 prints (s/print.ss)


def _flonum_digits(x: float):
    """(digits, e) for a positive finite x: the shortest digits that read back
    to x (Python's repr gives the same digits as Chez), without leading or
    trailing zeros, and the decimal exponent of the first digit."""
    s = repr(x)
    epos = s.find("e")
    if epos >= 0:
        mant, exp10 = s[:epos], int(s[epos + 1:])
    else:
        mant, exp10 = s, 0
    dot = mant.find(".")
    if dot < 0:
        dot = len(mant)
        whole = mant
    else:
        whole = mant[:dot] + mant[dot + 1:]
    lead = len(whole) - len(whole.lstrip("0"))
    digits = whole.strip("0")
    e = exp10 + dot - lead - 1
    # chez: when x lies exactly halfway between the two shortest candidates,
    # Python's repr rounds the last digit half to even and Chez's free-format
    # printer rounds it up (1586243275893042.25 prints as ...042.3 in Chez,
    # ...042.2 in Python; docs/anomalies_and_quirks.md)
    k = len(digits)
    unit = Fraction(10) ** (e - k + 1)
    lower = int(digits) * unit
    if Fraction(x) - lower == unit / 2:
        up = str(int(digits) + 1)
        e_up = e + (len(up) - k)
        up = up.rstrip("0")
        if float(up[0] + "." + (up[1:] or "0") + "e" + str(e_up)) == x:
            return up, e_up
    return digits, e


def _flonum_to_string(x: float) -> str:
    if x != x:
        return "+nan.0"
    if x == math.inf:
        return "+inf.0"
    if x == -math.inf:
        return "-inf.0"
    sign = "-" if math.copysign(1.0, x) < 0 else ""
    ax = abs(x)
    if ax == 0.0:
        return sign + "0.0"
    digits, e = _flonum_digits(ax)
    if e <= -4 or e >= 10:
        body = digits[0] + ("." + digits[1:] if len(digits) > 1 else "") + "e" + str(e)
    elif e < 0:
        body = "0." + "0" * (-e - 1) + digits
    else:
        int_len = e + 1
        if int_len >= len(digits):
            body = digits + "0" * (int_len - len(digits)) + ".0"
        else:
            body = digits[:int_len] + "." + digits[int_len:]
    if ax < 2.2250738585072014e-308:      # subnormal: Chez adds the precision
        m = (Fraction(ax) * (1 << 1074)).numerator.bit_length()
        if 0 < m < 53:
            body += "|" + str(m)
    return sign + body


def number_to_string(z) -> str:
    """Chez: number->string (radix 10)"""
    t = type(z)
    if t is float:
        return _flonum_to_string(z)
    if t is int or t is Fraction:
        return str(z)
    if t is complex:
        re, im = z.real, z.imag
        sign = "" if (im < 0.0 or math.copysign(1.0, im) < 0 or im != im or im == math.inf) else "+"
        return _flonum_to_string(re) + sign + _flonum_to_string(im) + "i"
    raise SchemeError("number->string", "~s is not a number", z)


_CHAR_NAMES = {0: "nul", 7: "alarm", 8: "backspace", 9: "tab", 10: "newline", 11: "vtab",
               12: "page", 13: "return", 27: "esc", 32: "space", 127: "delete"}
_LINE_SEPARATORS = (0x85, 0x2028)
_STRING_ESCAPES = {7: "a", 8: "b", 10: "n", 12: "f", 13: "r", 9: "t", 11: "v"}
_INITIAL = set("*=<>/!$%&:?^_~")
_SUBSEQUENT = set("-?*!=><$%&/:^_~+.@")
_ABBREVIATIONS = {"quote": "'", "quasiquote": "`", "unquote": ",", "unquote-splicing": ",@",
                  "syntax": "#'", "quasisyntax": "#`", "unsyntax": "#,", "unsyntax-splicing": "#,@"}


# chez: R6RS constituents beyond ASCII; other characters are written \xHH;
# in a symbol (U+00AB, U+00AD, U+00A0, U+0080-U+009F, U+FEFF, ...)
_CONSTITUENT = {"Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Nl", "No", "Pd", "Pc", "Po", "Sc", "Sm",
                "Sk", "So", "Co"}
_SUBSEQUENT_ONLY = {"Nd", "Mc", "Me"}


def _alpha(c: str) -> bool:
    return "a" <= c <= "z" or "A" <= c <= "Z"


def _hex(c: str) -> str:
    return "\\x%X;" % ord(c)


def _write_char(c: str, out: list):
    o = ord(c)
    out.append("#\\")
    name = _CHAR_NAMES.get(o)
    if name is not None:
        out.append(name)
    elif 0x21 <= o <= 0x7E or (o >= 0x80 and o not in _LINE_SEPARATORS):
        out.append(c)
    else:
        out.append("x%X" % o)


def _write_string(s: str, out: list):
    out.append('"')
    for c in s:
        o = ord(c)
        if c == '"' or c == "\\":
            out.append("\\" + c)
        elif 0x20 <= o <= 0x7E or (o >= 0x80 and o not in _LINE_SEPARATORS):
            out.append(c)
        elif o in _STRING_ESCAPES:
            out.append("\\" + _STRING_ESCAPES[o])
        else:
            out.append(_hex(c))
    out.append('"')


def _write_symbol(s: str, out: list):
    n = len(s)
    if n == 0:
        out.append("||")
        return
    c = s[0]
    if _alpha(c) or c in _INITIAL:
        out.append(c)
    elif c == ".":
        out.append(c if s == "..." else _hex(c))
    elif c == "-":
        out.append(c if n == 1 or s[1] == ">" else _hex(c))
    elif c == "+":
        out.append(c if n == 1 else _hex(c))
    elif ord(c) >= 0x80 and unicodedata.category(c) in _CONSTITUENT:
        out.append(c)
    else:
        out.append(_hex(c))
    for c in s[1:]:
        if _alpha(c) or "0" <= c <= "9" or c in _SUBSEQUENT or (
                ord(c) >= 0x80 and (unicodedata.category(c) in _CONSTITUENT
                                    or unicodedata.category(c) in _SUBSEQUENT_ONLY)):
            out.append(c)
        else:
            out.append(_hex(c))


def _elements(x):
    """The elements of a list or Pair chain, and its final cdr (None if proper)."""
    items = []
    while True:
        if type(x) is Pair:
            items.append(x.car)
            x = x.cdr
        elif isinstance(x, (list, tuple)) and not isinstance(x, Vector):
            items.extend(x)
            return items, None
        else:
            return items, x


def _print(x, out: list, write: bool):
    if x is True:
        out.append("#t")
    elif x is False:
        out.append("#f")
    elif x is None:
        out.append("#<void>")
    else:
        t = type(x)
        if t is str:
            if write:
                _write_symbol(x, out)
            else:
                out.append(x)
        elif t is int or t is float or t is Fraction or t is complex:
            out.append(number_to_string(x))
        elif t is String:
            if write:
                _write_string(x, out)
            else:
                out.append(x)
        elif t is Char:
            if write:
                _write_char(x, out)
            else:
                out.append(x)
        elif t is Vector:
            out.append("#(")
            for i, e in enumerate(x):
                if i:
                    out.append(" ")
                _print(e, out, write)
            out.append(")")
        elif t is list or t is tuple or t is Pair:
            items, tail = _elements(x)
            if not items:
                out.append("()")
                return
            # display abbreviates (quote x) as 'x; write does not
            if not write and tail is None and len(items) == 2 and type(items[0]) is str \
                    and items[0] in _ABBREVIATIONS:
                out.append(_ABBREVIATIONS[items[0]])
                _print(items[1], out, write)
                return
            out.append("(")
            for i, e in enumerate(items):
                if i:
                    out.append(" ")
                _print(e, out, write)
            if tail is not None:
                out.append(" . ")
                _print(tail, out, write)
            out.append(")")
        elif callable(x):
            # Chez also names procedures (#<procedure name>); not reproduced
            out.append("#<procedure>")
        else:
            raise TypeError(f"chez: no Scheme printed form for {x!r}")


def display_string(x) -> str:
    """What Chez's display prints for x."""
    out: list = []
    _print(x, out, False)
    return "".join(out)


def write_string(x) -> str:
    """What Chez's write prints for x."""
    out: list = []
    _print(x, out, True)
    return "".join(out)


def display(x, port=None):
    """Chez: display (to the current sys.stdout by default)"""
    (port or sys.stdout).write(display_string(x))


def write(x, port=None):
    """Chez: write"""
    (port or sys.stdout).write(write_string(x))


def _format(control: str, args) -> str:
    out: list = []
    n = len(control)
    i = 0
    k = 0
    while i < n:
        c = control[i]
        if c == "~" and i + 1 < n:
            d = control[i + 1].lower()
            if d == "a" or d == "s":
                if k >= len(args):
                    raise SchemeError("format", "too few arguments for control string ~s", String(control))
                _print(args[k], out, d == "s")
                k += 1
            elif d == "%" or d == "n":
                out.append("\n")
            elif d == "~":
                out.append("~")
            else:
                raise SchemeError("format", "unsupported directive ~~~a in ~s", d, String(control))
            i += 2
        else:
            out.append(c)
            i += 1
    if k < len(args):
        raise SchemeError("format", "too many arguments for control string ~s", String(control))
    return "".join(out)


def format_(control, *args) -> str:
    """Chez: (format control arg ...), the directives Metacat uses: ~a ~s ~% ~n
    ~~, in either case.  (format #f ...) is the same; (format #t ...) and
    (format port ...) are printf and fprintf."""
    return _format(control, args)


def fprintf(port, control, *args):
    """Chez: fprintf"""
    port.write(_format(control, args))


def printf(control, *args):
    """syntactic-sugar.ss: printf, to the sys.stdout current at the call (the
    original captured the port at load time; the Racket port does as here)."""
    sys.stdout.write(_format(control, args))


def newline(port=None):
    """syntactic-sugar.ss: newline"""
    (port or sys.stdout).write("\n")
