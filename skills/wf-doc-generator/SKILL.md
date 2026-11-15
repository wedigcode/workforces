---
name: wf-doc-generator
description: Auto-discovers project programming languages (TypeScript, Python, Go, Rust) and executes native documentation generators (TypeDoc, pydoc, go doc, cargo doc) to export structured API references. Reach for this skill when generating or refreshing technical documentation, publishing an Open Knowledge Format (OKF) catalog under `workforces/knowledge-catalog/`, or onboarding to an unfamiliar codebase needing extracted architectural references.
---
# Skill: Automated Documentation Generator

Detects project programming language, discovers native documentation generators (TypeDoc, pydoc/sphinx, go doc, cargo doc, etc.), extracts API docs, and formats them into the `workforces/knowledge-catalog/` directory using Open Knowledge Format (OKF).

---

## Language Auto-Discovery Matrix

| Language | Primary Signal Files | Native / Standard Doc Tool | Extraction Command |
|----------|----------------------|----------------------------|--------------------|
| **TypeScript / JS** | `package.json`, `tsconfig.json` | `typedoc`, `jsdoc`, `graph_indexer.py` | `npx -y typedoc --json workforces/docs/typedoc.json` |
| **Python** | `pyproject.toml`, `setup.py`, `requirements.txt` | `pydoc`, `sphinx`, `graph_indexer.py` | `python3 -m pydoc -w ./` |
| **Go** | `go.mod` | `go doc` | `go doc -all ./...` |
| **Rust** | `Cargo.toml` | `cargo doc` | `cargo doc --no-deps` |
| **Java** | `pom.xml`, `build.gradle` | `javadoc` | `javadoc -d workforces/docs/javadoc` |

---

## Execution Protocol

### Step 1: Detect Project Stack & Scaffold Repo-Local OKF Docs (`<repo>/docs/`)
Save architecture docs directly inside **`<repo>/docs/`** so all coding harnesses (even without Workforces installed) share architecture context:
1. Run the non-destructive OKF scaffolder across PHP, Go, Node/TypeScript, Python, Rust, and AWS SAM/IaC:
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --scan ./
   ```
   *(Fallback: `python3 skills/wf-doc-generator/scripts/scaffold_repo_okf.py --scan ./`)*
2. Inspect and enrich generated `<repo>/docs/index.md` and `docs/architecture/*.md` cards (`affected_files:` frontmatter globs + concise `## Constraints & Why` entries — never maintain a redundant `CHANGELOG.md`).

### Step 2: Repo Hygiene Audit & Dehydrating Shipped PRDs/Specs
1. Audit stray root files, bulky shipped PRDs/specs, and undocumented services (protects dirty, untracked, and Git-ignored files; never deletes files):
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --audit-hygiene ./
   ```
2. Collapse shipped PRDs/specs into permanent commit-linked stubs (retaining short summary + Git SHA snapshot link). Refuses specs with uncommitted edits or untracked status (`git status --porcelain=v1 --ignored=matching` must be clean and match `HEAD`); NEVER delete specs or root docs without explicit user consent:
   ```bash
   python3 .agents/skills/wf-doc-generator/scripts/scaffold_repo_okf.py --dehydrate-spec docs/specs/example-prd.md --living-doc docs/architecture/service.md
   ```

### Step 3: Optional Native Extractors & Canvas Symbol Index
- Native extractors (`typedoc`, `pydoc`, `go doc`, `cargo doc`) or optional symbol graph exports (`wf-code-graph`) may supplement `<repo>/docs/` when deep API dumps are needed.

---

## Output Location
- **Primary Architecture Surface (Universal)**: `<repo>/docs/index.md`, `<repo>/docs/architecture/*.md`
- **Optional Deep Reference Cache**: `workforces/docs/`, `workforces/knowledge-catalog/code/`
