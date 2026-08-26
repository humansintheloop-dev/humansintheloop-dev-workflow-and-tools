# Discussion: Fix i2code go menu default selection logic

## Classification

**Type:** Bug fix in a user-facing feature (A. User-facing feature)

**Rationale:** The menu default selection is a UX issue in the existing `i2code go` command. The defaults don't guide the user through the natural workflow progression, causing confusion and extra keystrokes.

## Q&A

### Q1: Should this fix also address the defaults when lifecycle state IS present (draft/ready/wip), or only fix the no-lifecycle-state fallback path?

**A:** What's there to fix with the different lifecycle states?

**Resolution:** After analysis, the lifecycle-state defaults for draft and wip are mostly correct, but the ready state needs a fix too (see Q5). The main issue is the no-lifecycle-state fallback path, which is triggered when projects are created outside of `i2code go`.

### Q2: For the no-lifecycle-state case, should the default priority be configure -> commit -> implement?

**A:** Yes, that's right. Default progression: configure -> commit -> implement.

### Q3: Should this fix treat 'no metadata file' as the primary/common path, or is lifecycle metadata something planned for broad adoption?

**A:** Why does it matter?

**Resolution:** It doesn't affect the fix. The default priority logic applies regardless.

### Q4: Why was the user not prompted to change the lifecycle state in the original scenario?

**A:** The reason there was no metadata was because the idea/spec/plan were created outside of `i2code go`.

**Resolution:** The "Move to ready/wip" options only appear when a metadata file with a `state` field exists. Projects created outside `i2code go` have no metadata file, so lifecycle transitions are unavailable.

### Q5: When `i2code go` encounters a project with no metadata file, how should it handle it?

**A:** Auto-create as draft. Silently create a metadata file with `state: draft`, so lifecycle transitions are always available.

### Q6: The workflow progression was missing the Ready -> WIP transition.

**A:** Correct. The full progression should be:

1. Draft -> default: "Move to ready"
2. Ready + options not configured -> default: "Configure implement options"
3. Ready + options configured -> default: "Move to WIP"
4. WIP + dirty -> default: "Commit changes"
5. WIP + clean -> default: "Implement the entire plan"

**Resolution:** The ready-state default needs to be sensitive to whether the implement config file exists. If configured, the default shifts from "Configure implement options" to "Move to WIP".

### Q7: Any additional requirements before specification?

**A:** No, let's proceed.
