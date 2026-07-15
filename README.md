# Palworld Server Dashboard

ชุด Docker Compose สำหรับติดตั้ง **Palworld Dedicated Server พร้อม Dashboard ผู้ดูแล** โดยเอกสารและหน้าจอหลักเป็นภาษาไทย รองรับการดูสถานะเซิร์ฟเวอร์ จัดการผู้เล่น Ban/Unban สั่งงานผู้ดูแล ตั้งคิว Import/Export พร้อม Safety Backup และโหลด World Actor Snapshot ผ่าน GameData API

## ความสามารถหลัก

- แสดงสถานะ Palworld, Container, FPS, Frame time, Uptime และผู้เล่นออนไลน์
- ดูรายชื่อผู้เล่น พร้อม Kick และ Ban
- Ban/Unban ด้วย User ID และเก็บประวัติที่ Dashboard สั่งเอง
- ประกาศข้อความ, Save World, Shutdown แบบมีเวลาเตือน และ Force Stop
- Start Container สำหรับกู้คืนกรณีเซิร์ฟเวอร์หยุด
- ตั้งคิว Export/Import ทำงานทีละงาน พร้อมประกาศในเกมและแจ้ง Discord
- ตรวจ ZIP Import ป้องกัน path traversal, symlink, ZIP เสีย, จำนวนไฟล์หรือขนาดหลังแตกเกินเพดาน
- สร้าง Safety Backup ก่อน Import และพยายาม Rollback หากเปิดเซิร์ฟเวอร์หลัง Import ไม่สำเร็จ
- ดาวน์โหลดไฟล์ Export จากหน้า Dashboard
- อ่านค่าตั้งค่าจาก Palworld REST API แบบ Read-only
- โหลด World Actor Snapshot เฉพาะเมื่อกด โดยใช้ `GET /v1/api/game-data`
- ใช้ Docker Socket Proxy แทนการ Mount Docker Socket เข้าสู่ Dashboard โดยตรง

## โครงสร้างบริการ

| Service | หน้าที่ | พอร์ตจาก Host |
|---|---|---|
| `palworld` | Palworld Dedicated Server, RCON และ REST API | `8211/udp`, `27015/udp`, `25575/tcp`, `127.0.0.1:8212/tcp` |
| `docker-proxy` | จำกัดสิทธิ์ Docker API ให้ Dashboard ใช้ตรวจ/เปิด/หยุดคอนเทนเนอร์ | ไม่เปิดออก Host |
| `dashboard` | Web Dashboard และตัวประมวลผลคิว Import/Export | `${DASHBOARD_BIND_ADDRESS}:${DASHBOARD_PORT}` ค่าเริ่มต้น `0.0.0.0:8080` |

ข้อมูลถาวรอยู่ที่:

```text
./palworld/                 # ไฟล์เกม Config Save และ Backup ของ Palworld
./dashboard/data/           # state, bans, maintenance, imports และ exports ของ Dashboard
```

## ความต้องการเบื้องต้น

- Linux 64-bit ที่ติดตั้ง Docker Engine และ Docker Compose Plugin
- CPU อย่างน้อย 4 Core เป็นแนวทางเริ่มต้น
- RAM 16 GB เป็นระดับใช้งานพื้นฐาน และ 32 GB ขึ้นไปเหมาะกับโลก/ผู้เล่นจำนวนมาก
- SSD ที่มีพื้นที่เผื่อสำหรับไฟล์เกม เซฟ Backup Export และ Safety Backup
- เปิด UDP `8211` ให้ผู้เล่นเชื่อมต่อ และเปิด `27015/udp` เมื่อใช้ Query/Community Server
- สิทธิ์อ่านเขียนโฟลเดอร์โปรเจกต์ และสิทธิ์เข้าถึง `/var/run/docker.sock` สำหรับ `docker-proxy`

## ติดตั้งแบบเร็ว

### 1. แตกไฟล์และเข้าโฟลเดอร์

```bash
unzip palworld-dashboard.zip
```

### 2. ตั้งค่า `.env`

ไฟล์ชุดนี้มี `.env.example` ให้ใช้เป็นต้นแบบ:

```bash
cp .env.example .env
nano .env
```

อย่างน้อยต้องแก้:

```dotenv
PALWORLD_SERVER_PASSWORD=รหัสผ่านผู้เล่น
PALWORLD_ADMIN_PASSWORD=รหัสผู้ดูแลที่ยาวและเดายาก
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=รหัสผ่านหน้า Dashboard ที่ยาวและไม่ซ้ำรหัสอื่น
```

หากไม่ใช้ Discord ให้กำหนด Webhook เป็นค่าว่าง แทนการปล่อย URL ตัวอย่าง:

```dotenv
DISCORD_INFORMATION_WEBHOOK_URL=
DISCORD_WELCOME_WEBHOOK_URL=
DISCORD_SESSION_WEBHOOK_URL=
DISCORD_INVITE_URL=
```

### 3. เปิด GameData API สำหรับ World Actor Snapshot

เตรียมตัวแปรนี้ไว้แล้ว:

```dotenv
ENABLE_GAMEDATA_API=true
```

และ Compose ส่งเข้า Palworld container ดังนี้:

```yaml
ENABLE_GAMEDATA_API: "${ENABLE_GAMEDATA_API:-true}"
```

ฟังก์ชันนี้ต้องใช้อิมเมจ `thijsvanloef/palworld-server-docker` รุ่น **2.6.0 หรือใหม่กว่า** จึงควร Pull อิมเมจใหม่ก่อนสร้างคอนเทนเนอร์

### 4. สร้างโฟลเดอร์ข้อมูลและเปิดระบบ

```bash
mkdir -p dashboard/data/exports dashboard/data/imports

docker compose pull palworld docker-proxy
docker compose up -d --build
```

ติดตามการติดตั้งครั้งแรก:

```bash
docker compose logs -f palworld dashboard docker-proxy
```

การติดตั้งหรืออัปเดต Palworld ครั้งแรกอาจใช้เวลาหลายนาทีตามความเร็วเครือข่ายและดิสก์

### 5. เปิด Dashboard

```text
http://SERVER_IP:8080
```

เข้าสู่ระบบด้วย `DASHBOARD_USERNAME` และ `DASHBOARD_PASSWORD` ใน `.env`

## ตรวจสอบหลังติดตั้ง

```bash
docker compose ps
docker compose logs --tail=200 palworld
docker compose logs --tail=200 dashboard
docker compose logs --tail=200 docker-proxy
```

ตรวจ Health ของ Dashboard:

```bash
curl http://127.0.0.1:8080/health
```

ผลที่คาดหวัง:

```text
ok v1.0.0
```

ตรวจว่า GameData API ถูกส่งเข้า Container:

```bash
docker inspect palworld-server \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep '^ENABLE_GAMEDATA_API='
```

ผลที่คาดหวัง:

```text
ENABLE_GAMEDATA_API=true
```

จากนั้นกด **คำสั่งผู้ดูแล → World Actor Snapshot → โหลด Snapshot**

## หาก GameData API ยังตอบ 404

ข้อความ:

```text
PalGameDataBridge GameData API is not enabled
```

ให้ทำตามลำดับนี้:

```bash
grep '^ENABLE_GAMEDATA_API=' .env
docker compose pull palworld
docker compose up -d --force-recreate palworld
docker compose logs -f palworld
```

หากแก้เฉพาะ `.env` แต่ไม่ได้ Recreate คอนเทนเนอร์ ค่าใหม่จะยังไม่ถูกนำเข้า

## คำสั่งใช้งานประจำ

```bash
# ดูสถานะ
docker compose ps

# ดู Log ทั้งระบบ
docker compose logs -f --tail=200

# Restart เฉพาะ Dashboard
docker compose restart dashboard

# Restart Palworld แบบ Docker graceful stop/start
docker compose restart palworld

# อัปเดต Palworld image แล้วสร้างใหม่
docker compose pull palworld
docker compose up -d --force-recreate palworld

# Build Dashboard ใหม่หลังแก้ server.py/index.html
docker compose up -d --build dashboard

# ปิดระบบทั้งหมด
docker compose down

# ปิดโดยไม่ลบ Volume bind mount
docker compose down
```

## หลักการ Import/Export

### Export

เมื่อถึงเวลางาน ระบบจะ:

1. ประกาศในเกมและ Discord
2. รอตาม `warning_seconds`
3. สั่ง Save World
4. หยุด `palworld-server` แบบ graceful
5. สร้าง ZIP จาก `Pal/Saved/`
6. เก็บที่ `dashboard/data/exports/`
7. เปิดคอนเทนเนอร์กลับ
8. รอ REST API พร้อม
9. เปลี่ยนสถานะงานเป็น `completed` และแจ้ง Discord

### Import

1. อัปโหลดและตรวจ ZIP
2. เมื่อถึงเวลา ประกาศและรอ
3. Save World และหยุดคอนเทนเนอร์
4. สร้าง `pre-import-*.zip` เป็น Safety Backup
5. แตกไฟล์ใน Staging
6. ย้าย `Pal/Saved/` เดิมไปตำแหน่ง Rollback ชั่วคราว
7. นำ `Pal/Saved/` ใหม่เข้าที่
8. ตั้ง Owner ตาม `PALWORLD_PUID/PALWORLD_PGID`
9. เปิดเซิร์ฟเวอร์และรอ REST API
10. หากล้มเหลวหลังย้ายข้อมูล ระบบพยายามนำข้อมูลเดิมกลับ

รูปแบบ ZIP ที่ยอมรับ:

```text
dashboard-export-manifest.json   # มีหรือไม่มีก็ได้ตามเงื่อนไขตัวตรวจ
Pal/
└── Saved/
    ├── Config/
    ├── SaveGames/
    └── ...
```

ไฟล์อื่นนอก `Pal/Saved/` จะถูกปฏิเสธ

## ความปลอดภัยที่ต้องทำ

- ห้ามเปิด Palworld REST API `8212/tcp` ออก Internet; Compose ผูกไว้ที่ `127.0.0.1` แล้ว
- จำกัด RCON `25575/tcp` ด้วย Firewall หรือเปลี่ยนการ Bind เป็น localhost เมื่อไม่ต้องให้เครื่องอื่นใช้
- Dashboard ใช้ Basic Authentication แต่ไม่มี HTTPS ในตัว ควรใช้เฉพาะ LAN/VPN หรือวางหลัง Reverse Proxy ที่มี TLS
- เปลี่ยนรหัสผ่านตัวอย่างทั้งหมดก่อนเปิดใช้งาน
- ห้าม Commit `.env`, `palworld/` และ `dashboard/data/`
- Import มีสิทธิ์แทนที่เซฟทั้งชุด ควรตรวจไฟล์และเลือกช่วงไม่มีผู้เล่น
- เก็บ Backup นอกเครื่องเพิ่มอีกชุด เพราะ Export/Safety Backup ยังอยู่บนดิสก์เดียวกับเซิร์ฟเวอร์โดยค่าเริ่มต้น

## เอกสารฉบับเต็ม

อ่านรายละเอียดทุกเมนู ทุกขั้นตอนการกู้คืน ตัวแปรทั้งหมด และ Troubleshooting ได้ที่:

- [`PALWORLD-DASHBOARD-MANUAL-TH.md`](PALWORLD-DASHBOARD-MANUAL-TH.md)
- [`DASHBOARD-MAINTENANCE.md`](DASHBOARD-MAINTENANCE.md)

## แหล่งอ้างอิงหลัก

- [Palworld Server Guide: Requirements](https://docs.palworldgame.com/getting-started/requirements/)
- [Palworld Server Guide: REST API](https://docs.palworldgame.com/api/rest-api/palwold-rest-api/)
- [Palworld Server Guide: REST API endpoints](https://docs.palworldgame.com/category/rest-api/)
- [thijsvanloef/palworld-server-docker](https://github.com/thijsvanloef/palworld-server-docker)
- [Release 2.6.0: ENABLE_GAMEDATA_API](https://github.com/thijsvanloef/palworld-server-docker/releases/tag/2.6.0)

---

เอกสารปรับปรุงสำหรับชุด ณ วันที่ 15 กรกฎาคม 2026
