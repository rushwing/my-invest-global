#!/usr/bin/env bash
# Canonical enum values for the requirement state machine (requirement-standard.md §3-4).
# SOURCE OF TRUTH: keep in sync with requirement-standard.md §3 (frontmatter schema) and GLOSSARY.md §10.
#
# owner values are derived dynamically from harness/agent-registry.yml so that
# adding a new agent UID only requires updating the registry, not this file.
# Override registry path via: AGENT_REGISTRY=<path> (used by test fixtures).

# REQ status values — see requirement-standard.md §4 State Machine
REQ_VALID_STATUSES=(
  draft
  req_review
  tc_design
  tc_review
  tc_impl
  tc_impl_review
  req_impl
  req_impl_review
  pr_draft
  done
  blocked
)

# REQ owner values — derived from agent registry + unassigned
_REGISTRY_FILE="${AGENT_REGISTRY:-harness/agent-registry.yml}"
REQ_VALID_OWNERS=()
if [[ -f "$_REGISTRY_FILE" ]]; then
    while IFS= read -r _uid; do
        [[ -n "$_uid" ]] && REQ_VALID_OWNERS+=("$_uid")
    done < <(awk '/- uid:/ { print $NF }' "$_REGISTRY_FILE")
    REQ_VALID_OWNERS+=("unassigned")
else
    # Fallback: registry missing — only unassigned is valid (fail-safe, not fail-open)
    REQ_VALID_OWNERS=("unassigned")
fi
unset _REGISTRY_FILE _uid

# REQ tc_policy values
REQ_VALID_TC_POLICIES=(
  required
  optional
  exempt
)

# REQ priority values
REQ_VALID_PRIORITIES=(
  P0
  P1
  P2
  P3
)

# BUG status values — see bug-standard.md
BUG_VALID_STATUSES=(
  open
  in_progress
  blocked
  resolved
  closed
)

# Helper: check if value is in array
# Usage: in_array "$value" "${MY_ARRAY[@]}"
in_array() {
  local val="$1"; shift
  local item
  for item in "$@"; do
    [[ "$item" == "$val" ]] && return 0
  done
  return 1
}
