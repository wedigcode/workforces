---
description: Interactive visual command canvas — standup workstate radar, cross-team task dependency cables, and AST code-graph blast radius explorer.
---

# /wf-canvas — Interactive Workforce Command Canvas

An interactive, zero-npm visual command canvas for the workforce. Bridges high-level team coordination (Workstate, Standup Tasks, Goals, Hypotheses) down to granular code blast-radius analysis (call hierarchy and affected files).

---

## 🧭 Canvas Modes

1. **Workstate Standup Radar (Macro View)**:
   - Groups tasks by status (`in_progress`, `blocked`, `todo`, `done`) across all teams (Dev, Marketing, Social, Strategy, Design, Ops).
   - Draws cubic bezier dependency cables (`blocked_by` relationships).
   - Allows one-click status cycling, dragging to re-order, and drag-to-connect dependency cables.
   - Slide-over drawer for inspecting task details and appending evolution notes directly to Markdown.

2. **Code Blast Radius Explorer (Micro View)**:
   - Visualizes code symbols directly from `code-graph.json`.
   - Centers the target function in Amber.
   - Traces upstream dependencies (callees) on the left and downstream blast radius (callers) on the right.
   - Warns of affected areas before modifying code.

---

## 🚀 Launching the Canvas

```bash
# Launch server and automatically open in browser
python3 .agents/skills/workforce-canvas/scripts/server.py --port 8765 --open

# Fallback (from repository root)
python3 skills/workforce-canvas/scripts/server.py --port 8765 --open
```

---

## 🎮 Interactive Controls

- **Pan**: Click and drag on canvas background or hold `Space` + drag.
- **Zoom**: Mouse wheel towards cursor or use `+` / `-` on the bottom-left dock.
- **Reset View**: Press `R` or click the maximize icon in the dock.
- **Toggle Mode**: Click **Workstate Radar** or **Code Blast Radius** in the top navigation bar.
- **Cycle Status**: Click any task card's status pill to cycle (`todo` &rarr; `in_progress` &rarr; `done`).
- **Connect Dependencies**: Click and drag from an output port (right) of Task A to an input port (left) of Task B.
- **Search**: Press `Enter` in the top search bar to highlight a task or query a code symbol blast radius.
