---
name: code-graph
description: MANDATORY before writing, editing, or refactoring code. Graph documentor and method indexer to find existing functions, avoid duplication, and map call graphs.
---

# Skill: Code Graph & Method Indexer

Provides lightweight, zero-dependency symbol indexing, function discovery, and call graph mapping.

---

## Capabilities

1. **Symbol Search & Deduplication**: Fast query tool to check if a function or class already exists before writing code.
2. **OKF Catalog Generation**: Automatically generates OKF concept Markdown files under `workforces/knowledge-catalog/code/`.
3. **Graph Serialization**: Generates `workforces/code-graph.json` with symbol counts, file locations, line numbers, signatures, and call dependencies.

---

## Commands

### 1. Check if a method exists
```bash
python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./ --query "<method_name>" [--target-dir <path>]
```
*(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py ...`)*

### 2. Full Codebase Indexing
```bash
python3 .agents/skills/code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog/code --build-okf [--target-dir <path>]
```
*(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py ...`)*

### 3. Pre-Hook Impact & Blast Radius Analysis
```bash
python3 .agents/skills/code-graph/scripts/pre_impact_analyzer.py --file <path_to_file> [--target-dir <path>]
```
*(Fallback: `python3 skills/code-graph/scripts/pre_impact_analyzer.py ...`)*

*(Note: Automatically resolves target project root from `workrules.md`/`workstate.md`, `WORKFORCE_TARGET_DIR`, or pass explicit `--target-dir <path>`)*

> For full architecture, language support, and output schema details, see the [Code Graph Documentation](../../docs/code-graph.md).

---

## OKF Output Schema

Generates:
- `workforces/knowledge-catalog/index.md` (Main knowledge catalog index)
- `workforces/knowledge-catalog/code/index.md` (Code symbol catalog index)
- `workforces/knowledge-catalog/code/symbols/<symbol_name>.md` (Individual OKF concept file)

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
