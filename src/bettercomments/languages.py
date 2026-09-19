"""Language registry and extension-based detection."""

from __future__ import annotations

from pathlib import Path

from .models import LanguageSpec


_COMMENT = frozenset({"comment"})

LANGUAGES: tuple[LanguageSpec, ...] = (
    LanguageSpec("python", "python", (".py", ".pyi"), frozenset(), "#", None),
    LanguageSpec("javascript", "javascript", (".js", ".mjs", ".cjs"), _COMMENT, "//", ("/*", "*/")),
    LanguageSpec("typescript", "typescript", (".ts", ".mts", ".cts"), _COMMENT, "//", ("/*", "*/")),
    LanguageSpec("jsx", "javascript", (".jsx",), _COMMENT, "//", ("/*", "*/")),
    LanguageSpec("tsx", "tsx", (".tsx",), _COMMENT, "//", ("/*", "*/")),
    LanguageSpec("html", "html", (".html", ".htm"), _COMMENT, None, ("<!--", "-->")),
    LanguageSpec("css", "css", (".css",), _COMMENT, None, ("/*", "*/")),
    LanguageSpec("scss", "scss", (".scss",), frozenset({"comment", "js_comment"}), "//", ("/*", "*/")),
    LanguageSpec("c", "c", (".c", ".h"), _COMMENT, "//", ("/*", "*/")),
    LanguageSpec("cpp", "cpp", (".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx"), _COMMENT, "//", ("/*", "*/")),
)

_BY_EXTENSION = {
    extension: language
    for language in LANGUAGES
    for extension in language.extensions
}


def detect_language(path: Path) -> LanguageSpec | None:
    """Return the registered language for a path extension."""
    return _BY_EXTENSION.get(path.suffix.lower())


def supported_extensions() -> frozenset[str]:
    return frozenset(_BY_EXTENSION)
