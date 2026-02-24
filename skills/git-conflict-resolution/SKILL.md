---
name: git-conflict-resolution
description: Guidelines for resolving git merge and rebase conflicts efficiently. Claude should use this skill when resolving merge conflicts or rebase conflicts to prefer bulk git strategies over manual conflict marker editing.
---

# Git Conflict Resolution

When resolving merge or rebase conflicts, prefer efficient git strategies over manually editing conflict markers.

## Bulk Resolution with `git checkout`

When all conflicts in a file should be resolved the same way, use `git checkout` instead of editing conflict markers one at a time:

```bash
# Accept the incoming (remote/theirs) version entirely
git checkout --theirs <file>

# Accept the current (local/ours) version entirely
git checkout --ours <file>
```

After resolving, stage the file:

```bash
git add <file>
```

Multiple files can be resolved in one command:

```bash
git checkout --theirs file1.md file2.md
git add file1.md file2.md
```

## When to Use Each Strategy

| Strategy | When to Use |
|----------|-------------|
| `--theirs` | The remote version has the completed/updated work (e.g., plan files with tasks checked off) |
| `--ours` | Your local version is the one to keep (e.g., you made intentional local changes) |
| Manual edit | Conflicts require combining parts of both versions |

## Decision Process

Before editing conflict markers manually, ask:

1. **Can I accept one side entirely?** If yes, use `git checkout --theirs` or `--ours`.
2. **Are multiple files conflicted the same way?** Resolve them all in one command.
3. **Do I need parts of both sides?** Only then edit manually.

## Post-Resolution Verification

After resolving all conflicts:

1. Verify no conflict markers remain: search for `<<<<<<<`, `=======`, `>>>>>>>`
2. Run `git status` to confirm no unmerged paths remain
3. Run tests if source code was involved
