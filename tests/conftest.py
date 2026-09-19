from __future__ import annotations

from pathlib import Path

from bettercomments.config import Settings
from bettercomments.models import PlannedFile, ProcessingError
from bettercomments.processor import plan_file


def plan_source(
    tmp_path: Path,
    name: str,
    source: str,
    *,
    settings: Settings | None = None,
    generate: bool = False,
    newline: str | None = None,
) -> PlannedFile:
    path = tmp_path / name
    data = source.encode("utf-8")
    if newline == "crlf":
        data = data.replace(b"\n", b"\r\n")
    path.write_bytes(data)
    result = plan_file(path, settings or Settings(), generate=generate)
    assert not isinstance(result, ProcessingError), result
    return result
