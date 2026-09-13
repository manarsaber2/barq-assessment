# System Architecture & Infrastructure Topology



## 1. Component Topology & Network Layout

The system is deployed using Docker Compose with strict two-tier network isolation:
+-----------------------------------------------------------------------------------+
|                                 HOST ENVIRONMENT                                  |
|                                                                                   |
|    Client Request ---> Host Port: 8090 (or 8080)                                  |
|                                 |                                                 |
|  +------------------------------v----------------------------------------------+  |
|  | FRONTEND NETWORK (Public-Facing Bridge)                                    |  |
|  |                                                                            |  |
|  |   +--------------------------------------------------------------------+   |  |
|  |   | NGINX Reverse Proxy Container (nginx)                              |   |  |
|  |   | Port: 80 (Internal) <--- Proxies to http://flask_backends            |   |  |
|  |   +----------------------------------+---------------------------------+   |  |
|  +--------------------------------------|-------------------------------------+  |
|                                         |                                         |
|  +--------------------------------------v-------------------------------------+  |
|  | BACKEND NETWORK (Internal & Isolated)                                      |  |
|  |                                                                            |  |
|  |   +-------------------------+          +-------------------------+         |  |
|  |   | Flask Backend Instance  |          | Flask Backend Instance  |         |  |
|  |   | Container: app-01       |          | Container: app-02       |         |  |
|  |   | Port: 8080              |          | Port: 8080              |         |  |
|  |   +------------+------------+          +------------+------------+         |  |
|  |                |                                    |                      |  |
|  |                +------------------+-----------------+                      |  |
|  |                                   |                                        |  |
|  |               +-------------------+-------------------+                    |  |
|  |               |                                       |                    |  |
|  |               v                                       v                    |  |
|  |   +-----------------------+               +-----------------------+        |  |
|  |   | PostgreSQL Database   |               | Redis Cache & Counter |        |  |
|  |   | Container: postgres   |               | Container: redis      |        |  |
|  |   | Port: 5432            |               | Port: 6379            |        |  |
|  |   +-----------+-----------+               +-----------------------+        |  |
|  |               |                                                            |  |
|  |               v                                                            |  |
|  |   [ Volume: postgres-data ]                                                |  |
|  +----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+

---

## 2. Network Isolation & Security Boundaries

- **Frontend Network (`frontend`)**:
  - Accessible publicly via the mapped host port (e.g., `8090:80` or `8080:80`).
  - Contains **NGINX** and **Flask app instances** (`app-01`, `app-02`).
- **Backend Network (`backend`)**:
  - Marked as `internal: true` (non-routable to outside network interface).
  - Connects **Flask app instances**, **PostgreSQL**, and **Redis**.
  - **NGINX is strictly excluded** from this network. It cannot bypass application security controls to access PostgreSQL or Redis directly.

---

## 3. Data Flow & Request Lifecycle

1. **HTTP Ingress**: Client sends an HTTP request to `http://localhost:8090/`.
2. **Reverse Proxying**: NGINX receives the request and forwards it to `http://flask_backends` via Round-Robin load balancing.
3. **Failover Execution**: If one Flask backend (`app-01`) becomes unresponsive or fails, NGINX immediately retries the request against `app-02` (`proxy_next_upstream error timeout http_502 http_503 http_504`).
4. **Data Persistence & Caching**:
   - `/records` requests interact with PostgreSQL (`postgres:5432`), persisting data directly to named volume `postgres-data`.
   - `/counter` requests increment atomic counters inside Redis (`redis:6379`).

---

## 4. Health & Readiness Relationships

- **Container Dependencies**:
  - `app-01` and `app-02` wait for `postgres` and `redis` health checks (`condition: service_healthy`) before initiating runtime startup.
  - `nginx` waits for `app-01` and `app-02` readiness.
- **Upstream Passive Probing**:
  - NGINX monitors upstream status using `max_fails=1 fail_timeout=1s`.
  - Application endpoints `/health` (liveness) and `/ready` (dependency readiness) are continuously probed.

---

## 5. Remaining Single Points of Failure (SPOF)

While application instances (`app-01` and `app-02`) feature full High Availability and zero-downtime failover, the following single points of failure exist in this single-node topology:

1. **NGINX Load Balancer**: A single NGINX container acts as the ingress controller. If NGINX crashes, incoming traffic cannot reach any application backend.
   - *Mitigation in Production*: Deploy multiple ingress proxies behind a Virtual IP (Keepalived/VRRP) or AWS ALB/Cloudflare.
2. **PostgreSQL Database Server**: A single PostgreSQL instance processes database queries.
   - *Mitigation in Production*: Implement PostgreSQL Primary-Standby streaming replication with automatic failover (Patroni / Pgpool-II).
3. **Redis Cache Instance**: Single instance Redis deployment.
   - *Mitigation in Production*: Upgrade to Redis Sentinel or a multi-node Redis Cluster.
4. **Single Host Machine / Docker Daemon**: A failure of the physical host or Docker daemon halts all containers.
   - *Mitigation in Production*: Deploy across multi-AZ Kubernetes (EKS/GKE) clusters with Pod Anti-Affinity rules.