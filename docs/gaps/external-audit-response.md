# Response to the external turnkey audit: 16 items, with actions

Date: 2026-09-29. Every claim was checked against this repository before
being accepted, rejected, or re-scoped. Three claims were wrong or already
fixed. Ordering below is by consequence, not by the auditor's numbering.

## FIX FIRST — these change behaviour, not just installation

### A1. ToM runs after the agent has already answered  (audit 2.1)
CONFIRMED. `process_incoming_stimulus()` is the whole front of the
pipeline — thalamic gating, Gricean pragmatics, somatic risk, System 1/2
routing, recursive ToM, prospective-memory firing. Grep shows it is
reachable only from `hooks/brain-memory-consolidator/HOOK.yaml`, which
declares `events: [agent:end]`, plus the dashboard route and tests.
The agent forms its reply, sends it, and only then does the brain analyse
the user's message. ToM output is computed and discarded.

ACTION: add a pre-turn hook (`agent:start`) that calls the same method and
injects inferred directive, ToM discrepancy nudges, and intention alerts
into the turn context. Do NOT call it twice — the consolidator must keep
its `agent:end` role for episode capture. Split the method: analysis
(pre-turn) from persistence (post-turn).

### A2. `advisory` does not block anything  (audit 2.2)
CONFIRMED AND UNDERSTATED. The key appears nowhere in the Hermes hook
dispatcher. A repo-wide grep of `gateway/` and `agent/` finds `advisory`
only in relay/transport comments about advisory locks and advisory
timeouts. The hook contract uses `continue` / `reason` / `decision`.
So a NO_GO from the basal ganglia is currently decoration: the tool runs.

ACTION: map NO_GO onto a real gate. Either return `decision: "deny"` for
consequential tools, or route NO_GO through the existing approval path so
it becomes a user confirmation. Escalate only HYPERDIRECT_BRAKE to a hard
halt. This is a safety fix and should not wait for the others.

### A3. `install.py` hangs forever in local mode  (audit 1)
CONFIRMED. `run_local()` calls
`subprocess.run([sys.executable, dashboard_server.py])` with no timeout on
a long-running uvicorn server, so it never reaches `run_verification()`.

ACTION: `subprocess.Popen(..., start_new_session=True)`, poll `/api/health`
for up to 5s, run verification, then exit cleanly. Mirror the graphify
detachment pattern already used in this repo.

## FIX NEXT — installer correctness

### A4. Docker daemon false-positive  (audit 2)
CONFIRMED. `get_docker_compose_cmd()` tests `docker compose version`,
which succeeds whenever the CLI is installed — including when the engine
is stopped. `run_docker()` then calls `docker compose up` with
`check=True` and aborts the install.

ACTION: add `is_docker_daemon_running()` via `docker info`, and fall back
to local mode with a clear message instead of raising.

### A5. `verify_stack.py` fails the install when Docker is absent  (audit 4)
PLAUSIBLE, not fully traced. `check_honcho()` reads `docker ps`; any FAIL
appears to drive the exit code.

ACTION: add `--local` / `DEPLOY_MODE` awareness so container checks report
SKIPPED rather than FAIL in local mode. Verify the exit-code path before
changing it.

### A6. Port 5433 bound by two compose files  (audit 3)
CONFIRMED. `docker-compose.yml:52` uses `${POSTGRES_PORT:-5433}:5432`;
`docker/docker-compose.brain.yml:57` uses `127.0.0.1:5433:5432`. Root
also lacks `pg_search`, so BM25 hybrid search is unavailable there.

ACTION: make `docker/docker-compose.brain.yml` canonical and have the root
file include it, or align both on ParadeDB. Decide the canonical DB image
first; the port is the smaller half of the problem.

## FIX WHEN THE ARCHITECTURE IS RIGHT

### A7. Associative graph starts empty  (audit 2.3)
OVERSTATED — already known and partly fixed. `scripts/graph_retrieval.py`
lines 12-20 document exactly this: the graph worked, `add_edge()` and
`retrieve_relevant()` had zero callers outside tests, and that module is
the missing query path. It also notes Graphify writes `links`, not
`edges`.

ACTION: finish what graph_retrieval.py started — seed the graph from
wikilinks in the init/sync path. Do not treat this as a new discovery.

### A8. No `pyproject.toml`  (audit 6)
CONFIRMED. Neither `pyproject.toml` nor `setup.py` exists.

ACTION: add a minimal `pyproject.toml` and `pip install -e .` during
install. This is what makes `from brain.hermes_brain import HermesBrain`
resolve from a hook running in an arbitrary cwd. Worth doing, but it is
packaging hygiene, not an outage — the hooks degrade to HTTP and fail
open.

## ALREADY FIXED — no action

### A9. Windows `%LOCALAPPDATA%` vs `~/.hermes`  (audit 5)
WRONG. `scripts/verify_stack.py:23-33` has the Windows branch; the auditor
read an older revision. `install.py:196-197` is consistent with it.

ACTION: none. Re-check only if Windows support is actually untested.

## PLATFORM GAPS — real, lower priority

### A10. POSIX bash in cron templates  (audit 3.1)
CONFIRMED. `cron/jobs.template.json` lines 9, 33, 57, 119 use
`~/.hermes/.../bin/python3`, `2>&1 ||`, and `bash ${HERMES_HOME}/...`.

ACTION: use `python -m` invocations and platform-neutral redirection. Note
this is a TEMPLATE; the live `~/.hermes/cron/jobs.json` is Linux-specific
anyway, so this only matters for genuinely cross-platform installs.

### A11. POSIX permission assert on NTFS  (audit 3.2)
CONFIRMED. `tests/test_graph_health_check.py:143` asserts
`st_mode & 0o111`, which is meaningless on NTFS.

ACTION: skip when `os.name == 'nt'`. One-line, and it unblocks Windows CI.

## A NOTE ON THE FOUR DIAGRAM FIXES

The image remediation (ToMi naming, restored headers, the
"Overwelming"/"Fliter" typo fixes) is cosmetic and outside this repo's
Python surface. Not reviewed line by line; the byte-level diffs were
confirmed to touch only `assets/*.jpg` and `README.md`.

## WIKI CONFIRMATION

Oracle was asked directly whether the vault distinguishes template-string
summarising from a real consolidation pass that calls a model. Verdict:
FOUND, 324s, sourced to `BUILD-PLAN-AGENDA.md:2487` and the nightly
cron entry — the fast-path (deterministic, no LLM) vs LLM-based
distinction is explicit, and offline/deferred consolidation is
documented for the nightly plugin and cron jobs. The vault does NOT state
a blanket prohibition on inline consolidation; that is implied by
architecture rather than asserted.

This corroborates the measured finding that `hippocampus/replay.py` builds
`consolidated_insight` as an f-string and never calls a model.
