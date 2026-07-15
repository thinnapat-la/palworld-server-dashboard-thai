# คู่มือใช้งาน Palworld Server Dashboard ฉบับเต็ม

## ขอบเขตเอกสาร

หัวข้อครอบคลุมตั้งแต่การเตรียมเครื่อง ติดตั้ง ตั้งค่า เปิด GameData API ใช้ทุกเมนู สำรอง/ย้ายข้อมูล กู้คืน ตรวจสอบความปลอดภัย อัปเดต และแก้ปัญหา

> **ข้อสำคัญ:** เก็บ State, Ban history, Import และ Export ใน `dashboard/data/`

---

# ภาค 1: ภาพรวมระบบ

## 1.1 วัตถุประสงค์ของ

ทำหน้าที่เป็นชั้นบริหาร Palworld Dedicated Server ผ่านเว็บ โดยเชื่อมต่อกับ:

1. **Palworld REST API** สำหรับอ่าน Info, Metrics, Players, Settings และส่งคำสั่งผู้ดูแล
2. **Docker Engine API ผ่าน Docker Socket Proxy** สำหรับตรวจสถานะ เปิด และหยุดคอนเทนเนอร์ `palworld-server`
3. **ไฟล์ข้อมูลเซฟบน Host** สำหรับ Export, Import, Safety Backup และ Rollback
4. **Discord Webhook** สำหรับแจ้งเหตุการณ์สำคัญของ Dashboard และเหตุการณ์จากอิมเมจ Palworld

Dashboard ไม่ใช่ระบบแทนที่ Palworld Server และไม่แก้ข้อมูลเกมผ่านฐานข้อมูลโดยตรง การทำงานทั้งหมดอาศัย REST API, Docker API และไฟล์ `Pal/Saved/`

## 1.2 แผนผังการเชื่อมต่อ

```text
ผู้ดูแลผ่าน Browser
        |
        | HTTP/HTTPS จาก Reverse Proxy
        v
palworld-dashboard :8080
        |-------------------------|
        |                         |
        | REST API                | Docker API แบบจำกัดสิทธิ์
        v                         v
palworld :8212              docker-proxy :2375
        |                         |
        |                         v
        |                  /var/run/docker.sock
        |
        +---- Shared volume ./palworld <---- Dashboard อ่าน/เขียน Pal/Saved
```

## 1.3 บริการใน Compose

### `palworld`

- ใช้อิมเมจ `thijsvanloef/palworld-server-docker:latest`
- ชื่อคอนเทนเนอร์ `palworld-server`
- เก็บข้อมูลทั้งหมดใน `./palworld:/palworld/`
- เปิดเกมที่ `8211/udp`
- เปิด Query ที่ `27015/udp`
- เปิด RCON ที่ `25575/tcp`
- ผูก REST API เฉพาะ Host localhost ที่ `127.0.0.1:8212`
- ใช้ Healthcheck ตรวจ Process `PalServer-Linux-Test`

### `docker-proxy`

- ใช้อิมเมจ `tecnativa/docker-socket-proxy:latest`
- Mount Docker socket แบบ Read-only
- เปิดเฉพาะหมวด API ที่ต้องใช้คือ `CONTAINERS`, `POST` และ `PING`
- ไม่ Publish พอร์ตออก Host

### `dashboard`

- Build จาก `dashboard/Dockerfile`
- ใช้ Python 3.12 Alpine และไม่มี Dependency ภายนอก
- Root filesystem เป็น Read-only
- ใช้ `/tmp` เป็น `tmpfs` 64 MB
- Mount `./palworld` เป็น Read-write เพราะ Import ต้องแทนที่ข้อมูลเซฟ
- Mount `./dashboard/data` เป็น Read-write เพื่อเก็บ State และไฟล์ ZIP
- Mount `server.py` และ `index.html` แบบ Read-only เพื่อให้แก้ Source แล้ว Restart ได้ง่าย

## 1.4 ข้อมูลที่เก็บถาวร

```text
├── .env
├── docker-compose.yml
├── palworld/
│   ├── Pal/
│   │   └── Saved/
│   ├── backups/
│   └── ...
└── dashboard/
    ├── server.py
    ├── index.html
    └── data/
        ├── state.json
        ├── bans.json
        ├── maintenance.json      # มีเฉพาะช่วงงาน Maintenance หรือ Failed marker
        ├── exports/
        └── imports/
```

- `state.json`: คิวและประวัติงานสูงสุด 500 รายการ
- `bans.json`: Active Ban ที่ Dashboard รู้จักและประวัติสูงสุด 1,000 รายการ
- `maintenance.json`: Marker ขั้นตอนล่าสุดของงานที่กำลังทำหรือล้มเหลว
- `exports/`: ไฟล์ Export และ Safety Backup
- `imports/`: ไฟล์ที่อัปโหลดผ่านหน้าเว็บและผ่านการตรวจเบื้องต้นแล้ว

---

# ภาค 2: ความต้องการและการเตรียมเครื่อง

## 2.1 สเปกแนะนำ

แนวทางจากเอกสาร Palworld Server ปัจจุบันคือ CPU 4 Core, RAM 16 GB และแนะนำมากกว่า 32 GB สำหรับการใช้งานที่ใหญ่ขึ้น โดย 8 GB อาจเปิดได้แต่มีความเสี่ยง Out of Memory มากกว่า ควรใช้ SSD เพราะ I/O ที่ช้าสามารถเพิ่มความเสี่ยงต่อปัญหาเซฟ

ต้องเผื่อพื้นที่เพิ่มจากตัวเกม เนื่องจาก Export และ Import อาจมีไฟล์ซ้ำหลายชุดพร้อมกัน:

```text
พื้นที่ขั้นต่ำระหว่าง Import โดยประมาณ
= เซฟปัจจุบัน
+ ZIP Import
+ ไฟล์แตกใน Staging
+ Safety Backup ZIP
+ Rollback copy ชั่วคราว
+ พื้นที่เผื่อระบบไฟล์
```

จึงควรเหลือพื้นที่มากกว่าขนาด `Pal/Saved/` อย่างน้อย 3-5 เท่าในช่วง Import ขนาดใหญ่

## 2.2 ระบบปฏิบัติการและซอฟต์แวร์

ตรวจสอบ:

```bash
uname -m
docker --version
docker compose version
```

ควรได้สถาปัตยกรรม 64-bit และ Docker Compose V2

## 2.3 ตรวจ UID/GID ของผู้ใช้ Host

Compose ค่าเริ่มต้นใช้:

```yaml
PUID: "1000"
PGID: "1000"
```

ตรวจค่าจริง:

```bash
id
id -u
id -g
```

หากผู้ใช้ที่ดูแลไฟล์ไม่ใช่ `1000:1000` ให้แก้ทั้ง:

- `PUID` และ `PGID` ใน service `palworld`
- `PALWORLD_PUID` และ `PALWORLD_PGID` ใน service `dashboard`

ค่าทั้งสองฝั่งต้องสอดคล้องกัน เพื่อให้ไฟล์หลัง Import ถูกคืน Owner ให้ Palworld อ่านเขียนได้

## 2.4 พอร์ตและ Firewall

| พอร์ต | โปรโตคอล | ใช้ทำอะไร | ควรเปิดจากที่ใด |
|---|---|---|---|
| `8211` | UDP | เกมหลัก | Internet/LAN ตามกลุ่มผู้เล่น |
| `27015` | UDP | Query/Community listing | Internet เมื่อใช้งาน |
| `25575` | TCP | RCON | LAN/VPN หรือ localhost เท่านั้น |
| `8212` | TCP | Palworld REST API | Host localhost เท่านั้นตาม Compose |
| `8080` | TCP | Dashboard | LAN/VPN หรือ Reverse Proxy เท่านั้น |

ตัวอย่าง UFW:

```bash
sudo ufw allow 8211/udp
sudo ufw allow 27015/udp
sudo ufw allow from 192.168.0.0/16 to any port 8080 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 25575 proto tcp
sudo ufw status numbered
```

ปรับ Subnet ให้ตรงกับเครือข่ายจริง

## 2.5 DNS, NAT และ Port Forward

หากผู้เล่นจาก Internet เชื่อมต่อ:

1. Forward Router UDP `8211` ไป IP ของ Host
2. Forward UDP `27015` เมื่อใช้ Query/Community Server
3. ห้าม Forward `8212` และไม่ควร Forward `25575`/`8080` โดยตรง
4. หาก `PUBLIC_IP` ตรวจอัตโนมัติผิด ให้กรอก Public IP เอง
5. `PUBLIC_PORT` เป็นพอร์ตที่ประกาศต่อภายนอก แต่ไม่ได้เปลี่ยนพอร์ต Listen ภายใน

---

# ภาค 3: การติดตั้ง

## 3.1 เตรียม `.env`

หากไม่มี `.env`:

```bash
cp .env.example .env
```

เปิดแก้:

```bash
nano .env
```

ค่าขั้นต่ำที่ต้องเปลี่ยน:

```dotenv
PALWORLD_SERVER_PASSWORD=CHANGE_ME_PLAYER_PASSWORD
PALWORLD_ADMIN_PASSWORD=CHANGE_ME_ADMIN_PASSWORD
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=CHANGE_ME_DASHBOARD_PASSWORD
```

แนวทางรหัสผ่าน:

- ใช้อย่างน้อย 16-24 ตัวอักษรสำหรับ Admin/Dashboard
- ไม่ใช้รหัสเดียวกันทั้ง Player, Admin และ Dashboard
- หลีกเลี่ยงช่องว่างท้ายบรรทัด
- ห้าม Commit `.env`

## 3.2 ตั้ง Discord

### ขั้นตอนการสร้าง Discord Webhook URL 
[ชื่อเซิร์ฟเวอร์] → [Server Settings] → [Integrations] → [Webhooks] → [New Webhook] → [Copy Webhook URL]

หากใช้งาน ให้สร้าง Webhook แยกตามช่อง:

```dotenv
DISCORD_INFORMATION_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN
DISCORD_SESSION_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN
DISCORD_WELCOME_WEBHOOK_URL=
DISCORD_INVITE_URL=https://discord.gg/INVITE
```

`discord.gg` เป็น Invite Link ไม่ใช่ Webhook URL

หากไม่ใช้ Discord:

```dotenv
DISCORD_INFORMATION_WEBHOOK_URL=
DISCORD_SESSION_WEBHOOK_URL=
DISCORD_WELCOME_WEBHOOK_URL=
DISCORD_INVITE_URL=
```

## 3.3 สร้างโฟลเดอร์

```bash
mkdir -p dashboard/data/exports dashboard/data/imports
mkdir -p palworld
```

ตรวจสิทธิ์:

```bash
sudo chown -R 1000:1000 palworld dashboard/data
```

เปลี่ยน `1000:1000` ตาม UID/GID จริง

## 3.4 Pull และ Start

```bash
docker compose pull palworld docker-proxy
docker compose up -d --build
```

ตรวจ:

```bash
docker compose ps
docker compose logs -f --tail=200
```

## 3.5 ตรวจสุขภาพ

```bash
curl http://127.0.0.1:8080/health
```

ตรวจ REST API จาก Host:

```bash
curl -u 'admin:PALWORLD_ADMIN_PASSWORD' \
  http://127.0.0.1:8212/v1/api/info
```

แทน `PALWORLD_ADMIN_PASSWORD` ด้วยค่าจริง ระวัง Shell history

## 3.6 เปิดหน้า Dashboard

```text
http://SERVER_IP:8080
```

หากใช้ Reverse Proxy ให้ตั้ง `DASHBOARD_BIND_ADDRESS=127.0.0.1` และ Proxy เข้า `127.0.0.1:8080`

## [optional] เปิด World Actor Snapshot / GameData API

กำหนด:

```dotenv
ENABLE_GAMEDATA_API=true
```

Compose ชุดเอกสารนี้มี Mapping:

```yaml
ENABLE_GAMEDATA_API: "${ENABLE_GAMEDATA_API:-true}"
```

ตัวแปรนี้มีใน `thijsvanloef/palworld-server-docker` ตั้งแต่รุ่น `2.6.0` และทำให้ startup เปิด GameData Bridge สำหรับคำสั่ง `game-data`

> การตั้ง `REST_API_ENABLED=true` อย่างเดียวไม่เพียงพอสำหรับ `/v1/api/game-data`

---

# ภาค 4: ตั้งค่า GameData API และ World Actor Snapshot แบบละเอียด

## 4.1 GameData API คืออะไร

Palworld REST API ปกติมี endpoint เช่น `info`, `metrics`, `players`, `settings`, `announce`, `save`, `kick`, `ban`, `unban`, `shutdown` และ `stop` ส่วน `game-data` เป็นข้อมูล Snapshot ของ Actor ในโลกและต้องเปิด GameData Bridge เพิ่ม

ในปุ่ม **World Actor Snapshot** เรียกเส้นทาง:

```text
Browser -> GET /api/snapshot ของ Dashboard
Dashboard -> GET /v1/api/game-data ของ Palworld
```

Dashboard ส่ง JSON Snapshot ทั้งก้อนไปยัง Browser แล้วหน้าเว็บแสดงเพียง:

- เวลา Snapshot
- FPS
- Average FPS
- จำนวน Actor ที่ตรวจพบ
- ขนาด JSON โดยประมาณ

ปุ่มนี้ไม่ใช่ Backup, ไม่ Save World, ไม่สร้างไฟล์ และไม่ Restore ข้อมูล

## 4.2 เงื่อนไขที่ต้องครบ

1. `REST_API_ENABLED=true`
2. `REST_API_PORT=8212`
3. `ENABLE_GAMEDATA_API=true`
4. อิมเมจ `thijsvanloef/palworld-server-docker` รุ่น 2.6.0 ขึ้นไป
5. คอนเทนเนอร์ถูก Recreate หลังเปลี่ยน Environment
6. Palworld Server เปิดและ REST API พร้อม

## 4.3 ขั้นตอนเปิดจากศูนย์

```bash
nano .env
```

ตรวจให้มี:

```dotenv
ENABLE_GAMEDATA_API=true
```

Pull และ Recreate:

```bash
docker compose pull palworld
docker compose up -d --force-recreate palworld
```

ดู Log:

```bash
docker compose logs -f palworld
```

ตรวจ Environment จริงในคอนเทนเนอร์:

```bash
docker inspect palworld-server \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | sort | grep -E '^(REST_API_ENABLED|REST_API_PORT|ENABLE_GAMEDATA_API)='
```

ควรได้:

```text
ENABLE_GAMEDATA_API=true
REST_API_ENABLED=true
REST_API_PORT=8212
```

## 4.4 ทดสอบด้วย rest-cli

อิมเมจที่รองรับมีคำสั่ง:

```bash
docker exec palworld-server rest-cli game-data
```

ข้อมูลอาจยาวมาก จึงควรทดสอบเพียงส่วนต้น:

```bash
docker exec palworld-server sh -lc 'rest-cli game-data | head -c 1000; echo'
```

หรือกดจาก Dashboard โดยตรง

## 4.5 Error ที่พบบ่อย

### `HTTP 404: PalGameDataBridge GameData API is not enabled`

สาเหตุหลัก:

- ไม่มี `ENABLE_GAMEDATA_API=true`
- ใช้อิมเมจเก่ากว่า 2.6.0
- เปลี่ยน `.env` แต่ไม่ได้ Recreate คอนเทนเนอร์

แก้:

```bash
grep '^ENABLE_GAMEDATA_API=' .env
docker compose pull palworld
docker compose up -d --force-recreate palworld
```

### `HTTP 401`

รหัส `PALWORLD_ADMIN_PASSWORD` ที่ Dashboard ใช้ไม่ตรงกับ `ADMIN_PASSWORD` ของ Palworld

ตรวจ:

```bash
docker inspect palworld-server --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep '^ADMIN_PASSWORD='

docker inspect palworld-dashboard --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep '^PALWORLD_ADMIN_PASSWORD='
```

### `HTTP 502` หรือ Connect refused

- Palworld ยังเริ่มไม่เสร็จ
- REST API ปิด
- Container หยุด
- Network ใน Compose ผิดหรือ service name เปลี่ยน

ตรวจ:

```bash
docker compose ps
docker compose logs --tail=300 palworld
docker compose exec dashboard python3 - <<'PY'
import urllib.request
print(urllib.request.urlopen('http://palworld:8212/v1/api/info', timeout=5).status)
PY
```

คำสั่งทดสอบสุดท้ายจะได้ `401` หากเชื่อมถึง API แต่ไม่มี Authorization ซึ่งถือว่า Docker network ทำงาน

## 4.6 ผลกระทบด้านทรัพยากร

- Snapshot อาจมี JSON ขนาดใหญ่ตามจำนวน Actor
- Dashboard โหลดเฉพาะเมื่อกด ไม่ Poll อัตโนมัติ
- Browser ต้องรับ JSON ทั้งก้อน จึงอาจใช้ RAM และ Network ชั่วคราว
- ไม่ควรกดซ้ำถี่ ๆ ระหว่างเซิร์ฟเวอร์โหลดสูง
- ควรใช้ผ่าน LAN/VPN เท่านั้น เพราะข้อมูลโลกอาจมีรายละเอียดที่ไม่ควรเผยแพร่

## 4.7 ปิดฟังก์ชัน

```dotenv
ENABLE_GAMEDATA_API=false
```

จากนั้น:

```bash
docker compose up -d --force-recreate palworld
```

ปุ่ม Snapshot ะตอบ Error 404 ว่า GameData API ไม่ได้เปิด

---

# ภาค 5: การใช้งาน Dashboard ทุกเมนู

## 5.1 การ Login และ Refresh

Dashboard ใช้ HTTP Basic Authentication หาก `DASHBOARD_PASSWORD` ไม่ว่าง Browser จะแสดงกล่อง Login

หน้าเว็บ Poll ข้อมูลทุก `DASHBOARD_REFRESH_SECONDS` ค่าเริ่มต้น 15 วินาที แต่ Backend บังคับขั้นต่ำ 5 วินาที

ปุ่ม **รีเฟรช** เรียกข้อมูลทันทีโดยไม่ต้องรอรอบ Poll

## 5.2 เมนูภาพรวม

### ผู้เล่นออนไลน์

อ่านจาก `/v1/api/players` และนับจำนวนรายการ หาก REST API ไม่พร้อมอาจแสดง `0` หรือไม่มีข้อมูล โดย Error จริงจะอยู่ในผล `/api/status`

### Server FPS และ Frame time

อ่านจาก `/v1/api/metrics` ชื่อ Field อาจเปลี่ยนตามเวอร์ชัน Palworld; หน้าเว็บมี Logic รองรับชื่อที่ใช้บ่อย

### Uptime

อ่านจาก Metrics/Info ตามข้อมูลที่ API ส่งกลับ ไม่ใช่ Uptime ของ Host

### Container

อ่านจาก Docker API:

- `running`, `exited`, `created` เป็นต้น
- Health: `starting`, `healthy`, `unhealthy`, `none`

Palworld อาจเชื่อมต่อได้ก่อน Health เปลี่ยนเป็น `healthy` เพราะ `start_period` ตั้งไว้ 5 นาที

### Maintenance

แสดงงานที่กำลังทำก่อน หากไม่มีงานกำลังทำจะแสดงงาน Pending ที่ถึงคิวเร็วที่สุด ดังนั้นคำว่า Maintenance ในภาพรวมหมายถึง “งาน Import/Export ที่กำลังทำหรือรออยู่” ไม่ใช่ Game Maintenance Mode

### ข้อมูลเซิร์ฟเวอร์

แสดงชื่อ เวอร์ชัน คำอธิบาย หรือข้อมูลอื่นจาก `GET /info`

## 5.3 เมนูผู้เล่น

ตารางแสดง:

- ชื่อ
- User ID
- Player UID เมื่อ API ส่งมา
- ปุ่ม Kick
- ปุ่ม Ban

### Kick

1. กด Kick
2. กรอกข้อความแจ้งผู้เล่น
3. ยืนยัน
4. Dashboard ส่ง `POST /kick` พร้อม `userid` และ `message`

ยังไม่เก็บประวัติ Kick ในไฟล์

### Ban จากรายชื่อ

1. กด Ban
2. กรอกเหตุผล
3. ยืนยัน
4. Dashboard ส่ง `POST /ban`
5. หากสำเร็จจึงเขียน `bans.json` และส่ง Discord

## 5.4 เมนู Ban / Unban

### Ban แบบกรอกเอง

ต้องกรอก:

- User ID: ห้ามมีช่องว่าง ความยาวไม่เกิน 128
- ชื่อผู้เล่น: ไม่บังคับ
- เหตุผล: ไม่เกิน 500 ตัวอักษร

### Active Ban

เป็นรายการที่ Dashboard บันทึกเองเท่านั้น Palworld REST API ไม่มี endpoint อ่าน Ban list ทั้งหมด จึงไม่รวม Ban จาก RCON หรือเครื่องมืออื่น

### History

เก็บ 1,000 Event ล่าสุดใน `dashboard/data/bans.json` และหน้า API ส่งกลับ 300 Event ล่าสุด

### Unban และการเข้าเกมรอบแรก

หลัง Unban ระบบส่งคำสั่งไป Palworld แล้วบันทึก History ทันที หากผู้เล่นพบ:

```text
FailedPlayerSaveRecoveryFailed
```

เฉพาะการเข้าเกมรอบแรก แต่ครั้งถัดไปเข้าได้ ให้:

1. รอ 5-10 วินาทีหลัง Unban
2. ลองเชื่อมต่อใหม่
3. ตรวจ Log ในช่วงเกิดเหตุ

```bash
docker logs --since 10m palworld-server
```

ไม่ควรลบเซฟผู้เล่นจาก Error ครั้งเดียว หากเข้าไม่ได้ต่อเนื่องหลายครั้งจึงค่อยหยุดเซิร์ฟเวอร์และสำรองข้อมูลก่อนตรวจ SaveGames

## 5.5 เมนู Import / Export

### ความหมายของ “เวลาทำงาน”

เวลานี้คือเวลาที่ Workflow เริ่มประกาศและเริ่มนับ `warning_seconds` ไม่ใช่เวลาที่ Container จะหยุดสนิท

ตัวอย่าง:

```text
เวลาทำงาน: 20:00:00
เวลาเตือน: 30 วินาที
```

ลำดับโดยประมาณ:

```text
20:00:00  ประกาศในเกมและ Discord
20:00:00  เริ่มรอ 30 วินาที
20:00:30  สั่ง Save World
20:00:30  เริ่ม Docker graceful stop
หลังจากนั้น Export/Import จึงเริ่ม
```

หากต้องการ “เริ่มปิด” เวลา 20:00 ให้ตั้งเวลางานก่อนหน้า 30 วินาที

### ตั้งคิว Export

- กำหนดเวลา หรือเว้นว่างเพื่อทำทันที
- เวลาเตือน 0-3600 วินาที
- ข้อความไม่เกิน 500 ตัวอักษร
- ระบบรับงาน Pending/Running รวมไม่เกิน 20 งาน
- ประวัติเก็บ 500 งานล่าสุด

### ขั้นตอน Export

| Stage | ความหมาย |
|---|---|
| `scheduled` | รอถึงเวลาทำงาน |
| `starting` | Scheduler รับงานและล็อก Maintenance |
| `announcing` | ประกาศในเกม/Discord และรอเวลาเตือน |
| `stopping_server` | Save แล้วหยุด Container |
| `creating_archive` | สร้าง ZIP จาก `Pal/Saved/` |
| `starting_server` | เปิด Container และรอ REST API |
| `completed` | สำเร็จ |
| `failed` | ล้มเหลว |
| `interrupted` | Dashboard ถูก Restart ระหว่างงาน |

### ไฟล์ Export

ชื่อรูปแบบ:

```text
palworld-export-YYYYMMDD-HHMMSS-JOBID.zip
```

ภายในมี `dashboard-export-manifest.json` และ `Pal/Saved/`

Manifest ระบุ:

- Format และ Format version
- Dashboard version
- เวลาและ Timezone
- Source path
- Job ID
- Server info หาก REST API อ่านได้

### อัปโหลด Import

Browser ส่ง ZIP แบบ Binary ไป `/api/import/upload`

การตรวจ:

- ต้องมี `Content-Length`
- ขนาดไฟล์ไม่เกิน `DASHBOARD_MAX_UPLOAD_MB`
- ZIP ต้องไม่เสีย
- ห้าม Absolute path หรือ `..`
- ห้าม Symlink
- ต้องมีข้อมูลใต้ `Pal/Saved/`
- ห้ามไฟล์นอก `Pal/Saved/` ยกเว้น Manifest
- จำนวน Entry ไม่เกิน `DASHBOARD_MAX_ARCHIVE_FILES` ค่า Backend เริ่มต้น 200,000
- ขนาดรวมหลังแตกไม่เกิน `DASHBOARD_MAX_EXPANDED_MB`

### ขั้นตอน Import

| Stage | ความหมาย |
|---|---|
| `scheduled` | รอคิว |
| `announcing` | ประกาศและรอ |
| `stopping_server` | Save และหยุด Container |
| `safety_backup` | สร้าง `pre-import-*.zip` |
| `extracting` | แตก ZIP ไป Staging |
| `replacing_saved_data` | สลับข้อมูลเซฟเดิม/ใหม่ |
| `starting_server` | เปิดและตรวจ REST API |
| `completed` | สำเร็จและลบ Rollback ชั่วคราว |
| `failed` | ล้มเหลวและพยายาม Rollback/เปิด Server |

### Rollback

ก่อนแทนที่:

```text
Pal/Saved
-> .dashboard-rollback-saved-JOBID
```

หากข้อมูลใหม่ถูกวางแล้วแต่การเปิดเซิร์ฟเวอร์ล้มเหลว ระบบพยายาม:

1. หยุด Container หากยังรัน
2. ย้ายข้อมูลใหม่ไป `.dashboard-failed-import-JOBID`
3. ย้าย Rollback กลับเป็น `Pal/Saved`
4. คืน Owner
5. ส่ง Error และพยายามเปิด Server ในระดับ Job recovery

Rollback เป็น Best effort จึงต้องตรวจ Log และไฟล์จริงเมื่อ Job Failed

### ยกเลิกงาน

ยกเลิกได้เฉพาะ `pending` เมื่อ Job เป็น `running` แล้วปุ่มยกเลิกจะไม่แสดง เพราะการหยุดกลางขั้นตอนแทนที่เซฟมีความเสี่ยงสูง

## 5.6 เมนูตั้งค่า

อ่าน `GET /settings` และค้นหาได้ แต่แก้ไม่ได้ เพราะ Palworld REST API ไม่มี endpoint แก้ Server settings ผ่านหน้า

การเปลี่ยนค่าต้องแก้ `docker-compose.yml` หรือ Environment แล้ว Recreate/Restart ตามชนิดค่า

## 5.7 เมนูคำสั่งผู้ดูแล

### ประกาศข้อความ

ส่ง `POST /announce` ข้อความสูงสุด 500 ตัวอักษร

### Save World

ส่ง `POST /save` ทันที หน้าเว็บตอบเมื่อ REST API รับคำสั่ง ไม่ได้รอพิสูจน์ว่า Disk flush ทุกไฟล์เสร็จแล้ว

### Start Container

เรียก Docker API `POST /containers/palworld-server/start`

ใช้เมื่อ:

- Container อยู่ `exited`/`stopped`
- งาน Failed และ Recovery ไม่สำเร็จ
- ผู้ดูแลหยุด Server ไว้ก่อนหน้า

ห้ามกดซ้ำระหว่าง Import/Export เพราะ Workflow อาจตั้งใจหยุด Server อยู่

### World Actor Snapshot

อธิบายในภาค 4

### Shutdown แบบมีเวลาเตือน

ส่ง `POST /shutdown` พร้อม:

- `waittime` 0-3600 วินาที
- `message` สูงสุด 500 ตัวอักษร

เป็นคำสั่ง Palworld Server ไม่ใช่ Docker stop จาก Dashboard Scheduler

### Force Stop

ส่ง `POST /stop` ไป Palworld ซึ่งเป็นคำสั่งหยุดทันทีและมีความเสี่ยงต่อข้อมูลที่ยังไม่ Save หน้าเว็บจึงถามยืนยันสองครั้ง

---

# ภาค 6: ระบบคิว Maintenance

## 6.1 การทำงานของ Scheduler

- Thread Scheduler เริ่มหลัง Dashboard ประมาณ 3 วินาที
- ตรวจคิวทุก 2 วินาทีหรือเมื่อมี Event ปลุก
- ทำงานทีละงานด้วย `MAINTENANCE_LOCK`
- เลือก Pending ที่ `scheduled_at` เร็วที่สุด
- เวลาต้องไม่ย้อนหลังเกิน 1 นาทีและล่วงหน้าไม่เกิน 365 วัน

## 6.2 สถานะ Job

| Status | ความหมาย |
|---|---|
| `pending` | รอเวลา/รอคิว |
| `running` | กำลังทำ |
| `completed` | สำเร็จ |
| `failed` | ล้มเหลว |
| `cancelled` | ผู้ดูแลยกเลิกก่อนเริ่ม |

## 6.3 Dashboard Restart ระหว่างงาน

เมื่อเริ่มใหม่ จะเปลี่ยน Job ที่ค้าง `running` เป็น:

```text
status=failed
stage=interrupted
```

และพยายาม Start Container หากตรวจพบว่าหยุดอยู่ แต่จะไม่เดาว่าข้อมูลอยู่ระหว่าง Staging/Replace ขั้นใด ผู้ดูแลต้องตรวจ:

```bash
cat dashboard/data/state.json
cat dashboard/data/maintenance.json 2>/dev/null || true
find palworld -maxdepth 2 -name '.dashboard-*' -print
find dashboard/data/exports -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %f\n' | sort
```

## 6.4 วิธีประเมิน Job Failed

1. ดูข้อความ Error ในหน้า Dashboard
2. ดู Log Dashboard
3. ดูสถานะ Container
4. ตรวจไฟล์ Rollback/Failed import
5. ห้ามลบไฟล์ชั่วคราวจนระบุได้ว่า `Pal/Saved` ชุดใดถูกต้อง
6. เก็บสำเนาทุกชุดก่อนย้ายมือ

คำสั่ง:

```bash
docker compose logs --since=30m dashboard palworld docker-proxy
docker compose ps
sudo du -sh palworld/Pal/Saved palworld/.dashboard-* dashboard/data/exports dashboard/data/imports 2>/dev/null
```

---

# ภาค 7: Discord Notification

## 7.1 สองแหล่งการแจ้งเตือน

### จาก Palworld image

ควบคุมด้วย `DISCORD_PRE_*`, `DISCORD_POST_*`, `DISCORD_PLAYER_*` ใน service `palworld`

### จาก Dashboard

ใช้ `DASHBOARD_DISCORD_WEBHOOK_URL` ซึ่ง Compose Map จาก `DISCORD_INFORMATION_WEBHOOK_URL`

Dashboard แจ้ง:

- Ban/Unban
- ตั้งคิว Export/Import
- เริ่ม Maintenance
- Server ปิดชั่วคราว
- สร้าง Export
- สร้าง Safety Backup
- แทนที่ข้อมูล Import
- งานสำเร็จ
- งานล้มเหลวและผล Recovery
- ยกเลิก Job

บางช่วงอาจมีข้อความซ้ำกับอิมเมจ Palworld เช่น Shutdown/Start/Backup ให้ปิด `*_ENABLED` บางรายการหากต้องการลดข้อความซ้ำ

## 7.2 Welcome channel

อิมเมจและ Dashboard ไม่มี Event สมาชิกเข้า Discord จึงส่ง Welcome อัตโนมัติไม่ได้ ต้องใช้ Discord Welcome Screen หรือ Bot ภายนอก

## 7.3 ทดสอบ Webhook

```bash
curl -H 'Content-Type: application/json' \
  -d '{"content":"Palworld webhook test"}' \
  'https://discord.com/api/webhooks/ID/TOKEN'
```

ระวังไม่ให้ URL ปรากฏใน Shell history หรือ Log

---

# ภาค 8: Backup, Export และนโยบายเก็บข้อมูล

## 8.1 ความแตกต่าง

| ประเภท | ผู้สร้าง | เวลา Server หยุด | ตำแหน่ง | ใช้ทำอะไร |
|---|---|---:|---|---|
| Auto Backup | Palworld image | ตามระบบ Backup | `palworld/backups/` | Backup ประจำ |
| Export | Dashboard | หยุด | `dashboard/data/exports/` | ดาวน์โหลด/ย้าย/Import กลับ |
| Safety Backup | Dashboard | Server หยุดแล้ว | `dashboard/data/exports/pre-import-*` | กู้ก่อน Import |
| Native Save Data Backup | Palworld | ตามเกม | ภายใต้ Save | Recovery ของเกม |

## 8.2 นโยบาย 3-2-1

อย่างน้อย:

- 3 สำเนา
- 2 ประเภทสื่อ/ตำแหน่ง
- 1 สำเนานอกเครื่อง

ตัวอย่าง:

```bash
rsync -a --delete dashboard/data/exports/ backup-host:/backup/palworld/exports/
rsync -a palworld/backups/ backup-host:/backup/palworld/native-backups/
```

## 8.3 ตรวจ ZIP

```bash
unzip -t dashboard/data/exports/palworld-export-*.zip
unzip -l dashboard/data/exports/palworld-export-*.zip | head -100
```

## 8.4 ลบไฟล์เก่า

ไม่มีปุ่มลบ Export/Import ใน UI ต้องจัดการบน Host อย่างระมัดระวัง

ตัวอย่างแสดงไฟล์เก่ากว่า 30 วันก่อน:

```bash
find dashboard/data/exports -type f -name '*.zip' -mtime +30 -print
```

เมื่อตรวจแล้วจึงลบ:

```bash
find dashboard/data/exports -type f -name '*.zip' -mtime +30 -delete
```

อย่าลบ Safety Backup ของ Import ที่ยังไม่ได้ยืนยันว่าโลกใหม่ใช้งานได้

---

# ภาค 9: การอัปเดตและเปลี่ยน Configuration

## 9.1 เปลี่ยน `.env`

Environment ของคอนเทนเนอร์จะเปลี่ยนเมื่อ Recreate ไม่ใช่เพียง Restart:

```bash
docker compose up -d --force-recreate palworld dashboard
```

## 9.2 แก้ Source Dashboard

เนื่องจาก `server.py` และ `index.html` ถูก Bind mount:

```bash
docker compose restart dashboard
```

หากแก้ Dockerfile:

```bash
docker compose up -d --build --force-recreate dashboard
```

## 9.3 อัปเดตอิมเมจ Palworld

ก่อนอัปเดต:

1. ตรวจผู้เล่น
2. Export หรือ Backup
3. บันทึกค่าเวอร์ชันปัจจุบัน

จากนั้น:

```bash
docker compose pull palworld
docker compose up -d --force-recreate palworld
docker compose logs -f palworld
```

ตรวจ GameData API หลังอัปเดตด้วย

## 9.4 Pin เวอร์ชัน

`latest` สะดวกแต่เปลี่ยนได้ หากต้องการควบคุม Change ให้เปลี่ยน:

```yaml
image: thijsvanloef/palworld-server-docker:2.6.0
```

ก่อน Pin ควรตรวจ Release ใหม่และ Compatibility ของเกม

---

# ภาค 10: Security Hardening

## 10.1 Dashboard

ค่าเริ่มต้น:

```dotenv
DASHBOARD_BIND_ADDRESS=0.0.0.0
DASHBOARD_PORT=8080
```

หากใช้ Reverse Proxy บนเครื่องเดียวกัน:

```dotenv
DASHBOARD_BIND_ADDRESS=127.0.0.1
```

Basic Auth ไม่เข้ารหัสข้อมูล หากใช้ผ่านเครือข่ายที่ไม่ไว้วางใจต้องมี HTTPS/VPN

## 10.2 Read-only mode สำหรับผู้ดู

ตั้ง:

```dotenv
DASHBOARD_ACTIONS_ENABLED=false
```

จากนั้น Recreate Dashboard:

```bash
docker compose up -d --force-recreate dashboard
```

GET ยังอ่านได้ แต่ POST ทุกคำสั่งจะตอบ 403 รวมถึง Upload/Import/Export

## 10.3 REST API

Compose ผูก Host:

```yaml
- "127.0.0.1:8212:8212/tcp"
```

Dashboard ยังเข้าผ่าน Docker network ที่ `http://palworld:8212/v1/api`

ห้ามเปลี่ยนเป็น `0.0.0.0:8212` เว้นแต่มี Firewall และเหตุผลชัดเจน เอกสาร Palworld ระบุว่า REST API ไม่ได้ออกแบบให้เปิดตรงสู่ Internet

## 10.4 RCON

หากไม่ใช้ RCON จาก LAN ให้เปลี่ยน:

```yaml
- "127.0.0.1:25575:25575/tcp"
```

หรือปิดด้วย Firewall แต่ไม่ควรปิด `RCON_ENABLED` โดยไม่ตรวจผลกับ graceful save/stop ของอิมเมจ

## 10.5 Docker Socket Proxy

แม้ Dashboard ไม่ Mount socket ตรง แต่ Proxy ยังสามารถ Start/Stop Container ได้ จึง:

- ห้าม Publish Port 2375
- อย่าเพิ่มสิทธิ์ API ที่ไม่จำเป็น
- จำกัดผู้ที่แก้ Compose และเข้าถึง Dashboard

## 10.6 Secret handling

ตรวจว่า Git ไม่ติดไฟล์:

```bash
git status --ignored
```

`.gitignore` ปิด:

- `.env`
- `palworld/`
- `dashboard/data/*` ยกเว้น `.gitkeep`
- Python cache

Webhook URL ถือเป็น Secret เช่นเดียวกับ Password

---

# ภาค 11: Troubleshooting

## 11.1 Dashboard เปิดไม่ได้

```bash
docker compose ps dashboard
docker compose logs --tail=300 dashboard
ss -lntp | grep ':8080'
curl -v http://127.0.0.1:8080/health
```

สาเหตุ:

- Port 8080 ชน
- Bind address ไม่มีอยู่บน Host
- Docker build ล้มเหลว
- `index.html`/`server.py` ไม่มีหรือ permission ผิด

เปลี่ยนพอร์ต:

```dotenv
DASHBOARD_PORT=8081
```

Recreate:

```bash
docker compose up -d --force-recreate dashboard
```

## 11.2 Login ไม่ผ่าน

- ตรวจ `.env`
- Browser อาจ Cache Basic Auth ให้ปิด Tab/Private window
- Recreate หลังเปลี่ยนรหัส

```bash
docker inspect palworld-dashboard --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep '^DASHBOARD_\(USERNAME\|PASSWORD\)='
```

ระวังคำสั่งนี้แสดง Secret บนหน้าจอ

## 11.3 หน้า Overview Offline แต่ Container Running

ตรวจ REST:

```bash
curl -u 'admin:PASSWORD' http://127.0.0.1:8212/v1/api/info
docker compose logs --tail=300 palworld
```

สาเหตุ:

- Palworld ยัง Boot
- Admin password ไม่ตรง
- REST API ปิด
- API เปลี่ยนพฤติกรรมหลังอัปเดต

## 11.4 รายชื่อผู้เล่นว่าง

อาจหมายถึงไม่มีผู้เล่นจริง หรือ REST API Error หน้า UI ใช้ข้อความรวม

```bash
curl -u 'admin:PASSWORD' http://127.0.0.1:8212/v1/api/players
```

ตรวจ `REST_API_ENABLED`, `ENABLE_PLAYER_LOGGING` และ Log

## 11.5 GameData 404

ดูภาค 4.5

## 11.6 Export Failed: ไม่พบ Pal/Saved

```bash
ls -ld palworld/Pal/Saved
find palworld/Pal -maxdepth 3 -type d | head -50
```

อาจเกิดจาก Palworld ยังไม่สร้างโลก, Volume ผิด, หรือ Path ในอิมเมจเปลี่ยน

## 11.7 Import ปฏิเสธ ZIP

### มี Path อื่น

ZIP ต้องมีเฉพาะ:

```text
dashboard-export-manifest.json
Pal/Saved/**
```

หาก Zip เครื่องมือสร้าง Parent folder เพิ่ม เช่น `backup/Pal/Saved` จะไม่ผ่าน

### ขนาดหลังแตกเกิน

เพิ่มอย่างระมัดระวัง:

```dotenv
DASHBOARD_MAX_EXPANDED_MB=16384
```

ตรวจว่าดิสก์มีพื้นที่มากพอ แล้ว Recreate Dashboard

### ไฟล์อัปโหลดเกิน

```dotenv
DASHBOARD_MAX_UPLOAD_MB=8192
```

Reverse Proxy ต้องเพิ่ม Client body limit ให้สอดคล้องด้วย

## 11.8 Job ค้าง `starting_server`

```bash
docker compose ps
docker compose logs --since=30m palworld dashboard
curl -u 'admin:PASSWORD' http://127.0.0.1:8212/v1/api/info
```

รอได้ตาม `PALWORLD_START_TIMEOUT_SECONDS` ค่าเริ่มต้น 900 วินาที หากโลกใหญ่และ Boot นานเพิ่มได้ แต่ต้องแยกจากกรณี Crash loop

## 11.9 Stop timeout

ค่า:

```dotenv
PALWORLD_STOP_TIMEOUT_SECONDS=60
```

Docker stop เรียก Graceful termination และรอเพิ่มใน Backend หาก Save ใหญ่ อาจเพิ่มเป็น 120-300 วินาที พร้อมปรับ `stop_grace_period` ใน Compose ให้สอดคล้อง

## 11.10 Permission หลัง Import

```bash
ls -ln palworld/Pal | head
ls -ln palworld/Pal/Saved | head
```

แก้:

```bash
sudo chown -R 1000:1000 palworld
```

จากนั้นตรวจ `PUID/PGID` ทั้งสอง service

## 11.11 Disk Full

```bash
df -h
df -i
sudo du -xh --max-depth=2 palworld dashboard/data | sort -h | tail -50
```

หยุด Import/Export ใหม่ ลบเฉพาะไฟล์ที่ตรวจแล้ว และย้าย Backup ออกเครื่อง

## 11.12 Docker Proxy Error

```bash
docker compose logs --tail=300 docker-proxy
docker compose exec dashboard python3 - <<'PY'
import urllib.request
print(urllib.request.urlopen('http://docker-proxy:2375/_ping', timeout=5).read())
PY
```

คาดหวัง `OK`

## 11.13 Dashboard ถูก Restart ระหว่าง Import

ห้ามกด Import ซ้ำทันที ทำตามภาค 6.3 และเก็บสำเนา:

```bash
sudo cp -a palworld/Pal/Saved palworld/manual-recovery-Saved-$(date +%Y%m%d-%H%M%S)
```

จากนั้นค่อยตัดสินว่าต้องใช้ `rollback`, `failed-import` หรือ Safety Backup

## 11.14 Ban/Unban ไม่ตรงกับรายการจริง

Active Ban เป็น Local ledger ของ Dashboard ไม่ใช่ Source of truth ทั้งหมด หากใช้ RCON/เครื่องมืออื่น รายการอาจไม่ตรง ให้ใช้ User ID ที่ถูกต้องและเก็บขั้นตอนการบริหารผ่านช่องทางเดียวเมื่อทำได้

---

# ภาค 12: Checklist การปฏิบัติงาน

## 12.1 ก่อนเปิดให้ผู้เล่น

- [ ] เปลี่ยน Password ทุกตัว
- [ ] ปิด Webhook placeholder หรือใส่ของจริง
- [ ] ตรวจ `PUID/PGID`
- [ ] เปิดเฉพาะพอร์ตจำเป็น
- [ ] REST API ผูก `127.0.0.1`
- [ ] Dashboard อยู่ LAN/VPN/HTTPS
- [ ] `ENABLE_GAMEDATA_API=true` หากใช้ Snapshot
- [ ] Pull image 2.6.0+ และ Recreate
- [ ] ทดสอบ Save World
- [ ] ทดสอบ Export และเปิด ZIP
- [ ] ทดสอบ Restore บนสำเนา Server
- [ ] ตั้ง External backup

## 12.2 ก่อน Import

- [ ] แจ้งผู้เล่น
- [ ] ตรวจผู้เล่นออนไลน์
- [ ] ตรวจ Disk free และ inode
- [ ] ตรวจ ZIP ด้วย `unzip -t`
- [ ] ตรวจโครงสร้าง `Pal/Saved/`
- [ ] ดาวน์โหลด/คัดลอก Export ล่าสุดออกเครื่อง
- [ ] ตั้งเวลาเตือนเหมาะสม
- [ ] ไม่อัปเดตเกมหรือ Restart Dashboard ระหว่างงาน

## 12.3 หลัง Import

- [ ] Container Running
- [ ] REST API ตอบ
- [ ] Dashboard Online
- [ ] ผู้เล่นทดสอบเข้า
- [ ] โลก/ตัวละคร/กิลด์ถูกต้อง
- [ ] ตรวจ Log 15-30 นาที
- [ ] เก็บ Safety Backup จนยืนยันเสถียร
- [ ] ตรวจ GameData Snapshot ถ้าใช้งาน

## 12.4 รายวัน/รายสัปดาห์

- [ ] ตรวจ Disk/RAM
- [ ] ตรวจ Backup สำเร็จ
- [ ] ตรวจ Export/Safety Backup เก่า
- [ ] ตรวจ Error ใน Dashboard/Palworld log
- [ ] ทดสอบไฟล์ Backup แบบสุ่ม
- [ ] ตรวจ Release ก่อน Pull `latest`

---

# ภาค 13: Dashboard API

## 13.1 GET

| Endpoint | หน้าที่ | Auth |
|---|---|---|
| `/health` | Healthcheck `ok v1.0.0` | ไม่ต้อง |
| `/` | หน้า Dashboard | Basic Auth เมื่อมี Password |
| `/api/version` | Version และสถานะ Actions | ต้อง |
| `/api/status` | Info/Metrics/Players/Settings/Container/Active job | ต้อง |
| `/api/snapshot` | Proxy GameData Snapshot | ต้อง |
| `/api/bans` | Active/history ที่ Dashboard เก็บ | ต้อง |
| `/api/jobs` | รายการและ Active job | ต้อง |
| `/api/exports` | รายการ Export ZIP | ต้อง |
| `/api/imports` | รายการ Import ZIP และ Upload limit | ต้อง |
| `/api/export/download/<file>` | ดาวน์โหลด Export | ต้อง |

## 13.2 POST

ทุก POST ต้อง:

- Basic Auth ผ่าน
- Origin ตรงกับ Host เมื่อ Browser ส่ง Origin
- `DASHBOARD_ACTIONS_ENABLED=true`

| Endpoint | หน้าที่ |
|---|---|
| `/api/import/upload?filename=...` | อัปโหลดและ Validate ZIP |
| `/api/maintenance/export` | สร้าง Export job |
| `/api/maintenance/import` | สร้าง Import job |
| `/api/job/cancel` | ยกเลิก Pending job |
| `/api/action/start` | Start Container |
| `/api/action/announce` | ประกาศ |
| `/api/action/save` | Save World |
| `/api/action/kick` | Kick |
| `/api/action/ban` | Ban และเก็บ Ledger |
| `/api/action/unban` | Unban และเก็บ Ledger |
| `/api/action/shutdown` | Shutdown มีเวลาเตือน |
| `/api/action/stop` | Force Stop ผ่าน Palworld API |

## 13.3 ข้อจำกัด Request

- JSON body สูงสุด 256 KB
- ข้อความทั่วไปสูงสุด 500 ตัวอักษร
- User ID สูงสุด 128 และห้ามช่องว่าง
- Warning/Shutdown wait 0-3600 วินาที
- ชื่อไฟล์ถูก Normalize เหลือ `A-Z a-z 0-9 - _ .` และยาวสูงสุด 180

---

# ภาค 14: ตัวแปร `.env` ที่เปิดให้ปรับโดยตรง

| ตัวแปร | ค่าเริ่มต้น/ตัวอย่าง | หน้าที่ |
|---|---|---|
| `PALWORLD_SERVER_PASSWORD` | ต้องเปลี่ยน | รหัสผู้เล่น |
| `PALWORLD_ADMIN_PASSWORD` | ต้องเปลี่ยน | รหัส RCON/REST และที่ Dashboard ใช้ |
| `ENABLE_GAMEDATA_API` | `true` | เปิด World Actor Snapshot; ต้อง image 2.6.0+ |
| `DISCORD_INFORMATION_WEBHOOK_URL` | URL/ว่าง | สถานะระบบและ Dashboard |
| `DISCORD_WELCOME_WEBHOOK_URL` | URL/ว่าง | ชุดนี้ไม่ใช้ Event welcome โดยตรง |
| `DISCORD_SESSION_WEBHOOK_URL` | URL/ว่าง | ผู้เล่นเข้าออกจาก image |
| `DISCORD_INVITE_URL` | URL/ว่าง | Invite link; Compose ปัจจุบันมีข้อความบางส่วน Hard-code ด้วย |
| `DASHBOARD_BIND_ADDRESS` | `0.0.0.0` | IP ที่ Publish Dashboard |
| `DASHBOARD_PORT` | `8080` | Port Dashboard |
| `DASHBOARD_USERNAME` | `admin` | Basic Auth username |
| `DASHBOARD_PASSWORD` | ต้องเปลี่ยน | Basic Auth password; ถ้าว่าง Backend จะไม่ขอ Auth |
| `DASHBOARD_REFRESH_SECONDS` | `15` | Poll interval ขั้นต่ำ 5 |
| `DASHBOARD_ACTIONS_ENABLED` | `true` | ปิด POST ทั้งหมดเมื่อ false |
| `DASHBOARD_MAX_UPLOAD_MB` | `4096` | Upload ZIP max |
| `DASHBOARD_MAX_EXPANDED_MB` | `8192` | Expanded ZIP max |
| `PALWORLD_START_TIMEOUT_SECONDS` | `900` | รอ REST หลัง Start |
| `PALWORLD_STOP_TIMEOUT_SECONDS` | `60` | Docker graceful stop timeout |

> `.env` ไม่ได้ถูก Inject เข้า Container ทุกตัวโดยอัตโนมัติ จะมีผลเฉพาะตัวแปรที่ `docker-compose.yml` อ้างด้วย `${...}` หรือ Map เข้า `environment:` เท่านั้น

---

# ภาค 15: เอกสารอ้างอิง

- [Palworld Server Guide: Requirements](https://docs.palworldgame.com/getting-started/requirements/)
- [Palworld Server Guide: Configure server arguments](https://docs.palworldgame.com/settings-and-operation/arguments/)
- [Palworld Server Guide: REST API introduction and security warning](https://docs.palworldgame.com/api/rest-api/palwold-rest-api/)
- [Palworld Server Guide: REST API endpoints](https://docs.palworldgame.com/category/rest-api/)
- [thijsvanloef/palworld-server-docker repository](https://github.com/thijsvanloef/palworld-server-docker)
- [palworld-server-docker `.env.example`](https://github.com/thijsvanloef/palworld-server-docker/blob/main/.env.example)
- [palworld-server-docker release 2.6.0](https://github.com/thijsvanloef/palworld-server-docker/releases/tag/2.6.0)

---

# ภาคผนวก A: Environment Reference ทั้งหมดจาก Compose

ตารางต่อไปนี้สร้างจาก `docker-compose.yml` ในชุดโดยตรง ค่า คือค่าปัจจุบันของไฟล์ ไม่ใช่ค่าที่เหมาะกับทุกเครื่อง ตัวแปร Gameplay จำนวนมากต้องตรวจ Compatibility กับเวอร์ชัน Palworld ก่อนเปลี่ยน

## บริการ `palworld`

รวม **213 ตัวแปร** ตามไฟล์ `docker-compose.yml` ของชุดนี้

### ระบบพื้นฐานและสิทธิ์ไฟล์

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `TZ` | `"Asia/Bangkok"` | เขตเวลาที่ใช้กับ Log Backup Update และ Reboot |
| `PUID` | `"1000"` | UID ของผู้ใช้บน Host ที่ให้เป็นเจ้าของไฟล์ ห้ามใช้ 0 |
| `PGID` | `"1000"` | GID ของกลุ่มบน Host ที่ให้เป็นเจ้าของไฟล์ ห้ามใช้ 0 |
| `UPDATE_ON_BOOT` | `"true"` | ติดตั้งหรืออัปเดตเซิร์ฟเวอร์เมื่อเริ่มคอนเทนเนอร์ ต้องเปิดครั้งแรก |
| `MULTITHREADING` | `"true"` | เปิดโหมดประมวลผลหลายเธรด เหมาะกับ CPU ตั้งแต่ประมาณ 4 เธรด |
| `USE_DEPOT_DOWNLOADER` | `"false"` | ใช้ DepotDownloader แทน SteamCMD เหมาะกับเครื่องที่ SteamCMD ไม่รองรับ |
| `INSTALL_BETA_INSIDER` | `"false"` | ติดตั้ง Palworld Dedicated Server รุ่น Beta Insider |
| `TARGET_MANIFEST_ID` | `""` | ล็อกเวอร์ชันเกมด้วย Steam Manifest ID เว้นว่างเพื่อใช้รุ่นล่าสุด |
| `STEAM_USERNAME` | `""` | ชื่อผู้ใช้ Steam สำหรับโหลด Manifest เฉพาะรุ่น |
| `STEAM_PASSWORD` | `""` | รหัสผ่าน Steam สำหรับโหลด Manifest เฉพาะรุ่น |
### ข้อมูลและการเชื่อมต่อเซิร์ฟเวอร์

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `SERVER_NAME` | `"Mien Palworld Thailand"` | ชื่อตัวอย่างที่แสดงในรายการเซิร์ฟเวอร์; เปลี่ยนได้ตามชื่อชุมชน; ชื่อเซิร์ฟเวอร์ที่ผู้เล่นมองเห็น |
| `SERVER_DESCRIPTION` | `"เซิร์ฟเวอร์ Palworld ไทย \| Discord: https://discord.gg/B9wUtyg9s"` | คำอธิบายตัวอย่างพร้อม Invite Link สำหรับผู้เล่น; คำอธิบายเซิร์ฟเวอร์ |
| `SERVER_PASSWORD` | `"${PALWORLD_SERVER_PASSWORD:-CHANGE_ME_NOW}"` | รหัสเข้าห้อง; ตัวอย่าง Pw-Thailand-2026 และควรใส่จริงในไฟล์ .env; รหัสผ่านสำหรับผู้เล่น ควรเปลี่ยนก่อนเปิดใช้งาน |
| `ADMIN_PASSWORD` | `"${PALWORLD_ADMIN_PASSWORD:-CHANGE_ME_ADMIN_NOW}"` | รหัสผู้ดูแล RCON/REST; ควรยาวอย่างน้อย 16 ตัวและไม่ซ้ำรหัสผู้เล่น; รหัสผ่านผู้ดูแล RCON และ REST API ต้องตั้งให้เดายาก |
| `PLAYERS` | `"16"` | ตัวอย่างรองรับ 16 คน; ช่วง 1-32 และควรลดลงหาก RAM ต่ำกว่า 32GB |
| `PORT` | `"8211"` | พอร์ต UDP หลักของเกมภายในคอนเทนเนอร์ |
| `QUERY_PORT` | `"27015"` | พอร์ต UDP สำหรับ Query และการค้นหาเซิร์ฟเวอร์ |
| `PUBLIC_IP` | `""` | Public IP ของเซิร์ฟเวอร์ เว้นว่างเพื่อให้ระบบตรวจหาอัตโนมัติ |
| `PUBLIC_PORT` | `"8211"` | พอร์ตสาธารณะที่ผู้เล่นใช้เชื่อมต่อจากอินเทอร์เน็ต |
| `COMMUNITY` | `"true"` | true=แสดงใน Community Browser; ตั้งรหัสผ่านไว้แล้วเพื่อจำกัดผู้เล่น |
| `CROSSPLAY_PLATFORMS` | `"(Steam,Xbox,PS5,Mac)"` | แพลตฟอร์มที่อนุญาตให้เชื่อมต่อ ต้องมีวงเล็บครอบ |
| `ALLOW_CONNECT_PLATFORM` | `"Steam"` | ค่ารุ่นเก่าสำหรับ Steam หรือ Xbox ปัจจุบันเลิกแนะนำให้ใช้ |
### RCON และ REST API

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `RCON_ENABLED` | `"true"` | เปิด RCON และจำเป็นต่อการบันทึกก่อน Docker หยุด |
| `RCON_PORT` | `"25575"` | พอร์ต TCP สำหรับเชื่อมต่อ RCON |
| `REST_API_ENABLED` | `"true"` | เปิด REST API สำหรับคำสั่งและระบบตรวจผู้เล่น |
| `REST_API_PORT` | `"8212"` | พอร์ต TCP ของ REST API ไม่ควรเปิดสู่สาธารณะ |
| `ENABLE_GAMEDATA_API` | `"${ENABLE_GAMEDATA_API:-true}"` | เปิด GET /v1/api/game-data สำหรับ World Actor Snapshot; ต้องใช้อิมเมจ 2.6.0 ขึ้นไป |
| `ENABLE_PLAYER_LOGGING` | `"true"` | บันทึกและแจ้งผู้เล่นเข้าออก ต้องเปิด REST API |
| `PLAYER_LOGGING_POLL_PERIOD` | `"15"` | รอบตรวจรายชื่อผู้เล่นเข้าออกเป็นวินาที |
| `LOG_FILTER_ENABLED` | `"true"` | กรองบรรทัด Log ซ้ำเพื่อลดความรก |
| `LOG_FORMAT_TYPE` | `"default"` | รูปแบบ Log เลือก json logfmt colored plain หรือ default |
### การสำรองข้อมูล

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `BACKUP_ENABLED` | `"true"` | เปิดการสำรองข้อมูลอัตโนมัติ |
| `BACKUP_CRON_EXPRESSION` | `"0 0 * * *"` | ตาราง Backup แบบ Cron ค่าเดิมคือทุกวันเที่ยงคืน |
| `USE_BACKUP_SAVE_DATA` | `"true"` | ใช้ระบบ Native Save Data Backup ของเกม |
| `DELETE_OLD_BACKUPS` | `"true"` | ลบ Backup ที่เก่ากว่าจำนวนวันที่กำหนด |
| `OLD_BACKUP_DAYS` | `"30"` | จำนวนวันที่เก็บ Backup ก่อนลบอัตโนมัติ |
### อัปเดตและรีบูตอัตโนมัติ

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `AUTO_UPDATE_ENABLED` | `"false"` | เปิดตรวจและอัปเดตเซิร์ฟเวอร์อัตโนมัติ |
| `AUTO_UPDATE_CRON_EXPRESSION` | `"0 * * * *"` | ตารางตรวจอัปเดตแบบ Cron ค่าเดิมทุกต้นชั่วโมง |
| `AUTO_UPDATE_WARN_MINUTES` | `"30"` | เวลาประกาศเตือนก่อนอัปเดตเมื่อมีผู้เล่นออนไลน์ |
| `AUTO_REBOOT_ENABLED` | `"true"` | เปิดรีบูตเซิร์ฟเวอร์อัตโนมัติ |
| `AUTO_REBOOT_CRON_EXPRESSION` | `"0 5 * * *"` | ตารางรีบูตแบบ Cron ตัวอย่างทุกวันเวลา 05:00 |
| `AUTO_REBOOT_WARN_MINUTES` | `"10"` | เวลาประกาศเตือนผู้เล่นก่อนรีบูต |
| `AUTO_REBOOT_EVEN_IF_PLAYERS_ONLINE` | `"false"` | บังคับรีบูตแม้ยังมีผู้เล่นออนไลน์ |
### หยุดพักเซิร์ฟเวอร์เมื่อไม่มีผู้เล่น

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `AUTO_PAUSE_ENABLED` | `"false"` | พัก Process เมื่อไม่มีผู้เล่นเพื่อลดการใช้ทรัพยากร |
| `AUTO_PAUSE_TIMEOUT_EST` | `"180"` | เวลารอหลังผู้เล่นคนสุดท้ายออกก่อนพัก Process เป็นวินาที |
| `AUTO_PAUSE_LOG` | `"true"` | แสดง Log ของระบบ Auto Pause |
| `AUTO_PAUSE_DEBUG` | `"false"` | แสดง Debug Log ของระบบ Auto Pause |
### การสร้างไฟล์ Config

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DISABLE_GENERATE_SETTINGS` | `"false"` | ปิดการสร้าง PalWorldSettings.ini จาก Environment เมื่อเป็น true |
| `DISABLE_GENERATE_ENGINE` | `"false"` | ให้ระบบสร้าง Engine.ini จาก Environment เพื่อใช้ค่าหมวด Engine ด้านล่าง |
### Discord: การแบ่งช่องและ Webhook

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook กลางของช่อง #information; ตัวอย่าง https://discord.com/api/webhooks/123456789/token และเว้นว่างเพื่อปิด |
| `DISCORD_SUPPRESS_NOTIFICATIONS` | `"false"` | false=แจ้งเตือนตามปกติ; true=ส่งแบบ silent เหมาะเมื่อข้อความระบบถี่ |
| `DISCORD_CONNECT_TIMEOUT` | `"30"` | เวลารอเชื่อมต่อ Discord ต่อครั้งเป็นวินาที; ตัวอย่าง 30 และเพิ่มเป็น 60 เมื่ออินเทอร์เน็ตช้า |
| `DISCORD_MAX_TIMEOUT` | `"30"` | เวลารวมสูงสุดของคำขอ Webhook เป็นวินาที; ปกติใช้ 30 |
### #information: การเริ่ม ปิด อัปเดต และสำรองข้อมูล

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DISCORD_PRE_UPDATE_BOOT_MESSAGE` | `"🔄 กำลังอัปเดต Palworld Server กรุณารอสักครู่ \| Discord: https://discord.gg/B9wUtyg9s"` | ข้อความก่อนเริ่มอัปเดตเกม |
| `DISCORD_PRE_UPDATE_BOOT_MESSAGE_ENABLED` | `"true"` | true=แจ้งก่อนอัปเดต; false=ไม่ส่ง |
| `DISCORD_PRE_UPDATE_BOOT_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | ส่งข้อความนี้ไป #information; ต้องเป็น Webhook ของช่อง ไม่ใช่ Invite Link |
| `DISCORD_POST_UPDATE_BOOT_MESSAGE` | `"✅ อัปเดต Palworld Server เสร็จแล้ว กำลังเปิดให้บริการ"` | ข้อความหลังติดตั้งอัปเดตสำเร็จ |
| `DISCORD_POST_UPDATE_BOOT_MESSAGE_ENABLED` | `"true"` | เปิดการแจ้งผลหลังอัปเดต |
| `DISCORD_POST_UPDATE_BOOT_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_PRE_START_MESSAGE` | `"🟡 Palworld Server กำลังเริ่มทำงาน... ภายในอีก 1 นาที"` | ข้อความเมื่อ Process เซิร์ฟเวอร์กำลังเริ่ม |
| `DISCORD_PRE_START_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งสถานะเริ่มเซิร์ฟเวอร์ |
| `DISCORD_PRE_START_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_PRE_SHUTDOWN_MESSAGE` | `"🟠 Palworld Server กำลังปิดเพื่อบันทึกข้อมูล กรุณาออกจากเกมอย่างปลอดภัย"` | ข้อความก่อนหยุด Process |
| `DISCORD_PRE_SHUTDOWN_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งก่อนปิดเซิร์ฟเวอร์ |
| `DISCORD_PRE_SHUTDOWN_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_POST_SHUTDOWN_MESSAGE` | `"🔴 Palworld Server ปิดเรียบร้อยแล้ว"` | ข้อความหลังหยุดเซิร์ฟเวอร์ |
| `DISCORD_POST_SHUTDOWN_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งหลังปิดเซิร์ฟเวอร์ |
| `DISCORD_POST_SHUTDOWN_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_PRE_BACKUP_MESSAGE` | `"💾 กำลังสำรองข้อมูลโลกและตัวละคร..."` | ข้อความก่อนสร้าง Backup |
| `DISCORD_PRE_BACKUP_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งก่อน Backup; ปิดได้หาก Backup ถี่และข้อความมากเกินไป |
| `DISCORD_PRE_BACKUP_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_POST_BACKUP_MESSAGE` | `"✅ สำรองข้อมูลเสร็จแล้ว: `file_path`"` | file_path จะถูกแทนด้วยตำแหน่งไฟล์ Backup |
| `DISCORD_POST_BACKUP_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งหลังสร้าง Backup สำเร็จ |
| `DISCORD_POST_BACKUP_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_PRE_BACKUP_DELETE_MESSAGE` | `"🧹 กำลังลบ Backup ที่เก่ากว่า `old_backup_days` วัน"` | old_backup_days จะใช้ค่าจาก OLD_BACKUP_DAYS |
| `DISCORD_PRE_BACKUP_DELETE_MESSAGE_ENABLED` | `"false"` | ตัวอย่างปิดข้อความก่อนลบเพื่อลดข้อความซ้ำ |
| `DISCORD_PRE_BACKUP_DELETE_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_POST_BACKUP_DELETE_MESSAGE` | `"🧹 ลบ Backup ที่เก่ากว่า `old_backup_days` วันเรียบร้อยแล้ว"` | ข้อความยืนยันหลังลบ Backup เก่า |
| `DISCORD_POST_BACKUP_DELETE_MESSAGE_ENABLED` | `"true"` | เปิดแจ้งเมื่อทำความสะอาด Backup เสร็จ |
| `DISCORD_POST_BACKUP_DELETE_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
| `DISCORD_ERR_BACKUP_DELETE_MESSAGE` | `"⚠️ ไม่สามารถลบ Backup เก่าได้ กรุณาตรวจสิทธิ์ไฟล์และค่า OLD_BACKUP_DAYS=`old_backup_days`"` | ข้อความ Error เมื่อลบ Backup ไม่สำเร็จ |
| `DISCORD_ERR_BACKUP_DELETE_MESSAGE_ENABLED` | `"true"` | ควรเปิดเพื่อให้ผู้ดูแลเห็นปัญหา |
| `DISCORD_ERR_BACKUP_DELETE_MESSAGE_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | Webhook ช่อง #information |
### #session: ผู้เล่นเข้าและออกจากเกม

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DISCORD_PLAYER_JOIN_MESSAGE` | `"🟢 `player_name` เข้า Palworld Server แล้ว \| ข้อมูลชุมชน: https://discord.gg/B9wUtyg9s"` | player_name จะถูกแทนด้วยชื่อผู้เล่น |
| `DISCORD_PLAYER_JOIN_MESSAGE_ENABLED` | `"true"` | เปิดข้อความผู้เล่นเข้า; ต้องเปิด REST_API_ENABLED และ ENABLE_PLAYER_LOGGING |
| `DISCORD_PLAYER_JOIN_MESSAGE_URL` | `"${DISCORD_SESSION_WEBHOOK_URL:-}"` | Webhook ของช่อง #session |
| `DISCORD_PLAYER_LEAVE_MESSAGE` | `"⚪ `player_name` ออกจาก Palworld Server แล้ว"` | player_name จะถูกแทนด้วยชื่อผู้เล่น |
| `DISCORD_PLAYER_LEAVE_MESSAGE_ENABLED` | `"true"` | เปิดข้อความผู้เล่นออก; ต้องเปิด REST API และ Player Logging |
| `DISCORD_PLAYER_LEAVE_MESSAGE_URL` | `"${DISCORD_SESSION_WEBHOOK_URL:-}"` | Webhook ของช่อง #session |
### ค่าเกมพื้นฐานและ Randomizer

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DIFFICULTY` | `"None"` | ระดับความยากเลือก None Normal หรือ Difficult |
| `RANDOMIZER_TYPE` | `"None"` | รูปแบบสุ่ม Pal เลือก None Region หรือ All |
| `RANDOMIZER_SEED` | `""` | Seed สำหรับระบบสุ่ม Pal |
| `IS_RANDOMIZER_PAL_LEVEL_RANDOM` | `"false"` | สุ่มเลเวล Pal ป่าเต็มรูปแบบแทนการอิงพื้นที่ |
| `DAYTIME_SPEEDRATE` | `"1.000000"` | ความเร็วเวลากลางวัน ค่ายิ่งสูงกลางวันยิ่งสั้น |
| `NIGHTTIME_SPEEDRATE` | `"1.000000"` | ความเร็วเวลากลางคืน ค่ายิ่งสูงกลางคืนยิ่งสั้น |
| `EXP_RATE` | `"1.000000"` | ตัวคูณค่าประสบการณ์ที่ได้รับ |
| `PAL_CAPTURE_RATE` | `"1.000000"` | ตัวคูณโอกาสจับ Pal |
| `PAL_SPAWN_NUM_RATE` | `"1.000000"` | ตัวคูณจำนวน Pal ที่เกิดในโลก |
### ความเสียหายและการฟื้นฟู

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `PAL_DAMAGE_RATE_ATTACK` | `"1.000000"` | ตัวคูณความเสียหายที่ Pal สร้าง |
| `PAL_DAMAGE_RATE_DEFENSE` | `"1.000000"` | ตัวคูณความเสียหายที่ Pal ได้รับ |
| `PLAYER_DAMAGE_RATE_ATTACK` | `"1.000000"` | ตัวคูณความเสียหายที่ผู้เล่นสร้าง |
| `PLAYER_DAMAGE_RATE_DEFENSE` | `"1.000000"` | ตัวคูณความเสียหายที่ผู้เล่นได้รับ |
| `PLAYER_STOMACH_DECREASE_RATE` | `"1.000000"` | อัตราลดความหิวของผู้เล่น |
| `PLAYER_STAMINA_DECREASE_RATE` | `"1.000000"` | อัตราลด Stamina ของผู้เล่น |
| `PLAYER_AUTO_HP_REGEN_RATE` | `"1.000000"` | อัตราฟื้น HP อัตโนมัติของผู้เล่น |
| `PLAYER_AUTO_HP_REGEN_RATE_IN_SLEEP` | `"1.000000"` | อัตราฟื้น HP ของผู้เล่นขณะนอน |
| `PAL_STOMACH_DECREASE_RATE` | `"1.000000"` | อัตราลดความหิวของ Pal |
| `PAL_STAMINA_DECREASE_RATE` | `"1.000000"` | อัตราลด Stamina ของ Pal |
| `PAL_AUTO_HP_REGEN_RATE` | `"1.000000"` | อัตราฟื้น HP อัตโนมัติของ Pal |
| `PAL_AUTO_HP_REGEN_RATE_IN_SLEEP` | `"1.000000"` | อัตราฟื้น HP ของ Pal ใน Palbox |
### สิ่งปลูกสร้าง ทรัพยากร และไอเทม

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `BUILD_OBJECT_HP_RATE` | `"1.000000"` | ตัวคูณ HP ของสิ่งปลูกสร้าง |
| `BUILD_OBJECT_DAMAGE_RATE` | `"1.000000"` | ตัวคูณความเสียหายที่สิ่งปลูกสร้างได้รับ |
| `BUILD_OBJECT_DETERIORATION_DAMAGE_RATE` | `"1.000000"` | อัตราเสื่อมสภาพของสิ่งปลูกสร้าง |
| `COLLECTION_DROP_RATE` | `"1.000000"` | ตัวคูณจำนวนทรัพยากรที่เก็บได้ |
| `COLLECTION_OBJECT_HP_RATE` | `"1.000000"` | ตัวคูณ HP ของวัตถุทรัพยากร |
| `COLLECTION_OBJECT_RESPAWN_SPEED_RATE` | `"1.000000"` | รอบเกิดใหม่ของทรัพยากร ค่ายิ่งต่ำยิ่งเกิดเร็ว |
| `ENEMY_DROP_ITEM_RATE` | `"1.000000"` | ตัวคูณไอเทมที่ศัตรูดรอป |
| `ITEM_WEIGHT_RATE` | `"1.000000"` | ตัวคูณน้ำหนักไอเทม |
| `EQUIPMENT_DURABILITY_DAMAGE_RATE` | `"1.000000"` | ตัวคูณการลดความทนทานอุปกรณ์ |
| `ITEM_CORRUPTION_MULTIPLIER` | `"1.000000"` | ตัวคูณอัตราการเน่าเสียของไอเทม |
| `ITEM_CONTAINER_FORCE_MARK_DIRTY_INTERVAL` | `"1.000000"` | รอบบังคับอัปเดตสถานะ Container ไอเทม |
| `DROP_ITEM_MAX_NUM` | `"3000"` | จำนวนไอเทมตกบนโลกสูงสุด |
| `DROP_ITEM_MAX_NUM_UNKO` | `"100"` | จำนวนกองมูลสูงสุดในโลก |
| `DROP_ITEM_ALIVE_MAX_HOURS` | `"1.000000"` | ชั่วโมงก่อนที่ไอเทมตกพื้นจะหาย |
| `PHYSICS_ACTIVE_DROP_ITEM_MAX_NUM` | `"-1"` | จำนวนไอเทมตกที่ใช้ฟิสิกส์พร้อมกัน -1 คือไม่จำกัด |
### ฐาน กิลด์ และแรงงาน

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `BASE_CAMP_MAX_NUM` | `"128"` | จำนวนฐานทั้งหมดสูงสุดในโลก |
| `BASE_CAMP_WORKER_MAX_NUM` | `"15"` | จำนวน Pal ทำงานสูงสุดต่อฐาน |
| `BASE_CAMP_MAX_NUM_IN_GUILD` | `"4"` | จำนวนฐานสูงสุดต่อกิลด์ |
| `MAX_BUILDING_LIMIT_NUM` | `"0"` | จำนวนสิ่งปลูกสร้างสูงสุดต่อฐาน 0 คือไม่จำกัด |
| `GUILD_PLAYER_MAX_NUM` | `"20"` | จำนวนสมาชิกสูงสุดต่อกิลด์ |
| `COOP_PLAYER_MAX_NUM` | `"4"` | จำนวนผู้เล่นสูงสุดใน Co-op |
| `AUTO_RESET_GUILD_NO_ONLINE_PLAYERS` | `"false"` | ลบกิลด์อัตโนมัติเมื่อไม่มีสมาชิกออนไลน์ตามเวลา |
| `AUTO_RESET_GUILD_TIME_NO_ONLINE_PLAYERS` | `"72.000000"` | ชั่วโมงก่อนรีเซ็ตกิลด์ที่ไม่มีผู้เล่นออนไลน์ |
| `GUILD_REJOIN_COOLDOWN_MINUTES` | `"0"` | นาทีที่ต้องรอก่อนกลับเข้ากิลด์ |
| `AUTO_TRANSFER_MASTER_CHECK_INTERVAL_SECONDS` | `"3600.000000"` | รอบตรวจการโอนหัวหน้ากิลด์เป็นวินาที |
| `AUTO_TRANSFER_MASTER_THRESHOLD_DAYS` | `"14"` | วันที่หัวหน้ากิลด์ไม่เข้าเกมก่อนโอนตำแหน่ง |
| `MAX_GUILDS_PER_FRAME` | `"10"` | จำนวนกิลด์สูงสุดที่ประมวลผลต่อเฟรม |
| `WORK_SPEED_RATE` | `"1.000000"` | ตัวคูณความเร็วการทำงาน |
| `MONSTER_FARM_ACTION_SPEED_RATE` | `"1.000000"` | ตัวคูณความเร็วการทำงานในฟาร์มของ Pal |
| `PAL_EGG_DEFAULT_HATCHING_TIME` | `"1.000000"` | ชั่วโมงฟักไข่ขนาดใหญ่ตามค่าเริ่มต้น |
### กฎการเล่นและ PvP

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DEATH_PENALTY` | `"Item"` | บทลงโทษตายเลือก None Item ItemAndEquipment หรือ All |
| `ENABLE_PLAYER_TO_PLAYER_DAMAGE` | `"false"` | อนุญาตให้ผู้เล่นทำความเสียหายกัน |
| `ENABLE_FRIENDLY_FIRE` | `"false"` | เปิด Friendly Fire |
| `ENABLE_INVADER_ENEMY` | `"true"` | เปิดเหตุการณ์ศัตรูบุกฐาน |
| `ACTIVE_UNKO` | `"false"` | เปิดระบบ UNKO ของเกม |
| `ENABLE_AIM_ASSIST_PAD` | `"true"` | เปิด Aim Assist สำหรับจอย |
| `ENABLE_AIM_ASSIST_KEYBOARD` | `"false"` | เปิด Aim Assist สำหรับคีย์บอร์ด |
| `IS_MULTIPLAY` | `"true"` | เปิดโหมด Multiplayer |
| `IS_PVP` | `"false"` | เปิดโหมด PvP |
| `HARDCORE` | `"false"` | เปิดโหมด Hardcore |
| `CHARACTER_RECREATE_IN_HARDCORE` | `"false"` | อนุญาตสร้างตัวละครใหม่หลังตายใน Hardcore |
| `PAL_LOST` | `"false"` | ให้ Pal หายเมื่อ Pal ตายในโหมด Hardcore |
| `CAN_PICKUP_OTHER_GUILD_DEATH_PENALTY_DROP` | `"false"` | ให้กิลด์อื่นเก็บของที่ตกจากการตายได้ |
| `ENABLE_NON_LOGIN_PENALTY` | `"true"` | เปิดบทลงโทษเมื่อผู้เล่นไม่เข้าเกมนาน |
| `ENABLE_FAST_TRAVEL` | `"true"` | เปิดใช้งาน Fast Travel |
| `IS_START_LOCATION_SELECT_BY_MAP` | `"false"` | อนุญาตเลือกจุดเริ่มต้นจากแผนที่ |
| `EXIST_PLAYER_AFTER_LOGOUT` | `"false"` | ให้ตัวละครผู้เล่นยังคงอยู่หลัง Logout |
| `ENABLE_DEFENSE_OTHER_GUILD_PLAYER` | `"false"` | เปิดการป้องกันผู้เล่นจากกิลด์อื่น |
| `INVISIBLE_OTHER_GUILD_BASE_CAMP_AREA_FX` | `"false"` | ซ่อนเอฟเฟกต์พื้นที่ฐานของกิลด์อื่น |
| `BUILD_AREA_LIMIT` | `"false"` | เปิดข้อจำกัดพื้นที่ก่อสร้าง |
| `DISPLAY_PVP_ITEM_NUM_ON_WORLD_MAP_BASE_CAMP` | `"false"` | แสดงจำนวนไอเทม PvP ของฐานบนแผนที่ |
| `DISPLAY_PVP_ITEM_NUM_ON_WORLD_MAP_PLAYER` | `"false"` | แสดงจำนวนไอเทม PvP ของผู้เล่นบนแผนที่ |
| `ADDITIONAL_DROP_ITEM_WHEN_PLAYER_KILLING_IN_PVP_MODE` | `"PlayerDropItem"` | ประเภทไอเทมเพิ่มเมื่อฆ่าผู้เล่นใน PvP |
| `ADDITIONAL_DROP_ITEM_WHEN_PLAYER_KILLING_IN_PVP_MODE_NUM` | `"1"` | จำนวนไอเทมเพิ่มเมื่อฆ่าผู้เล่นใน PvP |
| `ADDITIONAL_DROP_ITEM_WHEN_PLAYER_KILLING_IN_PVP_MODE_ENABLED` | `"false"` | เปิดดรอปไอเทมเพิ่มเมื่อฆ่าผู้เล่นใน PvP |
### การเกิดใหม่และระบบโลก

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `AUTO_SAVE_SPAN` | `"300.000000"` | ช่วงเวลาบันทึกอัตโนมัติเป็นวินาที |
| `SUPPLY_DROP_SPAN` | `"180"` | ช่วงเวลาระหว่าง Supply Drop เป็นนาที |
| `BLOCK_RESPAWN_TIME` | `"5.000000"` | เวลาบล็อกการเกิดใหม่ |
| `RESPAWN_PENALTY_DURATION_THRESHOLD` | `"0.000000"` | เกณฑ์ระยะเวลาที่เริ่มใช้บทลงโทษการเกิดใหม่ |
| `RESPAWN_PENALTY_TIME_SCALE` | `"2.000000"` | ตัวคูณเวลาบทลงโทษการเกิดใหม่ |
| `ENABLE_PREDATOR_BOSS_PAL` | `"true"` | เปิด Predator Boss Pal |
| `SERVER_REPLICATE_PAWN_CULL_DISTANCE` | `"15000.000000"` | ระยะที่เซิร์ฟเวอร์ส่งข้อมูลตัวละครให้ Client |
### ระบบผู้เล่น การแชต และการเข้าถึง

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `REGION` | `""` | ชื่อ Region ของเซิร์ฟเวอร์ |
| `USEAUTH` | `"true"` | เปิดระบบยืนยันตัวตน |
| `BAN_LIST_URL` | `"https://b.palworldgame.com/api/banlist.txt"` | URL รายการ Ban ที่เซิร์ฟเวอร์ใช้ |
| `SHOW_PLAYER_LIST` | `"false"` | อนุญาตให้แสดงรายชื่อผู้เล่น |
| `CHAT_POST_LIMIT_PER_MINUTE` | `"30"` | จำนวนข้อความสูงสุดต่อผู้เล่นต่อนาที |
| `ENABLE_VOICE_CHAT` | `"false"` | เปิด Voice Chat |
| `VOICE_CHAT_MAX_VOLUME_DISTANCE` | `"3000.000000"` | ระยะที่เสียงสนทนาดังเต็มที่ |
| `VOICE_CHAT_ZERO_VOLUME_DISTANCE` | `"15000.000000"` | ระยะที่เสียงสนทนาเบาจนเป็นศูนย์ |
| `IS_SHOW_JOIN_LEFT_MESSAGE` | `"true"` | แสดงข้อความเข้าและออกในเกม |
| `ALLOW_CLIENT_MOD` | `"true"` | อนุญาตให้ Client ใช้ Mod |
| `PLAYER_DATA_PAL_STORAGE_UPDATE_CHECK_TICK_INTERVAL` | `"1.000000"` | รอบตรวจอัปเดต Pal Storage ของผู้เล่น |
### Global Palbox และค่าสถานะตัวละคร

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `ALLOW_GLOBAL_PALBOX_EXPORT` | `"true"` | อนุญาตส่ง Pal ไป Global Palbox |
| `ALLOW_GLOBAL_PALBOX_IMPORT` | `"false"` | อนุญาตนำ Pal จาก Global Palbox เข้าเซิร์ฟเวอร์ |
| `ALLOW_ENHANCE_STAT_HEALTH` | `"true"` | อนุญาตเพิ่มค่าสถานะ Health |
| `ALLOW_ENHANCE_STAT_ATTACK` | `"true"` | อนุญาตเพิ่มค่าสถานะ Attack |
| `ALLOW_ENHANCE_STAT_STAMINA` | `"true"` | อนุญาตเพิ่มค่าสถานะ Stamina |
| `ALLOW_ENHANCE_STAT_WEIGHT` | `"true"` | อนุญาตเพิ่มค่าสถานะ Weight |
| `ALLOW_ENHANCE_STAT_WORK_SPEED` | `"true"` | อนุญาตเพิ่มค่าสถานะ Work Speed |
### เทคโนโลยีและข้อมูลสิ่งปลูกสร้าง

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `DENY_TECHNOLOGY_LIST` | `""` | รายการ Technology ID ที่ห้ามใช้ |
| `ENABLE_BUILDING_PLAYER_UID_DISPLAY` | `"false"` | แสดง Player UID ของเจ้าของสิ่งปลูกสร้าง |
| `BUILDING_NAME_DISPLAY_CACHE_TTL_SECONDS` | `"60"` | อายุ Cache ชื่อสิ่งปลูกสร้างเป็นวินาที |
### Engine และ Network Tuning

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `LAN_SERVER_MAX_TICK_RATE` | `"120"` | Tick Rate สูงสุดสำหรับการเชื่อมต่อ LAN |
| `NET_SERVER_MAX_TICK_RATE` | `"120"` | Tick Rate สูงสุดสำหรับการเชื่อมต่ออินเทอร์เน็ต |
| `CONFIGURED_INTERNET_SPEED` | `"104857600"` | แบนด์วิดท์อินเทอร์เน็ตสมมติเป็นไบต์ต่อวินาที |
| `CONFIGURED_LAN_SPEED` | `"104857600"` | แบนด์วิดท์ LAN สมมติเป็นไบต์ต่อวินาที |
| `MAX_CLIENT_RATE` | `"104857600"` | อัตราส่งข้อมูลสูงสุดต่อ Client |
| `MAX_INTERNET_CLIENT_RATE` | `"104857600"` | อัตราส่งข้อมูลสูงสุดต่อ Internet Client |
| `SMOOTH_FRAME_RATE` | `"true"` | เปิดการปรับ Frame Rate ให้เรียบขึ้น |
| `SMOOTH_FRAME_RATE_UPPER_LIMIT` | `"120.000000"` | ขอบบนของช่วง Frame Rate ที่ใช้ปรับให้เรียบ |
| `SMOOTH_FRAME_RATE_LOWER_LIMIT` | `"30.000000"` | ขอบล่างของช่วง Frame Rate ที่ใช้ปรับให้เรียบ |
| `USE_FIXED_FRAME_RATE` | `"false"` | บังคับใช้ Frame Rate คงที่ |
| `FIXED_FRAME_RATE` | `"120.000000"` | ค่า Frame Rate คงที่เมื่อเปิดใช้งาน |
| `MIN_DESIRED_FRAME_RATE` | `"60.000000"` | Frame Rate ขั้นต่ำที่ Engine พยายามรักษา |
| `NET_CLIENT_TICKS_PER_SECOND` | `"120"` | จำนวนรอบอัปเดตข้อมูล Client ต่อวินาที |
### ARM64 และ Box64 เฉพาะเครื่อง ARM

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `ARM64_DEVICE` | `"generic"` | รุ่นอุปกรณ์ ARM64 เลือก generic m1 rpi5 หรือ adlink |
| `BOX64_DYNAREC_STRONGMEM` | `"1"` | ระดับจำลอง Strong Memory ของ Box64 เลือก 0-3 |
| `BOX64_DYNAREC_BIGBLOCK` | `"1"` | ระดับ BigBlock ของ Box64 เลือก 0-3 |
| `BOX64_DYNAREC_SAFEFLAGS` | `"1"` | ระดับจัดการ Flags ของ Box64 เลือก 0-2 |
| `BOX64_DYNAREC_FASTROUND` | `"1"` | เปิดการปัดเศษแบบเร็วของ Box64 เลือก 0 หรือ 1 |
| `BOX64_DYNAREC_FASTNAN` | `"1"` | เปิดการจัดการ NaN แบบเร็วของ Box64 เลือก 0 หรือ 1 |
| `BOX64_DYNAREC_X87DOUBLE` | `"0"` | บังคับ x87 ใช้ Double เลือก 0 หรือ 1 |

## บริการ `docker-proxy`

รวม **5 ตัวแปร** ตามไฟล์ `docker-compose.yml` ของชุดนี้

### ทั่วไป

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `TZ` | `"Asia/Bangkok"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `LOG_LEVEL` | `"warning"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `CONTAINERS` | `"1"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `POST` | `"1"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PING` | `"1"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |

## บริการ `dashboard`

รวม **19 ตัวแปร** ตามไฟล์ `docker-compose.yml` ของชุดนี้

### ทั่วไป

| ตัวแปร | ค่า | ความหมาย/ข้อควรระวัง |
|---|---|---|
| `TZ` | `"Asia/Bangkok"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_TIMEZONE` | `"Asia/Bangkok"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_API_URL` | `"http://palworld:8212/v1/api"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_ADMIN_PASSWORD` | `"${PALWORLD_ADMIN_PASSWORD}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_CONTAINER_NAME` | `"palworld-server"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_DATA_DIR` | `"/palworld-data"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_PUID` | `"1000"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_PGID` | `"1000"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DOCKER_API_URL` | `"http://docker-proxy:2375"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_DATA_DIR` | `"/data"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_USERNAME` | `"${DASHBOARD_USERNAME:-admin}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_PASSWORD` | `"${DASHBOARD_PASSWORD:-CHANGE_ME_DASHBOARD_PASSWORD}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_REFRESH_SECONDS` | `"${DASHBOARD_REFRESH_SECONDS:-15}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_ACTIONS_ENABLED` | `"${DASHBOARD_ACTIONS_ENABLED:-true}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_DISCORD_WEBHOOK_URL` | `"${DISCORD_INFORMATION_WEBHOOK_URL:-}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_MAX_UPLOAD_MB` | `"${DASHBOARD_MAX_UPLOAD_MB:-4096}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `DASHBOARD_MAX_EXPANDED_MB` | `"${DASHBOARD_MAX_EXPANDED_MB:-8192}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_START_TIMEOUT_SECONDS` | `"${PALWORLD_START_TIMEOUT_SECONDS:-900}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |
| `PALWORLD_STOP_TIMEOUT_SECONDS` | `"${PALWORLD_STOP_TIMEOUT_SECONDS:-60}"` | ไม่มีคำอธิบายเพิ่มเติมใน Compose |


---

# ภาคผนวก B: คำสั่งตรวจสอบฉบับรวม

```bash
# สถานะและ Health
docker compose ps
docker inspect palworld-server --format '{{json .State}}'
docker inspect palworld-dashboard --format '{{json .State}}'

# Log
docker compose logs -f --tail=200 palworld dashboard docker-proxy

# Environment ที่เกี่ยวกับ REST/GameData
docker inspect palworld-server \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | sort | grep -E '^(REST_API|ENABLE_GAMEDATA|ADMIN_PASSWORD|RCON)'

# ตรวจ Health dashboard
curl http://127.0.0.1:8080/health

# ตรวจ REST info
curl -u 'admin:PASSWORD' http://127.0.0.1:8212/v1/api/info

# ตรวจ GameData ผ่าน image CLI
docker exec palworld-server sh -lc 'rest-cli game-data | head -c 1000; echo'

# ตรวจ Disk/RAM
df -h
df -i
free -h
docker stats --no-stream

# ตรวจ Save และ ZIP
sudo du -sh palworld/Pal/Saved dashboard/data/exports dashboard/data/imports
unzip -t dashboard/data/exports/FILE.zip
unzip -l dashboard/data/exports/FILE.zip | head -100

# ตรวจไฟล์ Recovery
find palworld -maxdepth 2 -name '.dashboard-*' -print
cat dashboard/data/state.json
cat dashboard/data/maintenance.json 2>/dev/null || true
```

---

# ภาคผนวก C: ข้อจำกัดที่ควรทราบ

1. Active Ban ไม่ใช่ Ban list ทั้งหมดของ Server
2. ไม่มีปุ่มลบ Import/Export จาก UI
3. ไม่มี Audit log สำหรับ Kick, Announce, Save, Manual Start, Manual Shutdown และ Force Stop
4. Basic Auth ไม่มี TLS ในตัว
5. Snapshot ส่ง JSON ทั้งก้อนไป Browser แต่แสดงเฉพาะ Summary
6. Scheduler ทำงานใน Process Dashboard เดียว ไม่มี Distributed lock ข้ามหลาย Replica
7. ไม่ควรรัน Dashboard มากกว่า 1 Replica บน `dashboard/data` ชุดเดียว
8. Import แทนที่ `Pal/Saved/` ทั้งชุด ไม่ Merge
9. Rollback เป็น Best effort และต้องตรวจมือเมื่อ Dashboard/Host ดับกะทันหัน
10. `latest` สามารถเปลี่ยนพฤติกรรมได้ ควรอ่าน Release notes ก่อนอัปเดต
11. `DISCORD_INVITE_URL` ใน `.env` ไม่ได้แทนข้อความ Hard-coded ทุกตำแหน่งใน Compose ปัจจุบัน
12. `DASHBOARD_MAX_ARCHIVE_FILES` มีค่า Backend เริ่มต้น 200,000 แต่ Compose ยังไม่ได้ Map จาก `.env`; หากต้องปรับต้องเพิ่ม Mapping ใน service Dashboard
13. Healthcheck ของ Palworld ตรวจ Process ไม่ได้พิสูจน์ว่า REST API พร้อมเสมอ Workflow จึงตรวจ `/info` แยกอีกชั้น
14. การกด Start Container ระหว่าง Maintenance อาจทำให้ Export/Import เสียลำดับ
15. Force Stop อาจทำให้ข้อมูลที่ยังไม่บันทึกสูญหาย

---

เอกสารฉบับนี้ปรับปรุงสำหรับ Palworld Server Dashboard ณ วันที่ 15 กรกฎาคม 2026
