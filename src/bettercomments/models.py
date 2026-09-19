"""Shared immutable models for parsing and rewriting comments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CommentKind(StrEnum):
    LINE = "line"
    BLOCK = "block"
    DOCUMENTATION = "documentation"
    DOCSTRING = "docstring"


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    name: str
    parser_name: str
    extensions: tuple[str, ...]
    comment_node_types: frozenset[str]
    line_prefix: str | None
    block_delimiters: tuple[str, str] | None


@dataclass(frozen=True, slots=True)
class CommentSpan:
    start: int
    end: int
    content: str
    raw: str
    kind: CommentKind
    language: str
    inline: bool
    trailing_code: bool
    can_use_line_comment: bool
    line_prefix: str | None
    block_delimiters: tuple[str, str] | None
    quote_prefix: str = ""
    quote: str = ""


@dataclass(frozen=True, slots=True)
class Replacement:
    start: int
    end: int
    original: bytes
    replacement: bytes
    original_comment: str
    rewritten_comment: str
    reason: str


@dataclass(frozen=True, slots=True)
class PlannedFile:
    path: Path
    original: bytes
    updated: bytes
    replacements: tuple[Replacement, ...]
    encoding: str


@dataclass(frozen=True, slots=True)
class ProcessingError:
    path: Path
    message: str

