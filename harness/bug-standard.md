---
harness_id: BUG-STD-001
component: bug-management
owner: human-001
version: "0.1"
status: active
---

# Bug Standard

## §1 Scope

Governs how bugs are recorded, classified, linked to REQs, and resolved. All tracked issues — whether discovered by an agent, CI, or a human — must have a `BUG-NNN.md` file in `tasks/bugs/`.

---

## §2 Bug Types

| bug_type | When triggered | Triggered by | Blocks which REQ state |
|----------|---------------|-------------|----------------------|
| `req_bug` | Evaluator finds requirement defect in `req_review` | evaluator-001 | `req_review` |
| `tc_bug` | Optimizer finds TC text defect in `tc_review` | optimizer-001 | `tc_review` / `tc_design` |
| `impl_bug` | Evaluator finds code defect in `req_impl_review` | evaluator-001 | `req_impl_review` |
| `ci_bug` | CI gate fails on a PR | CI / evaluator-001 | `pr_draft` |
| `user_bug` | User reports defect post-merge | human-001 | Does not block (post-`done`) |

---

## §3 Frontmatter Schema

```yaml
---
bug_id: BUG-007
title: "check_portfolio_balance returns wrong direction for RED macro_state"
bug_type: impl_bug             # req_bug | tc_bug | impl_bug | ci_bug | user_bug
status: open                   # open | in_progress | blocked | resolved | closed
severity: high                 # critical | high | medium | low
owner: unassigned              # registered UID or unassigned — see harness/agent-registry.yml
linked_req: REQ-002            # REQ that is blocked by this bug
regression_tc: []              # [TC-NNN-SS] — TCs that would catch a recurrence
blocked_reason: ""             # filled if bug itself is blocked
---
```

---

## §4 Bug State Machine

| State | Meaning | Owner |
|-------|---------|-------|
| `open` | Filed; not yet confirmed | `unassigned` |
| `in_progress` | Being fixed | `optimizer-001` |
| `blocked` | Waiting on external dependency | `unassigned` |
| `resolved` | Fix committed; awaiting review | `evaluator-001` |
| `closed` | Fix reviewed and merged | — |

### Transition Table

| From | Event | To | Owner after |
|------|-------|-----|-------------|
| `open` | Optimizer identifies root cause and begins fix | `in_progress` | `optimizer-001` |
| `in_progress` | Fix committed | `resolved` | `evaluator-001` |
| `resolved` | Evaluator approves fix | `closed` | — |
| `resolved` | Evaluator rejects fix | `in_progress` | `optimizer-001` |
| `open` / `in_progress` | Human decides not to fix | `closed` | `human-001` |

---

## §5 Blocking a REQ

When a bug blocks a REQ from advancing, update both the BUG file and the REQ file atomically.

**REQ fields to set:**

```yaml
status: blocked
owner: unassigned
blocked_reason: "BUG-007: check_portfolio_balance returns wrong direction"
blocked_from_status: req_impl_review      # the state we were in
blocked_from_owner: evaluator-001          # who was working on it
pending_bugs: [BUG-007]
```

Commit message: `bug-block: REQ-NNN blocked by BUG-NNN`

---

## §6 Unblocking a REQ

When all `pending_bugs` are `closed`:

1. Remove the BUG ID from `pending_bugs`
2. If `pending_bugs` is now empty:
   - Restore `status` ← `blocked_from_status`
   - Restore `owner` ← `blocked_from_owner`
   - Clear `blocked_reason`, `blocked_from_status`, `blocked_from_owner`
3. Add a `## Bug History` section to the REQ body noting the bug type, ID, and close date

Commit message: `bug-unblock: REQ-NNN unblocked, BUG-NNN closed`

---

## §7 Regression TCs

For every `severity: high` or `severity: critical` bug, a regression TC must be added before the bug is closed:

1. Create `TC-NNN-SS.md` in `tasks/test-cases/` where NNN = the linked REQ's digits
2. Add the TC ID to `regression_tc` in the BUG file
3. Implement the TC in the test suite (optimizer-001)
4. Add the TC ID to `test_case_ref` in the linked REQ file

---

## §8 Severity Guidelines

| Severity | Criteria |
|----------|---------|
| `critical` | Data loss, security vulnerability, system cannot start |
| `high` | A core pipeline function returns wrong results (wrong action_code, wrong composite_score, broken SignalsFile) |
| `medium` | Degraded performance, minor signal miscalculation not affecting action_code, non-golden-path failure |
| `low` | Typo, log noise, cosmetic issue |
