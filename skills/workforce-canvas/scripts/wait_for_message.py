#!/usr/bin/env python3
"""
Workforce Canvas Message Watcher & Event Dispatcher
Monitors workforces/.events/pending/ and dispatches events to agents with zero race conditions.

Features:
- Immediate Catch-Up Phase: Checks pending events on launch; if events exist, processes them
  chronologically, moves them to processed/, updates cursor.json, and exits 0 immediately without sleeping.
- Polling Loop: If no events are pending, polls until an event arrives, timeout expires, or canvas stops.
- Cursor Offset Tracking: Persists last_processed_id and last_processed_timestamp in workforces/.events/cursor.json.
- Signal Handling: Handles SIGINT and SIGTERM gracefully.

Usage:
  python3 skills/workforce-canvas/scripts/wait_for_message.py --root ./ --once
  python3 skills/workforce-canvas/scripts/wait_for_message.py --root ./ --timeout 30 --max-batch 10
"""

import argparse
import datetime
import json
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from session_registry import (
        detect_current_chat_session,
        register_chat_session,
        heartbeat_chat_session,
        unregister_chat_session,
    )
except ImportError:
    def detect_current_chat_session(fallback=None):
        return os.environ.get("ANTIGRAVITY_CONVERSATION_ID") or fallback or "session-default"
    def register_chat_session(root_dir, session_id, **kwargs):
        return {"session_id": session_id}
    def heartbeat_chat_session(root_dir, session_id, **kwargs):
        return True
    def unregister_chat_session(root_dir, session_id, **kwargs):
        return True

_STOP_REQUESTED = False


def _event_sort_key(f: Path):
    """Extract chronological sort key: (timestamp, integer sequence, filename)."""
    parts = f.stem.split("_")
    ts_str = parts[0]
    seq_num = 0
    if len(parts) >= 2:
        try:
            seq_num = int(parts[1])
        except ValueError:
            seq_num = 0
    return (ts_str, seq_num, f.name)


def get_pending_event_files(pending_dir: Path) -> List[Path]:
    """Retrieve all pending JSON event files sorted in strict chronological order."""
    if not pending_dir.exists():
        return []
    # Ignore temporary files (.tmp) created during atomic writes
    files = [f for f in pending_dir.glob("*.json") if not f.name.endswith(".tmp")]
    return sorted(files, key=_event_sort_key)


def get_cursor(root_dir: Path) -> Dict[str, Any]:
    """Read cursor.json from workforces/.events/cursor.json, or return default empty cursor."""
    root_dir = Path(root_dir).resolve()
    cursor_file = root_dir / "workforces" / ".events" / "cursor.json"
    if cursor_file.exists():
        try:
            return json.loads(cursor_file.read_text(encoding="utf-8"))
        except Exception as err:
            sys.stderr.write(f"Warning: Failed reading cursor.json: {err}\n")
    return {
        "last_processed_id": None,
        "last_processed_timestamp": None,
        "updated_at": None,
        "batch_size": 0,
        "total_processed": 0,
    }


def format_event_summary(events: List[Dict[str, Any]]) -> str:
    """Format processed events into a structured, agent-friendly summary string."""
    if not events:
        return "No pending events."

    divider = "=" * 72
    lines = [
        divider,
        f"⚡ WORKFORCE CANVAS EVENT DISPATCH ({len(events)} event{'s' if len(events) != 1 else ''} processed)",
        divider,
    ]

    for idx, ev in enumerate(events, 1):
        ev_id = ev.get("id", "unknown")
        ev_type = ev.get("event_type") or ev.get("type", "unknown")
        ev_ts = ev.get("timestamp", "")
        payload = ev.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"data": payload}

        lines.append(f"\n[{idx}/{len(events)}] EVENT: {ev_type.upper()} | ID: {ev_id}")
        if ev_ts:
            lines.append(f"  Timestamp:   {ev_ts}")

        if ev_type == "comment":
            author = payload.get("author", "@human")
            target_id = payload.get("target_id") or payload.get("file", "")
            file_path = payload.get("file", "")
            comment = payload.get("comment", "")
            pin = payload.get("pin")
            stitch_url = payload.get("stitch_url")

            lines.append(f"  Author:      {author}")
            if target_id:
                lines.append(f"  Target ID:   {target_id}")
            if file_path and file_path != target_id:
                lines.append(f"  Target File: {file_path}")
            if pin and isinstance(pin, dict):
                lines.append(f"  Pin:         x={pin.get('x')}%, y={pin.get('y')}%")
            if stitch_url:
                lines.append(f"  Stitch URL:  {stitch_url}")
            lines.append(f"  Comment:     {comment}")

        elif ev_type == "inbox_submission":
            title = payload.get("title", "Untitled")
            sub_type = payload.get("type", "general")
            content = payload.get("content", "")
            source_url = payload.get("source_url", "")
            file_path = payload.get("file", "")
            tags = payload.get("tags", [])

            lines.append(f"  Title:       {title}")
            lines.append(f"  Type:        {sub_type}")
            if content:
                lines.append(f"  Content:     {content}")
            if source_url:
                lines.append(f"  Source URL:  {source_url}")
            if file_path:
                lines.append(f"  File:        {file_path}")
        elif ev_type == "task_created":
            title = payload.get("title", "Untitled Task")
            task_type = payload.get("type", "feature")
            priority = payload.get("priority", "P1")
            reporter = payload.get("reporter", "@human")
            file_path = payload.get("file", "")
            description = payload.get("description", "")
            images = payload.get("images", [])

            lines.append(f"  Title:       {title}")
            lines.append(f"  Priority:    {priority} | Type: {task_type}")
            lines.append(f"  Reporter:    {reporter}")
            if file_path:
                lines.append(f"  File:        {file_path}")
            if description:
                desc_snip = description[:300] + ("..." if len(description) > 300 else "")
                lines.append(f"  Description: {desc_snip}")
            if images:
                lines.append(f"  Images ({len(images)}): {', '.join(str(img) for img in images)}")
            lines.append("  👉 Directives:")
            lines.append("     - @scribe: record session context & task lineage if appropriate")
            lines.append("     - @project-manager: sequence task into active sprint / backlog")
            lines.append("     - @programmer: triage requirements and commence execution")

        elif ev_type in ("task_started", "task_dispatched"):
            title = payload.get("title", "Untitled Task")
            task_type = payload.get("type", "feature")
            priority = payload.get("priority", "P1")
            team = payload.get("team", "dev")
            agent = payload.get("agent") or payload.get("delegated_to", "@programmer")
            file_path = payload.get("file", "")
            action = payload.get("action", "")
            description = payload.get("description", "")

            lines.append(f"  Title:       {title}")
            lines.append(f"  Priority:    {priority} | Team: {team} | Type: {task_type}")
            lines.append(f"  Assigned:    {agent}")
            if file_path:
                lines.append(f"  File:        {file_path}")
            if action:
                lines.append(f"  Action:      {action}")
            if description:
                desc_snip = description[:300] + ("..." if len(description) > 300 else "")
                lines.append(f"  Description: {desc_snip}")
            lines.append("  👉 Directives:")
            lines.append(f"     - {agent}: commence immediate autonomous execution of this task")
            lines.append("     - @scribe: record session context & task lineage if appropriate")

        elif ev_type in ("task_review", "task_awaiting_review"):
            title = payload.get("title", "Untitled Task")
            task_type = payload.get("type", "feature")
            priority = payload.get("priority", "P1")
            team = payload.get("team", "dev")
            reviewer = payload.get("reviewer", "@human")
            agent = payload.get("agent") or payload.get("assignee", "@programmer")
            file_path = payload.get("file", "")
            action = payload.get("action", "")
            description = payload.get("description", "")

            lines.append(f"  Title:       {title}")
            lines.append(f"  Priority:    {priority} | Team: {team} | Type: {task_type}")
            lines.append(f"  Reviewer:    {reviewer}")
            lines.append(f"  Completed by:{agent}")
            if file_path:
                lines.append(f"  File:        {file_path}")
            if action:
                lines.append(f"  Action:      {action}")
            if description:
                desc_snip = description[:300] + ("..." if len(description) > 300 else "")
                lines.append(f"  Description: {desc_snip}")
            lines.append("  👉 Directives:")
            if reviewer in ("@human", "~", ""):
                lines.append("     - Human review requested: review implementation, verify quality gates, and approve (done) or request rework (in_progress)")
            else:
                lines.append(f"     - {reviewer}: review completed work and provide approval or rework feedback")
            lines.append("     - @scribe: record session context & task lineage if appropriate")

        elif ev_type in ("session_directive", "chat_message"):
            sender = payload.get("sender", "@human")
            msg = payload.get("message", "")
            action = payload.get("action", "Directive from workforce dashboard")
            prio = payload.get("priority", "P1")
            target_sid = ev.get("target_chat_session_id") or payload.get("session_id", "current")

            lines.append(f"  Sender:      {sender}")
            lines.append(f"  Priority:    {prio}")
            lines.append(f"  Target Chat: {target_sid}")
            if action:
                lines.append(f"  Context:     {action}")
            lines.append(f"  Message:     {msg}")
            lines.append("  👉 Directives:")
            lines.append(f"     - Process human instruction and respond or begin autonomous execution immediately")
            lines.append("     - @scribe: record session context & decisions if appropriate")

        else:
            for k, v in payload.items():
                lines.append(f"  {k}: {v}")

    lines.append("\n" + divider)
    return "\n".join(lines)


def process_pending_events(
    root_dir: Path,
    max_batch: int = 10,
    chat_session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Process pending events in chronological order, move them to processed/, and update cursor.json."""
    root_dir = Path(root_dir).resolve()
    events_dir = root_dir / "workforces" / ".events"
    pending_dir = events_dir / "pending"
    processed_dir = events_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    pending_files = get_pending_event_files(pending_dir)
    if not pending_files:
        return []

    processed_events: List[Dict[str, Any]] = []
    last_id: Optional[str] = None
    last_ts: Optional[str] = None

    for f in pending_files:
        if max_batch > 0 and len(processed_events) >= max_batch:
            break

        # Targeted event check BEFORE claiming: if event targets a different session, leave for that session
        if chat_session_id:
            try:
                peek_data = json.loads(f.read_text(encoding="utf-8"))
                target_sid = (
                    peek_data.get("target_chat_session_id")
                    or (peek_data.get("payload") or {}).get("target_chat_session_id")
                    or (peek_data.get("payload") or {}).get("session_id")
                    if peek_data.get("event_type") == "session_directive"
                    else None
                )
                if target_sid and target_sid not in ("all", chat_session_id):
                    # Event is explicitly targeted to another chat session; do not claim it!
                    continue
            except Exception:
                pass

        dest = processed_dir / f.name
        # Attempt atomic claim by moving from pending to processed first.
        # This eliminates race conditions where multiple workers try to read/unlink the same file.
        try:
            f.rename(dest)
        except FileNotFoundError:
            # Another process or thread already claimed this event file; safely skip
            continue
        except FileExistsError:
            try:
                f.replace(dest)
            except FileNotFoundError:
                continue
            except Exception:
                try:
                    shutil.move(str(f), str(dest))
                except (FileNotFoundError, Exception):
                    continue
        except OSError:
            try:
                shutil.move(str(f), str(dest))
            except (FileNotFoundError, Exception):
                continue

        # File is now safely claimed at dest. Read and parse event record.
        try:
            content = dest.read_text(encoding="utf-8")
            event_data = json.loads(content)
        except Exception as err:
            sys.stderr.write(f"Warning: Failed reading claimed event file {dest.name}: {err}\n")
            event_data = {"id": dest.stem, "error": str(err)}

        processed_events.append(event_data)
        last_id = event_data.get("id") or dest.stem
        last_ts = event_data.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Update cursor.json atomically
    if processed_events and last_id:
        cursor_file = events_dir / "cursor.json"
        prev_cursor = get_cursor(root_dir)
        total_processed = int(prev_cursor.get("total_processed", 0)) + len(processed_events)

        cursor_data = {
            "last_processed_id": last_id,
            "last_processed_timestamp": last_ts,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "batch_size": len(processed_events),
            "total_processed": total_processed,
            "chat_session_id": chat_session_id or prev_cursor.get("chat_session_id"),
        }
        try:
            cursor_tmp = cursor_file.with_suffix(".tmp")
            cursor_tmp.write_text(json.dumps(cursor_data, indent=2), encoding="utf-8")
            cursor_tmp.replace(cursor_file)
        except Exception as cursor_err:
            sys.stderr.write(f"Warning: Failed writing cursor.json: {cursor_err}\n")

    return processed_events


def wait_for_message(
    root_dir: Path,
    timeout: Optional[float] = None,
    once: bool = False,
    max_batch: int = 10,
    poll_interval: float = 0.5,
    chat_session_id: Optional[str] = None,
    alias: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Wait for messages / events with Immediate Catch-Up Phase and Chat Session Registration."""
    root_dir = Path(root_dir).resolve()
    events_dir = root_dir / "workforces" / ".events"
    pending_dir = events_dir / "pending"
    session_file = root_dir / "workforces" / ".canvas-session.json"

    actual_chat_session = chat_session_id or detect_current_chat_session()
    register_chat_session(
        root_dir=root_dir,
        session_id=actual_chat_session,
        alias=alias,
        role="watcher",
        status="active"
    )

    last_hb_time = time.time()

    # --- Phase 1: Immediate Catch-Up Phase ---
    pending_files = get_pending_event_files(pending_dir)
    if pending_files:
        events = process_pending_events(root_dir, max_batch=max_batch, chat_session_id=actual_chat_session)
        if events:
            print(format_event_summary(events))
            return events

    if once or _STOP_REQUESTED:
        print("No pending events found.")
        return []

    # --- Phase 2: Polling Loop ---
    start_time = time.time()
    try:
        while not _STOP_REQUESTED:
            time.sleep(poll_interval)
            if _STOP_REQUESTED:
                break

            now_t = time.time()
            if (now_t - last_hb_time) >= 10.0:
                heartbeat_chat_session(root_dir, actual_chat_session)
                last_hb_time = now_t

            # Check canvas session status
            if session_file.exists():
                try:
                    st = json.loads(session_file.read_text(encoding="utf-8"))
                    if st.get("status") == "stopped":
                        print("Canvas session marked as stopped. Exiting wait_for_message.")
                        return []
                except Exception:
                    pass

            # Check timeout
            if timeout is not None and (time.time() - start_time) >= timeout:
                print(f"Timeout of {timeout}s reached. No pending events.")
                return []

            # Check for new pending events
            pending_files = get_pending_event_files(pending_dir)
            if pending_files:
                events = process_pending_events(root_dir, max_batch=max_batch, chat_session_id=actual_chat_session)
                if events:
                    print(format_event_summary(events))
                    return events
    finally:
        unregister_chat_session(root_dir, actual_chat_session, status="idle")

    return []


def _handle_signal(signum, frame):
    """Clean exit on SIGINT or SIGTERM."""
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    sys.stderr.write(f"\nReceived signal {signum}. Stopping wait_for_message cleanly...\n")


def main():
    parser = argparse.ArgumentParser(
        description="Wait for Workforce Canvas events and dispatch to agent (Approach 2: Persistent Queue & Cursor Tracking)"
    )
    parser.add_argument("--root", type=str, default=".", help="Root workspace directory")
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Max wait timeout in seconds (default: wait indefinitely until event or canvas stop)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check once for pending events and exit immediately without polling",
    )
    parser.add_argument(
        "--max-batch",
        type=int,
        default=10,
        help="Max events to process per batch (default: 10, 0 for all)",
    )
    parser.add_argument(
        "--chat-session-id",
        type=str,
        default=None,
        help="Antigravity chat session ID (auto-detected by default)",
    )
    parser.add_argument(
        "--alias",
        type=str,
        default=None,
        help="Human-readable alias for this chat session",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    root_dir = Path(args.root).resolve()
    wait_for_message(
        root_dir=root_dir,
        timeout=args.timeout,
        once=args.once,
        max_batch=args.max_batch,
        chat_session_id=args.chat_session_id,
        alias=args.alias,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
