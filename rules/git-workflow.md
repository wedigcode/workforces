# Rule: Autonomous Git Commits, Workspace Topologies & PR Review Discipline

These rules govern all git operations, commit cadences, workspace topologies, and pull request generation across workforce sessions for **any project and codebase**.

---

## 1. Zero Blockers Mandate & GitHub PR-First Code Review

- **Direct Execution Permission:** The AI has direct permission and capability to execute `git add`, `git commit`, `git push`, and `gh pr create` (or `gh stack submit`).
- **No Blocking for Commit Approvals:** **Do NOT ask the user for permission to create standard commits or push feature branches.** Proceed autonomously whenever a deterministic commit milestone is reached.
- **GitHub PR-First Code Review Paradigm:**
  - Code reviews belong **inside GitHub Pull Requests**—not in local terminal blocking gates.
  - With high-velocity AI generation and multi-agent parallelization, pausing execution for local pre-commit human reviews creates unnecessary bottlenecks.
  - The AI commits and pushes autonomously, elevating code review to GitHub PRs where inline diffs, line comments, automated CI quality gates, and asynchronous peer/bot reviews occur naturally.

---

## 2. Workspace Topologies & Parallelization Selector (Declare Up-Front)

Before modifying code, creating branches, or running tasks, the AI agent or Coordinator MUST evaluate task dependencies and select one of three execution topologies:

```
TOPOLOGY 1: PARALLEL WORKTREES         TOPOLOGY 2: VERTICAL RELAY          TOPOLOGY 3: DIRECT SINGLE-BRANCH
    (Horizontal Fan-Out)                 (gh-stack Linear Chain)               (Atomic Local Fix)

         main (trunk)                          main (trunk)                       main (trunk)
       ┌──────┼──────┐                              │                                  │
       ▼      ▼      ▼                              ▼                                  ▼
    Task A  Task B  Task C                 Layer 1: Schema (PR #1)                Fix Branch (1 PR)
   (Worktree(Worktree(Worktree                      │
      w1)     w2)     w3)                           ▼
       │      │      │                     Layer 2: API    (PR #2)
    (Independent PRs that                           │
     can merge in any order)                        ▼
                                           Layer 3: UI     (PR #3)
```

### Topology 1: Parallel Isolated Worktrees (Horizontal Fan-Out)
- **Use Case:** 2+ independent issues, bugs, or feature tasks touching separate modules.
- **Isolation Rule:** Subagents MUST run with `Workspace: 'share'` in dedicated Git worktrees.
  ```bash
  git worktree add .worktrees/<task-slug> -b feat/<task-slug>
  ```
- **Filesystem Safety:** **NEVER run concurrent coding agents in `Workspace: 'inherit'`.** Git is single-threaded per working tree. Concurrent staging or checkouts in the root directory cause `.git/index.lock` collisions and working tree corruption.
- **Pruning:** When the task PR is submitted, clean up the worktree:
  ```bash
  git worktree remove .worktrees/<task-slug> && git worktree prune
  ```

### Topology 2: Vertical Relay (Linear Stack via `gh stack`)
- **Use Case:** A single epic with sequential architectural layer dependencies (e.g. Migration/Schema ➔ Service/API ➔ Frontend UI ➔ Integration Tests).
- **Execution Protocol:** Agents execute sequentially in a relay:
  ```bash
  gh stack init feat/<epic>-data    # Layer 1: Schema & models
  gh stack add feat/<epic>-api      # Layer 2: API endpoints
  gh stack add feat/<epic>-ui       # Layer 3: UI components
  gh stack submit                   # Submits stacked PR chain to GitHub
  ```
- **Conflict Auto-Resolution:** `gh stack init` enables `git rerere` (`rerere.enabled = true`) to remember and auto-resolve merge conflicts during downstream cascade rebases (`gh stack sync`).

### Topology 3: Direct Single-Branch
- **Use Case:** Localized, atomic bug fixes, copy corrections, or minor refactors taking <1 hour and touching <5 files.
- **Execution:** Create a standard feature branch off default branch:
  ```bash
  git checkout -b <type>/<task-slug>
  ```

### Branch Naming Convention
All branches MUST follow the standard convention:
`<type>/<task-id-or-slug>`
- `feat/TASK-043-git-workflow`
- `fix/issue-12-auth-null-check`
- `refactor/api-response-normalization`
- `chore/upgrade-deps`

---

## 3. Universal Stack-Agnostic Quality Gates

Before creating a commit for a completion milestone or submitting a PR, the agent MUST run the project's quality verification triad. The agent dynamically detects the stack from root project manifests:

| Tech Stack | Manifest | Unit Tests | Static Analysis / Types | Linter / Style | Build Check |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Node / TS / JS** | `package.json` | `npm test` / `pnpm test` | `npx tsc --noEmit` | `npx biome check` / `npm run lint` | `npm run build` |
| **Python** | `pyproject.toml`, `requirements.txt` | `pytest` / `python3 -m unittest` | `mypy --strict` / `pyright` | `ruff check` / `flake8` | `python3 -m build` |
| **Go** | `go.mod` | `go test ./...` | `go vet ./...` | `golangci-lint run` | `go build ./...` |
| **Rust** | `Cargo.toml` | `cargo test` | `cargo check` | `cargo clippy -- -D warnings` | `cargo build --release` |
| **PHP** | `composer.json` | `vendor/bin/phpunit` / `pest` | `vendor/bin/phpstan` | `vendor/bin/pint` / `phpcs` | N/A |
| **Ruby** | `Gemfile` | `bundle exec rspec` | `bundle exec srb tc` (Sorbet) | `bundle exec rubocop` | N/A |
| **General / Workforce** | Repository Root | `python3 .agents/skills/post-code-review/scripts/post_code_reviewer.py --root ./ --run-checks --strict` |

**Zero-Failing Gates Rule:** If any test fails, static analysis detects type errors, or linters report violations, **do NOT commit a completion gate or open a ready PR**. Fix and re-verify all errors first.

---

## 4. The 5 Deterministic Commit Milestones

The AI MUST automatically create a conventional commit upon reaching any of the following milestones:

1. **Task Completion Gate:** Immediately after marking a task in `workforces/tasks/` as `done` and verifying that all unit tests, static analysis, and builds pass with 0 errors.
2. **Structural Scaffolding & Manifest Setup:** Immediately after scaffolding a new framework, package, monorepo app, cloud backend, database schema, or migration, *before* writing UI or application logic.
3. **Approved Specs & Architecture:** When a formal specification (`DESIGN.md`, `LANDING_PAGE_SPEC.md`, `product-brief.md`, ADRs) is authored and approved.
4. **Atomic Refactoring & Quality Increments:** When completing a clean, self-contained sub-step (e.g. extracting a shared helper, restructuring a module) that passes verification.
5. **Session / Turn Handoff & Branch Switch:** Before concluding any substantive session turn or switching branches, ensure the working tree is clean. Never leave uncommitted production code.

---

## 5. Conventional Commit Protocol

All commits MUST adhere strictly to Conventional Commits:
- `feat(<scope>): <summary>` for new features or user-facing components.
- `fix(<scope>): <summary>` for bug fixes or copy corrections.
- `docs(<scope>): <summary>` for documentation and specification files.
- `style(<scope>): <summary>` for CSS tokens, visual polish, and layout adjustments.
- `refactor(<scope>): <summary>` for code restructuring without behavioral change.
- `test(<scope>): <summary>` for adding or updating unit/integration tests.
- `chore(<scope>): <summary>` for dependency installations, toolchain setups, and configs.

**Lineage in Commit Body:** Always reference the associated task or issue:
```git
feat(auth): add OAuth2 PKCE callback handler

- Implements PKCE token exchange with state validation
- Adds unit tests covering token expiry and invalid states
- Passes static typecheck with 0 errors

Task: workforces/tasks/20260906-auth-pkce.md
Resolves #42
```

---

## 6. Pull Request Discipline via `gh` CLI

When completing a feature branch or epic:

### Step 1: Remote Push
```bash
git push -u origin <branch-name>
```

### Step 2: High-Quality PR Generation
Create the pull request using `gh pr create` with a structured, review-ready description:

```bash
gh pr create \
  --title "feat(scope): concise title in conventional commit format" \
  --body "$(cat <<'EOF'
## 🎯 Overview & Intent
Brief summary of changes, motivation, and Job-to-be-Done (JTBD) addressed.

## 🔗 Linked Tasks & Issues
- Resolves #<issue-number>
- Task: `workforces/tasks/<task-file>.md`

## 🏗️ Architectural & Component Changes
- **Data & Schema:** Database models, migrations, or contract updates.
- **Backend / API:** Services, route handlers, middleware.
- **Frontend / UI:** Components, pages, styling tokens.
- **Tests & Toolchain:** Test suites, configs, or CI scripts.

## 🧪 Quality Gate Verification Proof
- [x] **Unit Tests:** `<X> passing, 0 failures` (e.g. `npm test`, `pytest`, `cargo test`)
- [x] **Static Analysis / Types:** `0 errors` (e.g. `tsc --noEmit`, `mypy --strict`)
- [x] **Code Styling & Linting:** Clean (e.g. `biome check`, `ruff check`)
- [x] **Build Status:** Verified production build (e.g. `npm run build`, `cargo build`)

## 🛡️ Self-Review & Security Considerations
- [x] Untrusted inputs sanitized; no SQL/command injection vectors.
- [x] Authentication & authorization checks enforced at boundaries.
- [x] Zero swallowed errors or empty catch blocks.
- [x] Backward-compatibility verified; no undocumented breaking API changes.

## 📋 Reviewer Inspection Guide
Step-by-step instructions for human or bot review:
```bash
# Checkout and test branch in worktree
git worktree add .worktrees/review-<slug> <branch-name>
cd .worktrees/review-<slug>

# Run verification suite
<test-command>

# Start local preview (if applicable)
PORT=3001 <dev-server-command>
\`\`\`
EOF
)"
```

### Step 3: Multi-Repository Scoping Compliance
- Always pass `--repo <owner/repo>` if operating in multi-repo workforce configurations defined in `workforces/workrules.md` / `workstate.md`.

### Step 4: Draft vs. Ready State
- **Draft PRs (`--draft`):** Open as draft for intermediate check-ins, multi-agent work in progress, or awaiting upstream dependencies.
- **Ready for Review:** Once all quality gates pass and tests are green, transition to ready:
  ```bash
  gh pr ready <pr_number>
  ```
