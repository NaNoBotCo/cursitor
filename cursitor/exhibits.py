"""Drop-a-folder exhibit package.

    cursitor exhibits <folder> <out-dir> --prefix DOE [--start 1] [--slip pleading|plain]
                      [--first-exhibit 1] [--letters] [--stamp-slips]

1. Order: order.txt in the folder (one file name per line) when present, else the number at the
   front of each file name, then the name.
2. OCR: any page with no text layer goes through ocrmypdf (or tesseract).
3. Slip sheet before each exhibit: "EXHIBIT 1" centred, with its title, on pleading paper or plain.
4. Bates: every page of every exhibit gets PREFIX000001, PREFIX000002, ... at the lower right.
   Slip sheets carry no number unless --stamp-slips.
5. Writes one stamped PDF per exhibit, index.txt (exhibit, Bates range, pages, title read from the
   first page's printed text) and the combined package PDF.
"""
import datetime as _dt
import io
import os
import re
import shutil
import tempfile

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from . import ocr as _ocr
from . import pdftext
from . import pleading as _pl

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


def ordered(folder):
    files = [f for f in os.listdir(folder)
             if f.lower().endswith((".pdf",) + IMAGE_EXT) and not f.startswith(".")
             and not f.lower().endswith(".ocr.pdf")]
    order_file = os.path.join(folder, "order.txt")
    if os.path.exists(order_file):
        with open(order_file, encoding="utf-8") as fh:
            wanted = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        missing = [w for w in wanted if w not in files]
        if missing:
            raise SystemExit("order.txt names files not in the folder: %s" % ", ".join(missing))
        rest = sorted(f for f in files if f not in wanted)
        return wanted + rest

    def key(f):
        m = re.match(r"^\s*(\d+)", f)
        return (0, int(m.group(1)), f.lower()) if m else (1, 0, f.lower())
    return sorted(files, key=key)


def image_to_pdf(img, out):
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(img)
    w, h = ir.getSize()
    W, H = LETTER
    scale = min((W - 72) / w, (H - 72) / h)
    c = canvas.Canvas(out, pagesize=LETTER)
    c.drawImage(ir, (W - w * scale) / 2, (H - h * scale) / 2, width=w * scale, height=h * scale)
    c.save()


SKIP_TITLE = re.compile(r"^(page \d+|\d+|-\s*\d+\s*-|[A-Z]{2,6}\d{4,}|exhibit \w+|date:.*|from:.*|to:.*)$", re.I)


def title_from_text(text):
    """The document's title as printed: the first capitals line near the top, else the first line."""
    lines = [re.sub(r"\s{2,}", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and len(ln) > 3 and not SKIP_TITLE.match(ln)]
    top = lines[:8]
    for ln in top:
        letters = [c for c in ln if c.isalpha()]
        if len(letters) >= 4 and ln.upper() == ln:
            caps = [ln]
            # a two-line title ("EXAMPLE AIR TESTING CO." / "MOLD INSPECTION REPORT")
            i = top.index(ln)
            if i + 1 < len(top) and top[i + 1].upper() == top[i + 1] and len(top[i + 1]) < 60:
                caps.append(top[i + 1])
            return " — ".join(caps)[:110]
    return (top[0] if top else "(no printed title found)")[:110]


def slip_sheet(path, label, title, style="pleading"):
    if style == "pleading":
        tpl = _pl.load_template("ca")
        doc = _pl.PleadingPaper(path, tpl, label, title=label)
        doc.line = 11
        doc.put(label, bold=True, center=True)
        doc.blank()
        for ln in _pl.wrap(title, doc.width - 72, doc.font, doc.size):
            doc.put(ln, center=True)
        doc.save()
    else:
        W, H = LETTER
        c = canvas.Canvas(path, pagesize=LETTER)
        c.setTitle(label)
        c.setFont("Times-Bold", 28)
        c.drawCentredString(W / 2, H / 2 + 20, label)
        c.setFont("Times-Roman", 13)
        y = H / 2 - 16
        for ln in _pl.wrap(title, W - 200, "Times-Roman", 13):
            c.drawCentredString(W / 2, y, ln)
            y -= 18
        c.save()


def stamp(page, text):
    w = float(page.mediabox.width) or LETTER[0]
    h = float(page.mediabox.height) or LETTER[1]
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFont("Helvetica-Bold", 9)
    tw = c.stringWidth(text, "Helvetica-Bold", 9)
    c.setFillColorRGB(1, 1, 1)
    c.rect(w - 30 - tw - 3, 14, tw + 6, 12, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(w - 30, 17, text)
    c.save()
    buf.seek(0)
    page.merge_page(PdfReader(buf).pages[0])
    return page


def label_for(n, letters):
    if not letters:
        return "EXHIBIT %d" % n
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return "EXHIBIT " + s


def build(folder, out_dir, prefix, start=1, slip="pleading", first_exhibit=1, letters=False,
          stamp_slips=False, package_name="exhibits-package.pdf", log=print):
    os.makedirs(out_dir, exist_ok=True)
    files = ordered(folder)
    if not files:
        raise SystemExit("no PDFs or images in %s" % folder)
    tmp = tempfile.mkdtemp(prefix="cursitor-ex-")
    n = start
    rows = []
    package = PdfWriter()
    try:
        for k, f in enumerate(files):
            num = first_exhibit + k
            label = label_for(num, letters)
            src = os.path.join(folder, f)
            if f.lower().endswith(IMAGE_EXT):
                conv = os.path.join(tmp, "img%d.pdf" % k)
                image_to_pdf(src, conv)
                src = conv
            rep = _ocr.ocr(src, os.path.join(tmp, "ocr%d.pdf" % k))
            work = rep["output"] if os.path.exists(rep["output"]) else src
            if rep.get("error"):
                log("  %s: %s" % (f, rep["error"]))
            pages = pdftext.pages(work, ocr=False)
            first_text = pages[0][1] if pages else ""
            title = title_from_text(first_text)
            slip_path = os.path.join(tmp, "slip%d.pdf" % k)
            slip_sheet(slip_path, label, title, slip)
            slip_page = PdfReader(slip_path).pages[0]
            reader = PdfReader(work)
            if stamp_slips:
                stamp(slip_page, "%s%06d" % (prefix, n))
                n += 1
            package.add_page(slip_page)
            single = PdfWriter()
            first = n
            for pg in reader.pages:
                stamp(pg, "%s%06d" % (prefix, n))
                single.add_page(pg)
                package.add_page(pg)
                n += 1
            last = n - 1
            name = "%s%06d-%s%06d %s.pdf" % (prefix, first, prefix, last, label.title())
            with open(os.path.join(out_dir, name), "wb") as fh:
                single.write(fh)
            rows.append({"label": label, "first": "%s%06d" % (prefix, first), "last": "%s%06d" % (prefix, last),
                         "pages": len(reader.pages), "ocred": rep.get("ocred", 0), "title": title,
                         "source": f, "file": name})
        pkg = os.path.join(out_dir, package_name)
        package.add_metadata({"/Title": "Exhibits %s%06d-%s%06d" % (prefix, start, prefix, n - 1),
                              "/Creator": "Cursitor"})
        try:
            package.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        except Exception:
            pass
        with open(pkg, "wb") as fh:
            package.write(fh)
        index = os.path.join(out_dir, "index.txt")
        with open(index, "w", encoding="utf-8") as fh:
            fh.write(index_text(rows, prefix, slip, stamp_slips))
        return rows, pkg, index
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def index_text(rows, prefix, slip, stamp_slips):
    out = ["EXHIBIT INDEX", "",
           "Bates prefix %s. Built %s. Titles are read from the printed text of each exhibit's first page. "
           "Slip sheets: %s, %s." % (prefix, _dt.date.today().isoformat(), slip,
                                     "numbered" if stamp_slips else "not numbered"), ""]
    for r in rows:
        pages = "%d page%s" % (r["pages"], "" if r["pages"] == 1 else "s")
        if r["ocred"]:
            pages += ", %d OCR'd" % r["ocred"]
        out.append("%s · %s–%s · %s · %s · source file: %s" % (
            r["label"].title(), r["first"], r["last"], pages, r["title"], r["source"]))
    total = sum(r["pages"] for r in rows)
    out += ["", "%d exhibits, %d pages, %s–%s." % (len(rows), total, rows[0]["first"], rows[-1]["last"])]
    return "\n".join(out) + "\n"
