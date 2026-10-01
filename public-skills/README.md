# public-skills

PII-stripped copies of the skills in `~/.hermes/skills`, published to GitHub.

**These files are generated. Do not edit them by hand.**

The live skills under `~/.hermes/skills` carry host-specific detail — LAN
addresses, real service and project names, the author's handle — because that
is what makes them useful on this machine. Publishing those verbatim would
leak the private deployment. So the rule is:

> **Local keeps the detail. Published gets the method.**

Every file here is the redacted variant of a live skill. The technical
instructions survive intact; only the identifying values are substituted with
placeholders (`{USER}`, `{LAN_IP}`, `{SSH_KEY}`, `{SERVICE}`), so a
published command stays runnable in shape even though it no longer names a
real host.

## Why a separate folder

Three things made `skills/` unusable as the publish target:

1. The category directories (`skills/research/`, `skills/devops/`, …) are
   gitignored wholesale as upstream-vendored. A skill created in a category
   directory is invisible to a fresh clone — which is how `wiki-cognition`
   went missing once already.
2. `~/.hermes/skills` is not itself a git repo.
3. A flat, never-ignored folder admits exactly one rule: *if it is here, it
   has been redacted.*

Nine of the skills here also exist under `skills/` from the first sweep, before
this folder existed. Those copies are still tracked and identical; the
`public-skills/` copies are canonical going forward.

## Keeping it in sync

```bash
# regenerate the redacted copies
scripts/sync_skills_to_repo.py

# verify nothing has drifted; exits non-zero if any published copy is stale
scripts/sync_skills_to_repo.py --check
```

Run `--check` in CI. It compares a fingerprint of each live `SKILL.md` against
the `.source-fingerprint` written at publish time, so an edited local skill
that was never republished is caught rather than silently shipped.

**Any time a skill is created or edited, re-run the sync and commit the
result.** That is the whole maintenance rule.

## How the redaction is enforced

`scripts/redact_skill.py` is the only thing that writes here. It is
deliberately fail-closed: it re-scans its own output for every PII class it
knows about, and **refuses to write** if anything survives. A publish run that
hits a refusal exits non-zero and leaves the file unwritten — a partially
scrubbed file can never reach the repo.

Substitute, never delete. A redacted skill that no longer works on a real host
is worse than one that was never published, so placeholders stand in for
values rather than the instruction being cut.

### Failures this design has already caught

Each of these got past a first version and is now pinned in
`tests/test_redact_skill.py`:

- **Rule ordering mangled a path.** The handle rule ran before the home-path
  rule, so `/home/operator` became `/home/the-author` — no PII left, but an
  obviously broken path that the residue check passed.
- **A size filter was treated as an identifier.** `awk '$1>100000000'` is nine
  digits, the same length as a Telegram ID, so the numeric rule rewrote it to
  `awk '$1>{ID}'` — a command that does not run. Digit count cannot separate
  the two; context does.
- **The residue check rejected its own correct output.** Tightening a rule
  without loosening the matching residue pattern produced a false refusal on
  an already-clean file.
- **The public commit identity was redacted.** The noreply exception tested
  for a domain starting with `noreply`, but the real address is
  `…@users.noreply.github.com` — the subdomain is `users.noreply`.
- **An environment survived in a filename.** `id_ed25519_lab` and
  `ssh the operator@host` name the deployment even with the address itself replaced.
- **A project name survived inside a compound filename.**
  `check_autognosia_dbs.py` — the surrounding underscores mean a
  word-delimited pattern never fires.

That last one is why the audit below is a *separate* script with different
patterns from the redactor's own. A check that shares the implementation's
assumptions cannot catch the implementation's blind spots.

## Verifying a publish

```bash
python3 scripts/sync_skills_to_repo.py --check
```

Independent of that, before pushing:

```bash
grep -rInE 'operator|10\.[0-9]+\.[0-9]+\.[0-9]+|id_(rsa|ed25519)' public-skills/
```

Expected: no output.
