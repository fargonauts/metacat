"""Prototype of the Scheme -> Python name mapping (item 01; docs/python-translation-plan.md).

Part of the Python translation of Metacat (GPL v2 or later, like Metacat itself).

Item 03 moves this into the package; until then it pins the rules, and
test_name_mapping.py checks them on every name the original defines.
"""
from __future__ import annotations

import builtins
import keyword
import re
from pathlib import Path

ORIGINAL = Path(__file__).resolve().parents[2] / "chez_scheme" / "original"

# Names no rule handles well: digits first, or a lone operator.
EXCEPTIONS = {
    "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
    "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
    "1-": "one_minus",            # (- 1 x)
    "10-": "ten_minus", "100-": "hundred_minus",
    "100*": "times_100",          # (round (* 100 x))
    "%": "percent",               # (/ n 100)
    "20%": "percent_20", "40%": "percent_40", "80%": "percent_80",
    "^2": "square", "^3": "cube",
    "~": "rough",                 # roughly n (draws)
    "?": "theme_help",            # themes.ss: prints the theme abbreviations
    "180/pi": "degrees_per_radian", "pi/180": "radians_per_degree",
}

# Python names a Scheme name must not take: keywords and the builtins.
RESERVED = set(keyword.kwlist) | set(keyword.softkwlist) | set(dir(builtins))


def scheme_to_python(name: str) -> str:
    """The fixed mapping, applied in this order:

    1. EXCEPTIONS
    2. markers around the whole name: *x* -> g_x (global variable), %x% -> p_x
       (parameter, Marshall's tunable constants), =x= -> c_x (colour)
    3. a trailing * (the extend-syntax forms) -> _star
    4. inside the name: -> to _to_, ? to _p, ! to _bang, : to __, / to _or_,
       . and - to _
    5. a Python keyword or builtin gets a trailing _
    """
    if name in EXCEPTIONS:
        return EXCEPTIONS[name]
    prefix = ""
    for mark, pre in (("*", "g_"), ("%", "p_"), ("=", "c_")):
        if len(name) > 2 and name.startswith(mark) and name.endswith(mark):
            name, prefix = name[1:-1], pre
            break
    suffix = ""
    if name.endswith("*") and len(name) > 1:
        name, suffix = name[:-1], "_star"
    name = name.replace("->", "-to-")
    name = re.sub(r"\?", "-p", name)
    name = name.replace("!", "-bang")
    name = name.replace(":", "--")
    name = name.replace("/", "-or-")
    name = name.replace(".", "-")
    out = prefix + name.replace("-", "_") + suffix
    if out in RESERVED:
        out += "_"
    return out


def original_names() -> dict[str, str]:
    """Every name the original defines, with the file that first defines it:
    (define name ...), (define (name ...) ...), extend-syntax keywords, codelet types
    (codelet-type-list*) and slipnodes (slipnet-node-list*)."""
    names: dict[str, str] = {}

    def add(name, f):
        names.setdefault(name, f)
    for path in sorted(ORIGINAL.glob("*.ss")):
        text = path.read_text(errors="replace")
        text = re.sub(r";[^\n]*", "", text)
        for m in re.finditer(r"\(define\s+\(?([^\s()]+)", text):
            add(m.group(1), path.name)
        for m in re.finditer(r"\(extend-syntax\s+\(([^\s()]+)", text):
            add(m.group(1), path.name)
        for block in ("codelet-type-list\\*", "slipnet-node-list\\*"):
            m = re.search(r"\(%s(.*?)\)\)\s*\n\s*\n" % block, text, re.S)
            if m and "extend-syntax" not in text[max(0, m.start() - 40):m.start()]:
                for item in re.finditer(r"\(\s*([^\s()\"]+)", m.group(1)):
                    add(item.group(1), path.name)
    return names
