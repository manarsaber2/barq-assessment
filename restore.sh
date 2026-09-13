#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-./backups/latest.sql}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "[FAIL] Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

echo "[INFO] Restoring PostgreSQL database from: ${BACKUP_FILE}..."

POSTGRES_USER="barq_app"
POSTGRES_DB="barq_tasks"
POSTGRES_PASSWORD="BarqLabOnly_7qN2vK8c"

# Clean existing table data before restoring to prevent primary key conflicts
docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "DROP TABLE IF EXISTS records CASCADE;" > /dev/null 2>&1

cat "${BACKUP_FILE}" | docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null

echo "[PASS] Database restore completed successfully!"