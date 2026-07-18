# Palworld Server Dashboard Thai 1.1.0

แพ็กเกจสำหรับติดตั้ง ดูแล และสำรอง Palworld Dedicated Server พร้อม Dashboard ภาษาไทย รองรับ 3 รูปแบบการใช้งาน:

| ระบบ | ตัวเกมรันที่ไหน | Dashboard รันที่ไหน | เหมาะกับ |
|---|---|---|---|
| Linux | Docker container | Docker container | เซิร์ฟเวอร์ Linux และการใช้งานระยะยาว |
| Windows | `PalServer.exe` บน Windows | Docker Desktop | เครื่อง Windows ที่ต้องการลดผลกระทบจากการรันเกมใน WSL2 |
| macOS | Linux container ผ่าน Docker Desktop | Docker container | การทดลองหรือดูแลเซิร์ฟเวอร์จาก Mac |

> **เริ่มครั้งแรกให้อ่านหัวข้อของระบบที่ใช้อยู่เท่านั้น** แล้วกลับมาดูหัวข้อ “คำสั่งประจำวัน” และ “การตั้งค่า” ภายหลัง

---

## สารบัญ

1. [เลือกโหมด](#1-เลือกโหมด)
2. [ข้อควรรู้ก่อนเริ่ม](#2-ข้อควรรู้ก่อนเริ่ม)
3. [Windows Host-native](#3-windows-host-native)
4. [Linux Docker](#4-linux-docker)
5. [macOS Docker](#5-macos-docker)
6. [เข้าเกมและเข้า Dashboard](#6-เข้าเกมและเข้า-dashboard)
7. [การตั้งค่า](#7-การตั้งค่า)
8. [ฟังก์ชัน Dashboard](#8-ฟังก์ชัน-dashboard)
9. [Export / Import / Backup](#9-export--import--backup)
10. [Update และ Restart](#10-update-และ-restart)
11. [Resource optimization](#11-resource-optimization)
12. [Troubleshooting แบบเร็ว](#12-troubleshooting-แบบเร็ว)
13. [โครงสร้างไฟล์](#13-โครงสร้างไฟล์)
14. [เอกสารเชิงลึก](#14-เอกสารเชิงลึก)

---

# 1. เลือกโหมด

## ใช้ Windows

เลือก **Windows Host-native mode**

- SteamCMD และ `PalServer.exe` รันบน Windows โดยตรง
- Docker Desktop ใช้เฉพาะ Dashboard
- World อยู่ในโฟลเดอร์ Windows เช่น `D:/PalServer`
- Dashboard สั่ง Start/Stop ผ่าน PowerShell Host Agent
- Export/Import ใช้ได้เมื่อ Host Agent และ Dashboard ทำงาน

ไฟล์หลัก:

```text
.env.host
docker-compose.host.yml
run/windows/
```

## ใช้ Linux

เลือก **Linux Docker mode**

- เกม, Dashboard และ Docker Proxy รันใน Docker
- ข้อมูลเกมอยู่ใน Named Volume `palworld-data`
- เหมาะกับ Linux host จริงมากที่สุด

ไฟล์หลัก:

```text
.env
docker-compose.yml
run/linux/
```

## ใช้ macOS

เลือก **macOS Docker mode**

- macOS ไม่มี Native Palworld Dedicated Server ในแพ็กเกจนี้
- เกมจึงรันเป็น Linux container ผ่าน Docker Desktop
- คำสั่งถูกห่อไว้ในไฟล์ `.command`

ไฟล์หลัก:

```text
.env
docker-compose.yml
run/macos/
```

---

# 2. ข้อควรรู้ก่อนเริ่ม

## 2.1 รหัสผ่าน 3 ชุดไม่ใช่ค่าเดียวกัน

| ตัวแปร | ใช้ทำอะไร |
|---|---|
| `PALWORLD_SERVER_PASSWORD` | รหัสที่ผู้เล่นใช้เข้าเซิร์ฟเวอร์ ปล่อยว่างได้ใน Windows mode |
| `PALWORLD_ADMIN_PASSWORD` | รหัส Admin ของ Palworld REST API/RCON |
| `DASHBOARD_PASSWORD` | รหัส Login หน้า Dashboard |

`PALWORLD_ADMIN_PASSWORD` ต้องตรงกับ `AdminPassword` ใน `PalWorldSettings.ini` มิฉะนั้น Dashboard จะแสดง REST API Offline หรือ Unauthorized

## 2.2 พอร์ตเริ่มต้น

| พอร์ต | Protocol | หน้าที่ |
|---:|---|---|
| 8211 | UDP | ผู้เล่นเชื่อมต่อเกม |
| 27015 | UDP | Query/Community server |
| 8212 | TCP | Palworld REST API |
| 25575 | TCP | RCON |
| 8080 | TCP | Dashboard |

ไม่ควรเปิด REST API และ RCON ออกอินเทอร์เน็ตโดยตรง ใช้ Firewall จำกัดเฉพาะเครื่องหรือเครือข่ายที่เชื่อถือได้

## 2.3 Setup ไม่ได้แปลว่า Server เปิดแล้ว

คำสั่ง Setup มีหน้าที่ติดตั้งไฟล์และสร้าง Config เท่านั้น หลัง Setup สำเร็จต้องสั่ง Start แยก

## 2.4 สำรองก่อน Import หรือ Migration

Dashboard สร้าง Safety Backup ก่อน Import แต่ยังควรเก็บสำเนา World นอกเครื่องเป็นระยะ โดยเฉพาะก่อนอัปเดตเกมหรือเปลี่ยนโหมด

---

# 3. Windows Host-native

## 3.1 ความต้องการ

- Windows 10/11 หรือ Windows Server ที่รัน PowerShell 5.1 ได้
- Docker Desktop สำหรับ Dashboard
- Internet สำหรับดาวน์โหลด SteamCMD และไฟล์เกม
- พื้นที่ว่างประมาณ 10 GB ขึ้นไป
- สิทธิ์เขียนโฟลเดอร์ Server

## 3.2 ต้องใช้ Path สั้น

แนะนำ:

```text
D:/PalServer
```

ไม่แนะนำให้ติดตั้งไว้ใต้โฟลเดอร์โปรเจกต์ที่ชื่อยาว เพราะ Palworld ต่อ path ของ World backup และ Player save อีกหลายชั้นจนเกิด:

```text
Failed to save. Failed copy from backup.
```

สคริปต์จะตรวจ projected path ก่อน Start และหยุดการทำงานเมื่อยาวเกินระดับปลอดภัย

## 3.3 ติดตั้งครั้งแรก

1. แตก ZIP ไปยังโฟลเดอร์ที่เขียนไฟล์ได้
2. เปิด Docker Desktop
3. ดับเบิลคลิก:

```text
run\windows\00-Setup.bat
```

ครั้งแรกระบบจะ:

1. สร้าง `.env.host`
2. ตั้ง `PALWORLD_HOST_DIR` เป็น `<Drive>:/PalServer`
3. เปิด Notepad ให้แก้รหัสผ่าน
4. ดาวน์โหลด Native Windows SteamCMD
5. ติดตั้ง App `2394010`
6. สร้าง `PalWorldSettings.ini`
7. เปิด REST API และ RCON ใน Config

แก้ขั้นต่ำใน `.env.host`:

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
PALWORLD_ADMIN_PASSWORD=ตั้งรหัสที่เดายาก
DASHBOARD_PASSWORD=ตั้งรหัสหน้าเว็บ
```

ค่าอื่นที่มักแก้:

```dotenv
PALWORLD_SERVER_NAME=Mien Palworld Windows
PALWORLD_SERVER_PASSWORD=
PALWORLD_HOST_PUBLIC_LOBBY=true
DASHBOARD_PORT=8080
```

> SteamCMD อาจตอบ `Missing configuration` ในรอบแรกแล้วสำเร็จในรอบ retry ถัดไป ให้ดูผลสุดท้ายว่าแสดง `Success! App '2394010' fully installed.` และพบ `PalServer.exe` หรือไม่

## 3.4 เปิด Server และ Dashboard

```text
run\windows\01-Start-All.bat
```

ลำดับการทำงาน:

1. ตรวจ path และสิทธิ์เขียน
2. Patch ค่า REST/RCON/Admin จาก `.env.host`
3. เปิด Host Agent แบบ background
4. เปิด `PalServer.exe`
5. รอ REST API Online
6. Build/Start Dashboard container
7. ทดสอบ Dashboard → `host.docker.internal` → REST API
8. เปิด Browser อัตโนมัติ

Dashboard:

```text
http://localhost:8080
```

## 3.5 คำสั่ง Windows

| งาน | ไฟล์ |
|---|---|
| ติดตั้ง/สร้าง Config | `00-Setup.bat` |
| เปิด Server + Dashboard | `01-Start-All.bat` |
| เปิดเฉพาะ Server + Agent | `02-Start-Server.bat` |
| เปิดเฉพาะ Dashboard | `03-Start-Dashboard.bat` |
| ดูสถานะ | `04-Status.bat` |
| ดู Log | `05-Logs.bat` |
| อัปเดตเกม | `06-Update.bat` |
| ปิดทั้งหมด | `07-Stop-All.bat` |
| ตรวจระบบ | `08-Doctor.bat` |
| ย้ายไป Path สั้น | `09-Move-Server-To-Short-Path.bat` |

## 3.6 การปิดอย่างปลอดภัย

เมื่อมีผู้เล่นหรือ World กำลังทำงาน ให้ใช้ปุ่ม **Stop Runtime** หรือ Maintenance workflow ใน Dashboard เพราะ Dashboard จะพยายาม Save World และสั่ง REST shutdown ก่อนส่งคำสั่งหยุด Host process

`07-Stop-All.bat` เหมาะกับการปิดทั้งชุดหลัง Server หยุดแล้ว หรือกรณีฉุกเฉิน ตัว Agent มี fallback เป็นการปิด process tree เมื่อ Server ไม่ออกภายใน timeout

## 3.7 Log ของ Windows

| Log | ตำแหน่ง |
|---|---|
| Palworld | `<PALWORLD_HOST_DIR>/Pal/Saved/Logs/Pal.log` |
| Host Agent stdout | `runtime/logs/host-agent.out.log` |
| Host Agent error | `runtime/logs/host-agent.err.log` |
| SteamCMD | `runtime/steamcmd-windows/logs/` |

ดูรวมด้วย:

```text
run\windows\05-Logs.bat
```

## 3.8 ตรวจระบบ

```text
run\windows\08-Doctor.bat
```

Doctor ตรวจ:

- Path length
- Write permission
- Native SteamCMD
- Docker Desktop
- `PalServer.exe`
- Config
- Host Agent
- Host REST API
- Dashboard เรียก REST API บน Windows ได้หรือไม่

---

# 4. Linux Docker

## 4.1 ความต้องการ

- Linux x86-64
- Docker Engine และ Docker Compose plugin
- SSD
- RAM อย่างน้อย 16 GB สำหรับ Host ที่รันงานอื่นร่วมด้วย

## 4.2 สร้าง `.env`

```bash
cp .env.example .env
nano .env
```

แก้ขั้นต่ำ:

```dotenv
PALWORLD_SERVER_PASSWORD=รหัสเข้าเกม
PALWORLD_ADMIN_PASSWORD=รหัส Admin
DASHBOARD_PASSWORD=รหัส Dashboard
```

## 4.3 First init

ใช้สคริปต์:

```bash
chmod +x run/linux/*.sh
./run/linux/first-init.sh
```

หรือตรงด้วย Compose:

```bash
PALWORLD_UPDATE_ON_BOOT=true docker compose up -d palworld
docker compose logs -f --tail=200 palworld
```

หลังติดตั้งเสร็จแก้ `.env`:

```dotenv
PALWORLD_UPDATE_ON_BOOT=false
```

จากนั้น Recreate เฉพาะเกม:

```bash
docker compose up -d --no-deps --force-recreate palworld
```

## 4.4 เปิดบริการ

เฉพาะเกม:

```bash
docker compose up -d palworld
```

เกมและ Dashboard:

```bash
./run/linux/start-all.sh
```

หรือ:

```bash
docker compose --profile admin up -d --build
```

เปิด Dashboard เพิ่มโดยไม่ Recreate เกม:

```bash
docker compose --profile admin up -d --no-deps --build docker-proxy dashboard
```

## 4.5 ดูสถานะและ Log

```bash
docker compose --profile admin ps
docker compose logs -f --tail=200 palworld
docker compose --profile admin logs -f --tail=200 dashboard docker-proxy
```

ตรวจทรัพยากร:

```bash
docker stats palworld-server palworld-dashboard palworld-docker-proxy
```

## 4.6 ปิดบริการ

ปิดเฉพาะ Admin tools:

```bash
docker compose --profile admin stop dashboard docker-proxy
```

ปิดทั้ง Stack โดยเก็บ Named Volume:

```bash
./run/linux/stop-all.sh
```

หรือ:

```bash
docker compose --profile admin down
```

> ห้ามใช้ `docker compose down -v` เว้นแต่ตั้งใจลบ Named Volume และข้อมูลเกม

## 4.7 Named Volume

ข้อมูลเกมอยู่ใน:

```text
palworld-data
```

ตรวจ:

```bash
docker volume inspect palworld-data
```

ชื่อจริงเปลี่ยนได้ผ่าน:

```dotenv
PALWORLD_VOLUME_NAME=palworld-data
```

---

# 5. macOS Docker

macOS ใช้ `docker-compose.yml` ชุดเดียวกับ Linux แต่รันผ่าน Docker Desktop

## 5.1 ครั้งแรก

```bash
chmod +x run/macos/*.command
./run/macos/00-Setup.command
```

ระบบจะสร้าง `.env` และเปิด TextEdit ให้แก้รหัสผ่าน

## 5.2 ใช้งานประจำวัน

| งาน | คำสั่ง |
|---|---|
| เปิดทั้งหมด | `./run/macos/01-Start-All.command` |
| เปิดเฉพาะเกม | `./run/macos/02-Start-Server.command` |
| เปิดเฉพาะ Dashboard | `./run/macos/03-Start-Dashboard.command` |
| ดูสถานะ | `./run/macos/04-Status.command` |
| ดู Log | `./run/macos/05-Logs.command` |
| อัปเดต | `./run/macos/06-Update.command` |
| ปิดทั้งหมด | `./run/macos/07-Stop-All.command` |
| ตรวจระบบ | `./run/macos/08-Doctor.command` |

Dashboard:

```text
http://localhost:8080
```

> macOS mode ใช้ Linux Palworld container ไม่ใช่ `PalServer` native บน macOS

---

# 6. เข้าเกมและเข้า Dashboard

## 6.1 เข้า Dashboard

```text
http://<IP-เครื่อง-Server>:8080
```

Login ด้วย:

```text
Username: DASHBOARD_USERNAME
Password: DASHBOARD_PASSWORD
```

ค่าเริ่มต้น Username คือ `admin`

## 6.2 เข้าเกม

ใช้:

```text
<IP-Server>:8211
```

ต้องอนุญาต UDP 8211 ใน Firewall และ Router เมื่อเชื่อมต่อจากภายนอก LAN

## 6.3 ตรวจ REST API

Windows host:

```powershell
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:<ADMIN_PASSWORD>"))
Invoke-RestMethod http://127.0.0.1:8212/v1/api/info -Headers @{Authorization="Basic $pair"}
```

Linux/macOS:

```bash
curl -u admin:'<ADMIN_PASSWORD>' http://127.0.0.1:8212/v1/api/info
```

---

# 7. การตั้งค่า

## 7.1 แหล่ง Config ตามโหมด

| โหมด | Runtime/Secret config | Gameplay config | Engine config |
|---|---|---|---|
| Linux/macOS | `.env` + `docker-compose.yml` | Named Volume: `LinuxServer/PalWorldSettings.ini` | สร้างจากตัวแปร Engine ใน Compose |
| Windows | `.env.host` | `<PALWORLD_HOST_DIR>/Pal/Saved/Config/WindowsServer/PalWorldSettings.ini` | แก้ใน Host directory ตามต้องการ |

## 7.2 Docker mode: ป้องกัน Config ถูกเขียนทับ

การติดตั้งใหม่ควรเริ่มด้วย:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=false
```

หลังเกมสร้าง Config สำเร็จและเริ่มแก้ผ่าน Dashboard ให้เปลี่ยนเป็น:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

แล้ว Recreate เฉพาะ `palworld` เพื่อป้องกัน Container generator เขียนค่าทับไฟล์ที่แก้ด้วย Dashboard

## 7.3 Windows mode: ค่าใดถูก Patch จาก `.env.host`

ทุกครั้งที่ Setup, Start, Update, Restart หรือ Doctor สคริปต์จะตรวจและ Patch ค่าเหล่านี้:

- `ServerName`
- `ServerPassword`
- `AdminPassword`
- `PublicPort`
- `RCONEnabled=True`
- `RCONPort`
- `RESTAPIEnabled=True`
- `RESTAPIPort`
- `bIsMultiplay=True`

ค่า Gameplay อื่นแก้ผ่าน Dashboard ได้ แต่ค่าข้างต้นจะกลับมาตรงกับ `.env.host` ในรอบ Start ถัดไป

## 7.4 การแก้ Config ผ่าน Dashboard

มีสองแบบ:

1. **Settings form** — แก้ค่าเป็นรายช่องและสร้าง Backup ก่อนเขียน
2. **Raw editor** — แก้ `PalWorldSettings.ini` โดยตรง

หลังแก้ค่าที่เกมอ่านตอนเริ่มระบบ ให้เลือก **Save + Restart** หรือสร้าง Restart job

## 7.5 Engine tuning ปัจจุบันใน Docker mode

Compose กำหนดค่าหลักไว้ที่ 60:

```text
LAN_SERVER_MAX_TICK_RATE=60
NET_SERVER_MAX_TICK_RATE=60
NET_CLIENT_TICKS_PER_SECOND=60
SMOOTH_FRAME_RATE_UPPER_LIMIT=60
SMOOTH_FRAME_RATE_LOWER_LIMIT=30
```

การเปลี่ยนค่า Engine ต้อง Recreate `palworld` ไม่ใช่แค่ Restart process ภายในเกม

## 7.6 Startup arguments Windows

ใน `.env.host`:

```dotenv
PALWORLD_HOST_PERF_ARGS=false
PALWORLD_HOST_WORKER_THREADS=
PALWORLD_HOST_EXTRA_ARGS=
```

เมื่อเปิด Perf args จะเพิ่ม:

```text
-useperfthreads
-NoAsyncLoadingThread
-UseMultithreadForDS
```

ควรเปลี่ยนทีละค่าและเปรียบเทียบผล ไม่ควรใส่ Worker Threads สูงสุดโดยอัตโนมัติ

รายละเอียดตัวแปรทั้งหมดดู [CONFIG-REFERENCE-TH.md](CONFIG-REFERENCE-TH.md)

---

# 8. ฟังก์ชัน Dashboard

Dashboard รองรับ:

- ดู Server info, metrics, players และ settings
- Start/Stop runtime
- Save World
- Announce
- Kick/Ban/Unban พร้อมประวัติ
- แก้ Config และสร้าง Config backup
- Queue Restart
- Export World
- Upload และ Import World
- ตั้งเวลา Maintenance
- ส่ง Discord notification ตาม switch

## Runtime mode

| โหมด | Label | ตัวควบคุม |
|---|---|---|
| Linux/macOS | Docker | Docker socket proxy |
| Windows | External | PowerShell Host Agent ผ่าน shared control directory |

## Refresh interval

```dotenv
DASHBOARD_REFRESH_SECONDS=30
```

ค่าต่ำมากจะเพิ่มจำนวน REST request ไม่ได้ทำให้ตัวเกม Tick เร็วขึ้น

---

# 9. Export / Import / Backup

## 9.1 Export

Dashboard จะ:

1. ประกาศ Maintenance ตามค่าที่กำหนด
2. พยายาม Save World
3. หยุด Runtime
4. สร้าง ZIP จาก `Pal/Saved`
5. เปิด Runtime กลับ
6. รอ REST API Online

ไฟล์อยู่ใน:

```text
dashboard/data/exports/
```

## 9.2 Import

Dashboard รับ ZIP ที่สร้างจากระบบนี้ โดยภายในต้องมี:

```text
dashboard-export-manifest.json
Pal/Saved/...
```

หลังอัปโหลด ให้เลือก **จุดประสงค์การ Import**:

| โหมด | ข้อมูลที่ถูกแทนที่ | ข้อมูลปลายทางที่เก็บไว้ | ใช้เมื่อ |
|---|---|---|---|
| **สลับ/ย้าย World และผู้เล่น** (`world_only`) | `Pal/Saved/SaveGames` | Config, Logs, Crashes และไฟล์อื่นใน `Pal/Saved` | สลับ Windows ↔ Linux/macOS หรือย้าย World ไปอีก Server **แนะนำ** |
| **กู้คืน Pal/Saved ทั้งชุด** (`full_restore`) | `Pal/Saved` ทั้งหมด | ไม่มี | Disaster recovery หรือกู้กลับเครื่อง/ระบบเดิม |
| **กู้คืน Config ของระบบปลายทาง** (`config_only`) | `Config/WindowsServer` หรือ `Config/LinuxServer` | World, Player save, Logs | กู้ Config โดยไม่แตะ World |

> การใช้ Save เดียวกันหมายถึง Export จาก Server A แล้ว Import เข้า Server B หลัง Server A ปิดแล้ว ห้ามเปิดสอง Runtime ให้เขียน World เดียวกันพร้อมกัน

Workflow:

1. ตรวจ path, ขนาด ZIP และตรวจว่า ZIP รองรับโหมดที่เลือก
2. ประกาศและ Save World
3. หยุด Runtime
4. สร้าง Safety Backup แบบเต็มชุด
5. Extract ไป staging
6. แทนที่เฉพาะ target ของโหมดที่เลือก
7. เปิด Runtime และรอ REST
8. Rollback target เดิมเมื่อเกิดข้อผิดพลาด

ค่าเริ่มต้นคือ `world_only` เพื่อป้องกัน Config คนละระบบถูกทับตอนสลับ Windows/Linux/macOS

> **สำคัญ:** โหมดนี้ไม่ได้คัดลอกเพียง `SaveGames` เท่านั้น ระบบจะอ่าน World ID จาก `GameUserSettings.ini` ภายใน ZIP หรือจากโฟลเดอร์ `SaveGames/0/<WorldID>` แล้วแก้ `Config/<ระบบปลายทาง>/GameUserSettings.ini` ค่า `DedicatedServerName` ให้ชี้ไปยัง World ที่นำเข้าอัตโนมัติ หลัง Start จะตรวจซ้ำว่า World ID ตรงและมี `Level.sav` ก่อนตั้ง Job เป็น `completed`

ไฟล์ Upload อยู่ใน:

```text
dashboard/data/imports/
```

Safety backup และ Export อยู่ใน:

```text
dashboard/data/exports/
```

รายละเอียดและตัวอย่างการสลับ Runtime ดูที่ [SAVE-TRANSFER-TH.md](SAVE-TRANSFER-TH.md)

## 9.3 ข้อจำกัดขนาด

```dotenv
DASHBOARD_MAX_UPLOAD_MB=4096
DASHBOARD_MAX_EXPANDED_MB=8192
```

## 9.4 Backup ของ Docker image

ค่าเริ่มต้น:

```dotenv
BACKUP_ENABLED=true
```

เป็น Backup ภายใน Palworld image แยกจาก Dashboard Export ควรวางนโยบายเก็บไฟล์และพื้นที่ Disk ให้เหมาะสม

---

# 10. Update และ Restart

## Windows

```text
run\windows\06-Update.bat
```

ระบบจะหยุด Server, เรียก Native SteamCMD, Patch Config, Start และรอ REST API

## macOS

```bash
./run/macos/06-Update.command
```

## Linux

```bash
PALWORLD_UPDATE_ON_BOOT=true docker compose up -d --no-deps --force-recreate palworld
docker compose logs -f --tail=200 palworld
```

หลังอัปเดต:

```bash
# แก้ .env กลับ
PALWORLD_UPDATE_ON_BOOT=false

docker compose up -d --no-deps --force-recreate palworld
```

## Recreate Dashboard โดยไม่แตะเกม

Linux/macOS:

```bash
docker compose --profile admin up -d --no-deps --build --force-recreate docker-proxy dashboard
```

Windows:

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin up -d --no-deps --build --force-recreate dashboard-host
```

---

# 11. Resource optimization

## Palworld

Docker mode ใช้ Soft reservation:

```dotenv
PALWORLD_MEMORY_RESERVATION=8g
```

ไม่มี Hard CPU/RAM limit สำหรับตัวเกม เพื่อหลีกเลี่ยง CPU throttling และ OOM จากเพดานที่ต่ำเกินไป

## Dashboard และ Docker Proxy

```dotenv
DASHBOARD_CPU_LIMIT=0.25
DASHBOARD_MEMORY_LIMIT=256m
DASHBOARD_MEMORY_RESERVATION=128m
DOCKER_PROXY_CPU_LIMIT=0.10
DOCKER_PROXY_MEMORY_LIMIT=64m
DOCKER_PROXY_MEMORY_RESERVATION=32m
```

## Log rotation

```dotenv
DOCKER_LOG_MAX_SIZE=20m
DOCKER_LOG_MAX_FILE=3
```

## Python log formatter

ปิดเป็นค่าเริ่มต้น:

```dotenv
LOG_FILTER_ENABLED=false
```

ตรวจใน Docker mode:

```bash
docker top palworld-server -eo pid,ppid,args
```

ไม่ควรเห็น `pal_logger.py`

---

# 12. Troubleshooting แบบเร็ว

## Dashboard เปิดไม่ได้

Linux/macOS:

```bash
docker compose --profile admin ps
docker compose --profile admin logs --tail=200 dashboard docker-proxy
```

Windows:

```text
run\windows\04-Status.bat
run\windows\08-Doctor.bat
```

## REST API Offline

ตรวจตามลำดับ:

1. Server process/container เปิดอยู่หรือไม่
2. `PALWORLD_ADMIN_PASSWORD` ตรงกับ Config หรือไม่
3. `RESTAPIEnabled=True` และ port 8212 หรือไม่
4. Firewall/VPN/Endpoint Security บล็อกหรือไม่
5. Windows Dashboard container เรียก `host.docker.internal` ได้หรือไม่

## Windows Script เปิดแล้วดับ

รันจาก CMD เพื่อเห็น Error:

```bat
run\windows\08-Doctor.bat
```

ดู:

```text
runtime\logs\host-agent.err.log
```

## Windows Save ไม่ได้

อาการ:

```text
Failed to save. Failed copy from backup.
```

ให้ตรวจ `PALWORLD_HOST_DIR` ต้องสั้น เช่น:

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
```

ย้ายด้วย:

```text
run\windows\09-Move-Server-To-Short-Path.bat
```

## World ใหม่หลังย้าย Named Volume

ตรวจว่าชื่อ Volume ตรงกับ `.env` และมีข้อมูลจริง:

```bash
docker volume inspect palworld-data
docker run --rm -v palworld-data:/data alpine:3.20 find /data/Pal/Saved -maxdepth 3 -type d
```

## Export/Import ค้าง

- อย่าปิด Dashboard ระหว่าง Job
- ตรวจ `dashboard/data/jobs.json`
- ดู Dashboard logs
- ตรวจ Host Agent ใน Windows
- ตรวจพื้นที่ Disk ทั้ง World, staging และ Safety Backup

รายละเอียดเพิ่มเติมดู [TROUBLESHOOTING-TH.md](TROUBLESHOOTING-TH.md)

---

# 13. โครงสร้างไฟล์

```text
.
├── .env.example                  # ตัวอย่าง Linux/macOS Docker mode
├── .env.host.example             # ตัวอย่าง Windows Host-native
├── docker-compose.yml            # Linux/macOS stack
├── docker-compose.host.yml       # Windows Dashboard stack
├── dashboard/
│   ├── server.py                 # Dashboard API และ Maintenance worker
│   ├── index.html                # UI
│   └── data/                     # Job, Import, Export, Config backup
├── run/
│   ├── linux/                    # สคริปต์ Linux
│   ├── macos/                    # คำสั่ง .command
│   └── windows/                  # Manager, Host Agent และ .bat
├── runtime/
│   ├── control/                  # Windows Host Agent IPC
│   ├── logs/                     # Host Agent logs
│   ├── steamcmd-windows/         # Native SteamCMD
│   └── config-backups/           # Config backup จาก Windows patcher
└── *.md                          # เอกสาร
```

ไฟล์ Runtime ถูกสร้างเมื่อใช้งานและอาจยังไม่มีใน ZIP ใหม่

---

# 14. เอกสารเชิงลึก

| เอกสาร | เนื้อหา |
|---|---|
| [FULL_GUIDE_TH.md](FULL_GUIDE_TH.md) | สถาปัตยกรรม, lifecycle, operation และ security |
| [CONFIG-REFERENCE-TH.md](CONFIG-REFERENCE-TH.md) | ตัวแปร `.env`, `.env.host`, Compose และ Config precedence |
| [WINDOWS-HOST-MODE-TH.md](WINDOWS-HOST-MODE-TH.md) | Windows SteamCMD, Host Agent, Firewall, REST และ path |
| [MIGRATE-TO-NAMED-VOLUME-TH.md](MIGRATE-TO-NAMED-VOLUME-TH.md) | Migration, verification, backup และ rollback |
| [DASHBOARD-MAINTENANCE.md](DASHBOARD-MAINTENANCE.md) | Dashboard workflow, Job stages, archive format และ data files |
| [ARCHITECTURE-TH.md](ARCHITECTURE-TH.md) | Component/data/control flow ของทั้ง 3 โหมด |
| [TROUBLESHOOTING-TH.md](TROUBLESHOOTING-TH.md) | Diagnose ตามอาการและคำสั่งตรวจ |
| [SAVE-TRANSFER-TH.md](SAVE-TRANSFER-TH.md) | การสลับ World, Import scope, Safety backup และ Rollback |
| [CHANGELOG.md](CHANGELOG.md) | ประวัติการเปลี่ยนแปลงรุ่น 1.1.0 |

---

- [`RELEASE-1.1.0.md`](RELEASE-1.1.0.md) — Release notes, Breaking changes และขั้นตอนอัปเกรดจาก 1.0.0

## Checklist ก่อนใช้งานจริง

- [ ] เปลี่ยน Admin และ Dashboard password แล้ว
- [ ] Windows ใช้ `PALWORLD_HOST_DIR` แบบสั้น
- [ ] REST/RCON ไม่เปิดออกอินเทอร์เน็ตโดยไม่จำเป็น
- [ ] ทดสอบ Save World
- [ ] ทดสอบ Export และดาวน์โหลด ZIP
- [ ] ทดสอบ Import ด้วย World สำเนา
- [ ] มี Backup นอกเครื่อง
- [ ] ตรวจพื้นที่ Disk และ Docker logs
- [ ] ทดสอบ Shutdown/Restart ก่อนเปิดให้ผู้เล่นใช้งาน

## [TH] เครดิตและแหล่งอ้างอิง

โปรเจกต์นี้ได้รับการพัฒนาต่อยอดและอ้างอิงโครงสร้างพื้นฐานมาจากโปรเจกต์ต้นแบบ โดยมีรายละเอียดดังนี้:

* **Docker Image และไฟล์ตั้งค่า (.env)**: อ้างอิงและดึงซอร์สโค้ดหลักมาจากผู้พัฒนาต้นฉบับ
* **ผู้พัฒนาต้นฉบับ**: [@thijsvanloef](https://github.com/thijsvanloef)
* **ลิงก์โปรเจกต์ต้นแบบ**: [palworld-server-docker](https://github.com/thijsvanloef/palworld-server-docker)

*ขอขอบคุณผู้พัฒนาต้นฉบับสำหรับการดูแลรักษาระบบ Docker Image และโครงสร้างไฟล์ตั้งค่าต่างๆ*

## [EN] Credits & Technical References

This project heavily relies on and references the infrastructure provided by the original creator:

* **Base Docker Image & Environment Configurations**: Inherited and customized from the upstream repository.
* **Original Creator**: [@thijsvanloef](https://github.com/thijsvanloef)
* **Original Repository**: [palworld-server-docker](https://github.com/thijsvanloef/palworld-server-docker)

*Special thanks to the original author for maintaining the base images and configuration templates.*
