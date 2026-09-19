from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from bettercomments.cli import main


def test_dry_run_prints_diff_without_writing(tmp_path: Path, capsys) -> None:
    path = tmp_path / "sample.py"
    original = b"# Comprueba los permisos.\nvalue = 1\n"
    path.write_bytes(original)

    status = main([str(path), "--dry-run", "--diff", "--config", str(tmp_path / "missing.toml")])
    assert status == 2

    status = main([str(path), "--dry-run", "--diff"])
    captured = capsys.readouterr()
    assert status == 0
    assert "-# Comprueba los permisos." in captured.out
    assert "+# Check permissions." in captured.out
    assert path.read_bytes() == original


def test_check_returns_one_when_changes_exist(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text("# Comprueba los permisos.\n", encoding="utf-8")
    assert main([str(path), "--check", "--quiet"]) == 1


def test_yes_writes_and_backup_preserves_original(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    original = b"# Comprueba los permisos.\n"
    path.write_bytes(original)

    status = main([str(path), "--yes", "--backup", "--quiet"])
    assert status == 0
    assert path.read_bytes() == b"# Check permissions.\n"
    assert (tmp_path / "sample.py.bak").read_bytes() == original


def test_no_comment_file_is_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "sample.js"
    original = b'const value = "hello // world";\n'
    path.write_bytes(original)
    assert main([str(path), "--yes", "--quiet"]) == 0
    assert path.read_bytes() == original


def test_unsupported_file_is_skipped(tmp_path: Path, capsys) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("# Comprueba los permisos.\n", encoding="utf-8")
    assert main([str(path), "--dry-run"]) == 0
    assert "0 supported file(s)" in capsys.readouterr().out


def test_check_prioritizes_processing_errors(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text("# Comprueba los permisos.\n", encoding="utf-8")
    missing = tmp_path / "missing.py"
    assert main([str(path), str(missing), "--check", "--quiet"]) == 3


def test_oversized_file_is_reported_without_modification(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    original = b"# Comprueba los permisos.\n" + b"x" * 2_000_000
    path.write_bytes(original)
    assert main([str(path), "--dry-run", "--quiet"]) == 3
    assert path.read_bytes() == original


def test_empty_file_succeeds_without_changes(tmp_path: Path) -> None:
    path = tmp_path / "empty.py"
    path.write_bytes(b"")
    assert main([str(path), "--check", "--quiet"]) == 0
    assert path.read_bytes() == b""


def test_invalid_utf8_file_is_left_untouched(tmp_path: Path) -> None:
    path = tmp_path / "sample.js"
    original = b"// Comprueba los permisos.\n\xff"
    path.write_bytes(original)
    assert main([str(path), "--yes", "--quiet"]) == 3
    assert path.read_bytes() == original


def test_root_script_does_not_shadow_source_package() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import bettercomments.languages"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
