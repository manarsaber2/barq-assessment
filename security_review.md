# Security and Production-Readiness Review


## 1. Hardcoded Secrets in Configuration Files
- **Risk and evidence**: Plaintext database credentials (`POSTGRES_PASSWORD: BarqLabOnly_7qN2vK8c`) were hardcoded in `docker-compose.yml` and repository environment templates.
- **Impact**: Exposure of secrets via version control leaks leads to unauthorized database access and privilege escalation.
- **Implemented fix / commit**: Parameterized credentials into environment files (`config/app.env`) and excluded sensitive files via `.gitignore`. (Commit: `1ae613e`)
- **Production follow-up**: Integrate HashiCorp Vault or AWS Secrets Manager with dynamic credential rotation and runtime injection.
- **How to verify**: Execute `git grep -i "BarqLabOnly"` across repository history to ensure zero unencrypted secrets exist in source code.

---

## 2. Unrestricted Host Network Port Binding & Database Exposure
- **Risk and evidence**: PostgreSQL and Redis ports were published to the host (`127.0.0.1:15432:5432`, `127.0.0.1:16379:6379`), reachable directly from the host machine and bypassing NGINX entirely.
- **Impact**: Unauthenticated or unauthorized network scanning and brute-force attacks could directly target internal databases, bypassing the reverse proxy boundary.
- **Implemented fix / commit**: Initial restriction to `127.0.0.1:15432`/`127.0.0.1:16379` (Commit: `1ae613e`), followed by full removal of host port publishing for both PostgreSQL and Redis — no `ports:` mapping remains for either service; access is now only possible from within the internal `backend` Docker network. (Commit: `78a6c70`)
- **Production follow-up**: Enforce host firewall rules (UFW/iptables) as defense-in-depth, and keep host port mapping disabled entirely in production/Kubernetes deployments.
- **How to verify**: From the host, `psql -h 127.0.0.1 -p 15432 ...` and `redis-cli -h 127.0.0.1 -p 16379 ping` must both fail with connection refused.

---

## 3. Excessive Container Privileges & Default Root Execution
- **Risk and evidence**: Containers executed as root despite a dedicated non-root user (`app`, uid 10001) being created in the Dockerfile — a `USER root` directive before CMD overrode it. Verified via `docker exec app-01 whoami` → `root`, `id` → `uid=0(root) gid=0(root) groups=0(root)`.
- **Impact**: Container escape or RCE grants the attacker root inside the container, removing the isolation the dedicated user was meant to provide.
- **Implemented fix / commit**: Removed `USER root`, switched to `USER app` in Dockerfile. Reverified: `whoami` → `app`, `id` → `uid=10001(app) gid=10001(app)`. App confirmed healthy post-change via `/health` and `/instance`. (Commit: `7a9c963`)
- **Production follow-up**: Add `read_only: true` root filesystem and drop all capabilities except those strictly required (`cap_drop: [ALL]`).
- **How to verify**: `docker exec app-01 whoami` → must return `app`, not `root`.

---

## 4. Supply Chain Risks & Unpinned Parent Image Tags
- **Risk and evidence**: Docker images originally used mutable tags (e.g., `postgres:16-alpine`), exposing builds to upstream image modification.
- **Impact**: Malicious upstream image poisoning or breaking updates could corrupt build reproducibility and compromise production clusters.
- **Implemented fix / commit**: Hardened all base container images using immutable cryptographic SHA256 digests (`postgres:16-alpine@sha256:...`). (Commit: `1ae613e`)
- **Production follow-up**: Implement automated container image scanning using Trivy or Grype in CI/CD pipelines to block vulnerable base layers.
- **How to verify**: Inspect `docker-compose.yml` to confirm all `image:` entries reference explicit `@sha256` checksums.

---

## 5. Network Perimeter Bypass & Unisolated Tier Architecture
- **Risk and evidence**: Nginx and internal backend datastores shared a common flat network, allowing potential lateral pivoting.
- **Impact**: A compromised Nginx reverse proxy could be leveraged to attack PostgreSQL or Redis datastores directly.
- **Implemented fix / commit**: Segmented infrastructure into `frontend` (public) and `backend` (internal-only, `internal: true`) networks. Nginx is restricted exclusively to `frontend`. (Commit: `1ae613e`)
- **Production follow-up**: Deploy Cilium or Calico CNI with strict Layer 7 NetworkPolicies restricting ingress/egress.
- **How to verify**: Run `docker exec nginx ping postgres` and verify network resolution fails.

---

## 6. Ephemeral Database Storage & Disaster Risk
- **Risk and evidence**: Initial deployment used temporary `tmpfs` mounts for PostgreSQL storage, risking data loss on container recreation.
- **Impact**: Container crashes or updates result in permanent deletion of business data and transaction logs.
- **Implemented fix / commit**: Replaced volatile mounts with persistent named Docker volume `postgres-data:/var/lib/postgresql/data`. (Commit: `1ae613e`)
- **Production follow-up**: Implement automated point-in-time recovery (PITR) with continuous Write-Ahead Logging (WAL) shipping to S3 storage.
- **How to verify**: Perform `docker compose down -v` vs `docker compose down` and test record survival via `validate.py`.

---

## 7. No Rate Limiting on Write Endpoints
- **Risk and evidence**: `grep -n "limiter\|rate_limit" app/server.py` returns no matches. `POST /records` and `/counter` accept an unlimited number of requests per client with no throttling at either the NGINX or application layer.
- **Impact**: Enables resource exhaustion (PostgreSQL/Redis connection saturation) or abuse of the `/records` write path with no rate control, increasing exposure to denial-of-service conditions.
- **Implemented fix / commit**: Not implemented — identified as a gap during review, documented here as a planned improvement rather than completed work.
- **Production follow-up**: Add rate limiting at the NGINX layer (`limit_req_zone`) or application layer (Flask-Limiter), scoped per client IP, with stricter limits on the write path (`POST /records`) than on read-only endpoints.
- **How to verify**: N/A — not yet implemented. Once added, send sustained traffic above the configured limit to `POST /records` and confirm a `429` response is returned instead of unconditional processing.

---

## 8. Single Point of Failure (SPOF) & Unhandled Upstream Errors
- **Risk and evidence**: Default Nginx reverse proxy configuration returned HTTP 502/504 errors directly to clients when a single Flask instance failed.
- **Impact**: Partial backend outages resulted in user-facing service downtime and degraded SLA availability metrics.
- **Implemented fix / commit**: Fine-tuned Nginx passive health checks (`max_fails=1 fail_timeout=1s`) and forced automatic failover retries (`proxy_next_upstream`). (Commit: `9b84e7b`)
- **Production follow-up**: Implement multi-region load balancing with active health checking (e.g., AWS ALB / Cloudflare).
- **How to verify**: Run `python failure_test.py` and confirm 100% request success rate during active container failure.

---

## 9. Redis Persistence Disabled for a Stateful Feature
- **Risk and evidence**: Redis runs with `--save "" --appendonly no`, disabling both RDB snapshots and AOF. The `/counter` endpoint relies on Redis for state.
- **Impact**: Any Redis container restart or crash silently resets the counter to zero with no warning to clients — a silent data-loss path.
- **Implemented fix / commit**: [decide: is this intentional for a stateless counter, or should AOF be enabled? Document your reasoning either way — do not leave this bracket in the final submission.]
- **Production follow-up**: Enable AOF (`appendonly yes`) if counter state must survive restarts, or document explicitly that it's treated as ephemeral cache.
- **How to verify**: `docker compose restart redis` then check `/counter` value.

---

## 10. Misconfigured Health Checks Masked True Service State
- **Risk and evidence**: Compose healthcheck targeted a non-existent `/healthz` path, so containers reported `unhealthy` even when the application was fully functional — see troubleshooting.md for full investigation.
- **Impact**: Orchestration tooling relying on health status (restart policies, load balancer registration) would have made incorrect decisions based on a false-negative health signal.
- **Implemented fix / commit**: Corrected healthcheck target to `/health` (Commit: `3ec357e`); corrected matching NGINX upstream port mismatch (Commit: `8b68139`) and listen/publish port mismatch (Commit: `807eca0`).
- **Production follow-up**: Add a CI step that fails the build if healthcheck targets don't match any route defined in the app.
- **How to verify**: `docker compose ps -a` shows all app containers `healthy`.