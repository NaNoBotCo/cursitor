"""cursitor — a litigation kit for Claude Code.

    python3 -m cursitor <command> [options]      (or bin/cursitor)

Commands:
  boot          print the matter's boot order: STATUS, DONE, calendar, open forks
  brief         morning brief: due today, next 7 days, clocks running, proposed, flagged
  deadline      the calendar engine: from | brief-schedule | list | ics | holidays
  pos           read a proof of service and propose the deadlines it starts
  plead         text to pleading paper (California, federal) or a letter
  paste-clean   repair text pasted from a PDF, Word or a court website
  ocr           make PDFs searchable
  exhibits      folder of PDFs to a Bates-stamped exhibit package with an index
  ask           find passages in a PDF, cited page:line
  gate          read your own record before send
  muzzle        check a draft against muzzles.txt
  voice         check writing against the firm's word lists
  fork          fork cards: new | list | decide
  link          short ASCII paths: add | list | prune | mv
  txt           Markdown to plain text
  guard         keep a matter's identifiers out of a git push; `guard install` writes the hook
  send          pick a recent output: show in Finder, copy the path, or open a Mail draft
  new-matter    scaffold a matter folder
  desk          open the large-type local window in the browser
  hook          entry points for the Claude Code plugin hooks
"""
import argparse
import datetime as _dt
import json
import os
import sys

from . import __version__


def _matter_arg(p, positional=True):
    if positional:
        p.add_argument("matter", nargs="?", default=None, help="matter folder (default: the folder holding matter.json at or above here)")
    else:
        p.add_argument("--matter", default=None, help="matter folder")


def _today(s):
    return _dt.date.fromisoformat(s) if s else None


# --------------------------------------------------------------------------- commands

def cmd_boot(a):
    from . import brief, matter
    m = matter.require(a.matter)
    sys.stdout.write(brief.boot(m, _today(a.today)))
    return 0


def cmd_brief(a):
    from . import brief, matter
    m = matter.require(a.matter)
    text, code = brief.brief(m, _today(a.today), docket=not a.no_docket)
    sys.stdout.write(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return code


def cmd_deadline(a):
    from . import calendar_file as cal
    from . import deadlines as dl
    from . import holidays as hol
    from . import matter as _m
    try:
        if a.dcmd == "from":
            r = dl.compute(a.rule, a.served, a.method, a.days, state_holidays=a.state_holidays)
            if a.json:
                print(json.dumps(r.as_dict(), indent=2, ensure_ascii=False))
            else:
                print(r.line)
                for n in r.notes:
                    print("  Note: " + n)
            return 0
        if a.dcmd == "back":
            r = dl.backward(a.rule, a.hearing, a.method)
            print(r.line)
            return 0
        if a.dcmd == "brief-schedule":
            label, rows = dl.brief_schedule(a.hearing, a.rules)
            h = dl.parse_date(a.hearing)
            out = ["BRIEFING SCHEDULE — hearing %s%s — %s" % (dl.fmt_full(h), (" at " + a.time) if a.time else "", label), ""]
            for heading, rule, results in rows:
                out.append(heading)
                for r in results:
                    out.append("  " + r.line)
                for n in (results[0].notes if results else []):
                    out.append("  Note: " + n)
                out.append("")
            text = "\n".join(out).rstrip() + "\n"
            sys.stdout.write(text)
            if a.out:
                with open(a.out, "w", encoding="utf-8") as fh:
                    fh.write(text)
            return 0
        if a.dcmd == "list":
            for table, rule in dl.all_rules():
                if a.jurisdiction and table["jurisdiction"] != ("fed" if a.jurisdiction.startswith("fed") else a.jurisdiction):
                    continue
                print(dl.describe_rule(table, rule))
            print("")
            for jur in ("ca", "fed"):
                t = dl.load_jurisdiction(jur)
                print("%s service methods: %s" % (t["name"], ", ".join(
                    "%s (+%d %s, %s)" % (k, v["add"], "court days" if v.get("unit") == "court" else "days", v["cite"])
                    for k, v in t["methods"].items())))
            return 0
        if a.dcmd == "ics":
            cal_path = os.path.abspath(a.calendar)
            mdir = _m.find(os.path.dirname(cal_path)) or os.path.dirname(cal_path)
            reader_tz, court_tz = a.reader_tz, "America/Los_Angeles"
            mj = os.path.join(mdir, "matter.json")
            if os.path.exists(mj):
                with open(mj, encoding="utf-8") as fh:
                    md = json.load(fh)
                reader_tz = reader_tz or md.get("reader_tz") or None
                court_tz = md.get("court_tz") or court_tz
            text, n = cal.to_ics(mdir, cal_path, reader_tz, court_tz)
            with open(a.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            print("%s: %d events%s" % (a.out, n, (", second time zone " + reader_tz) if reader_tz else ""))
            return 0
        if a.dcmd == "holidays":
            jur = "federal" if a.jurisdiction.startswith("fed") else "ca"
            if a.write:
                print(hol.write_table(a.year, jur))
            else:
                t = hol.table(a.year, jur)
                print("%s %d — %s" % (jur, a.year, t["source"]))
                print("verify against: %s" % t["verify"])
                for row in t["holidays"]:
                    print("  %s %s  %s%s" % (row["weekday"], row["date"], row["name"],
                                             (" (observed for %s)" % row["observed_for"]) if row.get("observed_for") else ""))
            return 0
    except dl.RuleError as exc:
        print("cursitor deadline: %s" % exc, file=sys.stderr)
        return 1
    return 1


def cmd_pos(a):
    from . import matter, pos
    m = matter.find(a.matter or os.path.dirname(os.path.abspath(a.pdf)))
    found, lines, entries = pos.propose(a.pdf, m)
    print("\n".join(lines))
    if a.confirm:
        if not m:
            print("--confirm needs a matter folder (matter.json)", file=sys.stderr)
            return 1
        added = pos.confirm(m, entries)
        print("Written to calendar.json: %d entr%s (order: the proof of service, so SCHEDULED)." % (
            len(added), "y" if len(added) == 1 else "ies"))
    elif entries:
        print("Nothing written. Rerun with --confirm to add %s to calendar.json." % (
            "it" if len(entries) == 1 else "them"))
    return 0 if found.get("date") else 1


def cmd_plead(a):
    from . import matter, pleading
    m = matter.find(a.matter or os.path.dirname(os.path.abspath(a.input)))
    fmt = a.format
    if not fmt and m:
        fmt = matter.load(m).get("format")
    pages, dropped = pleading.plead(a.input, a.output, a.caption, fmt or "ca", a.signed, a.date, a.sig_image,
                                    a.place, a.keep_caption, a.title, m)
    note = (" (dropped %d pasted caption lines; the caption comes from the caption file)" % dropped) if dropped else ""
    print("%s: %d page%s, format %s, %s%s" % (a.output, pages, "" if pages == 1 else "s", fmt or "ca",
                                               "signed /s/ " + a.signed if a.signed else "signature line blank", note))
    return 0


def cmd_paste(a):
    from . import paste
    res = paste.main_cli(a.input, a.output, a.ascii_quotes)
    if a.output:
        paras = sum(1 for ln in res.split("\n") if ln.strip())
        print("%s: %d lines out" % (a.output, paras), file=sys.stderr)
    return 0


def cmd_ocr(a):
    from . import ocr
    code = 0
    for pdf in a.pdfs:
        rep = ocr.ocr(pdf)
        print(ocr.describe(rep))
        if rep.get("error"):
            code = 1
    return code


def cmd_exhibits(a):
    from . import exhibits
    rows, pkg, index = exhibits.build(a.folder, a.out_dir, a.prefix, a.start, a.slip, a.first_exhibit, a.letters,
                                      a.stamp_slips)
    with open(index, encoding="utf-8") as fh:
        sys.stdout.write(fh.read())
    print("Package: %s" % pkg)
    print("Index:   %s" % index)
    return 0


def cmd_ask(a):
    from . import ask
    res = ask.search(a.pdf, " ".join(a.question), a.top, ocr=not a.no_ocr)
    print(ask.render(a.pdf, res, " ".join(a.question), a.json))
    return 0 if res else 1


def cmd_gate(a):
    from . import gate, matter
    m = matter.require(a.matter or os.path.dirname(os.path.abspath(a.draft)))
    text, code = gate.run(os.path.abspath(a.draft), m, a.read, a.top)
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return code


def cmd_muzzle(a):
    from . import matter, muzzle
    m = matter.require(a.matter or os.path.dirname(os.path.abspath(a.draft)))
    hits = muzzle.check(a.draft, m)
    if not muzzle.load(m):
        print("muzzles.txt in %s lists nothing; nothing to check" % m)
        return 0
    for h in hits:
        print(h)
    print("%d muzzle hit(s)" % len(hits) if hits else "clean: no muzzle in %s" % a.draft)
    return 1 if hits else 0


def cmd_voice(a):
    from . import matter, voice
    m = matter.find(os.path.dirname(os.path.abspath(a.files[0]))) if a.files else None
    hits = voice.check_files(a.files, a.words, m)
    for h in hits:
        print(h)
    print("%d hit(s)" % len(hits) if hits else "clean")
    return 1 if hits else 0


def cmd_fork(a):
    from . import forks, matter
    m = matter.require(a.matter)
    if a.fcmd == "new":
        card = forks.new(m, a.question, [forks.parse_option(o) for o in a.option], a.expiry, a.default, a.context or "")
        print(forks.render_card(card))
        print("Written: %s" % os.path.join(m, "forks", card["id"] + ".json"))
        return 0
    if a.fcmd == "list":
        rows = forks.status(m)
        shown = 0
        for card, dec in rows:
            if dec and not a.all:
                continue
            print(forks.render_card(card, dec))
            print("")
            shown += 1
        if not shown:
            print("no open forks" if rows else "no forks in %s" % os.path.join(m, "forks"))
        return 0
    if a.fcmd == "decide":
        row = forks.decide(m, a.id, a.choice, a.by, a.note or "")
        print("%s decided: (%s) by %s at %s — appended to forks/decisions.jsonl" % (row["id"], row["choice"], row["by"], row["at"]))
        return 0
    return 1


def cmd_link(a):
    from . import links
    if a.lcmd == "add":
        print(links.add(a.path, a.name, a.farm, a.force))
    elif a.lcmd == "list":
        print(links.listing(a.farm))
    elif a.lcmd == "prune":
        gone = links.prune(a.farm)
        for g in gone:
            print("removed dead link: %s" % g)
        print("%d removed" % len(gone))
    elif a.lcmd == "mv":
        pts = links.move(a.old, a.new, a.farm)
        print("moved to %s; re-pointed %d link(s)%s" % (a.new, len(pts), (": " + ", ".join(pts)) if pts else ""))
    return 0


def cmd_txt(a):
    from . import txt
    with open(a.input, encoding="utf-8") as fh:
        res = txt.convert(fh.read())
    out = a.output or (os.path.splitext(a.input)[0] + ".txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(res)
    print(out)
    return 0


def cmd_guard(a):
    from . import guard
    if a.repo == "install":
        repo = os.path.abspath(a.extra or ".")
        print("pre-push hook written: %s" % guard.install(repo))
        return 0
    repo = os.path.abspath(a.repo or ".")
    matters = guard.matters_for(a.matter)
    if not matters:
        print("guard: no matters registered (new-matter registers them) and none given with --matter; nothing to check")
        return 0
    hits, n = guard.scan(repo, matters)
    if hits:
        print("BLOCKED — %d hit(s) for matter identifiers in %d tracked/staged files:" % (len(hits), n))
        for h in hits[:200]:
            print("  " + h)
        return 1
    print("guard: clear — %d tracked/staged files carry none of the identifiers of %d matter(s)" % (n, len(matters)))
    return 0


def cmd_send(a):
    from . import matter, send
    m = matter.require(a.matter)
    files = send.recent(m)
    if not files:
        print("no outputs yet in %s" % ", ".join(send.LOOK_IN))
        return 1
    if a.list or a.number is None and not sys.stdin.isatty():
        print(send.menu(m, files))
        return 0
    n = a.number
    if n is None:
        print(send.menu(m, files))
        try:
            n = int(input("Number: ").strip())
        except (ValueError, EOFError, KeyboardInterrupt):
            return 1
    if not 1 <= n <= len(files):
        print("pick 1 to %d" % len(files))
        return 1
    path = files[n - 1]
    if a.mail:
        print(send.mail(path))
    elif a.copy:
        print(send.copy(path))
    else:
        print(send.reveal(path))
    return 0


def cmd_new_matter(a):
    from . import matter
    d = matter.scaffold(a.dir, a.plaintiff or "", a.defendant or "", a.case_no or "", a.county or "", a.caption,
                        a.federal, a.district or "", a.reader_tz)
    print("matter folder: %s" % d)
    for f in ("matter.json", "calendar.json", "STATUS.md", "DONE.md", "muzzles.txt", "CLAUDE.md") + matter.FOLDERS:
        print("  " + f)
    print("registered in %s" % matter.registry_path())
    return 0


def cmd_desk(a):
    from . import desk
    return desk.serve(a.port, a.matter, open_browser=not a.no_open)


def cmd_hook(a):
    from . import hook
    return hook.main(a.which)


# --------------------------------------------------------------------------- parser

def build_parser():
    P = argparse.ArgumentParser(prog="cursitor", description="Litigation kit for Claude Code.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    P.add_argument("--version", action="version", version="cursitor " + __version__)
    S = P.add_subparsers(dest="cmd", metavar="<command>")

    p = S.add_parser("boot", help="print the boot order")
    _matter_arg(p)
    p.add_argument("--today")
    p.set_defaults(fn=cmd_boot)

    p = S.add_parser("brief", help="morning brief")
    _matter_arg(p)
    p.add_argument("--today", help="YYYY-MM-DD (default: today)")
    p.add_argument("--no-docket", action="store_true", help="skip the CourtListener check")
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_brief)

    p = S.add_parser("deadline", help="the calendar engine")
    D = p.add_subparsers(dest="dcmd", metavar="<from|brief-schedule|list|ics|holidays>")
    q = D.add_parser("from", help="a deadline that runs after service or another event")
    q.add_argument("--served", "--from", dest="served", required=True, help="YYYY-MM-DD")
    q.add_argument("--method", default=None, help="personal, mail, mail_out_of_state, mail_out_of_us, overnight, fax, email (federal: mail, clerk, consent, email)")
    q.add_argument("--rule", required=True, help="a rule id from `deadline list`")
    q.add_argument("--days", type=int, help="override the rule's day count")
    q.add_argument("--state-holidays", action="store_true", help="federal: count California holidays under FRCP 6(a)(6)(C)")
    q.add_argument("--json", action="store_true")
    q = D.add_parser("back", help="one deadline counted back from a hearing")
    q.add_argument("--hearing", required=True)
    q.add_argument("--rule", required=True)
    q.add_argument("--method", default=None)
    q = D.add_parser("brief-schedule", help="last days to serve motion, opposition and reply, from a hearing date")
    q.add_argument("--hearing", required=True, help="YYYY-MM-DD")
    q.add_argument("--rules", default="ca", help="ca (CCP §1005) or fed.cdcal")
    q.add_argument("--time", help="hearing time, for the heading")
    q.add_argument("-o", "--out")
    q = D.add_parser("list", help="the rules and their citations")
    q.add_argument("--jurisdiction", default=None)
    q = D.add_parser("ics", help="calendar.json to an .ics file")
    q.add_argument("calendar")
    q.add_argument("out")
    q.add_argument("--reader-tz", default=None, help="second time zone line (default: matter.json reader_tz)")
    q = D.add_parser("holidays", help="print or write a holiday table")
    q.add_argument("--year", type=int, required=True)
    q.add_argument("--jurisdiction", default="ca", help="ca or federal")
    q.add_argument("--write", action="store_true", help="write holidays/<table>.json")
    p.set_defaults(fn=cmd_deadline)

    p = S.add_parser("pos", help="read a proof of service, propose deadlines")
    p.add_argument("pdf")
    _matter_arg(p, positional=False)
    p.add_argument("--confirm", action="store_true", help="write the proposed entries to calendar.json")
    p.set_defaults(fn=cmd_pos)

    p = S.add_parser("plead", help="text to pleading paper or a letter")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--caption", help="caption.json (merged over matter.json's caption)")
    p.add_argument("--format", choices=["ca", "federal", "letter"], default=None)
    p.add_argument("--signed", metavar="NAME", help="print /s/ NAME on the signature line")
    p.add_argument("--sig-image", help="PNG of a signature to draw on the line")
    p.add_argument("--date", help="text after 'Dated:' (default: a blank line)")
    p.add_argument("--place", help="place of signing, after the date")
    p.add_argument("--title", help="document title (caption and footer)")
    p.add_argument("--keep-caption", action="store_true", help="keep a caption pasted at the top of the text")
    _matter_arg(p, positional=False)
    p.set_defaults(fn=cmd_plead)

    p = S.add_parser("paste-clean", help="repair pasted text")
    p.add_argument("input", nargs="?", default="-")
    p.add_argument("-o", "--output")
    p.add_argument("--ascii-quotes", action="store_true", help="straighten curly quotes")
    p.set_defaults(fn=cmd_paste)

    p = S.add_parser("ocr", help="make PDFs searchable")
    p.add_argument("pdfs", nargs="+")
    p.set_defaults(fn=cmd_ocr)

    p = S.add_parser("exhibits", help="exhibit package from a folder")
    p.add_argument("folder")
    p.add_argument("out_dir")
    p.add_argument("--prefix", required=True, help="Bates prefix, e.g. DOE")
    p.add_argument("--start", type=int, default=1, help="first Bates number")
    p.add_argument("--first-exhibit", type=int, default=1)
    p.add_argument("--letters", action="store_true", help="Exhibit A, B, C instead of 1, 2, 3")
    p.add_argument("--slip", choices=["pleading", "plain"], default="pleading")
    p.add_argument("--stamp-slips", action="store_true", help="Bates-number the slip sheets too")
    p.set_defaults(fn=cmd_exhibits)

    p = S.add_parser("ask", help="find passages in a PDF, cited page:line")
    p.add_argument("pdf")
    p.add_argument("question", nargs="+")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-ocr", action="store_true")
    p.set_defaults(fn=cmd_ask)

    p = S.add_parser("gate", help="read your own record before send")
    p.add_argument("draft")
    _matter_arg(p)
    p.add_argument("--read", action="store_true", help="I have read the passages: clear the draft")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_gate)

    p = S.add_parser("muzzle", help="check a draft against muzzles.txt")
    p.add_argument("draft")
    _matter_arg(p)
    p.set_defaults(fn=cmd_muzzle)

    p = S.add_parser("voice", help="check writing against word lists")
    p.add_argument("files", nargs="+")
    p.add_argument("--words", help="a voice.json word list")
    p.set_defaults(fn=cmd_voice)

    p = S.add_parser("fork", help="fork cards")
    F = p.add_subparsers(dest="fcmd", metavar="<new|list|decide>")
    q = F.add_parser("new")
    q.add_argument("--question", required=True)
    q.add_argument("--option", action="append", required=True, help='"key|label|cost|worst case" (repeat)')
    q.add_argument("--expiry", help="YYYY-MM-DD")
    q.add_argument("--default", help="option key that happens if nobody answers, or 'none'")
    q.add_argument("--context")
    _matter_arg(q, positional=False)
    q = F.add_parser("list")
    q.add_argument("--all", action="store_true", help="include decided forks")
    _matter_arg(q, positional=False)
    q = F.add_parser("decide")
    q.add_argument("id")
    q.add_argument("choice")
    q.add_argument("--by", required=True)
    q.add_argument("--note")
    _matter_arg(q, positional=False)
    p.set_defaults(fn=cmd_fork)

    p = S.add_parser("link", help="short ASCII paths")
    L = p.add_subparsers(dest="lcmd", metavar="<add|list|prune|mv>")
    q = L.add_parser("add")
    q.add_argument("path")
    q.add_argument("name", nargs="?")
    q.add_argument("--force", action="store_true", help="re-point an existing name")
    q.add_argument("--farm")
    q = L.add_parser("list")
    q.add_argument("--farm")
    q = L.add_parser("prune")
    q.add_argument("--farm")
    q = L.add_parser("mv", help="rename a file and re-point its links")
    q.add_argument("old")
    q.add_argument("new")
    q.add_argument("--farm")
    p.set_defaults(fn=cmd_link)

    p = S.add_parser("txt", help="Markdown to plain text")
    p.add_argument("input")
    p.add_argument("output", nargs="?")
    p.set_defaults(fn=cmd_txt)

    p = S.add_parser("guard", help="block a push that carries matter identifiers")
    p.add_argument("repo", nargs="?", default=None, help="repository folder, or 'install'")
    p.add_argument("extra", nargs="?", default=None, help="with install: the repository folder")
    p.add_argument("--matter", action="append", help="matter folder (repeat); default: registered matters")
    p.set_defaults(fn=cmd_guard)

    p = S.add_parser("send", help="show, copy or mail a recent output")
    _matter_arg(p)
    p.add_argument("number", nargs="?", type=int)
    p.add_argument("--list", action="store_true")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--reveal", action="store_true", help="show in Finder (default)")
    g.add_argument("--copy", action="store_true", help="copy the path")
    g.add_argument("--mail", action="store_true", help="open a Mail draft with the file attached")
    p.set_defaults(fn=cmd_send)

    p = S.add_parser("new-matter", help="scaffold a matter folder")
    p.add_argument("dir")
    p.add_argument("--plaintiff")
    p.add_argument("--defendant")
    p.add_argument("--case-no")
    p.add_argument("--county")
    p.add_argument("--caption", help="caption.json to use as the caption")
    p.add_argument("--federal", action="store_true")
    p.add_argument("--district", help="e.g. 'Northern District of California'")
    p.add_argument("--reader-tz", help="second time zone for calendar files, e.g. Europe/London")
    p.set_defaults(fn=cmd_new_matter)

    p = S.add_parser("desk", help="large-type local window")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--matter", default=None)
    p.add_argument("--no-open", action="store_true", help="start the server without opening a browser")
    p.set_defaults(fn=cmd_desk)

    p = S.add_parser("hook", help="Claude Code hook entry points")
    p.add_argument("which", choices=["post-write", "pre-bash"])
    p.set_defaults(fn=cmd_hook)
    return P


def main(argv=None):
    P = build_parser()
    a = P.parse_args(argv)
    if not getattr(a, "fn", None):
        P.print_help()
        return 0
    if a.cmd == "deadline" and not a.dcmd:
        P.parse_args(["deadline", "--help"])
    if a.cmd == "fork" and not a.fcmd:
        P.parse_args(["fork", "--help"])
    if a.cmd == "link" and not a.lcmd:
        P.parse_args(["link", "--help"])
    return a.fn(a) or 0
