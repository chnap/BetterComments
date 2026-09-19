"""Coordinate decoding, parsing, rewriting, generation, and validation."""

from __future__ import annotations

from pathlib import Path

from .config import Settings
from .generator import plan_generated_comments
from .languages import detect_language
from .models import PlannedFile, ProcessingError, Replacement
from .parser import CommentParseError, extract_comments
from .source import SourceDecodingError, SourceDocument
from .transformer import apply_replacements, plan_replacements
from .validation import SafetyValidationError, validate_functional_source


def plan_file(path: Path, settings: Settings, *, generate: bool) -> PlannedFile | ProcessingError:
    language = detect_language(path)
    if language is None:
        return ProcessingError(path, "unsupported file type")
    try:
        if path.stat().st_size > settings.max_file_size:
            return ProcessingError(path, f"file exceeds {settings.max_file_size} bytes")
        original = path.read_bytes()
        document = SourceDocument.decode(original, python_source=language.name == "python")
        comments = extract_comments(document, language)
        replacements = list(plan_replacements(document, comments, settings))
        if generate:
            replacements.extend(plan_generated_comments(document, language.name))
        replacements_tuple = _validated_order(replacements)
        updated = apply_replacements(original, replacements_tuple)
        if updated != original:
            updated_document = SourceDocument.decode(updated, python_source=language.name == "python")
            validate_functional_source(document, updated_document, language)
        return PlannedFile(path, original, updated, replacements_tuple, document.encoding)
    except (OSError, SourceDecodingError, CommentParseError, SafetyValidationError, ValueError) as error:
        return ProcessingError(path, str(error))


def _validated_order(replacements: list[Replacement]) -> tuple[Replacement, ...]:
    ordered = tuple(sorted(replacements, key=lambda item: item.start))
    previous_end = -1
    for replacement in ordered:
        if replacement.start < previous_end:
            raise ValueError("generated comment overlaps a rewritten comment")
        previous_end = replacement.end
    return ordered

