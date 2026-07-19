# Architecture 1.1.0

## 1. Linux/macOS Docker mode

```text
                          +--------------------------+
Browser :8080 ---------->| Dashboard                |
                          | Python API + UI           |
                          +------------+-------------+
                                       |
                 REST /v1/api          | Docker API subset
                                       |
             +-------------------------+------------------+
             |                                            |
+------------v-------------+                 +------------v-------------+
| Palworld container       |                 | docker-socket-proxy      |
| Linux PalServer          |                 | CONTAINERS/POST/PING     |
+------------+-------------+                 +------------+-------------+
             |                                            |
             +------------------+-------------------------+
                                |
                        Docker Engine

Persistent:
- palworld-data -> /palworld and /palworld-data
- dashboard/data -> /data
```

### Control plane

- REST actions: Save, announce, kick, ban, unban, shutdown
- Docker actions: status, start, stop

### Data plane

- UDP 8211 gameplay
- UDP 27015 query
- REST 8212 internal/localhost

---

## 2. Windows Host-native mode

```text
Browser :8080
      |
      v
+--------------------------+
| dashboard-host container |
+----------+---------------+
           | REST via host.docker.internal:8212
           v
+--------------------------+
| PalServer.exe on Windows |
+--------------------------+

Dashboard lifecycle request
      |
      v
runtime/control/request-*.json
      |
      v
+--------------------------+
| PowerShell Host Agent    |
+----------+---------------+
           |
           +--> Start-Process PalServer.exe
           +--> REST Save/Shutdown + wait/taskkill fallback
           +--> status heartbeat

Shared data:
D:/PalServer <-> /palworld-data
runtime/control <-> /host-control
```


### Windows user commands

Windows เปิดให้ผู้ใช้เรียกเพียง 6 `.bat`: Setup/Update, Start All + System Check, Start Server, Start Dashboard, Stop All และ Move to Short Path ส่วน Status/Logs ใช้หน้า Dashboard หรือคำสั่ง Docker/PowerShell โดยตรง

`01-Start-All.bat` เป็น readiness gate หลัก และ `04-Stop-All.bat` เป็น shutdown gate ที่ตรวจว่า Server, Agent และ Dashboard หยุดจริงก่อนจบ
---

## 3. Windows IPC protocol

Request example:

```json
{
  "id": "<uuid>",
  "action": "start"
}
```

Response example:

```json
{
  "id": "<uuid>",
  "ok": true,
  "message": "Server started",
  "pid": 1234,
  "responded_at": "..."
}
```

Agent writes files atomically through temporary files to reduce partial JSON reads

---

## 4. Dashboard job model

```text
HTTP request -> jobs.json -> scheduler thread -> workflow -> job update -> UI poll
```

Only one active maintenance job should control runtime at a time Manual Start/Stop is blocked while a maintenance job is active

---

## 5. Storage ownership

### Docker mode

- Palworld image runs with PUID/PGID 1000
- Dashboard can chown imported files to configured Palworld owner
- Named Volume abstracts host path

### Windows mode

- PalServer and PowerShell run as current Windows user
- Docker Desktop mount permission depends on drive sharing and Windows ACL
- Imported files are written through Linux container onto Windows bind mount; verify ACL after Import if server cannot read them

---

## 6. Failure boundaries

| Failure | Game | Dashboard | Recovery |
|---|---|---|---|
| Dashboard container down/เคยถูก Stop | ยังรัน | Offline | รัน `03-Start-Dashboard.bat` หรือ `01-Start-All.bat` ซึ่ง Start Agent และ Container ให้ใหม่ |
| Docker proxy down | ยังรัน | อ่าน REST ได้ แต่ lifecycle ล้ม | Start proxy |
| Windows Agent down | ยังรันได้ | lifecycle/import/export ล้ม | `03-Start-Dashboard.bat` หรือ `01-Start-All.bat` เปิด Agent ให้อัตโนมัติ |
| REST password mismatch | ยังรัน | REST Offline | Sync password + restart |
| Named Volume missing | World ใหม่/ติดตั้งใหม่ | อาจอ่าน path ว่าง | Stop และแก้ volume name |
| Host path too long | Save failure | ยัง online | Relocate to short path |

---

## 7. Security boundaries

- Docker mode lifecycle ถูกจำกัดผ่าน socket proxy
- Windows mode ไม่มี Docker lifecycle access;ใช้ file IPC
- Dashboard container เป็น read-only root filesystem
- Temporary write อยู่ใน tmpfs
- `no-new-privileges` เปิด
- Persistent writes จำกัดที่ `/data`, `/palworld-data`, `/host-control`


## Import target selection

Export archive เป็น Full archive เสมอ:

```text
Pal/Saved/**
```

Import แยก target ตาม intent:

```text
world_only   -> Replace SaveGames only
config_only  -> Replace target OS config only
full_restore -> Replace complete Saved tree
```

แนวทางนี้แยก **backup format** ออกจาก **restore scope**: ไฟล์เดียวใช้ได้ทั้งย้าย World ข้ามระบบและ Full disaster recovery โดยไม่ต้องสร้าง Export หลายชนิด
