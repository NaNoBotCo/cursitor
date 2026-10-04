---
name: pleading-paper
description: "Make court papers: California or federal pleading paper (28 numbered lines, caption, footer) or a plain letter, from text. Use when a draft needs to become a PDF for filing, service or mailing, or when text pasted from a PDF needs cleaning first."
---

# Pleading paper

Engine: `"${CLAUDE_PLUGIN_ROOT}/scripts/cursitor" plead <in.txt|md> <out.pdf>`.

## Input

One paragraph per line, blank line between paragraphs. This is the shape `paste-clean` writes. Markdown works too.

- `# TITLE` or an ALL-CAPS line under 80 characters: centred bold heading.
- `1. Text`: numbered paragraph. `(a) Text`: sub-item.
- `> Text` or a line indented four spaces: block quote.
- `[[SIGNATURE]]` places the signature block; otherwise it goes at the end. A pasted "Dated: ..." block at the end is read and replaced by the engine's own.
- `[[PAGEBREAK]]` starts a new page.

## Caption

The caption comes from, in order: `--caption caption.json`, the matter's `matter.json` `caption`, then a caption pasted at the top of the text (lines with a `)` column), which the engine reads and redraws. Fields: `attorney_block`, `court`, `parties_left`, `case_number`, `document_title`, `right_extra`, `footer_title`, `signer` {name, role}.

## Formats

- `--format ca` (default): Cal. Rules of Court 2.100 et seq.; party block from line 1, court title on line 8, title of the paper in the footer.
- `--format federal`: same grid, district court title (from the caption's `court`).
- `--format letter`: one-inch margins, sender block at top, `--date` under it.

## Signatures

Without `--signed` the signature line prints blank for a wet signature. `--signed "Jane Doe"` prints `/s/ Jane Doe`. `--sig-image file.png` draws an image. `--date` fills the Dated line.

## Before filing or service

Run `muzzle` and `gate` on the source text first (see the read-the-record-gate skill). Paragraphs and the signature block do not split across pages, and the last paragraph stays with the signature.

## Pasted text

`paste-clean in.txt -o out.txt` removes margin line numbers, running headers and footers, and page numbers; rejoins hard-wrapped lines; mends words hyphenated across a line break; and keeps the caption, numbered paragraphs, headings and block quotes. `--ascii-quotes` straightens curly quotes.
