---
name: workforce-canvas
description: Renders an interactive, zero-npm visual command canvas bridging macro strategy (task states, dependencies, team standup boards) with micro code architecture (AST call graphs and blast radius analysis). Reach for this skill when presenting visual task dependencies to stakeholders, exploring architectural call graphs in a browser, or interactively managing task statuses and blocker linkages.
---
# Skill: Workforce Command Canvas

An interactive, zero-npm visual command canvas for workforces. It bridges **Macro Strategy** (Workstate, Goals, Hypotheses, Standup Tasks) down to **Micro Code** (AST call graphs and blast radius impact analysis).

---

## 🧭 Canvas Modes

1. **Workstate Standup Radar (Macro View)**:
   - Groups tasks into visual columns (`in_progress`, `blocked`, `todo`, `done`).
   - Renders smooth cubic bezier dependency cables linking tasks (`blocked_by` relationships).
   - Team color-coding: Dev (Indigo), Marketing (Emerald), Social (Violet), Design (Pink), Strategy (Amber), Ops (Cyan).
   - Direct human actions: cycle status with one click, drag cards, inspect details, append evolution notes.
2. **Code Blast Radius Explorer (Micro View)**:
   - Interactive inspection of code symbols from `code-graph.json`.
   - Highlights the target focal function in Amber.
   - Traces upstream callees (what the function calls) and downstream callers (what calls this function).
   - Warns of affected areas before modifying code.
3. **Zero External Dependencies**:
   - Backend runs on Python 3 standard library (`http.server`, `urllib`, `json`).
   - Frontend runs via CDN (Tailwind Play CDN + Lucide vector icons) on a pure DOM+SVG hybrid canvas.

---

## 🤖 Autonomous AI Agent Protocol

When the user asks to *"open the canvas"*, *"show the canvas"*, *"visualize workstate"*, or *"inspect blast radius"*:
1. **Never Ask the User to Run the Command Manually**:
   The AI agent MUST immediately launch the background daemon on behalf of the user using `run_command` with `IsDaemon=True`:
   ```bash
   python3 .agents/skills/workforce-canvas/scripts/server.py --open
   ```
   *(Fallback: `python3 skills/workforce-canvas/scripts/server.py --open`)*
2. **Confirm Launch & Link**:
   Provide the clickable browser link `http://127.0.0.1:8765/` (or allocated port) and report active workstate stats.
3. **Planning & Standup Integration**:
   During `/wf-plan`, `/wf-sync`, or before making major refactors, the agent should offer or proactively launch the canvas to visually showcase the affected blast radius.

---

## 🎮 Interactive Controls

- **Pan**: Click and drag on canvas background or hold `Space` + drag.
- **Zoom**: Mouse wheel towards cursor or use `+` / `-` on the bottom-left dock.
- **Reset View**: Press `R` or click the maximize icon in the dock.
- **Toggle Mode**: Click **Workstate Radar** or **Code Blast Radius** in the top navigation bar.
- **Cycle Status**: Click any task card's status pill to cycle (`todo` &rarr; `in_progress` &rarr; `done`).
- **Connect Dependencies**: Click and drag from an output port (right) of Task A to an input port (left) of Task B.
- **Search**: Press `Enter` in the top search bar to highlight a task or query a code symbol blast radius.

---

## CLI Commands

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
