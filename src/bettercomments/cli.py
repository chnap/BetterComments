"""Command-line interface for BetterComments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from . import __version__
from .config import ConfigurationError, Settings, load_settings
from .diffing import unified_diff
from .discovery import discover_paths
from .models import PlannedFile, ProcessingError
from .processor import plan_file
from .writer import WriteError, atomic_write


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bettercomments",
        description="Rewrite recognized source-code comments as concise English.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="source files or directories to process")
    parser.add_argument("-r", "--recursive", action="store_true", help="scan directories recursively")
    parser.add_argument("-n", "--dry-run", action="store_true", help="analyze files without writing changes")
    parser.add_argument("--check", action="store_true", help="exit with status 1 when changes are available")
    parser.add_argument("--diff", action="store_true", help="show a unified diff of proposed changes")
    parser.add_argument("-y", "--yes", action="store_true", help="apply all changes without confirmation")
    parser.add_argument("--interactive", action="store_true", help="confirm each changed file (the default write mode)")
    parser.add_argument("--backup", action="store_true", help="create a backup before each write")
    parser.add_argument("--generate", action="store_true", help="add comments for a small set of recognized patterns")
    parser.add_argument("--config", type=Path, help="read settings from a specific TOML file")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("-v", "--verbose", action="store_true", help="show details for processed files")
    output.add_argument("-q", "--quiet", action="store_true", help="show only errors and requested diffs")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.yes and arguments.interactive:
        parser.error("--yes and --interactive cannot be used together")
    if arguments.check and arguments.yes:
        parser.error("--check and --yes cannot be used together")

    try:
        settings = load_settings(arguments.config)
        return _run(arguments, settings, stdout=sys.stdout, stderr=sys.stderr)
    except ConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted; no pending file was written.", file=sys.stderr)
        return 130


def _run(arguments: argparse.Namespace, settings: Settings, *, stdout: TextIO, stderr: TextIO) -> int:
    discovery = discover_paths(arguments.paths, recursive=arguments.recursive, settings=settings)
    errors = list(discovery.errors)
    plans: list[PlannedFile] = []

    for path in discovery.files:
        result = plan_file(path, settings, generate=arguments.generate)
        if isinstance(result, ProcessingError):
            errors.append(result)
        elif result.updated != result.original:
            plans.append(result)
        elif arguments.verbose:
            print(f"unchanged: {path}", file=stdout)

    for error in errors:
        print(f"error: {error.path}: {error.message}", file=stderr)

    if arguments.diff:
        for plan in plans:
            print(unified_diff(plan), end="", file=stdout)

    change_count = sum(len(plan.replacements) for plan in plans)
    if arguments.check:
        if not arguments.quiet:
            _print_summary(stdout, len(discovery.files), len(plans), change_count, 0, len(errors), "check")
        return 3 if errors else (1 if plans else 0)

    if arguments.dry_run:
        if not arguments.quiet:
            _print_summary(stdout, len(discovery.files), len(plans), change_count, 0, len(errors), "dry run")
        return 3 if errors else 0

    written = 0
    declined = 0
    for plan in plans:
        if not arguments.yes:
            if not sys.stdin.isatty():
                print(
                    "error: confirmation requires a terminal; use --yes, --dry-run, or --check",
                    file=stderr,
                )
                return 3
            if not _confirm(plan, stdout=stdout):
                declined += 1
                continue
        try:
            backup_path = atomic_write(
                plan.path,
                plan.updated,
                backup=arguments.backup,
                backup_suffix=settings.backup_suffix,
            )
        except WriteError as error:
            errors.append(ProcessingError(plan.path, str(error)))
            print(f"error: {error}", file=stderr)
            continue
        written += 1
        if arguments.verbose:
            detail = f" ({len(plan.replacements)} change(s))"
            print(f"updated: {plan.path}{detail}", file=stdout)
            if backup_path is not None:
                print(f"backup: {backup_path}", file=stdout)

    if not arguments.quiet:
        _print_summary(stdout, len(discovery.files), len(plans), change_count, written, len(errors), "write")
        if declined:
            print(f"Declined files: {declined}.", file=stdout)
    return 3 if errors else 0


def _confirm(plan: PlannedFile, *, stdout: TextIO) -> bool:
    while True:
        answer = input(f"Apply {len(plan.replacements)} change(s) to {plan.path}? [y/N/d] ").strip().casefold()
        if answer in {"y", "yes"}:
            return True
        if answer in {"d", "diff"}:
            print(unified_diff(plan), end="", file=stdout)
            continue
        return False


def _print_summary(
    stream: TextIO,
    scanned: int,
    changed_files: int,
    changes: int,
    written: int,
    errors: int,
    mode: str,
) -> None:
    print(
        f"BetterComments {mode}: {scanned} supported file(s), {changed_files} changed file(s), "
        f"{changes} comment change(s), {written} file(s) written, {errors} error(s).",
        file=stream,
    )
