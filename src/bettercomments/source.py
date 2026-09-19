"""Decode source files while retaining exact byte offsets."""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass


class SourceDecodingError(ValueError):
    """Raised when a source file cannot be decoded safely."""


@dataclass(frozen=True, slots=True)
class SourceDocument:
    data: bytes
    text: str
    encoding: str
    bom_length: int
    char_to_byte: tuple[int, ...]
    line_starts: tuple[int, ...]

    @classmethod
    def decode(cls, data: bytes, *, python_source: bool) -> "SourceDocument":
        if b"\x00" in data[:8192]:
            raise SourceDecodingError("binary data detected")

        encoding, bom_length = _detect_encoding(data, python_source=python_source)
        try:
            text = data.decode("utf-8-sig" if bom_length else encoding)
        except UnicodeDecodeError as error:
            raise SourceDecodingError(f"cannot decode as {encoding}: {error}") from error

        offsets = [bom_length]
        current = bom_length
        for character in text:
            current += len(character.encode(encoding))
            offsets.append(current)

        starts = [0]
        starts.extend(index + 1 for index, character in enumerate(text) if character == "\n")
        return cls(data, text, encoding, bom_length, tuple(offsets), tuple(starts))

    def position_to_byte(self, row: int, column: int) -> int:
        try:
            character_offset = self.line_starts[row - 1] + column
            return self.char_to_byte[character_offset]
        except IndexError as error:
            raise SourceDecodingError(f"invalid source position {row}:{column}") from error

    def ast_position_to_byte(self, row: int, utf8_column: int) -> int:
        try:
            line_start = self.line_starts[row - 1]
            line_end = self.text.find("\n", line_start)
            if line_end < 0:
                line_end = len(self.text)
            line = self.text[line_start:line_end]
            prefix = line.encode("utf-8")[:utf8_column].decode("utf-8")
            return self.char_to_byte[line_start + len(prefix)]
        except (IndexError, UnicodeDecodeError) as error:
            raise SourceDecodingError(f"invalid AST source position {row}:{utf8_column}") from error

    def decode_slice(self, start: int, end: int) -> str:
        return self.data[start:end].decode(self.encoding)


def _detect_encoding(data: bytes, *, python_source: bool) -> tuple[str, int]:
    if not python_source:
        return ("utf-8", 3) if data.startswith(b"\xef\xbb\xbf") else ("utf-8", 0)

    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    except SyntaxError as error:
        raise SourceDecodingError(str(error)) from error
    bom_length = 3 if data.startswith(b"\xef\xbb\xbf") else 0
    return encoding.removesuffix("-sig"), bom_length
