# BetterComments

BetterComments is an offline Python CLI that safely rewrites recognized source-code comments as concise, consistent English.

## Why BetterComments?

Generated and collaboratively written code often accumulates verbose comments or comments written in the language of the original conversation. BetterComments applies explicit, reviewable rules to normalize those comments without sending source code to an AI service.

## Features

- Parser-backed comment extraction that does not confuse comment-like text inside strings with comments.
- Deterministic rules for common Spanish, French, German, Italian, Portuguese, and verbose English phrases.
- Exact project-specific rules in `bettercomments.toml`.
- Unified diffs, dry runs, CI checks, interactive confirmation, and optional backups.
- Atomic writes and a functional-token safety check before any file is changed.
- Protection for licenses, generated-file markers, TODOs, linters, type checkers, and other machine-readable comments.
- Explicitly opt-in, narrowly scoped comment generation.

## Before / After

Before:

```python
# Esta función comprueba si el usuario tiene permisos suficientes para continuar con la operación solicitada.
if user.has_permission():
    execute()
```

After:

```python
# Check user permissions.
if user.has_permission():
    execute()
```

Multiline comments retain their original newline count so line-number-sensitive behavior stays stable, but only the first line remains a comment.

## Installation

BetterComments requires Python 3.11 or newer.

```bash
python -m pip install .
```

For development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

The package installs the `bettercomments` command. A checkout can also be run directly with `python bettercomments.py`.

## Usage

Preview one file without writing it:

```bash
bettercomments example.py --dry-run --diff
```

Scan a directory recursively and confirm each changed file:

```bash
bettercomments src/ --recursive --diff
```

Apply all proposed changes without prompts and create backups:

```bash
bettercomments src/ --recursive --yes --backup
```

Use BetterComments in CI:

```bash
bettercomments . --recursive --check
```

`--check` returns exit status `1` when changes are available. Processing errors return `3`; invalid CLI usage or configuration returns `2`.

## Supported Languages

Version 0.1 supports:

- Python and Python stubs
- JavaScript, TypeScript, JSX, and TSX
- HTML
- CSS and SCSS
- C and C++

Support means parser-backed comment detection and safe replacement. The built-in translation vocabulary is intentionally curated rather than a general-purpose translation system.

## How It Works

BetterComments discovers supported files, decodes each file, extracts comments with Python's tokenizer or Tree-sitter, protects special comments, applies deterministic rewrite rules, validates functional tokens, and writes approved results atomically.

Comment extraction and transformation are separate. This keeps language-specific syntax out of the rewrite engine and makes new grammars easier to add.

## Safety

BetterComments never searches for comments with an unrestricted regular expression. Python uses its standard tokenizer and AST. Other supported languages use Tree-sitter grammars. Strings such as `"https://example.com"`, `"hello // world"`, and `"# not a comment"` are not extracted as comments.

Replacements use parser-provided byte ranges and are applied from right to left. The resulting file is parsed again and its functional token stream is compared with the original before writing. Writes use a temporary file and atomic replacement. If parsing, validation, or writing fails, the original file is left untouched.

Linked files are accepted, but recursive scans never enter linked directories. Known credential files and private-key formats are skipped.

## AI and Privacy

BetterComments has no AI integration. It works offline after installation and never uploads comments, surrounding code, or repository contents. Unknown phrases are preserved unless an explicit project rule can handle them.

## Configuration

BetterComments reads `bettercomments.toml` from the current directory, or a file selected with `--config`.

```toml
[bettercomments]
ignored_directories = [".git", "node_modules", ".venv", "dist", "build"]
max_file_size = 2000000
max_comment_length = 100
backup_suffix = ".bak"
excluded_comment_patterns = ["^DATABASE MIGRATION:"]

[[rules]]
match = "Comprueba la sesión activa"
replacement = "Check the active session."
```

Project rules are exact matches after whitespace normalization. Set `case_sensitive = true` on an individual rule when needed.

## CLI Reference

| Option | Purpose |
| --- | --- |
| `-r`, `--recursive` | Enter subdirectories. |
| `-n`, `--dry-run` | Analyze without writing. |
| `--check` | Report whether changes are needed for CI. |
| `--diff` | Print unified diffs. |
| `-y`, `--yes` | Write without confirmation. |
| `--interactive` | Explicitly select the default per-file prompt mode. |
| `--backup` | Preserve each original with a `.bak`-style suffix. |
| `--generate` | Add comments for recognized conservative patterns. |
| `--config PATH` | Read a specific TOML configuration. |
| `-v`, `--verbose` | Report unchanged and written files. |
| `-q`, `--quiet` | Print only errors and requested diffs. |

Directory traversal is non-recursive unless `--recursive` is supplied. Writing is interactive unless `--yes` is supplied.

## Examples

The [`examples`](examples) directory contains multilingual comments, verbose English, multiline comments, protected directives, and strings containing comment syntax.

The `--generate` feature is experimental and opt-in. In version 0.1 it only documents typed Python exception handlers whose entire body is `pass`:

```python
try:
    load_optional_plugin()
except PluginError:
    # Intentionally ignore PluginError.
    pass
```

## Architecture

- `languages.py` defines the supported-language registry.
- `parser.py` converts parser nodes into a common comment model.
- `protection.py` preserves special and machine-readable comments.
- `rules.py` contains deterministic language and shortening rules.
- `transformer.py` renders byte-range replacements.
- `validation.py` compares functional source before and after rewriting.
- `processor.py` coordinates the per-file pipeline.
- `cli.py` handles discovery, previews, confirmation, and writes.

## Performance

Files are filtered by extension before reading and parsed once for extraction. Validation adds a second parse only when a change is proposed. Unsupported, sensitive, binary, and oversized files are skipped early. BetterComments performs no network requests.

## Limitations

- Rule-based translation cannot understand arbitrary natural language. Unrecognized comments remain unchanged.
- Project rules are exact phrase replacements, not programmable search-and-replace expressions.
- Documentation comments and inline comments are rewritten more conservatively than standalone comments.
- Comment generation currently supports only one narrow Python pattern.
- UTF-8 is required outside Python; Python encoding declarations are honored.

## Development

Run the test suite and type checker:

```bash
pytest
pyright
```

Build distribution artifacts:

```bash
python -m build
```

## Testing

The test suite covers all supported language families, multilingual and multiline rewrites, inline comments, directives, URLs, escaped strings, Unicode, line endings, invalid syntax, discovery, configuration, atomic writes, CLI exit codes, and functional-source validation.

## Contributing

Open an issue before proposing a broad behavior change. Pull requests should include focused tests, preserve unknown comments by default, and keep all code and documentation in English.

## License

BetterComments is available under the [MIT License](LICENSE).
