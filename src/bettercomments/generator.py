"""Generate a small set of conservative comments when explicitly requested."""

from __future__ import annotations

import ast

from .models import Replacement
from .source import SourceDocument


def plan_generated_comments(document: SourceDocument, language: str) -> tuple[Replacement, ...]:
    if language != "python":
        return ()
    try:
        tree = ast.parse(document.text)
    except (SyntaxError, ValueError):
        return ()

    line_ending = "\r\n" if b"\r\n" in document.data else "\n"
    generated: list[Replacement] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Pass):
            continue
        statement = node.body[0]
        start = document.position_to_byte(statement.lineno, statement.col_offset)
        line_start = document.data.rfind(b"\n", 0, start) + 1
        indentation = document.data[line_start:start].decode(document.encoding)
        exception_name = _safe_exception_name(node.type)
        if exception_name is None:
            continue
        comment = f"# Intentionally ignore {exception_name}.{line_ending}{indentation}"
        generated.append(
            Replacement(
                start=start,
                end=start,
                original=b"",
                replacement=comment.encode(document.encoding),
                original_comment="",
                rewritten_comment=f"Intentionally ignore {exception_name}.",
                reason="opt-in empty-handler rule",
            )
        )
    return tuple(generated)


def _safe_exception_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name) and node.id.endswith(("Error", "Exception")):
        return node.id
    if isinstance(node, ast.Attribute) and node.attr.endswith(("Error", "Exception")):
        return node.attr
    return None

