"""Recognize comments that tools or developers may depend on verbatim."""

from __future__ import annotations

import re
from collections.abc import Iterable


_PROTECTED_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for pattern in (
        r"^\s*(?:\*\s*)?(?:TODO|FIXME|HACK|NOTE|WARNING|SECURITY)\b",
        r"\b(?:SPDX-License-Identifier|copyright|all rights reserved|license)\b",
        r"\b(?:generated (?:file|code)|auto-?generated|do not edit)\b",
        r"^\s*(?:\*\s*)?(?:noqa|type:\s*ignore|pyright:|mypy:|pylint:|ruff:|fmt:|isort:)",
        r"^\s*(?:\*\s*)?(?:eslint|prettier|stylelint|tslint|@ts-ignore|@ts-expect-error)\b",
        r"^\s*(?:\*\s*)?(?:coverage:|pragma:|nosec\b|NOLINT\b|IWYU pragma:|GCOVR_EXCL|istanbul\b|c8 ignore|v8 ignore)",
        r"^\s*(?:\*\s*)?(?:[#@]?(?:sourceMappingURL|sourceURL|webpack|vite|cspell:|clang-format)|[@#]__PURE__)",
        r"^\s*(?:\*\s*)?(?:region|endregion)\b",
        r"^\s*!/",
        r"coding[:=]\s*[-\w.]+",
        r"^\s*(?:https?|ftp)://\S+\s*$",
    )
)

_CODE_LIKE = re.compile(
    r"^\s*(?:#include|#define|import\s+\w|from\s+\w+\s+import|const\s+\w|let\s+\w|var\s+\w|"
    r"return\b|if\s*\(|for\s*\(|while\s*\(|class\s+\w|def\s+\w)"
)


def protection_reason(content: str, extra_patterns: Iterable[str] = ()) -> str | None:
    for pattern in _PROTECTED_PATTERNS:
        if pattern.search(content):
            return "protected special comment"
    if _CODE_LIKE.search(content):
        return "commented-out code"
    for pattern_text in extra_patterns:
        if re.search(pattern_text, content):
            return "project exclusion pattern"
    return None
