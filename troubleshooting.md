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
