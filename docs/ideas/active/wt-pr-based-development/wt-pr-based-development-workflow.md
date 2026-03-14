# Slice-based feature workflow using Git worktrees, GitHub, and `gh`

This document expands the **Option A** workflow (integration branch + numbered slice branches + Draft PRs) into step-by-step commands.

It assumes:

- Repo default branch: `main`
- You use GitHub and the GitHub CLI: `gh`
- Your docs live at: `docs/features/<idea>/`
- Worktree directory naming (sibling of repo dir): `<repodir>-wt-<idea>`
- Integration branch: `idea/<idea>`
- Slice branch (one PR per slice): `plan/<idea>/<nn>-<slice-name>` where `<nn>` is `01`, `02`, ...

---

## 0) Naming and variables

Set these once per terminal session (run from **inside the repo root**):

```bash
IDEA="ci-flaky-tests"          # must match docs/features/<idea>/
REPO="$(basename "$PWD")"
WT_DIR="../${REPO}-wt-${IDEA}"

INTEGRATION_BRANCH="idea/${IDEA}"
```

Slice variables (set per slice):

```bash
SLICE_NUM="01"
SLICE_NAME="repro-test"        # kebab-case
SLICE="${SLICE_NUM}-${SLICE_NAME}"
SLICE_BRANCH="plan/${IDEA}/${SLICE}"
```

---

## 1) Preconditions and sanity checks

From the repo root:

```bash
# Ensure plan doc exists
test -f "docs/features/${IDEA}/${IDEA}-plan.md" || echo "Missing plan doc"

# Ensure gh is authenticated
gh auth status

# Ensure your main worktree is clean
git status
```

---

## 2) Start idea (create integration branch + worktree)

From the repo root:

```bash
git fetch origin
git switch main
git pull --ff-only
```

Create integration branch + worktree:

```bash
# Create the idea worktree and integration branch from main
git worktree add -b "${INTEGRATION_BRANCH}" "${WT_DIR}" main
```

Push the integration branch (so it exists on GitHub):

```bash
cd "${WT_DIR}"
git push -u origin "${INTEGRATION_BRANCH}"
```

Confirm worktrees:

```bash
cd -  # back to repo root (optional)
git worktree list
```

---

## 3) Start slice (create slice branch + Draft PR)

Do this in the **idea worktree**:

```bash
cd "${WT_DIR}"
git switch "${INTEGRATION_BRANCH}"
```

Create the slice branch:

```bash
git switch -c "${SLICE_BRANCH}"
git push -u origin "${SLICE_BRANCH}"
```

Create a **Draft PR**:

```bash
gh pr create   --base main   --head "${SLICE_BRANCH}"   --title "${IDEA} - ${SLICE}"   --body "Implements docs/features/${IDEA}/${IDEA}-plan.md"   --draft   --web
```

At this point, development for this slice happens on `${SLICE_BRANCH}` in `${WT_DIR}`.

---

## 4) Develop slice (commit + push while Draft)

In the idea worktree:

```bash
cd "${WT_DIR}"
git branch --show-current   # should be ${SLICE_BRANCH}
```

Typical loop:

```bash
git status
git add -A
git commit -m "Describe change"
git push
```

---

### Preserving an unpushed commit when a slice PR is no longer Draft

If automation detects that the current slice PR is **no longer in Draft**, but there is an **unpushed commit** on the slice branch, use the following sequence to preserve the commit while freezing the slice PR.

#### Goal
- Preserve the commit in the **integration branch** and the **next slice**
- Reset the **previous slice branch** so it exactly matches the remote PR branch
- Avoid rewriting or polluting the existing PR

#### Steps

1. **Merge the current slice into the integration branch** (captures the unpushed commit)
```bash
git switch idea/<idea>
git merge --no-ff plan/<idea>/<old-slice>
```

2. **Start the next slice from integration**
```bash
git switch -c plan/<idea>/<new-slice>
```

3. **Reset the previous slice to match the remote PR branch**
```bash
git fetch origin
git switch plan/<idea>/<old-slice>
git reset --hard origin/plan/<idea>/<old-slice>
```

#### Notes
- The reset does **not** lose the commit: it is already preserved in the integration branch.
- This does **not** confuse Git history; future merges from the old slice will only bring in new review fixes.
- Do **not** push after the reset - the old slice PR is frozen.
- All further development continues on the new slice.


## 5) Continue development while review happens (merge slice into integration, then start next slice)

### 5.1 Merge slice branch into integration locally (to keep integration ahead)

In the idea worktree:

```bash
cd "${WT_DIR}"
git switch "${INTEGRATION_BRANCH}"
git merge --no-ff "${SLICE_BRANCH}"
```

Push integration:

```bash
git push
```

### 5.2 Mark PR ready for review (freeze slice except review fixes)

```bash
git switch "${SLICE_BRANCH}"
gh pr ready --web
```

### 5.3 Start the next slice (new branch + new Draft PR)

Increment `SLICE_NUM` and set `SLICE_NAME` for the next slice, then repeat section **3**.
You typically create the next slice from the integration branch:

```bash
git switch "${INTEGRATION_BRANCH}"

# Example next slice vars
SLICE_NUM="02"
SLICE_NAME="stabilize-clock"
SLICE="${SLICE_NUM}-${SLICE_NAME}"
SLICE_BRANCH="plan/${IDEA}/${SLICE}"

git switch -c "${SLICE_BRANCH}"
git push -u origin "${SLICE_BRANCH}"

gh pr create   --base main   --head "${SLICE_BRANCH}"   --title "${IDEA} - ${SLICE}"   --body "Slice ${SLICE} for docs/features/${IDEA}/${IDEA}-plan.md"   --draft   --web
```

---

## 6) Handle review feedback on a slice PR

When reviewers request changes on a slice, make fixes on that slice branch and push.

### 6.1 Fix the slice branch (PR-visible)

```bash
cd "${WT_DIR}"
git switch "plan/${IDEA}/01-repro-test"
# edit...
git add -A
git commit -m "Address review feedback"
git push
```

### 6.2 Bring those fixes into integration (so integration stays ahead)

**A) Merge the updated slice branch into integration (simple):**

```bash
git switch "${INTEGRATION_BRANCH}"
git merge "plan/${IDEA}/01-repro-test"
git push
```

**B) Cherry-pick the fix commit(s) into integration (tidier):**

```bash
git switch "${INTEGRATION_BRANCH}"
git cherry-pick <fix-commit-sha>         # or a range
git push
```

---

## 7) When `main` has advanced

When `main` has advanced:

1) **Rebase the integration branch onto `main`**
2) **Update any still-open slice branches** so they include the latest `main`

### 7.1 Rebase integration onto `main` (private/mutable branch)

From the idea worktree:

```bash
cd "${WT_DIR}"
git fetch origin

git switch "${INTEGRATION_BRANCH}"
git rebase origin/main
git push --force-with-lease
```

### 7.2 Update an open slice branch

If a slice PR is still open, update it from `main`.

- If the PR is **Ready for review**, prefer **merge `main` into the slice** (no history rewrite).
- If the PR is still **Draft** and you are OK force-pushing, you may rebase it.

**Merge `main` into slice (recommended once Ready):**

```bash
git switch "${SLICE_BRANCH}"
git merge origin/main
git push
```

**Rebase slice onto `main` (Draft only, then force-push):**

```bash
git switch "${SLICE_BRANCH}"
git rebase origin/main
git push --force-with-lease
```

---

## 8) Finish idea (cleanup)

After the final slice is merged and the idea is done:

### 8.1 Remove the worktree (from the repo root)

```bash
cd /path/to/${REPO}
git worktree remove "${WT_DIR}"
```

### 8.2 Delete branches (optional)

Delete local branches:

```bash
git branch -d "${INTEGRATION_BRANCH}"
# delete any local slice branches you still have:
# git branch -d "plan/${IDEA}/01-repro-test"
```

Delete remote branches (optional; only if your repo policy allows it):

```bash
git push origin --delete "${INTEGRATION_BRANCH}"
git push origin --delete "plan/${IDEA}/01-repro-test"
```

---

## Appendix: Useful inspection commands

```bash
git worktree list
git branch --show-current
gh pr status
gh pr view --web
gh pr list --head "plan/${IDEA}/"
```
