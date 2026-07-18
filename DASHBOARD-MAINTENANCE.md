# Dashboard และ Maintenance Guide 1.1.0

เอกสารสำหรับเข้าใจ Dashboard API, Runtime control, Config editor, Export/Import และไฟล์ข้อมูลภายใน

---

## 1. Runtime modes

### Docker mode

```text
PALWORLD_RUNTIME_MODE=docker
```

Dashboard ใช้:

- REST API สำหรับ info/metrics/players/settings/actions
- Docker socket proxy สำหรับ container start/stop/status
- Named Volume สำหรับ Config/Save

### External mode

```text
PALWORLD_RUNTIME_MODE=external
```

ใช้ใน Windows Host-native:

- REST API ผ่าน `host.docker.internal`
- Shared control files สำหรับ Start/Stop
- Host directory mount สำหรับ Config/Save

---

## 2. Authentication

หน้าเว็บใช้ HTTP Basic Authentication จาก:

```dotenv
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=...
```

Palworld REST ใช้ Basic Auth:

```text
admin:<PALWORLD_ADMIN_PASSWORD>
```

อย่าสับสนสองชุดนี้

---

## 3. Dashboard data directories

ภายใน container:

```text
/data
```

Host:

```text
dashboard/data
```

ประกอบด้วยโดยประมาณ:

```text
config-backups/
exports/
imports/
staging/
jobs.json
bans.json
maintenance.json
```

ชื่อบางไฟล์สร้างเมื่อใช้งานครั้งแรก

---

## 4. Server snapshot

Dashboard poll Palworld REST endpoints เช่น:

- `/v1/api/info`
- `/v1/api/metrics`
- `/v1/api/players`
- `/v1/api/settings`

รอบ poll จาก:

```dotenv
DASHBOARD_REFRESH_SECONDS=30
```

การ Refresh UI ไม่ได้เปลี่ยน server tick แต่เพิ่ม request และ log ของ REST

---

## 5. Player actions

รองรับ:

- Announce
- Save
- Kick
- Ban
- Unban
- Shutdown/Stop

ประวัติ Ban/Kick/Unban เก็บใน Dashboard data ไม่ใช่แหล่ง ban ทั้งหมดของเกม จึงแสดงเฉพาะคำสั่งที่ผ่าน Dashboard

Dashboard พยายาม Save World ก่อน Kick/Ban ตาม workflow และบันทึกผล action กับผล save แยกกัน

---

## 6. Config editor

### Raw editor

- อ่านไฟล์ Config จาก `PALWORLD_CONFIG_FILE`
- Validate โครงสร้าง
- จำกัดขนาด `DASHBOARD_MAX_CONFIG_KB`
- Backup ก่อนเขียน

### Settings form

- Parse `OptionSettings=(...)`
- แสดง current value
- Patch key ที่เลือก
- ตรวจ SHA-256 เพื่อลด lost update

### Backup retention

```dotenv
DASHBOARD_MAX_CONFIG_BACKUPS=100
```

ไฟล์เก่าเกิน limit จะถูกลบตามเวลาที่แก้ไข

---

## 7. Job scheduler

ประเภท job:

```text
restart
export
import
```

สถานะหลัก:

```text
pending
running
completed
failed
cancelled
```

Stage อาจประกอบด้วย:

```text
waiting
warning
saving
stopping
exporting
safety_backup
extracting
replacing
starting
waiting_server
completed
rollback
failed
```

ชื่อ stage เป็น implementation detail และอาจเปลี่ยนได้ ควรดู `jobs.json` และ Dashboard UI ร่วมกัน

---

## 8. Restart workflow

```text
queue
-> wait schedule
-> announce warning
-> Save World
-> Stop runtime
-> Start runtime
-> wait REST API
-> complete
```

ถ้า Save World ล้ม ระบบยังพยายาม graceful runtime stop และบันทึก warning

---

## 9. Export workflow

```text
queue
-> announce/save
-> stop runtime
-> zip Pal/Saved
-> start runtime
-> wait REST
-> expose download
```

Archive มี:

```text
dashboard-export-manifest.json
Pal/Saved/...
```

Manifest มี metadata เช่น format, version, created time และ job id

---

## 10. Import workflow

Request body ของ `POST /api/maintenance/import` รับ:

```json
{
  "filename": "palworld-export-....zip",
  "import_mode": "world_only",
  "warning_seconds": 300,
  "message": "Server maintenance",
  "scheduled_at": null
}
```

ค่า `import_mode`:

| ค่า | Source จาก staging | Target ปลายทาง |
|---|---|---|
| `world_only` | `Pal/Saved/SaveGames` | `Pal/Saved/SaveGames` |
| `full_restore` | `Pal/Saved` | `Pal/Saved` |
| `config_only` | `Pal/Saved/Config/<target-platform>` | `Pal/Saved/Config/<target-platform>` |

Target platform ถูกเลือกจาก Runtime:

- `PALWORLD_RUNTIME_MODE=external` → `WindowsServer`
- `PALWORLD_RUNTIME_MODE=docker` → `LinuxServer`

```text
upload
-> validate archive and discover available paths
-> queue with import_mode
-> announce/save
-> stop runtime
-> create full safety export
-> extract to staging
-> move current target to rollback path
-> replace selected target only
-> start runtime
-> wait REST
-> cleanup or rollback selected target
```

Temporary paths ใช้ชื่อประมาณ:

```text
.dashboard-rollback-<mode>-<job-id>
.dashboard-failed-import-<mode>-<job-id>
```

### ZIP validation

ระบบปฏิเสธ:

- Absolute path
- `..` traversal
- Symlink-like unsafe entry
- Root file/directory ที่ไม่อนุญาต
- Expanded size เกิน limit
- Archive ไม่มี `Pal/Saved`
- `world_only` แต่ไม่มี `Pal/Saved/SaveGames`
- `config_only` แต่ไม่มี Config ของ platform ปลายทาง

Upload response จะรายงาน `supported_import_modes`, `config_platforms`, `target_config_platform` และ `recommended_import_mode` เพื่อให้ UI เลือกโหมดที่ปลอดภัยเป็นค่าเริ่มต้น

---

## 11. Runtime Start/Stop buttons

### Start

- ตรวจไม่มี Maintenance job active
- ตรวจ runtime status
- Start ผ่าน Docker API หรือ external control

### Stop

- ตรวจไม่มี Maintenance job active
- พยายาม Save World
- พยายาม REST shutdown
- หยุด runtime ผ่าน controller
- แสดง Save failure แยกจาก Stop result

---

## 12. Discord

Dashboard notification switch:

```dotenv
DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED=false
DISCORD_INFORMATION_WEBHOOK_URL=
```

Docker Palworld image notification switches แยกต่างหาก:

```dotenv
DISCORD_SERVER_NOTIFICATIONS_ENABLED=false
DISCORD_PLAYER_NOTIFICATIONS_ENABLED=false
```

ปิด master switch จะไม่ส่ง request แม้ URL ยังอยู่ใน env

---

## 13. Health and logs

Dashboard health:

```text
GET /health
```

Docker logs:

Linux/macOS:

```bash
docker compose --profile admin logs -f --tail=200 dashboard
```

Windows:

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin logs -f --tail=200 dashboard-host
```

---

## 14. Recreate Dashboard safely

Linux/macOS:

```bash
docker compose --profile admin up -d --no-deps --build --force-recreate docker-proxy dashboard
```

Windows:

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin up -d --no-deps --build --force-recreate dashboard-host
```

`--no-deps` ป้องกันไม่ให้คำสั่งลาก runtime อื่นมาทำงานโดยไม่ตั้งใจ

---

## 15. Capacity planning

Import ต้องมีพื้นที่สำหรับพร้อมกัน:

- ZIP upload
- Expanded staging
- Current World
- Safety backup ZIP
- Failed/rollback copy ชั่วคราว

แนะนำพื้นที่ว่างอย่างน้อย 2-3 เท่าของขนาด `Pal/Saved` ก่อน Import ใหญ่

---

## 16. Recovery

### Job ค้างหลัง Dashboard restart

ตรวจ:

```text
dashboard/data/jobs.json
dashboard/data/maintenance.json
```

อย่าลบไฟล์ทันที ให้สำรองก่อนและตรวจ runtime/world state

### Export สำเร็จแต่ Server ไม่กลับ

- ตรวจ runtime controller
- Start runtime ด้วยปุ่มหรือสคริปต์
- ตรวจ REST password
- ตรวจ job error

### Import failed

- ห้าม Upload/Import ซ้ำทันที
- ตรวจ Safety backup ใน exports
- ตรวจ staging/failed import
- ตรวจพื้นที่และ permission


### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว
