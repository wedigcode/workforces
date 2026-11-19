---
name: wf-doc-generator
description: Generates and maintains living Open Knowledge Format (OKF) architecture documentation under `<repo>/docs/` (`docs/index.md` and `docs/architecture/*.md`), concise source-file boundary docblocks and inline 'why' comments, ranked documentation-gap recommendations, and optional API reference documentation for TypeScript, Python, PHP, Go, Rust, and IaC packages into an Open Knowledge Format catalog (`workforces/knowledge-catalog/code/`). Reach for this skill when scaffolding or enriching repo architecture cards, onboarding to an unfamiliar codebase, documenting high-blast-radius modules for safer refactoring, or dehydrating shipped PRDs.
---
# Skill: Living Architecture & Code Documentation Generator

Maintains universal, agent- and human-readable Open Knowledge Format (OKF) architecture docs inside **`<repo>/docs/`** (`docs/index.md` + `docs/architecture/*.md`), paired with concise source-file docblocks and inline *"why"* comments so every coding harness and developer has immediate wiring, blast-radius, and verification context.

---

## Stack & Language Auto-Discovery Matrix

| Stack / Language | Primary Signal Files | OKF Architecture Card | Optional Native API Extractor |
|---|---|---|---|
| **PHP** | `composer.json`, `src/EventSubscriber/`, `src/Service/` | `docs/architecture/php-backend.md` | `phpdoc` / `graph_indexer.py` |
| **TypeScript / JS** | `package.json`, `tsconfig.json` | `docs/architecture/node-typescript.md` | `npx -y typedoc --json workforces/docs/typedoc.json` |
| **Python** | `pyproject.toml`, `setup.py`, `requirements.txt` | `docs/architecture/python-modules.md` | `python3 -m pydoc -w ./` |
| **Go** | `go.mod`, `cmd/`, `internal/`, `pkg/` | `docs/architecture/go-services.md` | `go doc -all ./...` |
| **Rust** | `Cargo.toml`, `crates/` | `docs/architecture/rust-crates.md` | `cargo doc --no-deps` |
| **Java** | `pom.xml`, `build.gradle` | `docs/architecture/<module>.md` | `javadoc -d workforces/docs/javadoc` |
| **IaC / Deployment** | `template.yaml`, `samconfig.toml`, `serverless.yml` | `docs/architecture/iac-deployment.md` | IaC parameter & env parity cross-check |

---

## Refactor-Ready OKF Architecture Card Schema (`<repo>/docs/architecture/<module>.md`)

Every module architecture card should stay concise, factual, and scannable so agents save tokens and avoid regressions during refactoring:

```yaml
---
type: Architecture Component
title: "<Human-Readable Module Name>"
description: "<One-sentence summary of role and responsibility.>"
doc_status: "documented"      # scaffold | documented | stale
last_verified_commit: "<git_sha>"
affected_files:
  - "src/billing/**/*"
tags: [billing, payments, webhook]
updated_at: "YYYY-MM-DD"
---
```

Required body sections:
1. **`## Purpose & Boundaries`** — What this module owns vs. explicitly does *not* own.
2. **`## Entrypoints, Events & Data Flow`** — Controllers, routes, CLI commands, queues, event subscribers/listeners, external APIs, and database tables.
3. **`## Key Dependencies & Blast Radius`** — Upstream services called and high-fan-in downstream callers that break if contracts change.
4. **`## Environment & Deployment Config`** — Exact env vars read by the module and their IaC/manifest source (`template.yaml`, `samconfig.toml`, `.env.example`). Never hardcode `"prod"`/`"production"` defaults.
5. **`## Test Coverage & Verification`** — Matching test file paths and exact test/lint/typecheck commands to verify edits.
6. **`## Constraints, Invariants & Gotchas`** — Dated bullets explaining non-obvious invariants and *why* choices exist (replaces keeping a separate `CHANGELOG.md`).

---

## Code Docblocks & Inline Documentation Protocol

Architecture cards tell agents *where* things connect; concise inline source docs prevent misreads when editing files directly:
- **Module & Class Boundary Docblocks**: Keep a short 2–4 line docstring/comment on services, controllers, event subscribers, and integration handlers describing responsibility, events handled, and external config assumptions.
- **Public & High-Fan-In Functions**: Document non-obvious parameters, return contracts, side effects, and error conditions on public functions/methods referenced across modules.
- **Inline *"Why"* Comments**: Add brief inline comments only for non-obvious invariants, ordering constraints, race-condition guards, or workarounds—never narrate obvious syntax (`# increment counter`).
- **Quality Gate After Code Edits**: Whenever modifying source files to add docblocks/comments, run `post_code_reviewer.py --root ./ --run-checks --strict` before opening a Draft PR.

---

## Execution Protocol

### Step 1: Discover Gaps & Scaffold `<repo>/docs/`
1. Non-destructively scaffold `<repo>/docs/index.md` and starter cards, and auto-index **all** `docs/architecture/*.md` cards (including custom domain cards with `doc_status`):
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --scan ./
   ```
   *(Fallback: `python3 skills/wf-doc-generator/scripts/scaffold_repo_okf.py --scan ./`)*
2. Rank undocumented, scaffold-only, stale, or low-docblock modules by external caller blast radius and size:
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --recommend-docs ./ --json
   ```

### Step 2: Enrich Cards & Inline Docblocks
1. Inspect the recommended module, its matching tests, env vars, and callers (`pre_impact_analyzer.py --file <entry>`).
2. Author or enrich `<repo>/docs/architecture/<module>.md` using the Refactor-Ready OKF schema above (`doc_status: documented`, `last_verified_commit: <HEAD>`).
3. Add concise boundary docblocks, public docstrings, and *"why"* inline comments in that module's source files.
4. Re-run `scaffold_repo_okf.py --scan ./` so `docs/index.md` updates the module's status and summary table non-destructively.

### Step 3: Repo Hygiene Audit & Dehydrating Shipped PRDs/Specs
1. Audit stray root files, bulky shipped PRDs/specs, stale `affected_files:` globs, and doc gaps (protects dirty, untracked, and Git-ignored files; never deletes files):
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --audit-hygiene ./
   ```
2. Collapse shipped PRDs/specs into permanent commit-linked stubs (retaining short summary + Git SHA snapshot link). Refuses specs with uncommitted edits or untracked status (`git status --porcelain=v1 --ignored=matching` must be clean and match `HEAD`); NEVER delete specs or root docs without explicit user consent:
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --dehydrate-spec docs/specs/example-prd.md --living-doc docs/architecture/service.md
   ```

### Step 4: Optional Deep API Reference Cache
- Native extractors (`typedoc`, `pydoc`, `go doc`, `cargo doc`) or optional Canvas symbol exports (`wf-code-graph --build-okf`) write supplemental API dumps to `workforces/docs/` and `workforces/knowledge-catalog/code/` when deep symbol catalogs are needed.

---

## Output Location
- **Primary Universal Surface (All Harnesses + Humans)**: `<repo>/docs/index.md`, `<repo>/docs/architecture/*.md`, and concise source-file docblocks/comments.
- **Optional Deep Reference Cache**: `workforces/docs/`, `workforces/knowledge-catalog/code/`
