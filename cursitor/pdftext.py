"""Text from PDFs, page by page, with OCR for pages that carry no text layer.

Order of tools: pdftotext -layout (poppler) when present, else pypdf. A page with no text
falls back to ghostscript + tesseract when both are installed. When neither is, the page
comes back empty and `missing_ocr()` names what to install.
"""
import glob
import os
import shutil
import subprocess
import tempfile

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def which(name):
    """Find a tool on PATH, or in the per-user Python bin folders pip uses on macOS."""
    p = shutil.which(name)
    if p:
        return p
    home = os.path.expanduser("~")
    for cand in sorted(glob.glob(os.path.join(home, "Library", "Python", "3.*", "bin", name)), reverse=True):
        if os.access(cand, os.X_OK):
            return cand
    for cand in ("/opt/homebrew/bin/" + name, "/usr/local/bin/" + name):
        if os.access(cand, os.X_OK):
            return cand
    return None


def missing_ocr():
    need = [t for t in ("tesseract", "gs") if not which(t)]
    if not need:
        return None
    return "OCR needs %s (macOS: brew install %s)" % (
        " and ".join(need), " ".join("ghostscript" if t == "gs" else t for t in need))


def page_count(pdf):
    return len(PdfReader(pdf).pages)


def _pdftotext(pdf, page):
    exe = which("pdftotext")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-layout", "-f", str(page), "-l", str(page), pdf, "-"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60)
        return out.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return None


def _pypdf(reader, idx):
    page = reader.pages[idx]
    try:
        t = page.extract_text(extraction_mode="layout") or ""
    except Exception:
        t = ""
    if has_text(t):
        return t
    # layout mode drops invisible text, which is how OCR layers are drawn
    try:
        return page.extract_text() or ""
    except Exception:
        return t


def ocr_page(pdf, page, dpi=300):
    """OCR one page (1-based) with ghostscript + tesseract. Returns text or None."""
    gs, tess = which("gs"), which("tesseract")
    if not (gs and tess):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "p.png")
        r = subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pnggray",
                            "-r%d" % dpi, "-dFirstPage=%d" % page, "-dLastPage=%d" % page,
                            "-sOutputFile=" + png, pdf],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if r.returncode != 0 or not os.path.exists(png):
            return None
        out = subprocess.run([tess, png, "stdout", "--psm", "6"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=180)
        return out.stdout.decode("utf-8", "replace")


def has_text(s):
    return bool(s and sum(c.isalpha() for c in s) >= 20)


def pages(pdf, ocr=True):
    """List of (page_number, text, source) where source is 'text', 'ocr' or 'none'."""
    reader = PdfReader(pdf)
    out = []
    for i in range(len(reader.pages)):
        txt = _pdftotext(pdf, i + 1)
        if txt is None:
            txt = _pypdf(reader, i)
        if has_text(txt):
            out.append((i + 1, txt, "text"))
            continue
        if ocr:
            o = ocr_page(pdf, i + 1)
            if has_text(o):
                out.append((i + 1, o, "ocr"))
                continue
        out.append((i + 1, txt or "", "none"))
    return out


def text_pages_without_text(pdf):
    """Page numbers (1-based) whose text layer is empty."""
    reader = PdfReader(pdf)
    empty = []
    for i in range(len(reader.pages)):
        t = _pypdf(reader, i)
        if not has_text(t):
            empty.append(i + 1)
    return empty


def read_any(path, ocr=True):
    """Text of a .txt/.md/.pdf file as a list of (page, text). Text files are one page."""
    if path.lower().endswith(".pdf"):
        return [(n, t) for n, t, _src in pages(path, ocr=ocr)]
    with open(path, encoding="utf-8", errors="replace") as fh:
        return [(1, fh.read())]
