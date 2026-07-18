# Config Reference 1.1.0

เอกสารอ้างอิงตัวแปรที่ผู้ดูแลแก้บ่อย แยกตามโหมดและอธิบายผลกระทบ/เวลาที่ต้อง Restart หรือ Recreate

---

## 1. หลักการ

| ประเภทการเปลี่ยน | ต้องทำอะไร |
|---|---|
| Dashboard credential/resource | Recreate Dashboard |
| Docker Compose environment ของ Palworld | Recreate `palworld` |
| Gameplay Config ผ่าน Dashboard | Restart Server สำหรับค่าที่อ่านตอน boot |
| Windows `.env.host` startup args | Restart Windows Server |
| Windows Admin/REST/RCON/Port | Start/Restart ซึ่งจะ Patch Config |
| Volume name/path | Stop stack และตรวจ data ก่อน Start |

---

## 2. `.env` — Linux/macOS Docker mode

### Lifecycle

| ตัวแปร | Default | ความหมาย |
|---|---|---|
| `PALWORLD_UPDATE_ON_BOOT` | `false` | เปิด SteamCMD update ตอน container start |
| `PALWORLD_DISABLE_GENERATE_SETTINGS` | `false` | ห้าม image generate `PalWorldSettings.ini` |
| `BACKUP_ENABLED` | `true` | Auto backup ของ image |
| `AUTO_REBOOT_ENABLED` | `false` | Auto reboot ของ image |
| `ENABLE_PLAYER_LOGGING` | `false` | Poll player join/leave helper |
| `LOG_FILTER_ENABLED` | `false` | Python log formatter `pal_logger.py` |

### Credentials

| ตัวแปร | Default | ความหมาย |
|---|---|---|
| `PALWORLD_SERVER_PASSWORD` | ต้องแก้ | รหัสเข้าเกม |
| `PALWORLD_ADMIN_PASSWORD` | ต้องแก้ | REST/RCON admin |
| `DASHBOARD_USERNAME` | `admin` | Dashboard user |
| `DASHBOARD_PASSWORD` | ต้องแก้ | Dashboard password |

### Feature

| ตัวแปร | Default | ความหมาย |
|---|---|---|
| `ENABLE_GAMEDATA_API` | `false` | เปิด World Actor Snapshot/GameData API |
| `DISCORD_SERVER_NOTIFICATIONS_ENABLED` | `false` | Notification จาก image |
| `DISCORD_PLAYER_NOTIFICATIONS_ENABLED` | `false` | Player notification จาก image |
| `DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED` | `false` | Maintenance notification จาก Dashboard |
| `PLAYER_LOGGING_POLL_PERIOD` | `60` | รอบ player logger เมื่อเปิด |

### Dashboard

| ตัวแปร | Default | ความหมาย |
|---|---|---|
| `DASHBOARD_BIND_ADDRESS` | `0.0.0.0` | Interface ที่ publish Dashboard |
| `DASHBOARD_PORT` | `8080` | Host port |
| `DASHBOARD_REFRESH_SECONDS` | `30` | Poll interval ของหน้าเว็บ |
| `DASHBOARD_ACTIONS_ENABLED` | `true` | เปิดปุ่มที่แก้ runtime/config |

### Resource

| ตัวแปร | Default |
|---|---|
| `PALWORLD_MEMORY_RESERVATION` | `8g` |
| `DASHBOARD_CPU_LIMIT` | `0.25` |
| `DASHBOARD_MEMORY_LIMIT` | `256m` |
| `DASHBOARD_MEMORY_RESERVATION` | `128m` |
| `DASHBOARD_PIDS_LIMIT` | `128` |
| `DOCKER_PROXY_CPU_LIMIT` | `0.10` |
| `DOCKER_PROXY_MEMORY_LIMIT` | `64m` |
| `DOCKER_PROXY_MEMORY_RESERVATION` | `32m` |
| `DOCKER_PROXY_PIDS_LIMIT` | `64` |

### Storage and limits

| ตัวแปร | Default | ความหมาย |
|---|---|---|
| `PALWORLD_VOLUME_NAME` | `palworld-data` | Named Volume |
| `DOCKER_LOG_MAX_SIZE` | `20m` | Log segment |
| `DOCKER_LOG_MAX_FILE` | `3` | จำนวน segment |
| `DASHBOARD_MAX_UPLOAD_MB` | `4096` | ZIP upload |
| `DASHBOARD_MAX_EXPANDED_MB` | `8192` | Expanded import |
| `DASHBOARD_MAX_CONFIG_KB` | `1024` | Config editor size |
| `DASHBOARD_MAX_CONFIG_BACKUPS` | `100` | Config backup retention |
| `PALWORLD_START_TIMEOUT_SECONDS` | `900` | รอ REST หลัง Start |
| `PALWORLD_STOP_TIMEOUT_SECONDS` | `60` | รอ Stop |

---

## 3. `.env.host` — Windows Host-native

### Host directory

| ตัวแปร | Default | หมายเหตุ |
|---|---|---|
| `PALWORLD_HOST_DIR` | `<ProjectDrive>:/PalServer` | ต้อง path สั้น |
| `PALWORLD_HOST_SHORT_DIR` | ว่าง | Destination ของ relocate command |

### Server identity/network

| ตัวแปร | Default |
|---|---|
| `PALWORLD_SERVER_NAME` | `Mien Palworld Windows` |
| `PALWORLD_SERVER_PASSWORD` | ว่าง |
| `PALWORLD_ADMIN_PASSWORD` | ต้องแก้ |
| `PALWORLD_HOST_PORT` | `8211` |
| `PALWORLD_HOST_QUERY_PORT` | `27015` |
| `PALWORLD_HOST_REST_PORT` | `8212` |
| `PALWORLD_HOST_RCON_PORT` | `25575` |
| `PALWORLD_HOST_PUBLIC_LOBBY` | `true` |
| `PALWORLD_HOST_API_HOST` | `host.docker.internal` |

### Native SteamCMD

| ตัวแปร | Default |
|---|---|
| `PALWORLD_STEAMCMD_DOWNLOAD_URL` | Valve installer URL |
| `PALWORLD_STEAMCMD_VALIDATE` | `true` |
| `PALWORLD_STEAMCMD_RETRIES` | `2` |

`validate=true` ใช้เวลานานกว่าแต่ตรวจไฟล์ เหมาะกับ Setup และการแก้ไฟล์เสีย

### Startup

| ตัวแปร | Default | ผล |
|---|---|---|
| `PALWORLD_HOST_PERF_ARGS` | `false` | เพิ่ม 3 performance args |
| `PALWORLD_HOST_WORKER_THREADS` | ว่าง | เพิ่ม `-NumberOfWorkerThreadsServer=N` |
| `PALWORLD_HOST_EXTRA_ARGS` | ว่าง | Argument เพิ่มเติม |
| `PALWORLD_HOST_STOP_TIMEOUT_SECONDS` | `60` | Agent รอก่อน fallback taskkill |
| `PALWORLD_HOST_START_TIMEOUT_SECONDS` | `900` | Manager รอ REST |
| `PALWORLD_EXTERNAL_CONTROL_TIMEOUT` | `90` | Dashboard/manager รอ Agent response |
| `PALWORLD_HOST_AUTO_OPEN_DASHBOARD` | `true` | เปิด browser หลัง Start All |

### Dashboard/resource/import

ใช้ชื่อและ default เดียวกับ `.env` ยกเว้นไม่มี Docker Proxy resource เพราะ Windows compose ไม่มี proxy service

---

### Import mode API

`POST /api/maintenance/import` รองรับค่า:

| `import_mode` | ความหมาย |
|---|---|
| `world_only` | แทนที่เฉพาะ `SaveGames`; เป็นค่าเริ่มต้นและเหมาะกับการสลับ Server |
| `full_restore` | แทนที่ `Pal/Saved` ทั้งชุด |
| `config_only` | แทนที่ Config ของ platform ปลายทางเท่านั้น |

`GET /api/version` ส่งคืน `runtime_mode`, `target_config_platform` และรายการ `import_modes` ส่วน Upload API ส่งคืนโหมดที่ archive รองรับ


## 4. `docker-compose.yml` Gameplay settings

Compose มี environment จำนวนมากที่ map ไป `PalWorldSettings.ini` เช่น:

- Difficulty/rates
- Player/Pal stats
- Building/base limits
- PvP
- Death penalty
- Auto save
- Server visibility/auth
- Voice chat
- Global Palbox

เมื่อ `PALWORLD_DISABLE_GENERATE_SETTINGS=false` ค่าเหล่านี้อาจถูกเขียนลง Config ตอน start

เมื่อใช้ Dashboard เป็นหลัก ให้ตั้ง `true` และจัดการ Gameplay ในไฟล์ Config

---

## 5. Engine/Network tuning ใน Docker mode

| Key | Current |
|---|---:|
| `LAN_SERVER_MAX_TICK_RATE` | 60 |
| `NET_SERVER_MAX_TICK_RATE` | 60 |
| `NET_CLIENT_TICKS_PER_SECOND` | 60 |
| `SMOOTH_FRAME_RATE` | true |
| `SMOOTH_FRAME_RATE_LOWER_LIMIT` | 30 |
| `SMOOTH_FRAME_RATE_UPPER_LIMIT` | 60 |
| `USE_FIXED_FRAME_RATE` | false |
| `FIXED_FRAME_RATE` | 60 |
| `MIN_DESIRED_FRAME_RATE` | 30 |
| `CONFIGURED_INTERNET_SPEED` | 104857600 |
| `CONFIGURED_LAN_SPEED` | 104857600 |
| `MAX_CLIENT_RATE` | 104857600 |
| `MAX_INTERNET_CLIENT_RATE` | 104857600 |

แก้ใน Compose แล้ว Recreate `palworld`

---

## 6. Password synchronization

### Docker

```text
.env PALWORLD_ADMIN_PASSWORD
=
PalWorldSettings.ini AdminPassword
=
Dashboard PALWORLD_ADMIN_PASSWORD environment
```

### Windows

`.env.host` เป็น source of truth และ patcher เขียน `AdminPassword` ทุก Start/Update/Doctor

---

## 7. Recommended production baseline

### Linux

```dotenv
PALWORLD_UPDATE_ON_BOOT=false
PALWORLD_DISABLE_GENERATE_SETTINGS=true
LOG_FILTER_ENABLED=false
ENABLE_PLAYER_LOGGING=false
ENABLE_GAMEDATA_API=false
AUTO_REBOOT_ENABLED=false
DASHBOARD_REFRESH_SECONDS=30
```

เปิด feature เพิ่มเมื่อมีเหตุผลและตรวจ resource/log หลังเปลี่ยน

### Windows

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
PALWORLD_HOST_PERF_ARGS=false
PALWORLD_HOST_WORKER_THREADS=
PALWORLD_HOST_EXTRA_ARGS=
PALWORLD_STEAMCMD_VALIDATE=true
```
