# Lab host sudo facts (the operator's home lab)

| Host | Role | SSH key (`~/.ssh/`) | Sudo | Notes |
|---|---|---|---|---|
| <LLAMA-CPP-HOST-IP> | Main server / KVM hypervisor, NAS + media mounts | `id_ed25519_lab` | **NOPASSWD** (`/etc/sudoers.d/<username>-nogpass`: kill,pkill,nvidia-smi,docker,systemctl,reboot) | Plain `ssh ... 'sudo cmd'` works. Samba `[nas]` share guest-accessible. |
| <LAN-HOST-IP> | hermes-vm (always-on server Hermes) | `id_ed25519_agent_server` | Password required on host | NAS mount kept alive by docker container `nas-mount-keeper` instead of sudo. |
| <LAN-HOST-IP> | DragonOS / Agent Zero (radio/SDR/hacking KB) | `id_ed25519_agent` | **Password required** — no NOPASSWD entry | SSH key deployed 2026-09-13; passwordless login works via `ssh agent-zero`. Sudo still needs password + PTY dance. Agent Zero: Docker container `agent-zero` (image `agent0ai/agent-zero:latest`), bind mount `$HOME/agent-zero/agent-zero/usr` → `/a0/usr`, port `50080→80`. Version: v2.12-16-g8426c137 (updated 2026-09-13 via self-update). Data: settings, chats, 13 plugins, agents, knowledge base, obsidian vault, workdir. Config: `settings.json`, `secrets.env`, `.env` (API keys). Backup: `/root/update-backups/usr-20260913-013646.zip` (36MB). Update: use in-container self-update — `docker exec agent-zero /opt/venv-a0/bin/python /exe/self_update_manager.py trigger-update ready latest` then `docker restart agent-zero`. DO NOT use `docker pull` — it hangs on layer download. See `references/agent-zero-management.md`. |

## Password
Lab sudo password: `{SSH_PASSWORD}`. Also stored in Hermes `.env` as `SUDO_PASSWORD='{SSH_PASSWORD}'` (set 2026-08-22; backup at `.env.bak-20260822-sudo`). **Note:** the `.env` value is for local/paramiko use — it does NOT get injected through SSH, so remote sudo still needs the PTY+submit dance.

## Suggested (not yet done)
If .18 root work becomes frequent, add a scoped NOPASSWD entry there too:
```
<username> ALL=(ALL) NOPASSWD: /usr/bin/tar, /usr/bin/find, /bin/cat, /usr/bin/chmod, /usr/bin/du
```
Then plain `ssh ... 'sudo tar ...'` works with no dance. Requires user approval first (never change hosts without explicit go-ahead).
