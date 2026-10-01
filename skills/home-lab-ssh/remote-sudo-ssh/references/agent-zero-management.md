# Agent Zero Management (<LAN-HOST-IP>)

## SSH

- Key: `~/.ssh/id_ed25519_agent` (ED25519, deployed 2026-09-13)
- Login: `ssh agent-zero` (config block in `~/.ssh/config`)
- Password fallback: paramiko with `{SSH_PASSWORD}` when key is unavailable
- Sudo: still password-required, needs PTY+submit dance — no NOPASSWD entry

## Container

- Name: `agent-zero`
- Image: `agent0ai/agent-zero:latest` (old tag `d8fd86114b02`, 12.4GB — see Docker update note below)
- Data mount: `$HOME/agent-zero/agent-zero/usr` → `/a0/usr` (bind mount, 115MB)
- Port: `50080→80` (container port 80, host port 50080)
- Other ports: `22/tcp`, `9000-9009/tcp` (internal services)
- Restart policy: none (does not auto-restart on failure)
- Version: v2.12-16-g8426c137 (updated via self-update 2026-09-13)

## Data Layout (`$HOME/agent-zero/agent-zero/usr/`)

| Path | Contents |
|---|---|
| `settings.json` | Agent Zero settings: version, workdir config, MCP/A2A, searxng/n8n vars |
| `secrets.env` | API keys (Tavily, FreshRSS, GitHub, n8n, Alpha Vantage, Finnhub, FRED) |
| `.env` | Runtime env: API keys for all providers, ROOT_PASSWORD, ALLOWED_ORIGINS, tz |
| `chats/` | 34 chat sessions |
| `plugins/` | 13 plugins (playwright_cli, agent_harness, bmad_method, google, _oauth, _telegram_integration, _whisper_stt, etc.) |
| `agents/` | Agent profiles (developer, dragon_os_agent, osint_agent) + profiles.json |
| `knowledge/` | Knowledge base fragments |
| `obsidian_vault/` | 5.8MB obsidian vault |
| `workdir/` | 7.6MB workspace |
| `memory/`, `projects/`, `prompt_profiles/`, `scheduler/`, `shared/`, `skills/`, `uploads/` | Supporting dirs |

**Root-owned files that `<username>` cannot back up without sudo:** SDR/radio KB files in `shared/knowledge_base/`, `obsidian_vault/`, `projects/knowledge_base/`, `workdir/` subdirectories, and `plugins/google/data`. These are the DragonOS agent-zero radio/SDR/hacking knowledge base. Manual backup with `--ignore-failed-read` skips them.

## Update Procedure

**Use the self-update mechanism.** Do NOT use `docker pull` — it hangs on layer download (writes "Pulling fs layer" to log but makes no progress, likely Docker Hub throttling on this connection).

### Step 1: Queue the update inside the container

```bash
ssh agent-zero "docker exec agent-zero /opt/venv-a0/bin/python /exe/self_update_manager.py trigger-update ready latest"
```

Or the shell wrapper:

```bash
ssh agent-zero "docker exec agent-zero /exe/trigger_self_update.sh ready latest"
```

This writes `/exe/a0-self-update.yaml` and prints "Queued Agent Zero self-update for the next startup attempt."

### Step 2: Restart the container

```bash
ssh agent-zero "docker restart agent-zero"
```

On restart, the self-update manager (`/exe/self_update_manager.py docker-run-ui`) runs and:

1. Cleans uv cache
2. Stashes local changes (`git -C /a0 stash push --include-untracked`)
3. Creates a backup of `/a0/usr` to `/root/update-backups/usr-<timestamp>.zip`
4. Fetches latest from `https://github.com/agent0ai/agent-zero.git` (branch `ready`, tags)
5. Resolves `latest` tag to a commit
6. Checks out the new code (`git checkout -B ready`)
7. Runs `git clean -ffd`
8. Runs `prepare.py --dockerized=true` (installs dependencies like json-repair, patchright)
9. Starts the UI
10. Drops the stash on success

### Step 3: Verify

```bash
# Container is up
ssh agent-zero "docker ps --filter name=agent-zero --format '{{.Names}} {{.Status}}'"

# Web UI responds
ssh agent-zero "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://localhost:50080/"

# New version
ssh agent-zero "docker exec agent-zero bash -c 'cd /a0 && git log --oneline -1'"
```

### Rollback

The self-update manager keeps a stash during the update. If the update fails, it should restore. The backup zip at `/root/update-backups/` can be manually extracted to `/a0/usr` if needed.

## Docker Image Update (separate from self-update)

The self-update updates the CODE inside the container but NOT the Docker image tag. The container still runs from the old `d8fd86114b02` image. To update the image persistently (so a `docker rm` + `docker run` would use the new version):

1. Pull the new image — **WARNING: `docker pull agent0ai/agent-zero:latest` hangs** on this server (stuck at "Pulling fs layer" for 10+ minutes, likely Docker Hub throttling on this connection). This is a Docker Hub throttling issue on this connection, not a code problem.
2. If pull ever works: stop container, then `docker run` with the same mounts and port mapping as the original.

For now, the self-update mechanism is the working update path.

## Troubleshooting

### Container exited (like it did 2 weeks ago)

The container exited 2026-08-29 after ~7 weeks of uptime. Logs showed Telegram bot hitting API rate limits (Flood control on GetUpdates) — not OOM (OOMKilled=false, ExitCode=255). Restarting with `docker start agent-zero` brings it back.

### Port 50080 not responding immediately after restart

The Flask/uvicorn server inside the container needs ~30 seconds to start after `docker start`. Wait before checking HTTP. First check may return 000 — retry after 30s.

### Lighttpd on port 80

lighttpd runs on the HOST (not in Docker) serving a static default page on port 80. This is separate from Agent Zero's port 50080. Do not confuse the two.

### Permission denied on backup

Files owned by root inside the bind mount cannot be read by `<username>` for tar backup. Use `tar --ignore-failed-read` for a partial backup, or use `docker exec` to run tar inside the container where root access is available.
