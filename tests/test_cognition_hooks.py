#!/usr/bin/env python3
"""Prove the two cognition hooks work end to end, offline.

Runs against a stub brain API so nothing depends on the dashboard being
up, and asserts the behaviours that matter:
  1. brain-cognitive-prep fires only on agent:start, not agent:end.
  2. It posts the stimulus BEFORE the action-check (ordering matters:
     the gate reads the thalamic buffer).
  3. The verdict is written and readable by the consolidator.
  4. The consolidator SKIPS the duplicate stimulus when that state exists.
  5. Both fail open (return cleanly) when the brain is unreachable.
  6. A NO_GO verdict produces a real `{"decision": "deny", ...}` return
     from the guard, not an `advisory` key.
"""
import importlib.util
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = "/home/operator/hermes-brain"
HOOKS = os.path.join(REPO, "hooks")
sys.path.insert(0, HOOKS)

CALLS = []


class Stub(BaseHTTPRequestHandler):
    def _read(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_POST(self):
        CALLS.append((self.path, self._read()))
        body = json.dumps({
            "decision": "NO_GO",
            "rationale": "stub rationale",
            "somatic_warning": "elevated cortisol",
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["BRAIN_API_URL"] = f"http://127.0.0.1:{port}"

    import brain_cognitive_prep.state as state
    # Redirect the real constant BEFORE loading the handlers, so the
    # `from ... import write_state` binding inside them resolves to the
    # temp dir. Patching state.STATE_DIR after import would not: the
    # function closes over the module global and would still write to
    # ~/.hermes. Point HOME itself at the sandbox as a second guard.
    os.makedirs("/tmp/brain_cog_test", exist_ok=True)
    os.environ["HOME"] = "/tmp/brain_cog_test_home"
    os.makedirs(os.environ["HOME"], exist_ok=True)
    state.STATE_DIR = "/tmp/brain_cog_test"

    prep = load(os.path.join(HOOKS, "brain-cognitive-prep", "handler.py"), "prep")
    cons = load(os.path.join(HOOKS, "brain-memory-consolidator", "handler.py"), "cons")
    guard = load(os.path.join(HOOKS, "brain-cognitive-guard", "handler.py"), "guard")

    fails = []

    def check(label, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        if not cond:
            fails.append(label)

    ctx = {"session_id": "sess1", "message": "delete prod db",
           "platform": "telegram", "tools_called": [], "response": ""}

    # 1 + 2: fires on agent:start, stimulus before action-check
    CALLS.clear()
    prep.handle("agent:start", ctx)
    paths = [p for p, _ in CALLS]
    check("posts stimulus on agent:start", "/api/brain/stimulus" in paths)
    check("calls action-check", "/api/brain/action-check" in paths)
    check("stimulus precedes action-check",
          paths.index("/api/brain/stimulus") < paths.index("/api/brain/action-check"))

    # 3: verdict persisted
    st = state.read_state("sess1")
    check("verdict persisted", st is not None)
    check("verdict records NO_GO", st and st.get("decision") == "NO_GO")

    # 4: consolidator skips the duplicate stimulus
    CALLS.clear()
    cons.handle("agent:end", ctx)
    paths = [p for p, _ in CALLS]
    check("consolidator does NOT repost stimulus", "/api/brain/stimulus" not in paths)

    # 4b: with no cached state it must still post (fail-open direction)
    for f in os.listdir("/tmp/brain_cog_test"):
        os.unlink(os.path.join("/tmp/brain_cog_test", f))
    CALLS.clear()
    cons.handle("agent:end", ctx)
    paths = [p for p, _ in CALLS]
    check("consolidator posts stimulus when no cache", "/api/brain/stimulus" in paths)

    # 1b: prep ignores non-agent:start events
    CALLS.clear()
    prep.handle("agent:end", ctx)
    check("prep ignores agent:end", len(CALLS) == 0)

    # 6: guard returns a real deny decision
    out = guard.handle("agent:step", {"tool_name": "terminal",
                                      "tool_args": {"command": "rm -rf /"}})
    check("guard returns decision key", isinstance(out, dict) and "decision" in out)
    check("guard does NOT return advisory", not (isinstance(out, dict) and "advisory" in out))
    check("guard does NOT return halt", not (isinstance(out, dict) and "halt" in out))
    if isinstance(out, dict):
        check("guard decision is deny", out.get("decision") == "deny")
        check("guard carries a message", bool(out.get("message")))

    # 5: fail open with BOTH transports down. A dead HTTP port is not
    # enough: the brain loads in-process, so the gate legitimately
    # succeeds with the dashboard offline. To reach the unavailable path,
    # brain/ must be unimportable AND the HTTP endpoint must be gone --
    # the stub server is still live, so pointing BRAIN_API_URL at a
    # refused port is what actually cuts HTTP.
    poison = "/tmp/brain_cog_poison"
    os.makedirs(os.path.join(poison, "brain"), exist_ok=True)
    with open(os.path.join(poison, "brain", "__init__.py"), "w") as fh:
        fh.write("raise ImportError('brain disabled for test')\n")

    # Bind a port, learn its number, then close it. Connecting to it now
    # gives ECONNREFUSED, which is a genuinely dead endpoint rather than
    # the still-running stub.
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    dead_port = probe.getsockname()[1]
    probe.close()
    os.environ["BRAIN_API_URL"] = f"http://127.0.0.1:{dead_port}"

    saved_path = sys.path[:]
    saved_modules = {k: v for k, v in sys.modules.items()
                     if k == "brain" or k.startswith("brain.")}
    for k in saved_modules:
        del sys.modules[k]
    sys.path.insert(0, poison)
    try:
        prep.handle("agent:start", ctx)
        cons.handle("agent:end", ctx)
        guard.handle("agent:step", {"tool_name": "terminal", "tool_args": "x"})
        check("all three hooks survive a dead brain", True)
    except Exception as e:
        check(f"all three hooks survive a dead brain ({e})", False)
    finally:
        sys.path = saved_path
        for k in [m for m in sys.modules
                  if m == "brain" or m.startswith("brain.")]:
            del sys.modules[k]
        sys.modules.update(saved_modules)
        import shutil
        shutil.rmtree(poison, ignore_errors=True)

    # The verdict must still be written, and must say the gate genuinely
    # could not run, so the post-turn path can tell "the gate ran and
    # said GO" apart from "the gate never ran".
    st = state.read_state("sess1")
    check("records brain_reachable=False when both transports are down",
          st is not None and st.get("brain_reachable") is False)
    check("records gate_via=unavailable",
          st is not None and st.get("gate_via") == "unavailable")

    # 7: the in-process path must work with HTTP dead -- the brain is a
    # stdlib library and does not need the dashboard. Asserting this
    # guards against regressing to HTTP-only, which would report a
    # healthy brain as dead whenever the dashboard is down.
    for f in os.listdir("/tmp/brain_cog_test"):
        os.unlink(os.path.join("/tmp/brain_cog_test", f))
    os.environ["BRAIN_API_URL"] = "http://127.0.0.1:1"
    sys.path.insert(0, REPO)
    prep.handle("agent:start", ctx)
    st2 = state.read_state("sess1")
    check("in-process gate works with the dashboard down",
          st2 is not None and st2.get("gate_via") == "in-process")
    check("in-process verdict is a real decision",
          st2 is not None and st2.get("decision") in
          ("GO", "NO_GO", "HYPERDIRECT_BRAKE"))
    check("in-process verdict carries a rationale",
          st2 is not None and bool(st2.get("rationale")))

    srv.shutdown()
    import shutil
    shutil.rmtree("/tmp/brain_cog_test", ignore_errors=True)
    shutil.rmtree("/tmp/brain_cog_test_home", ignore_errors=True)
    print(f"\n  {'ALL PASS' if not fails else str(len(fails)) + ' FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
