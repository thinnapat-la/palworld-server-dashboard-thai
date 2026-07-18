#!/bin/sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT" || exit 1
ACTION=${1:-help}
ENV_FILE="$ROOT/.env"

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

need_docker() {
  command -v docker >/dev/null 2>&1 || fail "ไม่พบ Docker CLI"
  docker info >/dev/null 2>&1 || fail "Docker Desktop ยังไม่พร้อม กรุณาเปิด Docker Desktop"
  docker compose version >/dev/null 2>&1 || fail "ไม่พบ Docker Compose plugin"
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    printf 'สร้าง .env แล้ว กรุณาแก้รหัสผ่านใน TextEdit จากนั้น Save และปิดหน้าต่าง\n'
    if command -v open >/dev/null 2>&1; then
      open -W -a TextEdit "$ENV_FILE" || true
    fi
  fi
}

validate_env() {
  ensure_env
  if grep -Eq '^(PALWORLD_SERVER_PASSWORD|PALWORLD_ADMIN_PASSWORD|DASHBOARD_PASSWORD)=.*CHANGE_ME' "$ENV_FILE"; then
    fail "กรุณาแก้ PALWORLD_SERVER_PASSWORD, PALWORLD_ADMIN_PASSWORD และ DASHBOARD_PASSWORD ใน .env ก่อน"
  fi
}

set_env_value() {
  key=$1
  value=$2
  tmp="$ENV_FILE.tmp"
  awk -v key="$key" -v value="$value" '
    BEGIN { found=0 }
    $0 ~ "^" key "=" { print key "=" value; found=1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
}

wait_palworld_healthy() {
  timeout=${1:-900}
  elapsed=0
  printf 'Waiting for Palworld container health...\n'
  while [ "$elapsed" -lt "$timeout" ]; do
    status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' palworld-server 2>/dev/null || true)
    case "$status" in
      healthy|running)
        printf 'Palworld status: %s\n' "$status"
        return 0
        ;;
      exited|dead)
        docker compose logs --tail=100 palworld || true
        fail "Palworld container หยุดระหว่างเริ่มระบบ"
        ;;
    esac
    sleep 5
    elapsed=$((elapsed + 5))
  done
  docker compose logs --tail=100 palworld || true
  fail "Palworld ยังไม่พร้อมภายใน $timeout วินาที"
}

wait_dashboard() {
  port=$(awk -F= '$1=="DASHBOARD_PORT" {print $2}' "$ENV_FILE" | tail -n 1)
  port=${port:-8080}
  count=0
  while [ "$count" -lt 60 ]; do
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      printf 'Dashboard online: http://127.0.0.1:%s\n' "$port"
      return 0
    fi
    count=$((count + 1))
    sleep 2
  done
  fail "Dashboard healthcheck ไม่พร้อมที่ port $port"
}

case "$ACTION" in
  setup)
    need_docker
    validate_env
    set_env_value PALWORLD_UPDATE_ON_BOOT true
    PALWORLD_UPDATE_ON_BOOT=true docker compose up -d --force-recreate palworld || fail "เริ่มติดตั้ง Palworld ไม่สำเร็จ"
    wait_palworld_healthy 900
    set_env_value PALWORLD_UPDATE_ON_BOOT false
    docker compose up -d --no-deps --force-recreate palworld || fail "Recreate หลังติดตั้งไม่สำเร็จ"
    wait_palworld_healthy 900
    printf '\nSetup complete. Run 01-Start-All.command\n'
    ;;
  start-all)
    need_docker
    validate_env
    docker compose --profile admin up -d --build || fail "เปิดบริการไม่สำเร็จ"
    wait_dashboard
    port=$(awk -F= '$1=="DASHBOARD_PORT" {print $2}' "$ENV_FILE" | tail -n 1)
    port=${port:-8080}
    open "http://127.0.0.1:$port" 2>/dev/null || true
    ;;
  start-server)
    need_docker
    validate_env
    docker compose up -d palworld || fail "เปิด Palworld ไม่สำเร็จ"
    ;;
  start-dashboard)
    need_docker
    validate_env
    docker compose --profile admin up -d --no-deps --build docker-proxy dashboard || fail "เปิด Dashboard ไม่สำเร็จ"
    wait_dashboard
    ;;
  status)
    need_docker
    ensure_env
    docker compose --profile admin ps
    ;;
  logs)
    need_docker
    ensure_env
    docker compose --profile admin logs -f --tail=200
    ;;
  update)
    need_docker
    validate_env
    PALWORLD_UPDATE_ON_BOOT=true docker compose up -d --no-deps --force-recreate palworld || fail "เริ่มอัปเดตไม่สำเร็จ"
    wait_palworld_healthy 900
    set_env_value PALWORLD_UPDATE_ON_BOOT false
    docker compose up -d --no-deps --force-recreate palworld || fail "Recreate หลังอัปเดตไม่สำเร็จ"
    wait_palworld_healthy 900
    ;;
  stop-all)
    need_docker
    ensure_env
    docker compose --profile admin down || fail "ปิดบริการไม่สำเร็จ"
    ;;
  doctor)
    need_docker
    validate_env
    docker compose config >/dev/null || fail "Compose config ไม่ถูกต้อง"
    printf '[OK] Docker และ Compose\n'
    docker compose --profile admin ps
    volume_name=$(awk -F= '$1=="PALWORLD_VOLUME_NAME" {print $2}' "$ENV_FILE" | tail -n 1)
    volume_name=${volume_name:-palworld-data}
    if docker volume inspect "$volume_name" >/dev/null 2>&1; then
      printf '[OK] พบ Named Volume ของ Compose\n'
    else
      printf '[INFO] Named Volume จะถูกสร้างเมื่อ Start ครั้งแรก\n'
    fi
    printf '[INFO] macOS ใช้ Linux Palworld container; Dashboard Export/Import ใช้ Named Volume เดียวกัน\n'
    ;;
  *)
    cat <<'HELP'
Usage: run/macos/palworld.command ACTION

Actions:
  setup          สร้าง .env และเริ่มติดตั้งครั้งแรก
  start-all      เปิด Palworld + Dashboard
  start-server   เปิดเฉพาะ Palworld
  start-dashboard เปิดเฉพาะ Dashboard
  status         ดูสถานะ
  logs           ดู Log แบบต่อเนื่อง
  update         อัปเดตเกมและ Recreate กลับสู่โหมดปกติอัตโนมัติ
  stop-all       ปิดทุกบริการ
  doctor         ตรวจ Docker/Compose/Config
HELP
    ;;
esac
