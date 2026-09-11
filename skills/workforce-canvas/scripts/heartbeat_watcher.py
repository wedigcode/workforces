#!/usr/bin/env python3
"""
Heartbeat Watcher CLI & Standalone Inbox Router
Sweeps workforces/inbox/pending/ and routes items to tasks/, ideas/, or human_review/.

Usage:
  python3 skills/workforce-canvas/scripts/heartbeat_watcher.py --root ./ --once
  python3 skills/workforce-canvas/scripts/heartbeat_watcher.py --root ./ --interval 2.0
"""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

# Add script directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from server import InboxHeartbeatWatcher


def main():
    parser = argparse.ArgumentParser(description="Heartbeat Watcher & Inbox Router")
    parser.add_argument("--root", type=str, default=".", help="Root workspace directory")
    parser.add_argument("--once", action="store_true", help="Run a single sweep and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--require-canvas", action="store_true", help="Exit when canvas session is stopped")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    watcher = InboxHeartbeatWatcher(root_dir, interval=args.interval)

    pending_dir = root_dir / "workforces" / "inbox" / "pending"
    processed_dir = root_dir / "workforces" / "inbox" / "processed"
    human_dir = root_dir / "workforces" / "inbox" / "human_review"
    tasks_dir = root_dir / "workforces" / "tasks"

    for d in (pending_dir, processed_dir, human_dir, tasks_dir):
        d.mkdir(parents=True, exist_ok=True)

    if args.once:
        items_before = len(list(pending_dir.glob("*.json")) + list(pending_dir.glob("*.md")))
        watcher._scan_and_route(pending_dir, processed_dir, human_dir, tasks_dir)
        watcher._sweep_dispatch_queue(tasks_dir)
        items_after = len(list(pending_dir.glob("*.json")) + list(pending_dir.glob("*.md")))
        routed_count = items_before - items_after
        print(f"Sweep completed. {routed_count} item(s) processed. {items_after} pending.")
        sys.exit(0)

    print(f"Starting Heartbeat Watcher daemon on {root_dir} (interval: {args.interval}s)...")

    def handle_signal(sig, frame):
        print("\nStopping Heartbeat Watcher...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    watcher.start()

    session_file = root_dir / "workforces" / ".canvas-session.json"

    try:
        while True:
            time.sleep(args.interval)
            if args.require_canvas and session_file.exists():
                try:
                    import json
                    st = json.loads(session_file.read_text(encoding="utf-8"))
                    if st.get("status") == "stopped":
                        print("Canvas session marked as stopped. Shutting down watcher.")
                        break
                except Exception:
                    pass
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
