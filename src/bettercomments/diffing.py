"""Render readable unified diffs for planned source changes."""

from __future__ import annotations

import difflib

from .models import PlannedFile


def unified_diff(plan: PlannedFile) -> str:
    before = plan.original.decode(plan.encoding).splitlines(keepends=True)
    after = plan.updated.decode(plan.encoding).splitlines(keepends=True)
    path = plan.path.as_posix().lstrip("/")
    return "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
