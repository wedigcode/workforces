#!/usr/bin/env python3
"""
report-task — Task & Action Item capture, evolution, and lifecycle management script.

Usage:
    # 1. Report a new task linked to a session:
    python3 skills/task-tracker/scripts/report-task.py \
        --title "Follow up with pilot team lead" \
        --type follow-up \
        --priority P1 \
        --assignee "@user" \
        --reporter scribe \
        --session-id "026" \
        --session-file "workforces/session-context/026_2026-08-23_claude_scribe_product_brief.md" \
        --description "Send updated SOC2 summary and schedule 15m review." \
        --suggested-action "Draft email and attach SOC2 bridge letter." \
        --evolution-note "Initial discussion: user agreed to follow up by Tuesday." \
        --sync-session

    # 2. Update status in-place (e.g. start working on it):
    python3 skills/task-tracker/scripts/report-task.py \
        --update "workforces/tasks/20260823-120000-follow-up-with-pilot-team-lead.md" \
        --start \
        --evolution-note "Started drafting email response." \
        --sync-session

    # 3. Mark task as blocked or done:
    python3 skills/task-tracker/scripts/report-task.py \
        --update "follow-up-with-pilot-team-lead" \
        --done \
        --evolution-note "Sent email and scheduled call for Thursday." \
        --sync-session

    # 4. Drop a task with deciding factors / reason:
    python3 skills/task-tracker/scripts/report-task.py \
        --update "follow-up-with-pilot-team-lead" \
        --drop "Lead reached out directly; separate follow-up no longer required." \
        --sync-session

    # 5. Check for similar tasks before creating:
    python3 skills/task-tracker/scripts/report-task.py \
        --find-similar "pilot team lead"
"""

import argparse
import datetime
import difflib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

VALID_STATUSES = ["todo", "in_progress", "blocked", "done", "dropped"]
VALID_PRIORITIES = ["P0", "P1", "P2", "P3"]


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML-style frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml = parts[1]
    body = parts[2].lstrip("\r\n")

    metadata: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    current_dict_in_list: Optional[Dict[str, Any]] = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle list item start: "- ..."
        if stripped.startswith("- ") and current_list_key:
            item_text = stripped[2:].strip()
            if ":" in item_text:
                # Dict item in list: e.g. "- id: '123'"
                sub_k, sub_v = item_text.split(":", 1)
                sub_k = sub_k.strip()
                sub_v = sub_v.strip().strip('"').strip("'")
                current_dict_in_list = {sub_k: sub_v}
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(current_dict_in_list)
            else:
                # Scalar item in list: e.g. "- src/utils.py"
                current_dict_in_list = None
                val = item_text.strip('"').strip("'")
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(val)
            continue

        # Handle subsequent lines of dict in list: e.g. "  file: '...'"
        if (line.startswith("  ") or line.startswith("\t")) and current_dict_in_list is not None and ":" in line:
            sub_k, sub_v = stripped.split(":", 1)
            sub_k = sub_k.strip()
            sub_v = sub_v.strip().strip('"').strip("'")
            current_dict_in_list[sub_k] = sub_v
            continue

        if ":" in line:
            current_dict_in_list = None
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            if val == "" or val == "~" or val == "null":
                metadata[key] = None
                current_list_key = key
            elif val.startswith("[") and val.endswith("]"):
                current_list_key = None
                raw_items = val[1:-1].split(",")
                metadata[key] = [item.strip().strip('"').strip("'") for item in raw_items if item.strip()]
            elif val.startswith('"') and val.endswith('"'):
                current_list_key = None
                metadata[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                current_list_key = None
                metadata[key] = val[1:-1]
            elif val.lower() == "true":
                current_list_key = None
                metadata[key] = True
            elif val.lower() == "false":
                current_list_key = None
                metadata[key] = False
            else:
                current_list_key = None
                metadata[key] = val

    return metadata, body


def dump_frontmatter(metadata: Dict[str, Any], body: str) -> str:
    """Convert metadata dictionary and body into markdown with YAML frontmatter."""
    lines = ["---"]
    for k, v in metadata.items():
        if v is None:
            lines.append(f"{k}: ~")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            elif isinstance(v[0], dict):
                lines.append(f"{k}:")
                for item in v:
                    first = True
                    for sub_k, sub_v in item.items():
                        if first:
                            lines.append(f'  - {sub_k}: "{sub_v}"')
                            first = False
                        else:
                            lines.append(f'    {sub_k}: "{sub_v}"')
            else:
                formatted_items = [f'"{item}"' for item in v]
                lines.append(f"{k}: [{', '.join(formatted_items)}]")
        else:
            clean_v = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{clean_v}"')
    lines.append("---")
    lines.append("")
    lines.append(body.strip("\r\n"))
    lines.append("")
    return "\n".join(lines)


def extract_title(filepath: str) -> str:
    """Pull the `title:` value from a YAML frontmatter block in a task file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            metadata, _ = parse_frontmatter(f.read())
            return str(metadata.get("title", ""))
    except OSError:
        pass
    return ""


def find_task_by_identifier(identifier: str, search_dirs: List[str]) -> Optional[str]:
    """Find task/issue file by exact path, relative path, filename, or partial slug match."""
    if os.path.isfile(identifier):
        return os.path.abspath(identifier)

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        direct = os.path.join(d, identifier)
        if os.path.isfile(direct):
            return os.path.abspath(direct)
        if not identifier.endswith(".md"):
            with_ext = direct + ".md"
            if os.path.isfile(with_ext):
                return os.path.abspath(with_ext)

        for fname in os.listdir(d):
            if not fname.endswith(".md"):
                continue
            if identifier.lower() in fname.lower():
                return os.path.abspath(os.path.join(d, fname))
    return None


def find_similar_tasks(
    query_title: str, search_dirs: List[str], threshold: float = 0.70
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Return existing task files whose title or content is similar to query_title.
    Returns list of (filepath, ratio, metadata).
    """
    matches = []
    seen_paths = set()
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.abspath(os.path.join(directory, fname))
            if fpath in seen_paths:
                continue
            seen_paths.add(fpath)
            try:
                with open(fpath, encoding="utf-8") as f:
                    meta, _ = parse_frontmatter(f.read())
                    title = meta.get("title", "")
                    if not title:
                        continue
                    ratio = difflib.SequenceMatcher(
                        None, query_title.lower(), str(title).lower()
                    ).ratio()
                    if ratio >= threshold or query_title.lower() in str(title).lower():
                        score = max(ratio, 0.85 if query_title.lower() in str(title).lower() else ratio)
                        matches.append((fpath, score, meta))
            except OSError:
                continue
    return sorted(matches, key=lambda x: x[1], reverse=True)


def build_task_markdown(
    title: str,
    task_type: str = "task",
    priority: str = "P2",
    status: str = "todo",
    reporter: str = "scribe",
    assignee: Optional[str] = None,
    description: str = "",
    suggested_action: str = "",
    file_path: str = "",
    session_id: str = "",
    session_file: str = "",
    recommended_tools: Optional[List[str]] = None,
    delegated_to: Optional[str] = None,
    github_labels: Optional[List[str]] = None,
    github_issue: Optional[str] = None,
    evolution_notes: Optional[List[str]] = None,
    created_at: Optional[datetime.datetime] = None,
    updated_at: Optional[datetime.datetime] = None,
) -> str:
    """Construct complete task file markdown with frontmatter and lineage."""
    now = created_at or datetime.datetime.now()
    up_now = updated_at or now

    metadata: Dict[str, Any] = {
        "title": title,
        "type": task_type or "task",
        "priority": priority,
        "status": status,
        "reporter": reporter,
        "assignee": assignee or None,
        "reported_at": now.isoformat(),
        "updated_at": up_now.isoformat(),
        "file": file_path or "",
        "session_id": session_id or None,
        "session_file": session_file or None,
        "recommended_tools": recommended_tools or [],
        "delegated_to": delegated_to or None,
        "github_labels": github_labels or [],
        "github_issue": github_issue or None,
    }

    session_origin_link = ""
    if session_file:
        session_origin_link = f"**Origin Session:** [{os.path.basename(session_file)}]({session_file})\n"

    header_parts = [
        f"**Type:** `{task_type}`",
        f"**Priority:** `{priority}`",
        f"**Status:** `{status}`",
        f"**Reporter:** `{reporter}`",
    ]
    if assignee:
        header_parts.append(f"**Assignee:** `{assignee}`")
    header_line = " | ".join(header_parts)

    tool_delegation_line = ""
    parts_line = []
    if recommended_tools:
        parts_line.append(f"**Recommended Tools:** `{', '.join(recommended_tools)}`")
    if delegated_to:
        parts_line.append(f"**Delegated To:** `{delegated_to}`")
    if github_labels:
        parts_line.append(f"**GitHub Labels:** `{'`, `'.join(github_labels)}`")
    if parts_line:
        tool_delegation_line = " | ".join(parts_line) + "\n"

    evolution_lines = []
    if evolution_notes:
        for note in evolution_notes:
            evolution_lines.append(f"- {note}")
    else:
        evolution_lines.append(f"- **{now.strftime('%Y-%m-%d %H:%M')}:** Initial creation: {description[:120] if description else title}")

    body = f"""# {title}

{header_line}  
**Reported:** {now.strftime("%Y-%m-%d %H:%M")} | **Updated:** {up_now.strftime("%Y-%m-%d %H:%M")}  
{session_origin_link}{f"**Affected file:** `{file_path}`\n" if file_path else ""}{tool_delegation_line}
## Description

{description if description else "_No description provided._"}

## Suggested Action

{suggested_action if suggested_action else "_No suggested action provided._"}

## 🧠 Session Lineage & Deciding Factors

{chr(10).join(evolution_lines)}
"""

    return dump_frontmatter(metadata, body)


def sync_task_to_session_file(
    session_file_path: str,
    task_file_path: str,
    task_meta: Dict[str, Any],
    evolution_summary: str = "",
) -> bool:
    """
    Ensure the session context markdown file lists the task in frontmatter (tracked_tasks) and body.
    Maintains backward compatibility with tracked_issues.
    """
    if not os.path.isfile(session_file_path):
        return False

    try:
        with open(session_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        task_id = os.path.splitext(os.path.basename(task_file_path))[0]
        title = task_meta.get("title", task_id)
        task_type = task_meta.get("type", "task")
        priority = task_meta.get("priority", task_meta.get("severity", "P2"))
        status = task_meta.get("status", "todo")
        is_dropped = status in ("dropped", "rejected", "wont-fix")

        # Update or append in frontmatter tracked_tasks (or tracked_issues if present)
        uses_tracked_tasks = "tracked_tasks" in meta or "tracked_issues" not in meta
        list_key = "tracked_tasks" if uses_tracked_tasks else "tracked_issues"
        tracked = meta.get(list_key)
        if not isinstance(tracked, list):
            tracked = []

        found = False
        new_tracked = []
        for item in tracked:
            if isinstance(item, dict) and (
                item.get("id") == task_id or item.get("file") == task_file_path or (item.get("title") and item.get("title") == title)
            ):
                found = True
                new_item = {
                    "id": task_id,
                    "file": task_file_path,
                    "title": title,
                    "type": task_type,
                    "priority" if list_key == "tracked_tasks" else "severity": priority,
                    "status": status,
                }
                new_tracked.append(new_item)
            else:
                new_tracked.append(item)

        if not found:
            new_item = {
                "id": task_id,
                "file": task_file_path,
                "title": title,
                "type": task_type,
                "priority" if list_key == "tracked_tasks" else "severity": priority,
                "status": status,
            }
            new_tracked.append(new_item)

        meta[list_key] = new_tracked
        meta["updated_at"] = datetime.datetime.now().isoformat()

        # Determine task line formatting in Markdown body
        summary_text = evolution_summary or task_meta.get("description", "")[:100]
        for prefix in ["❌ Dropped:", "❌ Rejected:", "❌ Dropped by user:", "❌ Rejected by user:"]:
            if summary_text.startswith(prefix):
                summary_text = summary_text[len(prefix):].strip()

        if is_dropped:
            task_entry = f"- [~~{title}~~](file://{os.path.abspath(task_file_path)}) (~~`{task_type}`~~ | ~~{priority}~~) — ❌ **Dropped:** {summary_text}"
        elif status == "done":
            task_entry = f"- [{title}](file://{os.path.abspath(task_file_path)}) (`{task_type}` | {priority}) — ✅ **Done:** {summary_text}"
        elif status == "in_progress":
            task_entry = f"- [{title}](file://{os.path.abspath(task_file_path)}) (`{task_type}` | {priority}) — ⏳ **In Progress:** {summary_text}"
        elif status == "blocked":
            task_entry = f"- [{title}](file://{os.path.abspath(task_file_path)}) (`{task_type}` | {priority}) — ⚠️ **Blocked:** {summary_text}"
        else:
            task_entry = f"- [{title}](file://{os.path.abspath(task_file_path)}) (`{task_type}` | {priority}) — {summary_text}"

        # Match section header (either tasks or legacy issues)
        section_headers = [
            "## 📋 Tracked Tasks & Action Items",
            "## 📋 Tracked Tasks",
            "## 📋 Tracked Issues & Feature Ideas",
            "## 📋 Tracked Issues",
        ]
        target_header = None
        for h in section_headers:
            if h in body:
                target_header = h
                break

        if target_header:
            parts = body.split(target_header, 1)
            before_sec = parts[0] + target_header + "\n"
            after_sec = parts[1]

            next_header = re.search(r"\n##\s+", after_sec)
            if next_header:
                sec_content = after_sec[:next_header.start()]
                rest = after_sec[next_header.start():]
            else:
                sec_content = after_sec
                rest = ""

            lines = [l for l in sec_content.splitlines() if l.strip()]
            new_lines = []
            replaced = False
            for l in lines:
                if task_id in l or title in l or os.path.basename(task_file_path) in l:
                    new_lines.append(task_entry)
                    replaced = True
                else:
                    new_lines.append(l)
            if not replaced:
                new_lines.append(task_entry)

            updated_sec = "\n" + "\n".join(new_lines) + "\n"
            body = before_sec + updated_sec + rest
        else:
            new_header = "## 📋 Tracked Tasks & Action Items"
            insert_marker = "## 📁 Key Files & Code Symbols"
            if insert_marker in body:
                body = body.replace(
                    insert_marker,
                    f"{new_header}\n{task_entry}\n\n{insert_marker}"
                )
            else:
                body = body.rstrip() + f"\n\n{new_header}\n{task_entry}\n"

        new_content = dump_frontmatter(meta, body)
        with open(session_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"⚠️ Failed to sync task to session file {session_file_path}: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report, update, evolve, and manage tasks and action items."
    )
    parser.add_argument("--title", help="Short task/action title")
    parser.add_argument(
        "--type", default="task",
        help="Task type/tag (e.g. 'follow-up', 'bug', 'idea', 'debt', 'design', 'ops', 'business', 'marketing')",
    )
    parser.add_argument(
        "--priority", default="P2",
        choices=VALID_PRIORITIES,
        help="Priority level (P0=urgent, P1=high, P2=medium, P3=low)",
    )
    parser.add_argument(
        "--severity", dest="priority_alias",
        choices=VALID_PRIORITIES,
        help="Backward-compatible alias for --priority",
    )
    parser.add_argument(
        "--status",
        choices=VALID_STATUSES,
        help="Task status: todo | in_progress | blocked | done | dropped",
    )
    parser.add_argument(
        "--start", "--in-progress", dest="start_task", action="store_true",
        help="Set task status to 'in_progress'",
    )
    parser.add_argument(
        "--block", nargs="?", const="Blocked on external dependency",
        help="Set task status to 'blocked' with optional reason",
    )
    parser.add_argument(
        "--done", "--complete", dest="done_task", action="store_true",
        help="Set task status to 'done'",
    )
    parser.add_argument(
        "--drop", "--reject", dest="drop_reason", nargs="?",
        const="Dropped by user during consultation",
        help="Mark task as dropped with optional deciding factors / reason",
    )
    parser.add_argument("--reporter", default="scribe", help="Agent or human that logged the task")
    parser.add_argument("--assignee", help="Person or agent assigned (e.g. '@user', '@me', '@aaron', '@scribe')")
    parser.add_argument("--file", default="", help="Affected file path (optional)")
    parser.add_argument("--description", default="", help="Full description of the task or action")
    parser.add_argument("--suggested-action", default="", help="Recommended next step or implementation plan")
    parser.add_argument("--session-id", default="", help="Associated session sequence ID (e.g. '026')")
    parser.add_argument("--session-file", default="", help="Path to session context markdown note")
    parser.add_argument(
        "--tools", "--recommended-tools", dest="recommended_tools",
        help="Comma-separated list of recommended enabling tools or MCP servers",
    )
    parser.add_argument(
        "--delegated-to",
        help="Subagent or worker delegated to execute this task",
    )
    parser.add_argument(
        "--github-labels",
        help="Comma-separated list of GitHub labels to attach",
    )
    parser.add_argument(
        "--github-issue",
        help="Linked GitHub issue number/url if synced",
    )
    parser.add_argument(
        "--evolution-note",
        help="Decision note explaining requirement evolution, trade-offs, or updates mid-session",
    )
    parser.add_argument(
        "--update",
        help="File path or ID/slug of an existing task to update",
    )
    parser.add_argument(
        "--find-similar",
        help="Search for existing tasks similar to the given title string",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List tasks across task directories",
    )
    parser.add_argument(
        "--sync-session", action="store_true",
        help="Sync task metadata back into the active session context file",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--out-dir", default="",
        help="Output directory for task files (defaults to workforces/tasks/ or .scribe/tasks/)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip duplicate check and write regardless",
    )

    args = parser.parse_args()

    # Determine default tasks directory
    if args.out_dir:
        tasks_dir = args.out_dir
    elif os.path.isdir("workforces/tasks"):
        tasks_dir = "workforces/tasks"
    elif os.path.isdir(".scribe/tasks"):
        tasks_dir = ".scribe/tasks"
    elif os.path.isdir("workforces/issues/inbox"):
        tasks_dir = "workforces/tasks"
    else:
        tasks_dir = "workforces/tasks"

    # Search directories include standard task dirs and legacy issue dirs
    search_dirs = [
        tasks_dir,
        "workforces/tasks",
        ".scribe/tasks",
        "workforces/issues/inbox",
        "workforces/issues/triaged",
        "workforces/issues/completed",
    ]

    # Resolve priority
    effective_priority = args.priority_alias or args.priority

    # MODE 1: Find Similar Tasks
    if args.find_similar:
        results = find_similar_tasks(args.find_similar, search_dirs)
        if args.json:
            output = [
                {
                    "path": fpath,
                    "similarity": round(ratio, 2),
                    "title": meta.get("title", ""),
                    "type": meta.get("type", ""),
                    "priority": meta.get("priority", meta.get("severity", "")),
                    "status": meta.get("status", ""),
                    "session_id": meta.get("session_id"),
                }
                for fpath, ratio, meta in results
            ]
            print(json.dumps(output, indent=2))
        else:
            if not results:
                print(f"No similar tasks found for '{args.find_similar}'.")
            else:
                print(f"🔍 Found {len(results)} matching task(s):")
                for fpath, ratio, meta in results:
                    status_str = meta.get("status", "todo")
                    print(f"  - [{ratio:.0%}] ({status_str}) {meta.get('title', '')}")
                    print(f"    Path: {fpath}")
                    if meta.get("session_id"):
                        print(f"    Session: #{meta.get('session_id')}")
        return

    # MODE 2: List Tasks
    if args.list:
        tasks = []
        seen_paths = set()
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.abspath(os.path.join(d, fname))
                if fpath in seen_paths:
                    continue
                seen_paths.add(fpath)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        meta, _ = parse_frontmatter(f.read())
                        status_val = meta.get("status", "todo")
                        if args.status and status_val != args.status:
                            continue
                        tasks.append((fpath, meta))
                except OSError:
                    continue

        if args.json:
            print(json.dumps([{"path": p, **m} for p, m in tasks], indent=2))
        else:
            if not tasks:
                print("No tasks found.")
            else:
                print(f"📋 Found {len(tasks)} task(s):")
                for fpath, meta in tasks:
                    prio = meta.get("priority", meta.get("severity", "P2"))
                    st = meta.get("status", "todo")
                    ttype = meta.get("type", "task")
                    print(f"  - [{st}] [{prio}] ({ttype}) {meta.get('title', '')} -> {fpath}")
        return

    # MODE 3: Update Existing Task
    update_target = args.update or (args.drop_reason if (args.drop_reason and not args.title and os.path.exists(str(args.drop_reason))) else None)
    if update_target:
        target_file = find_task_by_identifier(update_target, search_dirs)
        if not target_file:
            print(f"❌ Error: Could not locate task matching '{update_target}'", file=sys.stderr)
            sys.exit(1)

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        now = datetime.datetime.now()

        # Update metadata fields if explicitly provided
        if args.title:
            meta["title"] = args.title
        if args.type and args.type != "task":
            meta["type"] = args.type
        if effective_priority and effective_priority != "P2":
            meta["priority"] = effective_priority
            if "severity" in meta:
                del meta["severity"]
        elif "severity" in meta and "priority" not in meta:
            meta["priority"] = meta.pop("severity")

        if args.reporter and args.reporter != "scribe":
            meta["reporter"] = args.reporter
        if args.assignee:
            meta["assignee"] = args.assignee
        if args.file:
            meta["file"] = args.file
        if args.session_id:
            meta["session_id"] = args.session_id
        if args.session_file:
            meta["session_file"] = args.session_file
        if args.recommended_tools:
            tools_list = [t.strip() for t in args.recommended_tools.replace(",", " ").split() if t.strip()]
            meta["recommended_tools"] = tools_list
        if args.delegated_to:
            meta["delegated_to"] = args.delegated_to
        if args.github_labels:
            labels_list = [l.strip() for l in args.github_labels.replace(",", " ").split() if l.strip()]
            meta["github_labels"] = labels_list
        if args.github_issue:
            meta["github_issue"] = args.github_issue

        # Handle status transitions
        if args.status:
            meta["status"] = args.status
        elif args.start_task:
            meta["status"] = "in_progress"
        elif args.block:
            meta["status"] = "blocked"
        elif args.done_task:
            meta["status"] = "done"
        elif args.drop_reason:
            meta["status"] = "dropped"

        # Remove legacy triage fields if present
        if "triage_status" in meta:
            del meta["triage_status"]

        meta["updated_at"] = now.isoformat()

        # Update description / suggested action in body if provided
        if args.description:
            desc_match = re.search(r"## Description\s*\n\n(.*?)(?=\n\n##|\Z)", body, re.DOTALL)
            if desc_match:
                body = body[:desc_match.start(1)] + args.description + body[desc_match.end(1):]

        if args.suggested_action:
            act_match = re.search(r"## Suggested Action\s*\n\n(.*?)(?=\n\n##|\Z)", body, re.DOTALL)
            if act_match:
                body = body[:act_match.start(1)] + args.suggested_action + body[act_match.end(1):]

        # Handle deciding factor / evolution note
        evo_header = "## 🧠 Session Lineage & Deciding Factors"
        evo_entry = None
        drop_note = None

        if args.drop_reason:
            drop_note = args.drop_reason if (isinstance(args.drop_reason, str) and args.drop_reason.strip() and args.drop_reason != "true") else "Dropped by user during consultation."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ❌ Dropped: {drop_note}"
        elif args.block and isinstance(args.block, str) and args.block.strip() and args.block != "true":
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ⚠️ Blocked: {args.block}"
        elif args.done_task:
            note_text = args.evolution_note or "Task completed."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ✅ Completed: {note_text}"
        elif args.start_task:
            note_text = args.evolution_note or "Started task execution."
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ⏳ In Progress: {note_text}"
        elif args.evolution_note:
            evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}"

        if evo_entry:
            if evo_header in body:
                parts = body.split(evo_header, 1)
                before = parts[0] + evo_header + "\n\n"
                after = parts[1].lstrip("\r\n")
                body = before + evo_entry + "\n" + after
            else:
                body = body.rstrip() + f"\n\n{evo_header}\n\n{evo_entry}\n"

        # Update frontmatter & write in-place
        new_content = dump_frontmatter(meta, body)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Task updated: {target_file} (Status: {meta.get('status', 'todo')})")

        # Sync back to session file if requested
        session_file = args.session_file or meta.get("session_file")
        if (args.sync_session or session_file) and session_file:
            evo_summary = args.evolution_note or drop_note or (f"Status changed to {meta.get('status')}")
            sync_task_to_session_file(
                session_file,
                target_file,
                meta,
                evolution_summary=evo_summary
            )
            print(f"🔗 Synced to session context: {session_file}")

        return

    # MODE 4: Create New Task
    if not args.title:
        print("❌ Error: --title is required to create a new task.", file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        sys.exit(1)

    # Check for duplicates unless --force
    if not args.force:
        similar = find_similar_tasks(args.title, search_dirs, threshold=0.75)
        if similar:
            print("⚠️  Similar task(s) already exist — skipping to avoid duplicates:\n")
            for fpath, ratio, meta in similar:
                st = meta.get("status", "todo")
                print(f"   [{ratio:.0%} match] ({st}) {meta.get('title', extract_title(fpath))}")
                print(f"   → {fpath}\n")
            print("💡 Options:")
            print(f"   - Update existing: python3 {sys.argv[0]} --update \"{similar[0][0]}\" --evolution-note \"...\"")
            print(f"   - Drop existing:   python3 {sys.argv[0]} --update \"{similar[0][0]}\" --drop \"...\"")
            print("   - Force create anyway: re-run with --force")
            sys.exit(1)

    os.makedirs(tasks_dir, exist_ok=True)
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    filename = f"{timestamp}-{slug}.md"
    filepath = os.path.join(tasks_dir, filename)

    evolution_notes = []
    if args.evolution_note:
        evolution_notes.append(f"**{now.strftime('%Y-%m-%d %H:%M')}:** {args.evolution_note}")

    tools_list = [t.strip() for t in args.recommended_tools.replace(",", " ").split() if t.strip()] if args.recommended_tools else []
    labels_list = [l.strip() for l in args.github_labels.replace(",", " ").split() if l.strip()] if args.github_labels else []

    init_status = args.status or ("in_progress" if args.start_task else "todo")

    content = build_task_markdown(
        title=args.title,
        task_type=args.type,
        priority=effective_priority,
        status=init_status,
        reporter=args.reporter,
        assignee=args.assignee,
        description=args.description,
        suggested_action=args.suggested_action,
        file_path=args.file,
        session_id=args.session_id,
        session_file=args.session_file,
        recommended_tools=tools_list,
        delegated_to=args.delegated_to,
        github_labels=labels_list,
        github_issue=args.github_issue,
        evolution_notes=evolution_notes,
        created_at=now,
        updated_at=now,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Task created: {filepath}")

    if args.sync_session and args.session_file:
        meta_dict = {
            "title": args.title,
            "type": args.type,
            "priority": effective_priority,
            "status": init_status,
            "assignee": args.assignee,
            "description": args.description,
            "recommended_tools": tools_list,
            "delegated_to": args.delegated_to,
            "github_labels": labels_list,
        }
        sync_task_to_session_file(
            args.session_file,
            filepath,
            meta_dict,
            evolution_summary=args.evolution_note or args.description[:100]
        )
        print(f"🔗 Synced to session context: {args.session_file}")


if __name__ == "__main__":
    main()
