from __future__ import annotations

from pathlib import Path

from bettercomments.config import Settings
from bettercomments.discovery import discover_paths


def test_directory_scan_requires_explicit_recursion(tmp_path: Path) -> None:
    (tmp_path / "top.py").write_text("value = 1\n")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "inside.py").write_text("value = 2\n")

    shallow = discover_paths([tmp_path], recursive=False, settings=Settings())
    recursive = discover_paths([tmp_path], recursive=True, settings=Settings())

    assert [path.name for path in shallow.files] == ["top.py"]
    assert {path.name for path in recursive.files} == {"top.py", "inside.py"}


def test_ignored_directories_and_unsupported_files_are_skipped(tmp_path: Path) -> None:
    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "dependency.js").write_text("// Check permissions.\n")
    (tmp_path / "notes.txt").write_text("# Not source.\n")
    (tmp_path / "main.cpp").write_text("int main() {}\n")

    result = discover_paths([tmp_path], recursive=True, settings=Settings())
    assert result.files == (tmp_path / "main.cpp",)
    assert result.skipped >= 2


def test_recursive_scan_does_not_follow_linked_directory(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "main.py").write_text("value = 1\n")
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)

    result = discover_paths([link], recursive=True, settings=Settings())
    assert result.files == ()


def test_explicit_ignored_directory_is_skipped(tmp_path: Path) -> None:
    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "main.js").write_text("// Check permissions.\n")
    result = discover_paths([ignored], recursive=True, settings=Settings())
    assert result.files == ()


def test_linked_file_and_target_are_deduplicated(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    target.write_text("value = 1\n")
    link = tmp_path / "linked.py"
    link.symlink_to(target)
    result = discover_paths([target, link], recursive=False, settings=Settings())
    assert result.files == (target,)
