#!/usr/bin/env python3
import base64
import hashlib
import json
import math
import re
import os
import shutil
import stat
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

APP_VERSION = "1.1.0"
API_URL = os.getenv("PALWORLD_API_URL", "http://127.0.0.1:8212/v1/api").rstrip("/")
ADMIN_PASSWORD = os.getenv("PALWORLD_ADMIN_PASSWORD", "")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
REFRESH_SECONDS = max(5, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30")))
LISTEN_PORT = int(os.getenv("DASHBOARD_LISTEN_PORT", "8080"))
ACTIONS_ENABLED = os.getenv("DASHBOARD_ACTIONS_ENABLED", "true").lower() == "true"
TIMEZONE_NAME = os.getenv("DASHBOARD_TIMEZONE", "Asia/Bangkok")
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)
DOCKER_API_URL = os.getenv("DOCKER_API_URL", "http://docker-proxy:2375").rstrip("/")
PALWORLD_CONTAINER_NAME = os.getenv("PALWORLD_CONTAINER_NAME", "palworld-server")
RUNTIME_MODE = os.getenv("PALWORLD_RUNTIME_MODE", "docker").strip().lower()
if RUNTIME_MODE not in ("docker", "external"):
    RUNTIME_MODE = "docker"
RUNTIME_LABEL = os.getenv("PALWORLD_RUNTIME_LABEL", "Docker container" if RUNTIME_MODE == "docker" else "Host-native server")
TARGET_CONFIG_PLATFORM = "WindowsServer" if RUNTIME_MODE == "external" else "LinuxServer"
IMPORT_MODE_LABELS = {
    "world_only": "ย้าย World/ผู้เล่นข้ามเซิร์ฟเวอร์",
    "full_restore": "กู้คืน Pal/Saved ทั้งชุด",
    "config_only": f"กู้คืน Config สำหรับ {TARGET_CONFIG_PLATFORM}",
}
DEFAULT_IMPORT_MODE = "world_only"
WORLD_ID_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
DEDICATED_SERVER_NAME_RE = re.compile(r"(?mi)^\s*DedicatedServerName\s*=\s*([A-Fa-f0-9]{32})\s*$")
JOB_STAGE_INFO = {
    "scheduled": ("รอถึงเวลาที่กำหนด", "งานอยู่ในคิวและยังไม่เริ่ม", 0),
    "starting": ("กำลังเริ่มงาน", "Dashboard กำลังเตรียม Workflow", 2),
    "announcing": ("กำลังประกาศ Maintenance", "ส่งข้อความแจ้งผู้เล่นและรอตามเวลาเตือน", 8),
    "stopping_server": ("กำลังหยุดเซิร์ฟเวอร์", "บันทึก World และหยุด Palworld runtime ก่อนจัดการไฟล์", 18),
    "safety_backup": ("กำลังสร้าง Safety Backup", "สำรอง Pal/Saved ปัจจุบันก่อน Import", 30),
    "creating_archive": ("กำลังสร้างไฟล์ Export", "กำลังบีบอัด Pal/Saved เป็น ZIP", 52),
    "validating_archive": ("กำลังตรวจไฟล์ Import", "ตรวจโครงสร้าง ZIP และความเข้ากันได้กับระบบปลายทาง", 4),
    "extracting": ("กำลังแตกไฟล์ ZIP", "ตรวจและแตกข้อมูลไปยังพื้นที่ชั่วคราว", 45),
    "replacing_savegames": ("กำลังแทนที่ World และผู้เล่น", "แทนที่เฉพาะ Pal/Saved/SaveGames", 58),
    "updating_world_selection": ("กำลังเลือก World ที่นำเข้า", "แก้ DedicatedServerName ให้ชี้ไปยัง World ID จาก ZIP", 68),
    "replacing_target_config": ("กำลังกู้คืน Config", "แทนที่ Config ของระบบปลายทางเท่านั้น", 60),
    "replacing_saved_data": ("กำลังกู้คืน Pal/Saved", "แทนที่ข้อมูล Pal/Saved ทั้งชุด", 60),
    "starting_server": ("กำลังสั่งเปิดเซิร์ฟเวอร์", "ส่งคำสั่ง Start ไปยัง Palworld runtime", 72),
    "waiting_rest_api": ("กำลังรอ REST API", "Server process เริ่มแล้ว กำลังรอ Palworld พร้อมใช้งาน", 82),
    "verifying_imported_world": ("กำลังตรวจ World ที่เปิดใช้งาน", "ตรวจว่า Server เลือก World ID ที่นำเข้าและมี Level.sav จริง", 98),
    "rollback_stopping_server": ("กำลังหยุด Server เพื่อ Rollback", "Import ไม่สำเร็จ กำลังหยุด Runtime ก่อนคืนข้อมูลเดิม", 72),
    "rollback_restoring": ("กำลังคืนข้อมูลเดิม", "ย้ายข้อมูลก่อน Import กลับเข้าที่", 78),
    "rollback_starting_server": ("กำลังเปิด Server หลัง Rollback", "คืนข้อมูลเดิมแล้ว กำลังเปิด Palworld กลับ", 88),
    "rollback_waiting_rest_api": ("กำลังรอ REST หลัง Rollback", "กำลังตรวจว่า Server เดิมกลับมาใช้งานได้", 92),
    "completed": ("เสร็จสมบูรณ์", "งานเสร็จและ Server พร้อมใช้งาน", 100),
    "failed": ("งานล้มเหลว", "ตรวจข้อความข้อผิดพลาดและสถานะการกู้คืน", 100),
    "interrupted": ("งานถูกขัดจังหวะ", "Dashboard ถูกรีสตาร์ตระหว่างทำงาน", 100),
    "cancelled": ("ยกเลิกแล้ว", "งานถูกยกเลิกก่อนเริ่ม", 100),
}
EXTERNAL_CONTROL_DIR = Path(os.getenv("PALWORLD_EXTERNAL_CONTROL_DIR", "/host-control")).resolve()
EXTERNAL_CONTROL_TIMEOUT = max(10, int(os.getenv("PALWORLD_EXTERNAL_CONTROL_TIMEOUT", "90")))
PALWORLD_DATA_DIR = Path(os.getenv("PALWORLD_DATA_DIR", "/palworld-data")).resolve()
SAVED_DIR = PALWORLD_DATA_DIR / "Pal" / "Saved"
DATA_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", "/data")).resolve()
EXPORT_DIR = DATA_DIR / "exports"
IMPORT_DIR = DATA_DIR / "imports"
STAGING_DIR = PALWORLD_DATA_DIR / ".dashboard-staging"
STATE_FILE = DATA_DIR / "state.json"
BAN_FILE = DATA_DIR / "bans.json"
MAINTENANCE_FILE = DATA_DIR / "maintenance.json"
CONFIG_FILE = Path(os.getenv("PALWORLD_CONFIG_FILE", str(SAVED_DIR / "Config" / "LinuxServer" / "PalWorldSettings.ini"))).resolve()
CONFIG_BACKUP_DIR = DATA_DIR / "config-backups"
MAX_CONFIG_BYTES = max(16 * 1024, int(os.getenv("DASHBOARD_MAX_CONFIG_KB", "1024")) * 1024)
MAX_CONFIG_BACKUPS = max(1, int(os.getenv("DASHBOARD_MAX_CONFIG_BACKUPS", "100")))
DISCORD_WEBHOOK_URL = os.getenv("DASHBOARD_DISCORD_WEBHOOK_URL", "").strip()
DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED = os.getenv("DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED", "true").strip().lower() == "true"
MAX_UPLOAD_BYTES = max(1, int(os.getenv("DASHBOARD_MAX_UPLOAD_MB", "4096"))) * 1024 * 1024
MAX_EXPANDED_BYTES = max(MAX_UPLOAD_BYTES, int(os.getenv("DASHBOARD_MAX_EXPANDED_MB", "8192")) * 1024 * 1024)
MAX_ARCHIVE_FILES = max(100, int(os.getenv("DASHBOARD_MAX_ARCHIVE_FILES", "200000")))
START_TIMEOUT_SECONDS = max(60, int(os.getenv("PALWORLD_START_TIMEOUT_SECONDS", "900")))
STOP_TIMEOUT_SECONDS = max(10, int(os.getenv("PALWORLD_STOP_TIMEOUT_SECONDS", "60")))
PALWORLD_PUID = int(os.getenv("PALWORLD_PUID", "1000"))
PALWORLD_PGID = int(os.getenv("PALWORLD_PGID", "1000"))
MAX_JSON_BODY = max(256 * 1024, MAX_CONFIG_BYTES * 2 + 64 * 1024)

STATE_LOCK = threading.RLock()
MAINTENANCE_LOCK = threading.Lock()
CONFIG_LOCK = threading.RLock()
SCHEDULER_WAKE = threading.Event()


def now_local():
    return datetime.now(LOCAL_TZ)


def iso_now():
    return now_local().isoformat(timespec="seconds")


def ensure_directories():
    paths = [DATA_DIR, EXPORT_DIR, IMPORT_DIR, STAGING_DIR, CONFIG_BACKUP_DIR]
    if RUNTIME_MODE == "external":
        paths.append(EXTERNAL_CONTROL_DIR)
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def load_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
            return value
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def initial_state():
    return {"jobs": [], "last_job_id": None}


def initial_bans():
    return {"active": {}, "history": []}


ensure_directories()
STATE = load_json(STATE_FILE, initial_state())
BANS = load_json(BAN_FILE, initial_bans())
if not isinstance(STATE, dict) or not isinstance(STATE.get("jobs"), list):
    STATE = initial_state()
if not isinstance(BANS, dict) or not isinstance(BANS.get("active"), dict) or not isinstance(BANS.get("history"), list):
    BANS = initial_bans()


def save_state():
    with STATE_LOCK:
        atomic_json_write(STATE_FILE, STATE)


def save_bans():
    with STATE_LOCK:
        BANS["history"] = BANS.get("history", [])[-1000:]
        atomic_json_write(BAN_FILE, BANS)


def auth_header():
    token = base64.b64encode(f"admin:{ADMIN_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def api_request(endpoint, method="GET", payload=None, timeout=20):
    data = None
    headers = auth_header()
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{API_URL}/{endpoint}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {"message": raw.decode("utf-8", errors="replace")}


def docker_request(path, method="GET", payload=None, timeout=30, allow_status=()):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{DOCKER_API_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in allow_status:
            return {}
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Docker API HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"เชื่อมต่อ Docker Socket Proxy ไม่ได้: {exc.reason}") from exc


def external_agent_status():
    status_file = EXTERNAL_CONTROL_DIR / "status.json"
    try:
        with status_file.open("r", encoding="utf-8-sig") as fh:
            payload = json.load(fh)
        heartbeat = payload.get("heartbeat_at")
        stale = True
        if heartbeat:
            try:
                stamp = datetime.fromisoformat(heartbeat)
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=LOCAL_TZ)
                stale = (now_local() - stamp.astimezone(LOCAL_TZ)).total_seconds() > 15
            except Exception:
                stale = True
        if stale:
            raise RuntimeError("Host Agent ไม่ตอบสนองเกิน 15 วินาที")
        return {
            "available": True,
            "running": bool(payload.get("running")),
            "status": payload.get("status", "unknown"),
            "health": "host-agent",
            "pid": payload.get("pid"),
            "started_at": payload.get("started_at"),
            "finished_at": payload.get("finished_at"),
            "runtime_mode": RUNTIME_MODE,
            "runtime_label": RUNTIME_LABEL,
        }
    except Exception as exc:
        try:
            api_request("info", timeout=3)
            return {
                "available": False,
                "running": True,
                "status": "running-no-agent",
                "health": "rest-online",
                "runtime_mode": RUNTIME_MODE,
                "runtime_label": RUNTIME_LABEL,
                "error": str(exc),
            }
        except Exception:
            return {
                "available": False,
                "running": False,
                "status": "agent-offline",
                "health": "unknown",
                "runtime_mode": RUNTIME_MODE,
                "runtime_label": RUNTIME_LABEL,
                "error": str(exc),
            }


def external_control_request(action):
    if action not in ("start", "stop"):
        raise ValueError("คำสั่ง Host Agent ไม่ถูกต้อง")
    EXTERNAL_CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    request_id = uuid.uuid4().hex
    request_file = EXTERNAL_CONTROL_DIR / f"request-{request_id}.json"
    response_file = EXTERNAL_CONTROL_DIR / f"response-{request_id}.json"
    atomic_json_write(request_file, {"id": request_id, "action": action, "requested_at": iso_now()})
    deadline = time.time() + EXTERNAL_CONTROL_TIMEOUT
    while time.time() < deadline:
        if response_file.is_file():
            try:
                with response_file.open("r", encoding="utf-8-sig") as fh:
                    response = json.load(fh)
            finally:
                try:
                    response_file.unlink()
                except FileNotFoundError:
                    pass
            if not response.get("ok"):
                raise RuntimeError(response.get("error") or f"Host Agent ทำคำสั่ง {action} ไม่สำเร็จ")
            return response
        time.sleep(0.5)
    try:
        request_file.unlink()
    except FileNotFoundError:
        pass
    raise RuntimeError(f"Host Agent ไม่ตอบกลับคำสั่ง {action} ภายใน {EXTERNAL_CONTROL_TIMEOUT} วินาที")


def container_info():
    if RUNTIME_MODE != "docker":
        return {}
    quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
    return docker_request(f"/containers/{quoted}/json", timeout=10)


def container_status():
    if RUNTIME_MODE == "external":
        return external_agent_status()
    try:
        info = container_info()
        state = info.get("State", {})
        return {
            "available": True,
            "running": bool(state.get("Running")),
            "status": state.get("Status", "unknown"),
            "health": (state.get("Health") or {}).get("Status", "none"),
            "started_at": state.get("StartedAt"),
            "finished_at": state.get("FinishedAt"),
            "runtime_mode": RUNTIME_MODE,
            "runtime_label": RUNTIME_LABEL,
        }
    except Exception as exc:
        return {"available": False, "running": False, "status": "unknown", "health": "unknown", "runtime_mode": RUNTIME_MODE, "runtime_label": RUNTIME_LABEL, "error": str(exc)}


def stop_container():
    if RUNTIME_MODE == "external":
        try:
            api_request("shutdown", "POST", {"waittime": 0, "message": "Dashboard maintenance shutdown"}, timeout=15)
        except Exception as exc:
            print(f"REST shutdown before Host Agent stop failed: {exc}")
        external_control_request("stop")
    else:
        quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
        docker_request(
            f"/containers/{quoted}/stop?t={STOP_TIMEOUT_SECONDS}",
            method="POST",
            timeout=STOP_TIMEOUT_SECONDS + 15,
            allow_status=(304,),
        )
    deadline = time.time() + STOP_TIMEOUT_SECONDS + 30
    while time.time() < deadline:
        status = container_status()
        if not status.get("running"):
            return
        time.sleep(1)
    raise RuntimeError("หยุด Palworld runtime ไม่สำเร็จภายในเวลาที่กำหนด")


def start_container():
    if RUNTIME_MODE == "external":
        external_control_request("start")
        return
    quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
    docker_request(f"/containers/{quoted}/start", method="POST", timeout=30, allow_status=(304,))

def wait_for_server_ready(timeout_seconds=START_TIMEOUT_SECONDS, job_id=None, stage="waiting_rest_api", context=""):
    started = time.time()
    deadline = started + timeout_seconds
    last_error = ""
    label, default_detail, base_progress = JOB_STAGE_INFO.get(stage, (stage.replace("_", " "), "", 82))
    if job_id:
        set_job_stage(job_id, stage, detail=context or default_detail, progress=base_progress)
    while time.time() < deadline:
        status = container_status()
        elapsed = int(time.time() - started)
        remaining = max(0, int(deadline - time.time()))
        runtime_state = status.get("status") or ("running" if status.get("running") else "stopped")
        if status.get("available") and not status.get("running"):
            last_error = f"Palworld runtime หยุดระหว่างรอ (status={runtime_state})"
        else:
            try:
                api_request("info", timeout=8)
                if job_id:
                    update_job(
                        job_id,
                        stage_detail=f"REST API พร้อมแล้วหลังรอ {elapsed} วินาที",
                        progress_percent=max(base_progress, 98),
                    )
                return
            except Exception as exc:
                last_error = str(exc)
        if job_id:
            span = max(1, timeout_seconds)
            dynamic_progress = min(97, base_progress + int((elapsed / span) * max(1, 97 - base_progress)))
            detail_prefix = context or default_detail
            update_job(
                job_id,
                stage_detail=(
                    f"{detail_prefix} | รอแล้ว {elapsed} วินาที, เหลือไม่เกิน {remaining} วินาที | "
                    f"Runtime: {runtime_state} | REST: {last_error or 'กำลังตรวจ'}"
                ),
                progress_percent=dynamic_progress,
                runtime_status=status,
            )
        time.sleep(5)
    raise RuntimeError(
        f"Palworld REST API ยังไม่พร้อมหลังรอ {timeout_seconds} วินาที: {last_error}. "
        f"ตรวจ Config/{TARGET_CONFIG_PLATFORM}/PalWorldSettings.ini ว่า RESTAPIEnabled=True, "
        "RESTAPIPort และ AdminPassword ตรงกับ Dashboard"
    )


def clean_text(value, max_len=500, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("ข้อมูลต้องเป็นข้อความ")
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError("ข้อความต้องไม่ว่าง")
    if len(value) > max_len:
        raise ValueError(f"ข้อความยาวเกิน {max_len} ตัวอักษร")
    return value


def clean_userid(value):
    value = clean_text(value, 128)
    if any(ch.isspace() for ch in value):
        raise ValueError("User ID ต้องไม่มีช่องว่าง")
    return value


def safe_filename(value, expected_suffix=None):
    if not isinstance(value, str):
        raise ValueError("ชื่อไฟล์ไม่ถูกต้อง")
    name = Path(value).name.strip()
    if name != value.strip() or not name or name in (".", ".."):
        raise ValueError("ชื่อไฟล์ไม่ถูกต้อง")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    normalized = "".join(ch if ch in allowed else "_" for ch in name)
    normalized = normalized[:180]
    if expected_suffix and not normalized.lower().endswith(expected_suffix):
        normalized += expected_suffix
    return normalized


def discord_notify(title, description, level="info", fields=None):
    if not DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED or not DISCORD_WEBHOOK_URL:
        return False
    colors = {"info": 3447003, "success": 5763719, "warning": 16705372, "error": 15548997}
    embed = {
        "title": str(title)[:256],
        "description": str(description)[:4000],
        "color": colors.get(level, colors["info"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"Palworld Dashboard v{APP_VERSION}"},
    }
    if fields:
        embed["fields"] = [
            {"name": str(item.get("name", ""))[:256], "value": str(item.get("value", ""))[:1024], "inline": bool(item.get("inline", False))}
            for item in fields[:25]
        ]
    payload = json.dumps({"embeds": [embed]}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(DISCORD_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15):
            return True
    except Exception as exc:
        print(f"Discord notification failed: {exc}")
        return False


def add_player_action_record(userid, name, reason, action, action_success, save_world_success=False, error=""):
    event = {
        "userid": userid,
        "name": name or "",
        "reason": reason or "",
        "action": action,
        "action_success": bool(action_success),
        "save_world_success": bool(save_world_success),
        "error": error or "",
        "at": iso_now(),
    }
    with STATE_LOCK:
        if action_success and action == "ban":
            BANS["active"][userid] = {
                "userid": userid,
                "name": name or "",
                "reason": reason or "",
                "banned_at": event["at"],
            }
        elif action_success and action == "unban":
            previous = BANS["active"].pop(userid, None)
            if previous and not event["name"]:
                event["name"] = previous.get("name", "")
        BANS["history"].append(event)
        save_bans()

    titles = {"kick": "ผู้เล่นถูก Kick", "ban": "ผู้เล่นถูกแบน", "unban": "ผู้เล่นถูกปลดแบน"}
    save_text = "สำเร็จ" if save_world_success else "ไม่สำเร็จ"
    status_text = "สำเร็จ" if action_success else "ไม่สำเร็จ"
    discord_notify(
        titles.get(action, "คำสั่งผู้เล่น"),
        f"สถานะคำสั่ง: {status_text}\nUser ID: `{userid}`\nชื่อ: {event['name'] or '-'}\nเหตุผล: {reason or '-'}\nSave World: {save_text}"
        + (f"\nข้อผิดพลาด: {error}" if error else ""),
        "success" if action_success and save_world_success else ("warning" if action_success else "error"),
    )
    return event


def perform_player_action(action, userid, name="", reason=""):
    payload = {"userid": userid}
    if action in ("kick", "ban"):
        payload["message"] = reason
    try:
        api_request(action, "POST", payload)
    except Exception as exc:
        add_player_action_record(userid, name, reason, action, False, False, str(exc))
        raise

    try:
        api_request("save", "POST")
    except Exception as exc:
        add_player_action_record(userid, name, reason, action, True, False, str(exc))
        return {
            "ok": False,
            "message": f"{action.upper()} สำเร็จ แต่ Save World ไม่สำเร็จ: {exc}",
            "save_world": False,
        }

    add_player_action_record(userid, name, reason, action, True, True)
    return {
        "ok": True,
        "message": f"{action.upper()} ผู้เล่นและ Save World เรียบร้อยแล้ว",
        "save_world": True,
    }


def config_snapshot():
    with CONFIG_LOCK:
        exists = CONFIG_FILE.is_file()
        content = ""
        modified_at = None
        size = 0
        sha256 = None
        if exists:
            raw = CONFIG_FILE.read_bytes()
            if len(raw) > MAX_CONFIG_BYTES:
                raise ValueError(f"ไฟล์ Config ใหญ่เกิน {MAX_CONFIG_BYTES / 1024:.0f} KB")
            content = raw.decode("utf-8-sig")
            stat_info = CONFIG_FILE.stat()
            size = stat_info.st_size
            modified_at = datetime.fromtimestamp(stat_info.st_mtime, LOCAL_TZ).isoformat(timespec="seconds")
            sha256 = hashlib.sha256(raw).hexdigest()
        return {
            "path": str(CONFIG_FILE),
            "exists": exists,
            "content": content,
            "size": size,
            "modified_at": modified_at,
            "sha256": sha256,
            "max_bytes": MAX_CONFIG_BYTES,
        }


def validate_config_content(content):
    if not isinstance(content, str):
        raise ValueError("Config ต้องเป็นข้อความ")
    if "\x00" in content:
        raise ValueError("Config มีอักขระ NUL ที่ไม่ถูกต้อง")
    encoded = content.encode("utf-8")
    if not encoded.strip():
        raise ValueError("Config ต้องไม่ว่าง")
    if len(encoded) > MAX_CONFIG_BYTES:
        raise ValueError(f"Config ใหญ่เกิน {MAX_CONFIG_BYTES / 1024:.0f} KB")
    if "[/Script/Pal.PalGameWorldSettings]" not in content or "OptionSettings=" not in content:
        raise ValueError("Config ต้องมี section [/Script/Pal.PalGameWorldSettings] และ OptionSettings=")
    return encoded


def save_config_content(content):
    encoded = validate_config_content(content)
    with CONFIG_LOCK:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        backup_name = None
        if CONFIG_FILE.is_file():
            timestamp = now_local().strftime("%Y%m%d-%H%M%S")
            backup_name = f"PalWorldSettings-{timestamp}-{uuid.uuid4().hex[:6]}.ini"
            shutil.copy2(CONFIG_FILE, CONFIG_BACKUP_DIR / backup_name)
            backups = sorted(CONFIG_BACKUP_DIR.glob("*.ini"), key=lambda item: item.stat().st_mtime, reverse=True)
            for old_backup in backups[MAX_CONFIG_BACKUPS:]:
                try:
                    old_backup.unlink()
                except OSError:
                    pass
        temp = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + ".dashboard.tmp")
        with temp.open("wb") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, CONFIG_FILE)
        try:
            os.chown(CONFIG_FILE, PALWORLD_PUID, PALWORLD_PGID)
        except OSError:
            pass
        snapshot = config_snapshot()
    discord_notify(
        "แก้ไข PalWorldSettings.ini",
        f"บันทึก Config แล้ว\nไฟล์: `{CONFIG_FILE}`" + (f"\nBackup: `{backup_name}`" if backup_name else ""),
        "info",
    )
    return {"backup": backup_name, **snapshot}


SETTING_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
BARE_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.:/+\-]+$")
UNQUOTED_STRING_KEYS = {"Difficulty", "RandomizerType", "DeathPenalty", "LogFormatType", "AdditionalDropItemWhenPlayerKillingInPvPMode"}


def find_option_settings_bounds(content):
    match = re.search(r"(?m)^[ \t]*OptionSettings[ \t]*=[ \t]*\(", content)
    if not match:
        raise ValueError("ไม่พบ OptionSettings=(...) ใน Config")
    opening = content.find("(", match.start(), match.end())
    depth = 0
    quote = None
    escaped = False
    for index in range(opening, len(content)):
        char = content[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return opening + 1, index
    raise ValueError("OptionSettings ปิดวงเล็บไม่ครบ")


def split_top_level(value, delimiter=","):
    parts = []
    start = 0
    depth = 0
    quote = None
    escaped = False
    for index, char in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}" and depth:
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def parse_option_settings(content):
    body_start, body_end = find_option_settings_bounds(content)
    body = content[body_start:body_end]
    ordered = []
    values = {}
    for raw_entry in split_top_level(body):
        entry = raw_entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"รูปแบบ OptionSettings ไม่ถูกต้องใกล้ค่า: {entry[:80]}")
        key, raw_value = entry.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not SETTING_KEY_PATTERN.fullmatch(key):
            raise ValueError(f"ชื่อค่า Config ไม่ถูกต้อง: {key}")
        if key in values:
            raise ValueError(f"พบชื่อค่า Config ซ้ำ: {key}")
        ordered.append(key)
        values[key] = raw_value
    return body_start, body_end, ordered, values


def quote_setting_string(value):
    return json.dumps(value, ensure_ascii=False)


def format_list_item(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Array มีตัวเลขที่ไม่ใช่ค่าปกติ")
        return format(value, ".15g")
    if isinstance(value, str):
        if BARE_VALUE_PATTERN.fullmatch(value):
            return value
        return quote_setting_string(value)
    raise ValueError("Array รองรับเฉพาะข้อความ ตัวเลข และ Boolean")


def format_setting_value(value, existing_raw=None, key=None):
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("ค่าตัวเลขต้องเป็นค่าปกติ")
        return format(value, ".15g")
    if isinstance(value, list):
        if len(value) > 500:
            raise ValueError("Array มีสมาชิกมากเกิน 500 ค่า")
        return "(" + ",".join(format_list_item(item) for item in value) + ")"
    if isinstance(value, str):
        if len(value) > 8192:
            raise ValueError("ข้อความยาวเกิน 8,192 ตัวอักษร")
        existing = (existing_raw or "").strip()
        was_quoted = len(existing) >= 2 and existing[0] == existing[-1] and existing[0] in ('"', "'")
        if existing_raw is None and key not in UNQUOTED_STRING_KEYS:
            return quote_setting_string(value)
        if was_quoted or not value or not BARE_VALUE_PATTERN.fullmatch(value):
            return quote_setting_string(value)
        return value
    raise ValueError("ชนิดข้อมูลรองรับเฉพาะ Boolean, Number, String และ Array")


def patch_config_settings(changes, expected_sha256=None):
    if not isinstance(changes, dict) or not changes:
        raise ValueError("ยังไม่มีค่าที่ต้องอัปเดต")
    if len(changes) > 300:
        raise ValueError("อัปเดตได้ไม่เกิน 300 ค่าต่อครั้ง")
    with CONFIG_LOCK:
        snapshot = config_snapshot()
        if not snapshot["exists"]:
            raise ValueError("ยังไม่พบ PalWorldSettings.ini")
        if expected_sha256 and expected_sha256 != snapshot.get("sha256"):
            raise ValueError("ไฟล์ Config ถูกแก้ไขหลังจากเปิดหน้านี้ กรุณาโหลด Config ใหม่ก่อนอัปเดต")
        content = snapshot["content"]
        body_start, body_end, ordered, current = parse_option_settings(content)
        changed = []
        for key, value in changes.items():
            if not isinstance(key, str) or not SETTING_KEY_PATTERN.fullmatch(key):
                raise ValueError(f"ชื่อค่า Config ไม่ถูกต้อง: {key}")
            old_raw = current.get(key)
            new_raw = format_setting_value(value, old_raw, key)
            if old_raw == new_raw:
                continue
            if key not in current:
                ordered.append(key)
            current[key] = new_raw
            changed.append({"key": key, "old": old_raw, "new": new_raw})
        if not changed:
            raise ValueError("ค่าที่เลือกเหมือนกับ Config ปัจจุบัน ไม่มีข้อมูลต้องเขียน")
        new_body = ",".join(f"{key}={current[key]}" for key in ordered)
        updated_content = content[:body_start] + new_body + content[body_end:]
        saved = save_config_content(updated_content)
    return {"changed": changed, "changed_count": len(changed), **saved}


def parse_schedule(value):
    if value in (None, "", "now"):
        return now_local()
    if not isinstance(value, str):
        raise ValueError("เวลาทำงานไม่ถูกต้อง")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("เวลาทำงานต้องเป็น ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    else:
        parsed = parsed.astimezone(LOCAL_TZ)
    current = now_local()
    if parsed < current - timedelta(minutes=1):
        raise ValueError("เวลาทำงานอยู่ในอดีต")
    if parsed > current + timedelta(days=365):
        raise ValueError("กำหนดเวลาล่วงหน้าได้ไม่เกิน 365 วัน")
    return parsed


def normalize_import_mode(value):
    mode = str(value or DEFAULT_IMPORT_MODE).strip().lower()
    if mode not in IMPORT_MODE_LABELS:
        raise ValueError("โหมด Import ไม่ถูกต้อง")
    return mode


def stage_payload(stage, detail=None, progress=None):
    label, default_detail, default_progress = JOB_STAGE_INFO.get(
        stage, (stage.replace("_", " "), "", 0)
    )
    return {
        "stage": stage,
        "stage_label": label,
        "stage_detail": detail if detail is not None else default_detail,
        "progress_percent": int(default_progress if progress is None else max(0, min(100, progress))),
        "stage_started_at": iso_now(),
        "updated_at": iso_now(),
    }


def decorate_job(job):
    item = dict(job)
    stage = item.get("stage", "scheduled")
    label, detail, progress = JOB_STAGE_INFO.get(stage, (stage.replace("_", " "), "", 0))
    item.setdefault("stage_label", label)
    item.setdefault("stage_detail", detail)
    item.setdefault("progress_percent", progress)
    item.setdefault("updated_at", item.get("created_at"))
    started_at = item.get("started_at")
    finished_at = item.get("finished_at")
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            if started.tzinfo is None:
                started = started.replace(tzinfo=LOCAL_TZ)
            end = datetime.fromisoformat(finished_at) if finished_at else now_local()
            if end.tzinfo is None:
                end = end.replace(tzinfo=LOCAL_TZ)
            item["elapsed_seconds"] = max(0, int((end.astimezone(LOCAL_TZ) - started.astimezone(LOCAL_TZ)).total_seconds()))
        except Exception:
            item["elapsed_seconds"] = None
    else:
        item["elapsed_seconds"] = 0
    return item


def create_job(job_type, schedule_at, warning_seconds, message, source_file=None, import_mode=None, archive_summary=None):
    if job_type not in ("export", "import", "restart"):
        raise ValueError("ประเภทงานไม่ถูกต้อง")
    if not isinstance(warning_seconds, int) or not 0 <= warning_seconds <= 3600:
        raise ValueError("เวลาประกาศเตือนต้องเป็นจำนวนเต็ม 0-3600 วินาที")
    schedule = parse_schedule(schedule_at)
    job = {
        "id": uuid.uuid4().hex[:12],
        "type": job_type,
        "status": "pending",
        **stage_payload("scheduled"),
        "scheduled_at": schedule.isoformat(timespec="seconds"),
        "warning_seconds": warning_seconds,
        "message": clean_text(message or "Server maintenance", 500),
        "source_file": source_file,
        "import_mode": normalize_import_mode(import_mode) if job_type == "import" else None,
        "output_file": None,
        "safety_backup": None,
        "created_at": iso_now(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "archive_summary": archive_summary if isinstance(archive_summary, dict) else None,
    }
    with STATE_LOCK:
        pending = [item for item in STATE["jobs"] if item.get("status") in ("pending", "running")]
        if len(pending) >= 20:
            raise ValueError("มีงานรอหรือกำลังทำมากเกินไป")
        STATE["jobs"].append(job)
        STATE["jobs"] = STATE["jobs"][-500:]
        save_state()
    discord_notify(
        "ตั้งคิว Export" if job_type == "export" else ("ตั้งคิว Import" if job_type == "import" else "ตั้งคิว Restart"),
        f"งาน `{job['id']}`\nเวลาทำงาน: {job['scheduled_at']}\nเวลาเตือน: {warning_seconds} วินาที"
        + (f"\nไฟล์: `{source_file}`" if source_file else "")
        + (f"\nโหมด: {IMPORT_MODE_LABELS[job['import_mode']]}" if job_type == "import" else ""),
        "info",
    )
    SCHEDULER_WAKE.set()
    return job


def update_job(job_id, **changes):
    with STATE_LOCK:
        for job in STATE["jobs"]:
            if job.get("id") == job_id:
                if "stage" in changes and changes["stage"] != job.get("stage"):
                    stage = changes["stage"]
                    label, detail, progress = JOB_STAGE_INFO.get(stage, (stage.replace("_", " "), "", 0))
                    changes.setdefault("stage_label", label)
                    changes.setdefault("stage_detail", detail)
                    changes.setdefault("progress_percent", progress)
                    changes.setdefault("stage_started_at", iso_now())
                changes.setdefault("updated_at", iso_now())
                job.update(changes)
                STATE["last_job_id"] = job_id
                save_state()
                return decorate_job(job)
    raise KeyError(job_id)


def set_job_stage(job_id, stage, detail=None, progress=None):
    changes = stage_payload(stage, detail=detail, progress=progress)
    return update_job(job_id, **changes)


def get_job(job_id):
    with STATE_LOCK:
        for job in STATE["jobs"]:
            if job.get("id") == job_id:
                return decorate_job(job)
    return None


def job_snapshot(limit=100):
    with STATE_LOCK:
        return [decorate_job(item) for item in reversed(STATE["jobs"][-limit:])]


def active_job_snapshot():
    with STATE_LOCK:
        running = [decorate_job(item) for item in STATE["jobs"] if item.get("status") == "running"]
        if running:
            return running[0]
        pending = sorted(
            [decorate_job(item) for item in STATE["jobs"] if item.get("status") == "pending"],
            key=lambda item: item.get("scheduled_at", ""),
        )
        return pending[0] if pending else None


def set_maintenance_marker(job, stage):
    atomic_json_write(
        MAINTENANCE_FILE,
        {"job_id": job["id"], "type": job["type"], "stage": stage, "updated_at": iso_now()},
    )


def clear_maintenance_marker():
    try:
        MAINTENANCE_FILE.unlink()
    except FileNotFoundError:
        pass


def mark_job_stage(job, stage, detail=None, progress=None):
    set_job_stage(job["id"], stage, detail=detail, progress=progress)
    set_maintenance_marker(job, stage)


def chown_tree(root):
    if RUNTIME_MODE == "external":
        return
    try:
        os.chown(root, PALWORLD_PUID, PALWORLD_PGID)
    except OSError:
        pass
    for current, dirs, files in os.walk(root):
        for name in dirs:
            try:
                os.chown(Path(current) / name, PALWORLD_PUID, PALWORLD_PGID)
            except OSError:
                pass
        for name in files:
            try:
                os.chown(Path(current) / name, PALWORLD_PUID, PALWORLD_PGID)
            except OSError:
                pass


def create_export_archive(prefix="palworld-export", job_id=None):
    if not SAVED_DIR.is_dir():
        raise RuntimeError(f"ไม่พบโฟลเดอร์ข้อมูลเซฟ: {SAVED_DIR}")
    timestamp = now_local().strftime("%Y%m%d-%H%M%S")
    suffix = job_id or uuid.uuid4().hex[:8]
    filename = f"{prefix}-{timestamp}-{suffix}.zip"
    target = EXPORT_DIR / filename
    temp_target = target.with_suffix(".zip.part")
    manifest = {
        "format": "palworld-dashboard-export",
        "format_version": 1,
        "dashboard_version": APP_VERSION,
        "created_at": iso_now(),
        "timezone": TIMEZONE_NAME,
        "source_path": "Pal/Saved",
        "runtime_mode": RUNTIME_MODE,
        "runtime_label": RUNTIME_LABEL,
        "config_platform": TARGET_CONFIG_PLATFORM,
        "included_paths": ["Pal/Saved"],
        "recommended_import_mode": DEFAULT_IMPORT_MODE,
        "job_id": job_id,
    }
    try:
        try:
            info = api_request("info", timeout=5)
            manifest["server"] = info
        except Exception:
            manifest["server"] = None
        with zipfile.ZipFile(temp_target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            archive.writestr("dashboard-export-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for current, dirs, files in os.walk(SAVED_DIR):
                current_path = Path(current)
                dirs[:] = [name for name in dirs if not (current_path / name).is_symlink()]
                for name in files:
                    source = current_path / name
                    if source.is_symlink() or not source.is_file():
                        continue
                    relative = source.relative_to(PALWORLD_DATA_DIR).as_posix()
                    archive.write(source, relative)
        os.replace(temp_target, target)
        return target
    except Exception:
        try:
            temp_target.unlink()
        except FileNotFoundError:
            pass
        raise


def parse_dedicated_server_name(text):
    if not isinstance(text, str):
        return None
    match = DEDICATED_SERVER_NAME_RE.search(text)
    return match.group(1).upper() if match else None


def inspect_archive_worlds(path):
    world_ids = set()
    config_world_ids = {}
    player_counts = {}
    with zipfile.ZipFile(path, "r", allowZip64=True) as archive:
        for item in archive.infolist():
            raw_name = item.filename.replace("\\", "/")
            level_match = re.match(r"^Pal/Saved/SaveGames/0/([A-Fa-f0-9]{32})/Level\.sav$", raw_name)
            if level_match and not item.is_dir():
                world_ids.add(level_match.group(1).upper())
            player_match = re.match(r"^Pal/Saved/SaveGames/0/([A-Fa-f0-9]{32})/Players/[^/]+\.sav$", raw_name)
            if player_match and not item.is_dir():
                world_id = player_match.group(1).upper()
                player_counts[world_id] = player_counts.get(world_id, 0) + 1
            config_match = re.match(
                r"^Pal/Saved/Config/(WindowsServer|LinuxServer)/GameUserSettings\.ini$",
                raw_name,
            )
            if config_match and not item.is_dir() and item.file_size <= 4 * 1024 * 1024:
                try:
                    text = archive.read(item).decode("utf-8-sig", errors="replace")
                    world_id = parse_dedicated_server_name(text)
                    if world_id:
                        config_world_ids[config_match.group(1)] = world_id
                except OSError:
                    pass
    return {
        "world_ids": sorted(world_ids),
        "config_world_ids": config_world_ids,
        "player_counts": player_counts,
    }


def game_user_settings_path():
    return SAVED_DIR / "Config" / TARGET_CONFIG_PLATFORM / "GameUserSettings.ini"


def read_active_world_id(path=None):
    target = Path(path) if path is not None else game_user_settings_path()
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    return parse_dedicated_server_name(text)


def write_active_world_id(world_id, path=None):
    world_id = str(world_id or "").strip().upper()
    if not WORLD_ID_RE.fullmatch(world_id):
        raise ValueError(f"World ID ไม่ถูกต้อง: {world_id or '-'}")
    target = Path(path) if path is not None else game_user_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = b""
    try:
        raw = target.read_bytes()
    except FileNotFoundError:
        pass
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace") if raw else ""
    newline = "\r\n" if "\r\n" in text else "\n"
    replacement = f"DedicatedServerName={world_id}"
    if DEDICATED_SERVER_NAME_RE.search(text):
        text = DEDICATED_SERVER_NAME_RE.sub(replacement, text, count=1)
    else:
        section = "[/Script/Pal.PalGameLocalSettings]"
        section_match = re.search(r"(?mi)^\s*\[/Script/Pal\.PalGameLocalSettings\]\s*$", text)
        if section_match:
            insert_at = section_match.end()
            text = text[:insert_at] + newline + replacement + text[insert_at:]
        else:
            prefix = section + newline + replacement + newline
            text = prefix + (newline + text if text else "")
    if text and not text.endswith(("\n", "\r")):
        text += newline
    temp = target.with_suffix(target.suffix + ".dashboard.tmp")
    encoding = "utf-8-sig" if had_bom else "utf-8"
    with temp.open("w", encoding=encoding, newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, target)
    return world_id


def restore_world_selection_backup(backup_path, missing_marker):
    target = game_user_settings_path()
    backup_path = Path(backup_path)
    missing_marker = Path(missing_marker)
    if backup_path.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)
        backup_path.unlink()
        try:
            missing_marker.unlink()
        except FileNotFoundError:
            pass
        return "คืน DedicatedServerName เดิมสำเร็จ"
    if missing_marker.exists():
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        missing_marker.unlink()
        return "ลบ GameUserSettings.ini ที่ถูกสร้างระหว่าง Import สำเร็จ"
    return "ไม่มี Backup ของ DedicatedServerName ที่ต้องคืน"


def validate_import_archive(path, import_mode=None):
    if not path.is_file():
        raise ValueError("ไม่พบไฟล์ Import")
    mode = normalize_import_mode(import_mode) if import_mode is not None else None
    total_size = 0
    file_count = 0
    has_saved_content = False
    has_savegames = False
    config_platforms = set()
    manifest = None
    with zipfile.ZipFile(path, "r", allowZip64=True) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP เสียหายที่ไฟล์: {bad}")
        for item in archive.infolist():
            file_count += 1
            if file_count > MAX_ARCHIVE_FILES:
                raise ValueError(f"ZIP มีจำนวนไฟล์เกิน {MAX_ARCHIVE_FILES:,} ไฟล์")
            raw_name = item.filename.replace("\\", "/")
            pure = PurePosixPath(raw_name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"พบ path ที่ไม่ปลอดภัยใน ZIP: {raw_name}")
            mode_bits = (item.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode_bits):
                raise ValueError(f"ไม่อนุญาต symlink ใน ZIP: {raw_name}")
            if raw_name == "dashboard-export-manifest.json":
                if item.file_size <= 1024 * 1024:
                    try:
                        parsed = json.loads(archive.read(item).decode("utf-8"))
                        manifest = parsed if isinstance(parsed, dict) else None
                    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
                        manifest = None
                continue
            if not raw_name.startswith("Pal/Saved/"):
                raise ValueError(f"ZIP ต้องมีเฉพาะ dashboard-export-manifest.json และ Pal/Saved/: {raw_name}")
            if raw_name.startswith("Pal/Saved/SaveGames/") and not item.is_dir():
                has_savegames = True
            config_match = re.match(r"^Pal/Saved/Config/(WindowsServer|LinuxServer)/", raw_name)
            if config_match and not item.is_dir():
                config_platforms.add(config_match.group(1))
            if not item.is_dir():
                has_saved_content = True
                total_size += item.file_size
                if total_size > MAX_EXPANDED_BYTES:
                    raise ValueError(f"ขนาดหลังแตก ZIP เกิน {MAX_EXPANDED_BYTES / 1024 / 1024:.0f} MB")
    if not has_saved_content:
        raise ValueError("ZIP ไม่มีข้อมูลภายใต้ Pal/Saved/")

    config_platforms_sorted = sorted(config_platforms)
    target_config_available = TARGET_CONFIG_PLATFORM in config_platforms
    source_runtime = str((manifest or {}).get("runtime_mode") or "unknown")
    source_config_platform = str((manifest or {}).get("config_platform") or "")
    if not source_config_platform and len(config_platforms) == 1:
        source_config_platform = config_platforms_sorted[0]
    source_platform_conflict = bool(source_config_platform) and source_config_platform != TARGET_CONFIG_PLATFORM
    cross_platform = source_platform_conflict or (bool(config_platforms) and not target_config_available)
    full_restore_safe = target_config_available and not source_platform_conflict

    world_info = inspect_archive_worlds(path)
    world_ids = world_info["world_ids"]
    config_world_ids = world_info["config_world_ids"]
    source_world_id = config_world_ids.get(source_config_platform) if source_config_platform else None
    selected_world_id = source_world_id if source_world_id in world_ids else None
    world_selection_source = "source_game_user_settings" if selected_world_id else None
    if not selected_world_id and len(world_ids) == 1:
        selected_world_id = world_ids[0]
        world_selection_source = "single_world_in_archive"
    selected_player_count = world_info["player_counts"].get(selected_world_id, 0) if selected_world_id else 0

    supported_modes = []
    if has_savegames and selected_world_id:
        supported_modes.append("world_only")
    # Full restore is safe only when the archive contains the target platform config.
    # Otherwise PalServer may start without REST/RCON/Admin settings and the job will wait until timeout.
    if full_restore_safe:
        supported_modes.append("full_restore")
    if target_config_available:
        supported_modes.append("config_only")

    if mode == "world_only" and not has_savegames:
        raise ValueError("ZIP ไม่มี Pal/Saved/SaveGames สำหรับโหมดสลับ World/ผู้เล่น")
    if mode == "world_only" and not selected_world_id:
        if len(world_ids) > 1:
            raise ValueError(
                "ZIP มีหลาย World แต่ระบุ World ที่เปิดใช้งานไม่ได้: "
                + ", ".join(world_ids)
                + ". ต้องมี DedicatedServerName ใน GameUserSettings.ini ที่ตรงกับโฟลเดอร์ World"
            )
        raise ValueError("ZIP ไม่มี World ที่สมบูรณ์: ต้องพบ SaveGames/0/<WorldID>/Level.sav")
    if mode == "config_only" and not target_config_available:
        available = ", ".join(config_platforms_sorted) or "ไม่มี"
        raise ValueError(
            f"ZIP ไม่มี Config/{TARGET_CONFIG_PLATFORM} สำหรับระบบปลายทางนี้ (พบ: {available})"
        )
    if mode == "full_restore" and not full_restore_safe:
        available = ", ".join(config_platforms_sorted) or "ไม่มี Config ของ Server"
        recommendation = "เลือก 'สลับ/ย้าย World และผู้เล่น' เพื่อย้าย Save โดยเก็บ Config ของปลายทางไว้"
        raise ValueError(
            "ไม่อนุญาต Full Restore ข้ามระบบหรือ ZIP ที่ไม่มี Config ของปลายทาง: "
            f"ปลายทางใช้ Config/{TARGET_CONFIG_PLATFORM} แต่ ZIP พบ {available}. {recommendation}"
        )

    warning = None
    if cross_platform:
        warning = (
            f"ZIP มาจาก Config/{source_config_platform or config_platforms_sorted[0]} แต่ปลายทางใช้ "
            f"Config/{TARGET_CONFIG_PLATFORM}; ใช้โหมด World/ผู้เล่นเท่านั้น"
        )
    return {
        "files": file_count,
        "expanded_bytes": total_size,
        "has_savegames": has_savegames,
        "world_ids": world_ids,
        "selected_world_id": selected_world_id,
        "world_selection_source": world_selection_source,
        "selected_world_player_files": selected_player_count,
        "config_world_ids": config_world_ids,
        "config_platforms": config_platforms_sorted,
        "source_runtime": source_runtime,
        "source_config_platform": source_config_platform or None,
        "target_config_platform": TARGET_CONFIG_PLATFORM,
        "target_config_available": target_config_available,
        "full_restore_safe": full_restore_safe,
        "cross_platform": cross_platform,
        "supported_import_modes": supported_modes,
        "recommended_import_mode": "world_only" if has_savegames else ("full_restore" if target_config_available else None),
        "warning": warning,
        "manifest": manifest,
    }

def import_target_for_mode(extracted_saved, import_mode):
    mode = normalize_import_mode(import_mode)
    if mode == "world_only":
        source = extracted_saved / "SaveGames"
        target = SAVED_DIR / "SaveGames"
    elif mode == "config_only":
        source = extracted_saved / "Config" / TARGET_CONFIG_PLATFORM
        target = SAVED_DIR / "Config" / TARGET_CONFIG_PLATFORM
    else:
        source = extracted_saved
        target = SAVED_DIR
    if not source.is_dir():
        raise RuntimeError(f"ไฟล์ Import ไม่มีข้อมูลที่ต้องใช้สำหรับโหมด {IMPORT_MODE_LABELS[mode]}: {source}")
    return mode, source, target


def extract_import_archive(path, destination):
    validate_import_archive(path)
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(path, "r", allowZip64=True) as archive:
        for item in archive.infolist():
            raw_name = item.filename.replace("\\", "/")
            if raw_name == "dashboard-export-manifest.json":
                continue
            pure = PurePosixPath(raw_name)
            target = destination.joinpath(*pure.parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    extracted_saved = destination / "Pal" / "Saved"
    if not extracted_saved.is_dir():
        raise RuntimeError("แตก ZIP แล้วไม่พบ Pal/Saved")
    return extracted_saved


def announce_and_wait(job):
    warning = int(job.get("warning_seconds", 0))
    message = job.get("message") or "Server maintenance"
    try:
        api_request("announce", "POST", {"message": message})
    except Exception as exc:
        print(f"Server announcement failed: {exc}")
    discord_notify(
        "เริ่มช่วง Maintenance",
        f"งาน `{job['id']}` ({job['type']})\nประกาศ: {message}\nเซิร์ฟเวอร์จะปิดใน {warning} วินาที",
        "warning",
    )
    if warning > 0:
        time.sleep(warning)
    try:
        api_request("save", "POST")
    except Exception as exc:
        print(f"Save before maintenance failed; graceful runtime stop will still be attempted: {exc}")


def run_export_job(job):
    mark_job_stage(job, "announcing")
    announce_and_wait(job)
    mark_job_stage(job, "stopping_server")
    stop_container()
    discord_notify("เซิร์ฟเวอร์ปิดชั่วคราว", f"งาน `{job['id']}` กำลัง Export ข้อมูล", "warning")
    mark_job_stage(job, "creating_archive")
    output = create_export_archive("palworld-export", job["id"])
    discord_notify(
        "สร้างไฟล์ Export แล้ว",
        f"งาน `{job['id']}`\nไฟล์: `{output.name}`\nกำลังเปิดเซิร์ฟเวอร์กลับ",
        "info",
    )
    update_job(job["id"], output_file=output.name)
    mark_job_stage(job, "starting_server")
    start_container()
    wait_for_server_ready(
        job_id=job["id"],
        stage="waiting_rest_api",
        context="Export เสร็จแล้วและสั่งเปิด Server กลับ กำลังรอ REST API",
    )
    size = output.stat().st_size
    discord_notify(
        "Export เสร็จและเปิดเซิร์ฟเวอร์แล้ว",
        f"งาน `{job['id']}`\nไฟล์: `{output.name}`\nขนาด: {size / 1024 / 1024:.2f} MB",
        "success",
    )


def run_import_job(job):
    source_name = safe_filename(job.get("source_file", ""), ".zip")
    source = IMPORT_DIR / source_name
    import_mode = normalize_import_mode(job.get("import_mode"))

    mark_job_stage(job, "validating_archive")
    archive_details = validate_import_archive(source, import_mode)
    update_job(job["id"], archive_summary={
        "source_config_platform": archive_details.get("source_config_platform"),
        "target_config_platform": archive_details.get("target_config_platform"),
        "supported_import_modes": archive_details.get("supported_import_modes"),
        "cross_platform": archive_details.get("cross_platform"),
        "warning": archive_details.get("warning"),
        "selected_world_id": archive_details.get("selected_world_id"),
        "selected_world_player_files": archive_details.get("selected_world_player_files"),
    })
    imported_world_id = archive_details.get("selected_world_id") if import_mode == "world_only" else None
    mode_label = IMPORT_MODE_LABELS[import_mode]

    mark_job_stage(job, "announcing")
    announce_and_wait(job)
    mark_job_stage(job, "stopping_server")
    stop_container()
    discord_notify(
        "เซิร์ฟเวอร์ปิดชั่วคราว",
        f"งาน `{job['id']}` กำลัง Import `{source.name}`\nโหมด: {mode_label}",
        "warning",
    )

    mark_job_stage(job, "safety_backup")
    safety_backup = create_export_archive("pre-import", job["id"])
    update_job(job["id"], safety_backup=safety_backup.name)
    discord_notify(
        "สร้าง Safety Backup แล้ว",
        f"งาน `{job['id']}`\nไฟล์: `{safety_backup.name}`\nกำลังนำเข้าด้วยโหมด: {mode_label}",
        "info",
    )

    staging_root = STAGING_DIR / f"import-{job['id']}"
    rollback_target = PALWORLD_DATA_DIR / f".dashboard-rollback-{import_mode}-{job['id']}"
    failed_target = PALWORLD_DATA_DIR / f".dashboard-failed-import-{import_mode}-{job['id']}"
    world_config_backup = PALWORLD_DATA_DIR / f".dashboard-rollback-world-config-{job['id']}.ini"
    world_config_missing = PALWORLD_DATA_DIR / f".dashboard-rollback-world-config-{job['id']}.missing"
    imported = False
    old_moved = False
    target = None
    if staging_root.exists():
        shutil.rmtree(staging_root)
    for temporary in (rollback_target, failed_target):
        if temporary.exists():
            shutil.rmtree(temporary)
    for temporary_file in (world_config_backup, world_config_missing):
        try:
            temporary_file.unlink()
        except FileNotFoundError:
            pass
    try:
        mark_job_stage(job, "extracting")
        extracted_saved = extract_import_archive(source, staging_root)
        import_mode, extracted_target, target = import_target_for_mode(extracted_saved, import_mode)

        stage = {
            "world_only": "replacing_savegames",
            "config_only": "replacing_target_config",
            "full_restore": "replacing_saved_data",
        }[import_mode]
        mark_job_stage(job, stage)
        if target.exists():
            os.replace(target, rollback_target)
            old_moved = True
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(extracted_target, target)
        imported = True
        chown_tree(target)
        if import_mode == "world_only":
            if not imported_world_id:
                raise RuntimeError("ระบุ World ID จาก ZIP ไม่ได้ จึงไม่สามารถเลือก World หลัง Import")
            mark_job_stage(
                job,
                "updating_world_selection",
                detail=f"กำลังตั้ง DedicatedServerName={imported_world_id} สำหรับ Config/{TARGET_CONFIG_PLATFORM}",
            )
            settings_file = game_user_settings_path()
            previous_world_id = read_active_world_id(settings_file)
            if settings_file.is_file():
                shutil.copy2(settings_file, world_config_backup)
            else:
                world_config_missing.touch()
            write_active_world_id(imported_world_id, settings_file)
            update_job(
                job["id"],
                imported_world_id=imported_world_id,
                previous_world_id=previous_world_id,
                active_world_config=str(settings_file),
            )
        discord_notify(
            "แทนที่ข้อมูล Import แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{source.name}`\nโหมด: {mode_label}\nกำลังเปิดเซิร์ฟเวอร์เพื่อตรวจสอบ",
            "info",
        )

        mark_job_stage(job, "starting_server")
        start_container()
        wait_for_server_ready(
            job_id=job["id"],
            stage="waiting_rest_api",
            context=f"Import {mode_label} เสร็จแล้วและสั่งเปิด Server ใหม่",
        )
        if import_mode == "world_only":
            mark_job_stage(
                job,
                "verifying_imported_world",
                detail=f"กำลังตรวจว่า DedicatedServerName และ World folder ตรงกับ {imported_world_id}",
            )
            active_world_id = read_active_world_id()
            level_file = SAVED_DIR / "SaveGames" / "0" / imported_world_id / "Level.sav"
            if active_world_id != imported_world_id:
                raise RuntimeError(
                    f"Server เปิดผิด World: ต้องเป็น {imported_world_id} แต่ GameUserSettings.ini เป็น {active_world_id or 'ว่าง'}"
                )
            if not level_file.is_file():
                raise RuntimeError(f"ไม่พบ Level.sav ของ World ที่นำเข้า: {level_file}")
            update_job(
                job["id"],
                active_world_id=active_world_id,
                imported_world_verified=True,
                completion_detail=(
                    f"Import สำเร็จ Server เปิด World {active_world_id} และพร้อมใช้งาน "
                    f"(พบ Player save {archive_details.get('selected_world_player_files', 0)} ไฟล์)"
                ),
            )

        if rollback_target.exists():
            shutil.rmtree(rollback_target)
        for temporary_file in (world_config_backup, world_config_missing):
            try:
                temporary_file.unlink()
            except FileNotFoundError:
                pass
        if staging_root.exists():
            shutil.rmtree(staging_root)
        discord_notify(
            "Import เสร็จและเปิดเซิร์ฟเวอร์แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{source.name}`\nโหมด: {mode_label}\nSafety backup: `{safety_backup.name}`",
            "success",
        )
    except Exception as import_exc:
        rollback_messages = []
        rollback_safe = True
        try:
            mark_job_stage(job, "rollback_stopping_server", detail=f"Import ล้มเหลว: {import_exc}")
            stop_container()
        except Exception as stop_exc:
            rollback_safe = False
            rollback_messages.append(f"หยุด Server ก่อน Rollback ไม่สำเร็จ จึงไม่ย้ายไฟล์ขณะ Runtime อาจยังทำงาน: {stop_exc}")

        if rollback_safe:
            try:
                mark_job_stage(job, "rollback_restoring")
                if imported and target is not None and target.exists():
                    os.replace(target, failed_target)
                    update_job(job["id"], failed_import_path=str(failed_target))
                if old_moved and rollback_target.exists() and target is not None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(rollback_target, target)
                    chown_tree(target)
                    rollback_messages.append("คืนข้อมูลเดิมสำเร็จ")
                elif old_moved:
                    rollback_messages.append("ไม่พบข้อมูล Rollback ที่ควรมี")
                else:
                    rollback_messages.append("ไม่มีข้อมูลเดิมที่ต้องย้ายกลับ")
                if import_mode == "world_only":
                    rollback_messages.append(restore_world_selection_backup(world_config_backup, world_config_missing))
            except Exception as rollback_exc:
                rollback_messages.append(f"คืนข้อมูลเดิมไม่สำเร็จ: {rollback_exc}")

            try:
                mark_job_stage(job, "rollback_starting_server")
                start_container()
                wait_for_server_ready(
                    timeout_seconds=min(START_TIMEOUT_SECONDS, 600),
                    job_id=job["id"],
                    stage="rollback_waiting_rest_api",
                    context="คืนข้อมูลเดิมแล้วและกำลังเปิด Server กลับ",
                )
                rollback_messages.append("เปิด Server เดิมกลับและ REST API พร้อมแล้ว")
            except Exception as restart_exc:
                rollback_messages.append(f"เปิด Server หลัง Rollback ไม่สำเร็จ: {restart_exc}")

        recovery_result = "; ".join(rollback_messages)
        update_job(job["id"], recovery_completed=True, recovery_result=recovery_result)
        raise RuntimeError(
            f"Import ไม่สำเร็จ: {import_exc}. ผลการกู้คืน: {recovery_result}"
        ) from import_exc
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)


def run_restart_job(job):
    mark_job_stage(job, "announcing")
    announce_and_wait(job)
    mark_job_stage(job, "stopping_server")
    stop_container()
    discord_notify("เซิร์ฟเวอร์ปิดชั่วคราว", f"งาน `{job['id']}` กำลัง Restart หลังแก้ Config", "warning")
    mark_job_stage(job, "starting_server")
    start_container()
    wait_for_server_ready(
        job_id=job["id"],
        stage="waiting_rest_api",
        context="Restart แล้ว กำลังรอ REST API",
    )
    discord_notify(
        "Restart เสร็จและเปิดเซิร์ฟเวอร์แล้ว",
        f"งาน `{job['id']}`\nConfig: `{CONFIG_FILE.name}`",
        "success",
    )

def run_job(job):
    with MAINTENANCE_LOCK:
        initial = stage_payload("starting")
        update_job(
            job["id"],
            status="running",
            started_at=iso_now(),
            error=None,
            **initial,
        )
        current = get_job(job["id"])
        try:
            if current["type"] == "export":
                run_export_job(current)
            elif current["type"] == "import":
                run_import_job(current)
            else:
                run_restart_job(current)
            finished_job = get_job(job["id"]) or {}
            completed = stage_payload("completed", detail=finished_job.get("completion_detail"))
            update_job(job["id"], status="completed", finished_at=iso_now(), **completed)
            clear_maintenance_marker()
        except Exception as exc:
            message = str(exc)
            print(f"Maintenance job {job['id']} failed: {message}")
            recovery = ""
            current_failure = get_job(job["id"]) or {}
            if current_failure.get("recovery_completed"):
                recovery = current_failure.get("recovery_result") or "Import workflow จัดการ Rollback แล้ว"
            else:
                try:
                    status = container_status()
                    if not status.get("running"):
                        mark_job_stage(
                            job,
                            "rollback_starting_server",
                            detail="งานล้มเหลวและ Server ยังปิดอยู่ กำลังเปิด Runtime กลับอัตโนมัติ",
                        )
                        start_container()
                        wait_for_server_ready(
                            timeout_seconds=min(START_TIMEOUT_SECONDS, 600),
                            job_id=job["id"],
                            stage="rollback_waiting_rest_api",
                            context="กำลังเปิด Server กลับหลังงานล้มเหลว",
                        )
                        recovery = "ระบบเปิดเซิร์ฟเวอร์กลับและ REST API พร้อมแล้ว"
                    else:
                        recovery = "Palworld runtime ยังทำงานอยู่"
                except Exception as recovery_exc:
                    recovery = f"เปิดเซิร์ฟเวอร์กลับอัตโนมัติไม่สำเร็จ: {recovery_exc}"
            failed = stage_payload("failed", detail=f"{message} | การกู้คืน: {recovery}", progress=100)
            update_job(
                job["id"],
                status="failed",
                finished_at=iso_now(),
                error=f"{message} การกู้คืน: {recovery}",
                **failed,
            )
            set_maintenance_marker(job, "failed")
            discord_notify(
                "Maintenance ล้มเหลว",
                f"งาน `{job['id']}`\nข้อผิดพลาด: {message}\nการกู้คืน: {recovery}",
                "error",
            )

def recover_interrupted_job(job):
    messages = ["Dashboard ถูกรีสตาร์ตระหว่างทำงาน"]
    if job.get("type") == "import":
        import_mode = normalize_import_mode(job.get("import_mode"))
        if import_mode == "world_only":
            target = SAVED_DIR / "SaveGames"
        elif import_mode == "config_only":
            target = SAVED_DIR / "Config" / TARGET_CONFIG_PLATFORM
        else:
            target = SAVED_DIR
        rollback_target = PALWORLD_DATA_DIR / f".dashboard-rollback-{import_mode}-{job['id']}"
        world_config_backup = PALWORLD_DATA_DIR / f".dashboard-rollback-world-config-{job['id']}.ini"
        world_config_missing = PALWORLD_DATA_DIR / f".dashboard-rollback-world-config-{job['id']}.missing"
        recovery_files_exist = rollback_target.exists() or world_config_backup.exists() or world_config_missing.exists()
        if recovery_files_exist:
            try:
                stop_container()
            except Exception as exc:
                messages.append(f"หยุด Runtime ก่อน Startup recovery ไม่สำเร็จ จึงไม่ย้ายไฟล์: {exc}")
                return "; ".join(messages)
            try:
                failed_target = PALWORLD_DATA_DIR / (
                    f".dashboard-interrupted-import-{import_mode}-{job['id']}-{now_local().strftime('%Y%m%d-%H%M%S')}"
                )
                if target.exists():
                    os.replace(target, failed_target)
                    messages.append(f"เก็บข้อมูล Import ที่ค้างไว้ที่ {failed_target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if rollback_target.exists():
                    os.replace(rollback_target, target)
                    chown_tree(target)
                    messages.append("คืนข้อมูลก่อน Import จาก Rollback สำเร็จ")
                if import_mode == "world_only":
                    messages.append(restore_world_selection_backup(world_config_backup, world_config_missing))
            except Exception as exc:
                messages.append(f"คืนข้อมูล Rollback ไม่สำเร็จ: {exc}")
        else:
            messages.append("ไม่พบ Rollback directory; งานอาจหยุดก่อนเริ่มแทนที่ข้อมูล")

    try:
        status = container_status()
        if not status.get("running"):
            start_container()
        wait_for_server_ready(timeout_seconds=min(START_TIMEOUT_SECONDS, 600))
        messages.append("Server เปิดกลับและ REST API พร้อมแล้ว")
    except Exception as exc:
        messages.append(f"เปิด Server กลับไม่สำเร็จ: {exc}")
    return "; ".join(messages)


def scheduler_loop():
    time.sleep(3)
    with STATE_LOCK:
        interrupted_jobs = [decorate_job(job) for job in STATE["jobs"] if job.get("status") == "running"]
    for interrupted_job in interrupted_jobs:
        recovery = recover_interrupted_job(interrupted_job)
        failed = stage_payload("interrupted", detail=recovery, progress=100)
        update_job(
            interrupted_job["id"],
            status="failed",
            finished_at=iso_now(),
            error=recovery,
            **failed,
        )
        set_maintenance_marker(interrupted_job, "interrupted")
        print(f"Interrupted job {interrupted_job['id']} recovery: {recovery}")
    while True:
        due = None
        with STATE_LOCK:
            running = any(job.get("status") == "running" for job in STATE["jobs"])
            if not running:
                pending = sorted(
                    [job for job in STATE["jobs"] if job.get("status") == "pending"],
                    key=lambda item: item.get("scheduled_at", ""),
                )
                if pending:
                    try:
                        scheduled = datetime.fromisoformat(pending[0]["scheduled_at"])
                        if scheduled.tzinfo is None:
                            scheduled = scheduled.replace(tzinfo=LOCAL_TZ)
                        if scheduled <= now_local():
                            due = dict(pending[0])
                    except Exception:
                        pending[0]["status"] = "failed"
                        pending[0]["error"] = "scheduled_at ไม่ถูกต้อง"
                        pending[0]["finished_at"] = iso_now()
                        save_state()
        if due:
            run_job(due)
            continue
        SCHEDULER_WAKE.wait(timeout=2)
        SCHEDULER_WAKE.clear()


def list_files(directory):
    items = []
    for path in directory.glob("*.zip"):
        try:
            info = path.stat()
        except OSError:
            continue
        items.append({
            "name": path.name,
            "size": info.st_size,
            "modified_at": datetime.fromtimestamp(info.st_mtime, LOCAL_TZ).isoformat(timespec="seconds"),
        })
    return sorted(items, key=lambda item: item["modified_at"], reverse=True)


def api_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            detail = ""
        return 502, f"Palworld REST API ตอบกลับ HTTP {exc.code}" + (f": {detail}" if detail else "")
    if isinstance(exc, urllib.error.URLError):
        return 502, f"เชื่อมต่อบริการภายนอกไม่ได้: {exc.reason}"
    if isinstance(exc, (ValueError, KeyError, zipfile.BadZipFile)):
        return 400, str(exc)
    return 500, str(exc)


class Handler(BaseHTTPRequestHandler):
    server_version = f"PalworldDashboard/{APP_VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.client_address[0]} {fmt % args}")

    def authenticated(self):
        if not DASHBOARD_PASSWORD:
            return True
        expected = "Basic " + base64.b64encode(f"{DASHBOARD_USERNAME}:{DASHBOARD_PASSWORD}".encode()).decode()
        return self.headers.get("Authorization", "") == expected

    def require_auth(self):
        if self.authenticated():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Palworld Dashboard"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def same_origin(self):
        origin = self.headers.get("Origin", "").strip()
        if not origin:
            return True
        parsed = urllib.parse.urlparse(origin)
        return parsed.scheme in ("http", "https") and parsed.netloc == self.headers.get("Host", "")

    def common_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")

    def send_bytes(self, code, data, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.common_headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, payload):
        self.send_bytes(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def send_file(self, path, download_name):
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.common_headers()
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with path.open("rb") as fh:
            shutil.copyfileobj(fh, self.wfile, length=1024 * 1024)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length ไม่ถูกต้อง") from exc
        if length < 0 or length > MAX_JSON_BODY:
            raise ValueError("Request body ใหญ่เกินไป")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON ไม่ถูกต้อง") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON ต้องเป็น object")
        return value

    def handle_upload(self, query):
        raw_name = (query.get("filename") or [""])[0]
        filename = safe_filename(raw_name, ".zip")
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError as exc:
            raise ValueError("Content-Length ไม่ถูกต้อง") from exc
        if length < 1:
            raise ValueError("ไฟล์ว่างหรือเบราว์เซอร์ไม่ได้ส่ง Content-Length")
        if length > MAX_UPLOAD_BYTES:
            raise ValueError(f"ไฟล์ใหญ่เกิน {MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB")
        target = IMPORT_DIR / filename
        temp = target.with_suffix(target.suffix + ".uploading")
        remaining = length
        with temp.open("wb") as output:
            while remaining:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("รับข้อมูลไฟล์ไม่ครบ")
                output.write(chunk)
                remaining -= len(chunk)
        try:
            details = validate_import_archive(temp)
            os.replace(temp, target)
            return {"message": "อัปโหลดและตรวจสอบไฟล์เรียบร้อยแล้ว", "file": target.name, **details}
        except Exception:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            raise

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/health":
            return self.send_bytes(200, f"ok v{APP_VERSION}".encode(), "text/plain; charset=utf-8")
        if not self.require_auth():
            return
        try:
            if path in ("/", "/index.html"):
                html = Path("/app/index.html").read_bytes()
                return self.send_bytes(200, html, "text/html; charset=utf-8")
            if path == "/api/version":
                return self.send_json(200, {
                    "version": APP_VERSION,
                    "actions_enabled": ACTIONS_ENABLED,
                    "runtime_mode": RUNTIME_MODE,
                    "runtime_label": RUNTIME_LABEL,
                    "target_config_platform": TARGET_CONFIG_PLATFORM,
                    "import_modes": IMPORT_MODE_LABELS,
                })
            if path == "/api/status":
                errors = {}
                values = {}
                for name, endpoint in (("info", "info"), ("metrics", "metrics"), ("players", "players"), ("settings", "settings")):
                    try:
                        values[name] = api_request(endpoint)
                    except Exception as exc:
                        values[name] = {} if name != "players" else []
                        errors[name] = str(exc)
                values.update({
                    "server_online": not errors.get("info"),
                    "errors": errors,
                    "container": container_status(),
                    "runtime_mode": RUNTIME_MODE,
                    "runtime_label": RUNTIME_LABEL,
                    "active_job": active_job_snapshot(),
                    "actions_enabled": ACTIONS_ENABLED,
                })
                return self.send_json(200, values)
            if path == "/api/snapshot":
                snapshot = api_request("game-data")
                size = len(json.dumps(snapshot, ensure_ascii=False).encode("utf-8"))
                return self.send_json(200, {"snapshot": snapshot, "bytes": size})
            if path == "/api/config":
                return self.send_json(200, config_snapshot())
            if path == "/api/config/backups":
                files = []
                for item in CONFIG_BACKUP_DIR.glob("*.ini"):
                    try:
                        info = item.stat()
                    except OSError:
                        continue
                    files.append({"name": item.name, "size": info.st_size, "modified_at": datetime.fromtimestamp(info.st_mtime, LOCAL_TZ).isoformat(timespec="seconds")})
                files.sort(key=lambda item: item["modified_at"], reverse=True)
                return self.send_json(200, {"files": files[:100]})
            if path == "/api/bans":
                with STATE_LOCK:
                    payload = {"active": list(BANS["active"].values()), "history": list(reversed(BANS["history"][-300:]))}
                return self.send_json(200, payload)
            if path == "/api/jobs":
                return self.send_json(200, {"jobs": job_snapshot(200), "active": active_job_snapshot()})
            if path == "/api/exports":
                return self.send_json(200, {"files": list_files(EXPORT_DIR)})
            if path == "/api/imports":
                return self.send_json(200, {"files": list_files(IMPORT_DIR), "max_upload_bytes": MAX_UPLOAD_BYTES})
            if path.startswith("/api/import/inspect/"):
                filename = safe_filename(urllib.parse.unquote(path.rsplit("/", 1)[-1]), ".zip")
                source = IMPORT_DIR / filename
                details = validate_import_archive(source)
                return self.send_json(200, {"file": filename, **details})
            if path.startswith("/api/export/download/"):
                filename = safe_filename(urllib.parse.unquote(path.rsplit("/", 1)[-1]), ".zip")
                target = EXPORT_DIR / filename
                if not target.is_file():
                    return self.send_json(404, {"error": "ไม่พบไฟล์ Export"})
                return self.send_file(target, filename)
            return self.send_json(404, {"error": "ไม่พบ endpoint"})
        except Exception as exc:
            code, message = api_error(exc)
            return self.send_json(code, {"error": message})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self.require_auth():
            return
        if not self.same_origin():
            return self.send_json(403, {"error": "Origin ไม่ถูกต้อง"})
        if not ACTIONS_ENABLED:
            return self.send_json(403, {"error": "คำสั่งผู้ดูแลถูกปิด"})
        try:
            if path == "/api/import/upload":
                result = self.handle_upload(urllib.parse.parse_qs(parsed.query))
                return self.send_json(200, result)

            body = self.read_json()
            if path == "/api/config/save":
                result = save_config_content(body.get("content"))
                return self.send_json(200, {"message": "บันทึก Config เรียบร้อยแล้ว", **result})
            if path == "/api/config/settings":
                result = patch_config_settings(body.get("changes"), body.get("expected_sha256"))
                return self.send_json(200, {"message": f"อัปเดต Config {result['changed_count']} ค่าเรียบร้อยแล้ว", **result})
            if path == "/api/maintenance/restart":
                job = create_job(
                    "restart",
                    body.get("scheduled_at"),
                    body.get("warning_seconds", 60),
                    body.get("message", "Server maintenance: restarting to apply configuration."),
                )
                return self.send_json(200, {"message": "ตั้งคิว Restart แล้ว", "job": job})
            if path == "/api/maintenance/export":
                job = create_job(
                    "export",
                    body.get("scheduled_at"),
                    body.get("warning_seconds", 60),
                    body.get("message", "Server maintenance for export"),
                )
                return self.send_json(200, {"message": "ตั้งคิว Export แล้ว", "job": job})
            if path == "/api/maintenance/import":
                filename = safe_filename(body.get("filename", ""), ".zip")
                source = IMPORT_DIR / filename
                import_mode = normalize_import_mode(body.get("import_mode"))
                details = validate_import_archive(source, import_mode)
                archive_summary = {
                    "source_runtime": details.get("source_runtime"),
                    "source_config_platform": details.get("source_config_platform"),
                    "target_config_platform": details.get("target_config_platform"),
                    "target_config_available": details.get("target_config_available"),
                    "cross_platform": details.get("cross_platform"),
                    "supported_import_modes": details.get("supported_import_modes"),
                    "warning": details.get("warning"),
                    "selected_world_id": details.get("selected_world_id"),
                    "selected_world_player_files": details.get("selected_world_player_files"),
                }
                job = create_job(
                    "import",
                    body.get("scheduled_at"),
                    body.get("warning_seconds", 60),
                    body.get("message", "Server maintenance for import"),
                    source_file=filename,
                    import_mode=import_mode,
                    archive_summary=archive_summary,
                )
                return self.send_json(200, {"message": "ตั้งคิว Import แล้ว", "job": job})
            if path == "/api/job/cancel":
                job_id = clean_text(body.get("job_id"), 64)
                job = get_job(job_id)
                if not job:
                    raise ValueError("ไม่พบงาน")
                if job.get("status") != "pending":
                    raise ValueError("ยกเลิกได้เฉพาะงานที่ยังรอ")
                update_job(job_id, status="cancelled", stage="cancelled", finished_at=iso_now())
                discord_notify("ยกเลิกงาน Maintenance", f"งาน `{job_id}` ถูกยกเลิก", "warning")
                return self.send_json(200, {"message": "ยกเลิกงานแล้ว"})
            if path == "/api/action/start":
                if not MAINTENANCE_LOCK.acquire(blocking=False):
                    raise ValueError("มีงาน Maintenance กำลังทำอยู่ ไม่สามารถเปิด Palworld runtime ด้วยตนเองได้")
                try:
                    status = container_status()
                    if not status.get("available"):
                        raise RuntimeError(status.get("error") or "ไม่สามารถตรวจสอบ Palworld runtime ได้")
                    if status.get("running"):
                        return self.send_json(200, {"message": "Palworld runtime เปิดอยู่แล้ว"})
                    start_container()
                    discord_notify("เปิด Palworld runtime ด้วยตนเอง", f"Runtime `{RUNTIME_LABEL}` ถูกสั่ง Start จาก Dashboard", "info")
                    return self.send_json(200, {"message": "ส่งคำสั่งเปิด Palworld runtime แล้ว"})
                finally:
                    MAINTENANCE_LOCK.release()
            if path == "/api/action/container-stop":
                if not MAINTENANCE_LOCK.acquire(blocking=False):
                    raise ValueError("มีงาน Maintenance กำลังทำอยู่ ไม่สามารถปิด Palworld runtime ด้วยตนเองได้")
                try:
                    status = container_status()
                    if not status.get("available"):
                        raise RuntimeError(status.get("error") or "ไม่สามารถตรวจสอบ Palworld runtime ได้")
                    if not status.get("running"):
                        return self.send_json(200, {"message": "Palworld runtime ปิดอยู่แล้ว"})
                    save_error = None
                    try:
                        api_request("save", "POST", timeout=30)
                    except Exception as exc:
                        save_error = str(exc)
                    stop_container()
                    if save_error:
                        message = f"ปิด Palworld runtime แล้ว แต่ Save World ก่อนปิดไม่สำเร็จ: {save_error}"
                        discord_notify("ปิด Palworld runtime ด้วยตนเอง", f"Runtime `{RUNTIME_LABEL}` ถูกปิดจาก Dashboard\nSave World ไม่สำเร็จ: {save_error}", "warning")
                    else:
                        message = "บันทึกโลกและปิด Palworld runtime เรียบร้อยแล้ว"
                        discord_notify("ปิด Palworld runtime ด้วยตนเอง", f"Runtime `{RUNTIME_LABEL}` ถูก Save World และ Stop จาก Dashboard", "warning")
                    return self.send_json(200, {"message": message, "save_world_success": save_error is None})
                finally:
                    MAINTENANCE_LOCK.release()
            if path == "/api/action/announce":
                api_request("announce", "POST", {"message": clean_text(body.get("message"))})
                return self.send_json(200, {"message": "ส่งประกาศเรียบร้อยแล้ว"})
            if path == "/api/action/save":
                api_request("save", "POST")
                return self.send_json(200, {"message": "บันทึกโลกเรียบร้อยแล้ว"})
            if path == "/api/action/kick":
                userid = clean_userid(body.get("userid"))
                name = clean_text(body.get("name", ""), 128, allow_empty=True)
                reason = clean_text(body.get("message", "Removed by administrator"))
                return self.send_json(200, perform_player_action("kick", userid, name, reason))
            if path == "/api/action/ban":
                userid = clean_userid(body.get("userid"))
                reason = clean_text(body.get("message", "Banned by administrator"))
                name = clean_text(body.get("name", ""), 128, allow_empty=True)
                return self.send_json(200, perform_player_action("ban", userid, name, reason))
            if path == "/api/action/unban":
                userid = clean_userid(body.get("userid"))
                name = clean_text(body.get("name", ""), 128, allow_empty=True)
                return self.send_json(200, perform_player_action("unban", userid, name, ""))
            if path == "/api/action/shutdown":
                waittime = body.get("waittime")
                if not isinstance(waittime, int) or not 0 <= waittime <= 3600:
                    raise ValueError("waittime ต้องเป็นจำนวนเต็ม 0-3600")
                message = clean_text(body.get("message", "Server shutdown"))
                api_request("shutdown", "POST", {"waittime": waittime, "message": message})
                return self.send_json(200, {"message": f"ตั้งเวลาปิดเซิร์ฟเวอร์ใน {waittime} วินาทีแล้ว"})
            if path == "/api/action/stop":
                api_request("stop", "POST")
                return self.send_json(200, {"message": "ส่งคำสั่ง Force Stop แล้ว"})
            return self.send_json(404, {"error": "ไม่พบ endpoint"})
        except Exception as exc:
            code, message = api_error(exc)
            return self.send_json(code, {"error": message})


if __name__ == "__main__":
    if not ADMIN_PASSWORD:
        print("WARNING: PALWORLD_ADMIN_PASSWORD is empty; REST API authentication will fail.")
    if not DASHBOARD_PASSWORD:
        print("WARNING: DASHBOARD_PASSWORD is empty; dashboard has no login protection.")
    if not DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED:
        print("INFO: Dashboard Discord workflow notifications are disabled by DASHBOARD_DISCORD_NOTIFICATIONS_ENABLED=false.")
    elif not DISCORD_WEBHOOK_URL:
        print("WARNING: DASHBOARD_DISCORD_WEBHOOK_URL is empty; workflow notifications are disabled.")
    print(f"INFO: Palworld runtime mode={RUNTIME_MODE} label={RUNTIME_LABEL}")
    threading.Thread(target=scheduler_loop, name="maintenance-scheduler", daemon=True).start()
    print(f"Palworld Dashboard v{APP_VERSION} listening on 0.0.0.0:{LISTEN_PORT}")
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler).serve_forever()
