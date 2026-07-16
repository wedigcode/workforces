---
name: memory-management
description: Provides persistent local memory for skills and a protocol for reading project knowledge catalogs in Open Knowledge Format (OKF). Use whenever a skill needs to read or write its own config/state, or when an agent needs to navigate a project's knowledge-catalog/ directory.
---

# Memory Management

Two distinct memory surfaces, two distinct purposes:

| Surface | Path | Who writes it | What it contains |
|---------|------|--------------|-----------------|
| **Skill memory** | `workforces/memory/<skill-name>.md` | The skill itself | Config, cached IDs, last-sync timestamps |
| **Knowledge catalog** | `workforces/knowledge-catalog/` | The user / project agents | OKF-formatted knowledge about projects, systems, and resources |

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

## 2. Knowledge Catalog (OKF)

The `workforces/knowledge-catalog/` directory is an **Open Knowledge Format (OKF) bundle** — a collection of markdown files with YAML frontmatter describing the project's systems, APIs, data sources, and resources.

This is a **read surface** for agents in most cases. The project owner or enrichment agents write it; workforce agents read it to gain context.

### How to navigate

1. **Start at the index:**
   ```
   workforces/knowledge-catalog/index.md
   ```
   The index lists all concepts with their `type` and `description`. Read it first to find the right file.

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
| `type` | ✅ Yes | Kind of concept (e.g. `API Endpoint`, `Playbook`, `BigQuery Table`, `Metric`). Consumers use this for routing. |
| `title` | Recommended | Human-readable name. Falls back to filename if omitted. |
| `description` | Recommended | One sentence. Used by indexes and search. |
| `resource` | Optional | URI of the underlying asset (DB URL, API base URL, etc.) |
| `tags` | Optional | Array of strings for filtering |
| `timestamp` | Optional | ISO 8601 last-modified time |

### Reserved filenames (do not use for concepts)

| Filename | Purpose |
|----------|---------|
| `index.md` | Directory listing — for progressive navigation |
| `log.md` | Chronological update history |

### System prompt for navigating OKF

When instructing an agent to use the catalog, include:

> *"The knowledge catalog at `workforces/knowledge-catalog/` is formatted in Open Knowledge Format (OKF). Start by reading `index.md` to get a directory listing. Parse the YAML frontmatter of each file to check its `type` and `description` before loading the full body. Follow markdown links within files to gather related concepts. Do not load all files at once — navigate progressively using the index."*

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
