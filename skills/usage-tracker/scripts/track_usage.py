#!/usr/bin/env python3
"""
Workforces Token & Content Usage Tracker
Parses Antigravity transcript logs to track character counts, thoughts, model responses,
tool payload sizes, and subagent executions. Logs results to workforces/usage-log.json
and workforces/usage-summary.md.
"""

import json
import os
import sys
from datetime import datetime

CHAR_PER_TOKEN_ESTIMATE = 4.0

def estimate_tokens(char_count):
    return int(round(char_count / CHAR_PER_TOKEN_ESTIMATE))

def parse_transcript_file(file_path):
    metrics = {
        "user_input_chars": 0,
        "thought_chars": 0,
        "model_output_chars": 0,
        "tool_payload_chars": 0,
        "step_count": 0,
        "tool_call_count": 0,
        "tool_counts": {},
        "tool_payloads": {},
        "workflows_triggered": set(),
        "subagent_invocations": []
    }

    if not os.path.exists(file_path):
        return metrics

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue

                metrics["step_count"] += 1
                source = entry.get("source", "")
                entry_type = entry.get("type", "")
                content = entry.get("content", "") or ""
                thinking = entry.get("thinking", "") or ""
                tool_calls = entry.get("tool_calls", []) or []

                # Detect workflow invocations in user inputs or planner responses
                if entry_type == "USER_INPUT" and isinstance(content, str):
                    metrics["user_input_chars"] += len(content)
                    for wf in ["/wf-work", "/wf-feature", "/wf-plan", "/wf-investigate", "/wf-sync", "/wf-update", "/wf-advisor", "/wf-ideate", "/wf-task", "/wf-site-setup", "/work", "/feature", "/plan", "/investigate", "/sync", "/update-workforces"]:
                        if wf in content:
                            metrics["workflows_triggered"].add(wf)
                elif source == "MODEL" and entry_type == "PLANNER_RESPONSE":
                    if isinstance(content, str) and content:
                        metrics["model_output_chars"] += len(content)
                elif source in ("MODEL", "SYSTEM") and entry_type not in ("USER_INPUT", "PLANNER_RESPONSE"):
                    metrics["tool_payload_chars"] += len(content)

                # Thoughts / Reasoning
                if thinking:
                    metrics["thought_chars"] += len(thinking)

                # Tool Calls Breakdown & Subagents
                if tool_calls:
                    metrics["tool_call_count"] += len(tool_calls)
                    for tc in tool_calls:
                        name = tc.get("name", "")
                        args = tc.get("args", {})
                        arg_len = len(json.dumps(args))
                        metrics["tool_payload_chars"] += arg_len
                        
                        if name:
                            metrics["tool_counts"][name] = metrics["tool_counts"].get(name, 0) + 1
                            metrics["tool_payloads"][name] = metrics["tool_payloads"].get(name, 0) + arg_len

                        if name == "invoke_subagent":
                            subagents_list = args.get("Subagents", []) if isinstance(args, dict) else []
                            for sub in subagents_list:
                                if isinstance(sub, dict):
                                    metrics["subagent_invocations"].append({
                                        "role": sub.get("Role", "Unknown Subagent"),
                                        "type_name": sub.get("TypeName", "subagent"),
                                        "prompt": sub.get("Prompt", "")
                                    })
    except Exception as e:
        print(f"Warning: Error parsing transcript {file_path}: {e}", file=sys.stderr)

    metrics["workflows_triggered"] = list(metrics["workflows_triggered"])
    return metrics

def find_conversation_dirs(brain_dir):
    if not os.path.exists(brain_dir):
        return []
    dirs = []
    try:
        for item in os.listdir(brain_dir):
            full_path = os.path.join(brain_dir, item)
            try:
                if os.path.isdir(full_path):
                    log_dir = os.path.join(full_path, ".system_generated", "logs")
                    if os.path.exists(log_dir):
                        dirs.append(full_path)
            except Exception:
                continue
    except PermissionError:
        print(f"Notice: Cannot list {brain_dir} due to permission restrictions. Skipping external brain dir scan.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Notice: Error reading brain dir {brain_dir}: {e}", file=sys.stderr)
        return []

    dirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
    return dirs

def track_usage(workspace_root=".", brain_dir=None):
    workspace_root = os.path.abspath(workspace_root)
    
    conv_dirs = []
    if brain_dir:
        conv_dirs.extend(find_conversation_dirs(brain_dir))
    else:
        candidates = [
            os.path.expanduser("~/.gemini/antigravity-ide/brain"),
            os.path.expanduser("~/.gemini/antigravity/brain"),
        ]
        for b_dir in candidates:
            for c_dir in find_conversation_dirs(b_dir):
                if c_dir not in conv_dirs:
                    conv_dirs.append(c_dir)
        conv_dirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)

    
    all_sessions = []
    total_aggregate = {
        "user_input_chars": 0,
        "thought_chars": 0,
        "model_output_chars": 0,
        "tool_payload_chars": 0,
        "step_count": 0,
        "tool_call_count": 0,
        "est_total_tokens": 0
    }

    for cdir in conv_dirs:
        conv_id = os.path.basename(cdir)
        logs_dir = os.path.join(cdir, ".system_generated", "logs")
        transcript_file = os.path.join(logs_dir, "transcript.jsonl")
        if not os.path.exists(transcript_file):
            transcript_file = os.path.join(logs_dir, "transcript_full.jsonl")

        if not os.path.exists(transcript_file):
            continue

        metrics = parse_transcript_file(transcript_file)
        mtime = os.path.getmtime(transcript_file)
        dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        total_chars = (
            metrics["user_input_chars"] +
            metrics["thought_chars"] +
            metrics["model_output_chars"] +
            metrics["tool_payload_chars"]
        )
        est_tokens = estimate_tokens(total_chars)

        session_summary = {
            "conversation_id": conv_id,
            "last_updated": dt_str,
            "metrics": metrics,
            "total_chars": total_chars,
            "est_total_tokens": est_tokens,
            "est_thought_tokens": estimate_tokens(metrics["thought_chars"]),
            "est_user_tokens": estimate_tokens(metrics["user_input_chars"]),
            "est_model_tokens": estimate_tokens(metrics["model_output_chars"]),
            "est_tool_tokens": estimate_tokens(metrics["tool_payload_chars"])
        }
        all_sessions.append(session_summary)

        total_aggregate["user_input_chars"] += metrics["user_input_chars"]
        total_aggregate["thought_chars"] += metrics["thought_chars"]
        total_aggregate["model_output_chars"] += metrics["model_output_chars"]
        total_aggregate["tool_payload_chars"] += metrics["tool_payload_chars"]
        total_aggregate["step_count"] += metrics["step_count"]
        total_aggregate["tool_call_count"] += metrics["tool_call_count"]
        total_aggregate["est_total_tokens"] += est_tokens

    # Write JSON log output to workforces/tmp/ (gitignored)
    tmp_dir = os.path.join(workspace_root, "workforces", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    json_log_path = os.path.join(tmp_dir, "usage-log.json")
    
    # Remove legacy location if it exists
    legacy_log_path = os.path.join(workspace_root, "workforces", "usage-log.json")
    if os.path.exists(legacy_log_path):
        try:
            os.remove(legacy_log_path)
        except Exception:
            pass


    log_data = {
        "last_tracked_at": datetime.now().isoformat(),
        "aggregate": {
            "total_sessions": len(all_sessions),
            "step_count": total_aggregate["step_count"],
            "tool_call_count": total_aggregate["tool_call_count"],
            "user_input_chars": total_aggregate["user_input_chars"],
            "thought_chars": total_aggregate["thought_chars"],
            "model_output_chars": total_aggregate["model_output_chars"],
            "tool_payload_chars": total_aggregate["tool_payload_chars"],
            "est_total_tokens": total_aggregate["est_total_tokens"],
            "est_thought_tokens": estimate_tokens(total_aggregate["thought_chars"])
        },
        "sessions": all_sessions
    }

    with open(json_log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    # Write Markdown Summary Output
    workforces_dir = os.path.join(workspace_root, "workforces")
    summary_md_path = os.path.join(workforces_dir, "usage-summary.md")
    active_session = all_sessions[0] if all_sessions else None

    md_lines = [
        "# Workforces Token & Usage Tracking Summary\n",
        f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Tracked Sessions:** {len(all_sessions)}\n",
        "## Overall Workspace Usage Aggregate\n",
        "| Category | Chars / Steps | Est. Tokens |",
        "|---|---|---|",
        f"| **User Inputs** | {total_aggregate['user_input_chars']:,} chars | {estimate_tokens(total_aggregate['user_input_chars']):,} tokens |",
        f"| **Model Thoughts (Reasoning)** | {total_aggregate['thought_chars']:,} chars | {estimate_tokens(total_aggregate['thought_chars']):,} tokens |",
        f"| **Model Outputs (Responses)** | {total_aggregate['model_output_chars']:,} chars | {estimate_tokens(total_aggregate['model_output_chars']):,} tokens |",
        f"| **Tool Payloads & Outputs** | {total_aggregate['tool_payload_chars']:,} chars | {estimate_tokens(total_aggregate['tool_payload_chars']):,} tokens |",
        f"| **TOTAL AGGREGATE** | **{total_aggregate['user_input_chars'] + total_aggregate['thought_chars'] + total_aggregate['model_output_chars'] + total_aggregate['tool_payload_chars']:,} chars** | **{total_aggregate['est_total_tokens']:,} tokens** |\n",
        "## Active Session Highlights\n"
    ]

    if active_session:
        m = active_session["metrics"]
        md_lines.extend([
            f"**Session ID:** `{active_session['conversation_id']}`  ",
            f"**Total Steps:** {m['step_count']} | **Tool Calls:** {m['tool_call_count']}\n",
            "| Metric | Details | Est. Tokens |",
            "|---|---|---|",
            f"| User Inputs | {m['user_input_chars']:,} chars | {active_session['est_user_tokens']:,} tokens |",
            f"| Model Thoughts | {m['thought_chars']:,} chars | {active_session['est_thought_tokens']:,} tokens |",
            f"| Model Outputs | {m['model_output_chars']:,} chars | {active_session['est_model_tokens']:,} tokens |",
            f"| Tool Payloads | {m['tool_payload_chars']:,} chars | {active_session['est_tool_tokens']:,} tokens |",
            f"| **Session Total** | **{active_session['total_chars']:,} chars** | **{active_session['est_total_tokens']:,} tokens** |\n"
        ])

        if m.get("tool_counts"):
            md_lines.append("### Active Tool Selection Breakdown\n")
            md_lines.append("| Tool Name | Invocation Count | Est. Payload Tokens |")
            md_lines.append("|---|---|---|")
            sorted_tools = sorted(m["tool_counts"].items(), key=lambda x: x[1], reverse=True)
            for tool_name, count in sorted_tools:
                payload_chars = m.get("tool_payloads", {}).get(tool_name, 0)
                md_lines.append(f"| `{tool_name}` | {count} calls | {estimate_tokens(payload_chars):,} tokens |")
            md_lines.append("")

        if m.get("workflows_triggered"):
            md_lines.append("### Workflows Triggered\n")
            for wf in m["workflows_triggered"]:
                md_lines.append(f"- Workflow Command: `{wf}`")
            md_lines.append("")

        if m["subagent_invocations"]:
            md_lines.append("### Subagent Activity\n")
            for sub in m["subagent_invocations"]:
                md_lines.append(f"- **Role:** `{sub['role']}` ({sub['type_name']})")
                md_lines.append(f"  - *Prompt:* {sub['prompt'][:120]}...")
            md_lines.append("")

    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Also update turn summary text file
    if active_session:
        conv_id = active_session.get("conversation_id")
        m = active_session["metrics"]
        sorted_tools = sorted(m.get("tool_counts", {}).items(), key=lambda x: x[1], reverse=True)
        tool_str = ", ".join([f"{name}: {cnt}" for name, cnt in sorted_tools]) if sorted_tools else "None"
        wf_str = ", ".join(m.get("workflows_triggered", [])) if m.get("workflows_triggered") else "None"
        sum_lines = [
            "═" * 68,
            " 📊 WORKFORCES TURN SUMMARY (Post-Hook Execution)",
            "═" * 68,
            f" • Active Tools ({m.get('tool_call_count', 0)} calls): {tool_str}",
            f" • Workflows Triggered : {wf_str}",
            f" • Session Payload Tokens: ~{active_session['est_total_tokens']:,} tokens ({active_session['total_chars']:,} chars)",
            "═" * 68
        ]
        sum_text = "\n".join(sum_lines) + "\n"
        target_files = [os.path.join(tmp_dir, "turn-summary.txt")]
        if conv_id:
            target_files.append(os.path.join(tmp_dir, f"turn-summary-{conv_id}.txt"))

        for tf in target_files:
            try:
                with open(tf, "w", encoding="utf-8") as stf:
                    stf.write(sum_text)
            except Exception:
                pass


    print(f"✓ Token & Usage updated! Log: {json_log_path} | Summary: {summary_md_path}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    track_usage(workspace_root=target)

