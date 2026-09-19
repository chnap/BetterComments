# Examples

Each `*_before` file is safe to copy and process with BetterComments. The matching `*_after` file shows the expected result.

The examples demonstrate:

- Spanish comments rewritten as concise English.
- Verbose English condensed to one comment line.
- A multiline C-style comment rewritten without changing its line count.
- Inline comments handled conservatively.
- TODO and ESLint directives preserved verbatim.
- URLs and comment-like text inside strings left untouched.

Preview an example:

```bash
bettercomments examples/python_before.py --dry-run --diff
```
