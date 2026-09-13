#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting PostgreSQL database backup..."

POSTGRES_USER="barq_app"
POSTGRES_DB="barq_tasks"
POSTGRES_PASSWORD="BarqLabOnly_7qN2vK8c"

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > "${BACKUP_FILE}"

if [ -s "${BACKUP_FILE}" ]; then
  echo "[PASS] Backup successfully created at: ${BACKUP_FILE}"
  ln -sf "postgres_backup_${TIMESTAMP}.sql" "${BACKUP_DIR}/latest.sql"
else
  echo "[FAIL] Backup file is empty or failed to generate!"
  exit 1
fi