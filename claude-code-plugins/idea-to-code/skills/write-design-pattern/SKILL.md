---
name: write-design-pattern
description: Write a design pattern catalog entry. Use when the user asks to document a design pattern, add a pattern to the catalog, or after a refactoring session identifies a reusable pattern.
user-invokable: true
---

# Design Pattern Catalog Entry

Create or update a pattern entry in `design-pattern-catalog/<category>/<pattern-name>.md`.

## Steps

1. **Determine category and name** — use AskUserQuestion if not clear from context. Use kebab-case for the pattern name. Category examples: `commands`, `testing`, `architecture`.

2. **Read existing entries** — check `design-pattern-catalog/` for existing entries to maintain consistency in structure and tone.

3. **Write the entry** — `design-pattern-catalog/<category>/<pattern-name>.md` with these sections:

### `# Pattern Name`

### `## Problem`
State the general principle, not a specific symptom. 1-2 sentences. Specific examples belong in later sections.

### `## Structure` or `## Example`
Choose the appropriate section based on the pattern type:

**Use `## Structure`** for patterns that define collaborating elements (e.g., Command + Assembler):
A table of key elements, their files, and responsibilities. Lead each row with the key element, not the filename.

| Key Element | File | Responsibility |
|-------------|------|---------------|
| ... | `...` | ... |

#### `### Reference implementation` (within Structure)
Bullet list of symbols and their files. Format: `SymbolName` in `path/to/file.py`. No line numbers — they're too unstable.

**Use `## Example`** for patterns about code organization or refactoring, with `### Before` and `### After` subsections showing the concrete change.

### `## Testing Strategies` (when applicable)
One subsection per strategy. Each starts with **What is tested:** naming the specific element under test. Include example references as `path/to/test_file.py` — `test_function_name`.

### `## When to Apply`
Bullet list of conditions where the pattern is appropriate.

### `## Key Principles`
Bullet list of bold-titled principles. These are the memorable takeaways.

## Guidelines

- **No code samples** — reference files and symbols instead; the catalog points to living code, not duplicated snippets
- **No line numbers** — use `path/to/file` — `symbol_name` format for references
- **Lead with the key element** — in tables and bullet lists, put the symbol/concept first, then the file
- **Testing strategies name what is tested** — each strategy starts with the specific class or function under test
- **Concise** — a catalog entry is a reference guide, not a tutorial
