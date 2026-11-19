---
name: wf-code-graph
description: Constructs AST-based code graphs, indexes functions and classes, and maps call dependencies to evaluate blast radius before refactoring inside the Workforce Canvas UI (`wf-canvas` / `wf-dashboard`). Reach for this skill only when refreshing `workforces/code-graph.json` for Canvas UI visualization; deprecated for AI agent coding, planning, and research workflows (use `<repo>/docs/index.md` and `grep_search` instead).
---
# Skill: Code Graph & Method Indexer *(Canvas UI Only — Deprecated for AI Workflows)*

> [!WARNING]
> **Deprecated for AI Agent Workflows (`disable_model_invocation: true`):** AI coding, planning, and research agents do **not** use `wf-code-graph` or `pre_impact_analyzer.py`. Read **`<repo>/docs/index.md`** + `docs/architecture/*.md` (`wf-doc-generator`) and use `grep_search` / `list_dir` instead.

This skill remains available exclusively for the **`wf-canvas` / `wf-dashboard` visual UI** (`workforces/code-graph.json`) so human developers can inspect symbol dependency graphs visually.

---

## Capabilities (Canvas UI Support)

1. **JSON Graph Serialization (`workforces/code-graph.json`)**: Indexes symbol locations, signatures, and call dependencies on demand when launched by `/wf-dashboard` or `wf-canvas/scripts/server.py`.
2. **Symbol Search (UI Helper)**: Supports visual symbol lookup inside Canvas.
3. **Optional OKF Symbol Export**: Generates supplemental OKF Markdown files under `workforces/knowledge-catalog/code/` when `--build-okf` is passed explicitly.

---

## Commands (Manual / Canvas UI Use)

### 1. Build `workforces/code-graph.json` for Canvas UI
```bash
python3 .agents/skills/wf-code-graph/scripts/graph_indexer.py --scan ./ [--target-dir <path>]
```
*(Fallback: `python3 skills/wf-code-graph/scripts/graph_indexer.py ...`)*

### 2. Optional Full Symbol OKF Catalog Export
```bash
python3 .agents/skills/wf-code-graph/scripts/graph_indexer.py --scan ./ --out-okf workforces/knowledge-catalog/code --build-okf [--target-dir <path>]
```

> For full architecture, language support, and Canvas integration details, see `docs/code-graph.md` in the Workforces repository.
