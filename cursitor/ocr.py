"""Make PDFs searchable.

    cursitor ocr <pdf>...        writes name.ocr.pdf beside each input

Uses ocrmypdf --skip-text, which OCRs only the pages that carry no text. Without ocrmypdf it
falls back to ghostscript + tesseract for those pages. Without either it says what to install.
"""
import os
import shutil
import subprocess
import tempfile

from pypdf import PdfReader, PdfWriter

from . import pdftext


def out_name(pdf):
    base, _ext = os.path.splitext(pdf)
    return base + ".ocr.pdf"


def _fallback(pdf, out, pages):
    gs, tess = pdftext.which("gs"), pdftext.which("tesseract")
    if not (gs and tess):
        return False
    reader = PdfReader(pdf)
    writer = PdfWriter()
    with tempfile.TemporaryDirectory() as tmp:
        for i, page in enumerate(reader.pages, 1):
            if i not in pages:
                writer.add_page(page)
                continue
            png = os.path.join(tmp, "p%d.png" % i)
            subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pnggray", "-r200",
                            "-dFirstPage=%d" % i, "-dLastPage=%d" % i, "-sOutputFile=" + png, pdf],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            base = os.path.join(tmp, "p%d" % i)
            subprocess.run([tess, png, base, "pdf"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            writer.add_page(PdfReader(base + ".pdf").pages[0])
        with open(out, "wb") as fh:
            writer.write(fh)
    return True


def ocr(pdf, out=None, quiet=False):
    """OCR the pages of `pdf` that have no text. Returns a dict report."""
    out = out or out_name(pdf)
    total = pdftext.page_count(pdf)
    empty = pdftext.text_pages_without_text(pdf)
    report = {"input": pdf, "output": out, "pages": total, "needed": len(empty), "ocred": 0, "tool": None}
    if not empty:
        shutil.copyfile(pdf, out)
        report["tool"] = "none needed"
        return report
    exe = pdftext.which("ocrmypdf")
    ok = False
    if exe:
        r = subprocess.run([exe, "--skip-text", "--output-type", "pdf", "--optimize", "1", "-q", pdf, out],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ok = r.returncode == 0 and os.path.exists(out)
        report["tool"] = "ocrmypdf"
        if not ok:
            report["error"] = r.stderr.decode("utf-8", "replace").strip()[-400:]
    if not ok:
        ok = _fallback(pdf, out, set(empty))
        report["tool"] = "tesseract" if ok else None
    if not ok:
        report["error"] = report.get("error") or (pdftext.missing_ocr() or "OCR failed") + \
            "; ocrmypdf is a pip or brew install"
        return report
    still = pdftext.text_pages_without_text(out)
    report["ocred"] = len(empty) - len(still)
    report["still_empty"] = still
    return report


def describe(rep):
    if rep.get("error"):
        return "%s: no OCR run (%s)" % (rep["input"], rep["error"])
    if rep["needed"] == 0:
        return "%s: %d pages, all have text; copied to %s" % (rep["input"], rep["pages"], rep["output"])
    s = "%s: OCR'd %d of %d pages with %s -> %s" % (rep["input"], rep["ocred"], rep["pages"], rep["tool"], rep["output"])
    if rep.get("still_empty"):
        s += " (pages still without text: %s)" % ", ".join(map(str, rep["still_empty"]))
    return s
