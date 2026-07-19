# 🚀 Palworld Server & Dashboard Thai Edition — 1.1.0 (Official Release)

เวอร์ชัน **1.1.0** เป็นการปรับปรุงครั้งใหญ่จากเวอร์ชัน 1.0.0 โดยขยายจากระบบ Palworld Server บน Docker เพียงรูปแบบเดียว ไปเป็นระบบบริหารเซิร์ฟเวอร์แบบหลาย Runtime ที่รองรับทั้ง **Linux Docker**, **Windows Host-native** และ **macOS Docker**

ในรุ่นนี้มีการปรับปรุงด้านประสิทธิภาพ การจัดเก็บ Save การ Export/Import ผ่าน Dashboard การติดตั้งบน Windows การตรวจสอบปัญหา และเอกสารประกอบทั้งหมด

Version **1.1.0** is a major operational update over 1.0.0. The project now supports multiple server runtime modes, improved save management, safer import/export workflows, native Windows server execution, resource optimization, and expanded documentation.

---

## ✨ Highlights / จุดเด่นของเวอร์ชัน 1.1.0

* รองรับการใช้งาน 3 รูปแบบ

  * Linux Docker
  * Windows Host-native
  * macOS Docker
* เพิ่ม Windows Native SteamCMD installer
* เพิ่ม Windows Host Agent สำหรับควบคุม `PalServer.exe`
* เพิ่ม Dashboard Export/Import แบบเลือกจุดประสงค์
* รองรับการย้าย World ข้าม Windows, Linux และ macOS
* เปลี่ยน Linux Docker storage ไปใช้ Docker Named Volume
* ปรับ Resource optimization และ Docker log rotation
* ปิด Python log formatter ที่ไม่จำเป็น
* เพิ่มระบบตรวจสอบ Windows path เพื่อป้องกัน Save ล้มเหลว
* ลดคำสั่ง Windows เหลือ 6 ไฟล์ โดยรวม System Check ไว้ใน Start All และใช้ Setup สำหรับ Update
* Restart หลังแก้ Config รองรับกำหนดเวลาเริ่มงานและเวลารอแจ้งผู้เล่น พร้อม Countdown แบบ Shutdown Server
* ปรับ README และเอกสารเชิงลึกใหม่ทั้งหมด
* เพิ่ม Import progress แบบแสดงขั้นตอน เปอร์เซ็นต์ เวลารอ และสถานะ REST API
* เพิ่ม Import compatibility guard ป้องกัน Full restore ข้ามระบบปฏิบัติการ
* เพิ่มการเลือก World ID และแก้ `DedicatedServerName` อัตโนมัติเมื่อย้าย World
* เพิ่ม Automatic rollback และ Startup recovery เมื่อ Import หรือการเปิด Server ล้มเหลว

---

# 🔄 Summary of Changes: 1.0.0 → 1.1.0

## 1. Multi-runtime Architecture

### เวอร์ชัน 1.0.0

Palworld Server และ Dashboard ทำงานผ่าน Docker เป็นหลัก:

```text
Docker
├─ Palworld Server
├─ Dashboard
└─ Docker Proxy
```

### เวอร์ชัน 1.1.0

รองรับหลายรูปแบบตามระบบปฏิบัติการ:

```text
Linux
└─ Palworld Server + Dashboard ผ่าน Docker

Windows
├─ PalServer.exe รันบน Windows โดยตรง
├─ PowerShell Host Agent
└─ Dashboard รันผ่าน Docker

macOS
└─ Palworld Linux Server + Dashboard ผ่าน Docker Desktop
```

Windows Host-native mode ถูกเพิ่มขึ้นเพื่อหลีกเลี่ยงปัญหาประสิทธิภาพและพฤติกรรมของ Palworld Linux Server ที่รันผ่าน Docker Desktop/WSL2

---

## 2. Windows Host-native Mode

เพิ่มระบบรัน Palworld Dedicated Server บน Windows โดยตรง:

```text
PalServer.exe
```

โดยไม่ต้องรันตัวเกมอยู่ใน Linux container

### ฟีเจอร์ที่เพิ่ม

* ดาวน์โหลดและอัปเดต Dedicated Server ผ่าน Native Windows SteamCMD
* สร้าง `PalWorldSettings.ini` อัตโนมัติ
* เปิด REST API และ RCON อัตโนมัติ
* ตั้ง Admin password ผ่าน `.env.host`
* Start/Stop/Restart Server จาก Dashboard
* รองรับ Export/Import และ Safety Backup
* รองรับ Host path ทั้งแบบ relative และ absolute
* เก็บ Host Agent log สำหรับตรวจสอบปัญหา

### คำสั่ง Windows

```text
run\windows\00-Setup.bat
run\windows\01-Start-All.bat
run\windows\02-Start-Server.bat
run\windows\03-Start-Dashboard.bat
run\windows\04-Stop-All.bat
run\windows\05-Move-Server-To-Short-Path.bat
```

- `00-Setup.bat` ใช้ทั้งติดตั้งครั้งแรกและ Update/Validate ผ่าน SteamCMD โดยหยุด Component เดิมก่อนและไม่เปิดกลับอัตโนมัติ
- `01-Start-All.bat` รวม System Check เดิมของ Doctor และเปิด Dashboard ที่เคยถูก Stop ให้กลับมาทำงาน
- `03-Start-Dashboard.bat` เปิด Host Agent ให้อัตโนมัติ
- `04-Stop-All.bat` Save World, REST Shutdown 1 วินาที, REST `/stop` และ taskkill fallback, ปิด Agent/Dashboard และตรวจผลหลังปิด
- แก้ HTTP 400 ระหว่าง `00-Setup.bat`/`04-Stop-All.bat` โดยไม่ส่ง `waittime=0` ไปยัง Palworld REST API

---

## 3. Native Windows SteamCMD

เวอร์ชันก่อนหน้าใช้ Linux SteamCMD container เป็นหลัก

ในเวอร์ชัน 1.1.0 ระบบ Windows เปลี่ยนมาใช้:

```text
steamcmd.exe
```

บน Windows โดยตรง

ไฟล์ SteamCMD จะถูกจัดเก็บไว้ที่:

```text
runtime/steamcmd-windows/
```

และติดตั้ง Palworld Dedicated Server ด้วย App ID:

```text
2394010
```

ระบบรองรับ:

* ดาวน์โหลด SteamCMD อัตโนมัติ
* Retry เมื่อ SteamCMD รอบแรกยังไม่พร้อม
* ตรวจว่ามี `PalServer.exe` หลังติดตั้ง
* Update และ Validate ผ่านสคริปต์ Windows

---

## 4. Windows Save Path Protection

Palworld บน Windows อาจ Save ไม่สำเร็จเมื่อเส้นทางติดตั้งยาวเกินไป เช่น:

```text
Failed to save. Failed copy from backup.
```

เวอร์ชัน 1.1.0 เพิ่ม:

* การตรวจความยาว Path ก่อน Start
* คำเตือนเมื่อ Path มีความเสี่ยง
* ตรวจสิทธิ์เขียนไฟล์
* สคริปต์ย้าย Server ไป Path สั้น
* รองรับตำแหน่งแนะนำ เช่น:

```text
D:/PalServer
```

คำสั่งย้ายข้อมูล:

```text
run\windows\05-Move-Server-To-Short-Path.bat
```

สคริปต์จะคัดลอก Server และ World ไปยังตำแหน่งใหม่โดยไม่ลบข้อมูลต้นฉบับทันที

---

## 5. Safer Export and Import

ระบบ Export ยังคงสร้าง **Full archive** เพื่อให้ไฟล์เดียวใช้ได้ทั้งสำหรับ Backup และการย้าย World:

```text
Pal/Saved/
```

ไฟล์ Export ประกอบด้วย `SaveGames`, `Config`, `Logs`, `Crashes` และ Manifest สำหรับตรวจสอบความเข้ากันได้ตอน Import

เมื่อ Import ผู้ใช้ต้องเลือกจุดประสงค์ให้ตรงกับงานที่ต้องการ

### 5.1 ย้าย World และผู้เล่นข้าม Server — แนะนำ

นำเข้าเฉพาะ:

```text
Pal/Saved/SaveGames/
```

เหมาะสำหรับ:

* ย้าย World จาก Windows ไป Linux/macOS
* ย้าย World จาก Linux/macOS ไป Windows
* ย้าย Server ไปเครื่องใหม่
* สลับ Runtime แต่เล่น World และตัวละครเดิมต่อ
* เก็บ Config, REST API, RCON และ Admin password ของเครื่องปลายทางไว้

ข้อมูลที่ย้ายประกอบด้วย:

* World และ Progress
* ตัวละครผู้เล่น
* Guild
* Pals
* สิ่งปลูกสร้าง
* กล่องและไอเทม

ก่อน Import ระบบจะค้นหา World ID ที่มี `Level.sav` และตรวจจำนวน Player save จาก ZIP จากนั้นจะ:

1. แทนที่ `Pal/Saved/SaveGames`
2. แก้ `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางให้ตรงกับ World ID ที่นำเข้า
3. เปิด Server ใหม่อัตโนมัติ
4. รอ REST API กลับมาพร้อม
5. ตรวจว่า World folder และ `DedicatedServerName` ตรงกับ World ที่นำเข้าจริง
6. ประกาศงานสำเร็จเมื่อการตรวจสอบผ่านเท่านั้น

การแก้ `DedicatedServerName` อัตโนมัติช่วยป้องกันกรณี Import สำเร็จแต่ Server เปิด World เดิมหรือ World ใหม่ จนผู้เล่นถูกขอให้สร้างตัวละครใหม่

### 5.2 กู้คืน Backup เต็มระบบ

แทนที่ทั้งหมด:

```text
Pal/Saved/
```

เหมาะสำหรับ:

* Disaster recovery
* กู้คืน Server เดิมจาก Backup
* ย้อน World และ Config กลับพร้อมกัน
* กู้ข้อมูลหลัง Save หรือ Config เสียหาย

Full restore ต้องใช้ Backup จากระบบประเภทเดียวกับปลายทาง:

| ปลายทาง | ZIP ต้องมี |
|---|---|
| Windows Host-native | `Pal/Saved/Config/WindowsServer/` |
| Linux/macOS Docker | `Pal/Saved/Config/LinuxServer/` |

Dashboard จะปฏิเสธ Full restore ข้ามระบบ **ก่อนหยุด Server** หาก Config ไม่ตรงกับปลายทางหรือ Manifest ระบุ source platform คนละประเภท

ตัวอย่างที่ถูกบล็อก:

```text
Linux backup → Full restore บน Windows
Windows backup → Full restore บน Linux/macOS
```

กรณีดังกล่าวให้เลือก **ย้าย World และผู้เล่นข้าม Server** แทน

### 5.3 กู้คืนเฉพาะการตั้งค่า Server

Windows:

```text
Pal/Saved/Config/WindowsServer/
```

Linux/macOS:

```text
Pal/Saved/Config/LinuxServer/
```

เหมาะสำหรับ:

* แก้ `PalWorldSettings.ini` ผิด
* REST API หรือ RCON ใช้งานไม่ได้
* Admin password ไม่ตรง
* ต้องการย้อน Config โดยไม่ย้อน World และผู้เล่น

ZIP ต้องมี Config ที่ตรงกับ Runtime ปลายทาง มิฉะนั้น Dashboard จะไม่อนุญาตให้เริ่มงาน

### 5.4 Import Progress และสถานะงาน

หน้า Maintenance แสดงข้อมูลระหว่าง Import แบบต่อเนื่อง:

* ขั้นตอนปัจจุบันภาษาไทย
* เปอร์เซ็นต์ความคืบหน้า
* รายละเอียดสิ่งที่กำลังทำ
* เวลาที่ใช้และเวลาที่อัปเดตล่าสุด
* Runtime status
* REST API error ล่าสุด
* World ID ที่นำเข้าและ World ID ที่เปิดใช้งาน
* จำนวน Player save
* ตำแหน่ง Safety Backup
* ผลการ Rollback หรือ Startup recovery

ตัวอย่างขั้นตอน:

```text
ตรวจสอบ ZIP
→ Save World ปัจจุบัน
→ หยุด Server
→ สร้าง Safety Backup
→ แตกไฟล์ไปยัง Staging
→ แทนที่ข้อมูลตามโหมด
→ เลือก World ID ที่นำเข้า
→ Start Server
→ รอ REST API
→ ตรวจ World ที่เปิดใช้งาน
→ เสร็จสมบูรณ์
```

### 5.5 Import Safety, Rollback และ Startup Recovery

ก่อน Import ทุกครั้ง ระบบจะ:

1. ตรวจ path traversal, absolute path, symlink, ZIP integrity, จำนวนไฟล์ และขนาดข้อมูล
2. ตรวจว่า ZIP รองรับ Import mode ที่เลือก
3. Save World ปัจจุบัน
4. หยุด Server
5. สร้าง Full Safety Backup
6. เก็บข้อมูลเดิมใน Rollback path
7. Import ผ่าน Staging directory
8. เปิด Server ใหม่อัตโนมัติ
9. รอ REST API และตรวจ World ที่เปิดใช้งาน

หาก Import หรือการเปิด Server ล้มเหลว ระบบจะ:

```text
หยุด Server
→ เก็บข้อมูล Import ที่ล้มเหลว
→ คืน Save/Config เดิมจาก Rollback
→ คืน DedicatedServerName เดิมเมื่อเป็น World-only import
→ เปิด Server เดิมกลับ
→ รอ REST API
→ บันทึกผลการกู้คืนใน Job
```

หาก Dashboard ถูก Restart ระหว่าง Import ระบบจะตรวจ Job ที่ค้างและไฟล์ Rollback ตอนเริ่มทำงาน แล้วพยายามคืนข้อมูลเดิมและเปิด Server กลับโดยอัตโนมัติ

> ห้ามเปิด Server สองตัวพร้อมกันโดยใช้ World ชุดเดียวกัน

Workflow สำหรับสลับ Server ที่แนะนำ:

```text
Server A: Save และ Export
→ ปิด Server A
→ Server B: Import แบบย้าย World และผู้เล่น
→ รอ Job ขึ้น Completed และตรวจ World ID
→ เข้าเกมทดสอบตัวละครเดิม
```

---

## 6. Config Restart Countdown

หน้า Config แยกคำสั่งเป็น **ล้างค่าร่าง**, **อัปเดตไฟล์** และ **Restart Server** อย่างชัดเจน ปุ่มอัปเดตไฟล์จะสร้าง Backup และเขียน `PalWorldSettings.ini` โดยไม่ Restart ส่วนปุ่ม Restart จะไม่เขียนค่าร่างและใช้ Config ที่บันทึกในไฟล์ล่าสุด ผู้ใช้กำหนดเวลาเริ่มงานและเวลารอแจ้งผู้เล่นได้ ระบบเรียก Palworld REST `POST /shutdown` พร้อม `waittime` และข้อความที่กำหนด

Workflow:

```text
ผู้ใช้กดอัปเดตไฟล์เพื่อเขียน Config และสร้าง Backup
→ ผู้ใช้กด Restart Server แยกต่างหาก
→ รอเวลาเริ่มงาน (ถ้ามี)
→ แจ้งผู้เล่นและนับถอยหลัง
→ Save/Stop Runtime
→ Start Server ใหม่
→ รอ REST API พร้อม
→ Completed
```

หน้า Maintenance แสดงเวลาที่เหลือและเปอร์เซ็นต์แบบสด ค่าเริ่มต้นคือเริ่มทันทีและแจ้งล่วงหน้า 60 วินาที หาก Dashboard ถูกรีสตาร์ตกลาง Countdown ระบบ Startup recovery จะรอคำสั่ง Shutdown เดิมและเปิด Server กลับอัตโนมัติ

---

## 7. Docker Named Volume

Linux และ macOS Docker mode เปลี่ยนจาก Bind mount:

```yaml
volumes:
  - ./palworld:/palworld
```

เป็น Docker Named Volume:

```yaml
volumes:
  - palworld-data:/palworld
```

ข้อดี:

* ลดการอ่านเขียนข้าม Windows/macOS shared filesystem
* ลด I/O overhead
* เหมาะกับ Palworld Save และไฟล์จำนวนมาก
* ลดปัญหาจาก Docker Desktop bind mount
* สามารถ Backup และ Restore ผ่าน Dashboard ได้

มีเอกสารและสคริปต์สำหรับ:

* Migration
* Verification
* Backup
* Restore
* Rollback

---

## 8. Resource Optimization

เพิ่มและปรับ Resource configuration สำหรับแต่ละ Service

### Palworld Server

* ไม่มี Hard CPU limit เป็นค่าเริ่มต้น
* ไม่มี Hard memory limit ที่อาจทำให้ Server ถูก Kill
* ใช้ Soft memory reservation
* ลดการเกิด CPU throttling
* ปรับ Engine และ Network settings ให้อยู่ในระดับสมดุล

### Dashboard และ Docker Proxy

รองรับการกำหนด:

```dotenv
DASHBOARD_CPU_LIMIT=
DASHBOARD_MEMORY_LIMIT=
DOCKER_PROXY_CPU_LIMIT=
DOCKER_PROXY_MEMORY_LIMIT=
```

เพิ่ม:

* Memory reservation
* PID limit
* Docker local logging driver
* Log rotation
* จำกัดขนาดและจำนวน Log files

---

## 9. Logging Improvements

ปิด Python log formatter เป็นค่าเริ่มต้น:

```dotenv
LOG_FILTER_ENABLED=false
```

ทำให้ Palworld ส่ง Log เข้า Docker logging driver โดยตรง

ลด Process เสริม:

```text
python3 /home/steam/server/pal_logger.py
```

และลด Runtime overhead ที่ไม่จำเป็น

---

## 10. Background Services

ปรับค่าเริ่มต้นเพื่อให้ Server ทำงานเบาลงและคาดเดาได้ง่ายขึ้น

ฟังก์ชันที่ไม่จำเป็นจะถูกปิดเป็นค่าเริ่มต้น เช่น:

```dotenv
UPDATE_ON_BOOT=false
AUTO_UPDATE_ENABLED=false
AUTO_REBOOT_ENABLED=false
ENABLE_PLAYER_LOGGING=false
```

GameData API, Discord notification, Backup cron และฟังก์ชันอื่นสามารถเปิดกลับผ่าน Config ได้ตามการใช้งาน

REST API และ RCON ยังคงเปิดใช้สำหรับ Dashboard

---

## 11. Dashboard Runtime Control

Dashboard รองรับ Runtime สองรูปแบบ

### Docker Runtime

ใช้ Docker Proxy เพื่อควบคุม:

```text
palworld-server container
```

### External Windows Runtime

ใช้ PowerShell Host Agent เพื่อควบคุม:

```text
PalServer.exe
```

Dashboard สามารถสั่ง:

* Start
* Stop
* Restart
* Save World
* Announce
* Kick
* Ban
* Unban
* Export
* Import
* Config update

ได้ทั้งสอง Runtime

---

## 12. Windows Host Agent

เพิ่ม PowerShell Host Agent สำหรับเชื่อม Dashboard กับ PalServer.exe

Host Agent ทำหน้าที่:

* ตรวจสถานะ Server
* Start และ Stop process
* Restart หลังแก้ Config
* หยุด Server ก่อน Import
* เปิด Server กลับหลัง Import/Export
* รายงานผลลัพธ์กลับ Dashboard
* เก็บ Log สำหรับวิเคราะห์ปัญหา

Log อยู่ที่:

```text
runtime/logs/host-agent.out.log
runtime/logs/host-agent.err.log
```

---

## 13. macOS Command Scripts

เพิ่มชุดคำสั่งสำหรับ macOS:

```text
run/macos/00-Setup.command
run/macos/01-Start-All.command
run/macos/02-Start-Server.command
run/macos/03-Start-Dashboard.command
run/macos/04-Status.command
run/macos/05-Logs.command
run/macos/06-Update.command
run/macos/07-Stop-All.command
run/macos/08-Doctor.command
```

macOS ใช้ Palworld Linux Server ผ่าน Docker Desktop เนื่องจากไม่มี Palworld Dedicated Server native สำหรับ macOS

---

## 14. Integrated System Check

Windows ย้าย Doctor มารวมใน:

```text
run\windows\01-Start-All.bat
```

Start All ตรวจ 10 ขั้นและ Start ระบบในรอบเดียว:

* Required settings และรหัสผ่าน
* Windows path length
* Write permission
* Docker Desktop และ Compose
* Native SteamCMD
* PalServer binary และ Config
* Host Agent heartbeat
* REST API readiness
* Dashboard health
* Dashboard → Windows REST connectivity

macOS ยังคงมีคำสั่งตรวจระบบแยก:

```bash
./run/macos/08-Doctor.command
```

Windows จึงไม่มี `08-Doctor.bat` อีกต่อไป ลดกรณีผู้ใช้เปิด Doctor แล้วระบบถูก Start ซ้ำโดยไม่ตั้งใจ

---

## 15. Documentation Rewrite

ปรับเอกสารทั้งหมดใหม่ โดยแบ่งเป็นระดับการใช้งานและระดับเชิงลึก

### เอกสารหลัก

```text
README.md
```

ครอบคลุม:

* เลือกโหมด
* Setup
* Start/Stop
* Config
* Backup
* Import/Export
* Update
* Troubleshooting

### เอกสารเชิงลึก

```text
FULL_GUIDE_TH.md
CONFIG-REFERENCE-TH.md
GAME-CONFIG-REFERENCE-TH.md
ARCHITECTURE-TH.md
WINDOWS-HOST-MODE-TH.md
MIGRATE-TO-NAMED-VOLUME-TH.md
SAVE-TRANSFER-TH.md
DASHBOARD-MAINTENANCE.md
TROUBLESHOOTING-TH.md
RELEASE-1.1.0.md
CHANGELOG.md
```

---

# ⚠️ Operational Breaking Changes

แม้เวอร์ชันนี้ใช้หมายเลข Minor release แต่มีการเปลี่ยนวิธีใช้งานบางส่วนจาก 1.0.0

## Named Volume

Linux/macOS Docker mode ใช้ Named Volume เป็นค่าเริ่มต้น

ข้อมูลเดิมใน:

```text
./palworld
```

จะไม่ถูกใช้อัตโนมัติ จนกว่าจะ Migration เข้า Volume ใหม่

ห้ามเปิด Server ก่อนตรวจว่าข้อมูล World ถูกย้ายสำเร็จแล้ว เพราะอาจทำให้เห็น World ใหม่

## Admin Profile

Dashboard และ Docker Proxy อาจอยู่ภายใต้ Compose profile:

```text
admin
```

เปิด Server อย่างเดียว:

```bash
docker compose up -d palworld
```

เปิด Server พร้อม Dashboard:

```bash
docker compose --profile admin up -d
```

## Windows Directory

Windows Host-native mode แนะนำให้ใช้ Path สั้น:

```text
D:/PalServer
```

ไม่ควรวาง Dedicated Server ไว้ภายใน Project directory ที่ซ้อนหลายชั้น

## Config Precedence

ใน Docker mode ค่า Environment อาจสร้างหรือเขียนทับ `PalWorldSettings.ini`

เมื่อเริ่มใช้ Dashboard แก้ Config โดยตรง ควรตรวจค่า:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

เพื่อป้องกัน Config ถูกสร้างทับเมื่อ Recreate container

---

# ⬆️ Upgrade Guide from 1.0.0

## ก่อนอัปเกรด

1. เข้า Dashboard
2. กด Save World
3. Export Backup
4. ปิด Server
5. สำรอง `.env`
6. สำรองโฟลเดอร์ `palworld`
7. เก็บ ZIP Backup ไว้นอก Project directory

## Linux/macOS Docker

1. แตกแพ็กเกจ 1.1.0 ไปยังโฟลเดอร์ใหม่
2. คัดลอกค่าที่จำเป็นจาก `.env`
3. Migration ข้อมูลเดิมเข้า Named Volume
4. ตรวจ World และ Player files
5. เปิด Server
6. เปิด Dashboard ด้วย `admin` profile
7. ตรวจ REST API และ World ก่อนอนุญาตให้ผู้เล่นเข้า

## Windows

1. แตกแพ็กเกจไปยังโฟลเดอร์ใหม่
2. รัน:

```text
run\windows\00-Setup.bat
```

3. ใช้ Server path สั้น เช่น:

```text
D:/PalServer
```

4. Import World ด้วยโหมด:

```text
ย้าย World ไปเครื่องนี้
```

5. เปิดระบบ:

```text
run\windows\01-Start-All.bat
```

6. `01-Start-All.bat` จะตรวจระบบครบก่อนประกาศว่า Server พร้อมใช้งาน

---

# 🛡️ Backup Recommendations

ก่อนดำเนินการต่อไปนี้ควร Export Backup ทุกครั้ง:

* Upgrade version
* เปลี่ยน Runtime
* ย้าย Windows ↔ Linux
* แก้ Config จำนวนมาก
* Update Palworld Server
* Migration Named Volume
* Import Save
* เปลี่ยน World

แนะนำให้มี Backup อย่างน้อย:

```text
Daily backup
Pre-update backup
Pre-import backup
Off-machine backup
```

---

# ⚠️ Known Limitations

* Windows, Linux และ macOS ห้ามเปิด World เดียวกันพร้อมกัน
* macOS ไม่มี Native Palworld Dedicated Server
* Docker Desktop อาจมี I/O และ virtualization overhead
* Full restore ข้ามระบบปฏิบัติการถูกบล็อกโดย Dashboard; ให้ใช้โหมด “ย้าย World และผู้เล่นข้าม Server”
* SteamCMD อาจต้อง Retry หลังอัปเดตตัวเองรอบแรก
* Windows Server path ที่ยาวเกินไปอาจทำให้ Save และ Backup ล้มเหลว
* Resource optimization ช่วยลด Overhead แต่ไม่รับประกันว่าปัญหา Physics หรือ Network correction ของ Palworld จะหายทั้งหมด

---

## 🛠️ Final Fixes Included Before Official Release

ก่อนเผยแพร่ `v1.1.0` ได้รวมการแก้ไขต่อไปนี้ไว้ในแพ็กเกจหลักแล้ว:

* แก้ Job Import ค้างที่ `starting_server` เมื่อ Full restore ZIP จาก Linux ไปยัง Windows หรือข้ามระบบในลักษณะเดียวกัน
* เพิ่มการตรวจ Config platform และปฏิเสธ Full restore ที่ไม่เข้ากันก่อนหยุด Server
* แก้ Import แบบ World-only ที่ไฟล์ผู้เล่นอยู่ครบ แต่ Server เปิด World ผิดเพราะ `DedicatedServerName` ยังชี้ไปยัง World เดิม
* เพิ่มการหา World ID จาก `Level.sav` และ Patch `DedicatedServerName` อัตโนมัติ
* เพิ่มการตรวจ World ID หลังเปิด Server ไม่ใช้ REST API พร้อมเพียงอย่างเดียวเป็นเกณฑ์สำเร็จ
* เพิ่ม Progress, Stage detail, elapsed time, REST status และ Safety Backup ในประวัติงาน
* เพิ่ม Automatic rollback เมื่อ Import หรือการเปิด Server ล้มเหลว
* เพิ่ม Startup recovery เมื่อ Dashboard ถูก Restart ระหว่าง Import
* Import สำเร็จแล้ว Start Server ใหม่อัตโนมัติ และ Job จะขึ้น `completed` เมื่อ Server พร้อมและเปิด World ที่นำเข้าถูกต้อง

---

## ⚠️ License Update / ประกาศสำคัญเรื่องสัญญาอนุญาต

* **[TH]** โปรเจกต์นี้ใช้ **Custom Non-Commercial License** สำหรับโค้ดภาษาไทย Dashboard สคริปต์ เครื่องมือ และส่วนดัดแปลงที่พัฒนาเพิ่ม ไม่อนุญาตให้นำส่วนดังกล่าวไปขายต่อ ใช้ให้บริการ Hosting แบบเก็บค่าบริการ หรือนำไปใช้งานเชิงพาณิชย์โดยไม่ได้รับอนุญาต
* **[EN]** The Thai localization, Dashboard modifications, helper scripts, documentation, and other custom additions are distributed under a **Custom Non-Commercial License**. Commercial hosting, resale, paid redistribution, or commercial exploitation of the modified components is prohibited without permission.
* โค้ดหรือ Component จากโครงการต้นฉบับยังคงอยู่ภายใต้ License ของเจ้าของเดิม

---

## 🙏 Credits

Special thanks to **@thijsvanloef** and the contributors of:

```text
thijsvanloef/palworld-server-docker
```

for providing the original Palworld Docker server foundation.

ขอขอบคุณผู้พัฒนาโครงการต้นฉบับและผู้มีส่วนร่วมทุกท่าน ที่สร้างพื้นฐานระบบ Palworld Docker Server ซึ่งถูกนำมาต่อยอดในโครงการนี้

---

## 📦 Release Information

```text
Version: 1.1.0
Previous version: 1.0.0
Release type: Minor version / Major operational update
Supported modes:
- Linux Docker
- Windows Host-native
- macOS Docker
```

### Release assets

```text
palworld-server-dashboard-thai-1.1.0-final.zip
palworld-server-dashboard-thai-1.1.0-final.zip.sha256
```

SHA-256:

```text
ดูค่าจริงจากไฟล์ `palworld-server-dashboard-thai-1.1.0-final.zip.sha256`
```

Recommended Git tag:

```bash
git tag -a v1.1.0 -m "Palworld Server Dashboard Thai 1.1.0"
git push origin v1.1.0
```


### สถานะค่าร่าง ค่าในไฟล์ และค่าที่ Server ใช้อยู่

หน้า Config แยกสถานะเป็น 3 ชั้นเพื่อป้องกันความสับสน:

- **Server ใช้อยู่**: ค่าจาก REST `GET /settings` ของ Process ที่กำลังรัน
- **ในไฟล์**: ค่าที่อ่านจาก `PalWorldSettings.ini` และจะถูกโหลดเมื่อ Restart
- **ค่าร่าง**: ค่าที่แก้ในหน้าเว็บแต่ยังไม่ได้กด **อัปเดตไฟล์**

หลังอัปเดตไฟล์สำเร็จ ค่าจะถูกย้ายออกจากรายการร่างและแสดงในคอลัมน์ **ในไฟล์ — รอ Restart** ปุ่ม Restart จะเตือนเฉพาะค่าร่างที่ยังไม่ได้เขียน ไม่เตือนค่าที่บันทึกลงไฟล์แล้ว

เมื่อเริ่ม Restart ระบบจะล็อกสำเนา `PalWorldSettings.ini` ล่าสุดไว้ก่อน จากนั้นแจ้งผู้เล่นและหยุด Server ให้สนิท แล้วเขียนสำเนาที่ล็อกไว้กลับลงไฟล์อีกครั้งก่อนเปิด Server วิธีนี้ป้องกันกรณี Process เดิมเขียนค่า Runtime เก่าทับไฟล์ระหว่าง Shutdown หลัง REST API พร้อม ระบบจะอ่าน `GET /settings` และตรวจเฉพาะค่าที่รอ Restart หากค่าไม่ตรง Job จะเป็น `failed` พร้อมระบุค่าที่ไม่ตรง แทนการขึ้น `completed` ผิด ๆ

เมื่อการตรวจผ่าน หน้า Config จะโหลดทั้ง `GET /settings` และไฟล์ใหม่อัตโนมัติ สถานะ **อัปเดตไฟล์แล้ว — รอ Restart** และตารางค่าที่รอใช้จะหายทันทีโดยไม่ต้อง Refresh หน้า นอกจากนี้ `DenyTechnologyList=` และ `DenyTechnologyList=()` จะถูกตีความเป็นรายการว่าง `[]` เหมือนกับ REST API จึงไม่แสดงเป็นความต่างปลอม
