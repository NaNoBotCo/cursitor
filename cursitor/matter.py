"""A matter folder: find it, read it, scaffold a new one, keep a list of them.

    cursitor new-matter <dir> --plaintiff "Jane Doe" --defendant "Roe Holdings, LLC"
                        --case-no 26CV000000 --county Alameda [--caption caption.json] [--federal]
"""
import datetime as _dt
import json
import os

FOLDERS = ("served", "received", "drafts", "exhibits", "out", "forks", "paste")


def home():
    return os.path.expanduser(os.environ.get("CURSITOR_HOME") or "~/.cursitor")


def registry_path():
    return os.path.join(home(), "matters.txt")


def registered():
    p = registry_path()
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def register(path):
    path = os.path.abspath(path)
    have = registered()
    if path in have:
        return False
    os.makedirs(home(), exist_ok=True)
    with open(registry_path(), "a", encoding="utf-8") as fh:
        fh.write(path + "\n")
    return True


def find(start=None):
    """The matter folder: `start` if it holds matter.json, else the nearest parent that does."""
    d = os.path.abspath(start or os.getcwd())
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        if os.path.exists(os.path.join(d, "matter.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def require(start=None):
    m = find(start)
    if not m:
        raise SystemExit("no matter.json in %s or any folder above it; `cursitor new-matter` makes one"
                         % os.path.abspath(start or os.getcwd()))
    return m


def load(matter_dir):
    with open(os.path.join(matter_dir, "matter.json"), encoding="utf-8") as fh:
        return json.load(fh)


CLAUDE_MD = """# Matter rules for Claude — {name}

Boot order, every session:
1. STATUS.md — the narrative. Append-only. The last dated block wins.
2. DONE.md — the ledger. A dated line means done. A line without a date, or an unclear one, means not done.
3. calendar.json — dates. `cursitor brief` reads it.
4. forks/ — open decisions. `cursitor fork list`.

`cursitor boot` prints all four.

Working rules for this matter:
- File links: give every file as a short link from `cursitor link add <path>`, a plain path with no file:// prefix.
- Dates: a date goes out with its arithmetic, in one line. `cursitor deadline from` writes the line.
- Scheduled: an event is SCHEDULED only when an order, notice or proof of service on disk names it (the entry's `order` field). Otherwise it is PROPOSED. A date is MOVED only when the signed stipulation or order that moved it is on disk and named in `moved_by`.
- Read the record before send: before clearing any paper for service or filing, run `cursitor gate <draft>`, read every passage it prints from served/ and received/, then rerun with `--read`.
- Muzzles: muzzles.txt lists words and topics that stay off paper. `cursitor muzzle <draft>` checks a draft.
- Forks go to the person: options, cost, worst case, expiry, default if silent — written with `cursitor fork new`, decided by the person with `cursitor fork decide`. A standing instruction with no recorded decision is an open fork.
- Reader copies: anything the person reads ships as plain .txt (`cursitor txt`), one paragraph per line.
- Absence: when a document is not in this folder, say "not on this disk", not "does not exist".
"""

STATUS_MD = """# STATUS — {name}

Append a dated block for each working session. The last block wins.

## {today}

Matter folder created. Nothing filed or served from this folder yet.
"""

DONE_MD = """# DONE — {name}

One line per finished item, starting with its date (YYYY-MM-DD). No date means not done.

{today} Matter folder created.
"""

MUZZLES = """# One entry per line: a word, a name or a regular expression (case-insensitive).
# `cursitor muzzle <draft>` exits 1 when a draft contains any of them.
# Lines starting with # are notes.
"""


def scaffold(dest, plaintiff="", defendant="", case_no="", county="", caption=None, federal=False,
             district="", reader_tz=None, name=None):
    dest = os.path.abspath(dest)
    if os.path.exists(os.path.join(dest, "matter.json")):
        raise SystemExit("a matter already lives at %s" % dest)
    os.makedirs(dest, exist_ok=True)
    for f in FOLDERS:
        os.makedirs(os.path.join(dest, f), exist_ok=True)
    today = _dt.date.today().isoformat()
    name = name or ("%s v. %s" % (plaintiff.split(",")[0] or "Plaintiff", defendant.split(",")[0] or "Defendant"))
    cap = {}
    if caption:
        with open(caption, encoding="utf-8") as fh:
            cap = json.load(fh)
    if not cap:
        court = (["UNITED STATES DISTRICT COURT", (district or "NORTHERN DISTRICT OF CALIFORNIA").upper()]
                 if federal else ["SUPERIOR COURT OF THE STATE OF CALIFORNIA",
                                  "COUNTY OF %s" % (county or "______________").upper()])
        cap = {
            "attorney_block": [plaintiff.upper(), "[street address]", "[city, state ZIP]",
                               "Telephone: [number]", "Email: [address]", "", "Plaintiff in Pro Per"],
            "court": court,
            "parties_left": [plaintiff.upper() + ",", "", "                    Plaintiff,", "",
                             "          v.", "", defendant.upper() + ",", "",
                             "                    Defendant."],
            "case_number": "Case No. %s" % case_no if case_no else "Case No. ______________",
            "signer": {"name": plaintiff.upper(), "role": "Plaintiff in Pro Per"},
        }
    ids = [x for x in (case_no, plaintiff, defendant.split(",")[0]) if x]
    matter = {
        "name": name,
        "jurisdiction": "fed" if federal else "ca",
        "format": "federal" if federal else "ca",
        "court_tz": "America/Los_Angeles",
        "reader_tz": reader_tz or "",
        "case_number": case_no,
        "parties": {"plaintiff": [plaintiff] if plaintiff else [], "defendant": [defendant] if defendant else []},
        "identifiers": ids,
        "docket_url": "",
        "caption": cap,
    }
    files = {
        "matter.json": json.dumps(matter, indent=2, ensure_ascii=False) + "\n",
        "calendar.json": json.dumps({"matter": name, "entries": []}, indent=2) + "\n",
        "STATUS.md": STATUS_MD.format(name=name, today=today),
        "DONE.md": DONE_MD.format(name=name, today=today),
        "muzzles.txt": MUZZLES,
        "CLAUDE.md": CLAUDE_MD.format(name=name),
        os.path.join("forks", "decisions.jsonl"): "",
    }
    for rel, body in files.items():
        with open(os.path.join(dest, rel), "w", encoding="utf-8") as fh:
            fh.write(body)
    register(dest)
    return dest
