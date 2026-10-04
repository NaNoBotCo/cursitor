"""Pleading paper and letters from plain text.

    python3 -m cursitor plead complaint.txt complaint.pdf --caption caption.json [--format ca|federal|letter]

Input: one paragraph per line (the shape `paste-clean` writes) or Markdown. The text marks:

    # TITLE / ## Heading      centred bold heading (an ALL-CAPS line under 80 characters also counts)
    1. Text                   numbered paragraph
    (a) Text                  sub-item, indented
    > Text  (or 4+ spaces)    block quote, indented both sides
    [[SIGNATURE]]             where the signature block goes (default: the end)
    [[PAGEBREAK]]             start a new page

Paragraphs and the signature block do not split across pages. A paragraph longer than a page
splits, since it cannot fit anywhere whole.
"""
import json
import os
import re

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as _canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "templates")
FORMATS = ("ca", "federal", "letter")


def load_template(name):
    path = name if name.endswith(".json") else os.path.join(TEMPLATE_DIR, name + ".json")
    if not os.path.exists(path):
        raise SystemExit("no template %r (have: %s)" % (name, ", ".join(FORMATS)))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def wrap(text, width, font, size, first_indent=0.0):
    """Greedy word wrap. The first line is `first_indent` narrower."""
    words, lines, cur = text.split(), [], ""
    limit = width - first_indent
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, font, size) <= limit or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
            limit = width
    if cur:
        lines.append(cur)
    return lines or [""]


# --------------------------------------------------------------------------- document model

HEADING_MD = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBERED = re.compile(r"^(\d{1,3})\.\s+(.*)$")
SUBITEM = re.compile(r"^\s*(\([a-z0-9]{1,4}\))\s+(.*)$")
PARA_SIGN = re.compile(r"^¶\s*\d+")
CLOSING = re.compile(r"^(Sincerely|Very truly yours|Yours truly|Respectfully submitted|Respectfully|Regards|Best regards),?$", re.I)


def is_caps_heading(s):
    t = s.strip()
    letters = [c for c in t if c.isalpha()]
    return (len(t) < 80 and len(letters) >= 3 and t.upper() == t
            and not NUMBERED.match(t) and not t.endswith((",", ";")))


def parse(text, markdown=False):
    """Text -> list of (kind, payload). kinds: heading, para, numbered, sub, quote, sig, pagebreak."""
    lines = text.replace("\r\n", "\n").split("\n")
    if markdown:
        joined, buf = [], []

        def flush():
            if buf:
                joined.append(" ".join(x.strip() for x in buf))
                del buf[:]
        for ln in lines:
            st = ln.strip()
            if not st:
                flush()
                joined.append("")
            elif (HEADING_MD.match(st) or NUMBERED.match(st) or SUBITEM.match(ln) or st.startswith(">")
                  or st.startswith("[[") or ln.startswith("    ")):
                flush()
                joined.append(ln)
            else:
                buf.append(ln)
        flush()
        lines = joined
    blocks = []
    for idx, ln in enumerate(lines):
        st = ln.strip()
        if not st:
            continue
        m = re.match(r"^Dated:\s*(.*?)(?:\s{2,}_+.*)?$", st)
        tail = [l.strip() for l in lines[idx + 1:] if l.strip()]
        if m and len(tail) <= 6:
            # a pasted signature block at the end: the engine draws its own
            blocks.append(("sig", {"date": m.group(1).strip(" _"), "lines": [t for t in tail if not set(t) <= set("_/ ")]}))
            break
        if CLOSING.match(st) and len(tail) <= 6:
            blocks.append(("sig", {"date": "", "lines": [t for t in tail if not set(t) <= set("_/ ")],
                                   "closing": st}))
            break
        if st == "[[SIGNATURE]]":
            blocks.append(("sig", {}))
        elif st == "[[PAGEBREAK]]":
            blocks.append(("pagebreak", ""))
        elif HEADING_MD.match(st):
            blocks.append(("heading", HEADING_MD.match(st).group(2).replace("**", "")))
        elif st.startswith(">"):
            blocks.append(("quote", st.lstrip("> ").strip()))
        elif ln.startswith("    ") and not NUMBERED.match(st):
            blocks.append(("quote", st))
        elif NUMBERED.match(st):
            blocks.append(("numbered", st))
        elif SUBITEM.match(ln):
            blocks.append(("sub", st))
        elif is_caps_heading(st):
            blocks.append(("heading", st))
        elif st.startswith("(") and st.endswith(")") and len(st) < 140 and blocks and blocks[-1][0] == "heading":
            blocks.append(("center", st))
        else:
            blocks.append(("para", st.replace("**", "")))
    return blocks


CAPTION_LINE = re.compile(r"\s\)\s|\s\)$|^\s*\)|Case No\.|CASE NO\.")


def strip_caption(text):
    """Drop a caption pasted at the head of a document (the caption comes from caption.json).
    Returns (body, lines_dropped)."""
    lines = text.split("\n")
    last = -1
    for i, ln in enumerate(lines[:80]):
        if CAPTION_LINE.search(ln):
            last = i
    if last < 0:
        return text, 0
    # also drop the document-title lines that sit right after the caption box
    j = last + 1
    while j < len(lines) and (not lines[j].strip() or (is_caps_heading(lines[j]) and j - last <= 3
                                                       and "CAUSE OF ACTION" not in lines[j].upper()
                                                       and "ALLEGATIONS" not in lines[j].upper())):
        j += 1
    return "\n".join(lines[j:]), j


# --------------------------------------------------------------------------- pleading paper

class PleadingPaper(object):
    def __init__(self, path, tpl, footer_title, title=None):
        self.t = tpl
        self.c = _canvas.Canvas(path, pagesize=tuple(tpl.get("page", LETTER)))
        self.c.setTitle(title or footer_title)
        self.c.setCreator("Cursitor")
        self.W, self.H = tpl.get("page", LETTER)
        self.font, self.bold, self.size = tpl["font"], tpl["bold"], float(tpl["size"])
        self.body_x, self.right_x = tpl["body_x"], tpl["right_x"]
        self.footer_title = footer_title
        self.pageno = 0
        self.line = 1
        self.pending = False
        self.new_page()

    @property
    def width(self):
        return self.right_x - self.body_x

    def y(self, line):
        return self.H - self.t["top"] - (line - 1) * self.t["lead"]

    def new_page(self):
        if self.pageno:
            self.c.showPage()
        self.pageno += 1
        self.line = 1
        t, c = self.t, self.c
        n = t["lines"]
        y_top = self.H - 18
        y_bot = 54
        c.setLineWidth(0.6)
        for x in t["rule_left"]:
            c.line(x, y_bot, x, y_top)
        if t.get("rule_right"):
            c.line(t["rule_right"], y_bot, t["rule_right"], y_top)
        c.setFont(self.font, self.size)
        for i in range(1, n + 1):
            c.drawRightString(t["num_x"], self.y(i), str(i))
        if t.get("footer_rule"):
            c.setLineWidth(0.5)
            c.line(self.body_x, 50, self.right_x, 50)
        fs = t.get("footer_size", 10)
        c.setFont(self.font, fs)
        c.drawCentredString(self.body_x + self.width / 2, 38, "- %d -" % self.pageno)
        c.drawCentredString(self.body_x + self.width / 2, 26, self.footer_title.upper())
        c.setFont(self.font, self.size)

    def open_page(self):
        if self.pending:
            self.pending = False
            self.new_page()

    def advance(self, k=1):
        self.line += k
        if self.line > self.t["lines"]:
            self.pending = True
            self.line = 1

    def need(self, k):
        """Keep k lines together: break first when they do not fit on this page."""
        if self.pending:
            return
        if k <= self.t["lines"] and self.line + k - 1 > self.t["lines"]:
            self.pending = True
            self.line = 1

    def put(self, text, bold=False, x=None, center=False, italic=False):
        self.open_page()
        f = self.bold if bold else (self.t.get("italic", self.font) if italic else self.font)
        self.c.setFont(f, self.size)
        if center:
            self.c.drawCentredString(self.body_x + self.width / 2, self.y(self.line), text)
        else:
            self.c.drawString(self.body_x if x is None else x, self.y(self.line), text)
        self.advance()

    def blank(self, k=1):
        if self.pending:
            return
        self.advance(k)

    def paragraph(self, text, indent=36.0, left=0.0, right=0.0, bold=False, keep=True):
        f = self.bold if bold else self.font
        lines = wrap(text, self.width - left - right, f, self.size, first_indent=indent)
        if keep:
            self.need(len(lines))
        for i, ln in enumerate(lines):
            self.put(ln, bold=bold, x=self.body_x + left + (indent if i == 0 else 0))

    def heading(self, text, keep_with=2):
        lines = wrap(text, self.width, self.bold, self.size)
        self.need(len(lines) + keep_with)
        for ln in lines:
            self.put(ln, bold=True, center=True)

    # ---- first page ----
    def first_page(self, cap):
        for ln in cap.get("attorney_block", []):
            self.put(ln)
        target = int(self.t.get("court_title_line", 8))
        if self.line < target and not self.pending:
            self.line = target
        for ln in cap.get("court") or self.t["court_default"]:
            self.put(ln, bold=True, center=True)
        self.blank()
        self.caption_box(cap)

    def caption_box(self, cap):
        t = self.t
        px, rx = t["caption_paren_x"], t["caption_right_x"]
        left = []
        lw = px - self.body_x - 6
        for ln in cap.get("parties_left", []):
            pad = len(ln) - len(ln.lstrip())
            if stringWidth(ln, self.font, self.size) <= lw:
                left.append(ln)
            else:
                left.extend(" " * pad + x for x in wrap(ln.strip(), lw - stringWidth(" " * pad, self.font, self.size),
                                                         self.font, self.size))
        right = []
        for txt, bold in ([(cap.get("case_number", ""), True), ("", False)]
                          + [(x, False) for x in cap.get("right_before_title", [])]
                          + [(cap.get("document_title", ""), True)]
                          + [(x, False) for x in cap.get("right_extra", [])]):
            if not txt:
                right.append(("", False, 0))
                continue
            f = self.bold if bold else self.font
            hang = stringWidth(re.match(r"^(\d+\.\s+|)", txt).group(1), f, self.size)
            for k, ln in enumerate(wrap(txt, self.right_x - rx - hang, f, self.size)):
                right.append((ln, bold, hang if k else 0))
        rows = max(len(left), len(right)) + 1
        self.need(rows)
        self.open_page()
        start = self.line
        c = self.c
        for i in range(rows):
            y = self.y(start + i)
            c.setFont(self.font, self.size)
            c.drawString(px, y, ")")
            if i < len(left):
                c.drawString(self.body_x, y, left[i])
        for i, (ln, bold, hang) in enumerate(right):
            c.setFont(self.bold if bold else self.font, self.size)
            c.drawString(rx + hang, self.y(start + i), ln)
        c.setLineWidth(0.6)
        yb = self.y(start + rows - 1) - 4
        c.line(self.body_x, yb, px + 4, yb)
        c.setFont(self.font, self.size)
        self.line = start + rows
        if self.line > t["lines"]:
            self.pending = True
            self.line = 1
        self.blank()

    def signature(self, signer, signed=None, dated=None, sig_image=None, place=None):
        name = signer.get("name", "")
        role = signer.get("role", "")
        extra = signer.get("lines", [])
        rows = 5 + len(extra) + (1 if role else 0)
        self.need(rows)
        self.open_page()
        sx = self.t["caption_paren_x"]
        date_line = "Dated: %s" % (dated or "____________________")
        if place:
            date_line += ", at %s" % place
        self.put(date_line)
        self.blank()
        if sig_image and os.path.exists(sig_image):
            yimg = self.y(self.line)
            self.c.drawImage(sig_image, sx, yimg - 4, width=132, height=40, mask="auto")
            self.advance()
            self.put("______________________________", x=sx)
        elif signed:
            self.put("/s/ %s" % signed, x=sx)
            self.c.setLineWidth(0.5)
            self.c.line(sx, self.y(self.line - 1) - 3, self.right_x, self.y(self.line - 1) - 3)
        else:
            self.blank()
            self.put("______________________________", x=sx)
        self.put(name, x=sx)
        if role:
            self.put(role, x=sx)
        for ln in extra:
            self.put(ln, x=sx)

    def save(self):
        self.c.save()


def render_pleading(blocks, out, cap, tpl, signed=None, dated=None, sig_image=None, place=None):
    footer = cap.get("footer_title") or cap.get("document_title") or "DOCUMENT"
    doc = PleadingPaper(out, tpl, footer, title=cap.get("pdf_title") or cap.get("document_title"))
    doc.first_page(cap)
    signed_done = False
    prev = None
    for i, (kind, txt) in enumerate(blocks):
        nxt = blocks[i + 1][0] if i + 1 < len(blocks) else None
        if nxt == "sig" and kind in ("para", "numbered", "sub", "quote"):
            # the last paragraph stays on the page with the signature: no orphan signature page
            left = 36.0 if kind in ("sub", "quote") else 0.0
            n = len(wrap(txt, doc.width - left, doc.font, doc.size, first_indent=36.0 if kind in ("para", "numbered") else 0))
            doc.need(n + 8)
        if kind == "heading":
            if prev not in (None, "heading"):
                doc.blank()
            doc.heading(txt)
        elif kind == "para":
            doc.paragraph(txt)
        elif kind == "numbered":
            doc.paragraph(txt, indent=36.0)
        elif kind == "sub":
            doc.paragraph(txt, indent=0.0, left=36.0)
        elif kind == "quote":
            doc.paragraph(txt, indent=0.0, left=36.0, right=36.0)
        elif kind == "pagebreak":
            doc.pending = True
            doc.line = 1
        elif kind == "center":
            for ln in wrap(txt, doc.width, doc.font, doc.size):
                doc.put(ln, center=True)
        elif kind == "sig":
            doc.blank()
            doc.signature(signer_from(cap, txt), signed, dated or txt.get("date") or None, sig_image, place)
            signed_done = True
        prev = kind
    if not signed_done and signer_from(cap, {}):
        doc.blank()
        doc.signature(signer_from(cap, {}), signed, dated, sig_image, place)
    doc.save()
    return doc.pageno


# --------------------------------------------------------------------------- letters

def render_letter(blocks, out, cap, tpl, signed=None, dated=None, sig_image=None, place=None):
    W, H = tpl.get("page", LETTER)
    m, lead, gap = tpl["margin"], tpl["lead"], tpl["paragraph_gap"]
    font, bold, size = tpl["font"], tpl["bold"], float(tpl["size"])
    c = _canvas.Canvas(out, pagesize=(W, H))
    c.setTitle(cap.get("document_title") or "Letter")
    c.setCreator("Cursitor")
    width = W - 2 * m
    state = {"y": H - m, "page": 1}

    def newpage():
        c.showPage()
        state["page"] += 1
        state["y"] = H - m
        c.setFont(font, tpl.get("footer_size", 9))
        c.drawCentredString(W / 2, 36, str(state["page"]))

    def need(k):
        if state["y"] - k * lead < m:
            newpage()

    def line(text, f=None, x=None, center=False):
        need(1)
        c.setFont(f or font, size)
        if center:
            c.drawCentredString(W / 2, state["y"], text)
        else:
            c.drawString(m if x is None else x, state["y"], text)
        state["y"] -= lead

    for ln in cap.get("letterhead") or cap.get("attorney_block", []):
        if ln.strip():
            line(ln, center=True)
    state["y"] -= lead
    if dated:
        line(dated)
        state["y"] -= gap
    for ln in cap.get("recipient", []):
        line(ln)
    if cap.get("recipient"):
        state["y"] -= gap
    if cap.get("re"):
        for i, ln in enumerate(wrap("Re: " + cap["re"], width - 36, bold, size)):
            line(ln, f=bold, x=m + (0 if i == 0 else 22))
        state["y"] -= gap
    signed_done = False

    def sig(payload=None):
        payload = payload or {}
        signer = signer_from(cap, payload)
        need(6)
        state["y"] -= gap
        line(payload.get("closing") or cap.get("closing", "Sincerely,"))
        if sig_image and os.path.exists(sig_image):
            c.drawImage(sig_image, m, state["y"] - 30, width=132, height=40, mask="auto")
            state["y"] -= 3 * lead
        elif signed:
            state["y"] -= lead
            line("/s/ %s" % signed)
        else:
            state["y"] -= 2 * lead
        for ln in [signer.get("name", "")] + ([signer["role"]] if signer.get("role") else []) + signer.get("lines", []):
            line(ln)

    for bi, (kind, txt) in enumerate(blocks):
        nxt = blocks[bi + 1] if bi + 1 < len(blocks) else (None, None)
        if nxt[0] == "sig" and kind != "sig":
            need(len(wrap(txt, width, font, size)) + 7)
        if kind == "sig":
            sig(txt)
            signed_done = True
            continue
        if kind == "pagebreak":
            newpage()
            continue
        f = bold if kind == "heading" else font
        left = 36.0 if kind in ("quote", "sub") else 0.0
        lines = wrap(txt, width - left - (36.0 if kind == "quote" else 0.0), f, size)
        if len(lines) <= 6:
            need(len(lines))
        for ln in lines:
            line(ln, f=f, x=m + left)
        short = kind == "para" and len(txt) < 60 and nxt[0] == "para" and len(nxt[1]) < 60
        if not short:
            state["y"] -= gap
    if not signed_done:
        sig()
    c.save()
    return state["page"]


# --------------------------------------------------------------------------- entry point

def signer_from(cap, payload):
    """The signer: caption.json or matter.json first, else the name lines of a pasted block."""
    if cap.get("signer") and cap["signer"].get("name"):
        return cap["signer"]
    lines = (payload or {}).get("lines") or []
    if lines:
        return {"name": lines[0], "role": lines[1] if len(lines) > 1 else "", "lines": lines[2:]}
    return {}


COURT_LINE = re.compile(r"\b(COURT|COUNTY OF|DISTRICT OF|DIVISION)\b")


def parse_pasted_caption(text):
    """Read a caption pasted at the top of a document into caption fields.
    Returns {} when the text carries no caption box (lines with a ')' column)."""
    lines = text.split("\n")[:80]
    rows = [i for i, ln in enumerate(lines) if re.search(r"\S?\s*\)(\s|$)", ln) and ")" in ln]
    box = [i for i in rows if re.search(r"^\s*\S.*?\s{2,}\)|^\s*\)|^_+\)", lines[i])]
    if len(box) < 3:
        return {}
    first, last = box[0], box[-1]
    court_idx = [i for i in range(first) if COURT_LINE.search(lines[i]) and lines[i].upper() == lines[i]]
    head_end = court_idx[0] if court_idx else first
    cap = {"attorney_block": [ln.strip() for ln in lines[:head_end]]}
    while cap["attorney_block"] and not cap["attorney_block"][-1]:
        cap["attorney_block"].pop()
    if court_idx:
        cap["court"] = [lines[i].strip() for i in range(court_idx[0], first) if lines[i].strip()]
    left, right = [], []
    for i in range(first, last + 1):
        ln = lines[i]
        pos = ln.find(")")
        if pos < 0:
            continue
        l_part = ln[:pos].rstrip()
        r_raw = ln[pos + 1:]
        r_part = r_raw.strip()
        if set(l_part.strip()) <= set("_"):
            l_part = ""
        left.append(l_part)
        if r_part:
            right.append((len(r_raw) - len(r_raw.lstrip()), r_part))
    while left and not left[-1].strip():
        left.pop()
    cap["parties_left"] = left
    merged = []
    base_ind = min([ind for ind, _r in right] or [0])
    for ind, r in right:
        if merged and (ind >= base_ind + 3 or (not re.match(r"^(\d+\.|Case No|CASE NO)", r) and r[:1].islower())):
            merged[-1] += " " + r
        else:
            merged.append(r)
    for r in merged:
        if re.match(r"^(Case No|CASE NO)", r):
            cap["case_number"] = r
        elif "document_title" not in cap and r.upper() == r:
            cap["document_title"] = r
            cap["footer_title"] = r
        else:
            extra = cap.setdefault("right_extra", [])
            if r.upper() == r and extra:
                extra.append("")
            extra.append(r)
    return cap


def load_caption(path=None, matter_dir=None):
    cap = {}
    if matter_dir and os.path.exists(os.path.join(matter_dir, "matter.json")):
        with open(os.path.join(matter_dir, "matter.json"), encoding="utf-8") as fh:
            cap.update(json.load(fh).get("caption", {}))
    if path:
        with open(path, encoding="utf-8") as fh:
            cap.update(json.load(fh))
    return cap


def plead(src, out, caption=None, fmt="ca", signed=None, dated=None, sig_image=None, place=None,
          keep_caption=False, title=None, matter_dir=None):
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    cap = load_caption(caption, matter_dir)
    if title:
        cap["document_title"] = title
        cap.setdefault("footer_title", title)
    dropped = 0
    tpl = load_template(fmt)
    if tpl["kind"] == "pleading" and not keep_caption:
        pasted = parse_pasted_caption(text)
        if pasted:
            base = dict(pasted)
            base.update(cap)
            cap = base
        if cap.get("parties_left"):
            text, dropped = strip_caption(text)
    blocks = parse(text, markdown=src.lower().endswith(".md"))
    if tpl["kind"] == "letter":
        pages = render_letter(blocks, out, cap, tpl, signed, dated, sig_image, place)
    else:
        pages = render_pleading(blocks, out, cap, tpl, signed, dated, sig_image, place)
    return pages, dropped
