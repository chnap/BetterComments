from __future__ import annotations

from pathlib import Path

import pytest

from bettercomments.languages import detect_language
from bettercomments.parser import extract_comments
from bettercomments.source import SourceDocument


@pytest.mark.parametrize(
    ("filename", "source", "expected"),
    [
        ("sample.py", 'value = "# not a comment"\n# Comprueba los permisos.\n', [" Comprueba los permisos."]),
        ("sample.js", 'const url = "https://example.com/api";\n// Vérifie les permissions.\n', [" Vérifie les permissions."]),
        ("sample.ts", 'const text: string = "hello // world";\n/* Verifica i permessi. */\n', [" Verifica i permessi. "]),
        ("sample.jsx", 'const view = <div>{"/* text */"}{/* Check permissions. */}</div>;\n', [" Check permissions. "]),
        ("sample.tsx", 'const view: JSX.Element = <div>{/* Check permissions. */}</div>;\n', [" Check permissions. "]),
        ("sample.html", '<a href="https://example.com">Link</a><!-- Vérifie les permissions. -->\n', [" Vérifie les permissions. "]),
        ("sample.css", '.hero { background: url("https://example.com/a.png"); } /* Configuración principal de la página. */\n', [" Configuración principal de la página. "]),
        ("sample.scss", '$value: "// text"; // Verifica as permissões.\n', [" Verifica as permissões."]),
        ("sample.c", 'const char *url = "https://example.com"; /* Check permissions. */\n', [" Check permissions. "]),
        ("sample.cpp", 'std::string value = "// text"; // Check permissions.\n', [" Check permissions."]),
    ],
)
def test_extracts_only_real_comments(filename: str, source: str, expected: list[str]) -> None:
    language = detect_language(Path(filename))
    assert language is not None
    document = SourceDocument.decode(source.encode(), python_source=language.name == "python")
    comments = extract_comments(document, language)
    assert [comment.content for comment in comments] == expected


def test_extracts_python_docstrings_but_not_ordinary_strings() -> None:
    source = '"""Comprueba los permisos."""\nvalue = "Comprueba los permisos."\n'
    language = detect_language(Path("sample.py"))
    assert language is not None
    document = SourceDocument.decode(source.encode(), python_source=True)
    comments = extract_comments(document, language)
    assert len(comments) == 1
    assert comments[0].content == "Comprueba los permisos."


def test_escaped_quotes_do_not_create_fake_javascript_comments() -> None:
    source = 'const value = "quoted \\\"// text\\\""; // Check permissions.\n'
    language = detect_language(Path("sample.js"))
    assert language is not None
    document = SourceDocument.decode(source.encode(), python_source=False)
    comments = extract_comments(document, language)
    assert [comment.content for comment in comments] == [" Check permissions."]
