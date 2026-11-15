---
trigger: always_on
---

# Workforces Base Rules

These core operational rules govern all workforce interactions and execution loops.

---

## 1. GitHub Rules & Multi-Repo Scoping

- **Multi-Repo Scoping**: All GitHub CLI queries (`gh issue`, `gh pr`) MUST iterate across all repositories configured under `tracked_repos` in `workforces/workrules.md` / `workstate.md` (pass `--repo <owner/repo>`).
- **Autonomous Feature-Branch Commits & Consent Gate**: Commit and push autonomously **only** on isolated feature branches/worktrees to open Draft PRs per [`wf-git-workflow`](wf-git-workflow.md). NEVER execute cloud deployments (`sam deploy`, `ampx`, `terraform apply`, `kubectl`, etc.), merge PRs (`gh pr merge`), or push to protected branches (`main`, `master`, `prod`, `staging`, `develop`) without explicit user consent.
- **Task Source of Truth & Reconciliation**: `workforces/tasks/*.md` is the single source of truth for all tasks. When remote PRs/issues close, automatically reconcile task status to `done` via `report-task.py` and sync `workforces/workstate.md`.
- **Private by Default**: All new repositories must be created as private unless explicitly specified.
- **Portable Remote Git Links**: Never emit `file://` URIs or OS local paths (`/Users/...`, `/home/...`); use remote Git host URLs (GitHub, GitLab, Bitbucket, Azure DevOps, Gitea) or repo-relative POSIX paths.
- **Protect Uncommitted, Untracked & Ignored Files**: NEVER delete, truncate, overwrite, dehydrate, or discard files with uncommitted edits, untracked (`??`) local files, or `.gitignore`d (`!!`) files without explicit user consent. Verify `git status --porcelain=v1 --ignored=matching -- <path>` is empty before removing any file per [`wf-file-integrity`](wf-file-integrity.md) and `deploy_safety_hook.py`.

---

## 1b. Cross-Service Architecture, IaC Env Parity & Production-Default Ban

- **Read Repo OKF Architecture Index First**: When `<repo>/docs/index.md` exists, inspect it before planning or implementing any system-wired, integration, webhook, or configuration change so existing services, event subscribers, and grouping patterns are reused rather than duplicated.
- **IaC & Environment Variable Parity**: Before adding, renaming, or removing an environment variable or hardcoded secret/config value, inspect deployment configs (`template.yaml`, `template.yml`, `samconfig.toml`, `serverless.yml`, `.env.example`, Terraform/Helm/Compose files) to verify parity across every target environment.
- **Ban `"production"` Fallbacks**: NEVER hardcode `"prod"`, `"production"`, or `"live"` as fallback defaults in application code (e.g., `os.getenv("ENV", "production")`, `process.env.APP_ENV || "prod"`). Missing configuration must fail fast or derive explicitly from deployment config.
- **Config Outage != Code Workaround**: When an outage or integration failure stems from missing/mismatched deployment environment variables, fix or document the deployment config/runbook instead of writing code workarounds or `"production"` defaults.

---

## 2. Coordinator & Execution Topologies (`wf-agent-parallelization`)

When in auto-execution mode (`--auto`, `--all`, or `auto_delegate: true`):
- **Autonomous Execution**: Never stop between tasks to ask "Should I do task 2 now?". Proceed through unblocked tasks. Update task records and `workforces/workstate.md`, unblock downstream dependents, and iterate until all tasks are complete before outputting the final execution summary.
- **Topology Protocol**:
  1. **Horizontal Fan-Out (Parallel Worktrees)**: 2+ independent tasks $\rightarrow$ Spawn subagents with `Workspace: 'share'` (Git worktrees in `.worktrees/<slug>`). **NEVER run concurrent subagents in `Workspace: 'inherit'`.**
  2. **Vertical Relay**: Layered epic dependencies $\rightarrow$ Sequential relay using `gh stack`.
  3. **Direct Single-Branch**: Localized atomic fixes (< 1h, < 5 files).
- **Quality Triad & Developer Inspection Card**: Run unit tests, static typechecks, and linters before task handoff. Output Developer Inspection Card.

---

## 3. Discovered Gaps & Decision Escalation

- **Minor Gaps**: Auto-fix missing helpers, utilities, or assets within scope; log in `workforces/workstate.md` and continue.
- **Major / Breaking Decisions**: STOP immediately on breaking changes (OAuth requirement, breaking DB schema mutations, brand strategy pivots). Present 2–3 structured trade-offs to the user.

---

## 4. Implementation Plans & Fast Path

- **Mandatory Plans**: Greenfield epics and major architectural refactors require an `implementation_plan.md` artifact with an `## Existing Codebase Audit Findings` section.
- **Fast Path Exemption**: Localized bug fixes, targeted helper modifications, single-file edits (< 50 lines), and direct Q&A bypass implementation plans and pre-plan audit rituals per [`wf-lean-execution`](wf-lean-execution.md).

---

## 5. Factual Grounding & Hypotheses

- **Strict Factual Grounding**: Never fabricate customer quotes, metrics, or demand. Report pre-launch baselines explicitly.
- **Hypothesis Conversion**: Untested assumptions must be logged as falsifiable hypotheses in `workforces/hypotheses/` with measurable kill thresholds.

---

## 6. Conversational Recall & Tentative Inquiry

- **Thread Memory First**: When the user refers to past discussions, previous decisions, or earlier session context, consult immediate conversation thread history first. Do NOT automatically trigger disk-wide searches or inspect `workforces/session-context/`.
- **Tentative Answers & Graded Confidence**: State what you recall from the current thread or working context with transparent confidence (e.g., *"Based on our earlier discussion..."* or *"I recall we discussed retiring X, but the files still exist on disk"*).
- **Confirm Before Disk Cascades**: If thread memory is insufficient or ambiguous, ask the user before launching multi-file greps or historical transcript/session-context research cascades.

