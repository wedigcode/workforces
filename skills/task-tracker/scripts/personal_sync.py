#!/usr/bin/env python3
"""
personal_sync — Personal status, task, git, and follow-up intelligence aggregator for /sync --me.

Aggregates:
  1. Git workspace (branch, uncommitted changes, recent commits)
  2. Active and blocked tasks from workforces/tasks/
  3. Sprint state and blockers from workforces/workstate.md
  4. Active decisions and context from workforces/session-context/
  5. GitHub PR reviews, assigned issues, and authored PRs via `gh` CLI
  6. Running hypotheses from workforces/hypotheses/running/
  7. Async workers (e.g. Google Jules sessions if available)

Usage:
  python3 skills/task-tracker/scripts/personal_sync.py
  python3 skills/task-tracker/scripts/personal_sync.py --root ./ --format markdown
  python3 skills/task-tracker/scripts/personal_sync.py --format json
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


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

        if stripped.startswith("- ") and current_list_key:
            item_text = stripped[2:].strip()
            if ":" in item_text:
                sub_k, sub_v = item_text.split(":", 1)
                sub_k = sub_k.strip()
                sub_v = sub_v.strip().strip('"').strip("'")
                current_dict_in_list = {sub_k: sub_v}
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(current_dict_in_list)
            else:
                current_dict_in_list = None
                val = item_text.strip('"').strip("'")
                if not isinstance(metadata.get(current_list_key), list):
                    metadata[current_list_key] = []
                metadata[current_list_key].append(val)
            continue

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


def get_git_status(root_dir: str) -> Dict[str, Any]:
    """Retrieve git branch, uncommitted changes, and recent user commits."""
    res = {
        "is_git": False,
        "branch": "unknown",
        "has_uncommitted": False,
        "modified_count": 0,
        "modified_files": [],
        "recent_commits": [],
    }

    try:
        # Check branch
        branch_proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_proc.returncode == 0:
            res["is_git"] = True
            res["branch"] = branch_proc.stdout.strip()
        else:
            return res

        # Check status porcelain
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if status_proc.returncode == 0:
            lines = [l.strip() for l in status_proc.stdout.splitlines() if l.strip()]
            res["has_uncommitted"] = len(lines) > 0
            res["modified_count"] = len(lines)
            res["modified_files"] = lines[:10]  # Cap at 10

        # Check recent commits
        log_proc = subprocess.run(
            ["git", "log", "-n", "5", "--format=%h - %s (%cr)"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if log_proc.returncode == 0:
            res["recent_commits"] = [l.strip() for l in log_proc.stdout.splitlines() if l.strip()]

    except (subprocess.SubprocessError, OSError):
        pass

    return res


def get_tasks_summary(root_dir: str, assignee: Optional[str] = None) -> Dict[str, Any]:
    """Scan workforces/tasks/ for active, blocked, and pending tasks."""
    summary: Dict[str, Any] = {
        "in_progress": [],
        "blocked": [],
        "high_priority_todo": [],
        "total_active": 0,
    }

    tasks_dir = os.path.join(root_dir, "workforces", "tasks")
    if not os.path.isdir(tasks_dir):
        # Fallback to local tasks directory
        tasks_dir = os.path.join(root_dir, "tasks")
        if not os.path.isdir(tasks_dir):
            return summary

    for fname in sorted(os.listdir(tasks_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(tasks_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                meta, _ = parse_frontmatter(f.read())

            status = meta.get("status", "todo")
            priority = meta.get("priority", meta.get("severity", "P2"))
            task_assignee = meta.get("assignee")
            title = meta.get("title", fname[:-3])

            task_item = {
                "id": fname[:-3],
                "file": fpath,
                "title": title,
                "type": meta.get("type", "task"),
                "priority": priority,
                "status": status,
                "assignee": task_assignee,
                "updated_at": meta.get("updated_at", ""),
                "suggested_action": meta.get("suggested_action", ""),
            }

            # If assignee filter is provided and does not match, skip if not relevant
            if assignee and task_assignee and assignee.lower() not in task_assignee.lower():
                continue

            if status == "in_progress":
                summary["in_progress"].append(task_item)
                summary["total_active"] += 1
            elif status == "blocked":
                summary["blocked"].append(task_item)
                summary["total_active"] += 1
            elif status == "todo" and priority in ("P0", "P1"):
                summary["high_priority_todo"].append(task_item)
                summary["total_active"] += 1

        except OSError:
            continue

    return summary


def get_workstate_summary(root_dir: str) -> Dict[str, Any]:
    """Parse workforces/workstate.md for active sprint tasks and blockers."""
    summary: Dict[str, Any] = {
        "active_sprint_tasks": [],
        "roadblocks": [],
        "last_updated": None,
    }

    workstate_path = os.path.join(root_dir, "workforces", "workstate.md")
    if not os.path.isfile(workstate_path):
        return summary

    try:
        with open(workstate_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Extract Active Tasks table
        table_match = re.search(r"## Active Tasks\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if table_match:
            table_text = table_match.group(1).strip()
            for line in table_text.splitlines():
                line = line.strip()
                if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                    cols = [c.strip() for c in line.split("|")[1:-1]]
                    if cols and len(cols) >= 3:
                        task_name = cols[1] if len(cols) > 1 else cols[0]
                        status = cols[2] if len(cols) > 2 else ""
                        summary["active_sprint_tasks"].append({
                            "name": task_name,
                            "status": status,
                            "raw": line
                        })

        # Extract Roadblocks
        roadblocks_match = re.search(r"## Unforeseen Risks & Discovered Gaps\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if roadblocks_match:
            for line in roadblocks_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    summary["roadblocks"].append(line.lstrip("-* ").strip())

    except OSError:
        pass

    return summary


def get_session_context_summary(root_dir: str) -> Dict[str, Any]:
    """Retrieve the newest session context note and key active decisions."""
    summary: Dict[str, Any] = {
        "session_file": None,
        "session_id": None,
        "topic": None,
        "updated_at": None,
        "recent_decisions": [],
        "active_files": [],
    }

    session_dir = os.path.join(root_dir, "workforces", "session-context")
    if not os.path.isdir(session_dir):
        return summary

    notes = [f for f in os.listdir(session_dir) if f.endswith(".md") and not f.startswith(".")]
    if not notes:
        return summary

    notes.sort(reverse=True)
    latest_note = os.path.join(session_dir, notes[0])

    try:
        with open(latest_note, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        summary["session_file"] = latest_note
        summary["session_id"] = meta.get("session_id", meta.get("sequence", ""))
        summary["topic"] = meta.get("topic", "")
        summary["updated_at"] = meta.get("updated_at", "")
        summary["active_files"] = meta.get("active_files", [])

        # Extract Decisions & Reasoning
        decisions_match = re.search(r"## 🧠 Decisions & Reasoning.*?\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if decisions_match:
            for line in decisions_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    summary["recent_decisions"].append(line.lstrip("-* ").strip())

    except OSError:
        pass

    return summary


def get_running_hypotheses(root_dir: str) -> List[Dict[str, Any]]:
    """Scan workforces/hypotheses/running/ for active experiments."""
    hypotheses = []
    hyp_dir = os.path.join(root_dir, "workforces", "hypotheses", "running")
    if not os.path.isdir(hyp_dir):
        return hypotheses

    for fname in sorted(os.listdir(hyp_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(hyp_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                meta, _ = parse_frontmatter(f.read())
            hypotheses.append({
                "id": fname[:-3],
                "title": meta.get("title", fname[:-3]),
                "owner": meta.get("owner", "unassigned"),
                "status": meta.get("status", "running"),
                "file": fpath,
            })
        except OSError:
            continue

    return hypotheses


def get_github_summary(root_dir: str, user: str = "@me") -> Dict[str, Any]:
    """Query GitHub CLI for review requests, assigned issues, and authored PRs."""
    gh_data: Dict[str, Any] = {
        "available": False,
        "review_requests": [],
        "assigned_issues": [],
        "authored_prs": [],
        "error": None,
    }

    if not shutil.which("gh"):
        gh_data["error"] = "GitHub CLI (`gh`) not installed in PATH"
        return gh_data

    # Check if gh is authenticated
    try:
        auth_check = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if auth_check.returncode != 0:
            gh_data["error"] = "GitHub CLI not logged in or authenticated"
            return gh_data
        gh_data["available"] = True
    except (subprocess.SubprocessError, OSError) as e:
        gh_data["error"] = str(e)
        return gh_data

    # 1. PR Reviews requested
    try:
        pr_rev_proc = subprocess.run(
            ["gh", "pr", "list", "--search", f"review-requested:{user}", "--state", "open", "--limit", "10", "--json", "number,title,url,author,updatedAt"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if pr_rev_proc.returncode == 0 and pr_rev_proc.stdout.strip():
            gh_data["review_requests"] = json.loads(pr_rev_proc.stdout)
    except Exception:
        pass

    # 2. Issues assigned
    try:
        issue_proc = subprocess.run(
            ["gh", "issue", "list", "--assignee", user, "--state", "open", "--limit", "10", "--json", "number,title,url,labels,updatedAt"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if issue_proc.returncode == 0 and issue_proc.stdout.strip():
            gh_data["assigned_issues"] = json.loads(issue_proc.stdout)
    except Exception:
        pass

    # 3. PRs authored by user awaiting review
    try:
        pr_auth_proc = subprocess.run(
            ["gh", "pr", "list", "--author", user, "--state", "open", "--limit", "10", "--json", "number,title,url,reviewRequests,updatedAt"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if pr_auth_proc.returncode == 0 and pr_auth_proc.stdout.strip():
            gh_data["authored_prs"] = json.loads(pr_auth_proc.stdout)
    except Exception:
        pass

    return gh_data


def get_jules_sessions(root_dir: str) -> List[Dict[str, Any]]:
    """Check for active Google Jules sessions if CLI is available (filtering out Completed)."""
    sessions: List[Dict[str, Any]] = []
    if not shutil.which("jules"):
        return sessions

    try:
        proc = subprocess.run(
            ["jules", "remote", "list", "--session"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=6,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("ID") and not line.startswith("---"):
                    # Strictly filter for active sessions where Status != 'Completed'
                    if not line.endswith("Completed") and " Completed" not in line:
                        sessions.append({"raw": line})
    except Exception:
        pass

    return sessions


def generate_personal_sync_data(
    root_dir: str,
    user: str = "@me",
    check_github: bool = True,
) -> Dict[str, Any]:
    """Aggregate all personal status and follow-up data across sources."""
    root_dir = os.path.abspath(root_dir)
    now = datetime.datetime.now()

    data = {
        "timestamp": now.isoformat(),
        "root_dir": root_dir,
        "user": user,
        "git": get_git_status(root_dir),
        "tasks": get_tasks_summary(root_dir, assignee=user if user != "@me" else None),
        "workstate": get_workstate_summary(root_dir),
        "session_context": get_session_context_summary(root_dir),
        "hypotheses": get_running_hypotheses(root_dir),
        "jules_sessions": get_jules_sessions(root_dir),
        "github": get_github_summary(root_dir, user=user) if check_github else {"available": False},
    }
    return data


def format_markdown_report(data: Dict[str, Any]) -> str:
    """Format aggregated personal data into a rich human-readable markdown briefing."""
    timestamp = datetime.datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d %H:%M")
    git = data.get("git", {})
    tasks = data.get("tasks", {})
    workstate = data.get("workstate", {})
    session_ctx = data.get("session_context", {})
    gh = data.get("github", {})
    hypotheses = data.get("hypotheses", [])
    jules = data.get("jules_sessions", [])

    lines = []
    lines.append(f"## 👤 Personal Sync & Follow-Up Radar (`/sync --me`) — {timestamp}")
    lines.append("")

    # Section 1: What You Are Working On
    lines.append("### 🔨 What You Are Working On (Active Focus)")
    if git.get("is_git"):
        branch = git.get("branch", "main")
        uncommitted = git.get("modified_count", 0)
        lines.append(f"- **Git Workspace:** Branch `{branch}` | {uncommitted} modified/staged file(s)")
        if git.get("recent_commits"):
            recent = git["recent_commits"][0]
            lines.append(f"  - *Latest Commit:* `{recent}`")
    else:
        lines.append("- **Git Workspace:** Non-git directory or git not initialized.")

    if tasks.get("in_progress"):
        for t in tasks["in_progress"]:
            lines.append(f"- **In-Progress Task:** [{t['title']}]({t['file']}) (`{t['type']}` | **{t['priority']}**)")
            if t.get("suggested_action"):
                lines.append(f"  - *Next Action:* {t['suggested_action']}")
    elif workstate.get("active_sprint_tasks"):
        for st in workstate["active_sprint_tasks"][:3]:
            lines.append(f"- **Active Sprint Task:** {st['name']} ({st['status']})")
    else:
        lines.append("- *No tasks currently flagged `in_progress` in `workforces/tasks/`.*")

    if session_ctx.get("topic"):
        lines.append(f"- **Active Session Topic:** {session_ctx['topic']} (Session #{session_ctx.get('session_id', 'N/A')})")

    if jules:
        lines.append(f"- **Async Coding Workers (Jules):** {len(jules)} active session(s)")
        for j in jules[:2]:
            lines.append(f"  - `{j['raw']}`")
    lines.append("")

    # Section 2: High-Priority Follow-ups Required From You
    lines.append("### 🚨 High-Priority Follow-ups Required From You (Action Needed)")
    has_action_items = False

    if gh.get("available") and gh.get("review_requests"):
        lines.append("- **🔍 PR Reviews Awaiting Your Approval:**")
        for pr in gh["review_requests"]:
            author_name = pr.get("author", {}).get("login", "unknown") if isinstance(pr.get("author"), dict) else pr.get("author", "unknown")
            lines.append(f"  - [PR #{pr['number']}: {pr['title']}]({pr['url']}) by `@{author_name}`")
        has_action_items = True

    if gh.get("available") and gh.get("assigned_issues"):
        lines.append("- **📋 Assigned GitHub Issues:**")
        for issue in gh["assigned_issues"][:5]:
            lines.append(f"  - [Issue #{issue['number']}: {issue['title']}]({issue['url']})")
        has_action_items = True

    if tasks.get("blocked"):
        lines.append("- **⚠️ Blocked Tasks Needing Unblocking:**")
        for t in tasks["blocked"]:
            lines.append(f"  - [{t['title']}]({t['file']}) (`{t['priority']}`) — *{t.get('suggested_action', 'Blocked')}*")
        has_action_items = True

    if not has_action_items:
        lines.append("- *No urgent blockers or assigned PR reviews flagged in local queues.*")
        lines.append("- *(Note: AI agent will dynamically query lazy communication MCPs like `ms-teams-email` for unread emails and direct messages).*")
    lines.append("")

    # Section 3: Follow-ups You Are Waiting On
    lines.append("### ⏳ Follow-ups You Are Waiting On (Pending Counterparties)")
    has_waiting_items = False

    if gh.get("available") and gh.get("authored_prs"):
        lines.append("- **PRs Authored by You Awaiting Review:**")
        for pr in gh["authored_prs"]:
            lines.append(f"  - [PR #{pr['number']}: {pr['title']}]({pr['url']})")
        has_waiting_items = True

    if hypotheses:
        lines.append("- **Active Running Hypotheses (Awaiting Telemetry / Pacing):**")
        for h in hypotheses:
            lines.append(f"  - [{h['title']}]({h['file']}) (Owner: `@{h['owner']}`)")
        has_waiting_items = True

    if not has_waiting_items:
        lines.append("- *No outgoing PRs or blocked dependencies currently waiting on external review.*")
    lines.append("")

    # Section 4: Upcoming Focus & High Priority Backlog
    if tasks.get("high_priority_todo"):
        lines.append("### 🎯 Ready to Pick Up (P0/P1 Backlog)")
        for t in tasks["high_priority_todo"][:4]:
            lines.append(f"- [{t['title']}]({t['file']}) (`{t['type']}` | **{t['priority']}**)")
        lines.append("")

    # Section 5: Recent Decisions & Context
    if session_ctx.get("recent_decisions"):
        lines.append("### 📝 Recent Decisions & Notes")
        for d in session_ctx["recent_decisions"][:4]:
            lines.append(f"- {d}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by Workforces Personal Sync Engine (`skills/task-tracker/scripts/personal_sync.py`)*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate personal status, tasks, git state, and follow-ups for /sync --me."
    )
    parser.add_argument("--root", default=os.getcwd(), help="Target root directory (default: current working dir)")
    parser.add_argument("--assignee", "--user", default="@me", help="User / Assignee filter (default: @me)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format (default: markdown)")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub CLI checks")

    args = parser.parse_args()

    data = generate_personal_sync_data(
        root_dir=args.root,
        user=args.assignee,
        check_github=not args.no_github,
    )

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_markdown_report(data))


if __name__ == "__main__":
    main()
