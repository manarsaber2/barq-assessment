Markdown
# BARQ Systems - DevOps Assessment Project



## 1. Prerequisites & Setup

Ensure Python 3.12+, Docker, Docker Compose, and Git are installed on your environment (WSL2 / Linux).

# Clone and prepare environment file
cp .env.example .env

# Create and activate virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Linux/WSL: source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
2. Build & Launch Environment
Bash
# Build and bring up all containers in detached mode
docker compose -p barq-assessment up --build -d

# Verify container statuses and active ports
docker compose -p barq-assessment ps -a
3. Testing & Validation
Bash
# Run unit tests
python -m unittest discover -s tests -v

# Run automated system validation suite
python validate.py

# Verify live endpoints
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
curl -s http://localhost:8080/instance
4. Failure & Resilience Testing
Bash
# Execute automated failover and network isolation tests
python failure_test.py
5. Database Backup & Restore
Bash
# Ensure scripts are executable
chmod +x backup.sh restore.sh

# Run database backup
./backup.sh

# Run database restore verification
./restore.sh
6. Cleanup
Bash
# Stop containers without removing volumes (preserves data)
docker compose -p barq-assessment down

# Full teardown including volumes (destructive)
docker compose -p barq-assessment down -v