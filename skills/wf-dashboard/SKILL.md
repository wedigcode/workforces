---
name: wf-dashboard
description: Launches the interactive Workforce Studio & Daily Standup Cockpit Dashboard, starting all required background daemons (the HTTP canvas/studio server, event dispatcher, and inbox heartbeat watcher) and opening the browser. Reach for this skill or trigger it when starting the visual command center, reviewing today's standup sprint radar, or inspecting AST code blast radius.
---
# Skill: /wf-dashboard — Workforce Studio & Daily Standup Cockpit

Launches the interactive visual studio and standup cockpit for the workforce (`server.py`). It bridges **Macro Sprint Coordination** (Daily Standup Cockpit, Kanban Pipeline, P0 Focus, Task Inspector, Canvas Radar) down to **Micro Code Architecture** (AST Call Graphs & Blast Radius Explorer).

---

## Usage

```
/wf-dashboard                 → Launch dashboard, start background services, open in browser
/wf-dashboard --port [port]   → Run on specific port (default: 8765)
/wf-dashboard --no-open       → Start background services without auto-opening browser
/wf-dashboard --status        → Check status of running dashboard server
/wf-dashboard --stop          → Gracefully stop running dashboard server
```

*(Aliased with `/wf-canvas`)*

---

## When to Use

Run `/wf-dashboard` (or `/wf-canvas`, `/dashboard`) when:
- You want a visual command center for today's sprint commitments and priorities.
- You want to inspect task details, cycle task statuses with 1 click, or resolve roadblocks.
- You want to trace AST code dependencies and blast radius impact before refactoring.
- You want to review incoming clips and requests from external tools or the Chrome extension.

---

## What Runs Under the Hood

When `/wf-dashboard` starts, the server automatically initializes and manages all required services:
1. **HTTP REST API Server**: Serves the Studio UI and endpoints (`/api/state`, `/api/sync`, `/api/task/*`, `/api/inbox/*`, `/api/comments`, `/api/impact`, etc.).
2. **Inbox Heartbeat Watcher**: Background daemon thread monitoring `workforces/inbox/pending/` for inbound tasks, clips, and messages, auto-routing them without human toil.
3. **Auto-Shutdown Watchdog**: Monitored idle watchdog that automatically shuts down cleanly after 5 minutes of inactivity when all browser tabs are closed, releasing the network port.
4. **Session State Tracker**: Records live runtime telemetry (port, PID, URL, status) to `workforces/.canvas-session.json`.

---

## Autonomous AI Agent Protocol

When the user invokes `/wf-dashboard`, `/wf-canvas`, or asks to *"open the dashboard"*, *"start the dashboard"*, or *"show the canvas"*:

### Step 1 — Check Runtime Status

Inspect `workforces/.canvas-session.json` to verify if the server is already active:

```json
{
  "status": "running",
  "port": 8765,
  "pid": 12345,
  "url": "http://127.0.0.1:8765"
}
```

If the status is `"running"`, test connectivity (e.g. `curl -s http://127.0.0.1:8765/api/heartbeat`). If alive, **do not spawn a duplicate server**; immediately return the active URL: `http://127.0.0.1:8765/`.

### Step 2 — Pre-Flight Sync & Indexing

Ensure tasks, workstate, and symbol index are aligned before launching:

1. **Reconcile Workstate**:
   ```bash
   python3 .agents/skills/task-tracker/scripts/personal_sync.py --root ./
   ```
   *(Fallback: `python3 skills/task-tracker/scripts/personal_sync.py --root ./`)*

2. **Verify Code Graph**:
   Check if `workforces/code-graph.json` exists. If missing or stale, generate it:
   ```bash
   python3 .agents/skills/code-graph/scripts/graph_indexer.py --target-dir ./
   ```
   *(Fallback: `python3 skills/code-graph/scripts/graph_indexer.py --target-dir ./`)*

### Step 3 — Autonomous Server & Event Watcher Launch

**Never ask the user to run commands manually.** The AI agent MUST launch BOTH background services on behalf of the user:

1. **Launch Studio & API Server** (`run_command` with `IsDaemon=True`):
   ```bash
   python3 .agents/skills/workforce-canvas/scripts/server.py --port 8765 --open
   ```
   *(Fallback: `python3 skills/workforce-canvas/scripts/server.py --port 8765 --open`)*

2. **Launch Event Watcher & Dispatcher** (`run_command` with `WaitMsBeforeAsync=1000`):
   ```bash
   python3 .agents/skills/workforce-canvas/scripts/wait_for_message.py --root ./
   ```
   *(Fallback: `python3 skills/workforce-canvas/scripts/wait_for_message.py --root ./`)*

   *Note: `wait_for_message.py` monitors `workforces/.events/pending/`. When a user submits a comment, pins a note, or updates a task on the canvas, `wait_for_message.py` processes the event, advances the cursor, and exits with code 0. This triggers Antigravity's reactive wakeup to notify the agent immediately.*

### Step 4 — Confirm Launch & Report Sprint Radar

1. Provide the clickable browser link:
   👉 **[http://127.0.0.1:8765/](http://127.0.0.1:8765/)**

2. Report the sprint summary from the cockpit:
   - **The One Thing (P0)**: Current primary focus task.
   - **Active Pipeline**: Up Next (Todo), In Progress, Blocked / Stalled, Completed.
   - **Roadblocks**: Any blocked tasks with resolution options.
   - **Daemons Active**: Dashboard server (`server.py`) and Event Dispatcher (`wait_for_message.py`).

---

## ⚡ Reactive Event Dispatch & Re-Arming Protocol

When Antigravity wakes up from `wait_for_message.py` with an event:
`⚡ WORKFORCE CANVAS EVENT DISPATCH (X event(s) processed)`:
1. **Handle the Event**: Inspect the event type and payload. If it's a task update, evolution note, or comment inquiry, execute the requested action or delegate to the appropriate agent (`@programmer`, `@designer`, etc.).
2. **Re-arm the Watcher**: Immediately re-launch `wait_for_message.py` in the background so the canvas listener remains active:
   ```bash
   python3 .agents/skills/workforce-canvas/scripts/wait_for_message.py --root ./
   ```

---

## ⏰ Cron Alternative (`/wf-dashboard --cron`)

If preferred over a continuous background task, or if running in an environment where long-running background tasks are killed:
Instead of running `wait_for_message.py` continuously, schedule a recurring cron check using the `schedule` tool:
```python
schedule(
    CronExpression="* * * * *",
    Prompt="Check for new workforce canvas events and process them: python3 .agents/skills/workforce-canvas/scripts/wait_for_message.py --root ./ --once",
    IsDaemon=True
)
```
This sweeps `workforces/.events/pending/` every 1 minute via `--once`.
