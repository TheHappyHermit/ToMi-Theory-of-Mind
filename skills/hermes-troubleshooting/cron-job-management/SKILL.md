---
name: cron-job-management
description: "Manage cron jobs: model pin, scheduling, troubleshooting."
category: hermes-troubleshooting
created: 2026-08-07
---

# Cron Job Management

Use when creating, debugging, rescheduling, or auditing Hermes cron jobs. Covers model routing failures, config drift, backup verification, and diagnostics.

## Triggers

- Cron job fails or routes to wrong model
- Need to create or modify a scheduled job
- Config drift blocks job execution
- Verifying backup cron health
- Auditing schedules against model availability

## Model Routing Gotcha

The `cronjob` tool does not accept a `model` parameter on create or update. When `model: null` in `jobs.json`, the system activates a hardcoded OpenRouter fallback even if a local model is online.

### Fix: Pin model in jobs.json directly

```python
import json, pathlib
jobs = json.loads(pathlib.Path("~/.hermes/cron/jobs.json").expanduser().read_text())
for job in jobs:
    if job.get("prompt"):  # agent-based jobs only
        job["model"] = "qwen/qwen3.6-27b"
        job["enabled_toolsets"] = ["web", "terminal", "file", "delegation"]
pathlib.Path("~/.hermes/cron/jobs.json").expanduser().write_text(json.dumps(jobs, indent=2))
```

Always set `enabled_toolsets` alongside `model` to reduce token overhead.

### Verify pinning

```python
import json, pathlib
jobs = json.loads(pathlib.Path("~/.hermes/cron/jobs.json").expanduser().read_text())
for j in jobs:
    if j.get("prompt"):
        print(f"  {j['name']}: model={j.get('model', 'NULL')}")
```

## Schedule Alignment

Local model runs Mon-Fri 07:30-14:00 PT only. Jobs outside this window fail silently.

Examples: `30 7 * * 1-5` (7:30 AM), `0 13 * * 1-5` (1:00 PM).

## Config Drift Safety Guard

Jobs created under an old config can be blocked by a config drift check. Fix: delete and recreate the job so it inherits the current config baseline.

## Backup Verification

Daily backup cron writes to `~/backups/`. Check:

```bash
ls -lt ~/backups/ | head -5
```

Both `holographic_*.db` and `organizer_*.db` should appear.

## Emergency Backup Pruning

State.db emergency backups at `~/.hermes/state.db.pre-update-emergency-*.bak` (~34 MB each). Keep only the latest:

```bash
ls -t ~/.hermes/state.db.pre-update-emergency-*.bak | tail -n +2 | xargs rm
```

## Memory Vacuum Safety

Session vacuum/prune only affects `state.db` (conversation history, 90-day retention). Never touches holographic.db, fact_store.db, or organizer.db. These are separate databases with their own daily backup cron.

## Diagnostic Checklist

1. Job not running? Check schedule vs model availability window
2. Wrong model? Check jobs.json for null model and pin explicitly
3. Config drift error? Delete and recreate the job
4. Tool timeout? Split large payloads into smaller calls
5. Backup missing? Check `~/backups/`
6. Script-only job silent? Empty stdout means no delivery

## Pitfall: Profile Fix vs Credential Problem — Don't Conflate Them

After fixing a cron job's profile reference (e.g., correcting `profile: online-lane-a` → `profile: google-researcher`), the job may STILL fail with errors that look identical to before. This is NOT evidence the fix was reverted. Two distinct failure modes produce similar output:

| Symptom after profile fix | What it means | How to verify |
|---|---|---|
| Error references the NEW provider (e.g., "Upstream error from Nvidia" after fixing to google-researcher) | Profile fix took effect; now hitting the provider's own failure (missing key → fallback chain) | `grep` the error for provider names; check `auth.json` `last_status` |
| Error still says skill/profile not found | Profile fix was NOT applied or was reverted | Check `jobs.json` profile field directly |
| "provider rate limit" / "fallback chain exhausted" | Profile is correct; primary provider has no key, fallback exhausted | Check `.env` for the provider's key env var; check `auth.json` for `"exhausted"` status |

**Rule**: After any profile config change, verify TWO things independently:
1. The profile reference in `jobs.json` is correct (read the file, don't trust the error message)
2. The credential supply chain for THAT profile is intact (check `.env`, `auth.json`, provider block)

A profile fix that "doesn't work" is usually a credential problem wearing the profile fix's clothes.

### How to tell if a fix was reverted

```bash
# Read the CURRENT state of jobs.json — don't trust cron error messages
python3 -c "
import json
with open('/home/{USER}/.hermes/cron/jobs.json') as f:
    data = json.load(f)
for job in data['jobs']:
    if 'Online' in job.get('name','') or 'Lane' in job.get('name',''):
        print(f\"{job['name']}: profile={job.get('profile')}\")
"
```

If the profile field shows the corrected value (`google-researcher`, not `online-lane-a`), the fix stuck. Any subsequent failure is a DIFFERENT problem — usually credentials.

### Credential supply chain after profile fix

Once the profile is confirmed correct, check if that profile can actually authenticate:

```bash
# 1. Does the profile have an explicit provider block?
grep -A 10 "^providers:" ~/.hermes/profiles/<profile>/config.yaml | grep -A 5 "gemini:"

# 2. Is the expected env var in .env?
grep -E "^GOOGLE_API_KEY|^GEMINI_API_KEY" ~/.hermes/.env ~/.hermes/profiles/<profile>/.env 2>/dev/null

# 3. What does auth.json say about this provider's credential health?
python3 -c "
import json
with open('/home/{USER}/.hermes/auth.json') as f:
    auth = json.load(f)
for pool, creds in auth.get('credential_pool', {}).items():
    for c in creds:
        if 'gemini' in pool.lower() or 'google' in pool.lower():
            print(f'{pool}: status={c.get(\"last_status\")} source={c.get(\"source\")}')
            if c.get('last_error_message'):
                print(f'  error: {c[\"last_error_message\"][:200]}')
"
```

**Critical**: `last_status: "exhausted"` means the key IS configured and WAS working — it's a quota/billing problem, NOT a missing credential. Do not waste time hunting for the key.

### Snapshot-based verification of what changed

When a fix appears not to have stuck, compare the current config against pre-change snapshots:

```bash
# Find the most recent pre-update snapshot
ls -lt ~/.hermes/state-snapshots/*/cron/jobs.json 2>/dev/null | head -3

# Compare current vs snapshot
diff <(python3 -c "import json; print(json.dumps(json.load(open('/home/{USER}/.hermes/cron/jobs.json')), indent=2))") \
     <(python3 -c "import json; print(json.dumps(json.load(open('~/.hermes/state-snapshots/<ts>-pre-update/cron/jobs.json')), indent=2))")
```

This tells you exactly what changed and whether your fix is still in place.