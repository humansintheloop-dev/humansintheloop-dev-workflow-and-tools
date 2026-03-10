# Discussion: i2code go should grant permissions

## Context from codebase analysis

- `i2code go` orchestrates through states: NO_IDEA -> HAS_IDEA_NO_SPEC -> HAS_SPEC -> HAS_PLAN
- Interactive commands (brainstorm, spec create/revise, design create, plan create/revise) invoke Claude with NO permission flags
- The `implement` command already handles permissions via `--allowedTools` and `.claude/settings.local.json`
- Command assembly is in `src/i2code/implement/command_builder.py`
- Permission infrastructure exists in `src/i2code/implement/claude_permissions.py`

## Questions and Answers

### Q1: Scope of commands

Should permissions be granted for all `i2code go` phases or only specific ones?

**Answer:** A — All `i2code go` phases (brainstorm, spec create/revise, design create, plan create/revise).

### Q2: Permission mechanism

Two options: A) CLI flags (`--allowedTools`) passed transiently to `claude`, or B) writing to `.claude/settings.local.json`.

**Answer:** A — CLI flags. Transient, doesn't modify project files, matches existing pattern for non-worktree invocations.

### Q3: Permission scope

What paths should Read and Write/Edit cover?

**Answer:** Read access to the repository root (Claude needs codebase context). Read and Write access to the idea directory (where idea, spec, discussion, and plan files live).

### Correction: CWD should be repo root

Currently, Claude is invoked with `cwd=project.directory` (the idea directory). The user clarified that `i2code go` should run Claude from the **repository root**, not the idea directory. This means:
- Claude's CWD = repo root (natural read access to the whole project)
- Write/Edit permissions scoped to the idea directory via CLI flags

This is also a behavioral change: `brainstorm.py`, `create_spec.py`, `revise_spec.py`, and other step functions currently pass `cwd=project.directory`.

### Q4: What does Claude currently prompt for?

Claude currently prompts for **read access** to the CWD. Write, Edit, Glob, Grep do not trigger permission prompts.

**Answer:** Only Read needs to be pre-authorized via CLI flags.

### Q5: Exact permissions (established)

From the original idea and discussion:
- **Read** scoped to the **repo root** — `Read(/<repo_root>/)`
- **Write** scoped to the **idea directory** — `Write(/<idea_dir>/)`
- **Edit** scoped to the **idea directory** — `Edit(/<idea_dir>/)`

No further questions needed on scope — this was stated upfront.

### Q6: Deriving the repo root

How to determine the repo root for Read permission scope?

**Answer:** It's simply the current working directory where `i2code` was invoked — no derivation needed.

### Q7: Any other commands affected?

Should standalone commands (`i2code idea brainstorm`, `i2code spec create`, etc.) also grant permissions?

**Answer:** The subcommands invoked by `i2code go` (brainstorm, spec, design, plan — not implement) should set permissions. Standalone commands run outside of `go` continue as-is. The implement step keeps its own existing permission handling.

## Classification

**Type: A — User-facing feature**

**Rationale:** This removes an interactive friction point where Claude prompts for read access during the `i2code go` workflow. It improves the user experience by pre-authorizing the permissions Claude needs.
