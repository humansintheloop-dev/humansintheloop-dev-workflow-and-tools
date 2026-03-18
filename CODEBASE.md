# Codebase Guide

This repository has three main components:

1. **`i2code` CLI Tool** — Python CLI for the humans-in-the-loop idea-to-code workflow
2. **Claude Code Plugin** — Skills, slash commands, and hooks that extend Claude Code
3. **Feature Documentation** — Structured idea tracking through lifecycle stages

---

## 1. `i2code` CLI Tool

A uv-managed Python CLI defined in `pyproject.toml`. Source is in `src/i2code/`, with the top-level Click group in `src/i2code/cli.py`.

Tests live in `tests/` but directory names don't always match source:

| Test directory | Tests for |
|----------------|-----------|
| `tests/plan-manager/` | `src/i2code/plan/` |
| `tests/plan-domain/` | `src/i2code/plan_domain/` |
| `test-scripts/` | End-to-end and smoke tests |

## 2. Claude Code Plugin

Plugin source lives in `claude-code-plugins/idea-to-code/`, with the marketplace index in `.claude-plugin/marketplace.json`.

The plugin bundles skills (in `skills/`), slash commands (in `commands/`), and hooks (in `hooks/`).

## 3. Feature Documentation

Ideas live in `docs/ideas/active/<name>/` or `docs/ideas/archived/<name>/`. Each has a `<name>-metadata.yaml` tracking lifecycle state: `draft` → `ready` → `wip` → `completed` | `abandoned`. Archival is orthogonal to state.
