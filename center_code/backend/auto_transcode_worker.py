import os
import sys
import subprocess
from datetime import datetime


def _truthy(v: str) -> bool:
    v = (v or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _is_production() -> bool:
    return (os.getenv("FLASK_ENV") == "production") or (os.getenv("ENVIRONMENT") == "production")


def _is_pid_running(pid: int) -> bool:
    try:
        pid = int(pid)
        if pid <= 0:
            return False
    except Exception:
        return False

    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    try:
        import ctypes  # type: ignore

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


class _FileLock:
    def __init__(self, path: str):
        self.path = path
        self.f = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.f = open(self.path, "a+", encoding="utf-8")
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.f:
                if os.name == "nt":
                    import msvcrt

                    try:
                        self.f.seek(0)
                        msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl

                    try:
                        fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
        finally:
            try:
                if self.f:
                    self.f.close()
            except Exception:
                pass


def _has_pending_work() -> bool:
    try:
        from db import get_db
        from models import Material, MaterialTranscodeTask
    except Exception:
        return False

    try:
        with get_db() as db:
            pending = (
                db.query(MaterialTranscodeTask.id)
                .filter(MaterialTranscodeTask.status.in_(["pending", "running"]))
                .limit(1)
                .first()
            )
            if pending:
                return True

            processing = db.query(Material.id).filter(Material.status == "processing").limit(1).first()
            return processing is not None
    except Exception:
        return False


def maybe_start_transcode_worker() -> bool:
    """
    Auto-start transcode worker when enabled and there is pending/processing work.

    Enable rules:
    - If AUTO_START_TRANSCODE_WORKER=true => enabled even in production.
    - Else enabled only when not production.
    """
    enabled = _truthy(os.getenv("AUTO_START_TRANSCODE_WORKER", ""))
    if not enabled and _is_production():
        return False
    if not enabled and not _has_pending_work():
        return False

    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    lock_path = os.path.join(logs_dir, "worker_transcode.lock")
    pid_path = os.path.join(logs_dir, "worker_transcode.pid")
    log_path = os.path.join(logs_dir, "worker_transcode.log")

    try:
        with _FileLock(lock_path):
            # If already running, skip.
            try:
                if os.path.exists(pid_path):
                    raw = open(pid_path, "r", encoding="utf-8").read().strip()
                    if raw:
                        pid = int(raw)
                        if _is_pid_running(pid):
                            return False
            except Exception:
                pass

            worker_py = os.path.join(base_dir, "worker_transcode.py")
            if not os.path.exists(worker_py):
                return False

            os.makedirs(logs_dir, exist_ok=True)
            logf = open(log_path, "a", encoding="utf-8")
            logf.write(f"\n[{datetime.now().isoformat()}] autostart\n")
            logf.flush()

            env = os.environ.copy()
            env["TRANSCODE_WORKER_AUTOSTARTED"] = "1"

            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                )

            p = subprocess.Popen(
                [sys.executable, worker_py],
                cwd=base_dir,
                stdout=logf,
                stderr=logf,
                env=env,
                creationflags=creationflags,
                close_fds=(os.name != "nt"),
            )

            try:
                with open(pid_path, "w", encoding="utf-8") as f:
                    f.write(str(p.pid))
            except Exception:
                pass

            return True
    except Exception:
        return False

