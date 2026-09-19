"""Verify that rewrites leave functional source tokens unchanged."""

from __future__ import annotations

import ast
import io
import tokenize
from copy import deepcopy
from typing import cast

from .models import LanguageSpec
from .source import SourceDocument


class SafetyValidationError(ValueError):
    """Raised when a planned rewrite changes functional source structure."""


def validate_functional_source(
    original: SourceDocument,
    updated: SourceDocument,
    language: LanguageSpec,
) -> None:
    if language.name == "python":
        before = _python_fingerprint(original.text)
        after = _python_fingerprint(updated.text)
    else:
        before = _tree_sitter_fingerprint(original.data, language)
        after = _tree_sitter_fingerprint(updated.data, language)
    if before != after:
        raise SafetyValidationError("functional source changed during comment rewriting")


def _python_fingerprint(source: str) -> object:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return _python_token_fingerprint(source)
    normalized = deepcopy(tree)
    for node in ast.walk(normalized):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.body and isinstance(node.body[0], ast.Expr):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                value.value = "<docstring>"
    return ast.dump(normalized, include_attributes=False)


def _python_token_fingerprint(source: str) -> tuple[tuple[int, str], ...]:
    ignored = {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER}
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    fingerprint: list[tuple[int, str]] = []
    try:
        for token in tokens:
            if token.type not in ignored:
                fingerprint.append((token.type, token.string))
    except (tokenize.TokenError, IndentationError):
        pass
    return tuple(fingerprint)


def _tree_sitter_fingerprint(data: bytes, language: LanguageSpec) -> tuple[tuple[str, bytes], ...]:
    from tree_sitter_language_pack import SupportedLanguage, get_parser

    tree = get_parser(cast(SupportedLanguage, language.parser_name)).parse(data)
    tokens: list[tuple[str, bytes]] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in language.comment_node_types:
            continue
        if node.child_count == 0:
            tokens.append((node.type, data[node.start_byte : node.end_byte]))
        else:
            stack.extend(reversed(node.children))
    return tuple(tokens)
