---
name: wf-memory-management
description: Navigates primary repository OKF architecture documentation (`<repo>/docs/index.md` and `docs/architecture/*.md`), manages persistent skill memory files (`workforces/memory/<skill-name>.md` with cached IDs, state, and timestamps), and reads/authors modular markdown knowledge catalogs in Open Knowledge Format (`workforces/knowledge-catalog/`). Reach for this skill when reading living system architecture cards before planning or coding, persisting skill state or config timestamps across sessions, or authoring cross-referenced markdown knowledge bases.
---
# Memory Management

Three memory and knowledge surfaces, each with a clear scope:

| Surface | Path | Who writes it | What it contains |
|---------|------|--------------|-----------------|
| **Living Repo Architecture** | `<repo>/docs/index.md` & `docs/architecture/*.md` | `wf-doc-generator`, engineers | Universal OKF architecture cards (`affected_files`, `doc_status`, blast radius, constraints) readable by every AI harness |
| **Skill memory** | `workforces/memory/<skill-name>.md` | The skill itself | Config, cached IDs, last-sync timestamps |
| **Knowledge catalog** | `workforces/knowledge-catalog/` | The user / project agents | Optional workforce-specific OKF domain playbooks & Canvas symbol exports (`code/`) |

---

## 1. Skill Memory

### Format

Each skill that needs persistent state stores a single plain-markdown file at:

```
workforces/memory/<skill-name>.md
```

The file is freeform markdown — no required schema. Use headers and tables. Keep it readable by a human in 30 seconds.

**Convention:**

```markdown
# <Skill Name> — Memory

## Config
key: value
key: value

## State
last_synced: YYYY-MM-DD
last_run: YYYY-MM-DDTHH:MM:SSZ

## Notes
- Any self-calibration or drift observations go here
```

### Rules

- **Always read before acting.** Check the memory file before any operation that depends on config (IDs, usernames, field names).
- **If missing or empty → trigger setup.** Tell the user what's needed and what to run.
- **After any config discovery** (e.g. user answers a setup question, a live API call returns IDs) → write the values back to the memory file immediately.
- **Write only what you know.** Never invent values. If a field is unknown, leave it blank or omit it.

### This skill's own state

```
workforces/memory/memory-management-skill.md
```

Tracks: last time memory was audited, any skills that registered themselves, notes on stale memory files.

---

## 2. Living Architecture Docs & Knowledge Catalog (OKF)

Use **two complementary OKF tiers**:
1. **Universal Repo Architecture (`<repo>/docs/` — PRIMARY for all harnesses)**: Stores `<repo>/docs/index.md` and `docs/architecture/*.md` cards with `affected_files:` globs and `## Constraints & Why` notes so non-Workforces agents also read system wiring and invariants.
2. **Workforce-Specific Domain Bundle (`workforces/knowledge-catalog/`)**: Optional internal catalog for workforce-only domain playbooks, Canvas symbol exports (`code/`), and analytics references.

### How to navigate

1. **Start at `<repo>/docs/index.md` (and `workforces/knowledge-catalog/index.md` if present):**
   The index lists all architecture cards and concepts with their `type`, `affected_files`, and `description`. Read it first before planning or reviewing system-wired changes.

2. **Parse the frontmatter:** Every concept file opens with YAML. Check `type` and `description` before reading the body.
   ```yaml
   ---
   type: API Endpoint        # What kind of thing this is
   title: Stripe Webhook     # Display name
   description: Handles incoming Stripe payment events and logs them.
   resource: https://api.stripe.com/webhooks
   tags: [payments, stripe, webhook]
   timestamp: 2026-07-15T00:00:00Z
   ---
   ```

3. **Follow links:** Concept files link to each other with standard markdown links. Follow them to gather related context (e.g. an API endpoint linking to its authentication scheme).

4. **Look for standard headers in the body:**
   - `## Schema` — tables, columns, field types
   - `## Examples` — code blocks showing usage
   - `## Citations` — external sources, docs, links

### OKF Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | ✅ Yes | Kind of concept (e.g. `OKF Index`, `Architecture Component`, `API Endpoint`, `Playbook`, `Dehydrated Spec Stub`). Consumers use this for routing. |
| `title` | Recommended | Human-readable name. Falls back to filename if omitted. |
| `description` | Recommended | One sentence. Used by indexes and search. |
| `affected_files` | For Architecture Cards | Array of repo-relative file globs covered by the card (checked by `post_code_reviewer.py` and `scaffold_repo_okf.py`). |
| `doc_status` | For Architecture Cards | `scaffold`, `documented`, or `stale`. |
| `last_verified_commit` | For Architecture Cards | Full Git SHA at which the card was last verified against code. |
| `updated_at` | Recommended | `YYYY-MM-DD` date last verified or modified. |
| `dehydrated` | For Archived Specs | `true` when a shipped PRD/spec has been collapsed into a commit-linked stub. |
| `resource` | Optional | URI of the underlying asset (DB URL, API base URL, etc.) |
| `tags` | Optional | Array of strings for filtering |
| `timestamp` | Optional | ISO 8601 last-modified time |

### Reserved filenames (do not use for concepts)

| Filename | Purpose |
|----------|---------|
| `index.md` | Directory listing — for progressive navigation |
| `log.md` | Chronological update history |

### System prompt for navigating OKF

When instructing an agent to use project OKF docs, include:

> *"Project architecture docs at `<repo>/docs/` (and optional domain catalogs at `workforces/knowledge-catalog/`) are formatted in Open Knowledge Format (OKF). Start by reading `<repo>/docs/index.md` first (then `workforces/knowledge-catalog/index.md` if present). Check YAML frontmatter (`type`, `doc_status`, `affected_files`, `description`) before loading full bodies, and load only the architecture cards matching the modules you are touching."*

---

## 3. Memory Lifecycle

```
Skill starts
     ↓
Read workforces/memory/<skill-name>.md
     ↓
[Missing / empty?] → Run setup → Write values to memory → Continue
[Present?] → Extract config → Continue
     ↓
Perform operation
     ↓
[Config changed or newly discovered?] → Update memory file
     ↓
Done
```

### Staleness detection

If a memory file has a `last_synced` date older than 7 days and the operation touches live external state (e.g. GitHub API), prompt:

```
⚠️ Memory last synced {N} days ago. Run a sync check to verify config is current.
```

Do not silently assume stale config is correct.
