# CONNECTORS

Runtime bindings — how agents read state, hand off work, and invoke project tooling.

---

## §1 Task State Connector

Task state is the single source of truth: the `status` and `owner` fields in REQ frontmatter.

| Operation | How | Example |
|-----------|-----|---------|
| Read current state | `cat tasks/features/REQ-NNN.md` | — |
| Claim task | Edit frontmatter, `git commit -m "claim: REQ-NNN by optimizer-001"` | — |
| Advance state | Edit frontmatter, `git commit -m "handoff: REQ-NNN → evaluator-001 (T03)"` | T03: req approved |
| Reject in review | Edit `owner` + `review_round`, `git commit -m "review-reject: REQ-NNN round N"` | T04, T08, T11, T14 |
| Block task | Set `status=blocked`, `blocked_from_*`, append to `pending_bugs` | T16 |
| Unblock task | Restore `status` + `owner` from `blocked_from_*` | T17 |

**Atomicity rule:** Frontmatter update and commit happen in one `git commit`. Never leave the file in an intermediate state without a commit.

---

## §2 Agent Handoff Signal

my-invest-global uses a **semi-manual handoff**: agents update frontmatter and commit, then Daniel opens the next agent session and says "pick up REQ-NNN."

For future automation, agents may write to an inbox directory:

```
tasks/inbox/
  for-optimizer/
    pending/    envelope files waiting for optimizer-001
    claimed/    claimed (atomic mv)
    done/       completed
  for-evaluator/
    pending/
    claimed/
    done/
```

Inbox envelope format (`REQ-NNN-T03.json`):

```json
{
  "req_id": "REQ-NNN",
  "transition": "T03",
  "from_agent": "evaluator-001",
  "to_agent": "optimizer-001",
  "summary": "Requirement approved. Proceed to tc_design.",
  "timestamp": "2026-05-16T10:00:00+08:00"
}
```

> The inbox system is optional in v1. The frontmatter commit alone is sufficient for the current semi-manual workflow.

---

## §3 Git / GitHub Connector

| Operation | Command | Who | When |
|-----------|---------|-----|------|
| Create feature branch | `git checkout -b feat/REQ-NNN` | optimizer-001 | Start of `req_impl` |
| Commit TC files | `git add tasks/test-cases/ && git commit -m "tc-design: TC-NNN"` | evaluator-001 | `tc_design` |
| Commit TC code | `git add tests/ && git commit -m "tc-impl: TC-NNN-SS"` | optimizer-001 | During `tc_impl` |
| Commit implementation | `git add engine/ scripts/ && git commit -m "feat: REQ-NNN <title>"` | optimizer-001 | During `req_impl` |
| **Open draft PR** | `gh pr create --draft --title "feat: REQ-NNN <title>" --body "..."` | **optimizer-001** | End of `req_impl` (T12) |
| View PR status | `gh pr view <PR_NUMBER> --json statusCheckRollup` | Any agent | Any time |
| Add review comment | `gh pr review <PR_NUMBER> --comment -b "[BLOCK] ..."` | evaluator-001 | `req_impl_review` |
| **Convert draft → ready** | `gh pr ready <PR_NUMBER>` | **evaluator-001** | T13 (approval) |
| Merge PR | `gh pr merge <PR_NUMBER>` or GitHub UI | **human-001** | `pr_draft` (T15) |

**PR description template** (optimizer-001 fills this at T12):

```markdown
## REQ
REQ-NNN — <title>

## Changes
- <bullet per logical change>

## Test evidence
- `uv run pytest tests/ -v` passed
- All TC-NNN-SS pass
- `uv run mypy engine/ --strict` passed
- `uv run ruff check engine/ tests/` passed

## Notes for reviewer
<anything evaluator-001 should know: tricky edge cases, deferred items, open questions>
```

---

## §4 Script / CI Connectors

| Script | Invocation | Purpose | Who runs it |
|--------|-----------|---------|------------|
| Data refresh | `uv run refresh-data-agent` | Fetch market data into DuckDB | Human / cron |
| Pipeline runner | `uv run python scripts/run_pipeline.py --date YYYY-MM-DD` | Phase 5 daily pipeline | optimizer-001 / human |
| Test suite | `uv run pytest tests/ -v` | All unit + integration tests | optimizer-001 before handoff |
| Type check | `uv run mypy engine/ --strict` | Static type checking | optimizer-001 before handoff |
| Lint | `uv run ruff check engine/ tests/` | Code style | optimizer-001 before handoff |

**Pre-handoff CI (optimizer-001 runs before every T02/T09/T12):**

```bash
uv run pytest tests/ -v \
  && uv run mypy engine/ --strict \
  && uv run ruff check engine/ tests/
```

All three must pass before handing off to evaluator-001.

---

## §5 Runtime / Service Connectors

| Service | Path / Endpoint | Phase introduced | Notes |
|---------|----------------|-----------------|-------|
| DuckDB | `data/db/aidc.duckdb` | Phase 0 (existing) | Local file; no server needed |
| MacroStateFile | `data/cache/macro_state.json` | Phase 5 (REQ-001) | Written by macro_gate CLI |
| SignalsFile | `data/processed/signals_{YYYYMMDD}.json` | Phase 5 (REQ-004) | Written by runner |
| Neo4j | `bolt://localhost:7687` | Phase 8a | Docker, shared with math-to-go |
| LanceDB | `data/lancedb/` | Phase 8b | Local directory |

**Environment variables** (in `.env`, documented in `.env.example`):

```bash
ANTHROPIC_API_KEY=...          # required for Phase 6+ (Claude API synthesis)
NEO4J_URI=bolt://localhost:7687  # Phase 8a
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

No services are required to run Phases 0–5. DuckDB and the filesystem are sufficient.
