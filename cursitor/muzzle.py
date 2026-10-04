"""Check a draft against the matter's muzzles.txt.

    cursitor muzzle <draft> [matter-dir]

muzzles.txt holds one entry per line: a word, a name, a phrase or a regular expression, matched
without regard to case. A line starting with # is a note. Exit 1 when the draft contains any
entry, with the line number of each hit.
"""
import os
import re


def load(matter):
    p = os.path.join(matter, "muzzles.txt")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for n, ln in enumerate(fh, 1):
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            try:
                rx = re.compile(s, re.I)
            except re.error:
                rx = re.compile(re.escape(s), re.I)
            out.append((n, s, rx))
    return out


def check_text(text, muzzles, where="draft"):
    hits = []
    for ln_no, line in enumerate(text.splitlines(), 1):
        for mline, pat, rx in muzzles:
            for m in rx.finditer(line):
                hits.append("%s:%d  muzzle %r (muzzles.txt line %d) matched %r" % (where, ln_no, pat, mline, m.group(0)))
    return hits


def check(path, matter):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return check_text(text, load(matter), path)
