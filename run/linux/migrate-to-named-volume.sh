#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../.."
VOLUME_NAME="${PALWORLD_VOLUME_NAME:-palworld-data}"
SOURCE_DIR="${1:-./palworld}"
BACKUP_DIR="./migration-backups"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "ไม่พบโฟลเดอร์เดิม: $SOURCE_DIR"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/palworld-bind-$STAMP.tar.gz"

echo "Stopping compose stack..."
docker compose --profile admin down

echo "Creating backup: $BACKUP_FILE"
tar -czf "$BACKUP_FILE" -C "$SOURCE_DIR" .

docker volume create "$VOLUME_NAME" >/dev/null
COUNT="$(docker run --rm -v "$VOLUME_NAME:/target" alpine:3.20 sh -c 'find /target -mindepth 1 -maxdepth 1 | wc -l')"
if [ "$COUNT" -gt 0 ] && [ "${FORCE_MIGRATE:-false}" != "true" ]; then
  echo "Named volume $VOLUME_NAME ไม่ว่าง ยกเลิกเพื่อป้องกันข้อมูลทับ"
  echo "ตั้ง FORCE_MIGRATE=true เฉพาะเมื่อยืนยันว่าต้องการเขียนทับ"
  exit 1
fi

if [ "$COUNT" -gt 0 ]; then
  docker run --rm -v "$VOLUME_NAME:/target" alpine:3.20 sh -c 'rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true'
fi

echo "Copying data into named volume $VOLUME_NAME..."
docker run --rm -v "$(pwd)/${SOURCE_DIR#./}:/source:ro" -v "$VOLUME_NAME:/target" alpine:3.20 sh -c 'cp -a /source/. /target/'

echo "Migration complete. Backup: $BACKUP_FILE"
echo "Start with: docker compose --profile admin up -d --build"
