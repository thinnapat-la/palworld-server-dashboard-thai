# Migration ไป Docker Named Volume

เอกสารนี้ใช้เมื่ออัปเกรดจากรุ่นที่ mount `./palworld:/palworld` ไปใช้ Named Volume `palworld-data`

> Windows Host-native mode ไม่ใช้ขั้นตอนนี้ เพราะ World อยู่ใน `PALWORLD_HOST_DIR`; หาก Path ยาวให้ใช้ `run\windows\05-Move-Server-To-Short-Path.bat`

---

## 1. เป้าหมาย

จาก:

```yaml
volumes:
  - ./palworld:/palworld
```

เป็น:

```yaml
volumes:
  - palworld-data:/palworld
```

Named Volume เก็บ binary, config, world, logs และ backup ของ Palworld container

---

## 2. ก่อนเริ่ม

- ผู้เล่นออกจาก Server
- Save World
- หยุด Stack
- ตรวจพื้นที่ว่าง
- ห้ามลบ source เดิมจนทดสอบ World สำเร็จ
- ตรวจชื่อ Volume ใน `.env`

```dotenv
PALWORLD_VOLUME_NAME=palworld-data
```

---

## 3. Migration อัตโนมัติ Linux/macOS

Linux:

```bash
chmod +x run/linux/migrate-to-named-volume.sh
./run/linux/migrate-to-named-volume.sh ./palworld
```

macOS สามารถเรียกสคริปต์เดียวกันจาก Terminal:

```bash
sh run/linux/migrate-to-named-volume.sh ./palworld
```

สคริปต์จะ:

1. `docker compose --profile admin down`
2. สร้าง tar.gz ที่ `migration-backups/`
3. สร้าง Named Volume
4. ตรวจปลายทางว่าง
5. Copy ด้วย Alpine container
6. ไม่ลบ source

---

## 4. Named Volume ไม่ว่าง

สคริปต์จะยกเลิกเพื่อป้องกันข้อมูลทับ

ตรวจ:

```bash
docker run --rm -v palworld-data:/data alpine:3.20 sh -c 'find /data -mindepth 1 -maxdepth 2 | head -100'
```

หากยืนยันว่าต้องทับ:

```bash
FORCE_MIGRATE=true ./run/linux/migrate-to-named-volume.sh ./palworld
```

คำสั่งนี้ลบข้อมูลใน Volume ปลายทางก่อน copy ใช้เฉพาะเมื่อมี Backup และตรวจชื่อ Volume แล้ว

---

## 5. Verification

ตรวจ directory:

```bash
docker run --rm -v palworld-data:/data alpine:3.20 sh -c '
  test -d /data/Pal/Saved &&
  find /data/Pal/Saved/SaveGames -maxdepth 3 -type d | head -50
'
```

เปิดเฉพาะ Server:

```bash
docker compose up -d palworld
docker compose logs -f --tail=200 palworld
```

ตรวจ:

- World เดิม
- Player เดิม
- Guild/base
- `PalWorldSettings.ini`
- Save World สำเร็จ

แล้วจึงเปิด Dashboard:

```bash
docker compose --profile admin up -d --no-deps --build docker-proxy dashboard
```

---

## 6. Manual backup ของ Named Volume

```bash
mkdir -p volume-backups
docker compose --profile admin down
docker run --rm \
  -v palworld-data:/source:ro \
  -v "$(pwd)/volume-backups:/backup" \
  alpine:3.20 \
  sh -c 'tar -czf /backup/palworld-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /source .'
```

ตรวจ archive:

```bash
tar -tzf volume-backups/palworld-data-*.tar.gz | head
```

---

## 7. Restore Named Volume

```bash
docker compose --profile admin down
docker volume create palworld-data
docker run --rm \
  -v palworld-data:/target \
  -v "$(pwd)/volume-backups:/backup:ro" \
  alpine:3.20 \
  sh -c 'rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true; tar -xzf /backup/<FILE>.tar.gz -C /target'
```

เปิดและตรวจ World ก่อนเปิด Dashboard

---

## 8. Rollback ไป bind mount

1. หยุด Stack
2. แก้ Compose กลับเป็น source เดิม
3. ยืนยันว่า source เดิมยังอยู่
4. เปิด Server
5. อย่าลบ Named Volume จนแน่ใจว่า rollback สำเร็จ

```yaml
volumes:
  - ./palworld:/palworld
```

---

## 9. เปลี่ยนชื่อ Volume

หาก `.env` ใช้:

```dotenv
PALWORLD_VOLUME_NAME=my-palworld-prod
```

ทุกคำสั่ง manual ต้องเปลี่ยน `palworld-data` เป็น `my-palworld-prod`

ตรวจชื่อจริงก่อนทำ destructive command:

```bash
docker compose config | sed -n '/volumes:/,$p'
docker volume ls
```

---

## 10. ห้ามทำ

- `docker compose down -v`
- `docker volume rm` ขณะยังไม่ Backup
- Copy World ขณะ Server กำลังเขียน Save
- ใช้ `FORCE_MIGRATE=true` โดยไม่ตรวจ destination
- ลบ source เดิมก่อนทดสอบ Player/World/Save
