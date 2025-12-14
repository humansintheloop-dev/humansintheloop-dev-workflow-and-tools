# Idea: Package Slash Commands as Claude Code Plugin

## Overview

Package the existing slash commands as a Claude Code plugin to provide an easier installation method for users.

## Goal

Replace the manual installation process (`./link-dotfiles.sh`) with a simple plugin installation command:

```bash
/plugin install idea-to-code-workflow
```

Since `link-dotfiles.sh` only installs the slash commands (it creates symlinks from `dotfiles/claude/commands/*.md` to `~/.claude/commands/`), the plugin completely replaces its functionality. The commands will be moved from `dotfiles/claude/commands/` to the standard `commands/` directory at the root level, and `link-dotfiles.sh` will be removed.

## What This Changes

**Installation Only** - This is purely a distribution/installation improvement. The workflow and UX remain identical.

### Current Installation (Manual)
```bash
git clone https://github.com/yourusername/genai-development-workflow
cd genai-development-workflow
./link-dotfiles.sh  # Creates symlinks to ~/.claude/commands/
```

### New Installation (Plugin)
```bash
/plugin install https://github.com/yourusername/genai-development-workflow
# Commands automatically available in ~/.claude/commands/
```

**Result**: Same 7 slash commands, same workflow, same shell scripts - just easier to install.

## What This Does NOT Change

- ✅ Workflow remains unchanged
- ✅ Shell scripts remain the primary way to use the workflow
- ✅ Users still run `./workflow-scripts/idea-to-code.sh`
- ✅ Commands work identically whether installed via plugin or `link-dotfiles.sh`
- ✅ No new features or UX changes
- ✅ Documentation about the workflow stays the same

## Commands Being Packaged

The plugin simply makes these 7 existing commands installable:

1. `commit-changes.md`
2. `commit-staged-changes.md`
3. `idea-create-implementation-plan-from-stories.md`
4. `idea-create-spec.md`
5. `idea-create-stories.md`
6. `idea-revise-implementation-plan.md`
7. `precommit-check.md`

## What Needs to Be Done

### 1. Create Plugin Manifest

**File**: `.claude-plugin/plugin.json`

```json
{
  "name": "idea-to-code-workflow",
  "version": "1.0.0",
  "description": "Slash commands for the Humans-in-the-Loop idea-to-code workflow. Use with the workflow scripts at https://github.com/yourusername/genai-development-workflow",
  "author": {
    "name": "Your Name",
    "email": "your@email.com"
  },
  "repository": "https://github.com/yourusername/genai-development-workflow",
  "license": "MIT",
  "keywords": ["workflow", "planning", "implementation", "tdd", "steel-thread"],
  "commands": ["./commands/*.md"]
}
```

**Key Points**:
- `name`: Use kebab-case (lowercase with hyphens)
- `commands`: Points to command files using standard `commands/` directory
- `description`: Makes it clear this is for use with the workflow scripts
- Commands will be moved from `dotfiles/claude/commands/` to `commands/` (standard plugin structure)

### 2. Update Installation Documentation

**File**: `README.adoc`

**Find this section** (around line 16-18):
```asciidoc
== Installing Claude Code

See https://microservices.io/post/architecture/2025/07/09/vibe-coding-good-almost-other-part-2.html[Vibe coding: the good, the almost, and the @#$%** - Part 2], which describes how to get started with the Claude Code - a command-line based coding agent.
```

**Replace with**:
```asciidoc
== Installation

=== Prerequisites

Install Claude Code - see https://microservices.io/post/architecture/2025/07/09/vibe-coding-good-almost-other-part-2.html[Vibe coding: the good, the almost, and the @#$%** - Part 2] for getting started.

=== Installing the Slash Commands

The workflow uses custom slash commands that need to be installed:

[source,bash]
----
/plugin install https://github.com/yourusername/genai-development-workflow
----

This automatically installs all workflow slash commands.

=== Getting the Workflow Scripts

To use the workflow orchestration scripts, clone the repository:

[source,bash]
----
git clone https://github.com/yourusername/genai-development-workflow
cd genai-development-workflow
----

NOTE: Even if you install via plugin, you still need to clone the repository to use the workflow scripts.
```

### 3. Add Plugin Note to Script Documentation

**File**: `docs/scripts/scripts.adoc`

**Add near the top** (after the introduction, before the script list):

```asciidoc
NOTE: The slash commands used by these scripts must be installed first via `/plugin install idea-to-code-workflow`.
```

### 4. Move Commands to Standard Location

**Action**: Move command files from `dotfiles/claude/commands/` to `commands/`

This follows the standard Claude Code plugin structure where commands are at the root level in a `commands/` directory.

```bash
# Move all .md files
mv dotfiles/claude/commands/*.md commands/

# Remove old directory structure
rm -rf dotfiles/
```

### 5. Remove link-dotfiles.sh (Manual Step)

**File**: `link-dotfiles.sh`

**Action**: Manually delete this file after plugin implementation is complete

Since the plugin replaces the functionality of `link-dotfiles.sh`, it's no longer needed. The script only created symlinks for the slash commands, which the plugin now handles automatically.

**Note**: This will be removed manually to ensure the plugin is working correctly before removing the old installation method.

### 6. Directory Structure After Changes

```
genai-development-workflow/
├── .claude-plugin/          # NEW
│   └── plugin.json          # NEW - Plugin manifest
├── commands/                # MOVED - Command files from dotfiles/claude/commands/
│   ├── commit-changes.md
│   ├── commit-staged-changes.md
│   ├── idea-create-implementation-plan-from-stories.md
│   ├── idea-create-spec.md
│   ├── idea-create-stories.md
│   ├── idea-revise-implementation-plan.md
│   └── precommit-check.md
├── workflow-scripts/        # UNCHANGED - All shell scripts
├── docs/                    # MOSTLY UNCHANGED
│   ├── scripts/
│   │   └── scripts.adoc     # MINOR UPDATE - Add plugin note
│   └── features/
│       └── simple-plugin/   # NEW
│           └── simple-plugin-idea.md  # THIS FILE
├── README.adoc              # UPDATE - Simplified installation section
├── LICENSE.md               # UNCHANGED
└── .gitignore              # UNCHANGED
```

**Removed**:
- ❌ `dotfiles/` directory - Commands moved to standard `commands/` location
- ❌ `link-dotfiles.sh` - No longer needed; replaced by plugin

## Implementation Checklist

- [ ] Create `commands/` directory at root level
- [ ] Move all `.md` files from `dotfiles/claude/commands/` to `commands/`
- [ ] Remove `dotfiles/` directory
- [ ] Create `.claude-plugin/` directory
- [ ] Create `.claude-plugin/plugin.json` with manifest
- [ ] Update `README.adoc` installation section (remove manual option)
- [ ] Add plugin note to `docs/scripts/scripts.adoc`
- [ ] Test plugin installation locally:
  ```bash
  /plugin install /Users/cer/src/genai-development-workflow
  /help  # Verify commands appear
  ```
- [ ] Commit changes with message: "Convert to Claude Code plugin with standard structure"
- [ ] Tag release: `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Test remote installation:
  ```bash
  /plugin install https://github.com/yourusername/genai-development-workflow
  ```
- [ ] **Manually remove** `link-dotfiles.sh` after confirming plugin works correctly

## Testing Plan

### Local Testing
```bash
# Install from local directory
/plugin install /Users/cer/src/genai-development-workflow

# Verify commands are available
/help

# Test a command
cd /tmp/test-idea
/idea-create-spec idea-file=./test-idea.txt discussion-file=./test-discussion.md

# Verify shell scripts still work
cd /Users/cer/src/genai-development-workflow
./workflow-scripts/idea-to-code.sh /tmp/test-idea
```

### Remote Testing (After Push)
```bash
# Uninstall local version
/plugin uninstall idea-to-code-workflow

# Install from GitHub
/plugin install https://github.com/yourusername/genai-development-workflow

# Verify everything works
/help
```

## Benefits

1. **Easier Installation**: Single command instead of clone + run script
2. **Automatic Updates**: Users can update via `/plugin update idea-to-code-workflow`
3. **Discoverability**: Plugin shows in `/plugin` listings
4. **Simplified Repo**: Remove `link-dotfiles.sh` and manual installation complexity
5. **Single Installation Method**: Only one way to install commands, easier to document and support

## Non-Goals

- ❌ Change the workflow or UX
- ❌ Replace shell scripts with plugin functionality
- ❌ Add new features or commands
- ❌ Modify existing command behavior
- ❌ Create custom TypeScript/JavaScript code
- ❌ Change how users interact with the workflow

## Success Criteria

1. Users can install commands via `/plugin install idea-to-code-workflow`
2. All 7 slash commands work identically to previous manual installation
3. Shell scripts continue to work exactly as before
4. `link-dotfiles.sh` is removed from the repository
5. Documentation clearly explains plugin installation
6. No changes to workflow or user experience

## Future Considerations

- Could create a separate plugin marketplace JSON for easier discovery
- Could add version management for commands
- Could explore creating workflow orchestration commands (future enhancement)
- For now: Keep it simple - just package existing commands

## Relationship to convert-to-plugin Idea

The `docs/features/convert-to-plugin/convert-to-plugin-idea.md` document explores a much more comprehensive plugin that would:
- Replace shell scripts with plugin functionality
- Add visual/CLI enhancements
- Create new workflow orchestration features

**This simple plugin idea is different**: It only packages existing commands for easier installation. It's a pragmatic first step that provides immediate value without the development overhead of a full-featured plugin.
