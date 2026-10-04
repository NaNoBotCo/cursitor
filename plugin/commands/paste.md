---
description: "Clean text pasted from a PDF, Word or a court website"
argument-hint: "<in.txt> [-o out.txt] [--ascii-quotes]"
---

Run `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" paste-clean $ARGUMENTS` with the Bash tool. With no file, write the pasted text to a file in the matter's paste/ folder first, then run it on that file with `-o`.

Show the first part of the result and say what was removed (line numbers, running headers and footers, page numbers) and what was kept (caption, numbered paragraphs, headings, block quotes).
