"""Kiln Studio's Claude worker: the page asks, Claude Code (`claude -p`) answers, on the
user's own Claude login — one run at a time.

A PROTOTYPE. What it holds to:
- **The account the user chose, and only it** (Settings → Claude, kept per user in
  ~/.kiln-studio/claude.json, never in the project): their Claude subscription as Claude
  Code is logged in (default); another Claude account, logged in once into a config folder
  of Studio's own (CLAUDE_CONFIG_DIR), so the terminal's Claude Code keeps its own; or an
  Anthropic API key, kept in the macOS keychain (elsewhere a 0600 file), billed per token
  and capped per request (--max-budget-usd). Before each run the account is checked
  (`claude auth status` must say claude.ai and the first-party provider for the first two);
  the child never inherits this session's keys, never `--bare`; and a run whose init event
  reports another source of credentials than the one chosen is stopped at once.
- **One run at a time**: a queue. The subscription's quota is shared by every session, and
  there is one Blender.
- **Its own Blender**: a GUI Blender on the project's `blender_port` (default 9877, never
  9876), with its own profile under .kiln-studio/cache/worker/, and an MCP config that
  points the Blender MCP server at that port — `--strict-mcp-config`, so the user's own
  `blender` MCP (port 9876) is never loaded.
- **Approvals**: `--permission-mode dontAsk`, a short --allowedTools list, and
  approval_hook.py as a PreToolUse hook (via --settings) that defers anything outside a
  safe list; the user allows or denies it in the page, and the session is resumed.
- **A conversation per model** (and per Create request): its session id and its messages
  are kept in .kiln-studio/claude/ (git-ignored).

Standard library only. The `claude` executable and the Blender launcher are injectable:
test_worker.py runs it against a fake `claude`.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import studiolib as sl

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
HOOK = HERE / "approval_hook.py"
BLENDER_START = HERE / "worker_blender.py"
RESERVED_PORT = 9876
MCP_VERSION = "2.0.0"   # ahujasid's blender-mcp, the server and its bundled add-on together
JOB_KINDS = ("chat", "notes", "create", "answer", "resume", "setup")
SETUP_KEY = "setup"
STATES = ("queued", "running", "waiting", "done", "failed", "stopped")
# Read-only tools Claude may use with no hook at all (belt and braces: if the hook ever
# fails, dontAsk refuses everything not listed here).
ALLOWED = ["Read", "Glob", "Grep", "TodoWrite", "Skill", "ToolSearch", "mcp__kiln-studio"]
# Variables that would bill an API, make the child think it is nested in this session,
# or carry this session's identity.
DROP_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_MESSAGING_SOCKET",
            "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_PID",
            "CLAUDE_SYSTEM_PROMPT", "CLAUDE_CODE_EXECPATH", "CLAUDE_EFFORT", "CLAUDE_PROJECT_DIR",
            "CLAUDE_PLUGIN_ROOT")
# A provider other than Anthropic's bills elsewhere: refused too.
PROVIDER_ENV = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
PROPOSAL = "KILN-PROPOSAL:"
MAX_RUN_S = 3600
ACCOUNTS = ("subscription", "account", "api_key")
USER_DIR = Path(os.environ.get("KILN_STUDIO_HOME") or "~/.kiln-studio").expanduser()
KEYCHAIN = ("kiln-studio", "anthropic-api-key")   # service, account
USE_KEYCHAIN = sys.platform == "darwin" and os.environ.get("KILN_STUDIO_KEYCHAIN") != "0"   # off in tests


class WorkerError(Exception):
    """A run that cannot start; the message is for the user."""


def clean_env(base: dict | None = None) -> dict:
    env = dict(os.environ if base is None else base)
    for k in DROP_ENV:
        env.pop(k, None)
    return env


# ── the account: per user, not per project ──────────────────────────────────


def user_settings() -> dict:
    d = sl.read_json(USER_DIR / "claude.json", {}) or {}
    return {"account": d.get("account") if d.get("account") in ACCOUNTS else "subscription"}


def save_user_settings(**kw) -> dict:
    if "account" in kw and kw["account"] not in ACCOUNTS:
        raise ValueError(f"account must be one of {', '.join(ACCOUNTS)}")
    cur = {**user_settings(), **kw}
    USER_DIR.mkdir(parents=True, exist_ok=True)
    sl.write_json(USER_DIR / "claude.json", cur)
    return cur


def account_dir() -> Path:
    """Studio's own Claude Code config folder, for another Claude account."""
    return USER_DIR / "claude-account"


def api_key_dir() -> Path:
    """The API key's runs keep their sessions apart from the subscription's."""
    return USER_DIR / "claude-api"


def _key_file() -> Path:
    return USER_DIR / "api_key"


def get_api_key() -> str | None:
    if USE_KEYCHAIN and shutil.which("security"):
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN[0], "-a", KEYCHAIN[1], "-w"],
                           capture_output=True, text=True)
        return r.stdout.strip() or None if r.returncode == 0 else None
    f = _key_file()
    return f.read_text().strip() or None if f.is_file() else None


def set_api_key(key: str | None) -> None:
    """Keep the key (None forgets it): the macOS keychain, else a file only the user reads."""
    if key is not None:
        key = key.strip()
        if not key.startswith("sk-ant-") or len(key) > 300 or any(c.isspace() for c in key):
            raise ValueError("that does not look like an Anthropic API key (sk-ant-…)")
    if USE_KEYCHAIN and shutil.which("security"):
        subprocess.run(["security", "delete-generic-password", "-s", KEYCHAIN[0], "-a", KEYCHAIN[1]], capture_output=True)
        if key:
            r = subprocess.run(["security", "add-generic-password", "-s", KEYCHAIN[0], "-a", KEYCHAIN[1], "-w", key, "-U"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise ValueError("the keychain refused the key: " + r.stderr.strip()[:200])
        return
    f = _key_file()
    if not key:
        f.unlink(missing_ok=True)
        return
    USER_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(key)
    f.chmod(0o600)


def account_env(account: str, base: dict | None = None) -> dict:
    """The child's environment for that account: never this session's credentials."""
    e = clean_env(base)
    if account == "account":
        e["CLAUDE_CONFIG_DIR"] = str(account_dir())
    elif account == "api_key":
        e["CLAUDE_CONFIG_DIR"] = str(api_key_dir())
        key = get_api_key()
        if key:
            e["ANTHROPIC_API_KEY"] = key
    else:
        e.pop("CLAUDE_CONFIG_DIR", None)
    return e


def auth_status(claude: str = "claude", env: dict | None = None, timeout: float = 20, account: str = "subscription") -> dict:
    """Whether the worker may run on the chosen account, and what to tell the user."""
    out = {"ok": False, "account": account, "method": None, "provider": None, "subscription": None, "message": ""}
    if account == "api_key":
        key = get_api_key()
        out.update(method="api_key", ok=bool(key),
                   message=f"your Anthropic API key (…{key[-4:]})" if key else "no API key yet: add one in Settings → Claude")
        return out
    e = account_env(account, env)
    out["message"] = ""
    on = [k for k in PROVIDER_ENV if e.get(k) not in (None, "", "0", "false")]
    if on:
        out["message"] = f"{on[0]} is set: Claude Code would bill that provider, not your subscription"
        return out
    try:
        r = subprocess.run([claude, "auth", "status"], capture_output=True, text=True, timeout=timeout,
                           env=e, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        out["message"] = f"Claude Code is not installed ({claude} not found)"
        return out
    except subprocess.TimeoutExpired:
        out["message"] = "claude auth status did not answer"
        return out
    try:
        st = json.loads(r.stdout)
    except ValueError:
        out["message"] = "claude auth status said something unexpected: " + (r.stdout or r.stderr).strip()[:200]
        return out
    out.update(method=st.get("authMethod"), provider=st.get("apiProvider"),
               subscription=st.get("subscriptionType"), email=st.get("email"))
    if not st.get("loggedIn"):
        out["message"] = ("this Claude account is not logged in yet: Settings → Claude → Log in" if account == "account"
                          else "Claude Code is not logged in: run `claude` once in a terminal and log in")
    elif st.get("authMethod") != "claude.ai":
        out["message"] = (f"Claude Code is logged in with {st.get('authMethod')!r}, not a Claude subscription "
                          "(claude.ai): to run on an API key, choose API key in Settings → Claude")
    elif st.get("apiProvider") not in (None, "firstParty"):
        out["message"] = f"Claude Code uses the {st.get('apiProvider')} provider, not your Claude subscription"
    else:
        out["ok"] = True
        who = st.get("subscriptionType") or "claude.ai"
        out["message"] = f"another Claude account ({st.get('email') or who})" if account == "account" else f"your Claude subscription ({who})"
    return out


def login_account(claude: str = "claude") -> subprocess.Popen:
    """Start `claude auth login` for Studio's own account folder: it opens the browser."""
    account_dir().mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([claude, "auth", "login", "--claudeai"], env=account_env("account"),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)


def machine() -> dict:
    """RAM and cores, and how many Blenders in parallel this machine takes: about 1 GB each
    beyond 4 GB kept for the rest, at most one per two cores, 1 to 4."""
    ram = None
    try:
        if sys.platform == "darwin":
            ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5).stdout.strip())
        elif hasattr(os, "sysconf"):
            ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError, subprocess.SubprocessError):
        ram = None
    cores = os.cpu_count() or 2
    gb = ram / 2**30 if ram else None
    ceiling = max(1, min(4, cores // 2, int(gb - 4) if gb else 1))
    return {"ram_gb": round(gb, 1) if gb else None, "cores": cores, "max_parallel": ceiling}


# ── the worker's Blender ─────────────────────────────────────────────────────


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    if port == RESERVED_PORT:
        raise WorkerError("port 9876 is reserved for your own Blender; the worker never uses it")
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def blender_binary() -> str | None:
    for c in (os.environ.get("BLENDER"), shutil.which("blender"),
              "/Applications/Blender.app/Contents/MacOS/Blender"):
        if c and Path(c).is_file():
            return c
    return None


def lab_dir() -> Path | None:
    p = os.environ.get("KILN_STUDIO_LAB_DIR")
    return Path(p) if p and (Path(p) / "mcp").is_dir() else None


def mcp_config(project: sl.Project, port: int, kind: str) -> dict:
    """The run's MCP servers: the Blender MCP on the worker's port, and kiln-studio."""
    if port == RESERVED_PORT:
        raise WorkerError("port 9876 is reserved for your own Blender; pick another in Settings")
    if kind == "lab":
        d = lab_dir()
        if not d:
            raise WorkerError("the Blender Lab MCP needs KILN_STUDIO_LAB_DIR: the folder of its git checkout")
        blender = {"command": "uvx", "args": ["--from", str(d / "mcp"), "blender-mcp"],
                   "env": {"BLENDER_MCP_PORT": str(port), "BLENDER_PATH": blender_binary() or ""}}
    else:
        blender = {"command": "uvx", "args": [f"blender-mcp=={MCP_VERSION}"],
                   "env": {"BLENDER_PORT": str(port)}}
    studio = {"command": sys.executable, "args": [str(HERE / "mcp_server.py")],
              "env": {"KILN_STUDIO_ROOT": str(project.root)}}
    # Named "blender" like the user's own, so the skill's mcp__blender__* calls reach it.
    return {"mcpServers": {"blender": blender, "kiln-studio": studio}}


class _PidProc:
    """A process Studio did not start itself (macOS `open -g`): poll, stop and wait on its pid."""

    def __init__(self, pid: int):
        self.pid, self.returncode = pid, None

    def poll(self):
        try:
            os.kill(self.pid, 0)
            return None
        except ProcessLookupError:
            self.returncode = self.returncode if self.returncode is not None else 0
            return self.returncode
        except PermissionError:
            return None

    def terminate(self) -> None:
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def kill(self) -> None:
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def wait(self, timeout: float | None = None):
        t0 = time.time()
        while self.poll() is None:
            if timeout is not None and time.time() - t0 > timeout:
                raise subprocess.TimeoutExpired(str(self.pid), timeout)
            time.sleep(0.2)
        return self.returncode


def app_bundle(exe: str) -> Path | None:
    """The .app a macOS Blender binary lives in (…/Blender.app/Contents/MacOS/Blender)."""
    p = Path(exe).resolve()
    return p.parents[2] if sys.platform == "darwin" and len(p.parents) > 2 and p.parents[2].suffix == ".app" else None


class Blender:
    """One of the worker's GUI Blenders: started on demand, reused, stopped with Studio.
    Blender `index` serves on blender_port + index, with a profile of its own."""

    def __init__(self, project: sl.Project, index: int = 0):
        self.project = project
        self.index = index
        self.proc: subprocess.Popen | None = None
        self.state = "stopped"   # stopped | starting | running | failed
        self.message = ""
        self.port: int | None = None
        self.lock = threading.Lock()

    @property
    def dir(self) -> Path:
        d = self.project.data / "cache" / "worker"
        return d if self.index == 0 else d / f"blender-{self.index + 1}"

    def port_now(self) -> int:
        return self.project.settings()["blender_port"] + self.index

    def status(self) -> dict:
        port = self.port_now()
        alive = self.proc is not None and self.proc.poll() is None
        try:
            up = port_open(port)
        except WorkerError:
            up = False
        state = self.state
        if state == "running" and not up:
            state = "stopped"
        if state == "stopped" and up:
            state = "running"
        return {"state": state, "port": port, "ours": alive, "message": self.message}

    def _addon(self) -> Path:
        out = subprocess.run(["uvx", "--from", f"blender-mcp=={MCP_VERSION}", "python", "-c",
                              "import blender_mcp, os; print(os.path.join(os.path.dirname(blender_mcp.__file__), 'bundled', 'addon.py'))"],
                             capture_output=True, text=True, timeout=300)
        p = Path((out.stdout.strip().splitlines() or [""])[-1])
        if out.returncode != 0 or not p.is_file():
            raise WorkerError(f"could not fetch blender-mcp {MCP_VERSION}'s add-on with uvx: {out.stderr.strip()[-300:]}")
        return p

    def ensure(self) -> str:
        """Blender serving the MCP add-on on the project's port: "reused" or "started"."""
        st = self.project.settings()
        port, kind = self.port_now(), st["blender_mcp"]
        with self.lock:
            if port_open(port):
                self.state, self.port, self.message = "running", port, ""
                return "reused"
            exe = blender_binary()
            if not exe:
                raise WorkerError("Blender not found: install it, or set $BLENDER")
            self.state, self.message = "starting", ""
            profile = self.dir / "blender-profile"
            try:
                extra: list[str] = []
                if kind == "lab":
                    d = lab_dir()
                    if not d:
                        raise WorkerError("the Blender Lab MCP needs KILN_STUDIO_LAB_DIR: the folder of its git checkout")
                    ext = profile / "extensions" / "user_default" / "mcp"
                    shutil.rmtree(ext, ignore_errors=True)
                    shutil.copytree(d / "addon" / "blender_mcp_addon", ext)
                    extra = ["--online-mode"]
                else:
                    (profile / "scripts" / "addons").mkdir(parents=True, exist_ok=True)
                    shutil.copy(self._addon(), profile / "scripts" / "addons" / "blender_mcp.py")
                env = dict(clean_env(), KILN_BLENDER_PORT=str(port), KILN_BLENDER_MCP=kind,
                           BLENDER_USER_SCRIPTS=str(profile / "scripts"), BLENDER_USER_CONFIG=str(profile / "config"),
                           BLENDER_USER_EXTENSIONS=str(profile / "extensions"), BLENDER_USER_DATAFILES=str(profile / "datafiles"))
                log = (self.dir / "blender.log").open("ab")
                # GUI, not --background: rule 2's viewport screenshots need a viewport.
                args = ["--factory-startup", *extra, "--python-exit-code", "1", "--python", str(BLENDER_START)]
                app = app_bundle(exe) if st["blender_behind"] else None
                pidfile = self.dir / "blender.pid"
                if app:
                    # Behind the other windows, focus left where it is: Blender's own
                    # --no-window-focus does not hold on macOS, `open -g` does.
                    pidfile.unlink(missing_ok=True)
                    envs = [a for k, v in env.items() if k.startswith(("KILN_", "BLENDER_USER_")) for a in ("--env", f"{k}={v}")]
                    envs += ["--env", f"KILN_BLENDER_PIDFILE={pidfile}"]
                    subprocess.run(["open", "-g", "-n", "-a", str(app), *envs, "--stdout", str(self.dir / "blender.log"),
                                    "--stderr", str(self.dir / "blender.log"), "--args", *args], check=True, timeout=30,
                                   capture_output=True)
                    self.proc = None
                else:
                    if st["blender_behind"]:
                        args.insert(1, "--no-window-focus")   # honoured outside macOS
                    self.proc = subprocess.Popen([exe, *args], env=env, stdout=log, stderr=subprocess.STDOUT,
                                                 stdin=subprocess.DEVNULL, start_new_session=True)
                for _ in range(240):
                    if self.proc is None and pidfile.is_file():
                        try:
                            self.proc = _PidProc(int(pidfile.read_text().strip()))
                        except ValueError:
                            pass
                    if port_open(port):
                        self.state, self.port = "running", port
                        return "started"
                    if self.proc is not None and self.proc.poll() is not None:
                        raise WorkerError(f"Blender exited ({self.proc.returncode}) before serving; see {self.dir / 'blender.log'}")
                    time.sleep(0.5)
                if self.proc is not None:
                    self.proc.kill()
                raise WorkerError(f"Blender never opened port {port}; see {self.dir / 'blender.log'}")
            except WorkerError as e:
                self.state, self.message = "failed", str(e)
                raise

    def stop(self) -> None:
        with self.lock:
            pidfile = self.dir / "blender.pid"
            if self.proc is None and pidfile.is_file():
                # One opened behind (open -g) by an earlier Studio, still serving.
                try:
                    self.proc = _PidProc(int(pidfile.read_text().strip()))
                except ValueError:
                    pass
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(15)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc, self.state = None, "stopped"


# ── conversations: .kiln-studio/claude/ ──────────────────────────────────────


PROJECT_KEY = "project"
SETUP_PARTS = ("blender", "optimizers", "skintokens", "unimate")


def thread_key(kind: str, asset: str | None, request: str | None) -> str:
    """A conversation per model (asset:<id>), per Create request (request:<id>), and one for
    the whole project (project): what concerns several models at once."""
    if kind == "setup":
        return SETUP_KEY
    if kind == "create" or (request and not asset):
        return f"request:{request}"
    return f"asset:{asset}" if asset else PROJECT_KEY


def short(v, n: int = 300) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"


class Store:
    def __init__(self, project: sl.Project):
        self.project = project
        self.lock = threading.Lock()

    @property
    def dir(self) -> Path:
        d = self.project.data / "claude"
        if not d.is_dir():
            self.project.ensure()
            d.mkdir(parents=True, exist_ok=True)
            # Conversations are the user's, not the project's: kept out of git.
            (d / ".gitignore").write_text("*\n")
        return d

    def _thread_file(self, key: str) -> Path:
        return self.dir / "threads" / (sl.asset_key(key.replace(":", "~", 1)) + ".jsonl")

    def append(self, key: str, entry: dict) -> dict:
        entry = {"at": sl.now(), **entry}
        p = self._thread_file(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, p.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def thread(self, key: str, limit: int = 400) -> list[dict]:
        p = self._thread_file(key)
        if not p.is_file():
            return []
        out = []
        for line in p.read_text().splitlines()[-limit:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def sessions(self) -> dict:
        return sl.read_json(self.dir / "sessions.json", {})

    def canonical(self, key: str) -> str:
        """The conversation a key stands for. A model made from a Create request keeps that
        request's conversation: Claude remembers making it, and the page shows it on the model."""
        if not key.startswith("asset:"):
            return key
        link = (self.sessions().get(key) or {}).get("alias")
        if link:
            return link
        if self.session(key):
            return key
        asset = key.split(":", 1)[1]
        r = next((x for x in sl.load_requests(self.project) if x.get("asset") == asset), None)
        if r:
            self.set_session(key, alias=f"request:{r['id']}")
            return f"request:{r['id']}"
        return key

    def session(self, key: str) -> dict | None:
        return self.sessions().get(key)

    def set_session(self, key: str, **kw) -> dict:
        with self.lock:
            all_ = self.sessions()
            s = {**all_.get(key, {}), **kw, "updated": sl.now()}
            all_[key] = s
            sl.write_json(self.dir / "sessions.json", all_)
        return s

    def usage(self, entry: dict | None = None) -> dict:
        p = self.dir / "usage.jsonl"
        if entry:
            with self.lock, p.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        runs, cost, by = 0, 0.0, {}
        if p.is_file():
            for line in p.read_text().splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                runs += 1
                cost += e.get("cost_usd") or 0
                a = by.setdefault(e.get("account") or "subscription", {"runs": 0, "cost_usd": 0.0})
                a["runs"] += 1
                a["cost_usd"] = round(a["cost_usd"] + (e.get("cost_usd") or 0), 4)
        # A subscription's runs cost nothing more (API-equivalent, for scale); an API key's are billed.
        return {"runs": runs, "cost_usd_equiv": round(cost, 4), "by_account": by}


# ── the worker ───────────────────────────────────────────────────────────────


def system_context(project: sl.Project, job: dict, port: int, lang: str) -> str:
    target = (f"The model the user has open in Kiln Studio is `{job['asset']}`." if job.get("asset")
              else "This conversation is about the whole project, not one model: the user may ask about "
                   "several models at once. `studio.py list` and the kiln-studio list_models tool name them."
              if job.get("key") == PROJECT_KEY
              else "This conversation installs what kiln needs on this computer, asked from Studio's setup list. "
                   "Before any download, say its size and licence and end with a KILN-PROPOSAL line asking to go "
                   "ahead; a licence that limits use (non-commercial, not in the EU) is said plainly."
              if job.get("key") == SETUP_KEY
              else "This conversation is about a model the user asked for in Studio's Create form. When it "
                   "exists, close the request with its asset (`studio.py request <id> --asset <asset>`).")
    return "\n".join([
        "You are running inside Kiln Studio, the user's browser page, started by its Claude worker with "
        "`claude -p`. There is no terminal: the user reads your messages in the page and answers in a later turn.",
        f"Project root: {project.root}. The kiln skill's folder (<skill>): {PLUGIN}. Run its scripts as "
        f"`python3 {PLUGIN}/studio/studio.py …` with absolute paths, from the project root.",
        "Kiln Studio is already running for this project and shows the user every change: do not start, "
        "stop or open it, do not print its URL.",
        f"Blender: the `blender` MCP tools drive Studio's own Blender (port {port}). Use only them.",
        target,
        "When kiln's rule 6, or any decision, needs the user's choice: stop before acting, say what you "
        f"propose, and end your message with one line `{PROPOSAL} <the question, answerable yes or no>`. "
        "The page shows Accept / Decline; the answer comes as the next message.",
        "A shell command other than the skill's own scripts or a read-only command, or a write outside the "
        "project, waits for the user's approval in the page: make such a call alone in its message, never in "
        "parallel with other calls.",
        f"Reply in {'French' if lang == 'fr' else 'English'} unless the user writes in another language.",
    ])


def clean_context(c) -> dict | None:
    """{"note": {"id", "number", "text"}, "view": true}: what the page sends with a message."""
    if not isinstance(c, dict):
        return None
    out = {}
    n = c.get("note")
    if isinstance(n, dict) and sl.NOTE_ID_RE.match(str(n.get("id", ""))):
        out["note"] = {"id": str(n["id"]), "number": n.get("number") if isinstance(n.get("number"), int) else None,
                       "text": str(n.get("text", ""))[:1000]}
    if c.get("view") is True:
        out["view"] = True
    return out or None


def context_lines(ctx: dict) -> list[str]:
    out = []
    if ctx.get("note"):
        n = ctx["note"]
        out.append(f"(About note {n.get('number') or ''} {n['id']}: \u201c{n['text']}\u201d.)")
    if ctx.get("view"):
        out.append("(Look at my current Studio view first: kiln-studio get_view_image.)")
    return out


class Worker:
    def __init__(self, project: sl.Project, emit=lambda ev: None, *, claude: str | None = None,
                 blender: Blender | None = None, auth_ttl: float = 60.0):
        self.project = project
        self.emit = emit
        self.claude = claude or os.environ.get("KILN_STUDIO_CLAUDE") or "claude"
        # One Blender per slot (claude_parallel); a test passes one fake for all.
        self._fake_blender = blender
        self.blenders: dict[int, Blender] = {}
        self.store = Store(project)
        self.jobs: dict[str, dict] = {}
        self.queue: deque[str] = deque()
        self.cv = threading.Condition()
        self.running: dict[int, dict] = {}      # slot -> its job
        self.rate: dict | None = None
        self._auth: tuple[float, dict] | None = None
        self.auth_ttl = auth_ttl
        self._threads: dict[int, threading.Thread] = {}
        self._stopping = False

    def blender_for(self, slot: int) -> Blender:
        if self._fake_blender is not None:
            return self._fake_blender
        if slot not in self.blenders:
            self.blenders[slot] = Blender(self.project, slot)
        return self.blenders[slot]

    @property
    def blender(self) -> Blender:
        return self.blender_for(0)

    # status
    def auth(self, force: bool = False) -> dict:
        account = user_settings()["account"]
        if force or not self._auth or time.time() - self._auth[0] > self.auth_ttl or self._auth[1].get("account") != account:
            self._auth = (time.time(), auth_status(self.claude, account=account))
        return self._auth[1]

    def view(self, job: dict) -> dict:
        out = {k: job.get(k) for k in ("id", "kind", "key", "asset", "request", "text", "state", "created",
                                       "started", "ended", "session", "cost_usd", "turns", "duration_ms",
                                       "stop_reason", "error", "waiting", "position")}
        if out["request"] and not out["asset"]:
            # A Create request's model, once kiln has named it.
            r = next((x for x in sl.load_requests(self.project) if x["id"] == out["request"]), None)
            out["asset"] = (r or {}).get("asset")
            out["brief"] = (r or {}).get("brief")
        return out

    def status(self, force_auth: bool = False) -> dict:
        st = self.project.settings()
        with self.cv:
            jobs = [self.view(self.jobs[j]) for j in list(self.jobs)[-30:]]
            queued = list(self.queue)
            running = [j["id"] for _, j in sorted(self.running.items())]
        for j in jobs:
            j["position"] = queued.index(j["id"]) + 1 if j["id"] in queued else None
        return {"enabled": st["claude_worker"], "port": st["blender_port"], "mcp": st["blender_mcp"],
                "approvals": st["claude_approvals"], "paid": st["claude_paid"], "blender_behind": st["blender_behind"], "model": st["claude_model"], "budget_usd": st["claude_budget_usd"],
                "parallel": st["claude_parallel"], "machine": machine(), "account": user_settings()["account"],
                "account_dir": str(account_dir()),
                "auth": self.auth(force_auth), "blender": self.blender.status(),
                "blenders": [self.blender_for(i).status() for i in sorted({0, *self.blenders})],
                "running": next(iter(running), None), "running_all": running,
                "jobs": jobs, "rate": self.rate, "usage": self.store.usage(),
                "api_key_in_env": bool(os.environ.get("ANTHROPIC_API_KEY"))}

    def thread(self, key: str) -> dict:
        key = self.store.canonical(key)
        with self.cv:
            jobs = [self.view(j) for j in self.jobs.values() if j["key"] == key]
        return {"key": key, "messages": self.store.thread(key), "session": self.store.session(key),
                "jobs": jobs[-10:]}

    def _changed(self, job: dict, entry: dict | None = None) -> None:
        self.emit({"type": "claude", "job": self.view(job), **({"entry": entry} if entry else {})})

    # submitting
    def submit(self, kind: str, *, asset: str | None = None, text: str = "", request: str | None = None,
               lang: str = "en", key: str | None = None, deferred: dict | None = None, context: dict | None = None) -> dict:
        if kind not in JOB_KINDS:
            raise ValueError(f"kind must be one of {', '.join(JOB_KINDS)}")
        if not self.project.settings()["claude_worker"]:
            raise ValueError("the Claude worker is off: turn it on in Settings → Claude")
        text = str(text or "").strip()
        if kind in ("chat", "answer") and not text:
            raise ValueError("a message needs text")
        if len(text) > 8000:
            raise ValueError("the message is too long (8,000 characters at most)")
        if kind == "notes" and not asset:
            raise ValueError("which model? (asset)")
        if kind == "create":
            r = next((x for x in sl.load_requests(self.project) if x["id"] == request), None)
            if not r:
                raise KeyError(f"no request {request}")
            text = r["command"].replace("/kiln ", "/blender-kiln:kiln ", 1)
        if kind == "notes":
            text = f"/blender-kiln:kiln studio {asset}"
        if kind == "setup":
            # Only a known part, never free text: the page names what to install.
            if text not in SETUP_PARTS:
                raise ValueError(f"which part? one of {', '.join(SETUP_PARTS)}")
            text = f"/blender-kiln:kiln setup {text}"
        # What goes with the words: the note the user picked, their view. Claude reads it ahead
        # of the message; the conversation shows it as tags, the user's words as they wrote them.
        ctx = clean_context(context)
        prompt = "\n".join([*context_lines(ctx), text]) if ctx else text
        job = {"prompt": prompt, "context": ctx, "id": sl.new_id("j"), "kind": kind, "asset": asset, "request": request,
               "key": self.store.canonical(key or thread_key(kind, asset, request)), "text": text, "lang": lang if lang in ("en", "fr") else "en",
               "state": "queued", "created": sl.now(), "deferred": deferred}
        with self.cv:
            busy = [j for j in self.jobs.values() if j["key"] == job["key"] and j["state"] in ("queued", "running")]
            if busy and kind != "resume":
                raise ValueError("Claude is already on this conversation: wait for it, or stop it")
            waiting = [j for j in self.jobs.values() if j["key"] == job["key"] and j["state"] == "waiting"]
            if kind != "resume" and any((j.get("waiting") or {}).get("type") == "tool" for j in waiting):
                raise ValueError("Claude is waiting for your approval of a tool call: allow or deny it first")
            for j in waiting:   # a proposal is answered by the next message
                j["state"], j["waiting"] = "done", {**j["waiting"], "answered": text[:200]}
            self.jobs[job["id"]] = job
            self.queue.append(job["id"])
            self.cv.notify_all()
            self._start_slots()
        if kind != "resume":
            entry = self.store.append(job["key"], {"job": job["id"], "role": "user", "kind": kind, "text": text,
                                                   **({"context": ctx} if ctx else {})})
        else:
            entry = None
        self._changed(job, entry)
        return self.view(job)

    def answer(self, job_id: str, decision: str, reason: str = "") -> dict:
        """The user's answer to a deferred tool call: allow or deny, then resume."""
        if decision not in ("allow", "deny"):
            raise ValueError("decision must be allow or deny")
        with self.cv:
            job = self.jobs.get(job_id)
        if not job:
            raise KeyError(f"no job {job_id}")
        w = job.get("waiting") or {}
        if job["state"] != "waiting" or w.get("type") != "tool":
            raise ValueError("this run is not waiting for an approval")
        d = self.decisions_dir()
        sl.write_json(d / f"{w['id']}.json", {"decision": decision, "reason": str(reason)[:500], "at": sl.now()})
        job["state"], job["waiting"] = "done", {**w, "answered": decision}
        entry = self.store.append(job["key"], {"job": job_id, "role": "approval-answer", "decision": decision,
                                               "tool": w.get("tool"), "id": w.get("id")})
        self._changed(job, entry)
        return self.submit("resume", asset=job["asset"], request=job["request"], key=job["key"],
                           lang=job.get("lang", "en"), deferred=w)

    def stop(self, job_id: str) -> dict:
        with self.cv:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError(f"no job {job_id}")
            if job["state"] == "queued":
                self.queue.remove(job_id)
                job["state"], job["ended"] = "stopped", sl.now()
                self._changed(job)
                return self.view(job)
            if job["state"] != "running":
                raise ValueError(f"this run is {job['state']}")
            job["stop_requested"] = True
            proc = job.get("_proc")
        if proc and proc.poll() is None:
            # SIGINT ends the turn the way Ctrl-C does; the session stays resumable.
            proc.send_signal(signal.SIGINT)
            threading.Timer(15, lambda: proc.poll() is None and proc.terminate()).start()
        return self.view(job)

    def shutdown(self) -> None:
        self._stopping = True
        with self.cv:
            self.cv.notify_all()
        with self.cv:
            procs = [j.get("_proc") for j in self.running.values()]
        for proc in procs:
            if proc and proc.poll() is None:
                proc.send_signal(signal.SIGINT)
        for b in ({self._fake_blender} if self._fake_blender is not None else set(self.blenders.values())):
            b.stop()

    def decisions_dir(self) -> Path:
        d = self.store.dir / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # running
    def _start_slots(self) -> None:
        """A thread per slot, up to claude_parallel (called with self.cv held)."""
        for slot in range(self.project.settings()["claude_parallel"]):
            t = self._threads.get(slot)
            if not t or not t.is_alive():
                self._threads[slot] = threading.Thread(target=self._loop, args=(slot,), daemon=True, name=f"claude-worker-{slot + 1}")
                self._threads[slot].start()

    def _next(self, slot: int) -> dict | None:
        """The first queued job this slot may take: never two runs on one conversation or one
        model at a time; a slot beyond claude_parallel (lowered since) takes nothing."""
        if slot >= self.project.settings()["claude_parallel"]:
            return None
        model = lambda j: j.get("asset") or (self.view(j)["asset"] if j.get("request") else None)
        busy_keys = {j["key"] for j in self.running.values()}
        busy_assets = {model(j) for j in self.running.values()} - {None}
        for jid in self.queue:
            j = self.jobs[jid]
            if j["key"] not in busy_keys and model(j) not in busy_assets:
                self.queue.remove(jid)
                return j
        return None

    def _loop(self, slot: int = 0) -> None:
        while not self._stopping:
            with self.cv:
                job = None
                while not self._stopping and (job := self._next(slot)) is None:
                    self.cv.wait(timeout=5)
                    if slot >= self.project.settings()["claude_parallel"] and not self.queue:
                        return
                if self._stopping or job is None:
                    return
                self.running[slot] = job
            try:
                self._run(job, slot)
            except WorkerError as e:
                self._fail(job, str(e))
            except Exception as e:  # never let the worker die
                self._fail(job, f"worker error: {e!r}")
            finally:
                with self.cv:
                    self.running.pop(slot, None)
                    job.pop("_proc", None)
                    self.cv.notify_all()

    def _fail(self, job: dict, msg: str) -> None:
        job["state"], job["error"], job["ended"] = "failed", msg, sl.now()
        self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "error", "text": msg}))

    def command(self, job: dict, session: dict | None, port: int | None = None) -> list[str]:
        st = self.project.settings()
        port = port or st["blender_port"]
        work = self.store.dir.parent / "cache" / "worker"
        work.mkdir(parents=True, exist_ok=True)
        mcp = work / f"mcp-{port}.json"
        sl.write_json(mcp, mcp_config(self.project, port, st["blender_mcp"]))
        settings = work / "settings.json"
        hook_cmd = f"{_q(sys.executable)} {_q(str(HOOK))}"
        sl.write_json(settings, {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [
            {"type": "command", "command": hook_cmd, "timeout": 30}]}]}})
        # Ask: the safe list passes, the rest waits for the user. Auto: Claude Code's auto mode
        # decides; the hook still holds back what can spend money (paid generation).
        mode = "auto" if st["claude_approvals"] == "auto" else "dontAsk"
        cmd = [self.claude, "-p"]
        cmd += ["--resume", session["id"]] if session and session.get("started") else ["--session-id", job["session"]]
        cmd += ["--plugin-dir", str(PLUGIN), "--mcp-config", str(mcp), "--strict-mcp-config",
                "--setting-sources", "project", "--settings", str(settings),
                "--permission-mode", mode, "--allowedTools", ",".join(ALLOWED),
                "--append-system-prompt", system_context(self.project, job, port, job.get("lang", "en")),
                "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
        if st["claude_model"]:
            cmd += ["--model", st["claude_model"]]
        if job.get("account") == "api_key":
            cmd += ["--max-budget-usd", str(st["claude_budget_usd"])]
        return cmd

    def _run(self, job: dict, slot: int = 0) -> None:
        if not self.project.settings()["claude_worker"]:
            raise WorkerError("the Claude worker is off: turn it on in Settings → Claude")
        job["state"], job["started"] = "running", sl.now()
        self._changed(job)
        auth = self.auth(force=True)
        if not auth["ok"]:
            raise WorkerError(f"Not running: {auth['message']}.")
        job["account"] = auth["account"]
        blender = self.blender_for(slot)
        how = blender.ensure()
        if how == "started":
            self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "system",
                                                              "text": f"Started Studio's Blender on port {blender.port}"}))
        session = self.store.session(job["key"])
        if session and session.get("started") and session.get("account", "subscription") != job["account"]:
            # Sessions live in the account's own Claude Code folder: another account cannot resume one.
            if job["kind"] == "resume":
                raise WorkerError("the account changed since Claude asked: send your answer as a message")
            self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "system",
                                                              "text": "New session: the Claude account changed since the last message"}))
            session = None
        if job["kind"] == "resume" and not (session and session.get("started")):
            raise WorkerError("no conversation to resume")
        job["session"] = session["id"] if session and session.get("started") else str(uuid.uuid4())
        if not (session and session.get("started")):
            self.store.set_session(job["key"], id=job["session"], started=False, account=job["account"])
        cmd = self.command(job, session, blender.port or self.project.settings()["blender_port"] + slot)
        env = dict(account_env(job["account"]), KILN_STUDIO_ROOT=str(self.project.root), KILN_PLUGIN_DIR=str(PLUGIN),
                   KILN_DECISIONS=str(self.decisions_dir()),
                   KILN_APPROVALS="auto" if self.project.settings()["claude_approvals"] == "auto" else "ask",
                   KILN_PAID="auto" if self.project.settings()["claude_paid"] == "auto" else "ask")
        err = (self.project.data / "cache" / "worker" / "claude.err").open("ab")
        t0 = time.time()
        proc = subprocess.Popen(cmd, cwd=str(self.project.root), env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1, start_new_session=True)
        with self.cv:
            job["_proc"] = proc
            # Stopped while it was starting (auth, Blender): stop() had no process to signal.
            if job.get("stop_requested"):
                proc.send_signal(signal.SIGINT)
        # The prompt goes on stdin; a resumed deferred call needs none.
        try:
            if job["kind"] != "resume":
                proc.stdin.write(job.get("prompt") or job["text"])
            proc.stdin.close()
        except BrokenPipeError:
            pass
        timer = threading.Timer(MAX_RUN_S, lambda: proc.poll() is None and proc.send_signal(signal.SIGINT))
        timer.start()
        result: dict = {}
        partial, last_emit = "", 0.0
        try:
            for line in proc.stdout:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                t = ev.get("type")
                if t == "system" and ev.get("subtype") == "init":
                    src = ev.get("apiKeySource")
                    want_key = job["account"] == "api_key"
                    if want_key and src != "ANTHROPIC_API_KEY":
                        proc.terminate()
                        raise WorkerError(f"Stopped: Claude Code was about to run on {src or 'another login'}, not your API key.")
                    if not want_key and src not in (None, "none"):
                        proc.terminate()
                        raise WorkerError(f"Stopped: Claude Code was about to use an API key ({src}), not your subscription.")
                    if ev.get("session_id"):
                        job["session"] = ev["session_id"]
                        self.store.set_session(job["key"], id=ev["session_id"], started=True, account=job["account"])
                elif t == "stream_event":
                    e = ev.get("event") or {}
                    if e.get("type") == "content_block_delta" and (e.get("delta") or {}).get("type") == "text_delta":
                        partial += e["delta"].get("text", "")
                        if time.time() - last_emit > 0.25:
                            last_emit = time.time()
                            self.emit({"type": "claude-text", "job": job["id"], "key": job["key"], "text": partial})
                    elif e.get("type") == "message_start":
                        partial = ""
                elif t == "assistant":
                    for b in (ev.get("message") or {}).get("content") or []:
                        if b.get("type") == "text" and b.get("text", "").strip():
                            self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "assistant", "text": b["text"]}))
                        elif b.get("type") == "tool_use":
                            self._changed(job, self.store.append(job["key"], {
                                "job": job["id"], "role": "tool", "tool": b.get("name"), "id": b.get("id"),
                                "input": short(b.get("input") or {}, 400)}))
                    partial = ""
                elif t == "user":
                    content = (ev.get("message") or {}).get("content")
                    for b in content if isinstance(content, list) else []:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            c = b.get("content")
                            text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                            self._changed(job, self.store.append(job["key"], {
                                "job": job["id"], "role": "tool-result", "id": b.get("tool_use_id"),
                                "error": bool(b.get("is_error")), "text": short(text, 300)}))
                elif t == "rate_limit_event":
                    # Claude Code says it during each run: the 5-hour session and the week, in
                    # unifiedWindows; the page shows the last word, and when it came.
                    self.rate = {**(ev.get("rate_limit_info") or {}), "at": sl.now()}
                elif t == "result":
                    result = ev
        finally:
            timer.cancel()
            try:
                proc.wait(30)
            except subprocess.TimeoutExpired:
                proc.kill()
            proc.stdout.close()
            err.close()
        job.update(ended=sl.now(), cost_usd=result.get("total_cost_usd"), turns=result.get("num_turns"),
                   duration_ms=result.get("duration_ms"), stop_reason=result.get("stop_reason"))
        self.store.usage({"at": sl.now(), "job": job["id"], "kind": job["kind"], "key": job["key"], "account": job["account"],
                          "cost_usd": result.get("total_cost_usd"), "turns": result.get("num_turns"),
                          "duration_ms": result.get("duration_ms"), "wall_s": round(time.time() - t0, 1),
                          "stop_reason": result.get("stop_reason")})
        if result.get("session_id"):
            self.store.set_session(job["key"], id=result["session_id"], started=True, account=job["account"])
        summary = {"job": job["id"], "role": "result", "cost_usd": result.get("total_cost_usd"),
                   "turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
                   "stop_reason": result.get("stop_reason")}
        if job.get("stop_requested"):
            job["state"] = "stopped"
            self._changed(job, self.store.append(job["key"], {**summary, "text": "Stopped."}))
            return
        if not result:
            raise WorkerError(f"claude exited ({proc.returncode}) without a result; see .kiln-studio/cache/worker/claude.err")
        if result.get("stop_reason") == "tool_deferred" and result.get("deferred_tool_use"):
            d = result["deferred_tool_use"]
            job["state"] = "waiting"
            job["waiting"] = {"type": "tool", "id": d.get("id"), "tool": d.get("name"), "input": short(d.get("input") or {}, 1500)}
            self.store.append(job["key"], summary)
            self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "approval", **job["waiting"]}))
            return
        if result.get("is_error"):
            raise WorkerError("Claude stopped on an error: " + short(result.get("result") or result.get("subtype") or "", 400))
        text = result.get("result") or ""
        q = next((ln.split(PROPOSAL, 1)[1].strip() for ln in reversed(text.splitlines()) if PROPOSAL in ln), None)
        if q:
            job["state"], job["waiting"] = "waiting", {"type": "proposal", "question": q}
            self.store.append(job["key"], summary)
            self._changed(job, self.store.append(job["key"], {"job": job["id"], "role": "proposal", "question": q}))
            return
        job["state"] = "done"
        self._changed(job, self.store.append(job["key"], summary))


def _q(s: str) -> str:
    import shlex
    return shlex.quote(s)
