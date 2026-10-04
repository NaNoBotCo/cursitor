"""The desk: a large-type window in the browser, served from this Mac.

    cursitor desk [--port 8765] [--matter DIR] [--no-open]

Starts a Python http.server on 127.0.0.1 only and opens /desk/index.html. Six buttons call the
same engine as the command line through small JSON endpoints. Uploaded files and results live
in ~/.cursitor/desk/<job>/. Each API call carries a token printed into the page at start-up,
and the server answers only requests addressed to 127.0.0.1 or localhost.
"""
import json
import os
import secrets
import shutil
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ask as _ask
from . import brief as _brief
from . import deadlines as dl
from . import exhibits as _exhibits
from . import matter as _matter
from . import paste as _paste
from . import pleading as _pleading
from . import send as _send

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "desk")
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript",
         ".pdf": "application/pdf", ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml",
         ".ics": "text/calendar; charset=utf-8", ".json": "application/json"}
MAX_UPLOAD = 60 * 1024 * 1024


def jobs_root():
    return os.path.join(_matter.home(), "desk")


def job_dir(job):
    job = "".join(c for c in (job or "") if c.isalnum())[:32]
    if not job:
        job = secrets.token_hex(6)
    d = os.path.join(jobs_root(), job)
    os.makedirs(d, exist_ok=True)
    return job, d


def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def safe_name(name):
    name = os.path.basename(urllib.parse.unquote(name or "file"))
    keep = "".join(c if (c.isalnum() or c in " ._-()") else "_" for c in name).strip(" .")
    return keep or "file"


class State(object):
    token = ""
    matter = None
    port = 8765


class Handler(BaseHTTPRequestHandler):
    server_version = "CursitorDesk/0.1"

    def log_message(self, fmt, *args):  # quiet console
        pass

    # ---- plumbing ----
    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _token_ok(self, query):
        t = self.headers.get("X-Cursitor-Token") or (query.get("t") or [""])[0]
        return secrets.compare_digest(t, State.token)

    def _json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("too large")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _file_url(self, job, name):
        return "/files/%s/%s?t=%s" % (job, urllib.parse.quote(name), State.token)

    # ---- GET ----
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "host"})
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/desk", "/desk/"):
            self.send_response(302)
            self.send_header("Location", "/desk/index.html")
            self.end_headers()
            return
        if u.path.startswith("/desk/"):
            name = safe_name(u.path[len("/desk/"):])
            p = os.path.join(STATIC, name)
            if not os.path.isfile(p):
                return self._send(404, {"error": "not found"})
            with open(p, "rb") as fh:
                body = fh.read()
            if name == "index.html":
                body = body.replace(b"{{TOKEN}}", State.token.encode())
                label = ""
                if State.matter:
                    try:
                        label = _matter.load(State.matter).get("name") or os.path.basename(State.matter)
                    except Exception:
                        label = os.path.basename(State.matter)
                body = body.replace(b"{{MATTER}}", html_escape(label).encode("utf-8"))
            return self._send(200, body, TYPES.get(os.path.splitext(name)[1], "application/octet-stream"))
        if not self._token_ok(q):
            return self._send(403, {"error": "token"})
        if u.path.startswith("/files/"):
            parts = u.path.split("/")
            if len(parts) != 4:
                return self._send(404, {"error": "not found"})
            job, d = job_dir(parts[2])
            p = os.path.join(d, safe_name(parts[3]))
            if not os.path.isfile(p):
                return self._send(404, {"error": "not found"})
            with open(p, "rb") as fh:
                body = fh.read()
            disp = "inline" if p.endswith((".pdf", ".txt")) else "attachment"
            return self._send(200, body, TYPES.get(os.path.splitext(p)[1], "application/octet-stream"),
                              {"Content-Disposition": '%s; filename="%s"' % (disp, os.path.basename(p))})
        if u.path == "/api/rules":
            rows = [{"id": r["id"], "label": r["label"], "cite": r["cite"]} for _t, r in dl.all_rules()
                    if r["direction"] == "after"]
            return self._send(200, {"rules": rows, "matter": State.matter})
        if u.path == "/api/brief":
            if not State.matter:
                return self._send(200, {"text": "No matter folder is open. Start the desk with --matter <folder> to see its dates."})
            text, _code = _brief.brief(State.matter, docket=False)
            return self._send(200, {"text": text})
        if u.path == "/api/recent":
            return self._send(200, {"files": self._recent()})
        return self._send(404, {"error": "not found"})

    def _recent(self):
        rows = []
        root = jobs_root()
        if os.path.isdir(root):
            for job in os.listdir(root):
                d = os.path.join(root, job)
                if not os.path.isdir(d):
                    continue
                for f in os.listdir(d):
                    p = os.path.join(d, f)
                    if f.lower().endswith((".pdf", ".txt", ".ics")) and not f.startswith("upload-"):
                        rows.append((os.path.getmtime(p), p, self._file_url(job, f)))
        if State.matter:
            for p in _send.recent(State.matter):
                rows.append((os.path.getmtime(p), p, None))
        rows.sort(reverse=True)
        return [{"path": p, "name": os.path.basename(p), "url": url} for _t, p, url in rows[:15]]

    def _allowed(self, path):
        real = os.path.realpath(path)
        roots = [os.path.realpath(jobs_root())] + ([os.path.realpath(State.matter)] if State.matter else [])
        return any(real == r or real.startswith(r + os.sep) for r in roots) and os.path.isfile(real)

    # ---- POST ----
    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "host"})
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if not self._token_ok(q):
            return self._send(403, {"error": "token"})
        try:
            if u.path == "/api/upload":
                job, d = job_dir((q.get("job") or [""])[0])
                name = "upload-" + safe_name((q.get("name") or ["file.pdf"])[0])
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAX_UPLOAD:
                    return self._send(413, {"error": "file over 60 MB"})
                with open(os.path.join(d, name), "wb") as fh:
                    fh.write(self.rfile.read(n))
                return self._send(200, {"job": job, "name": name})
            data = self._json()
            if u.path == "/api/paste":
                job, d = job_dir(data.get("job"))
                text = _paste.clean(data.get("text", ""), bool(data.get("ascii_quotes")))
                with open(os.path.join(d, "cleaned.txt"), "w", encoding="utf-8") as fh:
                    fh.write(text)
                return self._send(200, {"job": job, "text": text, "download": self._file_url(job, "cleaned.txt")})
            if u.path == "/api/plead":
                job, d = job_dir(data.get("job"))
                src = os.path.join(d, "pleading-input.txt")
                with open(src, "w", encoding="utf-8") as fh:
                    fh.write(data.get("text", ""))
                cap = os.path.join(d, "caption.json")
                with open(cap, "w", encoding="utf-8") as fh:
                    title = (data.get("title") or "DOCUMENT").upper()
                    c = {"document_title": title, "footer_title": title}
                    if not State.matter:
                        c.update({"court": [x for x in (data.get("court") or "").split("\n") if x.strip()] or None,
                                  "case_number": data.get("case_no") or "Case No. ______________",
                                  "parties_left": [x for x in (data.get("parties") or "").split("\n")],
                                  "attorney_block": [x for x in (data.get("sender") or "").split("\n")],
                                  "signer": {"name": data.get("signer") or "", "role": data.get("role") or ""}})
                        c = {k: v for k, v in c.items() if v}
                    json.dump(c, fh)
                fmt = data.get("format") or "ca"
                out_name = "%s.pdf" % ("".join(ch if ch.isalnum() else "-" for ch in title.lower()).strip("-")[:40] or "pleading")
                pages, dropped = _pleading.plead(src, os.path.join(d, out_name), cap, fmt, data.get("signed") or None,
                                                 data.get("date") or None, None, None, False, None, State.matter)
                return self._send(200, {"job": job, "pages": pages, "download": self._file_url(job, out_name),
                                        "note": "dropped %d pasted caption lines" % dropped if dropped else ""})
            if u.path == "/api/exhibits":
                job, d = job_dir(data.get("job"))
                src = os.path.join(d, "exhibits-in")
                os.makedirs(src, exist_ok=True)
                for f in sorted(os.listdir(d)):
                    if f.startswith("upload-") and f.lower().endswith((".pdf",) + _exhibits.IMAGE_EXT):
                        shutil.copyfile(os.path.join(d, f), os.path.join(src, f[len("upload-"):]))
                prefix = "".join(c for c in (data.get("prefix") or "EX").upper() if c.isalnum())[:10] or "EX"
                rows, pkg, index = _exhibits.build(src, d, prefix, int(data.get("start") or 1),
                                                   data.get("slip") or "pleading", log=lambda *_a: None)
                with open(index, encoding="utf-8") as fh:
                    idx = fh.read()
                return self._send(200, {"job": job, "index": idx, "package": self._file_url(job, os.path.basename(pkg)),
                                        "index_url": self._file_url(job, "index.txt")})
            if u.path == "/api/due":
                r = dl.compute(data["rule"], data["served"], data.get("method") or None)
                return self._send(200, {"line": r.line, "notes": r.notes, "date": r.date.isoformat()})
            if u.path == "/api/schedule":
                label, rows = dl.brief_schedule(data["hearing"], data.get("rules") or "ca")
                lines = [label]
                for heading, _rule, results in rows:
                    lines.append(heading)
                    lines.extend("  " + r.line for r in results)
                return self._send(200, {"text": "\n".join(lines)})
            if u.path == "/api/ask":
                job, d = job_dir(data.get("job"))
                p = os.path.join(d, safe_name(data.get("name") or ""))
                if not os.path.isfile(p):
                    return self._send(400, {"error": "add a PDF first"})
                res = _ask.search(p, data.get("question") or "", 8)
                return self._send(200, {"text": _ask.render(os.path.basename(p)[len("upload-"):], res, data.get("question") or "")})
            if u.path == "/api/send":
                path = data.get("path") or ""
                if not self._allowed(path):
                    return self._send(400, {"error": "that file is outside the desk and matter folders"})
                act = data.get("action")
                msg = _send.mail(path) if act == "mail" else _send.copy(path) if act == "copy" else _send.reveal(path)
                return self._send(200, {"text": msg})
        except dl.RuleError as exc:
            return self._send(400, {"error": str(exc)})
        except SystemExit as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:
            return self._send(500, {"error": "%s: %s" % (type(exc).__name__, exc)})
        return self._send(404, {"error": "not found"})


def serve(port=8765, matter=None, open_browser=True):
    State.token = secrets.token_urlsafe(18)
    State.matter = _matter.find(matter) if matter else _matter.find()
    State.port = port
    httpd = None
    for p in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            print("port %d is in use; trying %d" % (p, p + 1))
    if httpd is None:
        print("no free port between %d and %d; pass --port" % (port, port + 9))
        return 1
    port = State.port = httpd.server_address[1]
    url = "http://127.0.0.1:%d/desk/index.html" % port
    print("Cursitor desk: %s" % url, flush=True)
    print("Matter: %s" % (State.matter or "none (start with --matter <folder> to see its dates)"))
    print("Press Control-C to stop.", flush=True)
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0
