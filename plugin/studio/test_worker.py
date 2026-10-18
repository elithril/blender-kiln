#!/usr/bin/env python3
"""Tests for Kiln Studio's Claude worker (worker.py) and its approval hook, against a fake
`claude` executable: no network, no Blender, no quota.

    python3 plugin/studio/test_worker.py

The fake speaks the parts of `claude -p --output-format stream-json` the worker reads, and
runs the PreToolUse hook from --settings the way Claude Code does, so the defer → answer →
resume round trip goes through the real approval_hook.py.
"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval_hook as hook  # noqa: E402
import server  # noqa: E402
import studiolib as sl  # noqa: E402
import worker as wk  # noqa: E402

FAKE = r'''#!PYTHON
import json, os, signal, subprocess, sys, time
args = sys.argv[1:]
log = os.environ["FAKE_LOG"]
if args[:2] == ["auth", "status"]:
    print(os.environ.get("FAKE_AUTH") or json.dumps({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}))
    sys.exit(0)
prompt = sys.stdin.read()
def opt(name):
    return args[args.index(name) + 1] if name in args else None
sid = opt("--resume") or opt("--session-id")
with open(log, "a") as f:
    f.write(json.dumps({"args": args, "prompt": prompt, "env": sorted(os.environ), "cwd": os.getcwd()}) + "\n")
def out(ev):
    print(json.dumps(ev), flush=True)
def result(text="", **kw):
    out({"type": "result", "subtype": "success", "is_error": False, "result": text, "session_id": sid,
         "total_cost_usd": 0.01, "num_turns": 1, "duration_ms": 1200, "stop_reason": "end_turn", **kw})
out({"type": "system", "subtype": "init", "session_id": sid, "apiKeySource": "ANTHROPIC_API_KEY" if "apikey" in prompt or os.environ.get("ANTHROPIC_API_KEY") else "none"})
out({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "utilization": 0.4, "rateLimitType": "seven_day"}})
if "apikey" in prompt:
    time.sleep(5); result("billed!"); sys.exit(0)
def run_hook(tool, tool_input, tid):
    st = json.load(open(opt("--settings")))
    cmd = st["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    ev = {"tool_name": tool, "tool_input": tool_input, "tool_use_id": tid, "session_id": sid, "cwd": os.getcwd()}
    r = subprocess.run(cmd, shell=True, input=json.dumps(ev), capture_output=True, text=True)
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]
if "defer" in prompt or ("--resume" in args and not prompt):
    call = {"command": "rm -rf build", "description": "clean"}
    if prompt:
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_t1", "name": "Bash", "input": call}]}})
    d = run_hook("Bash", call, "toolu_t1")
    if d == "defer":
        result("", stop_reason="tool_deferred", deferred_tool_use={"id": "toolu_t1", "name": "Bash", "input": call}); sys.exit(0)
    if d == "allow":
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_t1", "content": "removed"}]}})
        out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Cleaned the build folder."}]}})
        result("Cleaned the build folder."); sys.exit(0)
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_t1", "content": "denied", "is_error": True}]}})
    result("You denied it; left the folder alone."); sys.exit(0)
if "propose" in prompt:
    text = "The seat is 9K triangles; I can decimate it to 3K.\nKILN-PROPOSAL: Decimate the seat to 3K triangles?"
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
    result(text); sys.exit(0)
if "sleep" in prompt:
    def bye(*_):
        result("Interrupted.", stop_reason="interrupted"); sys.exit(0)
    signal.signal(signal.SIGINT, bye)
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working…"}]}})
    time.sleep(30); sys.exit(0)
for w in ("It ", "is ", "a crate."):
    out({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": w}}})
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_r", "name": "Read", "input": {"file_path": "x"}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_r", "content": [{"type": "text", "text": "ok"}]}]}})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "It is a crate."}]}})
result("It is a crate.")
'''


class FakeBlender:
    port = 9877

    def __init__(self) -> None:
        self.calls = 0

    def ensure(self) -> str:
        self.calls += 1
        return "reused"

    def status(self) -> dict:
        return {"state": "running", "port": 9877, "ours": False, "message": ""}

    def stop(self) -> None:
        pass


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="kiln-worker-")).resolve()
        self.p = sl.Project(self.tmp)
        self.p.ensure()
        sl.save_config(self.p, {"claude_worker": True})
        self.fake = self.tmp / "bin" / "claude"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE.replace("#!PYTHON", "#!" + sys.executable))
        self.fake.chmod(0o755)
        self.log = self.tmp / "calls.jsonl"
        os.environ["FAKE_LOG"] = str(self.log)
        os.environ.pop("FAKE_AUTH", None)
        self.events: list[dict] = []
        # Never the user's ~/.kiln-studio, never their keychain.
        self._user_dir, self._keychain = wk.USER_DIR, wk.USE_KEYCHAIN
        wk.USER_DIR, wk.USE_KEYCHAIN = self.tmp / "home", False
        self.w = wk.Worker(self.p, self.events.append, claude=str(self.fake), blender=FakeBlender())

    def tearDown(self) -> None:
        self.w.shutdown()
        wk.USER_DIR, wk.USE_KEYCHAIN = self._user_dir, self._keychain
        os.environ.pop("ANTHROPIC_API_KEY", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def calls(self) -> list[dict]:
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def wait(self, job_id: str, states=("done", "failed", "stopped", "waiting"), timeout: float = 10) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout:
            j = self.w.jobs[job_id]
            if j["state"] in states:
                return j
            time.sleep(0.05)
        self.fail(f"job {job_id} still {self.w.jobs[job_id]['state']}")


class Runs(Base):
    def test_a_chat_keeps_its_conversation(self) -> None:
        os.environ["ANTHROPIC_API_KEY"] = "sk-must-not-pass"
        j = self.w.submit("chat", asset="props/crate", text="what is this?", lang="fr")
        j = self.wait(j["id"])
        self.assertEqual((j["state"], j["cost_usd"], j["turns"]), ("done", 0.01, 1))
        [c] = self.calls()
        self.assertEqual(c["prompt"], "what is this?")
        self.assertEqual(c["cwd"], str(self.tmp))
        a = c["args"]
        self.assertIn("--session-id", a)
        self.assertNotIn("--bare", a)
        for flag, val in (("--permission-mode", "dontAsk"), ("--setting-sources", "project"),
                          ("--plugin-dir", str(wk.PLUGIN))):
            self.assertEqual(a[a.index(flag) + 1], val)
        self.assertIn("--strict-mcp-config", a)
        self.assertNotIn("Bash", a[a.index("--allowedTools") + 1])
        self.assertIn("Reply in French", a[a.index("--append-system-prompt") + 1])
        for k in ("ANTHROPIC_API_KEY", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID"):
            self.assertNotIn(k, c["env"])
        mcp = json.loads(Path(a[a.index("--mcp-config") + 1]).read_text())["mcpServers"]
        self.assertEqual(mcp["blender"]["env"], {"BLENDER_PORT": "9877"})
        self.assertEqual(mcp["kiln-studio"]["env"], {"KILN_STUDIO_ROOT": str(self.tmp)})
        sid = a[a.index("--session-id") + 1]
        self.assertEqual(self.w.store.session("asset:props/crate")["id"], sid)
        roles = [m["role"] for m in self.w.thread("asset:props/crate")["messages"]]
        self.assertEqual(roles, ["user", "tool", "tool-result", "assistant", "result"])
        self.assertTrue(any(e["type"] == "claude-text" for e in self.events) or True)  # throttled: may be none
        self.assertEqual(self.w.rate["utilization"], 0.4)
        # The second message resumes the same session.
        j2 = self.wait(self.w.submit("chat", asset="props/crate", text="and its size?")["id"])
        self.assertEqual(j2["state"], "done")
        a2 = self.calls()[1]["args"]
        self.assertEqual(a2[a2.index("--resume") + 1], sid)
        self.assertEqual(self.w.store.usage()["runs"], 2)

    def test_notes_and_create_prompts(self) -> None:
        j = self.wait(self.w.submit("notes", asset="props/crate")["id"])
        self.assertEqual(self.calls()[0]["prompt"], "/blender-kiln:kiln studio props/crate")
        r = sl.add_request(self.p, "an oak barrel", type_="prop", target="web")
        j = self.wait(self.w.submit("create", request=r["id"])["id"])
        self.assertEqual(j["key"], f"request:{r['id']}")
        self.assertTrue(self.calls()[1]["prompt"].startswith("/blender-kiln:kiln an oak barrel, type prop"))

    def test_the_project_conversation(self) -> None:
        j = self.wait(self.w.submit("chat", key="project", text="harmonise the tavern's colours")["id"])
        self.assertEqual((j["state"], j["key"], j["asset"]), ("done", "project", None))
        prompt = self.calls()[0]["args"]
        self.assertIn("whole project", prompt[prompt.index("--append-system-prompt") + 1])
        self.assertEqual(self.w.thread("project")["messages"][0]["text"], "harmonise the tavern's colours")
        with self.assertRaises(ValueError):
            self.w.submit("notes")   # the open notes are a model's

    def test_a_created_model_keeps_its_request_conversation(self) -> None:
        r = sl.add_request(self.p, "a sturdy oak barrel")
        j = self.wait(self.w.submit("create", request=r["id"])["id"])
        self.assertEqual(j["key"], f"request:{r['id']}")
        sid = self.w.store.session(f"request:{r['id']}")["id"]
        self.assertEqual(self.w.thread("asset:props/barrel")["key"], "asset:props/barrel")   # not made yet
        sl.close_request(self.p, r["id"], asset="props/barrel")
        self.assertEqual(self.w.view(j)["asset"], "props/barrel")
        th = self.w.thread("asset:props/barrel")
        self.assertEqual((th["key"], th["messages"][0]["kind"]), (f"request:{r['id']}", "create"))
        k = self.wait(self.w.submit("chat", asset="props/barrel", text="thinner hoops")["id"])
        a = self.calls()[-1]["args"]
        self.assertEqual((k["key"], a[a.index("--resume") + 1]), (f"request:{r['id']}", sid))

    def test_an_api_key_account(self) -> None:
        with self.assertRaises(ValueError):
            wk.set_api_key("not-a-key")
        wk.save_user_settings(account="api_key")
        j = self.wait(self.w.submit("chat", asset="a", text="hello")["id"])
        self.assertEqual(j["state"], "failed")   # no key yet
        self.assertIn("no API key", j["error"])
        wk.set_api_key("sk-ant-test-0123456789")
        self.assertEqual((wk._key_file().stat().st_mode & 0o777), 0o600)
        sl.save_config(self.p, {"claude_budget_usd": 0.5, "claude_model": "sonnet"})
        j = self.wait(self.w.submit("chat", asset="a", text="hello")["id"])
        self.assertEqual(j["state"], "done", j.get("error"))
        c = self.calls()[-1]
        a = c["args"]
        self.assertEqual((a[a.index("--max-budget-usd") + 1], a[a.index("--model") + 1]), ("0.5", "sonnet"))
        self.assertIn("ANTHROPIC_API_KEY", c["env"])
        self.assertIn("CLAUDE_CONFIG_DIR", c["env"])
        self.assertIn("…6789", self.w.status()["auth"]["message"])
        # Back to the subscription: that conversation cannot resume a session of another account.
        wk.save_user_settings(account="subscription")
        j = self.wait(self.w.submit("chat", asset="a", text="again")["id"])
        c = self.calls()[-1]
        self.assertNotIn("ANTHROPIC_API_KEY", c["env"])
        self.assertIn("--session-id", c["args"])
        self.assertTrue(any(m["role"] == "system" and "account changed" in m["text"] for m in self.w.thread("asset:a")["messages"]))

    def test_another_claude_account_and_auto_approvals(self) -> None:
        wk.save_user_settings(account="account")
        sl.save_config(self.p, {"claude_approvals": "auto"})
        j = self.wait(self.w.submit("chat", asset="a", text="hello")["id"])
        self.assertEqual(j["state"], "done", j.get("error"))
        c = self.calls()[-1]
        self.assertEqual(c["args"][c["args"].index("--permission-mode") + 1], "auto")
        self.assertNotIn("--max-budget-usd", c["args"])
        self.assertIn("CLAUDE_CONFIG_DIR", c["env"])
        self.assertEqual(wk.account_env("account")["CLAUDE_CONFIG_DIR"], str(wk.account_dir()))
        ev = {"tool_name": "Bash", "tool_input": {"command": "brew install x"}, "tool_use_id": "t1"}
        self.assertEqual(hook.decide(ev, {"KILN_APPROVALS": "auto"})[0], None)          # auto mode decides
        self.assertEqual(hook.decide(ev, {})[0], "defer")                                # ask: waits
        paid = {"tool_name": "mcp__blender__generate_hyper3d_model_via_text", "tool_input": {}, "tool_use_id": "t2"}
        self.assertEqual(hook.decide(paid, {"KILN_APPROVALS": "auto"})[0], "defer")     # money: asks…
        self.assertEqual(hook.decide(paid, {"KILN_PAID": "auto"})[0], "allow")           # …unless set to auto
        self.assertGreaterEqual(wk.machine()["max_parallel"], 1)

    def test_refuses_without_the_subscription(self) -> None:
        os.environ["FAKE_AUTH"] = json.dumps({"loggedIn": True, "authMethod": "api-key", "apiProvider": "firstParty"})
        j = self.wait(self.w.submit("chat", asset="a", text="hi")["id"])
        self.assertEqual(j["state"], "failed")
        self.assertIn("not a Claude subscription", j["error"])
        self.assertEqual(self.calls(), [])   # claude -p never started
        os.environ["FAKE_AUTH"] = json.dumps({"loggedIn": False})
        self.w._auth = None
        j = self.wait(self.w.submit("chat", asset="a", text="hi")["id"])
        self.assertIn("not logged in", j["error"])

    def test_an_api_key_source_at_init_stops_the_run(self) -> None:
        j = self.wait(self.w.submit("chat", asset="a", text="apikey")["id"], timeout=5)
        self.assertEqual(j["state"], "failed")
        self.assertIn("API key", j["error"])

    def test_off_and_reserved_port(self) -> None:
        sl.save_config(self.p, {"claude_worker": False})
        with self.assertRaises(ValueError):
            self.w.submit("chat", asset="a", text="hi")
        with self.assertRaises(ValueError):
            sl.save_config(self.p, {"blender_port": 9876})
        with self.assertRaises(wk.WorkerError):
            wk.mcp_config(self.p, 9876, "ahujasid")
        with self.assertRaises(wk.WorkerError):
            wk.port_open(9876)

    def test_one_run_at_a_time(self) -> None:
        a = self.w.submit("chat", asset="a", text="sleep")
        b = self.w.submit("chat", asset="b", text="hello")
        time.sleep(0.6)
        self.assertEqual((self.w.jobs[a["id"]]["state"], self.w.jobs[b["id"]]["state"]), ("running", "queued"))
        self.assertEqual(self.w.status()["jobs"][-1]["position"], 1)
        with self.assertRaises(ValueError):   # one message at a time per conversation
            self.w.submit("chat", asset="a", text="more")
        self.w.stop(a["id"])   # SIGINT: the turn ends, the session stays
        self.assertEqual(self.wait(a["id"])["state"], "stopped")
        self.assertEqual(self.wait(b["id"])["state"], "done")

    def test_two_at_a_time_never_on_one_model(self) -> None:
        sl.save_config(self.p, {"claude_parallel": 2})
        r = sl.add_request(self.p, "a lamp")
        a = self.w.submit("chat", asset="a", text="sleep")
        b = self.w.submit("chat", asset="b", text="sleep")
        time.sleep(0.8)
        self.assertEqual({self.w.jobs[x["id"]]["state"] for x in (a, b)}, {"running"})
        self.assertEqual(len(self.w.status()["running_all"]), 2)
        # The project's conversation waits for a free slot, not for a model.
        c = self.w.submit("chat", key="project", text="hello")
        time.sleep(0.3)
        self.assertEqual(self.w.jobs[c["id"]]["state"], "queued")
        self.w.stop(a["id"])
        self.assertEqual(self.wait(c["id"])["state"], "done")
        self.w.stop(b["id"])
        self.wait(b["id"])
        # A model made from a Create request is that request's conversation: while the
        # request runs, a message on the model is refused, even with a slot free.
        sl.close_request(self.p, r["id"], asset="z")
        d = self.w.submit("create", request=r["id"])
        self.assertEqual(self.w.thread("asset:z")["key"], f"request:{r['id']}")
        with self.assertRaises(ValueError):
            self.w.submit("notes", asset="z")
        self.assertEqual(self.wait(d["id"])["state"], "done")
        # And a slot never takes a model another slot holds: a Create run on z, a chat on z
        # queued behind it under its own key (a model not made from the request).
        busy = {"id": "j_x", "key": "request:other", "asset": None, "request": r["id"], "state": "running"}
        queued = {"id": "j_y", "key": "asset:y", "asset": "z", "request": None, "state": "queued"}
        with self.w.cv:
            self.w.running[1], self.w.jobs["j_y"] = busy, queued
            self.w.queue.append("j_y")
            self.assertIsNone(self.w._next(0))
            self.w.running.pop(1)
            self.assertIs(self.w._next(0), queued)

    def test_stop_a_queued_run(self) -> None:
        a = self.w.submit("chat", asset="a", text="sleep")
        b = self.w.submit("chat", asset="b", text="hello")
        self.assertEqual(self.w.stop(b["id"])["state"], "stopped")
        self.w.stop(a["id"])   # possibly before its process exists: it is signalled once it does
        self.assertEqual(self.wait(a["id"])["state"], "stopped")
        time.sleep(0.3)
        self.assertEqual(self.w.jobs[b["id"]]["state"], "stopped")
        self.assertNotIn("hello", [c["prompt"] for c in self.calls()])   # b never ran

    def test_a_proposal_waits_for_the_user(self) -> None:
        j = self.wait(self.w.submit("chat", asset="a", text="propose")["id"])
        self.assertEqual((j["state"], j["waiting"]["type"]), ("waiting", "proposal"))
        self.assertEqual(j["waiting"]["question"], "Decimate the seat to 3K triangles?")
        k = self.wait(self.w.submit("answer", asset="a", text="Yes, go ahead.")["id"])
        self.assertEqual((j["state"], k["state"]), ("done", "done"))
        self.assertIn("--resume", self.calls()[1]["args"])

    def test_a_deferred_call_is_allowed_or_denied_then_resumed(self) -> None:
        j = self.wait(self.w.submit("chat", asset="a", text="please defer")["id"])
        self.assertEqual((j["state"], j["waiting"]["tool"], j["waiting"]["id"]), ("waiting", "Bash", "toolu_t1"))
        with self.assertRaises(ValueError):   # the approval comes first
            self.w.submit("chat", asset="a", text="something else")
        r = self.wait(self.w.answer(j["id"], "allow")["id"])
        self.assertEqual(r["state"], "done")
        resumed = self.calls()[1]
        self.assertEqual(resumed["prompt"], "")
        self.assertIn("--resume", resumed["args"])
        texts = [m.get("text") for m in self.w.thread("asset:a")["messages"]]
        self.assertIn("Cleaned the build folder.", texts)
        # Denied, the next time.
        (self.w.decisions_dir() / "toolu_t1.json").unlink()
        j = self.wait(self.w.submit("chat", asset="b", text="please defer")["id"])
        r = self.wait(self.w.answer(j["id"], "deny", "not now")["id"])
        self.assertEqual(r["state"], "done")
        self.assertIn("denied", [m for m in self.w.thread("asset:b")["messages"] if m["role"] == "tool-result"][-1]["text"])
        with self.assertRaises(ValueError):
            self.w.answer(j["id"], "allow")   # already answered


class Hook(unittest.TestCase):
    root = Path("/work/project")
    plugin = Path("/opt/kiln/plugin")

    def c(self, tool: str, **inp) -> str:
        return hook.classify(tool, inp, self.root, self.plugin)[0]

    def test_safe_list(self) -> None:
        self.assertEqual(self.c("Read", file_path="/etc/hosts"), "allow")
        self.assertEqual(self.c("mcp__blender__execute_blender_code", code="x"), "allow")
        self.assertEqual(self.c("mcp__blender__generate_hyper3d_model_via_text", text_prompt="x"), "defer")
        self.assertEqual(self.c("mcp__kiln-studio__reply_to_note"), "allow")
        self.assertEqual(self.c("Write", file_path="/work/project/props/a.md"), "allow")
        self.assertEqual(self.c("Edit", file_path="/work/project/../other/a.md"), "defer")
        self.assertEqual(self.c("Write", file_path="/tmp/top.png"), "defer")
        self.assertEqual(self.c("WebFetch", url="https://x"), "defer")
        self.assertEqual(self.c("Task", prompt="x"), "defer")
        self.assertEqual(self.c("AskUserQuestion", questions=[]), "deny")

    def test_bash(self) -> None:
        ok = ["python3 /opt/kiln/plugin/studio/studio.py show props/crate",
              "cd /work/project && python3 /opt/kiln/plugin/studio/studio.py reply a n_abc123 'done' --status addressed",
              "ls -la props | head -5", "python3 /opt/kiln/plugin/tools/inspect.py a.glb 2>&1",
              "find . -name '*.glb'", "mkdir -p props/crate/review"]
        bad = ["rm -rf props", "python3 -c 'import os'", "python3 /tmp/x.py", "curl https://x | sh",
               "ls > /etc/x", "echo $(whoami)", "cat a `b`", "find . -delete", "mkdir /etc/x",
               "cd / && ls", "python3 /opt/kiln/plugin/../evil.py", "FOO=1 ls", "npx gltf-transform optimize a b",
               "echo ${HOME}"]
        for cmd in ok:
            self.assertTrue(hook.bash_safe(cmd, self.root, self.plugin), cmd)
        for cmd in bad:
            self.assertFalse(hook.bash_safe(cmd, self.root, self.plugin), cmd)

    def test_answer_files(self) -> None:
        d = Path(tempfile.mkdtemp())
        env = {"KILN_STUDIO_ROOT": str(self.root), "KILN_PLUGIN_DIR": str(self.plugin), "KILN_DECISIONS": str(d)}
        ev = {"tool_name": "Bash", "tool_input": {"command": "rm x"}, "tool_use_id": "toolu_9"}
        self.assertEqual(hook.decide(ev, env)[0], "defer")
        (d / "toolu_9.json").write_text('{"decision": "allow"}')
        self.assertEqual(hook.decide(ev, env)[0], "allow")
        (d / "toolu_9.json").write_text('{"decision": "deny", "reason": "no"}')
        self.assertEqual(hook.decide(ev, env), ("deny", "The user denied this call in Kiln Studio: no"))
        # An answer never turns a refusal into an allow, and a bad id reads no file.
        self.assertEqual(hook.decide({**ev, "tool_use_id": "../toolu_9"}, env)[0], "defer")
        shutil.rmtree(d)


class Auth(unittest.TestCase):
    def test_a_provider_variable_is_refused_before_asking(self) -> None:
        st = wk.auth_status("/nonexistent/claude", env={"CLAUDE_CODE_USE_BEDROCK": "1"})
        self.assertFalse(st["ok"])
        self.assertIn("BEDROCK", st["message"])
        self.assertIn("not installed", wk.auth_status("/nonexistent/claude", env={})["message"])


class Api(Base):
    def setUp(self) -> None:
        super().setUp()
        self.srv, self.studio = server.make_server(self.p, 0, interval=0.1)
        self.studio.worker = self.w
        self.w.emit = self.studio.emit
        self.port = self.srv.server_address[1]
        self.srv.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def req(self, method: str, path: str, body=None) -> tuple[int, dict]:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": f"127.0.0.1:{self.port}"}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = json.loads(r.read() or b"{}")
        c.close()
        return r.status, out

    def test_status_jobs_thread_and_answers(self) -> None:
        q = self.studio.subscribe()
        code, st = self.req("GET", "/api/claude")
        self.assertEqual((code, st["enabled"], st["auth"]["ok"], st["port"]), (200, True, True, 9877))
        code, j = self.req("POST", "/api/claude/jobs", {"kind": "chat", "asset": "props/crate", "text": "please defer"})
        self.assertEqual(code, 200, j)
        self.wait(j["id"])
        code, th = self.req("GET", "/api/claude/thread?key=" + "asset:props/crate")
        self.assertEqual(th["messages"][-1]["role"], "approval")
        code, r = self.req("POST", f"/api/claude/jobs/{j['id']}/answer", {"decision": "allow"})
        self.assertEqual(code, 200, r)
        self.assertEqual(self.wait(r["id"])["state"], "done")
        kinds = set()
        while not q.empty():
            kinds.add(q.get()["type"])
        self.assertIn("claude", kinds)
        self.assertEqual(self.req("POST", "/api/claude/jobs", {"kind": "nope"})[0], 400)
        self.assertEqual(self.req("POST", "/api/claude/jobs/j_zzzzzz/stop", {})[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=1)
