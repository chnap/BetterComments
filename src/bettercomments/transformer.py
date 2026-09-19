"""Classify, rewrite, and render extracted comments safely."""

from __future__ import annotations

import re

from .config import Settings
from .models import CommentKind, CommentSpan, Replacement
from .protection import protection_reason
from .rules import apply_rules, collapse_comment, is_probably_english, normalize_sentence
from .source import SourceDocument


_NEWLINES = re.compile(r"\r\n|\r|\n")


def plan_replacements(
    document: SourceDocument,
    comments: tuple[CommentSpan, ...],
    settings: Settings,
) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for group in _line_comment_groups(document, comments):
        if len(group) == 1:
            replacement = _plan_comment(document, group[0], settings)
            if replacement is not None:
                replacements.append(replacement)
            continue

        if any(protection_reason(comment.content, settings.excluded_comment_patterns) for comment in group):
            replacements.extend(
                replacement
                for comment in group
                if (replacement := _plan_comment(document, comment, settings)) is not None
            )
            continue

        merged = _merge_group(document, list(group))
        replacement = _plan_comment(document, merged, settings)
        if replacement is not None:
            replacements.append(replacement)
            continue
        replacements.extend(
            replacement
            for comment in group
            if (replacement := _plan_comment(document, comment, settings)) is not None
        )
    return tuple(replacements)


def _plan_comment(document: SourceDocument, comment: CommentSpan, settings: Settings) -> Replacement | None:
    protected = protection_reason(comment.content, settings.excluded_comment_patterns)
    if protected is not None:
        return None

    conservative = comment.inline or comment.kind in {CommentKind.DOCUMENTATION, CommentKind.DOCSTRING}
    result = apply_rules(comment.content, settings.rules, allow_generic=not conservative)
    if result is None:
        collapsed = collapse_comment(comment.content)
        if conservative or "\n" not in comment.content or not is_probably_english(collapsed):
            return None
        if len(collapsed) > settings.max_comment_length:
            return None
        rewritten = normalize_sentence(collapsed)
        reason = "collapse multiline comment"
    else:
        rewritten = result.text
        reason = result.reason

    if len(rewritten) > settings.max_comment_length:
        return None
    replacement_text = _render(comment, rewritten)
    replacement_bytes = replacement_text.encode(document.encoding)
    original_bytes = document.data[comment.start : comment.end]
    if replacement_bytes == original_bytes:
        return None
    return Replacement(
        start=comment.start,
        end=comment.end,
        original=original_bytes,
        replacement=replacement_bytes,
        original_comment=collapse_comment(comment.content),
        rewritten_comment=rewritten,
        reason=reason,
    )


def apply_replacements(data: bytes, replacements: tuple[Replacement, ...]) -> bytes:
    previous_start = len(data) + 1
    updated = data
    for replacement in sorted(replacements, key=lambda item: item.start, reverse=True):
        if replacement.end > previous_start:
            raise ValueError("overlapping comment replacements")
        if data[replacement.start : replacement.end] != replacement.original:
            raise ValueError("source changed while replacements were planned")
        updated = updated[: replacement.start] + replacement.replacement + updated[replacement.end :]
        previous_start = replacement.start
    return updated


def _render(comment: CommentSpan, rewritten: str) -> str:
    newline_padding = "".join(_NEWLINES.findall(comment.raw))
    if comment.kind == CommentKind.DOCSTRING:
        if comment.quote in rewritten:
            return comment.raw
        return f"{comment.quote_prefix}{comment.quote}{rewritten}{comment.quote}{newline_padding}"

    if comment.kind == CommentKind.DOCUMENTATION:
        if comment.raw.startswith("///"):
            return f"/// {rewritten}{newline_padding}"
        if comment.raw.startswith("//!"):
            return f"//! {rewritten}{newline_padding}"
        return f"/** {rewritten} */{newline_padding}"

    may_convert_to_line = (
        comment.can_use_line_comment
        and comment.line_prefix is not None
        and not comment.inline
        and not comment.trailing_code
    )
    if comment.kind == CommentKind.LINE or may_convert_to_line:
        return f"{comment.line_prefix} {rewritten}{newline_padding}"

    if comment.block_delimiters is None:
        return comment.raw
    opening, closing = comment.block_delimiters
    if closing in rewritten:
        return comment.raw
    return f"{opening} {rewritten} {closing}{newline_padding}"


def _line_comment_groups(
    document: SourceDocument,
    comments: tuple[CommentSpan, ...],
) -> tuple[tuple[CommentSpan, ...], ...]:
    if not comments:
        return ()
    grouped: list[tuple[CommentSpan, ...]] = []
    index = 0
    while index < len(comments):
        first = comments[index]
        members = [first]
        while index + len(members) < len(comments):
            candidate = comments[index + len(members)]
            previous = members[-1]
            if not _can_group(document, previous, candidate):
                break
            members.append(candidate)
        grouped.append(tuple(members))
        index += len(members)
    return tuple(grouped)


def _can_group(document: SourceDocument, left: CommentSpan, right: CommentSpan) -> bool:
    if left.kind != right.kind or left.kind not in {CommentKind.LINE, CommentKind.DOCUMENTATION}:
        return False
    if left.language != right.language or left.inline or right.inline or left.trailing_code or right.trailing_code:
        return False
    if _indentation(document, left) != _indentation(document, right):
        return False
    between = document.data[left.end : right.start]
    return re.fullmatch(rb"(?:\r\n|\r|\n)[ \t]*", between) is not None


def _indentation(document: SourceDocument, comment: CommentSpan) -> bytes:
    line_start = document.data.rfind(b"\n", 0, comment.start) + 1
    return document.data[line_start : comment.start]


def _merge_group(document: SourceDocument, comments: list[CommentSpan]) -> CommentSpan:
    first, last = comments[0], comments[-1]
    return CommentSpan(
        start=first.start,
        end=last.end,
        content="\n".join(comment.content for comment in comments),
        raw=document.decode_slice(first.start, last.end),
        kind=first.kind,
        language=first.language,
        inline=False,
        trailing_code=False,
        can_use_line_comment=all(comment.can_use_line_comment for comment in comments),
        line_prefix=first.line_prefix,
        block_delimiters=first.block_delimiters,
        quote_prefix=first.quote_prefix,
        quote=first.quote,
    )
