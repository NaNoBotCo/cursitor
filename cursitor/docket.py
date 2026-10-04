"""Federal docket check through CourtListener's RECAP feed.

matter.json `docket_url` holds a CourtListener docket link, e.g.
https://www.courtlistener.com/docket/12345678/doe-v-roe/ . The check reads the docket's Atom
feed, compares it with docket_state.json in the matter, and reports.

Exit codes: 0 no change (or baseline saved), 2 new entries, 1 fetch or parse error.
RECAP holds what someone has bought from PACER, so it trails PACER; a quiet feed says the feed
is quiet, and PACER is the docket of record.
"""
import json
import os
import re
import urllib.request
from xml.etree import ElementTree

ATOM = "{http://www.w3.org/2005/Atom}"
UA = "Cursitor docket check (+https://github.com/)"


def feed_url(docket_url):
    m = re.search(r"courtlistener\.com/docket/(\d+)", docket_url or "")
    if not m:
        raise ValueError("docket_url is not a CourtListener docket link: %r" % docket_url)
    return "https://www.courtlistener.com/docket/%s/feed/" % m.group(1)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse(xml_bytes):
    root = ElementTree.fromstring(xml_bytes)
    updated = (root.findtext(ATOM + "updated") or "").strip()
    entries = []
    for e in root.iter(ATOM + "entry"):
        title = re.sub(r"\s+", " ", e.findtext(ATOM + "title") or "").strip()
        when = (e.findtext(ATOM + "updated") or e.findtext(ATOM + "published") or "").strip()
        eid = (e.findtext(ATOM + "id") or title).strip()
        entries.append({"id": eid, "title": title, "date": when[:10]})
    return updated, entries


def check(matter_dir, docket_url, fetcher=fetch):
    """Returns (exit_code, lines)."""
    state_path = os.path.join(matter_dir, "docket_state.json")
    try:
        updated, entries = parse(fetcher(feed_url(docket_url)))
    except Exception as exc:
        return 1, ["DOCKET: could not read the feed (%s). The docket page: %s" % (exc, docket_url)]
    prev = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            prev = json.load(fh)
    known = {e["id"] for e in prev.get("entries", [])}
    new = [e for e in entries if e["id"] not in known]
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"updated": updated, "entries": entries}, fh, indent=1)
    if not prev:
        return 0, ["DOCKET: baseline saved — last RECAP activity %s, %d entries." % (updated[:10], len(entries))]
    if not new and updated == prev.get("updated"):
        return 0, ["DOCKET: no change on RECAP since %s (%d entries). PACER is the docket of record." % (
            updated[:10], len(entries))]
    lines = ["DOCKET: NEW on RECAP (feed updated %s):" % updated[:10]]
    lines += ["  %s  %s" % (e["date"], e["title"]) for e in (new or entries)]
    lines.append("  Read the entry on PACER; RECAP carries descriptions only. %s" % docket_url)
    return 2, lines
