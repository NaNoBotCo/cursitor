# Cursitor

A litigation kit for Claude Code: a court-day calendar engine that prints every date with its arithmetic, California and federal pleading paper, exhibit packages with Bates numbers, OCR, page:line search in PDFs, a read-the-record gate before a paper goes out, muzzle lists, fork cards for decisions, and a Claude Code plugin that wires them into a session.

It runs on your Mac with Python 3.9 and two Python packages. The calendar, pleading, paste, gate, muzzle, fork and OCR code make no network calls. Two commands reach the network, and only when asked: `brief` reads a CourtListener feed when `matter.json` names a `docket_url`, and `desk` serves a page on 127.0.0.1.

The example matter, *Jane Doe v. Roe Holdings, LLC*, Case No. 26CV000000, is fictional. So is every name, address and number in it.

## Install

```sh
git clone <this repository> cursitor
cd cursitor
python3 -m pip install --user -r requirements.txt     # pypdf, reportlab
brew install ocrmypdf tesseract ghostscript poppler   # OCR and pdftotext (optional)
bin/cursitor --help
```

Put `bin/` on your PATH, or symlink `bin/cursitor` into a folder that is, to type `cursitor` anywhere. `python3 -m cursitor` works from the repository folder.

Without ocrmypdf, OCR falls back to tesseract with ghostscript. Without those, the OCR step names what to install and the rest of the kit works on PDFs that already carry text.

## A matter folder

```sh
cursitor new-matter ~/Matters/doe-v-roe --plaintiff "Jane Doe" --defendant "Roe Holdings, LLC" \
    --case-no 26CV000000 --county Alameda --reader-tz Europe/London
```

```
matter.json      caption, parties, identifiers, reader_tz, docket_url
calendar.json    dates; each SCHEDULED only when `order` names a file on disk
STATUS.md        narrative, append-only; the last dated block wins
DONE.md          ledger; a dated line is done
muzzles.txt      words, names and patterns that stay off paper
CLAUDE.md        the matter's rules for Claude
served/          discovery and papers you served
received/        responses, notices and orders you received
drafts/  exhibits/  out/  forks/  paste/
```

`new-matter` also records the folder in `~/.cursitor/matters.txt`, which `guard` reads.

## Commands

| Command | What it does |
|---|---|
| `boot [matter]` | Prints the boot order: last STATUS block, dated DONE lines, next dates, open forks |
| `brief [matter] [--today D]` | Due today, next 7 days, clocks running, PROPOSED items, flags, open forks, docket check |
| `deadline from --served D --method M --rule R` | One deadline, forward from service, with its arithmetic |
| `deadline back --hearing D --rule R` | One deadline, counted back from a hearing |
| `deadline brief-schedule --hearing D --rules ca` | Last day to serve the motion by each method, opposition and reply (`fed.cdcal` too) |
| `deadline list` | Rules, periods, citations, service methods |
| `deadline ics calendar.json out.ics` | Calendar file with the arithmetic in each event |
| `deadline holidays --year Y --jurisdiction ca --write` | Prints or writes a holiday table |
| `pos proof.pdf [--confirm]` | Reads a proof of service, prints the deadlines it starts as PROPOSED |
| `plead in.txt out.pdf [--caption c.json] [--format ca\|federal\|letter] [--signed NAME]` | Pleading paper or a letter |
| `paste-clean in.txt [-o out.txt]` | Repairs text pasted from a PDF, Word or a court site |
| `ocr file.pdf...` | Searchable PDFs, written as `file.ocr.pdf` |
| `exhibits folder out --prefix DOE` | Ordered, OCR'd, slip-sheeted, Bates-stamped package with `index.txt` |
| `ask file.pdf words...` | Matching passages cited `page:line` |
| `gate draft [matter] [--read]` | Passages in served/, received/, notes/ on the draft's subject; BLOCKED until `--read` |
| `muzzle draft [matter]` | Exit 1 on any muzzles.txt entry, with line numbers |
| `voice files...` | Filler, throat-clearing and absolute-assurance check, word lists per firm |
| `fork new / list / decide` | Fork cards in forks/, decisions appended to forks/decisions.jsonl |
| `link add / list / prune / mv` | Short ASCII symlinks in `~/cursitor-links/` |
| `txt in.md [out.txt]` | Markdown to plain text, one paragraph per line |
| `guard [repo] / guard install [repo]` | Blocks a push carrying a matter's identifiers; writes a pre-push hook |
| `send [matter] [N] --reveal\|--copy\|--mail` | A recent output: Finder, clipboard, or a Mail draft with it attached |
| `desk` | Large-type window in the browser at 127.0.0.1:8765 |

## The calendar engine

Rules live in `rules/ca.json` and `rules/federal.json`, one entry per rule with its period, direction and citation. Holidays live in `holidays/*.json`, written by `holidays.py` from the rules that define them, each table with a `source` and a `verify` field. Edit a table to match a court's own closures; the engine reads the table when it exists and computes the year when it does not.

Every result is one line:

```
Due Wed Sep 9 2026 — served by email Aug 5 + 30 days (CCP §2030.260) = Fri Sep 4; + 2 court days e-service (§1010.6(a)(3)(B)), skipping Mon Sep 7 Labor Day = Wed Sep 9.
```

California: CCP §12 and §12a counting, §12c backward counting, §1013(a) mail (+5 / +10 / +20 calendar days), §1013(c) overnight and §1010.6(a)(3)(B) e-service (+2 court days), discovery responses (§2030.260, §2031.260, §2033.250), motions to compel further (§2030.300(c), §2031.310(c), §2033.290(c)), answer (§412.20(a)(3), with the service-complete rules of §415.20, §415.30, §415.40), notice, opposition and reply (§1005(b)), case management statement (CRC 3.725). Holidays: CCP §135, Gov. Code §6700, CRC 1.11.

Federal: FRCP 6(a) counting, 6(a)(5) backward, 6(d) +3 days for mail, clerk and consented service (none for electronic service), answer (12(a)(1)(A)(i) and (ii)), discovery responses (33(b)(2), 34(b)(2)(A), 36(a)(3)), and the C.D. Cal. motion schedule (L.R. 6-1, 7-9, 7-10). Holidays: 5 U.S.C. §6103. A California holiday on a federal due date shows as a note (FRCP 6(a)(6)(C)); `--state-holidays` applies it.

Status in `calendar.json`: SCHEDULED when `order` names a file on disk, PROPOSED otherwise. An entry with `moved: true` needs `moved_by` naming the signed stipulation or order, or `brief` flags it. So does a date with no rule and no `arithmetic`, and a stated date that differs from what its rule computes.

## Claude Code plugin

The plugin is in `plugin/`. The repository root carries `.claude-plugin/marketplace.json`, so the repository is also a marketplace.

```sh
claude --plugin-dir ./plugin                 # one session
claude plugin marketplace add ./             # or, inside a session: /plugin marketplace add ./
claude plugin install cursitor@cursitor
```

It adds:

- slash commands: `/cursitor:boot`, `brief`, `deadline`, `plead`, `exhibits`, `ocr`, `paste`, `gate`, `fork`, `link`, `send`;
- skills: calendaring, pleading-paper, exhibits-and-pdfs, read-the-record-gate, forks, file-links;
- hooks: after Write or Edit on a file under a matter's `drafts/`, `muzzle` and `voice` run and report hits back to Claude (exit 2); before a Bash command containing `git push`, `guard` runs and blocks the push on a hit.

The plugin finds the engine through `plugin/scripts/cursitor`: `$CURSITOR_ROOT/bin/cursitor`, then the repository folder above the plugin, then `cursitor` on PATH. When the plugin is installed from a copy without the engine, set `CURSITOR_ROOT` to the repository folder.

## The desk

`cursitor desk --matter ~/Matters/doe-v-roe` (or double-click `Cursitor.command` in Finder) opens a page with six buttons: Paste a lawsuit, Add PDFs, Make pleading paper, What's due, Ask a PDF, Send. The server listens on 127.0.0.1 only, answers requests addressed to 127.0.0.1 or localhost, and checks a token printed into the page at start-up. Uploads and results go to `~/.cursitor/desk/`.

## Tests and samples

```sh
python3 tests/run.py               # uses pytest when installed, else a small built-in runner
python3 scripts/make_example.py    # rebuilds the example matter's PDFs and the messy paste
python3 scripts/make_samples.py    # rebuilds docs/samples/ from the example matter
```

## Layout

```
cursitor/        the package (python3 -m cursitor)
bin/cursitor     command-line shim
rules/           rule tables, one citation per rule
holidays/        holiday tables with source and verify fields
templates/       paper formats: ca, federal, letter
desk/            the desk page
plugin/          Claude Code plugin
examples/        the fictional example matter
tests/           tests
scripts/         example and sample builders
docs/samples/    outputs generated from the example matter
```
