# Changelog

## 1.1.0

- **Restart Config verification**: ล็อก Config ก่อน Shutdown, เขียนกลับหลัง Runtime หยุด, ตรวจ GET `/settings` ก่อน Completed และ Refresh หน้า Config อัตโนมัติ
- แก้ false mismatch ของ `DenyTechnologyList` ระหว่างค่าว่างใน INI กับ `[]` จาก REST API

### Architecture

- รองรับ Linux Docker, Windows Host-native และ macOS Docker ในแพ็กเกจเดียว
- Linux/macOS ใช้ Docker Named Volume `palworld-data`
- Windows รัน Native `steamcmd.exe` และ `PalServer.exe`
- Windows Dashboard ควบคุม runtime ผ่าน PowerShell Host Agent และ shared control directory

### Windows

- ลดคำสั่ง Windows เหลือ 6 ไฟล์: Setup/Update, Start All + System Check, Start Server, Start Dashboard, Stop All และ Move to Short Path
- ดาวน์โหลด Native Windows SteamCMD อัตโนมัติ
- Retry SteamCMD
- สร้างและ Patch Windows `PalWorldSettings.ini`
- เปิด REST API/RCON อัตโนมัติ
- รองรับ relative/absolute `PALWORLD_HOST_DIR`
- บังคับตรวจ path length และ write permission
- เพิ่ม migration ไป path สั้นเพื่อแก้ Save backup failure
- เก็บ Host Agent logs และ heartbeat
- `01-Start-All.bat` รวม Doctor เดิม ตรวจ 10 ขั้นและเปิด Dashboard ที่เคยถูก Stop ให้กลับมาทำงาน
- `03-Start-Dashboard.bat` เปิด Host Agent อัตโนมัติเพื่อให้ Lifecycle action ใช้งานได้
- `04-Stop-All.bat` Save World, REST Shutdown 1 วินาที, REST `/stop` และ taskkill fallback, หยุด Agent/Container และตรวจผลหลังปิด
- แก้ Windows `00-Setup.bat`/`04-Stop-All.bat` ที่ Palworld บางรุ่นตอบ HTTP 400 เมื่อส่ง `waittime=0`

### Dashboard

- รองรับ Docker และ External runtime mode
- Start/Stop/Restart maintenance
- แยกปุ่ม Config เป็น ล้างค่าร่าง, อัปเดตไฟล์ และ Restart Server; Restart ไม่เขียนค่าร่างหรือแก้ไฟล์ Config
- Restart Server ใช้ Palworld native shutdown countdown พร้อมเวลาเริ่มงาน, เวลารอแจ้งผู้เล่น, Countdown สด และเปิด Server กลับอัตโนมัติ
- เพิ่ม Startup recovery สำหรับกรณี Dashboard รีสตาร์ตระหว่าง Shutdown countdown
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
- เพิ่ม `GAME-CONFIG-REFERENCE-TH.md` อธิบายค่าเกมครบทุกตัว พร้อม Default และผลเมื่อเพิ่ม/ลด
- เพิ่มรายละเอียด Named Volume, Windows path, SteamCMD, Host Agent และ Dashboard workflow


### World selection verification

- `world_only` อ่าน World ID ที่ active จาก ZIP
- Patch `DedicatedServerName` ใน `GameUserSettings.ini` ของปลายทางอัตโนมัติ
- แสดง World ID และจำนวน Player save ในหน้า Import/Job
- ตรวจ World ID และ `Level.sav` หลัง Start ก่อนประกาศสำเร็จ
- Rollback ค่า `DedicatedServerName` พร้อม SaveGames เมื่อ Import ล้มเหลว


### สถานะค่าร่าง ค่าในไฟล์ และค่าที่ Server ใช้อยู่

หน้า Config แยกสถานะเป็น 3 ชั้นเพื่อป้องกันความสับสน:

- **Server ใช้อยู่**: ค่าจาก REST `GET /settings` ของ Process ที่กำลังรัน
- **ในไฟล์**: ค่าที่อ่านจาก `PalWorldSettings.ini` และจะถูกโหลดเมื่อ Restart
- **ค่าร่าง**: ค่าที่แก้ในหน้าเว็บแต่ยังไม่ได้กด **อัปเดตไฟล์**

หลังอัปเดตไฟล์สำเร็จ ค่าจะถูกย้ายออกจากรายการร่างและแสดงในคอลัมน์ **ในไฟล์ — รอ Restart** ปุ่ม Restart จะเตือนเฉพาะค่าร่างที่ยังไม่ได้เขียน ไม่เตือนค่าที่บันทึกลงไฟล์แล้ว

เมื่อเริ่ม Restart ระบบจะล็อกสำเนา `PalWorldSettings.ini` ล่าสุดไว้ก่อน จากนั้นแจ้งผู้เล่นและหยุด Server ให้สนิท แล้วเขียนสำเนาที่ล็อกไว้กลับลงไฟล์อีกครั้งก่อนเปิด Server วิธีนี้ป้องกันกรณี Process เดิมเขียนค่า Runtime เก่าทับไฟล์ระหว่าง Shutdown หลัง REST API พร้อม ระบบจะอ่าน `GET /settings` และตรวจเฉพาะค่าที่รอ Restart หากค่าไม่ตรง Job จะเป็น `failed` พร้อมระบุค่าที่ไม่ตรง แทนการขึ้น `completed` ผิด ๆ

เมื่อการตรวจผ่าน หน้า Config จะโหลดทั้ง `GET /settings` และไฟล์ใหม่อัตโนมัติ สถานะ **อัปเดตไฟล์แล้ว — รอ Restart** และตารางค่าที่รอใช้จะหายทันทีโดยไม่ต้อง Refresh หน้า นอกจากนี้ `DenyTechnologyList=` และ `DenyTechnologyList=()` จะถูกตีความเป็นรายการว่าง `[]` เหมือนกับ REST API จึงไม่แสดงเป็นความต่างปลอม
