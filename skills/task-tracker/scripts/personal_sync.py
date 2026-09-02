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


def sync_task_to_session_file(
    session_file_path: str,
    task_file_path: str,
    task_meta: Dict[str, Any],
    evolution_summary: str = "",
) -> bool:
    """Ensure the session context markdown file lists the task in frontmatter (tracked_tasks) and body."""
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


def get_tracked_repos(root_dir: str) -> List[str]:
    """
    Extract list of tracked repositories from workrules.md, workstate.md, projects/, or git remote.
    Returns clean, deduplicated list of 'owner/repo' strings.
    """
    repos: List[str] = []
    seen = set()

    def add_repo(r: str):
        if not isinstance(r, str):
            return
        r = r.strip().strip("'\"`").rstrip("/")
        if not r:
            return
        # If full git URL (git@github.com:owner/repo.git or https://github.com/owner/repo)
        url_match = re.search(r"github\.com[/:]([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$", r)
        if url_match:
            slug = f"{url_match.group(1)}/{url_match.group(2)}"
            if slug not in seen:
                seen.add(slug)
                repos.append(slug)
            return
        # Standard owner/repo slug
        if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", r):
            if r not in seen:
                seen.add(r)
                repos.append(r)

    # 1. Check workrules.md and workstate.md
    config_paths = [
        os.path.join(root_dir, "workforces", "workrules.md"),
        os.path.join(root_dir, "workforces", "workstate.md"),
        os.path.join(root_dir, "workrules.md"),
        os.path.join(root_dir, "workstate.md"),
    ]
    for cfg in config_paths:
        if not os.path.isfile(cfg):
            continue
        try:
            with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            meta, body = parse_frontmatter(content)
            # Check frontmatter keys
            for k in ("tracked_repos", "repos", "repositories", "projects"):
                v = meta.get(k)
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            add_repo(item)
                        elif isinstance(item, dict) and "repo" in item:
                            add_repo(item["repo"])

            # Check body lines for YAML-like lists under headers or keys
            in_repo_section = False
            in_tracked_key = False
            for line in content.splitlines():
                line_str = line.strip()
                if re.match(r"^#+\s*.*(?:tracked\s+repo|repositories|projects)", line_str, re.I):
                    in_repo_section = True
                    in_tracked_key = False
                    continue
                if line_str.startswith("#"):
                    in_repo_section = False
                    in_tracked_key = False

                if re.search(r"^(?:-\s+)?(?:tracked_repos|repos|repositories|projects)\s*:", line_str, re.I):
                    in_tracked_key = True
                    inline_val = re.sub(r"^(?:-\s+)?(?:tracked_repos|repos|repositories|projects)\s*:\s*", "", line_str, flags=re.I)
                    if inline_val.startswith("[") and inline_val.endswith("]"):
                        for raw in inline_val.strip("[]").split(","):
                            add_repo(raw)
                    continue

                if in_tracked_key:
                    if re.match(r"^\s+-\s+", line):
                        m_item = re.search(r"^\s+-\s+[`'\"]?([^\s`'\"]+)[`'\"]?", line)
                        if m_item:
                            add_repo(m_item.group(1))
                        continue
                    elif line_str:
                        in_tracked_key = False

                match_inline = re.search(r"(?:tracked_repos|repos|repositories)\s*:\s*\[(.*?)\]", line_str, re.I)
                if match_inline:
                    for raw in match_inline.group(1).split(","):
                        add_repo(raw)
                    continue

                if in_repo_section:
                    m_item = re.search(r"^\s*-\s+[`'\"]?([^\s`'\"]+)[`'\"]?", line)
                    if m_item:
                        add_repo(m_item.group(1))
        except OSError:
            pass

    # 2. Check workforces/projects/ directory
    projects_dir = os.path.join(root_dir, "workforces", "projects")
    if os.path.isdir(projects_dir):
        for entry in os.listdir(projects_dir):
            epath = os.path.join(projects_dir, entry)
            if os.path.isfile(epath) and entry.endswith(".md"):
                try:
                    with open(epath, "r", encoding="utf-8", errors="ignore") as f:
                        pmeta, _ = parse_frontmatter(f.read())
                    if pmeta.get("repo"):
                        add_repo(pmeta["repo"])
                except OSError:
                    pass

    # 3. Check current git remote origin
    try:
        remote_proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if remote_proc.returncode == 0 and remote_proc.stdout.strip():
            add_repo(remote_proc.stdout.strip())
    except Exception:
        pass

    return repos


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


def get_github_summary(
    root_dir: str,
    user: str = "@me",
    tracked_repos: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Query GitHub CLI for review requests, assigned issues, and authored PRs across all tracked repos."""
    gh_data: Dict[str, Any] = {
        "available": False,
        "review_requests": [],
        "assigned_issues": [],
        "authored_prs": [],
        "tracked_repos": tracked_repos or [],
        "error": None,
    }

    if not shutil.which("gh"):
        gh_data["error"] = "GitHub CLI (`gh`) not installed in PATH"
        return gh_data

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

    target_repos = tracked_repos if (tracked_repos and len(tracked_repos) > 0) else [None]

    for repo in target_repos:
        repo_flags = ["--repo", repo] if repo else []

        # 1. PR Reviews requested
        try:
            cmd = ["gh", "pr", "list", *repo_flags, "--search", f"review-requested:{user}", "--state", "open", "--limit", "10", "--json", "number,title,url,author,updatedAt"]
            pr_rev_proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, timeout=8)
            if pr_rev_proc.returncode == 0 and pr_rev_proc.stdout.strip():
                items = json.loads(pr_rev_proc.stdout)
                for item in items:
                    if repo:
                        item["repo"] = repo
                    gh_data["review_requests"].append(item)
        except Exception:
            pass

        # 2. Issues assigned
        try:
            cmd = ["gh", "issue", "list", *repo_flags, "--assignee", user, "--state", "open", "--limit", "10", "--json", "number,title,url,labels,updatedAt"]
            issue_proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, timeout=8)
            if issue_proc.returncode == 0 and issue_proc.stdout.strip():
                items = json.loads(issue_proc.stdout)
                for item in items:
                    if repo:
                        item["repo"] = repo
                    gh_data["assigned_issues"].append(item)
        except Exception:
            pass

        # 3. PRs authored by user awaiting review
        try:
            cmd = ["gh", "pr", "list", *repo_flags, "--author", user, "--state", "open", "--limit", "10", "--json", "number,title,url,reviewRequests,updatedAt"]
            pr_auth_proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, timeout=8)
            if pr_auth_proc.returncode == 0 and pr_auth_proc.stdout.strip():
                items = json.loads(pr_auth_proc.stdout)
                for item in items:
                    if repo:
                        item["repo"] = repo
                    gh_data["authored_prs"].append(item)
        except Exception:
            pass

    return gh_data


def reconcile_github_tasks(
    root_dir: str,
    tracked_repos: Optional[List[str]] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Scan workforces/tasks/*.md for tasks linked to GitHub PRs or issues.
    If a linked PR is merged or closed on GitHub, auto-transitions the task to 'done'.
    """
    reconciled: List[Dict[str, Any]] = []
    if not shutil.which("gh"):
        return reconciled

    tasks_dir = os.path.join(root_dir, "workforces", "tasks")
    if not os.path.isdir(tasks_dir):
        tasks_dir = os.path.join(root_dir, "tasks")
        if not os.path.isdir(tasks_dir):
            return reconciled

    now = datetime.datetime.now()

    for fname in sorted(os.listdir(tasks_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(tasks_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            meta, body = parse_frontmatter(content)
            status = meta.get("status", "todo")
            if status in ("done", "dropped", "rejected", "completed"):
                continue

            pr_ref = meta.get("github_pr") or meta.get("pr") or meta.get("github_issue") or meta.get("issue")
            repo_hint = None
            pr_number = None

            if pr_ref:
                pr_str = str(pr_ref).strip()
                url_m = re.search(r"github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)/(?:pull|issues)/(\d+)", pr_str)
                if url_m:
                    repo_hint = url_m.group(1)
                    pr_number = url_m.group(2)
                elif re.match(r"^\d+$", pr_str):
                    pr_number = pr_str
                elif "#" in pr_str:
                    num_m = re.search(r"#(\d+)", pr_str)
                    if num_m:
                        pr_number = num_m.group(1)
            else:
                body_m = re.search(r"(?:PR\s*#?|pull/|#)(\d{2,6})", body, re.IGNORECASE)
                if body_m:
                    pr_number = body_m.group(1)
                url_body_m = re.search(r"https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)/pull/(\d+)", body)
                if url_body_m:
                    repo_hint = url_body_m.group(1)
                    pr_number = url_body_m.group(2)

            if not pr_number:
                continue

            repos_to_check = [repo_hint] if repo_hint else (tracked_repos or [None])
            found_pr_info = None

            for r in repos_to_check:
                cmd = ["gh", "pr", "view", pr_number, "--json", "state,mergedAt,title,url"]
                if r:
                    cmd.extend(["--repo", r])
                try:
                    proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, timeout=6)
                    if proc.returncode == 0 and proc.stdout.strip():
                        found_pr_info = json.loads(proc.stdout)
                        if not repo_hint and r:
                            repo_hint = r
                        break
                except Exception:
                    pass

            if not found_pr_info:
                continue

            pr_state = found_pr_info.get("state", "").upper()
            pr_url = found_pr_info.get("url", f"#{pr_number}")
            title = meta.get("title", fname[:-3])

            if pr_state in ("MERGED", "CLOSED"):
                action_text = "merged" if pr_state == "MERGED" else "closed"
                evo_note = f"Auto-synced: PR #{pr_number} was {action_text} on GitHub ({pr_url})"

                reconciled_item = {
                    "task_id": fname[:-3],
                    "file": fpath,
                    "title": title,
                    "status": "done",
                    "pr_number": pr_number,
                    "pr_state": pr_state,
                    "pr_url": pr_url,
                    "repo": repo_hint,
                    "reason": evo_note,
                }
                reconciled.append(reconciled_item)

                if not dry_run:
                    meta["status"] = "done"
                    meta["updated_at"] = now.isoformat()
                    if repo_hint and not meta.get("github_pr"):
                        meta["github_pr"] = pr_url

                    evo_header = "## 🧠 Session Lineage & Deciding Factors"
                    evo_entry = f"- **{now.strftime('%Y-%m-%d %H:%M')}:** ✅ {evo_note}."

                    if evo_header in body:
                        parts = body.split(evo_header, 1)
                        body = parts[0] + evo_header + "\n\n" + evo_entry + "\n" + parts[1].lstrip("\r\n")
                    else:
                        body = body.rstrip() + f"\n\n{evo_header}\n\n{evo_entry}\n"

                    new_content = dump_frontmatter(meta, body)
                    with open(fpath, "w", encoding="utf-8") as out_f:
                        out_f.write(new_content)

                    session_file = meta.get("session_file")
                    if session_file and os.path.isfile(session_file):
                        sync_task_to_session_file(
                            session_file,
                            fpath,
                            meta,
                            evolution_summary=evo_note,
                        )
        except Exception:
            continue

    return reconciled


def sync_workstate_from_tasks(root_dir: str) -> bool:
    """
    Project and synchronize workforces/workstate.md's ## Active Tasks and ## Completed Tasks
    directly from workforces/tasks/*.md to maintain a single source of truth.
    """
    tasks_dir = os.path.join(root_dir, "workforces", "tasks")
    if not os.path.isdir(tasks_dir):
        tasks_dir = os.path.join(root_dir, "tasks")
        if not os.path.isdir(tasks_dir):
            return False

    if os.path.isdir(os.path.join(root_dir, "workforces")):
        workstate_path = os.path.join(root_dir, "workforces", "workstate.md")
    else:
        workstate_path = os.path.join(root_dir, "workstate.md")

    active_tasks: List[Dict[str, Any]] = []
    completed_tasks: List[Dict[str, Any]] = []

    priority_weight = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    status_weight = {"in_progress": 0, "blocked": 1, "todo": 2}

    for fname in sorted(os.listdir(tasks_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(tasks_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                meta, _ = parse_frontmatter(f.read())

            status = meta.get("status", "todo")
            priority = meta.get("priority", meta.get("severity", "P2"))
            title = meta.get("title", fname[:-3])
            assignee = meta.get("assignee", "@user") or "@user"
            updated = meta.get("updated_at", meta.get("reported_at", ""))
            if updated and "T" in updated:
                updated = updated.split("T")[0]

            pr_ref = meta.get("github_pr") or meta.get("pr") or meta.get("github_issue") or meta.get("issue") or "—"
            if isinstance(pr_ref, str) and pr_ref.startswith("http"):
                pr_num = re.search(r"/(?:pull|issues)/(\d+)", pr_ref)
                pr_label = f"PR #{pr_num.group(1)}" if pr_num else "Link"
                issue_pr_cell = f"[{pr_label}]({pr_ref})"
            elif pr_ref and pr_ref != "—":
                issue_pr_cell = f"#{pr_ref}"
            else:
                issue_pr_cell = "—"

            note = meta.get("suggested_action", "") or meta.get("type", "task")
            if len(note) > 60:
                note = note[:57] + "..."

            task_dict = {
                "id": fname[:-3],
                "file": fpath,
                "title": title,
                "priority": priority,
                "status": status,
                "issue_pr": issue_pr_cell,
                "assignee": assignee,
                "updated": updated or datetime.datetime.now().strftime("%Y-%m-%d"),
                "note": note,
            }

            if status in ("in_progress", "blocked", "todo"):
                active_tasks.append(task_dict)
            elif status in ("done", "dropped", "completed"):
                completed_tasks.append(task_dict)
        except OSError:
            continue

    active_tasks.sort(
        key=lambda x: (
            status_weight.get(x["status"], 9),
            priority_weight.get(x["priority"], 9),
            x["updated"],
        )
    )
    completed_tasks.sort(key=lambda x: x["updated"], reverse=True)

    active_table_lines = [
        "## Active Tasks",
        "| # | Task | Priority | Status | Issue / PR | Assignee | Updated | Notes |",
        "|---|------|----------|--------|------------|----------|---------|-------|",
    ]
    if active_tasks:
        for idx, t in enumerate(active_tasks, 1):
            rel_file = os.path.relpath(t["file"], root_dir)
            task_link = f"[{t['title']}]({rel_file})"
            active_table_lines.append(
                f"| {idx} | {task_link} | {t['priority']} | {t['status']} | {t['issue_pr']} | {t['assignee']} | {t['updated']} | {t['note']} |"
            )
    else:
        active_table_lines.append("| — | _No active tasks in progress or todo_ | — | — | — | — | — | — |")
    active_table_block = "\n".join(active_table_lines)

    completed_table_lines = [
        "## Completed Tasks (Recent)",
        "| Task | Priority | Status | Issue / PR | Completed |",
        "|------|----------|--------|------------|-----------|",
    ]
    if completed_tasks:
        for t in completed_tasks[:10]:
            rel_file = os.path.relpath(t["file"], root_dir)
            task_link = f"[{t['title']}]({rel_file})"
            completed_table_lines.append(
                f"| {task_link} | {t['priority']} | {t['status']} | {t['issue_pr']} | {t['updated']} |"
            )
    else:
        completed_table_lines.append("| _No completed tasks yet_ | — | — | — | — |")
    completed_table_block = "\n".join(completed_table_lines)

    if os.path.isfile(workstate_path):
        try:
            with open(workstate_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            content = "# Work State\n\n"
    else:
        content = "# Work State\n\n## Configuration\n| Setting | Value |\n|---------|-------|\n| GitHub Usernames | @me |\n| Ignored Repos | |\n| Goals Directory | workforces/goals/ |\n\n"

    if re.search(r"## Active Tasks\s*\n.*?(?=\n##|\Z)", content, re.DOTALL):
        content = re.sub(
            r"## Active Tasks\s*\n.*?(?=\n##|\Z)",
            active_table_block + "\n",
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + active_table_block + "\n"

    if re.search(r"## Completed Tasks.*?\n.*?(?=\n##|\Z)", content, re.DOTALL):
        content = re.sub(
            r"## Completed Tasks.*?\n.*?(?=\n##|\Z)",
            completed_table_block + "\n",
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + "\n\n" + completed_table_block + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(workstate_path)), exist_ok=True)
    with open(workstate_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    return True


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
    reconcile: bool = True,
    sync_workstate: bool = True,
) -> Dict[str, Any]:
    """Aggregate all personal status and follow-up data across sources."""
    root_dir = os.path.abspath(root_dir)
    now = datetime.datetime.now()
    tracked_repos = get_tracked_repos(root_dir)

    reconciled_items: List[Dict[str, Any]] = []
    if check_github and reconcile:
        reconciled_items = reconcile_github_tasks(root_dir, tracked_repos=tracked_repos)

    if sync_workstate:
        sync_workstate_from_tasks(root_dir)

    data = {
        "timestamp": now.isoformat(),
        "root_dir": root_dir,
        "user": user,
        "tracked_repos": tracked_repos,
        "git": get_git_status(root_dir),
        "tasks": get_tasks_summary(root_dir, assignee=user if user != "@me" else None),
        "workstate": get_workstate_summary(root_dir),
        "session_context": get_session_context_summary(root_dir),
        "hypotheses": get_running_hypotheses(root_dir),
        "jules_sessions": get_jules_sessions(root_dir),
        "reconciled_tasks": reconciled_items,
        "github": get_github_summary(root_dir, user=user, tracked_repos=tracked_repos) if check_github else {"available": False},
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
    reconciled = data.get("reconciled_tasks", [])
    tracked_repos = data.get("tracked_repos", [])

    lines = []
    lines.append(f"## 👤 Personal Sync & Follow-Up Radar (`/sync --me`) — {timestamp}")
    if tracked_repos:
        lines.append(f"> **Scoped Repositories:** `{', '.join(tracked_repos)}`")
    lines.append("")

    # Section 0: Reconciled GitHub Tasks (if any)
    if reconciled:
        lines.append("### 🔄 Remote GitHub State Reconciliation")
        for r in reconciled:
            lines.append(f"- ✅ **Auto-synced to Done:** [{r['title']}]({r['file']}) — *{r['reason']}*")
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
            repo_prefix = f"[`{pr['repo']}`] " if pr.get("repo") else ""
            lines.append(f"  - {repo_prefix}[PR #{pr['number']}: {pr['title']}]({pr['url']}) by `@{author_name}`")
        has_action_items = True

    if gh.get("available") and gh.get("assigned_issues"):
        lines.append("- **📋 Assigned GitHub Issues:**")
        for issue in gh["assigned_issues"][:5]:
            repo_prefix = f"[`{issue['repo']}`] " if issue.get("repo") else ""
            lines.append(f"  - {repo_prefix}[Issue #{issue['number']}: {issue['title']}]({issue['url']})")
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
            repo_prefix = f"[`{pr['repo']}`] " if pr.get("repo") else ""
            lines.append(f"  - {repo_prefix}[PR #{pr['number']}: {pr['title']}]({pr['url']})")
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
    parser.add_argument("--no-reconcile", action="store_true", help="Skip automatic GitHub PR/issue reconciliation")
    parser.add_argument("--no-sync-workstate", action="store_true", help="Skip automatic workstate.md synchronization")

    args = parser.parse_args()

    data = generate_personal_sync_data(
        root_dir=args.root,
        user=args.assignee,
        check_github=not args.no_github,
        reconcile=not args.no_reconcile,
        sync_workstate=not args.no_sync_workstate,
    )

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_markdown_report(data))


if __name__ == "__main__":
    main()
