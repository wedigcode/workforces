---
name: wf-code-graph
description: Constructs AST-based code graphs, indexes functions and classes, and maps call dependencies across codebases without external dependencies. Reach for this skill before authoring new functions to search for existing implementations and prevent duplicate code, when assessing the blast radius and cascading call impacts of a refactor, when feeding symbol/fan-in telemetry into `wf-doc-generator`, or when optionally exporting an Open Knowledge Format (OKF) symbol catalog for `wf-canvas`.
---
# Skill: Code Graph & Method Indexer

Provides lightweight, zero-dependency symbol indexing (`workforces/code-graph.json`) and call graph blast-radius mapping that feeds `pre_impact_analyzer.py`, `wf-doc-generator` (`--recommend-docs`), targeted symbol deduplication sweeps, and optional **`wf-canvas`** symbol catalogs.

> [!NOTE]
> For cross-harness architecture understanding and pre-plan wiring checks, prefer **`<repo>/docs/index.md`** (`wf-doc-generator`) + 1 codebase analog rather than running a full `graph_indexer.py --build-okf` scan.

---

## Capabilities

1. **Symbol Search & Deduplication**: Fast query tool (`workforces/code-graph.json`) to check if a function or class already exists before writing code.
2. **Pre-Edit Impact & Documentation Telemetry**: Feeds downstream caller blast radius and symbol docblock coverage to `pre_impact_analyzer.py` and `scaffold_repo_okf.py --recommend-docs`.
3. **Optional OKF Symbol Export**: Generates supplemental OKF Markdown symbol references under `workforces/knowledge-catalog/code/` when `--build-okf` is passed (for `wf-canvas` or deep API lookup).

---

## Commands

### 1. Check if a method exists
```bash
python3 .agents/skills/wf-code-graph/scripts/graph_indexer.py --scan ./ --query "<method_name>" [--target-dir <path>]
```
*(Fallback: `python3 skills/wf-code-graph/scripts/graph_indexer.py ...`)*

### 2. Optional Full Symbol OKF Catalog Export
```bash
python3 .agents/skills/wf-code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog/code --build-okf [--target-dir <path>]
```
*(Fallback: `python3 skills/wf-code-graph/scripts/graph_indexer.py ...`)*

### 3. Pre-Hook Impact & Blast Radius Analysis
```bash
python3 .agents/skills/wf-code-graph/scripts/pre_impact_analyzer.py --file <path_to_file> [--target-dir <path>]
```
*(Fallback: `python3 skills/wf-code-graph/scripts/pre_impact_analyzer.py ...`)*

*(Note: Automatically resolves target project root from `workrules.md`/`workstate.md`, `WORKFORCE_TARGET_DIR`, or pass explicit `--target-dir <path>`)*

> For full architecture, language support, and output schema details, see `docs/code-graph.md` in the Workforces repository.

---

## Optional OKF Symbol Output Schema

When `--build-okf` is requested, generates:
- `workforces/knowledge-catalog/index.md` (Supplemental knowledge catalog index)
- `workforces/knowledge-catalog/code/index.md` (Code symbol catalog index)
- `workforces/knowledge-catalog/code/symbols/<symbol_name>.md` (Individual OKF symbol file)

Example OKF frontmatter generated for symbols:
```yaml
---
type: Code Symbol
title: calculateTotal
description: Method in src/services/calculator.ts
language: typescript
file: src/services/calculator.ts
line: 42
---
```
