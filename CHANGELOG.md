# Changelog

## 1.1.0

### Architecture

- รองรับ Linux Docker, Windows Host-native และ macOS Docker ในแพ็กเกจเดียว
- Linux/macOS ใช้ Docker Named Volume `palworld-data`
- Windows รัน Native `steamcmd.exe` และ `PalServer.exe`
- Windows Dashboard ควบคุม runtime ผ่าน PowerShell Host Agent และ shared control directory

### Windows

- เพิ่ม Manager และคำสั่ง Setup/Start/Status/Logs/Update/Doctor
- ดาวน์โหลด Native Windows SteamCMD อัตโนมัติ
- Retry SteamCMD
- สร้างและ Patch Windows `PalWorldSettings.ini`
- เปิด REST API/RCON อัตโนมัติ
- รองรับ relative/absolute `PALWORLD_HOST_DIR`
- บังคับตรวจ path length และ write permission
- เพิ่ม migration ไป path สั้นเพื่อแก้ Save backup failure
- เก็บ Host Agent logs และ heartbeat

### Dashboard

- รองรับ Docker และ External runtime mode
- Start/Stop/Restart maintenance
- Config form/raw editor พร้อม backup
- Export/Import พร้อม safety backup, validation, staging และ rollback
- เพิ่ม Import scope 3 แบบ: ย้าย World/ผู้เล่น, Full restore และ Config-only โดยค่าเริ่มต้นรักษา Config ปลายทางไว้
- ป้องกัน Full restore ข้ามระบบก่อนหยุด Server โดยตรวจ `WindowsServer`/`LinuxServer` ใน ZIP
- แสดง Stage, รายละเอียด, เปอร์เซ็นต์, elapsed time และ REST wait status ในหน้า Maintenance
- Import สำเร็จแล้ว Start Server ใหม่อัตโนมัติ และ Completed เมื่อ REST API พร้อม
- เพิ่ม Rollback และ Startup recovery สำหรับ Job ที่ถูกขัดจังหวะระหว่าง Import
- Kick/Ban/Unban history
- Discord master switch
- Resource limit และ read-only container hardening

### Optimization

- ปิด `pal_logger.py` เป็น default ด้วย `LOG_FILTER_ENABLED=false`
- Palworld Docker ใช้ soft memory reservation ไม่มี hard CPU/RAM limit
- Dashboard และ Docker proxy มี CPU/RAM/PID limits
- Docker local log rotation
- Engine/network baseline 60 ใน Docker mode

### Documentation

- เขียน `README.md` ใหม่ให้ใช้งานได้ครบจากไฟล์เดียว
- ขยายคู่มือเชิงลึกทุกโหมด
- เพิ่ม Config reference, Architecture และ Troubleshooting
- เพิ่มรายละเอียด Named Volume, Windows path, SteamCMD, Host Agent และ Dashboard workflow


### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว
