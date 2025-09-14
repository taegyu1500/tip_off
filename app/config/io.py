import os, yaml, tempfile, json, fcntl
from pathlib import Path
from typing import Tuple

def get_config_dir() -> Path:
    return Path.home() / ".tipoff"

def ensure_dir(p: Path) -> None:
    p.mkdir(mode=0o700, parents=True, exist_ok=True)

def config_paths() -> Tuple[Path, Path, Path]:
    d = get_config_dir()
    return d / "config.yaml", d / "config.yaml.bak", d / "config.lock"

def read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def atomic_write_yaml(path: Path, data: dict) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            yaml.safe_dump(data, tmp, sort_keys=False, allow_unicode=True)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

class FileLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.f = None
    def __enter__(self):
        self.f = open(self.lock_path, "w")
        fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
            self.f.close()
        finally:
            self.lock_path.unlink(missing_ok=True)

def backup(path: Path, bak: Path):
    if path.exists():
        bak.write_bytes(path.read_bytes())

def restore_backup(path: Path, bak: Path) -> bool:
    if bak.exists():
        path.write_bytes(bak.read_bytes())
        return True
    return False

def dump_effective_log(effective: dict):
    print("[config] effective:\n", json.dumps(effective, ensure_ascii=False, indent=2))
