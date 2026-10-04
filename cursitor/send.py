"""Pick a recent output by number, then show it in Finder, copy its path, or open a Mail draft with
it attached. The draft opens in Mail; you address it and press Send.

    cursitor send [matter-dir] [--list] [N] [--reveal | --copy | --mail]
"""
import datetime as _dt
import os
import subprocess
import sys

LOOK_IN = ("out", "drafts", "exhibits-out")
EXT = (".pdf", ".txt", ".docx", ".ics", ".zip")


def recent(matter, limit=15):
    rows = []
    for d in LOOK_IN:
        base = os.path.join(matter, d)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for f in files:
                if f.lower().endswith(EXT) and not f.startswith("."):
                    p = os.path.join(root, f)
                    rows.append((os.path.getmtime(p), p))
    rows.sort(reverse=True)
    return [p for _t, p in rows[:limit]]


def menu(matter, files):
    out = ["Recent outputs in %s:" % matter]
    for i, p in enumerate(files, 1):
        when = _dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%b %d %H:%M")
        out.append("  %2d.  %s   %s   %s" % (i, os.path.relpath(p, matter), when, human(os.path.getsize(p))))
    return "\n".join(out)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0


def is_mac():
    return sys.platform == "darwin"


def reveal(path):
    if is_mac():
        subprocess.run(["open", "-R", path])
        return "Shown in Finder: %s" % path
    return "Path: %s" % path


def copy(path):
    if is_mac():
        subprocess.run(["pbcopy"], input=path.encode("utf-8"))
        return "Path copied: %s" % path
    return "Path: %s" % path


def mail(path):
    if is_mac():
        subprocess.run(["open", "-a", "Mail", path])
        return "Mail opened a new message with %s attached. Address it and press Send in Mail." % os.path.basename(path)
    return "Mail drafts open on macOS only. Path: %s" % path
