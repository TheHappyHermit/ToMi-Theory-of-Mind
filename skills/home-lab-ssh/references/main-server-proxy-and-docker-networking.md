# Main Server Reverse Proxy & Docker Networking

How the main server (<LLAMA-CPP-HOST-IP>) routes traffic and how to wire new Docker services into Traefik.

## Server Layout

- **Traefik** is the main reverse proxy: ports 80/443 (HTTP/HTTPS), 8082 (metrics/dashboard).
- Traefik config: `$HOME/docker_files/core/traefik/traefik.yml` (static) + `$HOME/docker_files/core/traefik/rules.yml` (dynamic, file provider).
- Traefik also uses the Docker provider (`providers.docker`) with `exposedByDefault: false` and `network: proxy` — so only containers explicitly attached to the `proxy` Docker network AND carrying Traefik labels get auto-discovered.
- `rules.yml` also defines static routers/services for non-Docker backends (e.g. homeassistant at <HOME-ASSISTANT-IP>, agentzero at <LAN-HOST-IP>).
- **Pi-hole** is a separate device on the LAN. The main server does NOT run Pi-hole. DNS resolution happens at the Pi-hole; the server only handles HTTP/TLS routing. The Pi-hole wildcard DNS setting handles `*.<SERVICE-DOMAIN>` → server IP automatically.

## Traefik Docker Label Pattern (for new services)

When adding a new Docker service that should be reachable through Traefik on the main server, follow this sequence. The critical dependency is that the container must be on the `proxy` network before Traefik can route to it.

1. **Connect the container to the `proxy` network.** In the service's docker-compose, add `proxy` to its `networks:` list AND declare `proxy` as an external network at the top level:
   ```yaml
   networks:
     - proxy        # <-- add this to the service's networks
   # ...
   networks:
     proxy:
       external: true   # <-- declare at top level
   ```

2. **Add Traefik labels to the service.** Minimum set:
   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.<name>.rule=Host(`<hostname>.<SERVICE-DOMAIN>`)"
     - "traefik.http.routers.<name>.entrypoints=websecure"
     - "traefik.http.routers.<name>.tls.certresolver=cloudflare"
     - "traefik.http.routers.<name>.middlewares=crowdsec-bouncer@file"
     - "traefik.http.services.<name>.loadbalancer.server.port=<container-port>"
   ```
   Replace `<name>` with a short unique Router/Service name (e.g. `deerflow`), `<hostname>` with the desired subdomain, and `<container-port>` with the port the container listens on internally.

3. **If the container was already running when labels were added**, restart Traefik (`docker restart traefik`) so the Docker provider rescans and picks up the new router. Traefik does not always hot-reload labels from already-running containers immediately.

4. **Verify**: `curl -s -o /dev/null -w '%{http_code}' http://<hostname>/` from another LAN device. A direct curl to `<LLAMA-CPP-HOST-IP>:<container-port>` also works as a fallback test bypassing Traefik.

## Docker Compose .env Shadowing

When a docker-compose project lives in a subdirectory (e.g. `docker/docker-compose.yaml`), Docker Compose reads `.env` from the same directory as the compose file — NOT the repo root. This means:

- Editing the repo-root `.env` does NOT affect `docker compose` run from the `docker/` subdirectory if a `docker/.env` exists there.
- **Pitfall:** both `../.env` and `docker/.env` can carry `BIND_HOST` / `PORT` / other vars. When things don't take effect, check `ls docker/.env` first — the subdirectory one wins for `docker compose` commands run from inside `docker/`.

## Traefik Troubleshooting

- **"Could not resolve host" when curling a Traefik hostname from the server itself:** The server's resolver (`systemd-resolved` at 127.0.0.53) may not forward to Pi-hole for local names, or the name isn't in `/etc/hosts`. Test DNS resolution separately: `dig @<LLAMA-CPP-HOST-IP> <SERVICE-HOST> +short` (pointing at Pi-hole directly). The hostname works from other LAN devices if Pi-hole's wildcard handles it; it may not resolve from the server itself.
- **"Connection refused" on Pi-hole DNS port (53):** Pi-hole may not be at <LLAMA-CPP-HOST-IP> at all — it's a separate device. Find its actual IP from another LAN device or the Pi-hole web UI. Don't assume the server is the DNS server.
- **Traefik logs are quiet by default:** `docker logs traefik --tail 30` shows Crowdsec errors and provider events. Look for "router" or the service name in logs after a restart to confirm the router was added.
- **Crowdsec bouncer errors in Traefik logs are normal** if Crowdsec container is down or restarting — they don't block routing. Ignore unless you're debugging auth blocks specifically.
- **Backticks in shell heredocs get eaten by bash command substitution.** When writing YAML with `Host(\`hostname\`)` or any backtick-containing content via `ssh ... "cat << 'EOF'"` or `python3 << 'PYEOF'`, bash may interpret the backticks as command substitution despite the quoted heredoc delimiter. Symptoms: the router rule arrives as `Host()` (empty) on the server. **Workaround:** use `chr(96)` in Python, or write the file with `python3 -c "..."` using escaped backticks, or base64-encode the payload and decode on the server. Always `grep` the written file on the server to confirm backticks survived before restarting the service.

## Adding a New Service to an Existing Docker Compose Stack

When adding a new container to an existing docker-compose file in `$HOME/docker_files/*/`:

1. **Read the current compose file in full first.** Note the top-level `networks:`, existing service patterns, env var conventions (`${VAR}` vs hardcoded), and volume mount style (`./service/data:/path` vs named volumes). Match the existing style.
2. **Back up the compose file on the server** before editing: `cp docker-compose.yml docker-compose.yml.bak-$(date +%Y%m%d%H%M%S)`. Compose edits are remote; a bad edit breaks the whole stack on the next `docker compose up`. Each stack's compose file is independently edited and backed up.
3. **Insert the new service block** in alphabetical or logical order among existing services (match the file's existing ordering convention — do not reorder existing services).
4. **Verify port availability** before assigning a host port mapping: `ss -tlnp | grep ':PORT '` and `docker ps --format '{{.Ports}}' | grep 'PORT'`. Note: containers that only expose a port internally (no `0.0.0.0:PORT->PORT` mapping, just `PORT/tcp`) do NOT occupy the host port — they appear in `docker ps` output but not in `ss`. Prefer internal-only ports when Traefik handles external routing; only add a host mapping for direct debugging access.
5. **After starting the container, verify connectivity from inside it** — not just that the container is running, but that it can reach its dependencies. For services that call external endpoints (LLM servers, search backends, databases), exec into the container and verify with Python urllib (curl is often not installed in slim images):
   ```bash
   docker exec <container> python3 -c "import urllib.request; r=urllib.request.urlopen('http://<host>:<port>', timeout=10); print(r.status)"
   ```
6. **Check container logs** for startup errors: `docker logs <container> --tail 20`. A container that is "Up" but erroring internally is not running.

## Large Docker Image Pulls

Pulling images >1 GB on this server is slow and prone to stalls.

- **Never run multiple parallel pulls of the same image** — they compete for bandwidth and can deadlock. Before starting a pull, check for and kill any existing pulls of the same image: `pkill -f 'docker.*<image-name>'`.
- **If `docker compose pull` or `docker pull` stalls** with no progress in the log for >5 minutes and the process is sleeping on `futex_wait`, kill it and retry. The Docker Hub connection may have stalled.
- **`docker compose up -d <service>` as a single command** often works better than a separate `pull` + `up` sequence for large images, because a single compose invocation manages the pull lifecycle without competing processes.
- **Monitor progress via `docker images <repo>`** (image appears when pull completes) rather than parsing the pull log — the log may not update during extraction.

## Adding a New Docker Service to an Existing Stack

When adding a new container to an existing docker-compose file (e.g. a new AI app alongside Ollama, Open-WebUI, DeerFlow):

1. **Read the current compose file in full first** — note the top-level `networks:`, existing service patterns, env var conventions (`${VAR}` vs hardcoded), and volume mount style (`./service/data:/path` vs named volumes). Match the existing style.
2. **Back up the compose file on the server** before editing: `cp docker-compose.yml docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)`. Compose edits are remote; a bad edit breaks the whole stack on restart.
3. **Insert the new service block** in alphabetical or logical order among the existing services (match the file's existing ordering convention — e.g. group by function, not randomly). Do not reorder existing services unless the user asks.
4. **Verify port availability** before assigning a host port mapping: `ss -tlnp | grep ':PORT '` and `docker ps --format '{{.Ports}}' | grep 'PORT'`. Containers that only expose a port internally (no `0.0.0.0:PORT->PORT` mapping) do NOT occupy the host port — they appear in `docker ps` but not in `ss`. Prefer internal-only ports when Traefik handles external routing; only add a host mapping for direct debugging access.
5. **Test connectivity from the new container after startup** — not just that the container is running, but that it can reach its dependencies. For services that call external endpoints (LLM servers, search backends, databases), exec into the container and verify with Python urllib (curl is often not installed in slim images):
   ```bash
   docker exec <container> python3 -c "import urllib.request; r=urllib.request.urlopen('http://<dependency>:<port>', timeout=10); print(r.status)"
   ```
6. **Check the container logs** for startup errors: `docker logs <container> --tail 20`. A container that is "Up" but erroring internally is not running.

## Large Docker Image Pulls

Pulling images >1 GB on this server is slow and prone to stalls. The `itzcrazykns1337/vane:slim-latest` image is ~2.8 GB.

- **Never run multiple parallel pulls of the same image** — they compete for bandwidth and can deadlock. Kill redundant pulls before starting a new one: `pkill -f 'docker.*<image>'`.
- If `docker compose pull` or `docker pull` stalls with no progress in the log for >5 minutes and the process is on `futex_wait`, kill it and retry. The Docker Hub connection may have stalled.
- `docker compose up -d <service>` as a single command triggers its own pull and is often more reliable than a separate `pull` + `up` sequence, because a single compose invocation manages the pull lifecycle without competing processes.
- Monitor progress via `docker images <repo>` (image appears when pull completes) rather than parsing the pull log — the log may not update during extraction.
