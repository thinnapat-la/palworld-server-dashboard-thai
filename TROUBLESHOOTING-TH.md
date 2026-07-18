# Troubleshooting 1.1.0

ใช้เอกสารนี้โดยเริ่มจากอาการ ไม่ควรแก้หลายค่าพร้อมกัน

---

## 1. Dashboard เข้าไม่ได้

### Linux/macOS

```bash
docker compose --profile admin ps
docker compose --profile admin logs --tail=200 dashboard docker-proxy
curl -v http://127.0.0.1:8080/health
```

ตรวจ port conflict:

```bash
ss -lntp | grep ':8080'
```

### Windows

```text
run\windows\04-Status.bat
run\windows\08-Doctor.bat
```

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin ps
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin logs --tail=200 dashboard-host
```

---

## 2. REST API Offline

### แยกปัญหา

1. Runtime เปิดหรือไม่
2. REST listen หรือไม่
3. Auth ถูกหรือไม่
4. Dashboard network ถึงหรือไม่

### Windows Host test

```powershell
$token=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:<PASSWORD>"))
Invoke-RestMethod http://127.0.0.1:8212/v1/api/info -Headers @{Authorization="Basic $token"}
```

- Host test fail: Config/password/server problem
- Host test pass แต่ Doctor step 9 fail: Firewall/VPN/EDR/host.docker.internal

### Docker mode

```bash
docker compose exec palworld sh -lc 'ss -lnt 2>/dev/null | grep 8212 || true'
docker compose --profile admin exec dashboard python3 -c "import urllib.request; print(urllib.request.urlopen('http://palworld:8212/v1/api/info').status)"
```

คำสั่งไม่มี Auth อาจตอบ 401 แต่แปลว่า network ถึง

---

## 3. Windows Setup: SteamCMD Missing configuration

หากเป็น attempt แรกและมี retry ให้รอดูผลสุดท้าย SteamCMD อาจ reconfigure แล้วดาวน์โหลดสำเร็จใน attempt ถัดไป

ถ้าทุก attempt ล้ม:

- ตรวจ Internet/Proxy/DNS
- ตรวจ Antivirus ไม่ block `steamcmd.exe`
- ลอง `PALWORLD_STEAMCMD_VALIDATE=false`
- ลบ `runtime/steamcmd-windows/appcache` ไม่ใช่ Host directory
- รัน `06-Update.bat`

ห้ามลบ `D:/PalServer/Pal/Saved`

---

## 4. Windows Script เปิดแล้วปิด

สคริปต์รุ่นนี้ pause เมื่อ error หากยังปิด ให้เปิด CMD ใน root แล้วรัน:

```bat
run\windows\08-Doctor.bat
```

ดู:

```text
runtime/logs/host-agent.err.log
runtime/logs/host-agent.out.log
```

---

## 5. Windows Save failure

อาการ:

```text
Failed to save. Failed copy from backup.
```

ตรวจ:

```text
PALWORLD_HOST_DIR=D:/PalServer
```

รัน:

```text
run\windows\09-Move-Server-To-Short-Path.bat
run\windows\08-Doctor.bat
```

ตรวจ Disk/ACL:

```bat
dir D:\PalServer\Pal\Saved
icacls D:\PalServer
```

ปิด OneDrive/backup scanner ชั่วคราวเพื่อทดสอบ file lock

---

## 6. Host Agent Offline

ตรวจ PID/status:

```bat
type runtime\control\agent.pid
type runtime\control\status.json
```

เปิด Agent ผ่าน:

```text
run\windows\02-Start-Server.bat
```

ถ้า Server รันอยู่ Agent จะตรวจพบ process และไม่เปิดซ้ำ

---

## 7. World ใหม่หรือข้อมูลหายหลังเปลี่ยน Volume

หยุดทันที อย่าสร้างของใหม่ใน World

```bash
docker compose --profile admin down
docker volume ls
docker volume inspect palworld-data
```

ค้นหา World directories:

```bash
docker run --rm -v palworld-data:/data alpine:3.20 find /data/Pal/Saved/SaveGames -maxdepth 4 -type d
```

ตรวจ `PALWORLD_VOLUME_NAME` และ project compose name

---

## 8. Dashboard Config ถูกเขียนทับ

Docker mode:

```dotenv
PALWORLD_DISABLE_GENERATE_SETTINGS=true
```

Recreate:

```bash
docker compose up -d --no-deps --force-recreate palworld
```

Windows: key หลัก REST/RCON/Admin/Port ถูก patch จาก `.env.host` โดย design

---

## 9. `pal_logger.py` ยังรัน

```bash
docker top palworld-server -eo pid,ppid,args
```

ตั้ง:

```dotenv
LOG_FILTER_ENABLED=false
```

แล้ว:

```bash
docker compose up -d --no-deps --force-recreate palworld
```

---

## 10. Export/Import failed

ตรวจ:

```text
dashboard/data/jobs.json
dashboard/data/exports/
dashboard/data/imports/
dashboard/data/staging/
```

Docker logs:

```bash
docker compose --profile admin logs --tail=300 dashboard
```

Windows:

```bat
docker compose --env-file .env.host -f docker-compose.host.yml --profile host-admin logs --tail=300 dashboard-host
```

สาเหตุทั่วไป:

- Agent offline
- Runtime stop timeout
- Disk เต็ม
- ZIP structure ไม่ถูก
- Expanded size เกิน limit
- Permission/ACL
- Dashboard ถูกปิดกลาง Job

---

## 11. Server ใช้ RAM สูง

Palworld เก็บ World/actor data ใน memory และการใช้ RAM อาจเพิ่มตามเวลา ตรวจทั้ง process/container และ available memory

Docker:

```bash
docker stats palworld-server
free -h
```

Windows:

```powershell
Get-Process PalServer* | Select-Object Id,CPU,WorkingSet64,PrivateMemorySize64
```

อย่าตั้ง hard memory limit ต่ำเพื่อบังคับลด RAM เพราะอาจทำให้ crash/OOM

---

## 12. มอนวาร์ปหรือ rubber-banding

แยกตัวแปร:

1. ทดสอบผู้เล่นเดียว
2. ปิด Dashboard/proxy ชั่วคราว
3. ตรวจ CPU core และ disk hitch
4. เปรียบเทียบ Windows native กับ Docker Linux
5. ปรับ Engine ทีละค่า
6. ทดสอบ World ใหม่

Dashboard polling ไม่ใช่ต้นเหตุหลักหากปิดแล้วอาการยังมี แต่สามารถเพิ่ม request/log เล็กน้อย

---

## 13. Port conflict

Windows:

```bat
netstat -ano | findstr :8211
netstat -ano | findstr :8212
netstat -ano | findstr :8080
```

Linux:

```bash
ss -lunp | grep ':8211'
ss -lntp | grep -E ':8212|:8080'
```

เปลี่ยน port ให้ครบทั้ง runtime, firewall และ client connection

---

## 14. ก่อนขอความช่วยเหลือ

เก็บข้อมูลนี้:

- ระบบปฏิบัติการ
- โหมดใช้งาน
- `.env` ที่ลบรหัส/Webhook แล้ว
- `docker compose config` ที่ลบ secret แล้ว
- Status/Doctor output
- Log 100-300 บรรทัดก่อน error
- ขนาด World และพื้นที่ว่าง
- ขั้นตอนที่ทำให้เกิดซ้ำ


## Import mode ไม่รองรับไฟล์

### ZIP ไม่มี `SaveGames`

ข้อความอาจเป็น:

```text
ZIP ไม่มี Pal/Saved/SaveGames สำหรับโหมดสลับ World/ผู้เล่น
```

เลือก `full_restore` เฉพาะเมื่อ ZIP เป็น Full backup ที่ถูกต้อง หรือสร้าง Export ใหม่จาก Server ต้นทาง

### ZIP ไม่มี Config ของระบบปลายทาง

ตัวอย่าง: Import ZIP จาก Linux เข้า Windows แล้วเลือก `config_only` จะไม่มี `Config/WindowsServer` ระบบจะปฏิเสธโดยตั้งใจ ให้เลือก `world_only` สำหรับย้าย World และตั้ง Config Windows ที่เครื่องปลายทางเอง

### Import สำเร็จแต่ Config ไม่เปลี่ยน

ตรวจว่าเลือก `world_only` หรือไม่ โหมดนี้ตั้งใจรักษา Config ปลายทางไว้ หากต้องกู้ Config ให้ใช้ `config_only` กับ archive ที่มาจาก platform เดียวกัน

## Import สำเร็จแต่ผู้เล่นถูกให้สร้างตัวละครใหม่

ตรวจ `GameUserSettings.ini` ของระบบปลายทางและชื่อโฟลเดอร์ใต้ `Pal/Saved/SaveGames/0/` ค่า `DedicatedServerName` ต้องตรงกับ World ID ที่มี `Level.sav` และ `Players/*.sav`

ตัวอย่าง:

```ini
DedicatedServerName=A87F921841464697B0832178618B7F46
```

รุ่น 1.1.0 ปัจจุบันแก้ค่านี้อัตโนมัติในโหมด `world_only` และจะไม่ตั้ง Job เป็น `completed` จนกว่าจะตรวจ World ID หลัง Start ผ่าน หาก World ถูกต้องแล้วยังสร้างตัวใหม่ ให้ตรวจว่าเข้าด้วยบัญชี/แพลตฟอร์มเดิม เพราะ Player UID คนละระบบอาจต้องทำ UID mapping แยกต่างหาก
