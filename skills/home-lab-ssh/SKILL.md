---
name: home-lab-ssh
description: SSH into the operator's home lab servers for management tasks.
---

## Home Lab Servers

### Desktop ({LAN_IP}) — Windows 11 Pro

- **Also called:** Desktop, Windows host
- **Username:** `operator`
- **OS:** Windows 11 Pro (accessed via SSH to the Windows sshd)
- **Hostname:** Desktop
- **SSH key:** `~/.ssh/id_rsa` (RSA key auth works — `{USER}@{LAN_IP}`)
- **GPU:** RTX 3090 (24GB) + {IGPU} (16GB)
- **Inference endpoints (Docker Desktop containers, NOT visible from WSL):**
  - Port 8080 — `qwen35-9b-mtp` (Qwen3.5-9B, llama.cpp server, on {IGPU})
  - Port 18020 — `qwen38-27b-rtx3090-single-1` (Qwen3.8-27B, vLLM server, on RTX 3090, requires API key `VLLM_API_KEY`)
- **Known gotcha:** This is the execution host for Windows-side Docker (Docker Desktop / WSL integration). The WSL instance on the agent server ({LAN_IP}) CANNOT see these containers — they run in a separate Docker Desktop daemon.
- **SSH command format:** `ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command"`

**Check GPU usage from the desktop:**
```bash
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no {USER}@{LAN_IP} "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
```

**Check if inference endpoints are being hit (logs):**
```bash
# Check for POST requests (actual inference) in container logs
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no {USER}@{LAN_IP} "docker logs qwen35-9b-mtp 2>&1 | grep -i 'POST' | tail -10"
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no {USER}@{LAN_IP} "docker logs qwen38-27b-rtx3090-single-1 2>&1 | grep -i 'POST' | tail -10"
```

### Main Server ({LAN_IP})

- **Username:** {USER}
- **OS:** Ubuntu 24.04
- **Hostname:** Server
- **SSH key:** `~/.ssh/{SSH_KEY}`
- **Network topology:**
  - `enp195s0` — physical 2.5 Gigabit Ethernet, link up, 2500 Mb/s, member of `bridge0`
  - `bridge0` — Linux bridge: enp195s0 + vnet0–vnet3 (VMs)
  - `wlp194s0` — WiFi adapter, operstate **down** (not active)
  - Default route via `{LAN_IP} dev bridge0` (router)
  - IP: {LAN_IP}/24 (dynamic, on bridge0)

### Agent Server ({LAN_IP})

- **Also called:** Agent server
- **Username:** {USER}
- **OS:** Ubuntu 24.04
- **SSH key:** `~/.ssh/{SSH_KEY}`
- **Role:** Runs Hermes agent, Paperclip, Honcho services, default-api, meilisearch, qdrant, redis, postgres
- **Disk:** 158GB total, ~26GB free (83% used) after cleanup
- **Execution context note:** This is the **execution host** for all tool calls when the desktop app SSH-tunnels in. The desktop GUI runs on a separate Windows machine; tool calls that return `hostname HermesAgent` or `ip {LAN_IP}` are running here, not on the desktop. See `hermes-troubleshooting` → "Diagnosing Your Execution Context" for details.

### Agent Zero / Radio Server ({LAN_IP})

- **Also called:** Agent zero server, radio server
- **Username:** {USER}
- **OS:** Ubuntu 22.04 (DragonOS hostname)
- **SSH key:** `~/.ssh/{SSH_KEY}` (deployed 2026-09-13; passwordless login works via `ssh agent-zero`)
- **Role:** Runs Agent Zero (Docker), ShadowBroker frontend/backend, MariaDB
- **Disk:** 117GB total, ~58GB free (49% used)
- **Full management:** see `remote-sudo-ssh/references/agent-zero-management.md` — container details, data layout, update procedure (self-update, NOT docker pull), troubleshooting

## Oracle Cloud Servers

### NetBird VPN Server (203.0.113.10)
- **Alias:** `netbird-vpn`
- **Username:** ubuntu
- **SSH key:** `~/.ssh/hermes_key` (chmod 600)
- **Role:** NetBird VPN management — relay (ports 80, 443), mgmt, signal (ports 33073, 33080)
- **Domain:** vpn.example.com (SSL via Let's Encrypt)
- **Config:** `/etc/netbird/config.yaml` managed by NetBird

### Gateway Server (203.0.113.11)
- **Alias:** `Gateway-server` (also accessible as `website-server` legacy alias at 203.0.113.13)
- **Username:** ubuntu
- **SSH key:** `~/.ssh/hermes_key`
- **Role:** Hosts n8n (https://n8n.example.com), DeerFlow, website
- **Services:** Docker containers for n8n, DeerFlow, web services

### Headscale Server (203.0.113.12)
- **Alias:** `headscale-server`
- **Username:** ubuntu
- **SSH key:** `~/.ssh/hermes_key`
- **Role:** Headscale VPN coordination server

### Oracle Cloud Credentials
All Oracle servers use the same `hermes_key` SSH key. Credentials stored in `~/.env.oracle` (git-ignored):
```bash
ORACLE_HOSTNAME=203.0.113.10
ORACLE_USER=ubuntu
ORACLE_KEY_PATH=~/.ssh/hermes_key
ORACLE_SSH_COMMAND="ssh -i ~/.ssh/hermes_key {USER}@203.0.113.10 -o StrictHostKeyChecking=no"

WG_HOSTNAME=203.0.113.11
WG_USER=ubuntu
WG_KEY_PATH=~/.ssh/hermes_key
WG_SSH_COMMAND="ssh -i ~/.ssh/hermes_key {USER}@203.0.113.11 -o StrictHostKeyChecking=no"

HS_HOSTNAME=203.0.113.12
HS_USER=ubuntu
HS_KEY_PATH=~/.ssh/hermes_key
HS_SSH_COMMAND="ssh -i ~/.ssh/hermes_key {USER}@203.0.113.12 -o StrictHostKeyChecking=no"
```

## How to Connect

### Preferred: SSH Key Auth (Terminal)

```bash
# Desktop (Windows 11 Pro)
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command here"

# Main server
ssh -i ~/.ssh/{SSH_KEY} -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command here"

# Agent server
ssh -i ~/.ssh/{SSH_KEY} -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command here"

# Agent Zero / Radio server
ssh -i ~/.ssh/{SSH_KEY} -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command here"
```

All of these also work via SSH config aliases (`ssh desktop`, `ssh main-server`, `ssh agent-server`, `ssh agent-zero`) since the aliases are defined in `~/.ssh/config`.

### Fallback: Paramiko (Python)

Only when programmatic access needed. Password: `<REDACTED_PASSWORD>`

```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='{LAN_IP}', username='{USER}', password='<REDACTED_PASSWORD>', timeout=15)
stdin, stdout, stderr = client.exec_command('command')
print(stdout.read().decode('utf-8'))
client.close()
```

**Agent Zero ({LAN_IP}):** SSH key `{SSH_KEY}` is now deployed — use `ssh -i ~/.ssh/{SSH_KEY} -o StrictHostKeyChecking=no {USER}@{LAN_IP} "command"` or the `ssh agent-zero` config alias. Fall back to paramiko only if the key is missing:

```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='{LAN_IP}', username='{USER}', password='<REDACTED_PASSWORD>', timeout=15)
stdin, stdout, stderr = client.exec_command('command')
print(stdout.read().decode('utf-8'))
client.close()
```

## Why SSH Keys > Paramiko

| Factor | SSH Key (terminal) | Paramiko |
|---|---|---|
| **Reliability** | Native OpenSSH, battle-tested | Python library, path issues on Windows |
| **Error handling** | SSH handles retries, timeouts | Manual exception handling |
| **Sandbox issues** | Runs in MSYS shell, full filesystem | Python sandbox can't see Windows paths |
| **Complexity** | One command | Import, connect, exec, decode, close |
| **File transfers** | `scp` / `sftp` available | Needs SFTPClient setup |

## Important Rules

- **NEVER change anything** without explicit user approval
- **Backup before editing configs on the main server.** Before touching `rules.yml`, `traefik.yml`, `.env`, `docker-compose.yaml`, `docker-compose.yml`, or any service config via SSH, create a timestamped backup on the server first: `cp <file> <file>.bak-$(date +%Y%m%d%H%M%S)`. SSH edits are remote — if something goes wrong you are on the other side of the network with no easy undo. Backups live alongside the original (same dir) unless a backup dir already exists (e.g. `core/traefik/backups/`). This applies to every docker-compose file in `/home/{USER}/docker_files/` — each stack's compose file is independently edited and independently backed up.

- **Backticks in YAML labels get eaten by shell quoting.** When piping a compose file edit through `ssh ... "python3 << 'PYEOF'"` or `ssh ... "cat > file << 'EOF'"`, bash may interpret backticks in `Host(\`hostname.example.com\`)` Traefik labels as command substitution even inside a quoted heredoc. The label arrives on the server as `Host()` (empty). **Workaround:** write the compose file using `python3 -c "..."` with the backtick as `\x60`, or use a heredoc with the delimiter quoted AND avoid backtick-containing content in the same command. Always `grep` the written file on the server for the hostname before restarting the service.
- Use this only when the user asks to interact with the home lab
- Agent server runs Docker containers: Hermes, Paperclip, LiteLLM, Honcho, default-api, meilisearch, qdrant, redis, postgres
- All docker-compose files in `/home/{USER}/docker_files/`
- Media on Terramaster: `/mnt/music`, `/mnt/movies`, `/mnt/tv`
- Internal SSD: `/mnt/nas`

## Network Diagnostics on Home Lab Servers

### Speed Testing — Use curl, Not speedtest-cli

**speedtest-cli is unreliable on the main server ({LAN_IP}).** It returns bogus results: 0.00 Mbit/s downloads, multi-million-millisecond pings to nearby servers, and timeouts to servers that should be reachable. Do not trust speedtest-cli output from the main server for throughput numbers.

**Use direct curl downloads against Cloudflare's speed test endpoint instead:**
```bash
# 1MB test — reads low due to cold start / TLS handshake overhead
curl -s -o /dev/null -w "Speed: %{speed_download} B/s in %{time_total}s\n" \
  https://speed.cloudflare.com/__down?bytes=1000000

# 10MB test — more representative of sustained throughput
curl -s -o /dev/null -w "Speed: %{speed_download} B/s in %{time_total}s\n" \
  https://speed.cloudflare.com/__down?bytes=10000000
```

Express results in **Mbps** (B/s × 8 / 1000000).

**Cross-verification:** if a VM or container routes through the main server, test both machines with the same curl command. They should agree within ~10% since they share the same physical uplink. A large discrepancy means either the VM has its own separate path or something is wrong with the bridging/NAT.

**Upload test:** Cloudflare's `__up` endpoint needs a payload file:
```bash
echo "test upload content" > /tmp/upload_test.txt
curl -s -X POST -T /tmp/upload_test.txt https://speed.cloudflare.com/__up \
  -w "Upload: %{speed_download} B/s\n"
rm /tmp/upload_test.txt
```

### Ethernet Utilization — Diagnostic Sequence

When asked "what's using the ethernet / how much bandwidth is flowing right now," run this sequence:

**Step 1 — Live rate (5-second sample):**
```bash
rx1=$(cat /sys/class/net/enp195s0/statistics/rx_bytes)
tx1=$(cat /sys/class/net/enp195s0/statistics/tx_bytes)
sleep 5
rx2=$(cat /sys/class/net/enp195s0/statistics/rx_bytes)
tx2=$(cat /sys/class/net/enp195s0/statistics/tx_bytes)
echo "RX: $((rx2 - rx1)) B/s = $(( (rx2 - rx1) * 8 / 1000000 )) Mbps"
echo "TX: $((tx2 - tx1)) B/s = $(( (tx2 - tx1) * 8 / 1000000 )) Mbps"
```

Replace `enp195s0` with the actual physical interface name. Find it with `ip route | grep default` (the dev column) or `ls /sys/class/net/` and pick the non-loopback, non-docker, non-bridge interface.

**Step 2 — Cumulative since boot:**
```bash
echo "RX total: $(($(cat /sys/class/net/enp195s0/statistics/rx_bytes) / {ID})) GB"
echo "TX total: $(($(cat /sys/class/net/enp195s0/statistics/tx_bytes) / {ID})) GB"
```

**Step 3 — Per-container network I/O (Docker hosts):**
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.NetIO}}"
```
Shows cumulative bytes in/out per container since each container started. Sort by largest numbers to find historical heavy users. **This is cumulative since container start, not live rate** — a container showing 29 GB RX may not be actively transferring now.

**Step 4 — Active connections:**
```bash
ss -tunap | grep ESTAB
```
Shows current connections with peer addresses and PIDs where visible.

**Step 5 — Interface topology:**
```bash
# Physical interface speed and link state
ethtool <iface> | grep -E "Speed|Link"

# Bridge membership
brctl show <bridge_name>

# Interface operstate
cat /sys/class/net/<iface>/operstate
```

**Interpreting utilization:** At 2.5 Gbps, 1% = 25 Mbps. A TX rate of 48 Mbps is ~2% utilization. The link is almost never saturated unless you see sustained rates above ~2 Gbps.

**Pitfall — Docker net I/O is cumulative since container start, not current rate.** Always pair `docker stats` (historical) with the live `/sys/class/net/` rate sample (current) to distinguish "what has this container transferred ever" from "what is flowing right now."

**Pitfall — Containers sharing a VPN tunnel show identical net I/O.** When multiple containers route through a VPN container (e.g. gluetun), their individual `docker stats` counters all reflect the shared tunnel, not per-container usage. In this session sabnzbd, kasm, qbittorrent, gluetun, and flaresolverr all showed identical 29.2 GB / 4.16 GB because they sit on the same VPN network. Use the live host-level rate + `ss` to see what's actually flowing.

## Disk Space (Agent Server {LAN_IP})

158GB disk. Major consumers:
- `/home/{USER}` — 55GB (projects, paperclip 1.9GB, hermesoriginalwebsite 1.3GB, cel-ast-research 1.3GB)
- `/snap` — 13GB (Firefox, GNOME, Chromium, Obsidian, Mesa)
- `/var/lib/snapd` — 5.3GB (snap packages data)
- `/tmp` — 4.9GB (build artifacts — leave alone)
- `/var/log` — was ~1.4GB, cleaned down
- Docker images — ~13GB (all active services)
