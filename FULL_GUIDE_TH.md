# คู่มือเชิงลึก Palworld Server Dashboard Thai 1.1.0

เอกสารนี้อธิบายการทำงานเชิงระบบสำหรับผู้ดูแลที่ต้องปรับแต่ง ตรวจสอบ และแก้ปัญหาเกินกว่าขั้นตอน Quick start ใน `README.md`

---

## 1. ภาพรวมสถาปัตยกรรม

แพ็กเกจแบ่งออกเป็น 4 ส่วน:

1. **Palworld runtime** — Docker container หรือ Windows `PalServer.exe`
2. **Dashboard API/UI** — Python HTTP server ใน container
3. **Runtime controller** — Docker socket proxy หรือ Windows Host Agent
4. **Persistent data** — Named Volume, Windows Host directory และ `dashboard/data`

### Linux/macOS

```text
Browser
  -> Dashboard container
      -> Palworld REST API ผ่าน Docker network
      -> Docker socket proxy สำหรับ lifecycle
      -> palworld-data volume สำหรับ Config/Save/Import/Export
  -> Palworld Linux container
```

### Windows

```text
Browser
  -> Dashboard container
      -> host.docker.internal:8212 -> PalServer.exe REST API
      -> runtime/control -> PowerShell Host Agent -> PalServer.exe lifecycle
      -> D:/PalServer mount -> Config/Save/Import/Export
```

---

## 2. Config precedence และ source of truth

### Docker mode

มี Config 3 ชั้น:

1. `.env` — secret, feature toggle, resource และ lifecycle
2. `docker-compose.yml` — game settings และ Engine tuning ที่ส่งให้อิมเมจ
3. `PalWorldSettings.ini` — ไฟล์ที่เกมอ่านจริง

เมื่อ `PALWORLD_DISABLE_GENERATE_SETTINGS=false` อิมเมจสามารถสร้าง/เขียนไฟล์จาก environment ใหม่ได้ จึงควรใช้เฉพาะ First boot หรือเมื่อจงใจให้ Compose เป็น source of truth

เมื่อเริ่มแก้ Gameplay ผ่าน Dashboard ให้ตั้ง:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

จากนั้น `PalWorldSettings.ini` จะเป็น source of truth สำหรับ Gameplay

Engine tuning ยังมาจาก environment ใน Compose และต้อง Recreate container เมื่อแก้

### Windows mode

`.env.host` เป็น source of truth สำหรับ:

- Server name/password
- Admin password
- Gameplay port
- REST port
- RCON port
- Public lobby startup flag
- Startup performance args
- Dashboard credentials/resources

`Configure-PalworldHost.ps1` Patch ค่า REST/RCON/Admin และข้อมูลหลักลง `PalWorldSettings.ini` ทุกครั้งที่ Setup/Start/Update/Restart/Doctor

Gameplay key อื่นยังแก้ผ่าน Dashboard ได้และจะไม่ถูก Patch เว้นแต่ชื่อ key ตรงกับรายการข้างต้น

---

## 3. Runtime lifecycle

### Docker runtime

- Start: Docker API start หรือ `docker compose up`
- Stop จาก Dashboard: REST Save/Shutdown แล้วรอ container หยุด
- Restart job: announce → save → stop → start → wait REST
- Compose stop/down: จัดการโดย Docker และ image stop handler

### Windows runtime

Host Agent รัน PowerShell แบบ background และเขียน heartbeat ที่:

```text
runtime/control/status.json
```

Dashboard สร้าง request:

```text
runtime/control/request-<id>.json
```

Agent ตอบ:

```text
runtime/control/response-<id>.json
```

Dashboard workflow จะเรียก REST Save/Shutdown ก่อน request `stop` ส่วนคำสั่ง manager ตรงจะ request Agent โดยตรงและอาจใช้ `taskkill /T /F` เมื่อ process ไม่ออกใน timeout

---

## 4. First boot lifecycle

### Linux/macOS

1. สร้าง `.env`
2. เปิด `UPDATE_ON_BOOT=true`
3. Start `palworld`
4. SteamCMD ติดตั้งเกมใน Named Volume
5. เกมสร้าง Config/Save directories
6. ปิด `UPDATE_ON_BOOT`
7. Recreate container
8. เปิด Dashboard

### Windows

1. สร้าง `.env.host`
2. เลือก Host directory แบบสั้น
3. ดาวน์โหลด Native SteamCMD
4. `app_update 2394010`
5. Copy `DefaultPalWorldSettings.ini` เป็น Windows config
6. Patch REST/RCON/Admin
7. Start Host Agent และ PalServer
8. Wait REST
9. Start Dashboard และทดสอบ cross-boundary REST

---

## 5. Persistent data

### Docker Named Volume

`palworld-data` เก็บ:

- Game binary
- Config
- World Save
- Server backups
- Logs ภายใน volume

การลบ container หรือ `docker compose down` ไม่ลบ volume แต่ `down -v` ลบได้

### Dashboard data

`dashboard/data` เป็น bind mount ของโปรเจกต์ เก็บ:

- Import ZIP
- Export ZIP
- Jobs/history
- Config backups
- Ban/Kick/Unban history
- Maintenance marker

ควรสำรอง directory นี้พร้อม World หากต้องการรักษาประวัติงาน

### Windows Host directory

เก็บทั้ง binary และ World ใน path เดียว เช่น:

```text
D:/PalServer
```

Dashboard mount directory นี้เข้าคอนเทนเนอร์เป็น `/palworld-data`

---

## 6. Export/Import internals

### Export

- Input: `/palworld-data/Pal/Saved`
- Output: `dashboard/data/exports/*.zip`
- Manifest: `dashboard-export-manifest.json`
- Root ที่อนุญาตใน archive: `Pal/Saved/`

### Import validation

ระบบตรวจ:

- ชื่อ ZIP และ path traversal
- จำนวน/ขนาด expanded files
- โครงสร้าง archive
- ต้องไม่มี root อื่นนอก manifest และ `Pal/Saved`

### Import modes และ transaction

Dashboard มี 3 โหมด:

- `world_only`: แทนที่ `Pal/Saved/SaveGames` เท่านั้น เหมาะกับการสลับ Runtime/OS
- `full_restore`: แทนที่ `Pal/Saved` ทั้งชุด เหมาะกับกู้คืนกลับระบบเดิม
- `config_only`: แทนที่ Config ของ platform ปลายทางเท่านั้น
  - External Windows runtime ใช้ `Config/WindowsServer`
  - Docker Linux/macOS ใช้ `Config/LinuxServer`

Transaction:

1. Validate source และตรวจว่า archive มี path ที่โหมดต้องใช้
2. Save/stop runtime
3. Export safety backup แบบเต็ม `Pal/Saved`
4. Extract staging
5. Move target ปัจจุบันไป rollback directory
6. Move target จาก staging เข้าแทน
7. Start runtime และรอ REST
8. Cleanup เมื่อสำเร็จ
9. Restore เฉพาะ target เดิมเมื่อเกิด failure

`world_only` เป็นค่าเริ่มต้นเพื่อรักษา Config และ Log ของเครื่องปลายทาง ขณะที่ Export ยังคงเก็บ `Pal/Saved` ทั้งชุดเพื่อใช้เป็น Full backup ได้

การมี Safety Backup ไม่แทนที่ off-host backup เพราะ Disk เดียวกันยังเสียพร้อมกันได้

---

## 7. Dashboard Config concurrency

Dashboard อ่าน SHA-256 ของ Config และส่ง `expected_sha256` ตอน Patch settings เพื่อป้องกันการเขียนทับการแก้ไขที่เกิดขึ้นหลังโหลดหน้า

Raw editor มี validation ว่า:

- Content ไม่ว่าง
- อยู่ในขนาดที่กำหนด
- มี section และ `OptionSettings=(...)`

Config backup เก็บใน:

```text
dashboard/data/config-backups/
```

จำนวนสูงสุด:

```dotenv
DASHBOARD_MAX_CONFIG_BACKUPS=100
```

---

## 8. Network boundaries

### Linux/macOS

- Dashboard → Palworld REST ผ่าน Docker network ไม่ผ่าน host port
- Host port 8212 bind ที่ `127.0.0.1` เท่านั้น
- Docker proxy ให้เฉพาะ API ที่จำเป็นกับ Dashboard

### Windows

- PalServer REST listen บน Windows
- Dashboard container เรียกผ่าน `host.docker.internal`
- Windows Firewall ต้องอนุญาต TCP 8212 จาก Docker Desktop/WSL virtual network
- VPN/EDR บางตัวอาจบล็อก traffic แม้ Host เรียก `127.0.0.1` ได้

แยกการทดสอบเป็น:

1. Windows host → `127.0.0.1:8212`
2. Dashboard container → `host.docker.internal:8212`

---

## 9. Security model

### Secrets

ไฟล์ `.env` และ `.env.host` ต้องไม่ commit หรือส่งต่อ เพราะมี Admin password, Dashboard password และอาจมี Discord webhook

### Dashboard exposure

ค่าเริ่มต้น bind `0.0.0.0:8080` ทำให้เข้าจาก LAN ได้ หากใช้เครื่องเดียวให้ตั้ง:

```dotenv
DASHBOARD_BIND_ADDRESS=127.0.0.1
```

### REST/RCON

ไม่ควร forward 8212 และ 25575 ออก Public Internet ใช้ VPN, SSH tunnel หรือ Firewall allowlist แทน

### Docker socket

Dashboard ไม่ mount `/var/run/docker.sock` โดยตรง แต่ผ่าน `tecnativa/docker-socket-proxy` ใน Docker mode

Windows Host mode ไม่มี Docker socket access เพราะ lifecycle ผ่าน shared control directory

---

## 10. Resource and performance model

### Palworld

- Soft memory reservation 8 GB
- ไม่มี hard CPU quota
- ไม่มี hard memory limit
- Performance args เปิดใน Docker mode แต่ Windows default ปิด
- Engine tick/frame default ของแพ็กเกจ 60

### Dashboard

- 0.25 CPU
- 256 MB hard memory
- 128 MB reservation
- PID limit 128

### Docker Proxy

- 0.10 CPU
- 64 MB hard memory
- 32 MB reservation
- PID limit 64

### I/O

Docker mode ใช้ Named Volume เพื่อลด file sharing overhead โดยเฉพาะ Docker Desktop

Windows modeใช้ Native NTFS โดยตรง แต่ต้องใช้ path สั้นและสิทธิ์เขียนครบ

---

## 11. Maintenance operation recommendations

### ก่อน Update

1. ตรวจผู้เล่น
2. Save World
3. Export World
4. เก็บ ZIP นอกเครื่อง
5. Update
6. ตรวจ REST/settings/players

### ก่อน Import

1. ตรวจว่า ZIP มาจากแพ็กเกจนี้
2. ตรวจพื้นที่ว่างอย่างน้อย 2-3 เท่าของ World
3. ไม่มี job อื่นรันอยู่
4. ผู้เล่นออกจาก Server
5. ห้ามปิด Dashboard ระหว่าง Import

### หลัง Config change

- Gameplay setting บางค่า apply ตอน Restart
- `.env`/Compose/Engine ต้อง Recreate container
- `.env.host` startup args ต้อง Restart Windows server
- Dashboard credential/resource ต้อง Recreate Dashboard

---

## 12. Upgrade package safely

1. หยุด runtime อย่างปลอดภัย
2. Export World
3. สำรอง `.env` หรือ `.env.host`
4. สำรอง `dashboard/data`
5. แตกแพ็กเกจใหม่คนละ directory
6. Copy env file และ dashboard data
7. Windows ให้ชี้ `PALWORLD_HOST_DIR` ไป path เดิม
8. Docker mode ให้ใช้ `PALWORLD_VOLUME_NAME` เดิม
9. รัน Doctor/Compose config
10. Start และทดสอบ Export

ห้าม copy Named Volume ด้วยการลากไฟล์จาก Docker Desktop UI ระหว่าง container ทำงาน

---

## 13. Recovery scenarios

### Dashboard หาย แต่เกมยังรัน

- Docker mode: Recreate dashboard/proxy ด้วย `--no-deps`
- Windows: Start `dashboard-host` ใหม่ ไม่ต้องหยุด `PalServer.exe`

### Host Agent หาย แต่เกมยังรัน

Windows Dashboard ยังอ่าน REST ได้ แต่ Start/Stop/Import/Export ที่ต้องควบคุม process จะล้ม ให้รัน:

```text
run\windows\02-Start-Server.bat
```

คำสั่งนี้เปิด Agent และจะไม่เปิด Server ซ้ำหาก process มีอยู่แล้ว

### Import ล้ม

ตรวจ:

- Job record
- Export safety backup
- `.dashboard-failed-import-*` ใน Palworld data
- Dashboard log
- Disk space/permission

---

## 14. เอกสารต่อเนื่อง

- `CONFIG-REFERENCE-TH.md` — ตัวแปรและ precedence
- `ARCHITECTURE-TH.md` — control/data flow
- `DASHBOARD-MAINTENANCE.md` — job stages และ API behavior
- `TROUBLESHOOTING-TH.md` — diagnosis ตามอาการ


### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว
