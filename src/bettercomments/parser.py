"""Extract comments with language-aware tokenizers and parsers."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterable
from typing import cast

from .models import CommentKind, CommentSpan, LanguageSpec
from .source import SourceDocument


class CommentParseError(ValueError):
    """Raised when comments cannot be identified safely."""


_TRIPLE_QUOTED = re.compile(r"(?is)^([rub]*)(\"\"\"|''')")


def extract_comments(document: SourceDocument, language: LanguageSpec) -> tuple[CommentSpan, ...]:
    if language.name == "python":
        return _extract_python(document, language)
    return _extract_tree_sitter(document, language)


def _extract_python(document: SourceDocument, language: LanguageSpec) -> tuple[CommentSpan, ...]:
    tokens: list[tokenize.TokenInfo] = []
    try:
        tokens.extend(tokenize.generate_tokens(io.StringIO(document.text).readline))
    except (tokenize.TokenError, IndentationError) as error:
        # Tokens emitted before an incomplete construct retain authoritative ranges.
        if not tokens:
            raise CommentParseError(f"tokenization failed: {error}") from error

    comments: list[CommentSpan] = []
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        start = document.position_to_byte(*token.start)
        end = document.position_to_byte(*token.end)
        comments.append(
            _make_span(
                document,
                language,
                start,
                end,
                token.string,
                kind=CommentKind.LINE,
                can_use_line_comment=True,
            )
        )

    comments.extend(_extract_docstrings(document, language, tokens))
    comments.sort(key=lambda comment: comment.start)
    return tuple(comments)


def _extract_docstrings(
    document: SourceDocument,
    language: LanguageSpec,
    tokens: Iterable[tokenize.TokenInfo],
) -> list[CommentSpan]:
    try:
        tree = ast.parse(document.text)
    except (SyntaxError, ValueError):
        return []

    string_tokens = {
        (
            document.position_to_byte(*token.start),
            document.position_to_byte(*token.end),
        ): token
        for token in tokens
        if token.type == tokenize.STRING and _TRIPLE_QUOTED.match(token.string)
    }
    spans: list[CommentSpan] = []
    for expression in _docstring_expressions(tree):
        if expression.end_lineno is None or expression.end_col_offset is None:
            continue
        key = (
            document.ast_position_to_byte(expression.lineno, expression.col_offset),
            document.ast_position_to_byte(expression.end_lineno, expression.end_col_offset),
        )
        token = string_tokens.get(key)
        if token is None:
            continue
        match = _TRIPLE_QUOTED.match(token.string)
        if match is None:
            continue
        prefix, quote = match.groups()
        if not token.string.endswith(quote):
            continue
        start = document.position_to_byte(*token.start)
        end = document.position_to_byte(*token.end)
        raw = document.decode_slice(start, end)
        spans.append(
            CommentSpan(
                start=start,
                end=end,
                content=raw[len(prefix) + len(quote) : -len(quote)],
                raw=raw,
                kind=CommentKind.DOCSTRING,
                language=language.name,
                inline=False,
                trailing_code=False,
                can_use_line_comment=False,
                line_prefix=None,
                block_delimiters=None,
                quote_prefix=prefix,
                quote=quote,
            )
        )
    return spans


def _docstring_expressions(tree: ast.AST) -> Iterable[ast.Constant]:
    nodes = (node for node in ast.walk(tree) if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)))
    for node in nodes:
        body = node.body
        if not body or not isinstance(body[0], ast.Expr):
            continue
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            yield value


def _extract_tree_sitter(document: SourceDocument, language: LanguageSpec) -> tuple[CommentSpan, ...]:
    try:
        from tree_sitter_language_pack import SupportedLanguage, get_parser
    except ImportError as error:
        raise CommentParseError("tree-sitter-language-pack is not installed") from error

    try:
        parser = get_parser(cast(SupportedLanguage, language.parser_name))
        tree = parser.parse(document.data)
    except (LookupError, TypeError, ValueError) as error:
        raise CommentParseError(f"Tree-sitter parser failed: {error}") from error

    comments: list[CommentSpan] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in language.comment_node_types:
            raw = document.decode_slice(node.start_byte, node.end_byte)
            kind = _tree_sitter_kind(raw)
            comments.append(
                _make_span(
                    document,
                    language,
                    node.start_byte,
                    node.end_byte,
                    raw,
                    kind=kind,
                    can_use_line_comment=_line_conversion_is_safe(node, language),
                )
            )
            continue
        stack.extend(reversed(node.children))

    comments.sort(key=lambda comment: comment.start)
    return tuple(comments)


def _tree_sitter_kind(raw: str) -> CommentKind:
    if raw.startswith(("/**", "///", "//!")):
        return CommentKind.DOCUMENTATION
    if raw.startswith("//"):
        return CommentKind.LINE
    return CommentKind.BLOCK


def _line_conversion_is_safe(node: object, language: LanguageSpec) -> bool:
    if language.line_prefix is None:
        return False
    parent = getattr(node, "parent", None)
    while parent is not None:
        if str(getattr(parent, "type", "")).startswith("jsx_"):
            return False
        parent = getattr(parent, "parent", None)
    return True


def _make_span(
    document: SourceDocument,
    language: LanguageSpec,
    start: int,
    end: int,
    raw: str,
    *,
    kind: CommentKind,
    can_use_line_comment: bool,
) -> CommentSpan:
    line_start = document.data.rfind(b"\n", 0, start) + 1
    line_end_position = document.data.find(b"\n", end)
    line_end = len(document.data) if line_end_position < 0 else line_end_position
    before = document.data[line_start:start].strip()
    after = document.data[end:line_end].strip(b" \t\r")
    return CommentSpan(
        start=start,
        end=end,
        content=_comment_content(raw, kind, language),
        raw=raw,
        kind=kind,
        language=language.name,
        inline=bool(before),
        trailing_code=bool(after),
        can_use_line_comment=can_use_line_comment,
        line_prefix=language.line_prefix,
        block_delimiters=language.block_delimiters,
    )


def _comment_content(raw: str, kind: CommentKind, language: LanguageSpec) -> str:
    if kind in {CommentKind.LINE, CommentKind.DOCUMENTATION} and raw.startswith("//"):
        prefix_length = 3 if raw.startswith(("///", "//!")) else 2
        return raw[prefix_length:]
    if language.name == "python" and raw.startswith("#"):
        return raw[1:]
    if raw.startswith("<!--") and raw.endswith("-->"):
        return raw[4:-3]
    if raw.startswith("/*") and raw.endswith("*/"):
        prefix_length = 3 if raw.startswith("/**") else 2
        return raw[prefix_length:-2]
    return raw
