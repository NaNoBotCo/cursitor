"""Find passages in a PDF and cite them by page and line.

    cursitor ask <pdf> "security deposit itemized statement" [--top 8] [--json]

Reads each page's text (OCR for pages without a text layer), scores every short window of lines
by the question's words and phrases, and prints the best windows as page:line ranges. On
pleading paper the line numbers are the printed margin numbers 1-28; elsewhere they count the
page's non-empty lines from the top. The code makes no network calls.
"""
import json
import re

from . import pdftext

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were
with which who what when where why how do does did not no any all our your their his her them
they we you i me my""".split())
MARGIN = re.compile(r"^\s{0,6}([1-9]|1\d|2[0-8])(\s{2,}|\s*$)")


def terms(question):
    q = question.lower()
    phrases = re.findall(r'"([^"]+)"', q)
    words = [w for w in re.findall(r"[a-z0-9§.$'-]+", q.replace('"', " ")) if w not in STOP and len(w) > 1]
    words = [w.strip(".'") for w in words if w.strip(".'")]
    if not phrases and len(words) >= 2:
        phrases = [" ".join(words)]
    return words, phrases


def numbered_lines(text):
    """[(line_no, text)] using printed margin numbers when the page has them."""
    raw = [ln for ln in text.split("\n")]
    margin = [MARGIN.match(ln) for ln in raw]
    if sum(1 for m in margin if m) >= 10:
        out, cur = [], None
        for ln, m in zip(raw, margin):
            if m:
                cur = int(m.group(1))
                body = ln[m.end():].strip()
                out.append((cur, body))
            elif ln.strip() and cur is not None:
                out.append((cur, ln.strip()))
        return out, True
    out, k = [], 0
    for ln in raw:
        if ln.strip():
            k += 1
            out.append((k, re.sub(r"\s{2,}", " ", ln.strip())))
    return out, False


def _stem(w):
    for suf in ("ies", "es", "s", "ing", "ed"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def score(text, words, phrases):
    t = text.lower()
    s = 0.0
    hit = set()
    for w in words:
        st = _stem(w)
        if re.search(r"\b" + re.escape(st), t):
            hit.add(w)
            s += 1.0 + min(2, t.count(st)) * 0.25
    for p in phrases:
        if p in t:
            s += 3.0 + len(p.split())
    if words:
        s *= (0.5 + len(hit) / float(len(words)))
    return s, hit


def search(pdf, question, top=8, window=3, ocr=True):
    words, phrases = terms(question)
    if not words:
        raise SystemExit("ask needs some words to look for")
    found = []
    for page, text, source in pdftext.pages(pdf, ocr=ocr):
        lines, printed = numbered_lines(text)
        for i in range(len(lines)):
            chunk = lines[i:i + window]
            body = " ".join(t for _, t in chunk)
            s, hit = score(body, words, phrases)
            if s <= 0 or not hit:
                continue
            found.append({"page": page, "from": chunk[0][0], "to": chunk[-1][0], "score": round(s, 2),
                          "text": body, "matched": sorted(hit), "source": source, "printed_lines": printed})
    found.sort(key=lambda r: (-r["score"], r["page"], r["from"]))
    picked = []
    for r in found:
        if any(p["page"] == r["page"] and not (r["to"] < p["from"] or r["from"] > p["to"]) for p in picked):
            continue
        picked.append(r)
        if len(picked) >= top:
            break
    return picked


def cite(r):
    lines = ("%d" % r["from"]) if r["from"] == r["to"] else ("%d-%d" % (r["from"], r["to"]))
    return "%d:%s" % (r["page"], lines)


def render(pdf, results, question, as_json=False):
    if as_json:
        return json.dumps({"pdf": pdf, "question": question, "results": results}, indent=2, ensure_ascii=False)
    if not results:
        return "No passage in %s matches: %s" % (pdf, question)
    out = ["%s — %d passage(s) for: %s" % (pdf, len(results), question)]
    for r in results:
        tag = " [OCR]" if r["source"] == "ocr" else ""
        out.append("%s%s  %s" % (cite(r), tag, r["text"]))
    return "\n".join(out)
