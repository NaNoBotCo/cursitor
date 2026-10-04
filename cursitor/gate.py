"""Read your own record before send.

    cursitor gate <draft> [matter-dir] [--read] [--top 15]

Pulls the subject terms out of a draft (repeated words and two-word phrases, request and
interrogatory numbers), searches the matter's served/ and received/ folders and notes/ for
passages on those subjects, and prints each passage with file and line.

Without --read it prints BLOCKED with the list and exits 1. With --read (you have read the
passages) it prints CLEARED, exits 0, and appends the acknowledgement to gate.log in the matter.
"""
import datetime as _dt
import hashlib
import os
import re

from . import pdftext

STOP = set("""a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its itself just me more most my no nor not now of off
on once only or other our out over own same she should so some such than that the their them then there
these they this those through to too under until up very was we were what when where which while who whom
why will with would you your yours dear sincerely regards please thank thanks write writing letter email
re cc bcc page also however therefore hereby herein thereof whether within without upon shall must may
january february march april june july august september october november december asked said told sent wrote
""".split())
# words every discovery paper uses; they say nothing about the subject
LEGAL = set("""plaintiff plaintiffs defendant defendants responding party propounding request requests
response responses responded respond interrogatory interrogatories special form production produce produced
document documents admission admissions set one two three objection objections objects subject waiving
counsel client clients your attorney court case action code civil procedure section discovery meet confer
conferred further verified verification served service serve deadline motion compel days day date dated
writing letter regarding concerning relating refer referring identify identified state states stated
information possession custody control reasonable diligent inquiry vague ambiguous overbroad burdensome
privilege privileged work product nos holdings llc inc corp company""".split())
NUMREF = re.compile(r"\b(?:special\s+interrogatory|interrogatory|request\s+for\s+production|request\s+for\s+admission|request|rfp|rfa|srog|rog)s?\s+(?:no\.?|number|#)\s*(\d+)", re.I)
RECORD_DIRS = ("served", "received", "notes")
TEXT_EXT = (".txt", ".md", ".pdf")


def _words(text):
    return re.findall(r"[a-z][a-z'-]{2,}", text.lower())


def subject_terms(text, limit=10, skip=()):
    skip = set(skip)
    words = [w.strip("'-") for w in _words(text)]
    words = [w for w in words if w not in skip]
    keep = [w for w in words if w not in STOP and w not in LEGAL and len(w) > 3]
    counts = {}
    for w in keep:
        counts[w] = counts.get(w, 0) + 1
    bigrams = {}
    for a, b in zip(words, words[1:]):
        if a in STOP or b in STOP or a in LEGAL or b in LEGAL or len(a) < 4 or len(b) < 4:
            continue
        k = a + " " + b
        bigrams[k] = bigrams.get(k, 0) + 1
    scored = [(c * 3 + len(k) / 40.0, k) for k, c in bigrams.items() if c >= 2]
    scored += [(c + len(k) / 60.0, k) for k, c in counts.items() if c >= 2]
    scored.sort(reverse=True)
    out = []
    for _s, k in scored:
        if any(k in o or o in k for o in out if " " in o or " " in k):
            # keep the phrase and the words not already inside it
            if " " in k and not any(" " in o and (k in o) for o in out):
                out = [o for o in out if o not in k.split()]
                out.append(k)
            continue
        out.append(k)
        if len(out) >= limit:
            break
    refs = set()
    for m in NUMREF.finditer(text):
        g = m.group(0).lower()
        kind = ("interrogatory" if ("interrog" in g or "rog" in g) else
                "admission" if ("admission" in g or "rfa" in g) else "request")
        refs.add("%s %s" % (kind, m.group(1)))
    refs = sorted(refs)
    return out[:limit], refs


def party_words(matter):
    """Words of the case name and parties: on every page of the record, so they say nothing."""
    p = os.path.join(matter, "matter.json")
    if not os.path.exists(p):
        return set()
    import json
    with open(p, encoding="utf-8") as fh:
        m = json.load(fh)
    vals = list(m.get("identifiers", [])) + [m.get("name", "")]
    for side in (m.get("parties") or {}).values():
        vals.extend(side)
    return set(w for v in vals for w in _words(v or ""))


def record_files(matter):
    out = []
    for d in RECORD_DIRS:
        base = os.path.join(matter, d)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for f in sorted(files):
                if f.lower().endswith(TEXT_EXT) and not f.startswith("."):
                    out.append(os.path.join(root, f))
    return sorted(out)


def _paragraphs(text):
    """[(first_line_no, paragraph)] split on blank lines; long blocks split every 8 lines."""
    out, buf, start = [], [], 1
    for n, ln in enumerate(text.split("\n"), 1):
        if not ln.strip() or len(buf) >= 8:
            if buf:
                out.append((start, " ".join(x.strip() for x in buf)))
            buf = [ln] if ln.strip() else []
            start = n
            continue
        if not buf:
            start = n
        buf.append(ln)
    if buf:
        out.append((start, " ".join(x.strip() for x in buf)))
    return out


def find_passages(matter, terms, refs, top=15):
    hits = []
    for path in record_files(matter):
        rel = os.path.relpath(path, matter)
        for page, text in pdftext.read_any(path):
            for line_no, para in _paragraphs(text):
                low = para.lower()
                matched = [t for t in terms if re.search(r"\b" + re.escape(t), low)]
                score = sum(2 if " " in t else 1 for t in matched)
                for r in refs:
                    kind, num = r.rsplit(" ", 1)
                    if re.search(r"\bno\.?\s*" + num + r"\b", low) and kind[:6] in low:
                        score += 2
                        matched.append(r)
                if score >= 2:
                    where = "%s:%d" % (rel, line_no) if not path.lower().endswith(".pdf") else \
                        "%s p.%d" % (rel, page)
                    hits.append({"where": where, "score": score, "matched": matched, "text": para,
                                 "folder": rel.split(os.sep)[0]})
    hits.sort(key=lambda h: (-h["score"], h["where"]))
    return hits[:top]


def run(draft, matter, read=False, top=15):
    with open(draft, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    terms, refs = subject_terms(text, skip=party_words(matter))
    hits = find_passages(matter, terms, refs, top)
    lines = ["GATE — %s" % os.path.relpath(draft, matter) if draft.startswith(matter) else "GATE — %s" % draft,
             "Subject terms: %s" % (", ".join(terms + refs) or "(none found)"),
             "Record searched: %s" % ", ".join(d + "/" for d in RECORD_DIRS if os.path.isdir(os.path.join(matter, d))),
             ""]
    if not hits:
        lines.append("No passage in served/, received/ or notes/ on these subjects. The record on this disk "
                     "holds nothing on them; the person may hold more.")
    for h in hits:
        body = h["text"] if len(h["text"]) <= 600 else h["text"][:600].rsplit(" ", 1)[0] + " …"
        lines.append("%s  [%s]" % (h["where"], ", ".join(h["matched"])))
        lines.append("    " + body)
        lines.append("")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    if read:
        lines.append("CLEARED — %d passage(s) acknowledged as read. Logged to gate.log (draft sha256 %s)." % (len(hits), digest))
        with open(os.path.join(matter, "gate.log"), "a", encoding="utf-8") as fh:
            fh.write("%s\tCLEARED\t%s\tsha256:%s\t%d passages\n" % (
                _dt.datetime.now().isoformat(timespec="seconds"), os.path.relpath(draft, matter), digest, len(hits)))
        return "\n".join(lines), 0
    lines.append("BLOCKED — read the %d passage(s) above, then run again with --read to clear this draft." % len(hits))
    return "\n".join(lines), 1
