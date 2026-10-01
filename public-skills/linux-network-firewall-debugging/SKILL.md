---
name: linux-network-firewall-debugging
description: >
  Debug "L2 works but L3 port blocked" on Linux hosts and KVM guests —
  the case where ping and SSH work but all other ports time out. Covers
  UFW silent drops, iptables-nft vs legacy confusion, KVM bridge filtering,
  and service binding (127.0.0.1 vs 0.0.0.0).
category: devops
---

# Linux Network Firewall Debugging

Diagnose the specific failure mode where Layer 2 works (ping, ARP) and SSH (port 22) works, but ALL other ports time out despite confirmed service listeners.

## The Classic Symptom

```
Host$ ping {LAN_IP}          → OK
Host$ ssh {LAN_IP}           → OK
Host$ curl http://{LAN_IP}:8088 → TIMEOUT (not refused)
```

This is almost always a firewall rule on the target host silently dropping packets.

## Root Cause: UFW Default-Deny

Ubuntu's UFW (Uncomplicated Firewall) defaults to:
- `Status: active`
- `Default: deny (incoming), allow (outgoing)`

SSH (22) is auto-allowed when UFW is enabled. Every other port gets **dropped** (not rejected), causing timeouts.

### Why `iptables -L` looks empty

Modern Ubuntu (22.04+) uses `iptables-nft` — the legacy `iptables -L` shows nothing because UFW rules live in the **nft ruleset**:

```bash
# Legacy view (lies — shows nothing)
sudo iptables -L -n -v

# Real view (shows UFW rules)
sudo nft list ruleset | grep -A2 "ufw"
```

## Diagnostic Sequence

Run from the target host (the one with the blocked port):

```bash
# 1. Is UFW active and default-deny?
sudo ufw status verbose
# Look for "Default: deny (incoming)"

# 2. Is the port actually listening on the right interface?
ss -tlnp | grep <port>
# LISTEN on 0.0.0.0 or specific IP = reachable
# LISTEN on 127.0.0.1 only = NOT reachable from outside (service issue, not firewall)

# 3. Test from the host itself to confirm the service works
curl -s http://127.0.0.1:<port>/health

# 4. Check the real firewall rules
sudo nft list ruleset 2>/dev/null | grep -E "ufw|drop|reject"
```

## Fix

```bash
# Allow specific port
sudo ufw allow <port>/tcp

# Allow a range
sudo ufw allow <start>:<end>/tcp

# Reload
sudo ufw reload

# Verify
sudo ufw status numbered
```

## KVM Guest Considerations

When the target is a KVM VM:
- The hypervisor's bridge (e.g., `bridge0`) does NOT filter by default — the drop is inside the guest
- `bridge-nf-call-iptables` is usually 0 (disabled) on Ubuntu desktop hosts
- Focus on the **guest's** UFW, not the host's

## Service Binding vs Firewall

Two distinct problems produce the same symptom:

| Problem | `ss -tlnp` shows | Fix |
|---------|------------------|-----|
| Firewall drop | `0.0.0.0:<port> LISTEN` | `ufw allow <port>/tcp` |
| Service bound local | `127.0.0.1:<port> LISTEN` | Change service config to bind `0.0.0.0` |
| Service not running | nothing | Start the service |

**Always check `ss -tlnp` first** — a service bound to `127.0.0.1` will time out from outside regardless of firewall rules.

## Prevention

When deploying a service that needs LAN access:
```bash
# Bind to all interfaces
python3 app.py --host 0.0.0.0 --port 8088

# Open firewall
sudo ufw allow 8088/tcp

# Verify from another host
curl http://<host-ip>:8088/
```

## Case Study: 2026-08-25

A FastAPI dashboard (port 8088) on KVM VM `HermesAgent` ({LAN_IP}) was running and confirmed listening via `ss -tlnp` on `0.0.0.0:8088`. Host could ping and SSH but port 8088 timed out. `iptables -L` showed zero rules. `ufw status` revealed only ports 22, 8787, 3100, 3389, 9119, 1022 were allowed. Fixed with `sudo ufw allow 8088/tcp`.
