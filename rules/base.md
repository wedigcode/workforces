---
trigger: always_on
---

# Workforces Base Rules

These rules apply to all workforces and projects. They are enforced by the AI agents at all times.

---

## GitHub Rules

- **All new GitHub repositories MUST be created as private** unless the user explicitly requests a public repo.
- Assigned issues and PRs are discovered by reading `workforces/workrules.md` (and the `workstate.md` tracker).
- Unassigned issues in configured repos should be surfaced as potential work items.
- Tasks should be saved as GitHub issues in the correct project repo for tracking.

## Repo Type Hierarchy

- **Workforce** – Central command. Can spawn sub-workforces or projects.
- **Project** – A specific initiative with its own repo and issue tracking.

## Rule Cascading

- A parent workforce can read all child `workforces/README.md` files to get context.
- A project should NOT need to know about other projects. Keep context scoped.
