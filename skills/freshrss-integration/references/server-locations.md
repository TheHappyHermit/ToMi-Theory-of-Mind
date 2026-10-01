# Internal Service Locations

Known IPs and access patterns for internal services on this network.

## Local Server (<LLAMA-CPP-HOST-IP>)

Primary machine running Docker-based services behind Traefik.

| Service | Hostname | Port | Access Pattern |
|---------|----------|------|----------------|
| FreshRSS | <SERVICE-HOST> | 443 | IP direct with `Host: <SERVICE-HOST>` |
| LiteLLM | <SERVICE-HOST> | 443 | IP direct with Host header |
| Traefik dashboard | <SERVICE-HOST> | 443 | Reverse proxy manager |
| Honcho | localhost | 8000 | Direct, no Host header needed |

### Connection Pattern

```bash
# All services use Traefik with self-signed certs
curl -sk "https://<LLAMA-CPP-HOST-IP>/api/greader.php/accounts/ClientLogin" \
  -H "Host: <SERVICE-HOST>" \
  --max-time 15
```

The Host header is critical — Traefik routes based on it.
DNS (`<SERVICE-HOST>`) may not resolve; always use IP direct.

## Oracle Server (<ORACLE-CLOUD-IP-1>)

Old/alternate cloud server. Currently no FreshRSS there.

| Service | Port | Notes |
|---------|------|-------|
| <SERVICE-DOMAIN> frontend | 443 | Public website, not FreshRSS |
| CognitivePlatform | 443 | Paperclip workspace at /opt/CognitivePlatform-ai/ |
