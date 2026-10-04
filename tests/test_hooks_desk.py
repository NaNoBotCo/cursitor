"""Plugin hook entry points and the desk's JSON endpoints."""
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "examples", "doe-v-roe")
CLI = [sys.executable, os.path.join(ROOT, "bin", "cursitor")]


def _hook(which, payload, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(CLI + ["hook", which], input=json.dumps(payload).encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=e)


def test_post_write_hook_reports_muzzle_hit_in_drafts():
    draft = os.path.join(EX, "drafts", "2026-10-02 meet-and-confer letter.txt")
    r = _hook("post-write", {"tool_name": "Write", "tool_input": {"file_path": draft}})
    assert r.returncode == 2
    assert b"settlement talks" in r.stderr


def test_post_write_hook_ignores_files_outside_drafts():
    r = _hook("post-write", {"tool_name": "Write", "tool_input": {"file_path": os.path.join(EX, "STATUS.md")}})
    assert r.returncode == 0


def test_pre_bash_hook_blocks_push_with_identifiers(tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    with open(os.path.join(repo, "a.txt"), "w") as fh:
        fh.write("Roe Holdings memo\n")
    subprocess.run(["git", "-C", repo, "add", "a.txt"], check=True)
    env = {"CURSITOR_MATTER": EX, "CURSITOR_HOME": str(tmp_path / "home")}
    r = _hook("pre-bash", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}, "cwd": repo}, env)
    assert r.returncode == 2 and b"push blocked" in r.stderr
    r = _hook("pre-bash", {"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": repo}, env)
    assert r.returncode == 0


def test_desk_endpoints(tmp_path):
    from cursitor import desk
    os.environ["CURSITOR_HOME"] = str(tmp_path / "home")
    try:
        desk.State.token = "t0ken"
        desk.State.matter = EX
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), desk.Handler)
        port = httpd.server_address[1]
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        base = "http://127.0.0.1:%d" % port

        def call(path, body=None, token="t0ken"):
            req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                         headers={"X-Cursitor-Token": token, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        code, page = call("/desk/index.html")
        assert code == 200 and b"t0ken" in page and b"Paste a lawsuit" in page
        assert call("/api/rules", token="wrong")[0] == 403
        code, body = call("/api/due", {"served": "2026-08-05", "method": "email", "rule": "ca.discovery_response"})
        assert code == 200 and b"Wed Sep 9 2026" in body
        raw = open(os.path.join(EX, "paste", "complaint-pasted.txt"), encoding="utf-8").read()
        code, body = call("/api/paste", {"text": raw})
        j = json.loads(body)
        assert code == 200 and "habitability" in j["text"]
        code, body = call("/api/plead", {"job": j["job"], "text": j["text"], "title": "Complaint", "format": "ca"})
        assert code == 200 and json.loads(body)["pages"] >= 4
        code, body = call("/api/brief")
        assert code == 200 and b"MORNING BRIEF" in body
        code, body = call("/api/send", {"path": "/etc/hosts", "action": "copy"})
        assert code == 400
        code, body = call("/api/recent")
        assert code == 200 and json.loads(body)["files"]
        httpd.shutdown()
        httpd.server_close()
    finally:
        os.environ.pop("CURSITOR_HOME", None)
        shutil.rmtree(str(tmp_path / "home"), ignore_errors=True)
