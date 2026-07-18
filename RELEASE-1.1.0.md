# Palworld Server Dashboard Thai 1.1.0

> Release notes สำหรับ Tag `v1.1.0`  
> เปรียบเทียบจากเวอร์ชัน `1.0.0`  
> วันที่เผยแพร่: 18 กรกฎาคม 2026

## สรุป

เวอร์ชัน `1.1.0` ปรับโปรเจกต์จากชุด Docker สำหรับ Linux เป็นแพ็กเกจดูแล Palworld Dedicated Server แบบหลาย Runtime ในชุดเดียว:

- **Linux:** เกมและ Dashboard รันใน Docker โดยใช้ Named Volume
- **Windows:** เกมรันเป็น `PalServer.exe` บน Windows โดยตรง ส่วน Dashboard รันใน Docker Desktop
- **macOS:** เกมและ Dashboard รันเป็น Linux containers ผ่าน Docker Desktop

รุ่นนี้เน้นความเสถียรของข้อมูล, ลดงานเบื้องหลังที่ไม่จำเป็น, เพิ่มการควบคุม Runtime จาก Dashboard, เพิ่มเครื่องมือ Setup/Update/Doctor และเขียนเอกสารใหม่ให้ใช้งานได้ครบจาก `README.md`

---

## จุดเด่นของรุ่นนี้

### รองรับ 3 รูปแบบการใช้งาน

| ระบบ | Palworld Runtime | Dashboard | Storage หลัก |
|---|---|---|---|
| Linux | Docker container | Docker container | Named Volume `palworld-data` |
| Windows | Native `PalServer.exe` | Docker Desktop | โฟลเดอร์ Windows เช่น `D:/PalServer` |
| macOS | Linux container ผ่าน Docker Desktop | Docker container | Named Volume `palworld-data` |

### Windows Host-native mode

เพิ่มโหมด Windows ที่ไม่รันตัวเกมภายใน WSL2/Docker Desktop:

- ดาวน์โหลดและอัปเดตเกมด้วย Native Windows `steamcmd.exe`
- รัน `PalServer.exe` บน Windows โดยตรง
- ใช้ PowerShell Host Agent รับคำสั่ง Start/Stop/Restart จาก Dashboard
- สร้างและปรับ `PalWorldSettings.ini` อัตโนมัติ
- เปิด REST API และ RCON จากค่าใน `.env.host`
- รองรับ `PALWORLD_HOST_DIR` ทั้ง Relative path และ Absolute path
- เพิ่มการตรวจ Path length และ Write permission
- เพิ่มเครื่องมือย้าย Server ไปยัง Path สั้นเพื่อป้องกัน Save failure
- เก็บ Host Agent heartbeat และ Log สำหรับตรวจปัญหา

### Linux/macOS ใช้ Docker Named Volume

เปลี่ยนข้อมูลเกมจาก Bind mount:

```yaml
- ./palworld:/palworld
```

เป็น Named Volume:

```yaml
- palworld-data:/palworld
```

เพื่อแยกข้อมูลเกมออกจากอายุของ Container และลดปัญหา I/O ผ่าน Shared folder โดยเฉพาะเมื่อใช้ Docker Desktop

### Dashboard รองรับหลาย Runtime

Dashboard สามารถควบคุมได้ทั้ง:

- Docker runtime
- External Windows runtime ผ่าน Host Agent

ฟังก์ชันหลักประกอบด้วย:

- Start, Stop และ Restart Runtime
- ตรวจ REST API, Metrics, Players และ Settings
- Save World ก่อนหยุด Server
- Config form editor และ Raw editor
- สำรอง Config ก่อนบันทึก
- Export World
- Import World พร้อม Validation, Staging, Safety backup และ Rollback
- Kick, Ban และ Unban พร้อมประวัติ
- Discord master switch
- Maintenance queue และสถานะของแต่ละขั้นตอน

---

## สิ่งที่เพิ่มจาก 1.0.0

### Runtime และสคริปต์

เพิ่มไฟล์และเครื่องมือใหม่:

```text
.env.host.example
docker-compose.host.yml
run/linux/
run/windows/
run/macos/
```

#### Linux

- `first-init.sh`
- `start-all.sh`
- `stop-all.sh`
- `migrate-to-named-volume.sh`

#### Windows

- `00-Setup.bat`
- `01-Start-All.bat`
- `02-Start-Server.bat`
- `03-Start-Dashboard.bat`
- `04-Status.bat`
- `05-Logs.bat`
- `06-Update.bat`
- `07-Stop-All.bat`
- `08-Doctor.bat`
- `09-Move-Server-To-Short-Path.bat`
- `PalworldManager.ps1`
- `PalworldHostAgent.ps1`
- `Configure-PalworldHost.ps1`

#### macOS

เพิ่มชุดคำสั่ง `.command` สำหรับ Setup, Start, Stop, Status, Logs, Update และ Doctor โดยไม่ต้องจำคำสั่ง Compose เอง

### เอกสาร

เพิ่มและเขียนใหม่:

- `README.md`
- `FULL_GUIDE_TH.md`
- `CONFIG-REFERENCE-TH.md`
- `ARCHITECTURE-TH.md`
- `TROUBLESHOOTING-TH.md`
- `WINDOWS-HOST-MODE-TH.md`
- `MIGRATE-TO-NAMED-VOLUME-TH.md`
- `DASHBOARD-MAINTENANCE.md`
- `CHANGELOG.md`
- `VERSION`

---

## สิ่งที่เปลี่ยน

### ค่าเริ่มต้นของ Linux Docker mode

| รายการ | 1.0.0 | 1.1.0 |
|---|---|---|
| Storage | `./palworld` Bind mount | Named Volume `palworld-data` |
| Update ตอน Start | เปิด | ปิดเป็นค่าเริ่มต้น |
| Performance arguments | `MULTITHREADING=true` | `ENABLE_PERF_THREADING_ARGS=true` |
| Worker threads | ตามค่าที่กำหนด | เว้นว่างให้เกมเลือกเอง |
| Player logging | เปิด | ปิดเป็นค่าเริ่มต้น |
| Python log filter | เปิด | ปิดเป็นค่าเริ่มต้น |
| Auto reboot | เปิด | ปิดเป็นค่าเริ่มต้น |
| Discord notification | เปิดหลายรายการ | ปิดผ่าน Master switch เป็นค่าเริ่มต้น |
| Dashboard refresh | 15 วินาที | 30 วินาที |
| Engine/Network baseline | 120 | 60 |
| Palworld RAM | ไม่มี Reservation | Soft reservation ค่าเริ่มต้น 8 GB |
| Dashboard/Proxy | ไม่มี Resource limit | มี CPU/RAM/PID limits |
| Container logs | ไม่มีขนาดสูงสุดชัดเจน | Docker local log rotation |

### Dashboard และ Docker Proxy เป็น `admin` profile

ใน `1.1.0` คำสั่งนี้เปิดเฉพาะ Palworld:

```bash
docker compose up -d
```

เมื่อต้องการเปิด Dashboard ด้วย ต้องใช้:

```bash
docker compose --profile admin up -d --build
```

หรือใช้สคริปต์:

```bash
./run/linux/start-all.sh
```

### การสร้าง Config

Docker mode รองรับการหยุดสร้าง `PalWorldSettings.ini` จาก Environment เพื่อให้ Dashboard แก้ Config แล้วไม่ถูกเขียนทับ:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

สำหรับการติดตั้งใหม่ ให้เริ่มด้วย `false` จน Server สร้าง Config สำเร็จครั้งแรก จากนั้นจึงเปลี่ยนเป็น `true`

---

## Operational breaking changes

แม้ `1.1.0` เป็น Minor release แต่มีการเปลี่ยนวิธีใช้งานที่ผู้ดูแลเดิมต้องทราบ

### 1. ห้ามเปิด 1.1.0 แล้วคาดว่าจะเห็น World เดิมทันที

เวอร์ชันใหม่ใช้ Named Volume แต่ `1.0.0` เก็บข้อมูลใน `./palworld`

ต้องย้ายข้อมูลก่อน:

```bash
./run/linux/migrate-to-named-volume.sh ./palworld
```

สคริปต์จะ:

1. หยุด Compose stack
2. สร้าง Backup แบบ `.tar.gz`
3. สร้าง Named Volume
4. ตรวจว่า Volume ปลายทางว่าง
5. คัดลอกข้อมูลเดิมเข้า Volume

ห้ามลบ `./palworld` เดิมจนกว่าจะเข้า World และตรวจข้อมูลครบแล้ว

### 2. Dashboard ไม่เปิดด้วยคำสั่งปกติ

เนื่องจาก Dashboard และ Docker Proxy อยู่ใน `admin` profile จึงต้องระบุ Profile หรือใช้สคริปต์ Start all

### 3. `UPDATE_ON_BOOT` ไม่เปิดตลอดเวลาแล้ว

First init หรือรอบ Update ต้องเปิดชั่วคราว:

```dotenv
PALWORLD_UPDATE_ON_BOOT=true
```

หลังติดตั้งหรืออัปเดตเสร็จให้เปลี่ยนกลับเป็น:

```dotenv
PALWORLD_UPDATE_ON_BOOT=false
```

### 4. Discord และ Player logging ถูกปิดเป็นค่าเริ่มต้น

ผู้ใช้ที่ต้องการ Notification เดิมต้องเปิด Master switch และตรวจ Webhook URL ใหม่

### 5. Engine baseline ลดจาก 120 เป็น 60

รุ่นนี้ลด Frame/Tick baseline เพื่อลดภาระ Server และ Background scheduling ค่าเหล่านี้ยังแก้ได้ใน `docker-compose.yml`

### 6. Windows ต้องใช้ Path สั้น

แนะนำ:

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
```

ไม่แนะนำให้วาง Server ไว้ในโฟลเดอร์โปรเจกต์ที่ซ้อนหลายชั้น เพราะ Palworld จะต่อ Path สำหรับ World backup และ Player save เพิ่มอีกหลายระดับ ซึ่งอาจทำให้ Save ล้มเหลวด้วยข้อความ:

```text
Failed to save. Failed copy from backup.
```

ใช้เครื่องมือย้าย:

```text
run\windows\09-Move-Server-To-Short-Path.bat
```

---

## วิธีอัปเกรดจาก 1.0.0 บน Linux

### 1. Save และหยุด Server เดิม

แนะนำให้ Save World จาก Dashboard ก่อน แล้วจึงหยุด Stack:

```bash
docker compose down
```

### 2. สำรองข้อมูล

อย่างน้อยต้องสำรอง:

```text
.env
palworld/
dashboard/data/
```

ตัวอย่าง:

```bash
tar -czf palworld-1.0.0-before-upgrade.tar.gz palworld dashboard/data .env
```

### 3. แตก 1.1.0 เป็นโฟลเดอร์ใหม่

ไม่แนะนำให้แตกทับโฟลเดอร์เดิมทันที เพื่อให้ Rollback ได้ง่าย

### 4. ย้ายค่า Secret

คัดลอกค่าจาก `.env` เดิมไปยัง `.env` ใหม่แบบเลือกเฉพาะค่า ไม่ควรทับ `.env.example` รุ่นใหม่ทั้งไฟล์

ตรวจอย่างน้อย:

```dotenv
PALWORLD_SERVER_PASSWORD=
PALWORLD_ADMIN_PASSWORD=
DASHBOARD_USERNAME=
DASHBOARD_PASSWORD=
DISCORD_INFORMATION_WEBHOOK_URL=
```

### 5. ย้าย World ไป Named Volume

นำโฟลเดอร์ `palworld` เดิมมาไว้ข้างแพ็กเกจใหม่ แล้วรัน:

```bash
chmod +x run/linux/*.sh
./run/linux/migrate-to-named-volume.sh ./palworld
```

### 6. ตรวจค่า First init

สำหรับ Server เดิมที่มี Config อยู่แล้ว:

```dotenv
PALWORLD_UPDATE_ON_BOOT=false
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

### 7. เปิดระบบ

```bash
./run/linux/start-all.sh
```

หรือ:

```bash
docker compose --profile admin up -d --build
```

### 8. ตรวจหลังอัปเกรด

```bash
docker compose --profile admin ps
docker compose logs --tail=200 palworld
docker compose --profile admin logs --tail=200 dashboard
```

ตรวจให้ครบ:

- เข้า World เดิมได้
- Player save อยู่ครบ
- Dashboard Online
- REST API Online
- Export สำเร็จ
- Config เปิดอ่านได้

เก็บ Backup และโฟลเดอร์ `1.0.0` เดิมไว้จนผ่านการทดสอบจริง

---

## วิธีเริ่มใช้งานใหม่

### Linux

```bash
cp .env.example .env
# แก้รหัสผ่านใน .env
chmod +x run/linux/*.sh
./run/linux/first-init.sh
# เปลี่ยน PALWORLD_UPDATE_ON_BOOT=false หลังติดตั้ง
./run/linux/start-all.sh
```

### Windows

แนะนำให้แตกโปรเจกต์ไว้ที่ใดก็ได้ แต่เก็บเกมจริงใน Path สั้น เช่น `D:/PalServer`

```text
run\windows\00-Setup.bat
run\windows\01-Start-All.bat
run\windows\08-Doctor.bat
```

### macOS

```bash
chmod +x run/macos/*.command
./run/macos/00-Setup.command
./run/macos/01-Start-All.command
```

---

## ข้อควรรู้สำหรับ Windows

### SteamCMD อาจไม่สำเร็จในรอบแรก

จากการทดสอบจริง Native SteamCMD อาจตอบ:

```text
ERROR! Failed to install app '2394010' (Missing configuration)
```

แล้วสำเร็จในรอบ Retry ถัดไป ตัว Manager รองรับ Retry อัตโนมัติ หากครบจำนวนรอบแล้วยังไม่สำเร็จ ให้รัน `06-Update.bat` หรือ `00-Setup.bat` อีกครั้งหลังตรวจการเชื่อมต่อ Steam

### Setup ไม่ได้เปิด Server

หลัง `00-Setup.bat` สำเร็จ ต้องรัน:

```text
run\windows\01-Start-All.bat
```

### Export/Import ต้องใช้ Host Agent

Windows Dashboard ต้องมี Host Agent ทำงานเพื่อหยุดและเปิด `PalServer.exe` ระหว่าง Maintenance workflow

ตรวจด้วย:

```text
run\windows\04-Status.bat
run\windows\08-Doctor.bat
```

### REST API Password ต้องตรงกัน

ค่าเหล่านี้ต้องสัมพันธ์กัน:

```text
PALWORLD_ADMIN_PASSWORD
AdminPassword ใน PalWorldSettings.ini
รหัสที่ Dashboard ใช้เรียก REST API
```

---

## ข้อจำกัดและ Known issues

- macOS ไม่มี Native Palworld Dedicated Server ในแพ็กเกจนี้ จึงใช้ Linux container ผ่าน Docker Desktop
- Docker Desktop มี Storage/VM overhead มากกว่า Docker Engine บน Linux host จริง
- Windows ควรใช้ Path สั้นเพื่อป้องกัน Save backup path ยาวเกินไป
- ห้ามให้ Docker Palworld และ Windows Native Palworld เขียน World เดียวกันพร้อมกัน
- Import จะหยุด Runtime ชั่วคราวและสร้าง Safety backup ก่อนดำเนินการ
- Import มี 3 scope: `world_only` (ค่าเริ่มต้น), `full_restore` และ `config_only`; การสลับ Windows/Linux/macOS ควรใช้ `world_only`
- `PALWORLD_ADMIN_PASSWORD` ที่ไม่ตรงกับ Config จะทำให้ Dashboard แสดง REST API Offline หรือ Unauthorized
- Dashboard และ Docker Proxy ไม่เปิดโดยอัตโนมัติเมื่อไม่ระบุ `admin` profile
- Resource values เป็นค่าเริ่มต้นทั่วไป ควรปรับตามจำนวนผู้เล่น, World size และ RAM จริง

---

## ความเข้ากันได้

| รายการ | สถานะ |
|---|---|
| อัปเกรด World จาก 1.0.0 | รองรับเมื่อทำ Migration ไป Named Volume |
| Dashboard data เดิม | คัดลอก `dashboard/data` ได้ |
| Linux Docker host | รองรับ |
| Windows Native PalServer | รองรับใน 1.1.0 |
| Windows Docker PalServer | ยังใช้ Docker mode ได้ แต่แนะนำ Host-native สำหรับเครื่อง Windows |
| macOS Native PalServer | ไม่รองรับ |
| macOS Docker Desktop | รองรับสำหรับการทดลองและใช้งานทั่วไป |
| Export จาก 1.0.0 แล้ว Import เข้า 1.1.0 | รองรับเมื่อ ZIP ผ่าน Validation และมี `Pal/Saved` ถูกต้อง |

---

## Security และการดูแลระบบ

- ไม่ควร Commit `.env`, `.env.host`, Password หรือ Discord Webhook
- ไม่ควรเปิด REST API `8212` และ RCON `25575` สู่ Internet โดยตรง
- Dashboard และ Docker Proxy มี Resource/PID limits
- Docker Proxy จำกัด Docker API ที่ Dashboard ใช้งาน
- Container logs ใช้ Rotation ลดความเสี่ยง Disk เต็ม
- Import ตรวจ ZIP path traversal, symlink, ขนาดไฟล์, โครงสร้าง และความพร้อมของ path ตามโหมดก่อน Extract
- Dashboard สร้าง Full safety backup ก่อน Import และ Rollback เฉพาะ target ที่ถูกแทนที่เมื่อ Workflow ล้มเหลว
- Export format ยังคงเป็น Full `Pal/Saved` archive แต่ผู้ใช้เลือก restore scope ตอน Import ได้

---

## Pre-release checklist

ก่อนสร้าง Tag ให้ตรวจอย่างน้อย:

- [ ] `VERSION` เป็น `1.1.0`
- [ ] ชื่อใน `README.md`, `CHANGELOG.md` และหน้า Dashboard เป็น `1.1.0`
- [ ] ไม่มี `.env`, `.env.host`, Save, Password หรือ Webhook จริงใน Release asset
- [ ] ไม่มี `__pycache__`, `.pyc`, Runtime log และไฟล์ Import/Export ส่วนตัว
- [ ] `docker compose config` ผ่าน
- [ ] `docker compose --profile admin config` ผ่าน
- [ ] Linux First init ผ่าน
- [ ] Linux Migration จาก Bind mount ไป Named Volume ผ่าน
- [ ] Windows `00-Setup.bat` ติดตั้ง Native Server สำเร็จ
- [ ] Windows `01-Start-All.bat` เปิด Server, Agent และ Dashboard สำเร็จ
- [ ] Windows Save World ผ่านเมื่อใช้ Path สั้น
- [ ] macOS Setup/Start scripts ทำงานบน Docker Desktop
- [ ] REST API, Players, Metrics และ Settings Online
- [ ] Export และ Import ผ่านทั้ง Docker runtime และ Windows external runtime
- [ ] ZIP Release แตกไฟล์ได้และ Checksum ตรง

---

## Release assets ที่แนะนำ

```text
palworld-server-dashboard-thai-1.1.0.zip
palworld-server-dashboard-thai-1.1.0.zip.sha256
RELEASE-1.1.0.md
```

ไม่แนะนำให้แนบไฟล์ `.patch` เป็น Asset หลักสำหรับผู้ใช้ทั่วไป แต่สามารถเก็บไว้สำหรับ Maintainer ได้

---

## คำสั่งสร้าง Tag

แนะนำ Tag แบบมี `v` นำหน้า:

```bash
git tag -a v1.1.0 -m "Palworld Server Dashboard Thai 1.1.0"
git push origin v1.1.0
```

หาก Repository ใช้ Tag แบบไม่มี `v`:

```bash
git tag -a 1.1.0 -m "Palworld Server Dashboard Thai 1.1.0"
git push origin 1.1.0
```

---

## Release description แบบย่อ

Palworld Server Dashboard Thai `1.1.0` เพิ่มการรองรับ Linux Docker, Windows Host-native และ macOS Docker ในแพ็กเกจเดียว พร้อม Named Volume, Native Windows SteamCMD, PowerShell Host Agent, Config editor, Runtime control, Export/Import workflow, Resource optimization, Log rotation และเอกสารภาษาไทยฉบับสมบูรณ์

ผู้ใช้งาน `1.0.0` บน Linux ต้องย้ายข้อมูลจาก `./palworld` ไปยัง Named Volume ก่อนเปิดรุ่นใหม่ และต้องใช้ `--profile admin` เมื่อต้องการเปิด Dashboard ส่วน Windows แนะนำให้ติดตั้งตัวเกมไว้ใน Path สั้น เช่น `D:/PalServer`

---

## Import Recovery และ Maintenance Progress ที่รวมใน 1.1.0

ก่อนเผยแพร่ `v1.1.0` ได้รวมการแก้ปัญหา Import แบบ Full restore ค้างที่ `starting_server` ไว้ในรุ่นนี้แล้ว โดยเฉพาะกรณีนำ Backup จากระบบหนึ่งไป Full restore บนอีกระบบ เช่น Linux backup ไปยัง Windows

### Import compatibility guard

- ตรวจ Config platform ใน ZIP ก่อนหยุด Server
- Windows Full restore ต้องมี `Pal/Saved/Config/WindowsServer`
- Linux/macOS Full restore ต้องมี `Pal/Saved/Config/LinuxServer`
- หาก Manifest ระบุ source platform คนละระบบ จะไม่อนุญาต Full restore
- การย้ายข้ามระบบต้องใช้โหมด `world_only`
- UI ปิดตัวเลือกที่ ZIP ไม่รองรับและแสดงคำเตือนทันที

### Maintenance progress

- แสดงชื่อ Stage ภาษาไทย
- แสดงรายละเอียดว่าระบบกำลังทำอะไร
- แสดงเปอร์เซ็นต์ความคืบหน้า
- แสดงเวลาที่ใช้และเวลาอัปเดตล่าสุด
- ระหว่างรอ REST API แสดง Runtime status, REST error ล่าสุด และเวลาที่เหลือ
- หน้า Maintenance refresh ทุก 2 วินาที

### Server restart, rollback และ recovery

- Import สำเร็จแล้ว Start Server ใหม่อัตโนมัติ
- Job จะ Completed ต่อเมื่อ REST API พร้อม
- หาก Start ไม่สำเร็จ ระบบหยุด Runtime, คืนข้อมูลเดิม และ Start Server เดิมกลับ
- แสดง Rollback stages ใน Dashboard
- เพิ่ม Startup recovery กรณี Dashboard ถูก Restart ระหว่าง Import

### การเลือก Import mode

| สถานการณ์ | โหมด |
|---|---|
| Windows ↔ Linux/macOS | `world_only` |
| ย้ายไปเครื่องใหม่แต่เก็บ Config ปลายทาง | `world_only` |
| กู้ Backup กลับระบบเดิมทั้งหมด | `full_restore` |
| กู้เฉพาะ Config ของระบบเดียวกัน | `config_only` |



### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว
