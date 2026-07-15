#!/usr/bin/env python3
import base64
import json
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

APP_VERSION = "5.1.0"
API_URL = os.getenv("PALWORLD_API_URL", "http://127.0.0.1:8212/v1/api").rstrip("/")
ADMIN_PASSWORD = os.getenv("PALWORLD_ADMIN_PASSWORD", "")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
REFRESH_SECONDS = max(5, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15")))
LISTEN_PORT = int(os.getenv("DASHBOARD_LISTEN_PORT", "8080"))
ACTIONS_ENABLED = os.getenv("DASHBOARD_ACTIONS_ENABLED", "true").lower() == "true"
TIMEZONE_NAME = os.getenv("DASHBOARD_TIMEZONE", "Asia/Bangkok")
LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)
DOCKER_API_URL = os.getenv("DOCKER_API_URL", "http://docker-proxy:2375").rstrip("/")
PALWORLD_CONTAINER_NAME = os.getenv("PALWORLD_CONTAINER_NAME", "palworld-server")
PALWORLD_DATA_DIR = Path(os.getenv("PALWORLD_DATA_DIR", "/palworld-data")).resolve()
SAVED_DIR = PALWORLD_DATA_DIR / "Pal" / "Saved"
DATA_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", "/data")).resolve()
EXPORT_DIR = DATA_DIR / "exports"
IMPORT_DIR = DATA_DIR / "imports"
STAGING_DIR = PALWORLD_DATA_DIR / ".dashboard-staging"
STATE_FILE = DATA_DIR / "state.json"
BAN_FILE = DATA_DIR / "bans.json"
MAINTENANCE_FILE = DATA_DIR / "maintenance.json"
DISCORD_WEBHOOK_URL = os.getenv("DASHBOARD_DISCORD_WEBHOOK_URL", "").strip()
MAX_UPLOAD_BYTES = max(1, int(os.getenv("DASHBOARD_MAX_UPLOAD_MB", "4096"))) * 1024 * 1024
MAX_EXPANDED_BYTES = max(MAX_UPLOAD_BYTES, int(os.getenv("DASHBOARD_MAX_EXPANDED_MB", "8192")) * 1024 * 1024)
MAX_ARCHIVE_FILES = max(100, int(os.getenv("DASHBOARD_MAX_ARCHIVE_FILES", "200000")))
START_TIMEOUT_SECONDS = max(60, int(os.getenv("PALWORLD_START_TIMEOUT_SECONDS", "900")))
STOP_TIMEOUT_SECONDS = max(10, int(os.getenv("PALWORLD_STOP_TIMEOUT_SECONDS", "60")))
PALWORLD_PUID = int(os.getenv("PALWORLD_PUID", "1000"))
PALWORLD_PGID = int(os.getenv("PALWORLD_PGID", "1000"))
MAX_JSON_BODY = 256 * 1024

STATE_LOCK = threading.RLock()
MAINTENANCE_LOCK = threading.Lock()
SCHEDULER_WAKE = threading.Event()


def now_local():
    return datetime.now(LOCAL_TZ)


def iso_now():
    return now_local().isoformat(timespec="seconds")


def ensure_directories():
    for path in (DATA_DIR, EXPORT_DIR, IMPORT_DIR, STAGING_DIR):
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


def container_info():
    quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
    return docker_request(f"/containers/{quoted}/json", timeout=10)


def container_status():
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
        }
    except Exception as exc:
        return {"available": False, "running": False, "status": "unknown", "health": "unknown", "error": str(exc)}


def get_restart_policy():
    policy = (container_info().get("HostConfig") or {}).get("RestartPolicy") or {}
    name = str(policy.get("Name") or "no")
    try:
        maximum_retry_count = int(policy.get("MaximumRetryCount") or 0)
    except (TypeError, ValueError):
        maximum_retry_count = 0
    return {
        "Name": name,
        "MaximumRetryCount": maximum_retry_count,
    }


def restart_policies_match(left, right):
    if (left or {}).get("Name", "no") != (right or {}).get("Name", "no"):
        return False
    if (left or {}).get("Name") == "on-failure":
        return int((left or {}).get("MaximumRetryCount") or 0) == int(
            (right or {}).get("MaximumRetryCount") or 0
        )
    return True


def set_restart_policy(policy):
    if not isinstance(policy, dict):
        raise ValueError("Restart Policy ไม่ถูกต้อง")
    name = str(policy.get("Name") or "no")
    if name not in ("no", "always", "unless-stopped", "on-failure"):
        raise ValueError(f"ไม่รองรับ Restart Policy: {name}")

    restart_policy = {"Name": name}
    if name == "on-failure":
        retry_count = int(policy.get("MaximumRetryCount") or 0)
        if retry_count < 0:
            raise ValueError("MaximumRetryCount ต้องไม่ติดลบ")
        restart_policy["MaximumRetryCount"] = retry_count

    quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
    docker_request(
        f"/containers/{quoted}/update",
        method="POST",
        payload={"RestartPolicy": restart_policy},
        timeout=30,
    )

    current = get_restart_policy()
    expected = {
        "Name": name,
        "MaximumRetryCount": int(restart_policy.get("MaximumRetryCount") or 0),
    }
    if not restart_policies_match(current, expected):
        raise RuntimeError(
            f"เปลี่ยน Restart Policy ไม่สำเร็จ: ต้องการ {expected} แต่ได้ {current}"
        )


def stop_container():
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
        if status.get("available") and not status.get("running"):
            return
        time.sleep(1)
    raise RuntimeError("หยุดคอนเทนเนอร์ Palworld ไม่สำเร็จภายในเวลาที่กำหนด")


def start_container():
    quoted = urllib.parse.quote(PALWORLD_CONTAINER_NAME, safe="")
    docker_request(f"/containers/{quoted}/start", method="POST", timeout=30, allow_status=(304,))


def wait_for_server_ready(timeout_seconds=START_TIMEOUT_SECONDS):
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        status = container_status()
        if status.get("available") and not status.get("running"):
            last_error = "container stopped while waiting"
        else:
            try:
                api_request("info", timeout=8)
                return
            except Exception as exc:
                last_error = str(exc)
        time.sleep(5)
    raise RuntimeError(f"Palworld REST API ยังไม่พร้อมหลังรอ {timeout_seconds} วินาที: {last_error}")


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
    if not DISCORD_WEBHOOK_URL:
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


def add_ban_record(userid, name, reason, action):
    event = {
        "userid": userid,
        "name": name or "",
        "reason": reason or "",
        "action": action,
        "at": iso_now(),
    }
    with STATE_LOCK:
        if action == "ban":
            BANS["active"][userid] = {
                "userid": userid,
                "name": name or "",
                "reason": reason or "",
                "banned_at": event["at"],
            }
        else:
            previous = BANS["active"].pop(userid, None)
            if previous and not event["name"]:
                event["name"] = previous.get("name", "")
        BANS["history"].append(event)
        save_bans()
    discord_notify(
        "ผู้เล่นถูกแบน" if action == "ban" else "ผู้เล่นถูกปลดแบน",
        f"User ID: `{userid}`\nชื่อ: {name or '-'}\nเหตุผล: {reason or '-'}",
        "warning" if action == "ban" else "success",
    )


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


def create_job(job_type, schedule_at, warning_seconds, message, source_file=None):
    if job_type not in ("export", "import"):
        raise ValueError("ประเภทงานไม่ถูกต้อง")
    if not isinstance(warning_seconds, int) or not 0 <= warning_seconds <= 3600:
        raise ValueError("เวลาประกาศเตือนต้องเป็นจำนวนเต็ม 0-3600 วินาที")
    schedule = parse_schedule(schedule_at)
    job = {
        "id": uuid.uuid4().hex[:12],
        "type": job_type,
        "status": "pending",
        "stage": "scheduled",
        "scheduled_at": schedule.isoformat(timespec="seconds"),
        "warning_seconds": warning_seconds,
        "message": clean_text(message or "Server maintenance", 500),
        "source_file": source_file,
        "output_file": None,
        "safety_backup": None,
        "restart_policy": None,
        "created_at": iso_now(),
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    with STATE_LOCK:
        pending = [item for item in STATE["jobs"] if item.get("status") in ("pending", "running")]
        if len(pending) >= 20:
            raise ValueError("มีงานรอหรือกำลังทำมากเกินไป")
        STATE["jobs"].append(job)
        STATE["jobs"] = STATE["jobs"][-500:]
        save_state()
    discord_notify(
        "ตั้งคิว Export" if job_type == "export" else "ตั้งคิว Import",
        f"งาน `{job['id']}`\nเวลาทำงาน: {job['scheduled_at']}\nเวลาเตือน: {warning_seconds} วินาที"
        + (f"\nไฟล์: `{source_file}`" if source_file else ""),
        "info",
    )
    SCHEDULER_WAKE.set()
    return job


def update_job(job_id, **changes):
    with STATE_LOCK:
        for job in STATE["jobs"]:
            if job.get("id") == job_id:
                job.update(changes)
                STATE["last_job_id"] = job_id
                save_state()
                return job
    raise KeyError(job_id)


def get_job(job_id):
    with STATE_LOCK:
        for job in STATE["jobs"]:
            if job.get("id") == job_id:
                return dict(job)
    return None


def job_snapshot(limit=100):
    with STATE_LOCK:
        return [dict(item) for item in reversed(STATE["jobs"][-limit:])]


def active_job_snapshot():
    with STATE_LOCK:
        running = [dict(item) for item in STATE["jobs"] if item.get("status") == "running"]
        if running:
            return running[0]
        pending = sorted(
            [dict(item) for item in STATE["jobs"] if item.get("status") == "pending"],
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


def chown_tree(root):
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


def validate_import_archive(path):
    if not path.is_file():
        raise ValueError("ไม่พบไฟล์ Import")
    total_size = 0
    file_count = 0
    has_saved_content = False
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
            mode = (item.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError(f"ไม่อนุญาต symlink ใน ZIP: {raw_name}")
            if raw_name == "dashboard-export-manifest.json":
                continue
            if not raw_name.startswith("Pal/Saved/"):
                raise ValueError(f"ZIP ต้องมีเฉพาะ dashboard-export-manifest.json และ Pal/Saved/: {raw_name}")
            if not item.is_dir():
                has_saved_content = True
                total_size += item.file_size
                if total_size > MAX_EXPANDED_BYTES:
                    raise ValueError(f"ขนาดหลังแตก ZIP เกิน {MAX_EXPANDED_BYTES / 1024 / 1024:.0f} MB")
    if not has_saved_content:
        raise ValueError("ZIP ไม่มีข้อมูลภายใต้ Pal/Saved/")
    return {"files": file_count, "expanded_bytes": total_size}


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


def wait_for_shutdown_completion(warning_seconds):
    warning_seconds = max(0, int(warning_seconds))
    shutdown_started_at = time.monotonic()
    force_stop_after = shutdown_started_at + warning_seconds + 5
    deadline = force_stop_after + STOP_TIMEOUT_SECONDS + 30
    last_error = ""

    while time.monotonic() < deadline:
        status = container_status()
        if status.get("available") and not status.get("running"):
            return
        if not status.get("available"):
            last_error = status.get("error", "อ่านสถานะคอนเทนเนอร์ไม่ได้")

        if time.monotonic() >= force_stop_after:
            try:
                api_request("info", timeout=3)
            except Exception:
                stop_container()
                return
        time.sleep(1)

    print(
        "Palworld shutdown did not stop the container within the expected time; "
        f"falling back to Docker stop. Last status error: {last_error or '-'}"
    )
    stop_container()


def shutdown_for_maintenance(job):
    warning = int(job.get("warning_seconds", 0))
    message = job.get("message") or "Server maintenance"
    status = container_status()
    if not status.get("available"):
        raise RuntimeError(
            f"อ่านสถานะคอนเทนเนอร์ Palworld ไม่ได้: {status.get('error', 'unknown error')}"
        )
    if not status.get("running"):
        return None

    original_policy = get_restart_policy()
    update_job(job["id"], restart_policy=original_policy)
    policy_changed = True
    try:
        set_restart_policy({"Name": "no", "MaximumRetryCount": 0})

        try:
            api_request("save", "POST")
        except Exception as exc:
            print(f"Save before shutdown warning failed: {exc}")

        api_request(
            "shutdown",
            "POST",
            {
                "waittime": warning,
                "message": message,
            },
        )
        discord_notify(
            "เริ่มช่วง Maintenance",
            f"งาน `{job['id']}` ({job['type']})\nประกาศ: {message}\nเซิร์ฟเวอร์จะปิดใน {warning} วินาที",
            "warning",
        )
        wait_for_shutdown_completion(warning)
        return original_policy
    except Exception:
        restored = False
        if policy_changed:
            try:
                set_restart_policy(original_policy)
                restored = True
            except Exception as restore_exc:
                print(f"Restore restart policy after shutdown failure failed: {restore_exc}")
        if restored:
            try:
                update_job(job["id"], restart_policy=None)
            except Exception as state_exc:
                print(f"Clear persisted restart policy failed: {state_exc}")
        raise


def restore_job_restart_policy(job_id, policy):
    if policy is None:
        return
    set_restart_policy(policy)
    update_job(job_id, restart_policy=None)


def run_export_job(job):
    original_policy = None
    try:
        update_job(job["id"], stage="announcing")
        set_maintenance_marker(job, "announcing")
        original_policy = shutdown_for_maintenance(job)

        update_job(job["id"], stage="stopping_server")
        set_maintenance_marker(job, "stopping_server")
        if container_status().get("running"):
            stop_container()
        discord_notify("เซิร์ฟเวอร์ปิดชั่วคราว", f"งาน `{job['id']}` กำลัง Export ข้อมูล", "warning")

        update_job(job["id"], stage="creating_archive")
        set_maintenance_marker(job, "creating_archive")
        output = create_export_archive("palworld-export", job["id"])
        discord_notify(
            "สร้างไฟล์ Export แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{output.name}`\nกำลังเปิดเซิร์ฟเวอร์กลับ",
            "info",
        )

        update_job(job["id"], output_file=output.name, stage="starting_server")
        set_maintenance_marker(job, "starting_server")
        restore_job_restart_policy(job["id"], original_policy)
        original_policy = None
        start_container()
        wait_for_server_ready()

        size = output.stat().st_size
        discord_notify(
            "Export เสร็จและเปิดเซิร์ฟเวอร์แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{output.name}`\nขนาด: {size / 1024 / 1024:.2f} MB",
            "success",
        )
    finally:
        if original_policy is not None:
            try:
                restore_job_restart_policy(job["id"], original_policy)
            except Exception as exc:
                print(f"Restore restart policy after export failed: {exc}")


def run_import_job(job):
    source_name = safe_filename(job.get("source_file", ""), ".zip")
    source = IMPORT_DIR / source_name
    validate_import_archive(source)

    original_policy = None
    staging_root = STAGING_DIR / f"import-{job['id']}"
    rollback_saved = PALWORLD_DATA_DIR / f".dashboard-rollback-saved-{job['id']}"
    imported = False
    old_moved = False

    if staging_root.exists():
        shutil.rmtree(staging_root)
    if rollback_saved.exists():
        shutil.rmtree(rollback_saved)

    try:
        update_job(job["id"], stage="announcing")
        set_maintenance_marker(job, "announcing")
        original_policy = shutdown_for_maintenance(job)

        update_job(job["id"], stage="stopping_server")
        set_maintenance_marker(job, "stopping_server")
        if container_status().get("running"):
            stop_container()
        discord_notify("เซิร์ฟเวอร์ปิดชั่วคราว", f"งาน `{job['id']}` กำลัง Import `{source.name}`", "warning")

        update_job(job["id"], stage="safety_backup")
        set_maintenance_marker(job, "safety_backup")
        safety_backup = create_export_archive("pre-import", job["id"])
        update_job(job["id"], safety_backup=safety_backup.name)
        discord_notify(
            "สร้าง Safety Backup แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{safety_backup.name}`\nกำลังตรวจสอบและนำเข้าข้อมูลใหม่",
            "info",
        )

        update_job(job["id"], stage="extracting")
        set_maintenance_marker(job, "extracting")
        extracted_saved = extract_import_archive(source, staging_root)

        update_job(job["id"], stage="replacing_saved_data")
        set_maintenance_marker(job, "replacing_saved_data")
        if SAVED_DIR.exists():
            os.replace(SAVED_DIR, rollback_saved)
            old_moved = True
        SAVED_DIR.parent.mkdir(parents=True, exist_ok=True)
        os.replace(extracted_saved, SAVED_DIR)
        imported = True
        chown_tree(SAVED_DIR)
        discord_notify(
            "แทนที่ข้อมูล Import แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{source.name}`\nกำลังเปิดเซิร์ฟเวอร์เพื่อตรวจสอบ",
            "info",
        )

        update_job(job["id"], stage="starting_server")
        set_maintenance_marker(job, "starting_server")
        restore_job_restart_policy(job["id"], original_policy)
        original_policy = None
        start_container()
        wait_for_server_ready()

        if rollback_saved.exists():
            shutil.rmtree(rollback_saved)
        if staging_root.exists():
            shutil.rmtree(staging_root)
        discord_notify(
            "Import เสร็จและเปิดเซิร์ฟเวอร์แล้ว",
            f"งาน `{job['id']}`\nไฟล์: `{source.name}`\nSafety backup: `{safety_backup.name}`",
            "success",
        )
    except Exception:
        if old_moved:
            try:
                if container_status().get("running"):
                    stop_container()
            except Exception:
                pass
            try:
                failed_saved = PALWORLD_DATA_DIR / f".dashboard-failed-import-{job['id']}"
                if failed_saved.exists():
                    shutil.rmtree(failed_saved)
                if imported and SAVED_DIR.exists():
                    os.replace(SAVED_DIR, failed_saved)
                if rollback_saved.exists():
                    os.replace(rollback_saved, SAVED_DIR)
                    chown_tree(SAVED_DIR)
            except Exception as rollback_exc:
                print(f"Rollback failed: {rollback_exc}")
        raise
    finally:
        if original_policy is not None:
            try:
                restore_job_restart_policy(job["id"], original_policy)
            except Exception as exc:
                print(f"Restore restart policy after import failed: {exc}")
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)


def run_job(job):
    with MAINTENANCE_LOCK:
        update_job(job["id"], status="running", stage="starting", started_at=iso_now(), error=None)
        current = get_job(job["id"])
        try:
            if current["type"] == "export":
                run_export_job(current)
            else:
                run_import_job(current)
            update_job(job["id"], status="completed", stage="completed", finished_at=iso_now())
            clear_maintenance_marker()
        except Exception as exc:
            message = str(exc)
            print(f"Maintenance job {job['id']} failed: {message}")
            recovery_parts = []

            latest = get_job(job["id"]) or {}
            persisted_policy = latest.get("restart_policy")
            if isinstance(persisted_policy, dict):
                try:
                    restore_job_restart_policy(job["id"], persisted_policy)
                    recovery_parts.append("คืนค่า Restart Policy แล้ว")
                except Exception as policy_exc:
                    recovery_parts.append(f"คืนค่า Restart Policy ไม่สำเร็จ: {policy_exc}")

            try:
                status = container_status()
                if not status.get("running"):
                    start_container()
                    wait_for_server_ready(timeout_seconds=min(START_TIMEOUT_SECONDS, 600))
                    recovery_parts.append("เปิดเซิร์ฟเวอร์กลับได้แล้ว")
            except Exception as recovery_exc:
                recovery_parts.append(f"เปิดเซิร์ฟเวอร์กลับอัตโนมัติไม่สำเร็จ: {recovery_exc}")

            recovery = " " + " | ".join(recovery_parts) if recovery_parts else ""
            update_job(job["id"], status="failed", stage="failed", finished_at=iso_now(), error=message + recovery)
            set_maintenance_marker(job, "failed")
            discord_notify(
                "Maintenance ล้มเหลว",
                f"งาน `{job['id']}`\nข้อผิดพลาด: {message}\nการกู้คืน: {recovery or 'ไม่ต้องกู้คืน'}",
                "error",
            )


def scheduler_loop():
    time.sleep(3)
    interrupted = []
    interrupted_policies = []
    with STATE_LOCK:
        for job in STATE["jobs"]:
            if job.get("status") == "running":
                job["status"] = "failed"
                job["stage"] = "interrupted"
                job["finished_at"] = iso_now()
                job["error"] = "Dashboard ถูกรีสตาร์ตระหว่างทำงาน กรุณาตรวจสอบข้อมูลและสถานะเซิร์ฟเวอร์"
                interrupted.append(job["id"])
                if isinstance(job.get("restart_policy"), dict):
                    interrupted_policies.append((job["id"], dict(job["restart_policy"])))
        if interrupted:
            save_state()
    if interrupted:
        for job_id, policy in interrupted_policies:
            try:
                restore_job_restart_policy(job_id, policy)
            except Exception as exc:
                print(f"Interrupted job {job_id} could not restore restart policy: {exc}")
        try:
            if not container_status().get("running"):
                start_container()
        except Exception as exc:
            print(f"Interrupted job recovery could not start server: {exc}")
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
                return self.send_json(200, {"version": APP_VERSION, "actions_enabled": ACTIONS_ENABLED})
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
                    "active_job": active_job_snapshot(),
                    "actions_enabled": ACTIONS_ENABLED,
                })
                return self.send_json(200, values)
            if path == "/api/snapshot":
                snapshot = api_request("game-data")
                size = len(json.dumps(snapshot, ensure_ascii=False).encode("utf-8"))
                return self.send_json(200, {"snapshot": snapshot, "bytes": size})
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
                validate_import_archive(source)
                job = create_job(
                    "import",
                    body.get("scheduled_at"),
                    body.get("warning_seconds", 60),
                    body.get("message", "Server maintenance for import"),
                    source_file=filename,
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
                start_container()
                return self.send_json(200, {"message": "ส่งคำสั่งเปิดคอนเทนเนอร์แล้ว"})
            if path == "/api/action/announce":
                api_request("announce", "POST", {"message": clean_text(body.get("message"))})
                return self.send_json(200, {"message": "ส่งประกาศเรียบร้อยแล้ว"})
            if path == "/api/action/save":
                api_request("save", "POST")
                return self.send_json(200, {"message": "บันทึกโลกเรียบร้อยแล้ว"})
            if path == "/api/action/kick":
                api_request("kick", "POST", {
                    "userid": clean_userid(body.get("userid")),
                    "message": clean_text(body.get("message", "Removed by administrator")),
                })
                return self.send_json(200, {"message": "Kick ผู้เล่นเรียบร้อยแล้ว"})
            if path == "/api/action/ban":
                userid = clean_userid(body.get("userid"))
                reason = clean_text(body.get("message", "Banned by administrator"))
                name = clean_text(body.get("name", ""), 128, allow_empty=True)
                api_request("ban", "POST", {"userid": userid, "message": reason})
                add_ban_record(userid, name, reason, "ban")
                return self.send_json(200, {"message": "Ban ผู้เล่นและบันทึกประวัติเรียบร้อยแล้ว"})
            if path == "/api/action/unban":
                userid = clean_userid(body.get("userid"))
                name = clean_text(body.get("name", ""), 128, allow_empty=True)
                api_request("unban", "POST", {"userid": userid})
                add_ban_record(userid, name, "", "unban")
                return self.send_json(200, {"message": "ปลดแบนและบันทึกประวัติเรียบร้อยแล้ว"})
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
    if not DISCORD_WEBHOOK_URL:
        print("WARNING: DASHBOARD_DISCORD_WEBHOOK_URL is empty; workflow notifications are disabled.")
    threading.Thread(target=scheduler_loop, name="maintenance-scheduler", daemon=True).start()
    print(f"Palworld Dashboard v{APP_VERSION} listening on 0.0.0.0:{LISTEN_PORT}")
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler).serve_forever()
