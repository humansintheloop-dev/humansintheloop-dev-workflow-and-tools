#! /bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "$DIR/_helper.sh"

_validate_idea
_validate_spec

export IDEA_FILE SPEC_FILE
export PLAN_SKILLS=$("$DIR/list-plugin-skills.sh")
PROMPT="$(envsubst < "$DIR/../prompt-templates/create-implementation-plan.md")"

SESSION_ID="$(_session_id)"

run_claude() {
    claude -p "$@" "$PROMPT"
}

validate_plan() {
  # Validates that every Task block contains the required contract fields:
  #   - TaskType:
  #   - Entrypoint:
  #   - Observable:
  #   - Evidence:
  #
  # Assumes tasks use the format:
  # - [ ] **Task X.Y: ...**
  #
  # Returns 0 if valid; non-zero if invalid and prints errors to stderr.
  local plan="$1"

  awk '
    function fail(msg) { print "PLAN_VALIDATION_ERROR: " msg > "/dev/stderr"; errors=1 }
    function reset_flags() { has_type=has_entry=has_obs=has_evid=0 }
    function check_block(which) {
      if (!in_task) return
      if (!has_type)  fail("Missing TaskType in " which)
      if (!has_entry) fail("Missing Entrypoint in " which)
      if (!has_obs)   fail("Missing Observable in " which)
      if (!has_evid)  fail("Missing Evidence in " which)
    }

    BEGIN { errors=0; in_task=0; reset_flags() }

    /^\- \[ \] \*\*Task [0-9]+\.[0-9]+:/ {
      # New task starts; validate previous task block
      if (in_task) check_block("previous task block")
      in_task=1
      reset_flags()
      next
    }

    in_task && /^[[:space:]]*- TaskType:/   { has_type=1 }
    in_task && /^[[:space:]]*- Entrypoint:/ { has_entry=1 }
    in_task && /^[[:space:]]*- Observable:/ { has_obs=1 }
    in_task && /^[[:space:]]*- Evidence:/   { has_evid=1 }

    END {
      check_block("last task block")
      exit errors
    }
  ' <<< "$plan"
}

repair_plan() {
  # Asks Claude to repair ONLY structural violations, without adding scope.
  local plan="$1"
  local errors="$2"

  local repair_prompt
  repair_prompt=$(
    cat <<'EOF'
You are repairing a generated implementation plan that must follow a strict task schema.

Fix ONLY the listed validation errors.
- Do NOT add new steel threads.
- Do NOT add new tasks unless required to fix a missing contract field on an existing task (prefer rewriting titles/structure).
- Do NOT change scope or introduce new features.
- Preserve numbering and ordering of tasks as much as possible.
- Ensure every task uses this format:

- [ ] **Task X.Y: Outcome-oriented description**
  - TaskType: OUTCOME | INFRA | REFACTOR
  - Entrypoint:
  - Observable:
  - Evidence:
  - Steps:
    - [ ] ...

Return the FULL corrected plan as markdown. No commentary.

Validation errors:
EOF
  )

  # We pass the repair instruction as the "prompt" to Claude, plus the plan + errors as stdin-like context.
  # Claude CLI generally treats the final argument as the user prompt; include plan inline.
  run_claude "$@" "${repair_prompt}"$'\n'"${errors}"$'\n\n''Plan to repair:'$'\n'"${plan}"
}

echo Generate plan

PLAN="$(run_claude "$@")"

echo  Validate - if invalid, attempt one repair pass then validate again

if ! ERRORS="$(validate_plan "$PLAN" 2>&1 >/dev/null)"; then
  echo "$ERRORS" >&2
  echo "Attempting one automatic repair pass..." >&2
  PLAN="$(repair_plan "$PLAN" "$ERRORS")"
  validate_plan "$PLAN" >/dev/null
fi

printf "%s\n" "$PLAN" > "${PLAN_WITHOUT_STORIES_FILE}"

echo plan written to "${PLAN_WITHOUT_STORIES_FILE}"

