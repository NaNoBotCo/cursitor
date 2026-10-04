---
description: "Make PDFs searchable (OCR for pages without text)"
argument-hint: "<pdf>..."
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" ocr $ARGUMENTS` with the Bash tool. Each file is written beside its input as name.ocr.pdf. Report one line per file: pages OCR'd and pages that still carry no text.
