# การย้ายและกู้คืน Save ด้วย Dashboard

เอกสารนี้อธิบายการใช้ Export ZIP เดียวกันกับ Import หลายวัตถุประสงค์ในเวอร์ชัน 1.1.0

## หลักการ

Export เก็บ `Pal/Saved` ทั้งชุดเสมอ เพื่อให้ไฟล์เดียวเป็นทั้ง:

- Backup เต็มชุด
- Source สำหรับย้าย World
- Source สำหรับกู้ Config

ตอน Import ผู้ใช้เป็นผู้เลือกขอบเขตที่จะ Restore

## โหมด Import

### 1. สลับ/ย้าย World และผู้เล่น (`world_only`)

แทนที่:

```text
Pal/Saved/SaveGames
```

เก็บของปลายทางไว้:

```text
Pal/Saved/Config
Pal/Saved/Logs
Pal/Saved/Crashes
```

ใช้สำหรับ:

- Windows → Linux/macOS
- Linux/macOS → Windows
- ย้าย World ไปเครื่องใหม่
- สลับเปิด Server คนละ Runtime แต่เล่น World เดิม

นี่คือค่าเริ่มต้นและเป็นตัวเลือกที่แนะนำ

### 2. Full restore (`full_restore`)

แทนที่:

```text
Pal/Saved
```

ใช้สำหรับ:

- กู้คืนเครื่องเดิมหลังข้อมูลเสีย
- Clone environment ที่โครงสร้างและ OS เหมือนกัน
- Disaster recovery ที่ต้องการ Config/Log/ข้อมูลประกอบจาก archive

ไม่แนะนำสำหรับย้ายข้าม Windows/Linux เพราะ Config directory คนละชื่อ

### 3. Config-only (`config_only`)

แทนที่เฉพาะ:

```text
Windows Host-native -> Pal/Saved/Config/WindowsServer
Linux/macOS Docker  -> Pal/Saved/Config/LinuxServer
```

ใช้สำหรับกู้ Config โดยไม่เปลี่ยน World หรือ Player save ระบบจะปฏิเสธหาก ZIP ไม่มี Config ของ platform ปลายทาง

## ขั้นตอนสลับ Server A → Server B

1. ตรวจว่า Server B ยังปิดอยู่
2. ที่ Server A กด Export และรอจน Runtime เปิดกลับ/Job completed
3. ดาวน์โหลด ZIP
4. ปิด Server A หลัง Save World
5. ที่ Server B อัปโหลด ZIP
6. เลือก `สลับ/ย้าย World และผู้เล่น`
7. กด Import และรอ Job completed
8. ตรวจ World GUID, ตัวละคร, Guild และสิ่งปลูกสร้าง
9. ห้ามเปิด Server A และ B พร้อมกันโดยใช้ World ชุดเดียวกัน

## Safety และ Rollback

ก่อน Import ทุกโหมด Dashboard สร้าง Full safety export ของปลายทาง จากนั้นย้าย target เดิมไป rollback path แล้วจึงนำข้อมูลใหม่เข้า หาก Server เปิดไม่สำเร็จ ระบบพยายามนำ target เดิมกลับ

Safety backup อยู่ที่:

```text
dashboard/data/exports/pre-import-*.zip
```

ยังควรเก็บ Backup นอกเครื่อง เพราะ Safety backup อยู่บน Disk เดียวกับระบบหลัก

## Compatibility

Export เก่าที่มี `Pal/Saved/` ยังใช้ได้ ระบบตรวจ path ภายใน ZIP เพื่อระบุว่าไฟล์รองรับโหมดใด หากไม่มี Manifest รุ่นใหม่ ระบบยัง Import ได้เมื่อโครงสร้างถูกต้อง

## การเลือก World หลัง Import

Palworld เลือก World ที่จะเปิดจากค่า `DedicatedServerName` ในไฟล์:

- Windows: `Pal/Saved/Config/WindowsServer/GameUserSettings.ini`
- Linux/macOS: `Pal/Saved/Config/LinuxServer/GameUserSettings.ini`

โหมด `world_only` จะตรวจ `SaveGames/0/<WorldID>/Level.sav`, เลือก World ID จาก ZIP, แก้ `DedicatedServerName` ของปลายทาง และตรวจซ้ำหลัง Server เปิด หากเลือก World ไม่สำเร็จ งานจะ Rollback ทั้ง `SaveGames` และค่า `DedicatedServerName` เดิม

หาก Job รุ่นเก่าแสดง `completed` แต่เกมให้สร้างตัวละครใหม่ ให้ตรวจว่าค่า `DedicatedServerName` ตรงกับชื่อโฟลเดอร์ World ที่นำเข้าหรือไม่
