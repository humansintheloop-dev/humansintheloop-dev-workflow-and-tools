Problem:

`i2code implement` runs commands (Claude, CI checks, etc.) that need environment variables defined in `.env.local`. The main work directory has a `.env.local`, but worktrees and clones do not (since `.env.local` is gitignored). This means commands run in worktree/clone contexts lack required env vars.

Solution:

At startup, `i2code implement` loads `.env.local` from the current working directory using `python-dotenv`. This applies to all three execution modes (trunk, worktree, isolate). Existing environment variables take precedence over values in `.env.local` (no override). If `.env.local` doesn't exist in CWD, nothing happens — no error, no fallback.

Dependencies:

- Add `python-dotenv` as a project dependency.
