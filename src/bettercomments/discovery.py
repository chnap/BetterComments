"""Discover supported source files without following directory symlinks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .languages import detect_language
from .models import ProcessingError


_SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "secrets.json",
}
_SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    files: tuple[Path, ...]
    errors: tuple[ProcessingError, ...]
    skipped: int


def discover_paths(paths: list[Path], *, recursive: bool, settings: Settings) -> DiscoveryResult:
    files: list[Path] = []
    errors: list[ProcessingError] = []
    skipped = 0
    seen: set[Path] = set()

    for path in paths:
        if not path.exists():
            errors.append(ProcessingError(path, "path does not exist"))
            continue
        if path.is_file():
            skipped += _add_file(path, files, seen)
            continue
        if path.is_symlink() and path.is_dir():
            skipped += 1
            continue
        if not path.is_dir():
            skipped += 1
            continue
        if path.name in settings.ignored_directories:
            skipped += 1
            continue

        if recursive:
            found, ignored = _walk_directory(path, settings, files, seen, errors)
            skipped += ignored
            if found == 0 and ignored == 0:
                skipped += 1
        else:
            try:
                entries = sorted(path.iterdir(), key=lambda item: item.name.casefold())
            except OSError as error:
                errors.append(ProcessingError(path, str(error)))
                continue
            for entry in entries:
                if entry.is_file():
                    skipped += _add_file(entry, files, seen)
                else:
                    skipped += 1

    return DiscoveryResult(tuple(files), tuple(errors), skipped)


def _walk_directory(
    root: Path,
    settings: Settings,
    files: list[Path],
    seen: set[Path],
    errors: list[ProcessingError],
) -> tuple[int, int]:
    found_before = len(files)
    skipped = 0

    def on_error(error: OSError) -> None:
        errors.append(ProcessingError(Path(error.filename or root), str(error)))

    for current, directory_names, file_names in os.walk(root, followlinks=False, onerror=on_error):
        kept_directories: list[str] = []
        for name in directory_names:
            child = Path(current) / name
            if name in settings.ignored_directories or child.is_symlink():
                skipped += 1
            else:
                kept_directories.append(name)
        directory_names[:] = sorted(kept_directories, key=str.casefold)
        for name in sorted(file_names, key=str.casefold):
            skipped += _add_file(Path(current) / name, files, seen)
    return len(files) - found_before, skipped


def _add_file(path: Path, files: list[Path], seen: set[Path]) -> int:
    if _is_sensitive(path) or detect_language(path) is None:
        return 1
    identity = path.resolve()
    if identity in seen:
        return 1
    seen.add(identity)
    files.append(path)
    return 0


def _is_sensitive(path: Path) -> bool:
    lower_name = path.name.casefold()
    return lower_name in _SENSITIVE_NAMES or path.suffix.casefold() in _SENSITIVE_SUFFIXES
