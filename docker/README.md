# Hermes Brain Docker Services
#
# Four independent Compose projects for isolation:
#   hermes-honcho
#   hermes-searxng
#   hermes-personal-organizer
#   hermes-brain
#
# Each service runs in its own network. Database ports are NOT exposed to LAN.
# All services bind to 127.0.0.1 (localhost only).
#
# Usage:
#   docker compose -f docker/docker-compose.honcho.yml up -d
#   docker compose -f docker/docker-compose.searxng.yml up -d
#   docker compose -f docker/docker-compose.personal-organizer.yml up -d
#   docker compose -f docker/docker-compose.brain.yml up -d

---
