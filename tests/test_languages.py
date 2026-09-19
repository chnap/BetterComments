from __future__ import annotations

from pathlib import Path

import pytest

from bettercomments.languages import detect_language, supported_extensions


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("main.py", "python"),
        ("main.js", "javascript"),
        ("main.ts", "typescript"),
        ("view.jsx", "jsx"),
        ("view.tsx", "tsx"),
        ("index.html", "html"),
        ("style.css", "css"),
        ("style.scss", "scss"),
        ("main.c", "c"),
        ("main.cpp", "cpp"),
    ],
)
def test_detects_supported_languages(filename: str, expected: str) -> None:
    language = detect_language(Path(filename))
    assert language is not None
    assert language.name == expected


def test_rejects_unsupported_extension() -> None:
    assert detect_language(Path("notes.txt")) is None
    assert ".py" in supported_extensions()
