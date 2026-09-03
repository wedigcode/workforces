---
name: workforce-canvas
description: Interactive zero-npm node-based visual canvas for workforces. Visualizes workstate standup radar, multi-team tasks, dependency linkages, and code-graph blast radiuses.
---

# Skill: Workforce Command Canvas

An interactive, zero-npm visual command canvas for workforces. It bridges **Macro Strategy** (Workstate, Goals, Hypotheses, Standup Tasks) down to **Micro Code** (AST call graphs and blast radius impact analysis).

---

## Capabilities

1. **Workstate Standup Radar (Macro View)**:
   - Groups tasks into visual columns (`in_progress`, `blocked`, `todo`, `done`).
   - Renders smooth cubic bezier dependency cables linking tasks (`blocked_by` relationships).
   - Team color-coding: Dev (Indigo), Marketing (Emerald), Social (Violet), Design (Pink), Strategy (Amber), Ops (Cyan).
   - Direct human actions: cycle status with one click, drag cards, inspect details, append evolution notes.
2. **Code Blast Radius Explorer (Micro View)**:
   - Interactive inspection of code symbols from `code-graph.json`.
   - Highlights the target focal function in Amber.
   - Traces upstream callees (what the function calls) and downstream callers (what calls this function).
3. **Zero External Dependencies**:
   - Backend runs on Python 3 standard library (`http.server`, `urllib`, `json`).
   - Frontend runs via CDN (Tailwind Play CDN + Lucide vector icons) on a pure DOM+SVG hybrid canvas.

---

## Commands

### 1. Launch the Canvas Server
```bash
python3 .agents/skills/workforce-canvas/scripts/server.py --port 8765 --open
```
*(Fallback: `python3 skills/workforce-canvas/scripts/server.py --port 8765 --open`)*

### 2. Specify Custom Port or Root Directory
```bash
python3 .agents/skills/workforce-canvas/scripts/server.py --port 9000 --root ./
```

---

## REST API Endpoints

- `GET /api/state`: Aggregates all tasks, hypotheses, goals, dependency edges, and summary stats.
- `GET /api/impact?symbol=<name>&file=<path>`: Traces blast radius, callers, and dependencies for a symbol.
- `POST /api/task/update`: Updates task status, priority, or evolution notes directly in `workforces/tasks/*.md`.
- `POST /api/task/connect`: Links two tasks with a dependency cable (sets `blocked_by` in frontmatter).
- `POST /api/task/order`: Saves custom drag layout coordinates.
