# Technical Decisions


## Decision 1: Base Image Standardization & Pinning
- **Choice**: Multi-stage/Minimal Alpine-based official images pinned via strict SHA256 image digests (`postgres:16-alpine@sha256:...`, `redis:7.4-alpine@sha256:...`, `nginx:1.28-alpine@sha256:...`).
- **Why**: Minimizes container surface area, reduces vulnerabilities, ensures predictable image builds, and guarantees absolute immutability across evaluation environments.
- **Alternative**: Unpinned `latest` tags or Debian-based full OS parent images.
- **Trade-off**: Slightly reduced runtime diagnostic tools in Alpine container instances (requires installing `curl`/`pg_isready` explicitly when debugging).
- **Evidence / commit**: Commits `fix(infra): harden docker-compose with strict network isolation, persistence, and resource limits`
- **Production improvement**: Prevents unintended version drifting and supply-chain attacks in automated CI/CD pipelines.

---

## Decision 2: Multi-Layer Health Checks & Bounded Waits
- **Choice**: Native health checks configured at both Docker Compose level (`pg_isready`, `redis-cli ping`, Python HTTP probes) and application level (`/health` & `/ready` endpoints).
- **Why**: Guarantees zero-downtime dependency readiness before Nginx routes external requests to backend Flask instances.
- **Alternative**: Arbitrary sleep timers (`sleep 10`) or unmonitored container starts.
- **Trade-off**: Marginal increase in CPU overhead during interval polls (3s-5s intervals).
- **Evidence / commit**: Commits `test(validation): add automated health, endpoint, and network isolation check script`
- **Production improvement**: Eliminates race conditions during cold starts and rolling deployments.

---

## Decision 3: Strict Two-Tier Network Isolation Architecture
- **Choice**: Segmented networks (`frontend` public-facing, `backend` internal & non-routable). Flask apps bridge both networks; Nginx is strictly bound to `frontend` only.
- **Why**: Enforces absolute perimeter boundary security. Nginx cannot bypass application logic to directly contact PostgreSQL or Redis.
- **Alternative**: Single shared `bridge` network for all containers.
- **Trade-off**: Requires microservice containers to manage multiple network interfaces.
- **Evidence / commit**: Commits `fix(infra): harden docker-compose with strict network isolation, persistence, and resource limits`
- **Production improvement**: Prevents lateral movement attacks if the public-facing Nginx web server is compromised.

---

## Decision 4: Aggressive Nginx Failover & Upstream Timeout Limits
- **Choice**: Configured `max_fails=1 fail_timeout=1s` with explicit retry directives (`proxy_next_upstream error timeout invalid_header http_502 http_503 http_504 non_idempotent;`) and connection timeouts (`proxy_connect_timeout 1s`).
- **Why**: Ensures 100% zero-downtime failover during backend instance crashes, routing incoming traffic seamlessly to healthy instances within milliseconds.
- **Alternative**: Default Nginx upstream balancing, which leaks HTTP 502/504 errors to end clients during instance shutdowns.
- **Trade-off**: Retried non-idempotent requests need backend idempotency protection.
- **Evidence / commit**: Commits `test(resilience): implement failure and recovery automation with zero-downtime nginx failover`
- **Production improvement**: Delivers resilient SLA uptime metrics under high workload component failures.

---

## Decision 5: Durable Named Storage & Resource Capping Policy
- **Choice**: Persistent PostgreSQL named volumes (`postgres-data:/var/lib/postgresql/data`) paired with explicit `cgroup` limits (`cpus: 0.25-0.50`, `memory: 128M-256M`) and `restart: unless-stopped`.
- **Why**: Prevents catastrophic data loss across service lifecycle events while preventing noisy-neighbor container resource exhaustion.
- **Alternative**: Ephemeral `tmpfs` mounts and unrestricted container resource usage.
- **Trade-off**: Requires explicit storage backup/restore routines for disaster recovery.
- **Evidence / commit**: Commits `fix(infra): harden docker-compose with strict network isolation, persistence, and resource limits`
- **Production improvement**: Ensures state persistence and stable node resource footprint during memory/CPU spikes.