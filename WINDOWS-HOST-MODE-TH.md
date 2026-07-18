# Windows Host-native Mode 1.1.0

Windows mode ออกแบบให้ `PalServer.exe` รันบน Windows โดยตรง ขณะที่ Dashboard รันใน Docker Desktop เพื่อรักษาความสามารถด้าน UI, Config, Export/Import และ Maintenance workflow

---

## 1. Component

| Component | Runtime | ตำแหน่ง |
|---|---|---|
| SteamCMD | Windows native | `runtime/steamcmd-windows/` |
| PalServer | Windows native | `PALWORLD_HOST_DIR` |
| Host Agent | PowerShell background | `run/windows/PalworldHostAgent.ps1` |
| Dashboard | Docker container | `palworld-dashboard-host` |
| Control IPC | Shared files | `runtime/control/` |

---

## 2. Path requirement

ใช้ path สั้น เช่น:

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
```

Manager คำนวณ projected path ของ Player backup และ:

- เตือนเมื่อใกล้ 220 ตัวอักษร
- ปฏิเสธเมื่อ projected path ตั้งแต่ 248 ตัวอักษร

ย้ายของเดิม:

```text
run\windows\09-Move-Server-To-Short-Path.bat
```

สคริปต์:

1. หยุด Server/Agent/Dashboard
2. ตรวจ Destination ต้องว่าง
3. ใช้ `robocopy /E /COPY:DAT /DCOPY:DAT /XJ`
4. ไม่ลบ Source
5. แก้ `.env.host`
6. Patch Config ที่ปลายทาง

ทดสอบ Save ก่อนลบ Source เดิม

---

## 3. Setup

```text
run\windows\00-Setup.bat
```

### `.env.host` ขั้นต่ำ

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
PALWORLD_ADMIN_PASSWORD=CHANGE_THIS
DASHBOARD_PASSWORD=CHANGE_THIS
```

### SteamCMD flow

```text
steamcmd.exe
  +force_install_dir D:\PalServer
  +login anonymous
  +app_update 2394010 validate
  +quit
```

`PALWORLD_STEAMCMD_RETRIES=2` ทำให้ retry อัตโนมัติ SteamCMD บางครั้ง reconfigure depot ในรอบแรกแล้วดาวน์โหลดได้ในรอบถัดไป

### Config flow

ถ้ายังไม่มี Config ระบบ copy:

```text
DefaultPalWorldSettings.ini
-> Pal/Saved/Config/WindowsServer/PalWorldSettings.ini
```

จากนั้น Patch ค่าใน `.env.host` และสร้าง backup ใน:

```text
runtime/config-backups/
```

---

## 4. Start flow

```text
run\windows\01-Start-All.bat
```

### Host Agent

Manager เปิด Agent แบบ Hidden process และ redirect log:

```text
runtime/logs/host-agent.out.log
runtime/logs/host-agent.err.log
```

PID:

```text
runtime/control/agent.pid
```

Heartbeat:

```text
runtime/control/status.json
```

### Server process

Agent เรียก:

```text
PalServer.exe -port=8211 -queryport=27015 [-publiclobby] [performance args]
```

Agent ตรวจ process name หลายรูปแบบเพื่อรองรับชื่อ binary ของเกมที่เปลี่ยนได้

### REST readiness

Manager poll:

```text
http://127.0.0.1:<REST_PORT>/v1/api/info
```

ด้วย Basic Auth `admin:<PALWORLD_ADMIN_PASSWORD>` จนกว่าจะ Online หรือ timeout

### Dashboard readiness

Manager start `dashboard-host`, รอ `/health` และทดสอบจากใน container ไปยัง:

```text
http://host.docker.internal:<REST_PORT>/v1/api/info
```

---

## 5. คำสั่งและผลกระทบ

| คำสั่ง | Server | Agent | Dashboard |
|---|---:|---:|---:|
| `00-Setup.bat` | ไม่เปิด | ไม่เปิด | ไม่เปิด |
| `01-Start-All.bat` | เปิด | เปิด | เปิด |
| `02-Start-Server.bat` | เปิด | เปิด | ไม่เปลี่ยน |
| `03-Start-Dashboard.bat` | ไม่เปลี่ยน | ไม่จำเป็นสำหรับอ่าน REST แต่จำเป็นกับ lifecycle | เปิด |
| `04-Status.bat` | ตรวจ | ตรวจ | ตรวจ |
| `05-Logs.bat` | อ่าน log | อ่าน log | ไม่ติดตาม Docker log |
| `06-Update.bat` | หยุด/Update/เปิด | เปิด | ไม่เปลี่ยน |
| `07-Stop-All.bat` | หยุด | หยุด | down |
| `08-Doctor.bat` | อาจ Start เพื่อทดสอบ | เปิด | เปิด |
| `09-Move...bat` | หยุด | หยุด | down |

> Doctor เป็น active test และอาจเปิด Server/Dashboard หากยังไม่ทำงาน

---

## 6. `.env.host` ที่สำคัญ

### Host and network

```dotenv
PALWORLD_HOST_DIR=D:/PalServer
PALWORLD_HOST_PORT=8211
PALWORLD_HOST_QUERY_PORT=27015
PALWORLD_HOST_REST_PORT=8212
PALWORLD_HOST_RCON_PORT=25575
PALWORLD_HOST_PUBLIC_LOBBY=true
PALWORLD_HOST_API_HOST=host.docker.internal
```

### Startup

```dotenv
PALWORLD_HOST_PERF_ARGS=false
PALWORLD_HOST_WORKER_THREADS=
PALWORLD_HOST_EXTRA_ARGS=
```

`PALWORLD_HOST_EXTRA_ARGS` ถูก tokenize ด้วย PowerShell parser หลีกเลี่ยง quote ซับซ้อนและทดสอบทีละ argument

### Timeouts

```dotenv
PALWORLD_HOST_STOP_TIMEOUT_SECONDS=60
PALWORLD_HOST_START_TIMEOUT_SECONDS=900
PALWORLD_EXTERNAL_CONTROL_TIMEOUT=90
```

### Dashboard

```dotenv
DASHBOARD_BIND_ADDRESS=0.0.0.0
DASHBOARD_PORT=8080
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=...
```

ตัวแปรครบดู `CONFIG-REFERENCE-TH.md`

---

## 7. Firewall

ต้องพิจารณา 3 เส้นทาง:

1. ผู้เล่น → UDP 8211
2. Dashboard container → Windows TCP 8212
3. ผู้ดูแล → TCP 8080

ตรวจ Host REST:

```powershell
$token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:<PASSWORD>"))
Invoke-WebRequest http://127.0.0.1:8212/v1/api/info -Headers @{Authorization="Basic $token"}
```

ตรวจจาก container:

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin exec -T dashboard-host python3 -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8212').status)"
```

คำสั่งตัวอย่างข้างบนไม่ใส่ Auth จึงอาจตอบ 401 ซึ่งยังยืนยันว่า network path ถึงแล้ว; Doctor ทดสอบพร้อม Auth ให้ครบ

VPN, Antivirus และ Endpoint Security อาจบล็อก `host.docker.internal` หรือ vEthernet interface

---

## 8. Export/Import

Dashboard mount:

```text
PALWORLD_HOST_DIR -> /palworld-data
runtime/control   -> /host-control
dashboard/data   -> /data
```

Export/Import จึงอ่าน World บน Windows ได้โดยตรง และใช้ Agent Start/Stop process

เมื่อนำ Save จาก Linux/macOS มาใช้บน Windows ให้เลือก Import แบบ **สลับ/ย้าย World และผู้เล่น (`world_only`)** เพื่อแทนที่เฉพาะ `SaveGames` และรักษา `Config/WindowsServer` ที่ Setup สร้างไว้ หากเลือก Full restore Config Windows อาจถูกลบหรือถูกแทนด้วยชุดจากระบบอื่น

เงื่อนไข:

- Host Agent heartbeat ต้องทำงาน
- `PALWORLD_HOST_DIR` ต้อง mount ได้ใน Docker Desktop
- Drive ต้องถูกแชร์/อนุญาตใน Docker Desktop
- พื้นที่ Disk ต้องพอสำหรับ staging + safety backup

---

## 9. Safe shutdown

### แนะนำ

ใช้ Dashboard Stop/Maintenance เพราะมีลำดับ:

```text
announce -> save -> REST shutdown -> agent stop -> operation -> agent start -> wait REST
```

### Direct script

`07-Stop-All.bat` ส่ง stop ไป Agent โดยตรง Agent รอ process ออกและ fallback เป็น `taskkill` เมื่อ timeout จึงควร Save World ก่อนเมื่อมีผู้เล่น

---

## 10. Save failure

อาการ:

```text
Failed to save. Failed copy from backup.
```

ตรวจ:

1. Path สั้นหรือไม่
2. Write permission
3. Antivirus quarantine/Controlled Folder Access
4. Disk free
5. File lock จาก backup/sync software
6. `Pal/Saved/SaveGames` ถูก Read-only หรือไม่

Doctor ตรวจ path และ temporary write แต่ไม่สามารถยืนยันทุก file lock ระหว่างเกมทำงานได้

---

## 11. Troubleshooting

### Script เปิดแล้วปิด

รันจาก CMD:

```bat
run\windows\08-Doctor.bat
```

ทุก `.bat` เรียก `_Run-Manager.bat` ซึ่ง pause เมื่อ exit code ไม่เป็น 0

### Agent หยุดทันที

ดู:

```text
runtime/logs/host-agent.err.log
```

ลบ stale control files ได้เมื่อทุก process หยุดแล้ว:

```bat
del /q runtime\control\request-*.json runtime\control\response-*.json runtime\control\status.json runtime\control\agent.pid
```

### Host REST Online แต่ Dashboard Offline

- ตรวจ `PALWORLD_HOST_API_HOST=host.docker.internal`
- รัน Doctor
- ตรวจ Windows Firewall/EDR
- Recreate dashboard-host

### SteamCMD Missing configuration

ปล่อยให้ retry ทำงาน หากทุก retry ล้ม:

- ปิด Steam client ชั่วคราว
- ตรวจ Internet/Proxy
- ลบเฉพาะ `runtime/steamcmd-windows/appcache` แล้วลองใหม่
- ตั้ง `PALWORLD_STEAMCMD_VALIDATE=false` ชั่วคราวเมื่อเป็นการ update ที่ไฟล์เดิมสมบูรณ์

อย่าลบ `PALWORLD_HOST_DIR` เพราะเป็น World หลัก


### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว
