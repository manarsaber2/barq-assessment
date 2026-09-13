## Entry 1 / 2026-09-13 / 11:12 pm
**Symptom**: app-01 and app-02 containers remain in unhealthy status continuously in docker compose ps.

**Hypothesis**: The Docker compose healthcheck is hitting a non-existent endpoint or the application fails to start up properly.

**Command or test**: docker compose logs app-01 --tail 50

**Actual output**: 127.0.0.1 - - [13/Sep/2026 20:05:10] "GET /healthz HTTP/1.1" 404 -

**Failed attempt and what changed your thinking:** N/A (Direct diagnosis from logs confirmed path mismatch immediately).

**Root cause:** The docker-compose.yml healthcheck command was configured to probe http://localhost:8080/healthz, whereas the Flask application defines the liveness endpoint at /health.

**Fix:** Updated docker-compose.yml healthcheck command for app-01 and app-02 from /healthz to /health.

**Retest evidence:** Ran docker compose up -d and verified docker compose ps shows (healthy) status for both app instances.

**Related commit:** fix(compose): correct healthcheck endpoint from /healthz to /health

**Remaining uncertainty:** None for this specific issue.

## Entry 2 / 2026-09-13 / 11:22
- **Symptom:** NGINX fails to route traffic to app-01, and host port 8080 yields connection refused/timeout.
-**Hypothesis:** NGINX container port mapping in docker-compose.yml does not match NGINX listen port in nginx.conf, and upstream configuration targets an incorrect backend port.
- **Command or test:** `cat nginx/nginx.conf` and `grep -A 10 "nginx:" docker-compose.yml`
- **Actual output:** `nginx.conf` listens on port 80 and passes traffic to `app-01:8081`. `docker-compose.yml` mapped host port to container port 81 (`:81`).
- **Failed attempt and what changed your thinking:** N/A (Direct configuration review identified two distinct port mismatches).
- **Root cause:** Container port misconfiguration in docker-compose.yml (`81` instead of `80`) and incorrect upstream port for `app-01` in `nginx/nginx.conf` (`8081` instead of `8080`).
- **Fix:** Corrected container port mapping in `docker-compose.yml` to `127.0.0.1:${PUBLIC_PORT:-8080}:80` and updated `nginx/nginx.conf` upstream for `app-01` to `app-01:8080`.
- **Retest evidence:** Executed `docker compose up -d` and verified `curl -s http://localhost:8080/` returns HTTP 200 response.
- **Related commit:** `fix(nginx): correct port mappings and upstream configuration`
- **Remaining uncertainty:** None.

## Entry 3 / 2026-09-13 / 11:43
Symptom: NGINX returns 502 Bad Gateway for incoming requests, and both app instances report identical INSTANCE_ID in responses.

Hypothesis: Python application containers are binding to loopback (127.0.0.1), isolating them from NGINX on the Docker network, and app-02 environment config shares app-01 identifier.

Command or test: cat docker-compose.yml and for i in {1..4}; do curl -s http://localhost:8080/instance; echo ""; done

Actual output: APP_HOST was set to 127.0.0.1 under &app-env, and app-02 had INSTANCE_ID: "app-01". Requests to NGINX resulted in 502 Bad Gateway.

Failed attempt and what changed your thinking: N/A (Direct compose configuration review revealed interface binding restrictions and duplicate environment variables).

Root cause: APP_HOST restricted listener sockets to 127.0.0.1 inside containers, preventing inter-container proxy traffic from NGINX, alongside a copy-paste error setting INSTANCE_ID to app-01 for app-02.

Fix: Updated APP_HOST to 0.0.0.0 in docker-compose.yml to listen on all container network interfaces, and corrected app-02 INSTANCE_ID to "app-02".

Retest evidence: Executed docker compose up -d --build and verified for i in {1..4}; do curl -s http://localhost:8080/instance; echo ""; done successfully alternates responses between app-01 and app-02 with 200 OK.

Related commit: fix(compose): update APP_HOST to 0.0.0.0 and correct app-02 instance ID

Remaining uncertainty: None.

## Entry 4 / 2026-09-13 / 11:58
Symptom: /ready, /records, and /counter endpoints return 503 SERVICE UNAVAILABLE with postgres_unavailable and redis_unavailable status messages.

Hypothesis: Mismatched connection credentials and ports inside config/app.env preventing applications from reaching database services on the backend network.

Command or test: cat config/app.env

Actual output: DATABASE_URL referenced port 5433 and password BarqLabOnly_7qN2vK8d. REDIS_URL referenced port 6380.

Failed attempt and what changed your thinking: N/A (Direct evaluation of connection string properties identified typo in password and incorrect non-standard container ports).

Root cause: Incorrect internal port bindings (5432 vs 5433, 6379 vs 6380) and a typographical error in the PostgreSQL password within config/app.env.

Fix: Corrected DATABASE_URL to postgresql://barq_app:BarqLabOnly_7qN2vK8c@postgres:5432/barq_tasks and REDIS_URL to redis://redis:6379/0 inside config/app.env.

Retest evidence: Executed docker compose up -d and verified curl -i http://localhost:8080/ready returns 200 OK with healthy Postgres and Redis dependencies.

Related commit: fix(config): correct postgres and redis ports and credentials in app.env

Remaining uncertainty: None.

### Entry #5: Infrastructure Hardening, Network Isolation, and Persistence Fixes ,2026-09-14 / 12:53
- **Symptoms**: Initial docker-compose layout used temporary `tmpfs` storage for PostgreSQL, risking data loss on restart; Nginx shared the backend network exposing internal boundaries; missing resource limits and container restart policies violated baseline assessment rules.
- **Hypotheses**: 
  1. Routing Nginx strictly through the frontend network while bridging Flask apps to both frontend and backend preserves complete security isolation.
  2. Binding `postgres-data` directly to `/var/lib/postgresql/data` ensures permanent state retention across reboots.
- **Commands**: 
  - Updated `docker-compose.yml` to remove `tmpfs` and attach `postgres-data` directly.
  - Restricted `nginx` networks to `frontend` only.
  - Added explicit CPU/Memory limits and `restart: unless-stopped` policies.
- **Results**: Complete compliance with isolation requirements, durable database persistence, and robust resource capping.
- **Root Cause**: Over-permissive Nginx network exposure and misconfigured database storage mapping in the template layout.
- **Fix**: Re-architected `docker-compose.yml` to enforce strict network separation, proper volume mounting, and container resilience policies.
- **Retest Evidence**: Validated container network inspection and database durability across service restarts.