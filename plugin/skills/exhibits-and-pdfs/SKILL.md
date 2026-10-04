---
name: exhibits-and-pdfs
description: "Exhibit packages, Bates numbers, OCR and finding passages in PDFs by page and line. Use when the person has PDFs or scans to attach, produce, search or cite."
---

# Exhibits and PDFs

Engine: `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor"`.

## Exhibit package

`exhibits <folder> <out-dir> --prefix DOE [--start 1] [--slip pleading|plain] [--letters] [--stamp-slips]`

- Order: `order.txt` in the folder (one file name per line), else the number at the front of each file name.
- OCR runs on any page with no text layer (ocrmypdf, or tesseract with ghostscript).
- A slip sheet ("EXHIBIT 1" and the title) goes before each exhibit, on pleading paper or plain.
- Every exhibit page gets a Bates number, PREFIX000001 onward, at the lower right. Slip sheets are not numbered unless `--stamp-slips`.
- Output: one stamped PDF per exhibit, `index.txt`, and `exhibits-package.pdf`.

The index title is read from the printed text of the exhibit's first page, not the file name. Report the index lines as printed.

## OCR

`ocr <pdf>...` writes `name.ocr.pdf` beside each input and reports the pages it OCR'd.

## Citing a PDF

`ask <pdf> "words to find"` prints the best passages as `page:line` (printed margin line numbers on pleading paper; counted lines elsewhere), with `[OCR]` on text that came from OCR. Cite from this output. When it finds nothing, say the words were not found in that PDF; the PDF may still discuss the subject in other words.
