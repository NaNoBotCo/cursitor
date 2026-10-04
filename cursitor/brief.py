"""Morning brief and boot order, as plain text.

    cursitor brief [matter-dir] [--today YYYY-MM-DD] [--no-docket]
    cursitor boot  [matter-dir]
"""
import datetime as _dt
import os
import re

from . import calendar_file as cal
from . import deadlines as dl
from . import docket as _docket
from . import forks as _forks
from . import matter as _matter


def _days(d, today):
    n = (d - today).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    if n < 0:
        return "%d days ago" % -n
    return "in %d days" % n


def brief(matter_dir, today=None, docket=True, fetcher=None):
    today = today or _dt.date.today()
    m = _matter.load(matter_dir)
    its = cal.items(matter_dir)
    open_items = [i for i in its if not i.done and i.date]
    week_end = today + _dt.timedelta(days=7)
    out = ["MORNING BRIEF — %s — %s" % (m.get("name", os.path.basename(matter_dir)), dl.fmt_full(today)), ""]

    def section(title, rows):
        out.append(title)
        out.extend(rows or ["  (none)"])
        out.append("")

    past = [i for i in open_items if i.date < today]
    due = [i for i in open_items if i.date == today]
    week = [i for i in open_items if today < i.date <= week_end]
    clocks = [i for i in open_items if i.date > week_end and i.entry.get("rule")]
    later = [i for i in open_items if i.date > week_end and not i.entry.get("rule")]

    def row(i):
        return "  [%s] %s (%s): %s" % (i.status, i.title, _days(i.date, today), i.line)

    if past:
        section("PAST, NOT MARKED DONE", [row(i) for i in sorted(past, key=lambda x: x.date)])
    section("DUE TODAY", [row(i) for i in due])
    section("NEXT 7 DAYS (through %s)" % dl.fmt(week_end, today.year), [row(i) for i in sorted(week, key=lambda x: x.date)])
    section("CLOCKS RUNNING", [row(i) for i in sorted(clocks, key=lambda x: x.date)])
    section("LATER", [row(i) for i in sorted(later, key=lambda x: x.date)])
    section("PROPOSED — no order, notice or proof of service on disk yet",
            ["  %s — %s" % (i.title, dl.fmt_full(i.date)) for i in sorted(open_items, key=lambda x: x.date)
             if i.status == "PROPOSED" and i.date >= today])
    section("FLAGGED", ["  %s: %s" % (i.title, f) for i in its for f in i.flags])
    fk = []
    for card, dec in _forks.status(matter_dir):
        if dec:
            continue
        exp = card.get("expiry")
        tail = (" — expires %s (%s)" % (exp, _days(dl.parse_date(exp), today))) if exp else ""
        d = card.get("default_if_silent", "none")
        tail += "; if silent: %s" % ("no default — yours" if d in ("none", "") else "(%s)" % d)
        fk.append("  %s %s%s" % (card["id"], card["question"], tail))
    section("OPEN FORKS", fk)
    code = 0
    if docket and m.get("docket_url"):
        kw = {"fetcher": fetcher} if fetcher else {}
        code, lines = _docket.check(matter_dir, m["docket_url"], **kw)
        section("DOCKET", ["  " + ln for ln in lines])
    return "\n".join(out).rstrip() + "\n", code


def last_block(md):
    """The last '## ' block of a Markdown file (the narrative's current state)."""
    parts = re.split(r"(?m)^(?=## )", md)
    blocks = [p for p in parts if p.startswith("## ")]
    return (blocks[-1] if blocks else md).strip()


def boot(matter_dir, today=None):
    today = today or _dt.date.today()
    out = ["BOOT ORDER — %s" % matter_dir, ""]
    st = os.path.join(matter_dir, "STATUS.md")
    out.append("1. STATUS.md — narrative, append-only; the last dated block wins:")
    if os.path.exists(st):
        with open(st, encoding="utf-8") as fh:
            out.extend("   " + ln for ln in last_block(fh.read()).split("\n"))
    else:
        out.append("   STATUS.md is not on this disk")
    out.append("")
    done = os.path.join(matter_dir, "DONE.md")
    out.append("2. DONE.md — a dated line is done; anything else is not:")
    if os.path.exists(done):
        with open(done, encoding="utf-8") as fh:
            dated = [ln.rstrip() for ln in fh if re.match(r"^\s*(- )?\d{4}-\d{2}-\d{2}\b", ln)]
        out.extend("   " + ln.strip() for ln in dated[-10:])
        if not dated:
            out.append("   (no dated lines)")
    else:
        out.append("   DONE.md is not on this disk")
    out.append("")
    out.append("3. calendar.json — next dates:")
    its = [i for i in cal.items(matter_dir) if not i.done and i.date and i.date >= today]
    for i in sorted(its, key=lambda x: x.date)[:6]:
        out.append("   [%s] %s: %s" % (i.status, i.title, i.line))
        for f in i.flags:
            out.append("      FLAG: %s" % f)
    if not its:
        out.append("   (no upcoming dates)")
    out.append("")
    out.append("4. Open forks:")
    open_f = [(c, d) for c, d in _forks.status(matter_dir) if not d]
    for c, _d in open_f:
        out.append("   " + _forks.render_card(c, None, today).replace("\n", "\n   "))
    if not open_f:
        out.append("   (none)")
    return "\n".join(out) + "\n"
