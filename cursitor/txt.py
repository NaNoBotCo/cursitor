"""Markdown to plain text a person reads in any text viewer.

    cursitor txt in.md [out.txt]

  # Title         -> upper case between rules of '='
  ## Heading      -> upper case over a rule of '-'
  ### Heading     -> upper case
  **short bold**  -> UPPER CASE (up to 60 characters); longer bold loses its markers
  `code`, _x_     -> markers removed
  | tables |      -> one record per row, "label: value" lines
  > quote         -> indented
  - list          -> "-" bullets, indented by depth
  ---             -> a rule
  ```fenced```    -> kept as written, indented

A paragraph or list item comes out as one line; the viewer wraps it.
"""
import re

RULE_W = 72
BOLD_CAPS_MAX = 60
H_RE = re.compile(r"\s*(#{1,6})\s+(.*)")
LI_RE = re.compile(r"(\s*)([-*+]|\d+[.)])\s+(.*)")
RULE_RE = re.compile(r"\s*([-*_]\s*){3,}\s*$")


def inline(s):
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
    s = s.replace("`", "")

    def bold(m):
        inner = m.group(1)
        return inner.upper() if len(inner) <= BOLD_CAPS_MAX else inner
    s = re.sub(r"\*\*(.+?)\*\*", bold, s)
    s = re.sub(r"__(.+?)__", bold, s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", s)
    s = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"\1", s)
    s = re.sub(r"~~(.+?)~~", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(re.fullmatch(r":?-{2,}:?", x or "-") for x in c)]
    if not cells:
        return []
    head, body = cells[0], cells[1:]
    if not body:
        return ["    " + inline(c) for c in head if c.strip()]
    out = []
    for row in body:
        first = inline(row[0]) if row else ""
        if first:
            out.append("  " + (first.upper() if len(first) <= BOLD_CAPS_MAX else first))
        for label, val in zip(head[1:], row[1:]):
            val = inline(val)
            if val:
                out.append("      %s%s" % ((inline(label) + ": ") if inline(label) else "", val))
        out.append("")
    return out


def _opens_block(ln):
    return (not ln.strip() or LI_RE.match(ln) or H_RE.match(ln) or RULE_RE.fullmatch(ln)
            or ln.lstrip().startswith(("|", ">", "```")))


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i = [], 0

    def gap():
        if out and out[-1] != "":
            out.append("")

    while i < len(lines):
        raw = lines[i]
        if raw.lstrip().startswith("```"):
            i += 1
            gap()
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                out.append("    " + lines[i].rstrip())
                i += 1
            i += 1
            out.append("")
            continue
        if not raw.strip():
            out.append("")
            i += 1
            continue
        if RULE_RE.fullmatch(raw):
            gap()
            out.extend(["-" * RULE_W, ""])
            i += 1
            continue
        m = H_RE.match(raw)
        if m:
            level, text = len(m.group(1)), inline(m.group(2))
            gap()
            if level == 1:
                out.extend(["=" * RULE_W, text.upper(), "=" * RULE_W])
            elif level == 2:
                out.extend([text.upper(), "-" * RULE_W])
            else:
                out.append("  " * (level - 3) + text.upper())
            out.append("")
            i += 1
            continue
        if raw.lstrip().startswith("|") and raw.count("|") >= 2:
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.extend(_table(rows))
            continue
        if raw.lstrip().startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            gap()
            out.extend(("    " + ln) if ln else "" for ln in convert("\n".join(block)).split("\n"))
            out.append("")
            continue
        m = LI_RE.match(raw)
        if m:
            depth = len(m.group(1).expandtabs(4)) // 2
            marker = m.group(2)
            bullet = marker if marker[0].isdigit() else "-"
            body = [m.group(3)]
            i += 1
            while i < len(lines) and not _opens_block(lines[i]):
                body.append(lines[i].strip())
                i += 1
            out.append("  " + "    " * depth + bullet + "  " + inline(" ".join(body)))
            continue
        body = [raw.strip()]
        i += 1
        while i < len(lines) and not _opens_block(lines[i]):
            body.append(lines[i].strip())
            i += 1
        out.append(inline(" ".join(body)))
    text = "\n".join(out)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip("\n") + "\n"
