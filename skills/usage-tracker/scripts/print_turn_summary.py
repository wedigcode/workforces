#!/usr/bin/env python3
"""
Zero-Token Turn & Session Summary Printer for Workforces
Runs as a post_tool_call hook. Parses the active conversation transcript log and prints
a compact summary of tool selection, workflows, and estimated tokens to stdout.
"""

import json
import os
import sys
from datetime import datetime

CHAR_PER_TOKEN = 4.0

def estimate_tokens(char_count):
    return int(round(char_count / CHAR_PER_TOKEN))

def find_latest_transcript():
    candidates = [
        os.path.expanduser("~/.gemini/antigravity-ide/brain"),
        os.path.expanduser("~/.gemini/antigravity/brain"),
    ]
    latest_file = None
    latest_mtime = 0

    for b_dir in candidates:
        if not os.path.exists(b_dir):
            continue
        try:
            for item in os.listdir(b_dir):
                full_path = os.path.join(b_dir, item)
                if os.path.isdir(full_path):
                    logs_dir = os.path.join(full_path, ".system_generated", "logs")
                    t_file = os.path.join(logs_dir, "transcript.jsonl")
                    if not os.path.exists(t_file):
                        t_file = os.path.join(logs_dir, "transcript_full.jsonl")
                    if os.path.exists(t_file):
                        mtime = os.path.getmtime(t_file)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_file = t_file
        except PermissionError:
            continue
        except Exception:
            continue

    return latest_file

def print_summary():
    transcript_file = find_latest_transcript()
    if not transcript_file:
        return

    tool_counts = {}
    workflows_triggered = set()
    total_tool_calls = 0
    total_chars = 0
    user_chars = 0
    model_chars = 0
    tool_payload_chars = 0

    try:
        with open(transcript_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue

                entry_type = entry.get("type", "")
                content = entry.get("content", "") or ""
                thinking = entry.get("thinking", "") or ""
                tool_calls = entry.get("tool_calls", []) or []

                if entry_type == "USER_INPUT" and isinstance(content, str):
                    user_chars += len(content)
                    for wf in ["/work", "/feature", "/plan", "/investigate", "/sync", "/update-workforces"]:
                        if wf in content:
                            workflows_triggered.add(wf)
                elif entry_type == "PLANNER_RESPONSE":
                    if isinstance(content, str) and content:
                        model_chars += len(content)
                else:
                    if isinstance(content, str) and content:
                        tool_payload_chars += len(content)

                if thinking and isinstance(thinking, str):
                    model_chars += len(thinking)

                if tool_calls:
                    total_tool_calls += len(tool_calls)
                    for tc in tool_calls:
                        name = tc.get("name", "")
                        args = tc.get("args", {})
                        arg_len = len(json.dumps(args))
                        tool_payload_chars += arg_len
                        if name:
                            tool_counts[name] = tool_counts.get(name, 0) + 1

    except Exception:
        return

    total_chars = user_chars + model_chars + tool_payload_chars
    est_tokens = estimate_tokens(total_chars)

    # Format Tool Counts String
    sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    tool_str = ", ".join([f"{name}: {cnt}" for name, cnt in sorted_tools]) if sorted_tools else "None"
    wf_str = ", ".join(workflows_triggered) if workflows_triggered else "None"

    print("\n" + "═" * 68)
    print(" 📊 WORKFORCES TURN SUMMARY (Post-Hook Execution)")
    print("═" * 68)
    print(f" • Active Tools ({total_tool_calls} calls): {tool_str}")
    print(f" • Workflows Triggered : {wf_str}")
    print(f" • Session Payload Tokens: ~{est_tokens:,} tokens ({total_chars:,} chars)")
    print("═" * 68 + "\n")

if __name__ == "__main__":
    print_summary()
