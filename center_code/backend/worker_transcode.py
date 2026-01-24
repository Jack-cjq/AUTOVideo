"""
Material transcode worker (standalone process).

Queue table: material_transcode_tasks
"""

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import text

from db import get_db
from models import MaterialTranscodeTask
from media_utils import ffprobe, get_duration_seconds, resolve_ffmpeg_exe

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass(frozen=True)
class TaskInfo:
    id: int
    material_id: int
    input_path: str
    output_path: str
    kind: str


def utcnow() -> datetime:
    return datetime.utcnow()


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def claim_one(wid: str, lock_timeout_seconds: int) -> Optional[TaskInfo]:
    now = utcnow()
    stale_before = now - timedelta(seconds=int(lock_timeout_seconds or 0))

    with get_db() as db:
        candidate = (
            db.query(MaterialTranscodeTask.id)
            .filter(
                MaterialTranscodeTask.status == "pending",
                MaterialTranscodeTask.attempts < MaterialTranscodeTask.max_attempts,
                (MaterialTranscodeTask.locked_at.is_(None)) | (MaterialTranscodeTask.locked_at < stale_before),
            )
            .order_by(MaterialTranscodeTask.created_at.asc())
            .first()
        )
        if not candidate:
            return None

        task_id = int(candidate[0])
        res = db.execute(
            text(
                """
                UPDATE material_transcode_tasks
                SET status='running',
                    locked_by=:worker_id,
                    locked_at=:now,
                    attempts=attempts+1,
                    updated_at=:now
                WHERE id=:id
                  AND status='pending'
                  AND (locked_at IS NULL OR locked_at < :stale_before)
                """
            ),
            {"worker_id": wid, "now": now, "id": task_id, "stale_before": stale_before},
        )
        if getattr(res, "rowcount", 0) != 1:
            return None

        task = db.query(MaterialTranscodeTask).filter(MaterialTranscodeTask.id == task_id).first()
        if not task:
            return None

        # Important: do not return ORM instances from this function.
        # get_db() commits on exit which expires ORM attributes, leading to detached instances.
        return TaskInfo(
            id=int(task.id),
            material_id=int(task.material_id),
            input_path=str(task.input_path),
            output_path=str(task.output_path),
            kind=str(task.kind),
        )


def update_task(task_id: int, **fields) -> None:
    if not fields:
        return
    now = utcnow()
    fields.setdefault("updated_at", now)

    sets = []
    params = {"id": int(task_id)}
    for k, v in fields.items():
        sets.append(f"{k}=:{k}")
        params[k] = v

    with get_db() as db:
        db.execute(text(f"UPDATE material_transcode_tasks SET {', '.join(sets)} WHERE id=:id"), params)
        db.commit()


def update_material(material_id: int, **fields) -> None:
    if not fields:
        return
    now = utcnow()
    fields.setdefault("updated_at", now)

    sets = []
    params = {"id": int(material_id)}
    for k, v in fields.items():
        sets.append(f"{k}=:{k}")
        params[k] = v

    with get_db() as db:
        db.execute(text(f"UPDATE materials SET {', '.join(sets)} WHERE id=:id"), params)
        db.commit()


def run_ffmpeg_transcode(
    *,
    input_abs: str,
    output_abs: str,
    kind: str,
    duration_seconds: float,
    task_id: int,
) -> None:
    os.makedirs(os.path.dirname(output_abs), exist_ok=True)
    ffmpeg_exe = resolve_ffmpeg_exe()
    kind = (kind or "").lower().strip()

    common = [
        ffmpeg_exe,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_abs,
        "-progress",
        "pipe:1",
        "-nostats",
    ]

    if kind == "video":
        cmd = common + [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_abs,
        ]
    elif kind == "audio":
        cmd = common + [
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            output_abs,
        ]
    else:
        raise RuntimeError(f"unknown kind: {kind}")

    last_pct = -1
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        if p.stdout:
            for line in p.stdout:
                line = (line or "").strip()
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k == "out_time_ms" and duration_seconds and duration_seconds > 0:
                    try:
                        out_ms = int(v)
                        pct = int(min(99, max(0, (out_ms / (duration_seconds * 1000000.0)) * 100.0)))
                        if pct > last_pct:
                            last_pct = pct
                            update_task(task_id, progress=pct)
                    except Exception:
                        continue
                elif k == "progress" and v.strip() == "end":
                    if last_pct < 99:
                        update_task(task_id, progress=99)
    finally:
        stdout, stderr = p.communicate(timeout=None)
        if p.returncode != 0:
            err = (stderr or stdout or "").strip()
            raise RuntimeError(err or f"ffmpeg failed, exit={p.returncode}")


def process_once(wid: str, lock_timeout_seconds: int) -> bool:
    task = claim_one(wid, lock_timeout_seconds)
    if not task:
        return False

    input_abs = os.path.join(BASE_DIR, task.input_path.replace("/", os.sep))
    output_abs = os.path.join(BASE_DIR, task.output_path.replace("/", os.sep))

    if not os.path.exists(input_abs):
        update_task(task.id, status="fail", error_message=f"input missing: {input_abs}")
        update_material(task.material_id, status="failed")
        return True

    duration_s = 0.0
    try:
        duration_s = float(get_duration_seconds(ffprobe(input_abs)) or 0.0)
    except Exception:
        pass

    try:
        update_task(task.id, progress=1)
        run_ffmpeg_transcode(
            input_abs=input_abs,
            output_abs=output_abs,
            kind=task.kind,
            duration_seconds=duration_s,
            task_id=task.id,
        )
        update_task(task.id, status="success", progress=100, error_message=None)
        update_material(task.material_id, status="ready", path=task.output_path)
    except Exception as e:
        msg = str(e)
        if len(msg) > 8000:
            msg = msg[-8000:]
        update_task(task.id, status="fail", error_message=msg)
        update_material(task.material_id, status="failed")

    return True


def main() -> None:
    wid = worker_id()
    sleep_seconds = float(os.environ.get("TRANSCODE_WORKER_SLEEP", "1.0") or "1.0")
    lock_timeout_seconds = int(os.environ.get("TRANSCODE_LOCK_TIMEOUT", "1800") or "1800")

    print(f"[worker] started: {wid}")
    print(f"[worker] sleep={sleep_seconds}s lock_timeout={lock_timeout_seconds}s")

    while True:
        did = False
        try:
            did = process_once(wid, lock_timeout_seconds)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[worker] error: {e}")

        if not did:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[worker] stopped")
