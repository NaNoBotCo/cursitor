"""calendar.json status, .ics, paste-clean, pleading paper, gate, muzzle, voice, forks, links, guard,
proof of service, docket, brief, new-matter, txt, exhibits."""
import datetime as dt
import json
import os
import shutil
import subprocess

from cursitor import ask, brief, calendar_file, docket, exhibits, forks, gate, guard, links
from cursitor import matter as matter_mod
from cursitor import muzzle, paste, pdftext, pleading, pos, txt, voice

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "examples", "doe-v-roe")


def _matter(tmp_path):
    d = str(tmp_path / "m")
    shutil.copytree(EX, d)
    return d


# --------------------------------------------------------------------------- calendar.json

def test_status_scheduled_only_with_an_order_on_disk(tmp_path):
    m = str(tmp_path)
    open(os.path.join(m, "order.pdf"), "w").close()
    yes = calendar_file.evaluate({"title": "a", "date": "2026-11-12", "arithmetic": "set by order", "order": "order.pdf"}, m)
    no = calendar_file.evaluate({"title": "b", "date": "2026-11-12", "arithmetic": "reserved online"}, m)
    gone = calendar_file.evaluate({"title": "c", "date": "2026-11-12", "arithmetic": "x", "order": "missing.pdf"}, m)
    assert yes.status == "SCHEDULED" and not yes.flags
    assert no.status == "PROPOSED"
    assert gone.status == "PROPOSED" and any("not on this disk" in f for f in gone.flags)


def test_moved_needs_a_named_stipulation(tmp_path):
    m = str(tmp_path)
    bad = calendar_file.evaluate({"title": "d", "date": "2026-10-28", "arithmetic": "x", "moved": True}, m)
    assert any("moved" in f for f in bad.flags)
    open(os.path.join(m, "stip.pdf"), "w").close()
    ok = calendar_file.evaluate({"title": "d", "date": "2026-10-28", "arithmetic": "x", "moved": True,
                                 "moved_by": "stip.pdf"}, m)
    assert not ok.flags


def test_bare_date_and_wrong_date_are_flagged(tmp_path):
    m = str(tmp_path)
    bare = calendar_file.evaluate({"title": "e", "date": "2026-10-20"}, m)
    assert any("bare date" in f for f in bare.flags)
    wrong = calendar_file.evaluate({"title": "f", "date": "2026-09-08", "rule": "ca.rog_response",
                                    "served": "2026-08-05", "method": "email"}, m)
    assert any("computes Wed Sep 9 2026" in f for f in wrong.flags)


def test_example_calendar_statuses():
    items = {i.id: i for i in calendar_file.items(EX)}
    assert items["mtc-further-rog-2026-09-09"].status == "SCHEDULED"
    assert items["cmc"].status == "SCHEDULED"
    assert items["mtc-hearing"].status == "PROPOSED"
    assert items["plaintiff-deposition"].flags
    assert items["mediation"].flags


def test_ics_has_timezone_arithmetic_and_second_zone():
    text, n = calendar_file.to_ics(EX, reader_tz="Europe/London", now=dt.datetime(2026, 10, 4, 12, 0))
    assert n == 8
    assert "DTSTART;TZID=America/Los_Angeles:20261112T090000" in text
    assert "DTSTART;VALUE=DATE:20261027" in text
    unfolded = text.replace("\r\n ", "")
    assert "in Europe/London" in unfolded
    assert "CCP §2030.300(c)" in unfolded
    assert "[PROPOSED] Hearing: motion to compel further responses" in unfolded
    for line in text.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


# --------------------------------------------------------------------------- paste-clean

def test_paste_clean_repairs_the_example():
    raw = open(os.path.join(EX, "paste", "complaint-pasted.txt"), encoding="utf-8").read()
    out = paste.clean(raw)
    lines = out.split("\n")
    assert "COMPLAINT FOR DAMAGES - " not in out
    assert "- 2 -" not in out
    assert "Doe v. Roe Holdings, LLC — Case No." not in out
    assert not any(l.startswith((" 1  ", "28  ")) for l in lines)
    assert "implied warranty of habitability." in out
    assert "untenantable within" in out
    assert "repair-and-deduct self-help" in out
    assert "inspection report is attached as Exhibit 2" in out
    assert "an inspector from Example Air Testing Co. inspected" in out          # rejoined over a page break
    assert "    Landlord shall keep the premises" in out                       # block quote kept
    assert "JANE DOE,                              )  Case No. 26CV000000" in out   # caption kept
    assert "(Breach of the Implied Warranty of Habitability — Against All Defendants)" in out
    assert "“Roe Holdings”" in out                                    # curly quotes kept by default
    para = [l for l in lines if l.startswith("16. ")]
    assert len(para) == 1 and para[0].endswith("17920.3.")
    assert lines[-3:-1] == ["JANE DOE", "Plaintiff in Pro Per"]


def test_paste_clean_ascii_quotes_only_when_asked():
    assert '"Roe Holdings"' in paste.clean("He said “Roe Holdings” did it.\n", ascii_quotes=True)


def test_paste_clean_plain_wrapped_text():
    src = ("This is a sentence that wraps\nacross two lines of a page and keeps go-\ning on.\n\n"
           "Second paragraph here.\n")
    out = paste.clean(src)
    assert out == "This is a sentence that wraps across two lines of a page and keeps going on.\n\nSecond paragraph here.\n"


# --------------------------------------------------------------------------- pleading paper

def test_plead_from_cleaned_paste(tmp_path):
    src = str(tmp_path / "c.txt")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(paste.clean(open(os.path.join(EX, "paste", "complaint-pasted.txt"), encoding="utf-8").read()))
    out = str(tmp_path / "c.pdf")
    pages, dropped = pleading.plead(src, out, os.path.join(EX, "caption-complaint.json"), "ca", matter_dir=EX)
    assert pages >= 4 and dropped > 10
    p1 = pdftext.pages(out, ocr=False)[0][1]
    assert "SUPERIOR COURT OF THE STATE OF CALIFORNIA" in p1
    assert "Case No. 26CV000000" in p1
    assert "COMPLAINT FOR DAMAGES" in p1
    assert " 28 " in p1 or "\n28" in p1
    last = pdftext.pages(out, ocr=False)[-1][1]
    assert "____" in last and "Plaintiff in Pro Per" in last


def test_plead_signed_federal_and_letter(tmp_path):
    src = str(tmp_path / "d.txt")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write("DECLARATION\n\n1. I am the plaintiff.\n\n2. I served the papers.\n")
    cap = str(tmp_path / "cap.json")
    with open(cap, "w", encoding="utf-8") as fh:
        json.dump({"document_title": "DECLARATION OF JANE DOE", "parties_left": ["JANE DOE,", "  v.", "ROE,"],
                   "case_number": "Case No. 0", "signer": {"name": "JANE DOE", "role": "Plaintiff"}}, fh)
    out = str(tmp_path / "s.pdf")
    pleading.plead(src, out, cap, "federal", signed="Jane Doe", dated="October 5, 2026")
    t = pdftext.pages(out, ocr=False)[0][1]
    assert "UNITED STATES DISTRICT COURT" in t and "/s/ Jane Doe" in t and "October 5, 2026" in t
    out2 = str(tmp_path / "l.pdf")
    pleading.plead(src, out2, cap, "letter")
    t2 = pdftext.pages(out2, ocr=False)[0][1]
    assert "Sincerely," in t2 and "\n 1 " not in t2


def test_wrap_keeps_width():
    lines = pleading.wrap("word " * 200, 300, "Times-Roman", 12)
    from reportlab.pdfbase.pdfmetrics import stringWidth
    assert all(stringWidth(l, "Times-Roman", 12) <= 300 for l in lines)


# --------------------------------------------------------------------------- gate, muzzle, voice

def test_gate_blocks_then_clears_and_finds_the_admission(tmp_path):
    m = _matter(tmp_path)
    draft = os.path.join(m, "drafts", "2026-10-02 meet-and-confer letter.txt")
    text, code = gate.run(draft, m)
    assert code == 1 and "BLOCKED" in text
    assert "Responses to Special Interrogatories Set One.txt" in text
    assert "delivered to Responding Party by email on March 3, 2026" in text
    text, code = gate.run(draft, m, read=True)
    assert code == 0 and "CLEARED" in text
    assert "CLEARED" in open(os.path.join(m, "gate.log"), encoding="utf-8").read()


def test_muzzle_hits_with_line_numbers():
    draft = os.path.join(EX, "drafts", "2026-10-02 meet-and-confer letter.txt")
    hits = muzzle.check(draft, EX)
    assert len(hits) == 1 and ":19 " in hits[0] and "settlement talks" in hits[0]


def test_voice_flags_and_skips_quotes():
    lists, _ = voice.load_lists()
    hits = voice.scan('Let me explain.\nWe just want to ensure this.\nHe wrote "we always pay".\n', lists)  # stylecheck: allow
    kinds = " ".join(hits)
    assert "THROAT" in kinds and "'just'" in kinds and "'ensure'" in kinds
    assert not any("always" in h for h in hits)


def test_voice_firm_list(tmp_path):
    p = str(tmp_path / "voice.json")
    with open(p, "w") as fh:
        json.dump({"filler": [r"\bper se\b"]}, fh)
    lists, src = voice.load_lists(p)
    assert voice.scan("Libel per se.", lists) and not voice.scan("We just ask.", lists)


# --------------------------------------------------------------------------- forks

def test_forks_new_list_decide_append_only(tmp_path):
    m = str(tmp_path)
    c = forks.new(m, "Q?", [forks.parse_option("a|A|1|bad"), forks.parse_option("b|B|2|worse")], "2026-10-20", "a")
    assert c["id"] == "F1"
    assert "If silent: option (a)" in forks.render_card(c, today=dt.date(2026, 10, 5))
    forks.decide(m, "F1", "b", "Jane Doe")
    forks.decide(m, "F1", "a", "Jane Doe", "changed mind")
    rows = forks.decisions(m)
    assert [r["choice"] for r in rows] == ["b", "a"]
    assert forks.status(m)[0][1]["choice"] == "a"
    try:
        forks.decide(m, "F1", "z", "Jane Doe")
    except SystemExit:
        pass
    else:
        raise AssertionError("bad choice accepted")


# --------------------------------------------------------------------------- links

def test_links_add_list_prune_move(tmp_path):
    farm = str(tmp_path / "farm")
    real = tmp_path / "3 — Reply ISO Motion (filed 9-22) — FINAL.pdf"
    real.write_text("x")
    link = links.add(str(real), farm=farm)
    assert os.path.basename(link) == "reply-iso-motion-final.pdf"
    assert all(ord(c) < 128 for c in link)
    other = tmp_path / "other.pdf"
    other.write_text("y")
    l2 = links.add(str(other), "reply-iso-motion-final.pdf", farm=farm)
    assert l2.endswith("reply-iso-motion-final-2.pdf")
    l3 = links.add(str(other), "reply-iso-motion-final.pdf", farm=farm, force=True)
    assert os.path.realpath(l3) == os.path.realpath(str(other))
    moved = links.move(str(other), str(tmp_path / "renamed.pdf"), farm=farm)
    assert moved and all(os.path.exists(os.path.realpath(p)) for p in moved)
    real.unlink()
    links.add(str(tmp_path / "renamed.pdf"), "keep.pdf", farm=farm)
    open(str(tmp_path / "gone.pdf"), "w").close()
    links.add(str(tmp_path / "gone.pdf"), "gone.pdf", farm=farm)
    os.remove(str(tmp_path / "gone.pdf"))
    removed = links.prune(farm)
    assert any(r.endswith("gone.pdf") for r in removed)


# --------------------------------------------------------------------------- guard

def test_guard_blocks_identifiers(tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    with open(os.path.join(repo, "notes.md"), "w") as fh:
        fh.write("public notes\n")
    subprocess.run(["git", "-C", repo, "add", "notes.md"], check=True)
    hits, n = guard.scan(repo, [EX])
    assert not hits and n == 1
    with open(os.path.join(repo, "leak.txt"), "w") as fh:
        fh.write("re: case 26CV000000\n")
    subprocess.run(["git", "-C", repo, "add", "leak.txt"], check=True)
    hits, n = guard.scan(repo, [EX])
    assert hits and "leak.txt:1" in hits[0]
    path = guard.install(repo)
    assert os.access(path, os.X_OK) and "cursitor" in open(path).read()


# --------------------------------------------------------------------------- proof of service

def test_pos_reads_date_method_and_papers():
    text = ("PROOF OF SERVICE\nOn September 9, 2026, I served RESPONSES TO SPECIAL INTERROGATORIES, SET ONE\n"
            "[ ] BY MAIL\n[X] BY ELECTRONIC SERVICE to the address listed\n")
    f = pos.read(text)
    assert f["date"] == dt.date(2026, 9, 9) and f["method"] == "email"
    assert [r for r, _ in f["papers"]] == ["ca.mtc_further_rog"]
    f2 = pos.read("On 09/04/2026, I served REQUESTS FOR ADMISSION by first-class mail to 1 Main St, Reno, NV 89501")
    assert f2["date"] == dt.date(2026, 9, 4) and f2["method"] == "mail" and f2["out_of_state"]
    assert [r for r, _ in f2["papers"]] == ["ca.rfa_response"]


def test_pos_example_pdf_proposes_without_writing(tmp_path):
    m = _matter(tmp_path)
    before = open(os.path.join(m, "calendar.json")).read()
    f, lines, entries = pos.propose(os.path.join(m, "received", "2026-09-09 Proof of Service of responses.pdf"), m)
    assert any("PROPOSED" in l and "Tue Oct 27 2026" in l for l in lines)
    assert open(os.path.join(m, "calendar.json")).read() == before
    assert pos.confirm(m, entries) == []          # already on the calendar under the same ids


# --------------------------------------------------------------------------- docket

FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Docket</title><updated>2026-10-01T10:00:00Z</updated>
<entry><title>ORDER setting hearing</title><id>e1</id><updated>2026-10-01T10:00:00Z</updated></entry>
</feed>"""
FEED2 = FEED.replace(b"</feed>", b"<entry><title>MOTION to dismiss</title><id>e2</id><updated>2026-10-03T10:00:00Z</updated></entry></feed>").replace(b"2026-10-01T10:00:00Z</updated>\n<entry>", b"2026-10-03T10:00:00Z</updated>\n<entry>")


def test_docket_baseline_nochange_new(tmp_path):
    m = str(tmp_path)
    url = "https://www.courtlistener.com/docket/123/doe-v-roe/"
    assert docket.feed_url(url) == "https://www.courtlistener.com/docket/123/feed/"
    code, lines = docket.check(m, url, fetcher=lambda u: FEED)
    assert code == 0 and "baseline" in lines[0]
    code, lines = docket.check(m, url, fetcher=lambda u: FEED)
    assert code == 0 and "no change" in lines[0]
    code, lines = docket.check(m, url, fetcher=lambda u: FEED2)
    assert code == 2 and any("MOTION to dismiss" in l for l in lines)

    def boom(u):
        raise IOError("offline")
    code, lines = docket.check(m, url, fetcher=boom)
    assert code == 1


# --------------------------------------------------------------------------- brief, boot, new-matter, txt

def test_brief_sections():
    text, code = brief.brief(EX, dt.date(2026, 10, 5), docket=False)
    assert code == 0
    for head in ("DUE TODAY", "NEXT 7 DAYS", "CLOCKS RUNNING", "PROPOSED", "FLAGGED", "OPEN FORKS"):
        assert head in text
    assert "Due Fri Oct 9 2026" in text
    assert "bare date" in text and "moved with no signed stipulation" in text
    assert "F1 " in text and "F2 " not in text


def test_boot_reads_last_status_block_and_dated_done_lines():
    text = brief.boot(EX, dt.date(2026, 10, 5))
    assert "## 2026-10-02" in text and "## 2026-09-12" not in text
    assert "2026-09-12 Triage" in text and "Meet-and-confer letter sent." not in text


def test_new_matter_scaffold(tmp_path):
    os.environ["CURSITOR_HOME"] = str(tmp_path / "home")
    try:
        d = matter_mod.scaffold(str(tmp_path / "new"), "Ann Example", "Acme, Inc.", "26CV111111", "Alameda")
        for f in ("matter.json", "calendar.json", "STATUS.md", "DONE.md", "muzzles.txt", "CLAUDE.md"):
            assert os.path.exists(os.path.join(d, f))
        for f in matter_mod.FOLDERS:
            assert os.path.isdir(os.path.join(d, f))
        assert d in matter_mod.registered()
        claude = open(os.path.join(d, "CLAUDE.md")).read()
        assert "not on this disk" in claude and "SCHEDULED" in claude and "gate" in claude
        m = json.load(open(os.path.join(d, "matter.json")))
        assert "26CV111111" in m["identifiers"]
    finally:
        os.environ.pop("CURSITOR_HOME", None)


def test_txt_convert():
    out = txt.convert("# Title\n\nA **bold** line\nwrapped here.\n\n| a | b |\n|---|---|\n| x | y |\n\n- item\n")
    assert "TITLE" in out and "A BOLD line wrapped here." in out and "b: y" in out and "-  item" in out


# --------------------------------------------------------------------------- PDFs: ask, exhibits

def test_ask_cites_page_and_line():
    res = ask.search(os.path.join(EX, "exhibits", "1 Lease agreement.pdf"), "security deposit", 3, ocr=False)
    assert res and res[0]["page"] == 1 and "deposit" in res[0]["text"].lower()
    assert ask.cite(res[0]).startswith("1:")


def test_exhibits_package(tmp_path):
    out = str(tmp_path / "out")
    rows, pkg, index = exhibits.build(os.path.join(EX, "exhibits"), out, "DOE", log=lambda *a: None)
    assert [r["first"] for r in rows] == ["DOE000001", "DOE000003", "DOE000004"]
    assert rows[0]["title"] == "RESIDENTIAL LEASE AGREEMENT"
    from pypdf import PdfReader
    assert len(PdfReader(pkg).pages) == 4 + 3
    text = open(index, encoding="utf-8").read()
    assert "Exhibit 3 · DOE000004–DOE000004" in text
    stamped = pdftext.pages(os.path.join(out, rows[0]["file"]), ocr=False)[0][1]
    assert "DOE000001" in stamped
    if pdftext.which("ocrmypdf") or not pdftext.missing_ocr():
        assert rows[1]["ocred"] == 1 and "MOLD INSPECTION REPORT" in rows[1]["title"]


def test_exhibits_order_file(tmp_path):
    src = str(tmp_path / "in")
    shutil.copytree(os.path.join(EX, "exhibits"), src)
    with open(os.path.join(src, "order.txt"), "w") as fh:
        fh.write("3 Email chain.pdf\n1 Lease agreement.pdf\n")
    assert exhibits.ordered(src)[:2] == ["3 Email chain.pdf", "1 Lease agreement.pdf"]
