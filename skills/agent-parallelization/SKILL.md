---
name: agent-parallelization
description: Enables safe concurrent multi-agent software engineering using isolated Git worktrees, stacked PRs (`gh-stack`), and conflict resolution (`git rerere`). Reach for this skill when dispatching multiple coding subagents concurrently, fanning out independent backlog tasks, building multi-layer epics that require dependent PR chains without blocking on review, or preventing `.git/index.lock` collisions and dirty working tree crosstalk across parallel sessions.
---
# Multi-Agent Parallelization & GitHub gh-stack Orchestration

A unified framework for orchestrating multiple AI agents working concurrently on a codebase without filesystem cross-contamination, Git index lock contention, or merge conflict chaos. Integrates Git worktrees (`Workspace: 'share'`) and GitHub's official stacked PR CLI (`github/gh-stack`).

---

## When to Use

- **Post-Meeting Backlog Fan-Out:** When multiple independent bugs or issues need to be resolved simultaneously by parallel subagents.
- **Deep Multi-Layer Epics:** When a single large feature spans multiple architectural layers (Database Schema ➔ Service/API Endpoints ➔ Frontend UI Components ➔ Integration Tests) and must be submitted as a chain of reviewable, stacked pull requests.
- **Parallel Coding Safeguards:** Whenever two or more coding subagents are invoked concurrently, ensuring zero `.git/index.lock` collisions or dirty working tree crosstalk.
- **Cascading Rebase & Conflict Management:** Keeping multi-layer branches cleanly rebased onto trunk as upstream changes merge, leveraging `git rerere` to eliminate repetitive conflict resolution.

---

## 1. The 3 Execution Topologies (Topology Selector)

Before delegating programming tasks, the primary Coordinator or `@project-manager` MUST evaluate the dependency graph and explicitly select one of three execution topologies:

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

### Mode 1: Parallel Isolated Worktrees (Horizontal Fan-Out)
- **Use Case:** 2+ independent issues or bugs touching separate subsystems (e.g. billing webhook fix + settings modal redesign + analytics export).
- **Subagent Invocation Mode:** MUST specify `Workspace: 'share'` or dedicated Git worktree.
- **Filesystem Rule:** **NEVER run parallel coding subagents in `Workspace: 'inherit'`.** Git is single-threaded per working directory. Concurrent checkout or staging in a shared folder causes `.git/index.lock` failures and working tree corruption.
- **Topology Mechanics:**
  1. Coordinator creates an isolated worktree for each task:
     ```bash
     git worktree add .worktrees/<task-slug> -b feat/<task-slug>
     ```
  2. Subagent executes entirely inside `.worktrees/<task-slug>/`.
  3. Subagent tests, commits, and opens an independent PR via `gh pr create` (or independent `gh stack submit` if internally multi-layered).
  4. Worktree is pruned after completion:
     ```bash
     git worktree remove .worktrees/<task-slug>
     ```

### Mode 2: Vertical Relay (Linear Stack via `gh-stack`)
- **Use Case:** A single complex feature or epic with strict sequential layer dependencies:
  - *Layer 1:* Database migrations & data models
  - *Layer 2:* Service logic & API endpoints
  - *Layer 3:* Frontend UI components & forms
  - *Layer 4:* End-to-end tests & documentation
- **Coordination Rule:** **Do NOT execute agents in parallel on the same branch chain.** Execute as a sequential assembly line / relay:
  1. `@programmer` (Backend) initializes stack:
     ```bash
     gh stack init feat/<epic>-data
     # writes schema, models, unit tests -> commits
     ```
  2. `@programmer` (API) stacks the next layer:
     ```bash
     gh stack add feat/<epic>-api
     # implements endpoints on top of data layer -> commits
     ```
  3. `@designer` / `@programmer` (Frontend) stacks UI:
     ```bash
     gh stack add feat/<epic>-ui
     # builds components on top of API layer -> commits
     ```
  4. Coordinator submits the stack to GitHub:
     ```bash
     gh stack submit
     ```
- **Review Mechanics:** GitHub automatically configures parent-child base branches:
  - PR #1 base: `main`
  - PR #2 base: `feat/<epic>-data`
  - PR #3 base: `feat/<epic>-api`
  Reviewers review each small layer diff in isolation. When PR #1 merges, GitHub and `gh stack sync` automatically re-target PR #2 to `main`.

### Mode 3: Single Branch Direct
- **Use Case:** Simple, atomic bug fixes, copy tweaks, or localized changes that take <1 hour and touch <5 files.
- **Execution:** Standard single branch off `main`, executed directly without worktree or stacking overhead.

---

## 2. GitHub gh-stack CLI Protocol

The `gh-stack` CLI extension (`github/gh-stack`) manages local stack metadata in `.git/gh-stack` and synchronizes with GitHub's Stacked PRs infrastructure.

### Core Command Reference

| Command | Action | When to Use |
| :--- | :--- | :--- |
| `gh stack init [branch]` | Initializes a new stack targeting the trunk (`main`) | Start of Layer 1 in a vertical epic |
| `gh stack add <branch>` | Adds a new layer branch on top of the current stack | Start of Layer 2, 3, etc. |
| `gh stack add -Am "<msg>"` | Stages all changes, commits, and creates a layer | Fast layer commit |
| `gh stack view` | Displays the current ASCII stack hierarchy and PR status | Inspecting stack layers |
| `gh stack switch` | Interactively switches between layers in the current stack | Navigating layers during development |
| `gh stack checkout <ref>` | Checks out a stack by stack #, PR #, or branch name | Inspecting or resuming work on a stack |
| `gh stack rebase` | Rebases the entire stack onto trunk or parent layers | Syncing after local changes |
| `gh stack sync` | Pulls trunk, cascade-rebases stack branches, syncs GitHub | When trunk moves or PRs merge |
| `gh stack submit` | Pushes branches and creates/updates linked GitHub PRs | Publishing the stack for review |
| `gh stack bottom` / `top` | Checks out the base (bottom) or tip (top) branch of the stack | Fast traversal |
| `gh stack up` / `down` | Moves one layer up (away from trunk) or down (toward trunk) | Step-by-step verification |

---

## 3. Merge Conflict Elimination & `git rerere`

Merge conflicts are the biggest friction point in parallel agent execution. Workforces uses a three-tier defense:

### 1. Automatic `git rerere` (Reuse Recorded Resolution)
- `gh stack init` **automatically enables `git rerere`** in the repository config (`rerere.enabled = true`).
- **How it works:** When a merge or rebase conflict is resolved and committed, Git records the pre-resolution and post-resolution diff chunks in `.git/rr-cache`.
- If the same conflict occurs during subsequent cascade rebases (e.g. across Layer 2 and Layer 3, or when syncing with updated trunk), Git automatically reapplies the recorded resolution without human or agent intervention.

### 2. Cascading Rebase via `gh stack sync`
When upstream `main` moves forward:
```bash
gh stack sync
```
1. Fetches latest trunk (`main`).
2. Cascade-rebases all stack branches onto their updated parents in sequence.
3. If a conflict occurs, rebase pauses and identifies conflicted files with line numbers.
4. The programmer resolves the conflict, stages changes (`git add .`), and runs:
   ```bash
   gh stack rebase --continue
   ```
5. All downstream branches inherit the resolution cleanly.

### 3. Hotspot File Partitioning
High-traffic shared files (`package.json`, `pnpm-lock.yaml`, route tables, schema files, barrel `index.ts` exports) represent 90% of merge conflicts.
- **Protocol:**
  - Before launching parallel agents, the Coordinator must identify shared hotspot files.
  - If two tasks require new dependencies in `package.json`, install dependencies **first** in trunk or Layer 1 before branching parallel workers.
  - Separate route definitions into modular sub-routers rather than appending to a monolithic router file.

---

## 4. Developer Testing & Worktree Inspection Protocol

Because worktrees share the root repository's `.git` database, testing agent branches is frictionless and requires zero stashing.

### Testing Options

#### Option A: In-Place Testing (Side-by-Side Verification)
Test the agent's code directly in its worktree directory without touching your main workspace:
```bash
# Navigate to the agent's worktree
cd .worktrees/<task-slug>

# Run unit / integration tests
npm test # or pytest, cargo test

# Spin up a dev server on an alternate port
PORT=3001 npm run dev
```

#### Option B: Main Workspace Checkout
Once the agent completes its commit:
```bash
git checkout feat/<task-slug>
# or
gh stack checkout feat/<task-slug>
```

#### Option C: Layered Stack Stepping
Traverse through each layer of a stacked feature:
```bash
gh stack bottom   # Test Layer 1 (Schema / Models)
gh stack up       # Test Layer 2 (API Routes)
gh stack top      # Test Layer 3 (Full UI)
```

### Developer Inspection Card
Whenever a subagent completes work in an isolated worktree or stack, the Coordinator MUST format the completion notification as a **Developer Inspection Card**:

```markdown
### 🧪 Feature Ready for Review: [Task Title]
- **Topology:** [Parallel Worktree | Vertical Stack Layer N of M | Direct]
- **Branch:** `feat/<branch-name>`
- **Worktree Path:** `.worktrees/<task-slug>/`
- **In-Place Test:** `cd .worktrees/<task-slug> && npm test`
- **Dev Server:** `cd .worktrees/<task-slug> && PORT=3001 npm run dev`
- **GitHub PR:** [PR URL or "Run `gh stack submit` to publish"]
```

---

## 5. Worktree Lifecycle & Cleanup Protocol

1. **Creation:**
   ```bash
   git worktree add .worktrees/<slug> -b feat/<slug>
   ```
2. **Exclusion:** Ensure `.worktrees/` is listed in `.gitignore` to prevent tracking worktree folders.
3. **Completion & Pruning:**
   When a task is merged or completed:
   ```bash
   # Remove the worktree directory and git administrative metadata
   git worktree remove .worktrees/<slug>
   
   # Clean up any stale worktree references
   git worktree prune
   ```
