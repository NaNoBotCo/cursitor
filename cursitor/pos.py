"""Read a proof of service and propose the deadlines it starts.

    cursitor pos <pdf> [--matter DIR] [--confirm]

Finds the service date ("On September 9, 2026, I served"), the method (a checked box, or the
words used), and what was served. Prints each deadline as PROPOSED with its arithmetic. It
writes to calendar.json only with --confirm, and the written entry names the proof of service
as its `order`, so it reads SCHEDULED.
"""
import datetime as _dt
import os
import re

from . import calendar_file as cal
from . import deadlines as dl
from . import pdftext

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
DATE_WORDS = r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})"
DATE_NUM = r"(\d{1,2})/(\d{1,2})/(\d{4})"

SERVED_ON = [
    re.compile(r"\bOn\s+" + DATE_WORDS + r",?\s+I\s+(?:caused\s+to\s+be\s+)?serve", re.I),
    re.compile(r"\bdate\s+of\s+service:?\s*" + DATE_WORDS, re.I),
    re.compile(r"\bserved\s+on\s+" + DATE_WORDS, re.I),
    re.compile(r"\bOn\s+" + DATE_NUM + r",?\s+I\s+(?:caused\s+to\s+be\s+)?serve", re.I),
    re.compile(r"\bdate\s+of\s+service:?\s*" + DATE_NUM, re.I),
]

METHODS = [
    ("email", r"electronic\s+service|electronic\s+transmission|by\s+e-?mail|e-?service|electronically\s+served"),
    ("overnight", r"overnight|express\s+mail|federal\s+express|fedex|\bups\b|next[-\s]day"),
    ("fax", r"\bfax|facsimile"),
    ("personal", r"personal\s+service|personal\s+delivery|by\s+hand|delivered\s+by\s+hand"),
    ("mail", r"by\s+mail|u\.?s\.?\s+mail|first[-\s]class\s+mail|deposited.*mail|postage"),
]
CHECKED = re.compile(r"(\[\s*[xX✓✔]\s*\]|☒|■|\(\s*[xX]\s*\))\s*(.{0,80})")
UNCHECKED = re.compile(r"(\[\s*\]|☐|□|\(\s*\))\s*(.{0,80})")

PAPERS = [
    (r"responses?\s+to\s+special\s+interrogatories|responses?\s+to\s+(form\s+)?interrogatories", "ca.mtc_further_rog",
     "Motion to compel further responses: interrogatories"),
    (r"responses?\s+to\s+requests?\s+for\s+production|responses?\s+to\s+(inspection\s+)?demands?", "ca.mtc_further_rfp",
     "Motion to compel further responses: production"),
    (r"responses?\s+to\s+requests?\s+for\s+admission", "ca.mtc_further_rfa",
     "Motion to compel further responses: admissions"),
    (r"(?<!responses to )special\s+interrogatories|(?<!responses to )form\s+interrogatories", "ca.rog_response",
     "Responses to interrogatories due"),
    (r"(?<!responses to )requests?\s+for\s+production|(?<!responses to )demand\s+for\s+inspection", "ca.rfp_response",
     "Responses to requests for production due"),
    (r"(?<!responses to )requests?\s+for\s+admission", "ca.rfa_response", "Responses to requests for admission due"),
]


def _date(m):
    g = m.groups()
    if g[0].isdigit():
        return _dt.date(int(g[2]), int(g[0]), int(g[1]))
    return _dt.date(int(g[2]), MONTHS[g[0].lower()], int(g[1]))


def read(text):
    flat = re.sub(r"\s+", " ", text)
    found = {"date": None, "method": None, "method_from": None, "papers": [], "out_of_state": False}
    for pat in SERVED_ON:
        m = pat.search(flat)
        if m:
            found["date"] = _date(m)
            break
    checked = [m.group(2) for m in CHECKED.finditer(text)]
    if checked:
        for label in checked:
            for key, pat in METHODS:
                if re.search(pat, label, re.I):
                    found["method"], found["method_from"] = key, "checked box: " + label.strip()[:60]
                    break
            if found["method"]:
                break
    if not found["method"]:
        body = UNCHECKED.sub(" ", text)
        for key, pat in METHODS:
            if re.search(pat, body, re.I):
                found["method"], found["method_from"] = key, "wording"
                break
    seen = set()
    rest = flat
    for pat, rule, label in PAPERS:
        if re.search(pat, rest, re.I) and rule not in seen:
            # a response set should not also trigger the "requests" rule for the same set
            if rule in ("ca.rog_response", "ca.rfp_response", "ca.rfa_response"):
                twin = {"ca.rog_response": "ca.mtc_further_rog", "ca.rfp_response": "ca.mtc_further_rfp",
                        "ca.rfa_response": "ca.mtc_further_rfa"}[rule]
                if twin in seen:
                    continue
            seen.add(rule)
            found["papers"].append((rule, label))
    if found["method"] == "mail":
        states = re.findall(r",\s*([A-Z]{2})\s+\d{5}", text)
        if states and any(s != "CA" for s in states):
            found["out_of_state"] = True
    return found


def propose(pdf, matter=None):
    text = "\n".join(t for _, t in pdftext.read_any(pdf))
    f = read(text)
    lines, entries = [], []
    if not f["date"]:
        return f, ["No service date found in %s. A proof of service reads like: \"On September 9, 2026, I served ...\"" % pdf], []
    method = f["method"] or "personal"
    if method == "mail" and f["out_of_state"]:
        method = "mail_out_of_state"
    lines.append("Proof of service: %s — served %s by %s (%s)." % (
        os.path.basename(pdf), dl.fmt_full(f["date"]), method,
        f["method_from"] or "no method found; personal delivery assumed, which adds no days"))
    if not f["papers"]:
        lines.append("No paper this engine has a rule for was named. `cursitor deadline from` computes one by hand.")
    rel = os.path.relpath(pdf, matter) if matter else pdf
    for rule, label in f["papers"]:
        r = dl.compute(rule, f["date"], method)
        lines.append("PROPOSED  %s: %s" % (label, r.line))
        entries.append({"id": "%s-%s" % (rule.split(".")[1].replace("_", "-"), f["date"].isoformat()),
                        "title": label, "kind": "deadline", "rule": rule, "served": f["date"].isoformat(),
                        "method": method, "date": r.date.isoformat(), "order": rel, "source": "pos"})
    return f, lines, entries


def confirm(matter, entries):
    path = os.path.join(matter, "calendar.json")
    data = cal.load(path) if os.path.exists(path) else {"entries": []}
    have = {e.get("id") for e in data["entries"]}
    added = [e for e in entries if e["id"] not in have]
    data["entries"].extend(added)
    cal.save(path, data)
    return added
