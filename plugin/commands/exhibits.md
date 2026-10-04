---
description: "Build a Bates-stamped exhibit package from a folder of PDFs"
argument-hint: "<folder> <out-dir> --prefix DOE [--start 1] [--slip pleading|plain]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" exhibits $ARGUMENTS` with the Bash tool.

Report the index lines as printed (exhibit, Bates range, pages, OCR'd pages, title read from the first page) and the package path as a short link. If a title reads wrong, the first page's printed text is the source; say which exhibit and what it printed.
