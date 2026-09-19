from __future__ import annotations

from pathlib import Path

import pytest

from bettercomments.config import ConfigurationError, load_settings


def test_loads_project_rules(tmp_path: Path) -> None:
    config = tmp_path / "bettercomments.toml"
    config.write_text(
        """
[bettercomments]
max_comment_length = 72
excluded_comment_patterns = ["^KEEP:"]

[[rules]]
match = "Texto original"
replacement = "Original text."
""".strip(),
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.max_comment_length == 72
    assert settings.rules[0].replacement == "Original text."


def test_rejects_unknown_configuration_key(tmp_path: Path) -> None:
    config = tmp_path / "bettercomments.toml"
    config.write_text("[bettercomments]\nunknown = true\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="unknown configuration"):
        load_settings(config)


def test_rejects_invalid_exclusion_pattern(tmp_path: Path) -> None:
    config = tmp_path / "bettercomments.toml"
    config.write_text('[bettercomments]\nexcluded_comment_patterns = ["["]\n', encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid excluded-comment"):
        load_settings(config)


def test_rejects_wrong_configuration_value_type(tmp_path: Path) -> None:
    config = tmp_path / "bettercomments.toml"
    config.write_text('[bettercomments]\nignored_directories = "node_modules"\n', encoding="utf-8")
    with pytest.raises(ConfigurationError, match="array of strings"):
        load_settings(config)
