---
name: doc-generator
description: Automated language-aware documentation generator discovery, extraction, and OKF catalog publisher.
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

### Step 1: Detect Project Stack
1. Scan project root for signature manifest files (`package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`).
2. Identify primary and secondary programming languages.

### Step 2: Extract & Convert to OKF
1. Run `code-graph` indexer first for baseline symbol indexing:
   ```bash
   python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog
   ```
   *(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py ...`)*
2. If native doc tools are installed or requested, invoke them to populate raw docs under `workforces/docs/`.
3. Synthesize API documentation into OKF concept files in `workforces/knowledge-catalog/docs/`.

---

## Output Location
All generated docs and indexes reside in the workspace directory:
- `workforces/knowledge-catalog/index.md`
- `workforces/knowledge-catalog/symbols/`
- `workforces/docs/`
