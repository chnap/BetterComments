"""Load and validate BetterComments project configuration."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast


DEFAULT_IGNORED_DIRECTORIES = (
    ".git",
    ".hg",
    ".svn",
    ".github",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "target",
    ".idea",
    ".vscode",
)


class ConfigurationError(ValueError):
    """Raised when a configuration file is invalid."""


@dataclass(frozen=True, slots=True)
class CustomRule:
    match: str
    replacement: str
    case_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class Settings:
    ignored_directories: tuple[str, ...] = DEFAULT_IGNORED_DIRECTORIES
    max_file_size: int = 2_000_000
    max_comment_length: int = 100
    backup_suffix: str = ".bak"
    excluded_comment_patterns: tuple[str, ...] = ()
    rules: tuple[CustomRule, ...] = ()


_SETTING_KEYS = {
    "ignored_directories",
    "max_file_size",
    "max_comment_length",
    "backup_suffix",
    "excluded_comment_patterns",
}


def load_settings(path: Path | None = None) -> Settings:
    config_path = path or Path.cwd() / "bettercomments.toml"
    if not config_path.exists():
        if path is not None:
            raise ConfigurationError(f"configuration file not found: {config_path}")
        return Settings()

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"cannot read {config_path}: {error}") from error

    section_object = raw.get("bettercomments", {})
    if not isinstance(section_object, dict):
        raise ConfigurationError("[bettercomments] must be a table")
    section = cast(dict[str, object], section_object)
    unknown = set(section) - _SETTING_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigurationError(f"unknown configuration option(s): {names}")

    rules_object = raw.get("rules", [])
    if not isinstance(rules_object, list):
        raise ConfigurationError("[[rules]] entries must be an array of tables")
    rules_raw = cast(list[object], rules_object)
    rules = tuple(_parse_rule(rule, index) for index, rule in enumerate(rules_raw, start=1))

    defaults = Settings()
    settings = Settings(
        ignored_directories=_string_tuple(
            section.get("ignored_directories", defaults.ignored_directories),
            "ignored_directories",
        ),
        max_file_size=_integer(section.get("max_file_size", defaults.max_file_size), "max_file_size"),
        max_comment_length=_integer(
            section.get("max_comment_length", defaults.max_comment_length),
            "max_comment_length",
        ),
        backup_suffix=_string(section.get("backup_suffix", defaults.backup_suffix), "backup_suffix"),
        excluded_comment_patterns=_string_tuple(
            section.get("excluded_comment_patterns", defaults.excluded_comment_patterns),
            "excluded_comment_patterns",
        ),
        rules=rules,
    )
    _validate_settings(settings)
    return settings


def _parse_rule(raw: object, index: int) -> CustomRule:
    if not isinstance(raw, dict):
        raise ConfigurationError(f"rule {index} must be a table")
    values = cast(dict[str, object], raw)
    unknown = set(values) - {"match", "replacement", "case_sensitive"}
    if unknown:
        raise ConfigurationError(f"rule {index} has unknown fields: {', '.join(sorted(unknown))}")
    if "match" not in values or "replacement" not in values:
        raise ConfigurationError(f"rule {index} requires match and replacement")
    match = _string(values["match"], f"rule {index} match")
    replacement = _string(values["replacement"], f"rule {index} replacement")
    case_sensitive = values.get("case_sensitive", False)
    if not isinstance(case_sensitive, bool):
        raise ConfigurationError(f"rule {index} case_sensitive must be a boolean")
    rule = CustomRule(match, replacement, case_sensitive)
    if not rule.match.strip() or not rule.replacement.strip():
        raise ConfigurationError(f"rule {index} cannot contain empty text")
    return rule


def _validate_settings(settings: Settings) -> None:
    if settings.max_file_size < 1:
        raise ConfigurationError("max_file_size must be a positive integer")
    if settings.max_comment_length < 20:
        raise ConfigurationError("max_comment_length must be an integer of at least 20")
    if not settings.backup_suffix.startswith(".") or any(character in settings.backup_suffix for character in "/\\"):
        raise ConfigurationError("backup_suffix must be a filename suffix such as .bak")
    for pattern in settings.excluded_comment_patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            raise ConfigurationError(f"invalid excluded-comment pattern {pattern!r}: {error}") from error


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string")
    return value


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"{name} must be an array of strings")
    return tuple(cast(list[str] | tuple[str, ...], value))


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigurationError(f"{name} must be an integer")
    return value
