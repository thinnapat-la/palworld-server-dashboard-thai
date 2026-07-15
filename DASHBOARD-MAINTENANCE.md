# Palworld Dashboard : Ban, Import/Export และ Maintenance

## สิ่งที่เพิ่ม

### Ban / Unban

- Ban ผู้เล่นจากรายชื่อผู้เล่นออนไลน์หรือกรอก User ID เอง
- Unban จาก User ID
- แสดง Active Ban ที่สั่งผ่าน Dashboard
- เก็บประวัติ Ban/Unban สูงสุด 1,000 รายการใน `dashboard/data/bans.json`
- แจ้ง Discord เมื่อ Ban หรือ Unban สำเร็จ

> Palworld REST API มีคำสั่ง `ban` และ `unban` แต่ไม่มี endpoint สำหรับอ่านรายชื่อผู้ถูกแบนทั้งหมด ดังนั้น Active Ban ในหน้านี้เป็นรายการที่ Dashboard บันทึกเอง ไม่ครอบคลุมคำสั่งที่สั่งผ่าน RCON หรือเครื่องมืออื่น

### Export

1. ตั้งเวลาทำงานจากหน้า Dashboard หรือปล่อยว่างเพื่อทำทันที
2. ส่งข้อความเข้าคิวงานไป Discord
3. เมื่อถึงเวลา ส่งประกาศในเกม
4. รอตามจำนวนวินาทีที่กำหนด
5. สั่ง Save World
6. หยุดคอนเทนเนอร์ `palworld-server` แบบ graceful
7. สร้าง ZIP จาก `Pal/Saved/`
8. เก็บไฟล์ที่ `dashboard/data/exports/`
9. เปิดคอนเทนเนอร์กลับ
10. รอจน Palworld REST API พร้อมใช้งาน
11. แจ้งผลและชื่อไฟล์ไป Discord
12. ดาวน์โหลด ZIP ผ่าน Dashboard

### Import

1. อัปโหลด ZIP ผ่าน Dashboard
2. ตรวจ ZIP ก่อนรับเข้า: ป้องกัน path traversal, symlink, ZIP เสีย และขนาดหลังแตกเกินเพดาน
3. ตั้งเวลาทำงานหรือทำทันที
4. เมื่อถึงเวลา ประกาศในเกมและรอตามเวลาที่กำหนด
5. Save World และหยุดคอนเทนเนอร์
6. สร้าง `pre-import-*.zip` เป็น Safety Backup
7. แตกไฟล์ไป staging directory
8. แทนที่ `Pal/Saved/`
9. กำหนด owner กลับเป็น PUID/PGID ของ Palworld
10. เปิดเซิร์ฟเวอร์และรอ REST API
11. ถ้าเปิดไม่สำเร็จ ระบบพยายาม rollback กลับข้อมูลเดิม
12. แจ้งทุกช่วงสำคัญและผลสำเร็จ/ล้มเหลวไป Discord

## รูปแบบไฟล์ Import

รองรับ ZIP ที่สร้างจาก Dashboard นี้ โดยภายในต้องมีโครงสร้างดังนี้:

```text
dashboard-export-manifest.json
Pal/
└── Saved/
    ├── Config/
    ├── SaveGames/
    └── ...
```

ไฟล์ ZIP ที่มี path อื่นนอก `Pal/Saved/` จะถูกปฏิเสธ เพื่อลดความเสี่ยงเขียนทับไฟล์ระบบ

## การติดตั้ง

```bash
cp .env.example .env
vi .env

mkdir -p dashboard/data/exports dashboard/data/imports

docker compose build dashboard
docker compose up -d
```

เปิด Dashboard ที่:

```text
http://SERVER_IP:8080
```

ตรวจสถานะ:

```bash
docker compose ps
docker compose logs -f dashboard docker-proxy palworld
```

## ตัวแปรสำคัญใน `.env`

```dotenv
DASHBOARD_PASSWORD=CHANGE_ME_DASHBOARD_PASSWORD
DISCORD_INFORMATION_WEBHOOK_URL=https://discord.com/api/webhooks/CHANGE_ME/CHANGE_ME
DASHBOARD_MAX_UPLOAD_MB=4096
DASHBOARD_MAX_EXPANDED_MB=8192
PALWORLD_START_TIMEOUT_SECONDS=900
PALWORLD_STOP_TIMEOUT_SECONDS=60
```

- `DASHBOARD_MAX_UPLOAD_MB`: ขนาด ZIP ที่อัปโหลดได้สูงสุด
- `DASHBOARD_MAX_EXPANDED_MB`: ขนาดรวมหลังแตก ZIP สูงสุด
- `PALWORLD_START_TIMEOUT_SECONDS`: เวลารอเซิร์ฟเวอร์เปิดหลัง Import/Export
- `PALWORLD_STOP_TIMEOUT_SECONDS`: เวลารอ Docker หยุดคอนเทนเนอร์แบบ graceful

## สิทธิ์และความปลอดภัย

- `docker-proxy` เป็นตัวกลางระหว่าง Dashboard กับ `/var/run/docker.sock`
- Dashboard ไม่ได้ mount Docker socket โดยตรง
- Dashboard mount `./palworld` แบบ read-write เพราะ Import ต้องแทนที่ข้อมูลเซฟ
- ควรเปิดพอร์ต Dashboard เฉพาะ LAN, VPN หรือผ่าน Reverse Proxy ที่มี HTTPS และ Access Control
- ตั้ง `DASHBOARD_PASSWORD` ให้ยาวและไม่ซ้ำกับรหัส Palworld
- ไม่ควร commit `.env` หรือไฟล์ใน `dashboard/data/`
- ก่อนใช้ Import ครั้งแรก ควรทดสอบกับสำเนาเซิร์ฟเวอร์และยืนยันว่า Export เปิดอ่านได้

## การแจ้ง Discord

Dashboard ส่งข้อความในเหตุการณ์ต่อไปนี้:

- สร้างคิว Export/Import
- เริ่ม Maintenance และเวลาเตือน
- เซิร์ฟเวอร์ปิดชั่วคราว
- สร้าง Export เสร็จ
- สร้าง Safety Backup ก่อน Import
- แทนที่ข้อมูล Import แล้วและกำลังเปิดเซิร์ฟเวอร์
- เปิดเซิร์ฟเวอร์และงานสำเร็จ
- งานล้มเหลวและผลการพยายามกู้คืน
- Ban/Unban สำเร็จ

ข้อความ start/shutdown/backup เดิมของ image Palworld ยังทำงานตามตัวแปร `DISCORD_*` ใน `docker-compose.yml` จึงอาจมีข้อความซ้ำบางช่วง หากไม่ต้องการให้ซ้ำให้ปิดข้อความเดิมบางรายการด้วยตัวแปร `*_ENABLED=false`

## ข้อจำกัด

- คิวงานทำทีละงาน เพื่อไม่ให้ Import/Export ชนกัน
- หาก Dashboard ถูกปิดระหว่างงาน ระบบจะบันทึกว่างานถูกขัดจังหวะและพยายามเปิดคอนเทนเนอร์กลับ แต่ควรตรวจ `dashboard/data/maintenance.json`, log และไฟล์ rollback ก่อนใช้งานต่อ
- Import เป็นการแทนที่ `Pal/Saved/` ทั้งชุด ไม่ใช่การ merge ตัวละครหรือโลก
- การย้ายเซฟจากเครื่องหรือ World ID อื่นอาจต้องปรับ `DedicatedServerName` เพิ่มเติมตามรูปแบบเซฟต้นทาง

## World Actor Snapshot และ GameData API

ปุ่ม `World Actor Snapshot` เรียก `GET /v1/api/game-data` ผ่าน Dashboard และต้องเปิด GameData API เพิ่มจาก REST API ปกติ:

```dotenv
ENABLE_GAMEDATA_API=true
```

จากนั้น Pull อิมเมจ `thijsvanloef/palworld-server-docker` รุ่น 2.6.0 ขึ้นไปและ Recreate:

```bash
docker compose pull palworld
docker compose up -d --force-recreate palworld
```

ตรวจค่า:

```bash
docker inspect palworld-server \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep '^ENABLE_GAMEDATA_API='
```

หากขึ้น `PalGameDataBridge GameData API is not enabled` แสดงว่า Container ยังไม่ได้รับค่า, ยังไม่ได้ Recreate หรือ Image เก่าเกินไป

Snapshot ไม่ใช่ Backup และอาจมี JSON ขนาดใหญ่ จึงโหลดเฉพาะเมื่อกด

## เอกสารเพิ่มเติม

- [`README.md`](README.md): ภาพรวมและ Quick start
- [`FULL_GUIDE_TH.md`](FULL_GUIDE_TH.md): คู่มือฉบับเต็ม การติดตั้ง ทุกเมนู GameData API Security และ Troubleshooting

---

เอกสารปรับปรุงสำหรับชุด ณ วันที่ 15 กรกฎาคม 2026

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
