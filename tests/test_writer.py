from __future__ import annotations

from pathlib import Path

from bettercomments.writer import atomic_write


def test_atomic_write_preserves_mode(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_bytes(b"old\n")
    path.chmod(0o744)
    atomic_write(path, b"new\n", backup=False, backup_suffix=".bak")
    assert path.read_bytes() == b"new\n"
    assert path.stat().st_mode & 0o777 == 0o744


def test_backup_names_do_not_overwrite_existing_backup(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_bytes(b"first\n")
    (tmp_path / "sample.py.bak").write_bytes(b"older\n")
    backup = atomic_write(path, b"second\n", backup=True, backup_suffix=".bak")
    assert backup is not None
    assert backup == tmp_path / "sample.py.bak.1"
    assert backup.read_bytes() == b"first\n"
