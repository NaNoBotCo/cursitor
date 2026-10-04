"""A matter's calendar.json: status, flags, and .ics export.

An entry is SCHEDULED only when `order` names an order, notice or proof of service that is on
disk in the matter folder. Otherwise it is PROPOSED. An entry marked `moved` needs `moved_by`
naming the signed stipulation or order that moved it, on disk; without one it is flagged.
A date with no rule and no `arithmetic` is flagged as a bare date.
"""
import datetime as _dt
import json
import os

from . import deadlines as dl

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        data = {"entries": data}
    data.setdefault("entries", [])
    return data


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _on_disk(matter_dir, rel):
    if not rel:
        return False
    p = rel if os.path.isabs(rel) else os.path.join(matter_dir, rel)
    return os.path.exists(p)


class Item(object):
    def __init__(self, entry, date, line, status, flags, result=None):
        self.entry = entry
        self.date = date
        self.line = line
        self.status = status
        self.flags = flags
        self.result = result

    @property
    def id(self):
        return self.entry.get("id") or self.entry.get("title", "entry")

    @property
    def title(self):
        return self.entry.get("title") or self.id

    @property
    def done(self):
        return bool(self.entry.get("done"))

    def headline(self):
        when = self.line
        return "[%s] %s: %s" % (self.status, self.title, when)


def evaluate(entry, matter_dir):
    flags = []
    result = None
    date = dl.parse_date(entry["date"]) if entry.get("date") else None
    if entry.get("rule"):
        try:
            if entry.get("hearing"):
                result = dl.backward(entry["rule"], entry["hearing"], entry.get("method"))
            else:
                result = dl.compute(entry["rule"], entry.get("served") or entry.get("trigger"),
                                    entry.get("method"), entry.get("days"))
            if date and date != result.date:
                flags.append("calendar says %s; the rule computes %s" % (dl.fmt_full(date), dl.fmt_full(result.date)))
            date = date or result.date
            line = result.line
            if date != result.date:
                line = "%s (calendar date %s)" % (line, dl.fmt_full(date))
        except (dl.RuleError, KeyError, TypeError) as exc:
            flags.append("rule could not be computed: %s" % exc)
            line = dl.fmt_full(date) if date else "no date"
    elif entry.get("arithmetic"):
        t = (" at %s" % entry["time"]) if entry.get("time") else ""
        line = "%s%s — %s" % (dl.fmt_full(date), t, entry["arithmetic"]) if date else entry["arithmetic"]
    else:
        line = dl.fmt_full(date) if date else "no date"
        flags.append("bare date: no rule and no arithmetic")

    order = entry.get("order")
    if order and _on_disk(matter_dir, order):
        status = "SCHEDULED"
    else:
        status = "PROPOSED"
        if order:
            flags.append("order named but not on this disk: %s" % order)

    if entry.get("moved"):
        mb = entry.get("moved_by")
        if not mb:
            flags.append("moved with no signed stipulation or order named in moved_by")
        elif not _on_disk(matter_dir, mb):
            flags.append("moved_by names a file not on this disk: %s" % mb)
    return Item(entry, date, line, status, flags, result)


def items(matter_dir, calendar_path=None):
    path = calendar_path or os.path.join(matter_dir, "calendar.json")
    if not os.path.exists(path):
        return []
    data = load(path)
    return [evaluate(e, matter_dir) for e in data["entries"]]


# --------------------------------------------------------------------------- .ics

def _esc(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n"))


def _fold(line):
    """RFC 5545: lines over 75 octets continue on the next line after a space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


VTIMEZONE_LA = [
    "BEGIN:VTIMEZONE",
    "TZID:America/Los_Angeles",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:-0800",
    "TZOFFSETTO:-0700",
    "TZNAME:PDT",
    "DTSTART:19700308T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0700",
    "TZOFFSETTO:-0800",
    "TZNAME:PST",
    "DTSTART:19701101T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def second_tz_line(date, time_str, court_tz, reader_tz):
    if not reader_tz or ZoneInfo is None:
        return None
    try:
        ctz, rtz = ZoneInfo(court_tz), ZoneInfo(reader_tz)
    except Exception:
        return "reader_tz %r is not a known time zone" % reader_tz
    if time_str:
        hh, mm = [int(x) for x in time_str.split(":")[:2]]
        local = _dt.datetime(date.year, date.month, date.day, hh, mm, tzinfo=ctz)
        there = local.astimezone(rtz)
        return "%s %s court time is %s %s in %s." % (
            dl.fmt_full(date), time_str, dl.fmt_full(there.date()), there.strftime("%H:%M"), reader_tz)
    local = _dt.datetime(date.year, date.month, date.day, 23, 59, tzinfo=ctz)
    there = local.astimezone(rtz)
    return "11:59 p.m. court time on %s is %s %s in %s." % (
        dl.fmt_full(date), dl.fmt_full(there.date()), there.strftime("%H:%M"), reader_tz)


def to_ics(matter_dir, calendar_path=None, reader_tz=None, court_tz="America/Los_Angeles", now=None):
    now = now or _dt.datetime.utcnow()
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cursitor//calendar engine//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"] + VTIMEZONE_LA
    count = 0
    for it in items(matter_dir, calendar_path):
        if it.done or not it.date:
            continue
        e = it.entry
        desc = [it.line, "Status: %s%s" % (it.status, (" — order: %s" % e["order"]) if it.status == "SCHEDULED" else
                                          " — no order or notice on disk yet")]
        for f in it.flags:
            desc.append("FLAG: " + f)
        if it.result:
            desc.extend("Note: " + n for n in it.result.notes)
        tzline = second_tz_line(it.date, e.get("time"), court_tz, reader_tz)
        if tzline:
            desc.append(tzline)
        lines.append("BEGIN:VEVENT")
        lines.append("UID:%s@cursitor" % _esc(str(it.id)).replace(" ", "-"))
        lines.append("DTSTAMP:" + stamp)
        if e.get("time"):
            hh, mm = [int(x) for x in e["time"].split(":")[:2]]
            start = _dt.datetime(it.date.year, it.date.month, it.date.day, hh, mm)
            end = start + _dt.timedelta(minutes=int(e.get("duration_min", 60)))
            lines.append("DTSTART;TZID=America/Los_Angeles:" + start.strftime("%Y%m%dT%H%M%S"))
            lines.append("DTEND;TZID=America/Los_Angeles:" + end.strftime("%Y%m%dT%H%M%S"))
        else:
            lines.append("DTSTART;VALUE=DATE:" + it.date.strftime("%Y%m%d"))
            lines.append("DTEND;VALUE=DATE:" + (it.date + _dt.timedelta(days=1)).strftime("%Y%m%d"))
        lines.append("SUMMARY:" + _esc("[%s] %s" % (it.status, it.title)))
        if e.get("location"):
            lines.append("LOCATION:" + _esc(e["location"]))
        lines.append("DESCRIPTION:" + _esc("\n".join(desc)))
        lines.append("STATUS:" + ("CONFIRMED" if it.status == "SCHEDULED" else "TENTATIVE"))
        lines.append("END:VEVENT")
        count += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n", count
