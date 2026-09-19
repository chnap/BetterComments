"""Write changed files atomically with optional recoverable backups."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


class WriteError(OSError):
    """Raised when an updated file cannot be committed safely."""


def atomic_write(path: Path, data: bytes, *, backup: bool, backup_suffix: str) -> Path | None:
    target = path.resolve() if path.is_symlink() else path
    backup_path = _create_backup(target, backup_suffix) if backup else None
    temporary_path: Path | None = None
    try:
        mode = target.stat().st_mode
        with tempfile.NamedTemporaryFile(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, target)
    except OSError as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise WriteError(f"cannot update {path}: {error}") from error
    return backup_path


def _create_backup(path: Path, suffix: str) -> Path:
    candidate = path.with_name(path.name + suffix)
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}{suffix}.{counter}")
        counter += 1
    try:
        shutil.copy2(path, candidate)
    except OSError as error:
        raise WriteError(f"cannot back up {path}: {error}") from error
    return candidate

