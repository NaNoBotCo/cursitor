"""Short ASCII paths for files with long names.

Court files collect names like "3 — Reply ISO Motion (filed 9-22) — FINAL.pdf". Pasting that into
a browser, a chat or an email gives a path full of percent-encoding. This keeps a folder of
symlinks with short ASCII names (default ~/cursitor-links/, or $CURSITOR_LINKS, or --farm) and
prints the plain short path.

    cursitor link add <path> [short-name] [--force]   make or re-point a link
    cursitor link list                                every link, OK or DEAD
    cursitor link prune                               remove dead links
    cursitor link mv <old> <new>                      rename a real file and re-point its links

Links are symlinks: opening one opens the real file; deleting one deletes only the link.
"""
import os
import re
import shutil


def farm_dir(farm=None):
    return os.path.expanduser(farm or os.environ.get("CURSITOR_LINKS") or "~/cursitor-links")


def slug(path):
    name = os.path.basename(path.rstrip("/"))
    name = re.sub(r"^\d{4}-\d{2}-\d{2}[\s_-]*", "", name)        # leading ISO date
    name = re.sub(r"^[0-9]+[a-z]?\s*[—–-]\s*", "", name)      # "3 — " ordinals
    name = re.sub(r"\([^)]*\)", " ", name)                    # bracketed tails
    if "." in name and not name.startswith("."):
        stem, ext = name.rsplit(".", 1)
    else:
        stem, ext = name, ""
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    stem = "-".join(stem.split("-")[:4])[:32].strip("-") or "item"
    return "%s.%s" % (stem, ext.lower()) if ext else stem


def _same(a, b):
    return os.path.realpath(a) == os.path.realpath(b)


def add(target, name=None, farm=None, force=False):
    """Make a link; return its plain path. A dead link under the same name is reclaimed.
    A live link under the same name to another file gets a numbered name, unless force."""
    t = os.path.realpath(os.path.expanduser(target))
    if not os.path.exists(t):
        raise SystemExit("nothing at: %s" % t)
    farm = farm_dir(farm)
    os.makedirs(farm, exist_ok=True)
    n = name or slug(t)
    if "/" in n:
        raise SystemExit("a short name has no slashes: %s" % n)
    link = os.path.join(farm, n)
    if os.path.islink(link) and not os.path.exists(os.path.realpath(link)):
        os.unlink(link)
    if (os.path.lexists(link)) and not _same(link, t) and not force:
        stem, dot, ext = n.partition(".")
        k = 2
        while True:
            cand = os.path.join(farm, "%s-%d%s%s" % (stem, k, dot, ext))
            if not os.path.lexists(cand) or _same(cand, t):
                link = cand
                break
            k += 1
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink(t, link)
    return link


def rows(farm=None):
    farm = farm_dir(farm)
    if not os.path.isdir(farm):
        return []
    out = []
    for e in sorted(os.listdir(farm)):
        if e.startswith("."):
            continue
        p = os.path.join(farm, e)
        real = os.path.realpath(p)
        out.append((os.path.exists(real), p, real))
    return out


def listing(farm=None):
    rs = rows(farm)
    if not rs:
        return "no links yet in %s" % farm_dir(farm)
    w = max(len(p) for _, p, _ in rs)
    lines = ["%s  %-*s  ->  %s" % ("OK  " if ok else "DEAD", w, p, real) for ok, p, real in rs]
    dead = sum(1 for ok, _, _ in rs if not ok)
    lines.append("%d link(s), %d dead" % (len(rs), dead))
    return "\n".join(lines)


def prune(farm=None):
    removed = []
    for ok, p, _ in rows(farm):
        if not ok and os.path.islink(p):
            os.unlink(p)
            removed.append(p)
    return removed


def move(old, new, farm=None):
    """Rename the real file and re-point every link that named it, in one step."""
    old_r = os.path.realpath(os.path.expanduser(old))
    new_p = os.path.abspath(os.path.expanduser(new))
    if not os.path.exists(old_r):
        raise SystemExit("nothing at: %s" % old_r)
    if os.path.exists(new_p):
        raise SystemExit("already exists: %s" % new_p)
    pointing = [p for ok, p, real in rows(farm) if real == old_r]
    shutil.move(old_r, new_p)
    for p in pointing:
        os.unlink(p)
        os.symlink(os.path.realpath(new_p), p)
    return pointing
