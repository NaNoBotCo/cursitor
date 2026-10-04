"""Repair text pasted from a PDF, a Word file or a court website.

    python3 -m cursitor paste-clean in.txt [-o out.txt] [--ascii-quotes]
    pbpaste | python3 -m cursitor paste-clean

What it does, in order:
  1. drops pleading line numbers (1-28 down the left margin), read as a running sequence so a
     sentence that starts with a number keeps it;
  2. drops page numbers ("- 3 -", "Page 3 of 9") and running headers and footers (a short line
     that repeats next to page breaks, such as "COMPLAINT FOR DAMAGES - 3");
  3. keeps the caption and the block above it line for line;
  4. rejoins hard-wrapped lines into paragraphs, one paragraph per line, and mends words split
     by a hyphen at a line break;
  5. keeps numbered paragraphs (1., 2., ¶ 3, (a)), headings in capitals and indented block
     quotes as their own paragraphs;
  6. straightens curly quotes only with --ascii-quotes.
"""
import re
import sys

LINE_NO = re.compile(r"^(\s*)([1-9]|1[0-9]|2[0-8])(?:(\s{1,})(.*))?$")
PAGE_NO = re.compile(r"^\s*(?:-\s*\d{1,3}\s*-|\d{1,3}|Page\s+\d+(?:\s+of\s+\d+)?|\[\d{1,3}\])\s*$", re.I)
CAPTION = re.compile(r"\S\s{2,}\)|^\s*\)\s|\s\)\s*$|^\s*\)$|Case No\.|CASE NO\.")
PAREN_COL = re.compile(r"\S\s{2,}\)|^\s*\)|\s\)\s*$")
NUMBERED = re.compile(r"^\s*(\d{1,3}\.|¶\s*\d+\.?|\([a-z0-9]{1,4}\))\s+\S")
KEEP_HYPHEN = ("self", "non", "well", "pre", "post", "co", "ex", "anti", "multi", "semi", "quasi",
               "cross", "counter", "third", "first", "second", "long", "short", "full", "part", "so")
SENTENCE_END = re.compile(r"[.:;?!\"”’)]\s*$")


def _caps_heading(s):
    t = s.strip()
    letters = [c for c in t if c.isalpha()]
    return (0 < len(t) < 80 and len(letters) >= 3 and t.upper() == t
            and not CAPTION.search(s) and not NUMBERED.match(t))


def strip_line_numbers(lines):
    """Remove margin line numbers read as a sequence 1..28 that restarts each page.
    Returns (lines, page_break_indexes)."""
    hits = sum(1 for ln in lines if LINE_NO.match(ln))
    if hits < 8:
        return lines, []
    out, breaks, expected = [], [], 1
    for ln in lines:
        m = LINE_NO.match(ln)
        if m:
            n = int(m.group(2))
            if n == expected or (n == 1 and expected > 20):
                if n == 1 and out:
                    breaks.append(len(out))
                expected = 1 if n == 28 else n + 1
                rest = m.group(4) or ""
                pad = m.group(3) or ""
                # keep the indentation that followed the number, less the usual gap
                lead = " " * max(0, len(pad) - 2) if rest else ""
                out.append(lead + rest)
                continue
        out.append(ln)
    return out, breaks


def _norm(s):
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", s.strip().lower()))


def strip_headers(lines, breaks):
    """Drop page numbers, running headers and footers, and the blank lines around page breaks.

    A running header repeats among the first lines of two or more pages; a running footer
    repeats among the last lines of two or more pages. A name that appears once at the top of
    page 1 and once in the signature block is neither, and stays."""
    for i, ln in enumerate(lines):
        if "\f" in ln:
            breaks.append(i)
    lines = [ln.replace("\f", "") for ln in lines]
    breaks = sorted(set(b for b in breaks if 0 < b < len(lines)))
    bounds = [0] + breaks + [len(lines)]
    heads, tails = {}, {}
    for a, b in zip(bounds, bounds[1:]):
        seg = [i for i in range(a, b) if lines[i].strip()]
        for i in seg[:3]:
            heads.setdefault(_norm(lines[i]), set()).add(a)
        for i in seg[-5:]:
            tails.setdefault(_norm(lines[i]), set()).add(a)
    drop = set()
    for i, ln in enumerate(lines):
        st = ln.strip()
        if not st:
            continue
        k = _norm(ln)
        if PAGE_NO.match(st):
            drop.add(i)
        elif re.match(r"^[A-Z][A-Z0-9 ,.'&()/-]{3,80}\s[-–—]\s*\d{1,3}\s*$", st):
            drop.add(i)                                 # "COMPLAINT FOR DAMAGES - 3"
        elif not PAREN_COL.search(ln) and len(k) < 100 and (
                len(heads.get(k, ())) >= 2 or len(tails.get(k, ())) >= 2):
            drop.add(i)
    # blank lines that sit in a page-break gap go too, so a paragraph that runs over a page
    # comes back whole
    for b in breaks:
        i = b - 1
        while i >= 0 and (not lines[i].strip() or i in drop):
            drop.add(i)
            i -= 1
        i = b
        while i < len(lines) and (not lines[i].strip() or i in drop):
            drop.add(i)
            i += 1
    return [ln for i, ln in enumerate(lines) if i not in drop]


def split_head(lines):
    """The caption and everything above it stay line for line."""
    last = -1
    for i, ln in enumerate(lines[:90]):
        if CAPTION.search(ln):
            last = i
    if last < 0:
        return [], lines
    j = last + 1
    # title lines in capitals right under the caption belong to it
    while j < len(lines) and j - last <= 4 and (not lines[j].strip() or _caps_heading(lines[j])) \
            and "CAUSE OF ACTION" not in lines[j].upper() and "ALLEGATION" not in lines[j].upper():
        j += 1
    head = [ln.rstrip() for ln in lines[:j]]
    # collapse runs of blank lines inside the head
    tidy = []
    for ln in head:
        if not ln.strip() and tidy and not tidy[-1].strip():
            continue
        tidy.append(ln)
    while tidy and not tidy[-1].strip():
        tidy.pop()
    while tidy and not tidy[0].strip():
        tidy.pop(0)
    return tidy, lines[j:]


def _join(buf, nxt):
    if not buf:
        return nxt
    m = re.search(r"([A-Za-z]+)-$", buf)
    if m and re.match(r"^[a-z]", nxt):
        if m.group(1).lower() in KEEP_HYPHEN:
            return buf + nxt
        return buf[:-1] + nxt
    if buf.endswith((" —", " –")):
        return buf + " " + nxt
    if buf.endswith(("—", "–")) or buf.endswith("/"):
        return buf + nxt
    return buf + " " + nxt


def rejoin(body):
    texts = [ln for ln in body if ln.strip()]
    if not texts:
        return []
    lengths = sorted(len(ln.rstrip()) for ln in texts)
    typical = lengths[int(len(lengths) * 0.85)] if lengths else 70
    indents = sorted(len(ln) - len(ln.lstrip()) for ln in texts)
    base = indents[len(indents) // 3] if indents else 0

    # double-spaced paste: nearly every text line is followed by one blank line
    singles = 0
    for i in range(1, len(body) - 1):
        if not body[i].strip() and body[i - 1].strip() and body[i + 1].strip():
            singles += 1
    double_spaced = singles >= 0.5 * len(texts)

    paras, buf, kind = [], "", "para"
    prev_raw, blank_run = "", 0

    def flush():
        if buf.strip():
            paras.append((kind, buf.strip()))

    for raw in body:
        if not raw.strip():
            blank_run += 1
            if not double_spaced or blank_run >= 2:
                flush()
                buf, kind = "", "para"
            continue
        blank_run = 0
        line = raw.rstrip()
        st = line.strip()
        ind = len(line) - len(line.lstrip())
        if kind == "center" and buf and not buf.rstrip().endswith(")"):
            buf = _join(buf, st)                     # a centred (parenthetical) runs to its ")"
            prev_raw = line
            continue
        if re.match(r"^Dated:", st):
            # the signature block stays line for line
            flush()
            rest = [x.strip() for x in body[body.index(raw):] if x.strip()]
            paras.append(("verbatim", "\n".join(re.sub(r"\s{3,}", "    ", x) for x in rest)))
            return paras
        is_center = ind >= base + 3 and st.startswith("(") and not NUMBERED.match(st)
        if is_center:
            flush()
            buf, kind = st, "center"
            prev_raw = line
            continue
        is_quote = ind >= base + 8 and not NUMBERED.match(st) and not _caps_heading(st)
        starts_new = (NUMBERED.match(st) or _caps_heading(st) or kind == "center"
                      or (is_quote and kind != "quote") or (not is_quote and kind == "quote"))
        prev_short = prev_raw and SENTENCE_END.search(prev_raw) and len(prev_raw.rstrip()) < 0.75 * typical
        indented_start = ind >= base + 3 and not is_quote and prev_raw and SENTENCE_END.search(prev_raw)
        if starts_new or (buf and (prev_short or indented_start)) or (buf and _caps_heading(prev_raw)):
            flush()
            buf = st
            kind = "quote" if is_quote else ("heading" if _caps_heading(st) else "para")
        else:
            buf = _join(buf, st)
        prev_raw = line
    flush()
    return paras


def straighten(s):
    return (s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'"))


def clean(text, ascii_quotes=False):
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ").replace("­", "")
    text = text.replace("\t", "    ")
    lines = text.split("\n")
    lines, breaks = strip_line_numbers(lines)
    lines = strip_headers(lines, breaks)
    head, body = split_head(lines)
    paras = rejoin(body)
    out = []
    if head:
        out.extend(head)
        out.append("")
    for kind, p in paras:
        if kind == "para":
            p = re.sub(r"^(\d{1,3}\.|¶\s*\d+\.?)\s{2,}", r"\1 ", p)
        out.append(("    " + p) if kind == "quote" else p)
        out.append("")
    result = "\n".join(out).rstrip("\n") + "\n"
    if ascii_quotes:
        result = straighten(result)
    return result


def main_cli(src, out=None, ascii_quotes=False):
    data = sys.stdin.read() if src in (None, "-") else open(src, encoding="utf-8", errors="replace").read()
    res = clean(data, ascii_quotes)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(res)
    else:
        sys.stdout.write(res)
    return res
