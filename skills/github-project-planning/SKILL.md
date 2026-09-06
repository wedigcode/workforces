---
name: github-project-planning
description: Integrates workforce tasks with GitHub Issues and GitHub Projects V2 boards. Reach for this skill when creating and tracking issues via the `gh` CLI, organizing tasks on project boards with custom fields (Status, Priority, Iteration), scoring and prioritizing backlogs with RICE/ICE methodologies, or reconciling local implementation plans with remote GitHub roadmaps.
---
# GitHub Project Planning & Task Generation Pipeline

Connect tasks to GitHub. Create issues, track them on a project board, set custom fields, execute strategic RICE/ICE planning cycles, and query the roadmap — all without hardcoding any owner, org, or project.

---

## Triggering & Execution

Connects GitHub Projects V2 and issues to the workforce planning cycle. Led by `@project-manager`:

### Coordinator & Command Invocations
- **Via `/wf-plan`**: Full strategic planning cycle (gap analysis, RICE scoring, GitHub issue sync).

### Prompt Triggers
- *"Sync tasks with GitHub project board"*
- *"Run strategic planning cycle and score tasks with RICE"*
- *"Create GitHub issues for active backlog items"*

---

## When to Use

- **Task Tracking & Storage:** Storing and tracking tasks that need to be completed.
- **Emergent Tasks & Ideas:** Capturing new tasks, bugs, refactor ideas, or feature ideas that pop up while you or another agent is completing work, and creating a GitHub issue for them immediately.
- Creating GitHub Issues from backlog tasks or gap analysis
- Adding issues to a GitHub Project V2 board
- Setting custom fields (Status, Priority, Size, Iteration, etc.) on project items
- Querying the roadmap by status or sprint
- Detecting when project fields have changed and keeping memory in sync

---

## 1. Memory

All config and cached state lives at:

```
workforces/memory/github-project-planning-skill.md
```

**If the file does not exist or is empty → trigger setup.** Tell the user:
> "No GitHub project config found. I need to walk through setup — it takes about 2 minutes."

Then run the setup flow in [Section 2](#2-setup) and write the results to memory before continuing.

### Memory Format

```markdown
# GitHub Project Planning — Memory

## Config
owner: {github-handle}
owner_type: user | org
last_synced: YYYY-MM-DD

## Projects
- name: {Project Name}
  number: {N}
  url: {project url}
  id: {PVT_...}
  tracked_repos:
    - owner/repo-name

## Custom Fields — {Project Name}
| Field       | Type         | Field ID   | Options / Notes           |
|-------------|--------------|------------|---------------------------|
| Status      | SingleSelect | PVTSSF_... | Todo · In progress · Done |
| Priority    | SingleSelect | PVTSSF_... | P0 · P1 · P2              |
| Size        | SingleSelect | PVTSSF_... | XS · S · M · L · XL      |
| Start date  | Date         | PVTF_...   | —                         |
| Target date | Date         | PVTF_...   | —                         |
| Iteration   | Iteration    | PVTIF_...  | Sprint-based              |

## Option IDs — {Project Name}
# Required for GraphQL mutations — SingleSelect fields need option node IDs, not names
Status / Todo:        {option-id}
Status / In progress: {option-id}
Status / Done:        {option-id}
Priority / P0:        {option-id}
Priority / P1:        {option-id}
Priority / P2:        {option-id}
```

---

## 2. Setup

Run when memory is missing or incomplete. Collect:

1. **Owner** — GitHub username or org name
2. **Owner type** — user or org (detect automatically):
   ```bash
   gh api users/{owner} 2>/dev/null && echo "user" || echo "org"
   ```
3. **Project** — list available projects and let the user pick:
   ```bash
   # User
   gh api graphql -f query='
     query($login: String!) {
       user(login: $login) {
         projectsV2(first: 20) { nodes { number title url id } }
       }
     }' -f login="{owner}"
   ```
4. **Tracked repos** — which repos will issues be created in?
5. **Custom fields** — fetch live and write to memory:
   ```bash
   gh api graphql -f query='
     query($owner: String!, $number: Int!) {
       user(login: $owner) {
         projectV2(number: $number) {
           fields(first: 30) {
             nodes {
               ... on ProjectV2Field { id name dataType }
               ... on ProjectV2SingleSelectField {
                 id name
                 options { id name }
               }
               ... on ProjectV2IterationField {
                 id name
                 configuration { iterations { id title startDate duration } }
               }
             }
           }
         }
       }
     }' -f owner="{owner}" -F number={project_number}
   ```

Write all discovered values to `workforces/memory/github-project-planning-skill.md` before proceeding.

---

## 3. Drift Detection

Run when:
- Starting any issue operation
- A GraphQL mutation fails with an invalid field ID error
- Explicitly asked to sync

**Algorithm:**
1. Fetch live fields (query from Section 2)
2. Compare to `## Custom Fields` table in memory
3. If added, removed, or changed options → show a diff:
   ```
   ⚠️ Project fields changed since last sync ({date})

   Added:   Team (SingleSelect)
   Removed: —
   Changed: Status — new option "Blocked" added

   Update memory? [Yes / No]
   ```
4. Yes → overwrite affected sections, update `last_synced`
5. No → continue with cached values (warn mutations may fail)

---

## 4. Issue Operations

### Rich Context Requirements
When creating a new issue (whether from a planning session or as an emergent task/idea that popped up during execution), you **must** ensure it has enough context so that *any* agent (human or AI) can pick it up and complete the work independently. 

Always format the issue body using the following template:

```markdown
## 📋 Goal & Objective
{Clear, detailed description of what needs to be accomplished and why.}

## 💻 Target Files & Directories
- `{absolute path or relative file URL to file1}` (e.g. `[filename](file:///path/to/file)`)
- `{absolute path or relative file URL to file2}`

## ✅ Acceptance Criteria
- [ ] {Concrete verification step 1}
- [ ] {Concrete verification step 2}
- [ ] {Test coverage/verification command to run}

## 💡 Implementation Details & Gotchas
- {Specific constraints, APIs to use, or design patterns to follow}
- {Any potential side effects or related systems to keep in mind}
- {References to existing examples or documentation}

## 🔗 Related & Blockers
- Supports Goal: {Goal description/reference}
- Depends on: #{issue_number} (if applicable)
```

### Create an Issue and Add to Project

```bash
# Step 1: Create the issue
ISSUE_URL=$(gh issue create \
  --repo {owner}/{repo} \
  --title "{title}" \
  --body "{body}" \
  --label "{labels}" \
  --assignee "@me" \
  --json url -q .url)

# Step 2: Get the issue node ID
ISSUE_ID=$(gh api graphql -f query='
  query($url: URI!) {
    resource(url: $url) { ... on Issue { id } }
  }' -f url="$ISSUE_URL" -q '.data.resource.id')

# Step 3: Add to project
ITEM_ID=$(gh api graphql -f query='
  mutation($project: ID!, $content: ID!) {
    addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
      item { id }
    }
  }' -f project="{project_id}" -f content="$ISSUE_ID" \
  -q '.data.addProjectV2ItemById.item.id')
```

### Set a Custom Field

```bash
# SingleSelect (e.g. Status = "In progress")
gh api graphql -f query='
  mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
    updateProjectV2ItemFieldValue(input: {
      projectId: $project
      itemId: $item
      fieldId: $field
      value: { singleSelectOptionId: $option }
    }) { projectV2Item { id } }
  }' \
  -f project="{project_id}" \
  -f item="{item_id}" \
  -f field="{field_id from memory}" \
  -f option="{option_id from memory}"

# Date field (e.g. Target date)
gh api graphql -f query='
  mutation($project: ID!, $item: ID!, $field: ID!, $date: Date!) {
    updateProjectV2ItemFieldValue(input: {
      projectId: $project
      itemId: $item
      fieldId: $field
      value: { date: $date }
    }) { projectV2Item { id } }
  }' \
  -f project="{project_id}" \
  -f item="{item_id}" \
  -f field="{field_id}" \
  -f date="YYYY-MM-DD"
```

> **Always read field IDs and option IDs from memory.** Never hardcode them.

---

## 5. Roadmap Query

```bash
gh api graphql -f query='
  query($project: Int!, $owner: String!) {
    user(login: $owner) {
      projectV2(number: $project) {
        items(first: 50) {
          nodes {
            content {
              ... on Issue {
                number title url state
                labels(first: 5) { nodes { name } }
              }
            }
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name field { ... on ProjectV2SingleSelectField { name } }
                }
                ... on ProjectV2ItemFieldDateValue {
                  date field { ... on ProjectV2Field { name } }
                }
              }
            }
          }
        }
      }
    }
  }' -f owner="{owner}" -F project={number}
```

> For **org** owners, replace `user(login: $owner)` with `organization(login: $owner)`.

**Present as:**

```markdown
### 🗺️ Roadmap — {Project Name}

| # | Title | Status | Priority | Size | Target |
|---|-------|--------|----------|------|--------|
| #12 | Build auth flow | In progress | P0 | M | 2026-03-01 |
```

---

## 6. Strategic Planning Cycle

When invoked by `/wf-plan`, execute the full planning cycle led by `@project-manager`:

1. **Step 0 — Load Config**: Read `workforces/memory/github-project-planning-skill.md`. If missing, trigger setup.
2. **Step 1 — Read the Landscape**: Read quarterly goals from `workforces/goals/`, active tasks from `workforces/workstate.md`, and the live GitHub board.
3. **Step 2 — Gap Analysis**: Compare goals vs. current backlog. For each key result, identify missing work and coverage gaps.
4. **Step 3 — Generate + Score Tasks**: Generate concrete tasks scored with **RICE** `(Reach × Impact × Confidence) ÷ Effort` or **ICE** `(Impact × Confidence × Ease)`.
5. **Step 4 — Update `workforces/workstate.md`**: After user approval, add new tasks to Active Tasks table sorted by priority score.
6. **Step 5 — Create GitHub Issues (P0 + P1)**: Create rich-context issues in the tracked repo, attach to project board, set custom fields (Status, Priority, Size), and sync issue number back to `workforces/workstate.md`.
7. **Step 6 — Present Roadmap**: Output weekly sprint view and highlight "The One Thing" P0 task.

---

## Rules

- **Read memory first.** Make live API calls only for drift detection or when memory is missing.
- **Never hardcode** owner, org, project number, repo, field IDs, or option IDs.
- **SingleSelect mutations require option IDs** (node ID strings), not option names.
- **Org vs user queries differ.** Check `owner_type` in memory before building GraphQL.
- **After any field mutation fails** → run drift check immediately.
