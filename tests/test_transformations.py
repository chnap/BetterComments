from __future__ import annotations

import ast

import pytest

from bettercomments.config import CustomRule, Settings
from bettercomments.models import PlannedFile

from conftest import plan_source


def updated_text(plan: PlannedFile) -> str:
    return plan.updated.decode(plan.encoding)


def test_translates_spanish_python_comment(tmp_path) -> None:
    plan = plan_source(
        tmp_path,
        "sample.py",
        "# Esta función comprueba si el usuario tiene permisos suficientes para continuar con la operación solicitada.\nif user.has_permission():\n    execute()\n",
    )
    assert updated_text(plan).startswith("# Check user permissions.\n")
    assert ast.dump(ast.parse(plan.original)) == ast.dump(ast.parse(plan.updated))


def test_translates_french_javascript_block_and_preserves_strings(tmp_path) -> None:
    source = (
        'const url = "https://example.com/api";\n'
        "/*\n * Cette fonction vérifie si l'utilisateur possède les permissions\n"
        " * nécessaires avant de continuer avec l'opération demandée.\n */\n"
        "if (user.hasPermission()) execute();\n"
    )
    plan = plan_source(tmp_path, "sample.js", source)
    result = updated_text(plan)
    assert 'const url = "https://example.com/api";' in result
    assert "// Check user permissions." in result
    assert result.count("\n") == source.count("\n")


def test_condenses_verbose_english(tmp_path) -> None:
    source = "// This function is responsible for iterating over all users and checking whether each user is active before adding them to the resulting array.\nconst active = users.filter(isActive);\n"
    plan = plan_source(tmp_path, "sample.js", source)
    assert updated_text(plan).startswith("// Add active users to the result.\n")


def test_collapses_multiline_comment_and_preserves_line_count(tmp_path) -> None:
    source = "/*\n * Iterate over every item returned by the API.\n * Check whether the item is currently active.\n * Add active items to the result array.\n */\nrun();\n"
    plan = plan_source(tmp_path, "sample.cpp", source)
    result = updated_text(plan)
    assert result.startswith("// Add active API items to the result.\n\n\n\n")
    assert result.count("\n") == source.count("\n")


def test_rewrites_css_without_invalid_line_comment(tmp_path) -> None:
    plan = plan_source(tmp_path, "style.css", "/* Configuración principal de la página. */\nbody {}\n")
    assert updated_text(plan).startswith("/* Main page configuration. */")


def test_rewrites_inline_comment_conservatively(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.py", "result = calculate()  # Guarda el resultado.\n")
    assert updated_text(plan) == "result = calculate()  # Store the result.\n"


@pytest.mark.parametrize(
    "comment",
    [
        "# TODO: implement caching",
        "# SPDX-License-Identifier: MIT",
        "# Generated file; do not edit",
        "# type: ignore",
        "# noqa: F401",
        "# coverage: ignore",
    ],
)
def test_preserves_special_comments(tmp_path, comment: str) -> None:
    source = f"value = 1  {comment}\n"
    plan = plan_source(tmp_path, "sample.py", source)
    assert plan.updated == plan.original


def test_project_rule_is_exact_and_offline(tmp_path) -> None:
    settings = Settings(rules=(CustomRule("Comprueba la sesión activa", "Check the active session."),))
    plan = plan_source(tmp_path, "sample.py", "# Comprueba la sesión activa\n", settings=settings)
    assert updated_text(plan) == "# Check the active session.\n"


def test_preserves_unknown_foreign_comment(tmp_path) -> None:
    source = "# Explicación desconocida del sistema.\n"
    plan = plan_source(tmp_path, "sample.py", source)
    assert plan.updated == plan.original


def test_preserves_crlf(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.py", "# Comprueba los permisos.\nvalue = 1\n", newline="crlf")
    assert plan.updated == b"# Check permissions.\r\nvalue = 1\r\n"


def test_handles_invalid_syntax_when_token_ranges_are_safe(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.py", "# Comprueba los permisos.\nvalue = (\n")
    assert plan.updated.startswith(b"# Check permissions.\n")


def test_rewrites_documentation_conservatively(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.js", "/** Vérifie les permissions. */\nfunction run() {}\n")
    assert updated_text(plan).startswith("/** Check permissions. */")


def test_rewrites_unicode_python_docstring_with_exact_offsets(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.py", '"""Vérifie les permissions."""\nvalue = "café"\n')
    assert updated_text(plan) == '"""Check permissions."""\nvalue = "café"\n'


def test_does_not_convert_jsx_block_to_line_comment(tmp_path) -> None:
    plan = plan_source(tmp_path, "sample.jsx", "const view = <div>{/* Vérifie les permissions. */}</div>;\n")
    assert updated_text(plan) == "const view = <div>{/* Check permissions. */}</div>;\n"


def test_preserves_multiline_tool_directive(tmp_path) -> None:
    source = "/*\n * TODO: Comprueba los permisos.\n */\nrun();\n"
    plan = plan_source(tmp_path, "sample.cpp", source)
    assert plan.updated == plan.original


def test_preserves_source_map_directive(tmp_path) -> None:
    source = "//# sourceMappingURL=app.js.map\n"
    plan = plan_source(tmp_path, "sample.js", source)
    assert plan.updated == plan.original


def test_adjacent_unrelated_comments_are_rewritten_independently(tmp_path) -> None:
    source = "# Comprueba los permisos.\n# Guarda el resultado.\nvalue = 1\n"
    plan = plan_source(tmp_path, "sample.py", source)
    assert updated_text(plan) == "# Check permissions.\n# Store the result.\nvalue = 1\n"


@pytest.mark.parametrize(
    ("filename", "source", "expected_comment"),
    [
        ("sample.ts", "// Vérifie les permissions.\nconst value: number = 1;\n", "// Check permissions."),
        ("sample.tsx", "const view = <div>{/* Vérifie les permissions. */}</div>;\n", "/* Check permissions. */"),
        ("sample.html", "<!-- Vérifie les permissions. -->\n<main></main>\n", "<!-- Check permissions. -->"),
        ("sample.scss", "// Vérifie les permissions.\n$value: 1;\n", "// Check permissions."),
        ("sample.c", "/* Vérifie les permissions. */\nint value = 1;\n", "// Check permissions."),
    ],
)
def test_rewrites_each_tree_sitter_language_family(
    tmp_path,
    filename: str,
    source: str,
    expected_comment: str,
) -> None:
    plan = plan_source(tmp_path, filename, source)
    assert expected_comment in updated_text(plan)
