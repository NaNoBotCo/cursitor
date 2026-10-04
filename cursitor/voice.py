"""A writing checker for the firm's own voice.

    cursitor voice <files>... [--words voice.json]

Three lists, each configurable: filler words, throat-clearing openings, and absolute assurances
in the writer's own voice. Text inside quotation marks is skipped, since a quoted witness or
statute keeps its own words. A line holding `voice: allow` is skipped. Exit 1 on a hit.

The lists come from, in order: --words FILE, voice.json in the matter folder,
~/.cursitor/voice.json, then the defaults below. A JSON file may set "filler", "throat",
"assurance" (lists of regular expressions) and "extend": true to add to the defaults.
"""
import json
import os
import re

# voice: allow-start  (stylecheck: allow-start — this list names the words it flags)
DEFAULTS = {
    "filler": [r"\bjust\b", r"\bactually\b", r"\bsimply\b", r"\bbasically\b", r"\brobust\b", r"\bseamless(ly)?\b",
               r"\bleverag(e|es|ed|ing)\b", r"\bensur(e|es|ed|ing)\b", r"\bcrucial(ly)?\b", r"\bvery\b",
               r"\breally\b", r"\bclearly\b", r"\bobviously\b"],
    "throat": [r"^\s*great question", r"^\s*let me\b", r"^\s*i'?ll go ahead", r"^\s*i hope this (email|letter) finds you",
               r"^\s*as you (may )?know", r"^\s*needless to say", r"^\s*it goes without saying"],
    "assurance": [r"\bwe never\b", r"\bwe always\b", r"\balways\b", r"\bguarantee(d|s)?\b",
                  r"\b100\s?%", r"\bwithout (a )?doubt\b", r"\bcertainly\b", r"\bundoubtedly\b"],
}
# voice: allow-end  (stylecheck: allow-end)

QUOTES = [re.compile(a + r".{0,800}?" + b) for a, b in (("“", "”"), ('"', '"'))]
APOS = re.compile(r"(?<=\w)['’](?=\w)")


def load_lists(words=None, matter=None):
    cands = [words, os.path.join(matter, "voice.json") if matter else None,
             os.path.join(os.path.expanduser(os.environ.get("CURSITOR_HOME") or "~/.cursitor"), "voice.json")]
    for c in cands:
        if c and os.path.exists(c):
            with open(c, encoding="utf-8") as fh:
                cfg = json.load(fh)
            out = {k: list(v) for k, v in DEFAULTS.items()} if cfg.get("extend") else {k: [] for k in DEFAULTS}
            for k in DEFAULTS:
                out[k].extend(cfg.get(k, []))
            return out, c
    return DEFAULTS, "defaults"


def scan(text, lists, where="-"):
    hits = []
    off = False
    for n, line in enumerate(text.splitlines(), 1):
        if "voice: allow-start" in line:
            off = True
            continue
        if "voice: allow-end" in line:
            off = False
            continue
        if off or "voice: allow" in line:
            continue
        masked = APOS.sub("\x00", line)
        spans = [m.span() for q in QUOTES for m in q.finditer(masked)]
        for kind in ("throat", "filler", "assurance"):
            for pat in lists.get(kind, []):
                for m in re.finditer(pat, line, re.I):
                    if any(a <= m.start() < b for a, b in spans):
                        continue
                    hits.append("%s:%d  %s  %r" % (where, n, kind.upper(), m.group(0)))
    return hits


def check_files(paths, words=None, matter=None):
    lists, _src = load_lists(words, matter)
    hits = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            hits.extend(scan(fh.read(), lists, p))
    return hits
