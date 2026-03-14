Currently:

* IsolateMode uses a Git worktree for the agent's working directory

The problem:

* The worktree shares the `.git` directory with the main repo, so the agent has write access back to the main repo (lock files, index, refs). This defeats the purpose of isolation — the main repo is not protected from the agent.

The goal:

* Security isolation — the agent running inside isolarium must not be able to modify the main repo

Solution:

1. Create a worktree as before
2. Run scaffolding in the worktree
3. Shallow clone the worktree to a new location (e.g. instead of '-wt-' use '-cl-' in the sibling directory name)
4. Reconfigure the clone's remote origin to point to the GitHub remote (not the local worktree) and track the idea branch
5. Run isolarium in the clone instead of the worktree

The clone is a fully independent git repo with its own `.git` directory and no references to the main repo — providing true filesystem and git-level isolation.

Scope: IsolateMode only (WorktreeMode keeps using worktrees).

Re-runs: If the clone already exists, reuse it. If the worktree already exists, keep it (scaffolding guard prevents re-scaffolding).
