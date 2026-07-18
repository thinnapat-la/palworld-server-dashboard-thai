#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../.."
export PALWORLD_UPDATE_ON_BOOT=true
docker compose up -d palworld
echo "ติดตามการติดตั้งด้วย: docker compose logs -f --tail=200 palworld"
echo "หลังติดตั้งเสร็จ ตั้ง PALWORLD_UPDATE_ON_BOOT=false ใน .env"
