## Entry 1 / 2026-09-13 / 11:12 pm
Symptom: app-01 and app-02 containers remain in unhealthy status continuously in docker compose ps.

Hypothesis: The Docker compose healthcheck is hitting a non-existent endpoint or the application fails to start up properly.

Command or test: docker compose logs app-01 --tail 50

Actual output: 127.0.0.1 - - [13/Sep/2026 20:05:10] "GET /healthz HTTP/1.1" 404 -

Failed attempt and what changed your thinking: N/A (Direct diagnosis from logs confirmed path mismatch immediately).

Root cause: The docker-compose.yml healthcheck command was configured to probe http://localhost:8080/healthz, whereas the Flask application defines the liveness endpoint at /health.

Fix: Updated docker-compose.yml healthcheck command for app-01 and app-02 from /healthz to /health.

Retest evidence: Ran docker compose up -d and verified docker compose ps shows (healthy) status for both app instances.

Related commit: fix(compose): correct healthcheck endpoint from /healthz to /health

Remaining uncertainty: None for this specific issue.

## Entry 2 / 2026-09-13 / 11:22
- Symptom: NGINX fails to route traffic to app-01, and host port 8080 yields connection refused/timeout.
- Hypothesis: NGINX container port mapping in docker-compose.yml does not match NGINX listen port in nginx.conf, and upstream configuration targets an incorrect backend port.
- Command or test: `cat nginx/nginx.conf` and `grep -A 10 "nginx:" docker-compose.yml`
- Actual output: `nginx.conf` listens on port 80 and passes traffic to `app-01:8081`. `docker-compose.yml` mapped host port to container port 81 (`:81`).
- Failed attempt and what changed your thinking: N/A (Direct configuration review identified two distinct port mismatches).
- Root cause: Container port misconfiguration in docker-compose.yml (`81` instead of `80`) and incorrect upstream port for `app-01` in `nginx/nginx.conf` (`8081` instead of `8080`).
- Fix: Corrected container port mapping in `docker-compose.yml` to `127.0.0.1:${PUBLIC_PORT:-8080}:80` and updated `nginx/nginx.conf` upstream for `app-01` to `app-01:8080`.
- Retest evidence: Executed `docker compose up -d` and verified `curl -s http://localhost:8080/` returns HTTP 200 response.
- Related commit: `fix(nginx): correct port mappings and upstream configuration`
- Remaining uncertainty: None.
