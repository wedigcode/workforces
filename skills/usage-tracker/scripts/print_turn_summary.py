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
                    for wf in ["/wf-work", "/wf-feature", "/wf-plan", "/wf-investigate", "/wf-sync", "/wf-update", "/wf-advisor", "/wf-ideate", "/wf-task", "/wf-site-setup", "/work", "/feature", "/plan", "/investigate", "/sync", "/update-workforces"]:
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

    summary_lines = [
        "═" * 68,
        " 📊 WORKFORCES TURN SUMMARY (Post-Hook Execution)",
        "═" * 68,
        f" • Active Tools ({total_tool_calls} calls): {tool_str}",
        f" • Workflows Triggered : {wf_str}",
        f" • Session Payload Tokens: ~{est_tokens:,} tokens ({total_chars:,} chars)",
        "═" * 68
    ]
    summary_text = "\n".join(summary_lines)

    # 1. Print to stdout
    print("\n" + summary_text + "\n")

    # 2. Save to workforces/tmp/turn-summary.txt & session-scoped file
    workspace_dir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    tmp_dir = os.path.join(os.path.abspath(workspace_dir), "workforces", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    conv_id = None
    try:
        # transcript_file path: .../brain/<conv_id>/.system_generated/logs/transcript.jsonl
        conv_id = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(transcript_file))))
    except Exception:
        pass

    summary_files = [os.path.join(tmp_dir, "turn-summary.txt")]
    if conv_id:
        summary_files.append(os.path.join(tmp_dir, f"turn-summary-{conv_id}.txt"))

    for sf_path in summary_files:
        try:
            with open(sf_path, "w", encoding="utf-8") as sf:
                sf.write(summary_text + "\n")
        except Exception:
            pass

if __name__ == "__main__":
    print_summary()


