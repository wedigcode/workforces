#!/usr/bin/env python3
"""
Workforce Command Canvas - Local Backend Server
Zero external dependencies (Standard Library: http.server, json, pathlib, urllib, subprocess).

Exposes:
- GET  /api/state               -> Aggregates tasks, workstate, hypotheses, goals, and dependency edges
- GET  /api/impact              -> Traces code symbol / file blast radius (callers, callees)
- POST /api/task/update         -> Updates task frontmatter (status, priority, note) & resyncs workstate
- POST /api/task/connect        -> Connects dependency (blocked_by) between tasks
- POST /api/task/order          -> Persists human-arranged canvas node order
- GET  /                        -> Serves the dark dot-grid interactive canvas UI
"""

import argparse
import datetime
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add skills/task-tracker and skills/code-graph to sys.path for direct utility composition
CURRENT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = CURRENT_DIR.parent.parent
sys.path.insert(0, str(SKILLS_DIR / "task-tracker" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "code-graph" / "scripts"))

try:
    from personal_sync import (
        get_workstate_summary,
        get_tasks_summary,
        get_running_hypotheses,
        get_session_context_summary,
        sync_workstate_from_tasks,
    )
except ImportError:
    # Safe fallbacks if running in standalone test environment
    get_workstate_summary = None
    get_tasks_summary = None
    get_running_hypotheses = None
    get_session_context_summary = None
    sync_workstate_from_tasks = None

try:
    from pre_impact_analyzer import load_code_graph, resolve_target_dir
except ImportError:
    load_code_graph = None
    resolve_target_dir = None


def parse_yaml_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Extract YAML frontmatter and body from a markdown file with zero pyyaml dependency."""
    metadata: Dict[str, Any] = {}
    if not file_path.exists():
        return metadata

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as err:
        sys.stderr.write(f"Error reading {file_path}: {err}\n")
        return metadata

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return metadata

    raw_yaml, body = match.group(1), match.group(2)
    metadata["_body"] = body.strip()

    current_list_key = None
    for line in raw_yaml.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # List item continuation
        if re.match(r"^\s+-\s+(.*)$", line) and current_list_key:
            item_val = re.match(r"^\s+-\s+(.*)$", line).group(1).strip().strip('"\'')
            if isinstance(metadata.get(current_list_key), list):
                metadata[current_list_key].append(item_val)
            continue

        # Key-value pair
        kv_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv_match:
            key, val = kv_match.group(1).strip(), kv_match.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                # Inline list
                raw_items = val[1:-1].split(",")
                metadata[key] = [i.strip().strip('"\'') for i in raw_items if i.strip()]
                current_list_key = None
            elif not val:
                metadata[key] = []
                current_list_key = key
            else:
                clean_val = val.strip('"\'')
                metadata[key] = clean_val
                current_list_key = None

    return metadata


def get_all_tasks(root_dir: Path) -> List[Dict[str, Any]]:
    """Scan workforces/tasks/*.md and extract all task nodes with full metadata."""
    tasks = []
    tasks_dir = root_dir / "workforces" / "tasks"
    if not tasks_dir.exists():
        return tasks

    for task_file in sorted(tasks_dir.glob("*.md")):
        if task_file.name == ".gitkeep":
            continue
        meta = parse_yaml_frontmatter(task_file)
        if not meta:
            continue

        task_id = meta.get("id") or task_file.stem
        task_type = (meta.get("type") or "other").lower()

        # Categorize team based on type/tags
        team = "dev"
        if task_type in ("marketing", "growth", "seo", "acquisition"):
            team = "marketing"
        elif task_type in ("social", "community", "reply", "triage"):
            team = "social"
        elif task_type in ("design", "ui", "ux", "visual", "brand"):
            team = "design"
        elif task_type in ("product", "strategy", "advisor", "jtbd", "goal"):
            team = "strategy"
        elif task_type in ("compliance", "security", "legal"):
            team = "compliance"
        elif task_type in ("ops", "infra", "deploy"):
            team = "ops"

        task_node = {
            "id": task_id,
            "file": str(task_file.relative_to(root_dir)),
            "title": meta.get("title") or task_file.stem,
            "type": task_type,
            "team": team,
            "priority": (meta.get("priority") or "P2").upper(),
            "status": (meta.get("status") or "todo").lower(),
            "reporter": meta.get("reporter") or "@human",
            "assignee": meta.get("assignee") or "",
            "session_id": meta.get("session_id") or "",
            "session_file": meta.get("session_file") or meta.get("origin_session") or "",
            "github_issue": meta.get("github_issue") or "",
            "github_pr": meta.get("github_pr") or "",
            "blocked_by": meta.get("blocked_by") or [],
            "delegated_to": meta.get("delegated_to") or "",
            "deciding_factors": meta.get("deciding_factors") or [],
            "body": meta.get("_body") or "",
            "updated_at": meta.get("updated_at") or meta.get("created_at") or "",
            "linked_commits": [],
            "linked_docs": [],
            "linked_symbols": [],
        }
        tasks.append(task_node)
    return tasks


def get_recent_commits(root_dir: Path, limit: int = 60) -> List[Dict[str, Any]]:
    """Extract recent git commits for task correlation."""
    try:
        output = subprocess.check_output(
            ["git", "log", f"-n", str(limit), "--format=%h|%an|%ad|%s", "--date=short"],
            cwd=str(root_dir),
            text=True,
            stderr=subprocess.DEVNULL
        )
        commits = []
        for line in output.strip().split("\n"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })
        return commits
    except Exception:
        return []


def link_task_relationships(tasks: List[Dict[str, Any]], available_symbols: List[Dict[str, Any]], commits: List[Dict[str, Any]]) -> None:
    """Detect and attach linked commits, documents, and code symbols to each task."""
    stop_words = {'and', 'the', 'for', 'with', 'task', 'model', 'into', 'from', 'that', 'this', 'workflow', 'engine'}
    for t in tasks:
        title = t.get("title", "")
        body = t.get("body", "")
        combined_text = f"{title} {body}".lower()

        # 1. Correlate Commits
        matched_commits = []
        words = [w.lower() for w in re.findall(r'[a-zA-Z0-9_-]{4,}', title) if w.lower() not in stop_words]
        for c in commits:
            msg_lower = c["message"].lower()
            matches = [w for w in words if w in msg_lower]
            if len(matches) >= 2 or (len(words) <= 2 and len(matches) >= 1):
                matched_commits.append(c)
        t["linked_commits"] = matched_commits[:4]

        # 2. Extract Document & File References
        doc_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
        linked_docs = []
        for text, url in doc_matches:
            if "session-context" in url:
                continue
            linked_docs.append({"title": text.strip(), "url": url.strip()})
        t["linked_docs"] = linked_docs[:6]

        # 3. Detect AST Code Symbols (excluding test files and fixtures)
        matched_symbols = []
        for s in available_symbols:
            name = s.get("name", "")
            file_path = s.get("file", "")
            if name in ("setUp", "tearDown") or name.startswith("test_"):
                continue
            if "tests/" in file_path or "/test_" in file_path:
                continue
            if len(name) >= 4 and name.lower() in combined_text:
                matched_symbols.append(s)
            elif file_path:
                base_name = Path(file_path).stem.lower()
                if len(base_name) >= 4 and base_name in combined_text:
                    matched_symbols.append(s)
        seen_syms = set()
        deduped_syms = []
        for s in matched_symbols:
            if s["name"] not in seen_syms:
                seen_syms.add(s["name"])
                deduped_syms.append(s)
        t["linked_symbols"] = deduped_syms[:6]


def get_all_hypotheses(root_dir: Path) -> List[Dict[str, Any]]:
    """Scan workforces/hypotheses/*.md and extract all hypothesis nodes."""
    hypotheses = []
    hyp_dir = root_dir / "workforces" / "hypotheses"
    if not hyp_dir.exists():
        return hypotheses

    for hyp_file in sorted(hyp_dir.glob("*.md")):
        if hyp_file.name == ".gitkeep":
            continue
        meta = parse_yaml_frontmatter(hyp_file)
        if not meta:
            continue
        hyp_node = {
            "id": meta.get("id") or hyp_file.stem,
            "file": str(hyp_file.relative_to(root_dir)),
            "title": meta.get("title") or hyp_file.stem,
            "status": (meta.get("status") or "testing").lower(),
            "owner": meta.get("owner") or "@growth",
            "leading_kpi": meta.get("leading_kpi") or "",
            "kill_threshold": meta.get("kill_threshold") or "",
            "body": meta.get("_body") or "",
        }
        hypotheses.append(hyp_node)
    return hypotheses


def get_all_sessions(root_dir: Path) -> List[Dict[str, Any]]:
    """Scan workforces/session-context/*.md and extract session notes."""
    sessions = []
    sess_dir = root_dir / "workforces" / "session-context"
    if not sess_dir.exists():
        sess_dir = root_dir / "session-context"
    if not sess_dir.exists():
        return sessions

    for sess_file in sorted(sess_dir.glob("*.md")):
        if sess_file.name == ".gitkeep" or sess_file.name.startswith("."):
            continue
        meta = parse_yaml_frontmatter(sess_file)
        if not meta:
            continue

        session_id = str(meta.get("session_id") or meta.get("sequence") or sess_file.stem.split("_")[0])
        topic = meta.get("topic") or sess_file.stem
        parent = meta.get("parent_session_id")
        active_files = meta.get("active_files") or []
        tracked_tasks = meta.get("tracked_tasks") or []
        tags = meta.get("tags") or []
        created_at = meta.get("created_at") or ""

        sessions.append({
            "id": session_id,
            "file": str(sess_file.relative_to(root_dir)),
            "title": topic,
            "topic": topic,
            "parent_session_id": str(parent) if parent else None,
            "active_files": active_files,
            "tracked_tasks": tracked_tasks,
            "tags": tags,
            "created_at": created_at,
            "body": meta.get("_body") or "",
        })
    return sessions


def get_standup_data(root_dir: Path, tasks: List[Dict[str, Any]], inbox_items: List[Dict[str, Any]], sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compile multi-source standup and executive productivity intelligence."""
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
    
    in_progress = [t for t in tasks if t.get("status") == "in_progress"]
    in_progress.sort(key=lambda t: priority_order.get(str(t.get("priority", "p2")).lower(), 2))
    
    todo = [t for t in tasks if t.get("status") == "todo"]
    todo.sort(key=lambda t: priority_order.get(str(t.get("priority", "p2")).lower(), 2))
    
    blocked = [t for t in tasks if t.get("status") == "blocked" or t.get("blocked_by")]
    done = [t for t in tasks if t.get("status") == "done"]
    done.sort(key=lambda t: str(t.get("updated_at") or ""), reverse=True)

    # 1. "The One Thing" (Today's top P0/P1 focus commitment)
    one_thing = None
    if in_progress:
        one_thing = in_progress[0]
    elif todo:
        one_thing = todo[0]
    elif done:
        one_thing = done[0]

    # 2. Needs Attention List
    needs_attention = []
    for b in blocked:
        blocker_names = b.get("blocked_by", [])
        needs_attention.append({
            "type": "blocker",
            "id": b["id"],
            "title": b["title"],
            "priority": b.get("priority", "P1"),
            "reason": f"Blocked by: {', '.join(blocker_names)}" if blocker_names else "Task marked as blocked",
            "task": b,
        })

    for it in inbox_items:
        if it.get("_folder") == "human_review" or it.get("requires_human"):
            needs_attention.append({
                "type": "inbox_review",
                "id": it.get("id"),
                "title": it.get("title", "Captured Item"),
                "priority": "P1",
                "reason": "Extension capture awaiting human decision or approval",
                "item": it,
            })

    # Read pending issues from workforces/issues/inbox/
    issues_dir = root_dir / "workforces" / "issues" / "inbox"
    issues = []
    if issues_dir.exists():
        for f in sorted(issues_dir.glob("*.md"), reverse=True):
            meta = parse_yaml_frontmatter(f)
            iss_title = meta.get("title") or f.stem.replace("-", " ").title()
            iss_id = meta.get("id") or f.stem
            iss_priority = meta.get("priority") or "P2"
            issues.append({
                "id": iss_id,
                "title": iss_title,
                "priority": iss_priority,
                "file": str(f.relative_to(root_dir)),
                "date": meta.get("reported_at") or meta.get("created_at") or "",
            })
            if len(needs_attention) < 8:
                needs_attention.append({
                    "type": "issue",
                    "id": iss_id,
                    "title": iss_title,
                    "priority": iss_priority,
                    "reason": "Unresolved backlog bug / tech debt in inbox",
                    "file": str(f.relative_to(root_dir)),
                })

    # 3. 24h Wins
    wins = []
    for d in done[:8]:
        wins.append({
            "id": d["id"],
            "title": d["title"],
            "priority": d.get("priority", "P1"),
            "completed_at": str(d.get("updated_at") or "")[:10],
            "file": d.get("file", ""),
            "linked_commits": d.get("linked_commits", []),
        })

    # 4. Installed Teams
    installed_teams = []
    workrules_file = root_dir / "workforces" / "workrules.md"
    if workrules_file.exists():
        try:
            w_meta = parse_yaml_frontmatter(workrules_file)
            installed_teams = w_meta.get("installed_teams") or []
        except Exception:
            pass

    # 5. Git Status
    git_info = {"branch": "main", "clean": True, "modified_count": 0, "recent_commits": []}
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(root_dir), text=True, stderr=subprocess.DEVNULL).strip()
        status_s = subprocess.check_output(["git", "status", "-s"], cwd=str(root_dir), text=True, stderr=subprocess.DEVNULL).strip()
        modified_count = len(status_s.splitlines()) if status_s else 0
        git_info["branch"] = branch or "main"
        git_info["clean"] = modified_count == 0
        git_info["modified_count"] = modified_count
    except Exception:
        pass

    # 6. Latest Session Context
    latest_session = {}
    if sessions:
        sorted_sessions = sorted(sessions, key=lambda s: str(s.get("id", "")), reverse=True)
        latest_session = sorted_sessions[0]
        sess_path = root_dir / latest_session.get("file", "")
        if sess_path.exists():
            sess_meta = parse_yaml_frontmatter(sess_path)
            latest_session["decisions"] = sess_meta.get("decisions") or []
            latest_session["participants"] = sess_meta.get("participants") or []
            latest_session["updated_at"] = sess_meta.get("updated_at") or ""

    # 7. Workstate markdown content
    workstate_md = ""
    ws_path = root_dir / "workforces" / "workstate.md"
    if ws_path.exists():
        try:
            workstate_md = ws_path.read_text(encoding="utf-8")
        except Exception:
            pass

    return {
        "one_thing": one_thing,
        "needs_attention": needs_attention,
        "wins_24h": wins,
        "in_progress": in_progress,
        "todo": todo,
        "blocked": blocked,
        "done": done,
        "issues": issues,
        "installed_teams": installed_teams,
        "git": git_info,
        "latest_session": latest_session,
        "workstate_markdown": workstate_md,
    }


def create_task_file(root_dir: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new task in workforces/tasks/ and synchronize workstate."""
    now = datetime.datetime.now()
    now_ts = now.strftime("%Y%m%d-%H%M%S")
    title = data.get("title", "").strip() or "Untitled Task"
    clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '-', title.lower()).strip('-')[:40] or "task"
    filename = f"{now_ts}-{clean_slug}.md"
    task_path = root_dir / "workforces" / "tasks" / filename
    task_path.parent.mkdir(parents=True, exist_ok=True)
    
    task_type = data.get("type", "feature").strip()
    priority = data.get("priority", "P1").strip().upper()
    reporter = data.get("reporter", "@human").strip()
    assignee = data.get("assignee", "").strip()
    suggested_action = data.get("suggested_action", "").strip()
    description = data.get("description", "").strip() or data.get("body", "").strip()
    
    body_text = f"""# {title}

**Type:** `{task_type}` | **Priority:** `{priority}` | **Status:** `todo` | **Reporter:** `{reporter}`  
**Reported:** {now.strftime("%Y-%m-%d %H:%M")} | **Updated:** {now.strftime("%Y-%m-%d %H:%M")}

## Description

{description or "No description provided."}

## Suggested Action

{suggested_action or "Review requirements and begin implementation."}

## 🧠 Session Lineage & Deciding Factors

- **{now.strftime("%Y-%m-%d %H:%M")}:** Created task from Workforce Studio Cockpit
"""
    frontmatter = f"""---
title: "{title}"
type: "{task_type}"
priority: "{priority}"
status: "todo"
reporter: "{reporter}"
assignee: {f'"{assignee}"' if assignee else '~'}
reported_at: "{now.isoformat()}"
updated_at: "{now.isoformat()}"
file: "{str(task_path.relative_to(root_dir))}"
session_id: ""
session_file: ""
recommended_tools: []
delegated_to: ~
github_labels: []
github_issue: ~
github_pr: ~
---

{body_text}
"""
    task_path.write_text(frontmatter, encoding="utf-8")
    
    if sync_workstate_from_tasks:
        try:
            sync_workstate_from_tasks(str(root_dir))
        except Exception:
            pass
            
    return {
        "id": task_path.stem,
        "file": str(task_path.relative_to(root_dir)),
        "title": title,
        "type": task_type,
        "priority": priority,
        "status": "todo",
        "reporter": reporter,
        "assignee": assignee,
        "body": body_text
    }


def resolve_inbox_item(root_dir: Path, item_id: str, action: str, priority: str = "P1", task_type: str = "feature") -> Dict[str, Any]:
    """Approve or dismiss an inbox item."""
    inbox_base = root_dir / "workforces" / "inbox"
    target_file = None
    for folder in ("human_review", "pending", "processed"):
        d = inbox_base / folder
        if d.exists():
            for f in list(d.glob(f"{item_id}.*")) + list(d.glob(f"*{item_id}*")):
                target_file = f
                break
        if target_file:
            break

    if not target_file or not target_file.exists():
        raise FileNotFoundError(f"Inbox item {item_id} not found")

    processed_dir = inbox_base / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    if action == "approve":
        if target_file.suffix == ".json":
            raw_data = json.loads(target_file.read_text(encoding="utf-8"))
            title = raw_data.get("title", "Inbox Task")
            content = raw_data.get("content") or raw_data.get("selection") or ""
            source_url = raw_data.get("source_url", "")
            raw_data["status"] = "approved"
        else:
            meta = parse_yaml_frontmatter(target_file)
            title = meta.get("title") or target_file.stem.replace("-", " ").title()
            content = meta.get("_body") or ""
            source_url = meta.get("source_url", "")
            raw_data = {"id": item_id, "title": title, "content": content, "status": "approved"}

        task_res = create_task_file(root_dir, {
            "title": title,
            "priority": priority,
            "type": task_type,
            "description": content,
            "suggested_action": f"Review research/capture from {source_url}" if source_url else "Follow up on approved inbox item.",
            "reporter": "@inbox"
        })

        raw_data["task_id"] = task_res["id"]
        raw_data["task_file"] = task_res["file"]
        raw_data["resolved_at"] = datetime.datetime.now().isoformat()
        dest = processed_dir / f"{target_file.stem}.json"
        dest.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
        if target_file != dest:
            target_file.unlink(missing_ok=True)
        return {"action": "approved", "task": task_res}
    else:
        if target_file.suffix == ".json":
            raw_data = json.loads(target_file.read_text(encoding="utf-8"))
            raw_data["status"] = "dismissed"
            raw_data["dismissed_at"] = datetime.datetime.now().isoformat()
            dest = processed_dir / f"{target_file.stem}.json"
            dest.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
        else:
            dest = processed_dir / target_file.name
            shutil.move(str(target_file), str(dest))
        if target_file != dest:
            target_file.unlink(missing_ok=True)
        return {"action": "dismissed", "item_id": item_id}


def get_commit_details(root_dir: Path, commit_hash: Optional[str]) -> Dict[str, Any]:
    """Inspect a git commit, touched files, and AST symbols."""
    if not commit_hash:
        return {"error": "Missing commit hash"}
    try:
        out = subprocess.check_output(
            ["git", "show", "--name-only", "--format=%h|%an|%ad|%s", commit_hash],
            cwd=str(root_dir),
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = out.strip().split("\n")
        header = lines[0].split("|", 3)
        files = [l.strip() for l in lines[1:] if l.strip()]

        commit_info = {
            "hash": header[0] if len(header) > 0 else commit_hash,
            "author": header[1] if len(header) > 1 else "Unknown",
            "date": header[2] if len(header) > 2 else "",
            "message": header[3] if len(header) > 3 else "",
            "files": files,
            "symbols": [],
        }

        # Find symbols in touched files from code-graph.json
        code_graph_file = root_dir / "workforces" / "code-graph.json"
        if not code_graph_file.exists():
            code_graph_file = root_dir / "code-graph.json"
        if code_graph_file.exists():
            try:
                cg_data = json.loads(code_graph_file.read_text(encoding="utf-8"))
                touched_set = set(files)
                for s in cg_data.get("symbols", []):
                    s_file = s.get("file", "")
                    if s_file in touched_set or any(f.endswith(s_file) or s_file.endswith(f) for f in files):
                        commit_info["symbols"].append({
                            "name": s["name"],
                            "file": s_file,
                            "line": s.get("line", 0),
                            "kind": s.get("kind", "function")
                        })
            except Exception:
                pass

        return commit_info
    except Exception as e:
        return {"error": str(e), "hash": commit_hash}


def get_all_goals(root_dir: Path) -> List[Dict[str, Any]]:
    """Scan workforces/goals/*.md and extract macro business goals."""
    goals = []
    goals_dir = root_dir / "workforces" / "goals"
    if not goals_dir.exists():
        return goals

    for goal_file in sorted(goals_dir.glob("*.md")):
        if goal_file.name == ".gitkeep":
            continue
        meta = parse_yaml_frontmatter(goal_file)
        goals.append({
            "id": meta.get("id") or goal_file.stem,
            "file": str(goal_file.relative_to(root_dir)),
            "title": meta.get("title") or goal_file.stem,
            "horizon": meta.get("horizon") or "current",
            "status": meta.get("status") or "active",
            "body": meta.get("_body") or "",
        })
    return goals


def load_multi_repo_symbols(root_dir: Path) -> List[Dict[str, Any]]:
    """
    Load AST symbols from primary repository, internal projects, and internal sibling repos.
    Enables cross-repository blast radius analysis for organizations controlling multiple repos.
    """
    symbols = []
    seen = set()

    def add_from_file(cg_file: Path, repo_name: str, prefix_path: bool = False):
        if not cg_file.exists():
            return
        try:
            data = json.loads(cg_file.read_text(encoding="utf-8"))
            for s in data.get("symbols", []):
                s_copy = dict(s)
                s_copy["repo"] = repo_name
                if prefix_path:
                    s_copy["file"] = f"{repo_name}/{s.get('file', '')}"
                key = (repo_name, s_copy.get("name"), s_copy.get("file"))
                if key not in seen:
                    seen.add(key)
                    symbols.append(s_copy)
        except Exception:
            pass

    # 1. Primary repository
    for p in [root_dir / "workforces" / "code-graph.json", root_dir / "code-graph.json"]:
        if p.exists():
            add_from_file(p, root_dir.name, prefix_path=False)
            break

    # 2. Projects subfolder if present
    proj_dir = root_dir / "projects"
    if proj_dir.exists():
        for p_sub in proj_dir.iterdir():
            if p_sub.is_dir() and not p_sub.name.startswith("."):
                for p in [p_sub / "workforces" / "code-graph.json", p_sub / "code-graph.json"]:
                    if p.exists():
                        add_from_file(p, p_sub.name, prefix_path=True)
                        break

    # 3. Sibling repositories under parent directory
    if root_dir.parent.exists():
        for sib in root_dir.parent.iterdir():
            if sib.is_dir() and sib.name != root_dir.name and not sib.name.startswith("."):
                for p in [sib / "workforces" / "code-graph.json", sib / "code-graph.json"]:
                    if p.exists():
                        add_from_file(p, sib.name, prefix_path=True)
                        break

    return symbols


def get_code_blast_radius(root_dir: Path, symbol_name: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract upstream internal callees and downstream blast radius callers for a given symbol.
    Excludes external standard library built-ins to maintain focused internal dependency maps.
    Aware of internal multi-repo symbols across repositories we control.
    """
    symbols = load_multi_repo_symbols(root_dir)

    # Build symbol map prioritizing local repo in case of identical names
    symbol_map: Dict[str, Dict[str, Any]] = {}
    for s in symbols:
        name = s.get("name")
        if name and (name not in symbol_map or s.get("repo") == root_dir.name):
            symbol_map[name] = s

    target_symbol = None
    if symbol_name and symbol_name in symbol_map:
        target_symbol = symbol_map[symbol_name]
    elif file_path:
        for s in symbols:
            if s.get("file") == file_path or file_path.endswith(s.get("file", "---")):
                target_symbol = s
                break

    if not target_symbol:
        return {
            "found": False,
            "target": None,
            "upstream_callees": [],
            "downstream_callers": [],
            "affected_files": [],
        }

    target_name = target_symbol.get("name")
    target_file = target_symbol.get("file")
    target_repo = target_symbol.get("repo", root_dir.name)

    # Upstream: ONLY internal methods called BY target_symbol (filtering out external/stdlib noise)
    upstream_callees = []
    seen_callees = set()
    calls = target_symbol.get("calls", [])
    for call_name in calls:
        if call_name in symbol_map:
            callee = symbol_map[call_name]
            callee_key = (callee.get("name"), callee.get("file"))
            if callee_key not in seen_callees:
                seen_callees.add(callee_key)
                upstream_callees.append(callee)
        # Note: External standard library and built-ins (abspath, append, get, etc.)
        # are intentionally omitted to focus strictly on internal architectural dependencies.

    # Downstream: other internal functions that CALL target_name (Blast Radius)
    downstream_callers = []
    seen_callers = set()
    affected_files = set()
    for s in symbols:
        if s.get("name") == target_name and s.get("file") == target_file and s.get("repo") == target_repo:
            continue
        if target_name in s.get("calls", []):
            caller_key = (s.get("name"), s.get("file"))
            if caller_key not in seen_callers:
                seen_callers.add(caller_key)
                downstream_callers.append(s)
                if s.get("file"):
                    affected_files.add(s.get("file"))

    return {
        "found": True,
        "target": target_symbol,
        "upstream_callees": upstream_callees,
        "downstream_callers": downstream_callers,
        "affected_files": sorted(list(affected_files)),
    }


def update_task_file(root_dir: Path, relative_file: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely update a task's frontmatter fields (status, priority, blocked_by, evolution notes).
    Automatically resynchronizes workforces/workstate.md.
    """
    task_path = root_dir / relative_file.lstrip("/")
    if not task_path.exists():
        if (root_dir / "workforces" / relative_file.lstrip("/")).exists():
            task_path = root_dir / "workforces" / relative_file.lstrip("/")
        elif (root_dir / "workforces" / "tasks" / relative_file.lstrip("/")).exists():
            task_path = root_dir / "workforces" / "tasks" / relative_file.lstrip("/")
        else:
            # Look up task in tasks directory by filename or stem
            tasks_dir = root_dir / "workforces" / "tasks"
            found_path = None
            if tasks_dir.exists():
                for tf in tasks_dir.glob("*.md"):
                    if tf.name == relative_file or tf.stem == relative_file or tf.name == f"{relative_file}.md":
                        found_path = tf
                        break
            if found_path:
                task_path = found_path
            else:
                raise FileNotFoundError(f"Task file not found: {relative_file}")

    content = task_path.read_text(encoding="utf-8", errors="ignore")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Task file does not have valid YAML frontmatter: {relative_file}")

    raw_yaml, body = match.group(1), match.group(2)
    yaml_lines = raw_yaml.splitlines()

    now_iso = datetime.datetime.now().isoformat()

    # Track if updated_at was modified
    has_updated_at = False

    new_yaml_lines = []
    for line in yaml_lines:
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1).strip()
            if key in updates:
                new_val = updates[key]
                if isinstance(new_val, list):
                    clean_items = ", ".join(f'"{i}"' for i in new_val)
                    new_yaml_lines.append(f"{key}: [{clean_items}]")
                else:
                    new_yaml_lines.append(f'{key}: "{new_val}"')
                del updates[key]
                continue
            elif key == "updated_at":
                new_yaml_lines.append(f'updated_at: "{now_iso}"')
                has_updated_at = True
                continue
        new_yaml_lines.append(line)

    # Append any remaining new keys
    for key, val in updates.items():
        if key == "evolution_note":
            continue
        if isinstance(val, list):
            clean_items = ", ".join(f'"{i}"' for i in val)
            new_yaml_lines.append(f"{key}: [{clean_items}]")
        else:
            new_yaml_lines.append(f'{key}: "{val}"')

    if not has_updated_at:
        new_yaml_lines.append(f'updated_at: "{now_iso}"')

    # Handle evolution note append
    evolution_note = updates.get("evolution_note")
    if evolution_note:
        evolution_block = f"\n\n### 📝 Evolution Note ({now_iso[:16]})\n- {evolution_note.strip()}"
        body = body.rstrip() + evolution_block + "\n"

    new_content = "---\n" + "\n".join(new_yaml_lines) + "\n---\n" + body
    task_path.write_text(new_content, encoding="utf-8")

    # Resync workstate.md if personal_sync is available
    if sync_workstate_from_tasks:
        try:
            sync_workstate_from_tasks(str(root_dir))
        except Exception as sync_err:
            sys.stderr.write(f"Workstate sync error: {sync_err}\n")

    return parse_yaml_frontmatter(task_path)


def write_session_state(root_dir: Path, status: str, port: int, pid: int, extra: Optional[Dict[str, Any]] = None):
    """Write or update workforces/.canvas-session.json with current runtime telemetry."""
    try:
        session_file = root_dir / "workforces" / ".canvas-session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "status": status,
            "pid": pid,
            "port": port,
            "url": f"http://127.0.0.1:{port}",
            "updated_at": datetime.datetime.now().isoformat(),
        }
        if extra:
            data.update(extra)
        session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"Error writing .canvas-session.json: {e}\n")


def get_comments(root_dir: Path, target_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve visual pins and comments from workforces/.canvas-comments.json."""
    comments_file = root_dir / "workforces" / ".canvas-comments.json"
    if not comments_file.exists():
        return []
    try:
        data = json.loads(comments_file.read_text(encoding="utf-8"))
        if target_id:
            tid_clean = str(target_id).rstrip("/").split("/")[-1]
            tid_stem = tid_clean[:-3] if tid_clean.endswith(".md") else tid_clean
            matched = []
            for c in data:
                c_tid = str(c.get("target_id") or "")
                c_file = str(c.get("file") or "")
                c_file_clean = c_file.rstrip("/").split("/")[-1]
                c_file_stem = c_file_clean[:-3] if c_file_clean.endswith(".md") else c_file_clean

                if (c_tid == target_id
                    or c_file == target_id
                    or c_tid == tid_clean
                    or c_tid == tid_stem
                    or c_file_clean == tid_clean
                    or c_file_stem == tid_stem):
                    matched.append(c)
            return matched
        return data
    except Exception as err:
        sys.stderr.write(f"Warning: Error reading comments: {err}\n")
        return []


def save_comment(root_dir: Path, comment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save a visual pin or review comment and append an evolution note if linked to a task."""
    comments_file = root_dir / "workforces" / ".canvas-comments.json"
    comments = []
    if comments_file.exists():
        try:
            comments = json.loads(comments_file.read_text(encoding="utf-8"))
        except Exception:
            comments = []

    comment_id = f"comment-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    pin = comment_data.get("pin")
    entry = {
        "id": comment_id,
        "target_type": comment_data.get("target_type", "task"),
        "target_id": comment_data.get("target_id") or comment_data.get("file", ""),
        "file": comment_data.get("file", ""),
        "comment": comment_data.get("comment", ""),
        "author": comment_data.get("author", "@human"),
        "pin": pin,
        "stitch_url": comment_data.get("stitch_url", ""),
        "created_at": datetime.datetime.now().isoformat(),
    }
    comments.append(entry)
    comments_file.parent.mkdir(parents=True, exist_ok=True)
    comments_file.write_text(json.dumps(comments, indent=2), encoding="utf-8")

    # If target points to a task file or task ID, resolve path and append evolution note
    target_identifier = comment_data.get("file") or comment_data.get("target_id") or ""
    resolved_task_file = None
    if target_identifier:
        cand = root_dir / str(target_identifier).lstrip("/")
        if cand.exists() and cand.is_file():
            resolved_task_file = str(cand.relative_to(root_dir))
        elif (root_dir / "workforces" / str(target_identifier).lstrip("/")).exists():
            resolved_task_file = str((root_dir / "workforces" / str(target_identifier).lstrip("/")).relative_to(root_dir))
        elif (root_dir / "workforces" / "tasks" / str(target_identifier).lstrip("/")).exists():
            resolved_task_file = str((root_dir / "workforces" / "tasks" / str(target_identifier).lstrip("/")).relative_to(root_dir))
        else:
            tasks_dir = root_dir / "workforces" / "tasks"
            if tasks_dir.exists():
                for tf in tasks_dir.glob("*.md"):
                    if tf.stem == target_identifier or tf.name == target_identifier or tf.name == f"{target_identifier}.md":
                        resolved_task_file = str(tf.relative_to(root_dir))
                        break
                    try:
                        meta = parse_yaml_frontmatter(tf)
                        if meta.get("id") == target_identifier:
                            resolved_task_file = str(tf.relative_to(root_dir))
                            break
                    except Exception:
                        pass

    if resolved_task_file:
        try:
            pin_str = f" [Pin: {pin.get('x', 0):.1f}%, {pin.get('y', 0):.1f}%]" if pin else ""
            stitch_str = f" [Stitch: {entry['stitch_url']}]" if entry.get("stitch_url") else ""
            note_text = f"{entry['author']}: {entry['comment']}{pin_str}{stitch_str}"
            update_task_file(root_dir, resolved_task_file, {"evolution_note": note_text})
            entry["task_updated"] = resolved_task_file
        except Exception as e:
            sys.stderr.write(f"Warning: Could not append comment to task file: {e}\n")

    return entry


def get_inbox_items(root_dir: Path) -> List[Dict[str, Any]]:
    """Retrieve all items from workforces/inbox/ (pending, human_review, processed), supporting JSON and Markdown."""
    items = []
    for sub in ("pending", "human_review", "processed"):
        d = root_dir / "workforces" / "inbox" / sub
        if d.exists():
            for f in sorted(list(d.glob("*.json")) + list(d.glob("*.md")), reverse=True):
                try:
                    if f.suffix == ".json":
                        item_data = json.loads(f.read_text(encoding="utf-8"))
                    else:
                        meta = parse_yaml_frontmatter(f)
                        raw_body = meta.get("_body")
                        if raw_body is None:
                            try:
                                raw_body = f.read_text(encoding="utf-8")
                            except Exception:
                                raw_body = ""
                        item_data = {
                            "id": meta.get("id") or f.stem,
                            "title": meta.get("title") or f.stem.replace("-", " ").title(),
                            "type": meta.get("type") or "research",
                            "content": raw_body,
                            "source_url": meta.get("source_url") or "",
                            "status": meta.get("status") or sub,
                            "captured_at": meta.get("created_at") or datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                        }
                    item_data["_folder"] = sub
                    item_data["_filename"] = f.name
                    items.append(item_data)
                except Exception as err:
                    sys.stderr.write(f"Warning: error reading inbox file {f.name}: {err}\n")
    return items


class InboxHeartbeatWatcher:
    """
    Background watcher that monitors workforces/inbox/pending/ for new items
    from the Chrome extension or external tools. Routes auto-dispatchable tasks
    to workforces/tasks/ and moves to processed, ideas to workforces/ideas/,
    and human review items to workforces/inbox/human_review/.
    Shuts down cleanly when server.py stops.
    """
    def __init__(self, root_dir: Path, interval: float = 2.0):
        self.root_dir = root_dir
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _run(self):
        pending_dir = self.root_dir / "workforces" / "inbox" / "pending"
        processed_dir = self.root_dir / "workforces" / "inbox" / "processed"
        human_dir = self.root_dir / "workforces" / "inbox" / "human_review"
        tasks_dir = self.root_dir / "workforces" / "tasks"

        for d in (pending_dir, processed_dir, human_dir, tasks_dir):
            d.mkdir(parents=True, exist_ok=True)

        while not self.stop_event.is_set():
            try:
                self._scan_and_route(pending_dir, processed_dir, human_dir, tasks_dir)
            except Exception as e:
                sys.stderr.write(f"[InboxWatcher] Error during scan: {e}\n")
            self.stop_event.wait(self.interval)

    def _scan_and_route(self, pending_dir: Path, processed_dir: Path, human_dir: Path, tasks_dir: Path):
        pending_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        human_dir.mkdir(parents=True, exist_ok=True)
        tasks_dir.mkdir(parents=True, exist_ok=True)
        ideas_dir = self.root_dir / "workforces" / "ideas"
        ideas_dir.mkdir(parents=True, exist_ok=True)

        for item_file in sorted(list(pending_dir.glob("*.json")) + list(pending_dir.glob("*.md"))):
            try:
                now_ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                is_md = item_file.suffix == ".md"
                if is_md:
                    meta = parse_yaml_frontmatter(item_file)
                    content = meta.get("_body")
                    if content is None:
                        content = item_file.read_text(encoding="utf-8")
                    title = meta.get("title")
                    if not title:
                        for line in content.splitlines():
                            if line.startswith("# "):
                                title = line[2:].strip()
                                break
                    title = title or item_file.stem.replace("-", " ").title()
                    item_id = meta.get("id") or f"inbox-{item_file.stem}"
                    auto_dispatch = str(meta.get("auto_dispatch", "")).lower() in ("true", "1", "yes")
                    requires_human = str(meta.get("requires_human", not auto_dispatch)).lower() in ("true", "1", "yes")
                    item_type = meta.get("type") or "research"
                    source_url = meta.get("source_url") or ""
                    priority = meta.get("priority") or "P1"
                    reporter = meta.get("reporter") or "chrome-extension"
                    data = {
                        "id": item_id,
                        "title": title,
                        "content": content,
                        "type": item_type,
                        "source_url": source_url,
                        "priority": priority,
                        "reporter": reporter,
                        "auto_dispatch": auto_dispatch,
                        "requires_human": requires_human,
                        "captured_at": meta.get("created_at") or datetime.datetime.now().isoformat(),
                    }
                else:
                    data = json.loads(item_file.read_text(encoding="utf-8"))
                    item_id = data.get("id", item_file.stem)
                    auto_dispatch = data.get("auto_dispatch", False)
                    requires_human = data.get("requires_human", not auto_dispatch)
                    item_type = data.get("type", "general")
                    title = data.get("title", "Inbox Item")
                    content = data.get("content", "")
                    source_url = data.get("source_url", "")
                    priority = data.get("priority", "P1")
                    reporter = data.get("reporter", "chrome-extension")

                if auto_dispatch:
                    # Create actionable workforce task
                    clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '-', title.lower()).strip('-')[:40] or "task"
                    task_filename = f"{now_ts}-{clean_slug}.md"
                    task_file = tasks_dir / task_filename
                    task_content = f"""---
id: "{item_id}"
title: "{title}"
type: "{item_type}"
priority: "{priority}"
status: "todo"
reporter: "@{reporter.lstrip('@')}"
source_url: "{source_url}"
created_at: "{datetime.datetime.now().isoformat()}"
---
{content}
"""
                    task_file.write_text(task_content, encoding="utf-8")
                    data["status"] = "dispatched"
                    data["dispatched_task_file"] = str(task_file.relative_to(self.root_dir))
                    data["routed_at"] = datetime.datetime.now().isoformat()
                    dest_file = processed_dir / f"{item_file.stem}.json"
                    dest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    item_file.unlink(missing_ok=True)
                    if sync_workstate_from_tasks:
                        try:
                            sync_workstate_from_tasks(str(self.root_dir))
                        except Exception as sync_err:
                            sys.stderr.write(f"Sync error: {sync_err}\n")
                    sys.stderr.write(f"[InboxWatcher] Auto-dispatched task {item_id} -> {task_file.name}\n")
                elif str(item_type).lower() in ("idea", "ideas") or data.get("target_folder") == "ideas":
                    # Route to ideas folder
                    clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '-', title.lower()).strip('-')[:40] or "idea"
                    idea_filename = f"{now_ts}-{clean_slug}.md"
                    idea_file = ideas_dir / idea_filename
                    idea_content = f"""---
id: "{item_id}"
title: "{title}"
type: "idea"
status: "captured"
reporter: "@{reporter.lstrip('@')}"
source_url: "{source_url}"
created_at: "{datetime.datetime.now().isoformat()}"
---
{content}
"""
                    idea_file.write_text(idea_content, encoding="utf-8")
                    data["status"] = "saved_to_ideas"
                    data["dispatched_idea_file"] = str(idea_file.relative_to(self.root_dir))
                    data["routed_at"] = datetime.datetime.now().isoformat()
                    dest_file = processed_dir / f"{item_file.stem}.json"
                    dest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    item_file.unlink(missing_ok=True)
                    sys.stderr.write(f"[InboxWatcher] Routed idea {item_id} -> {idea_file.name}\n")
                elif requires_human or data.get("requires_human", True):
                    # Route to human review folder
                    data["status"] = "needs_human_review"
                    data["routed_at"] = datetime.datetime.now().isoformat()
                    dest_file = human_dir / f"{item_file.stem}.json"
                    dest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    item_file.unlink(missing_ok=True)
                    sys.stderr.write(f"[InboxWatcher] Routed {item_id} to human review\n")
            except Exception as e:
                sys.stderr.write(f"[InboxWatcher] Failed to process {item_file.name}: {e}\n")


class WorkforceCanvasHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler serving the interactive canvas and REST APIs."""

    root_dir: Path = Path.cwd()
    web_dir: Path = Path(__file__).resolve().parent.parent / "web"
    last_activity_time: float = 0.0
    idle_timeout: int = 300  # Default 5 minutes (300 seconds)
    httpd_instance: Any = None
    is_shutting_down: bool = False
    server_port: int = 8765
    watcher_instance: Any = None

    @classmethod
    def record_activity(cls):
        """Reset the activity timestamp whenever an HTTP request or heartbeat is received."""
        cls.last_activity_time = time.time()

    @classmethod
    def trigger_shutdown(cls, delay: float = 0.5):
        """Gracefully stop the HTTP server on a separate background thread."""
        if cls.is_shutting_down:
            return
        cls.is_shutting_down = True

        if cls.watcher_instance:
            try:
                cls.watcher_instance.stop()
            except Exception:
                pass
        write_session_state(cls.root_dir, "stopped", getattr(cls, "server_port", 0) or 8765, os.getpid(), {"stopped_at": datetime.datetime.now().isoformat()})

        def _stop():
            time.sleep(delay)
            if cls.httpd_instance:
                try:
                    cls.httpd_instance.shutdown()
                except Exception as err:
                    sys.stderr.write(f"Shutdown error: {err}\n")

        shutdown_thread = threading.Thread(target=_stop, daemon=True)
        shutdown_thread.start()

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.record_activity()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/api/heartbeat", "/api/ping"):
            elapsed = time.time() - self.last_activity_time
            time_remaining = max(0, self.idle_timeout - elapsed) if self.idle_timeout > 0 else -1
            self.send_json_response({
                "status": "alive",
                "idle_timeout": self.idle_timeout,
                "time_remaining": int(time_remaining),
                "server_pid": os.getpid(),
                "timestamp": datetime.datetime.now().isoformat(),
            })
        elif path == "/api/state":
            self.send_json_response(self.handle_get_state())
        elif path in ("/api/sync", "/api/standup"):
            if sync_workstate_from_tasks:
                try:
                    sync_workstate_from_tasks(str(self.root_dir))
                except Exception:
                    pass
            self.send_json_response(self.handle_get_state())
        elif path == "/api/inbox":
            items = get_inbox_items(self.root_dir)
            self.send_json_response({"items": items, "count": len(items)})
        elif path == "/api/comments":
            target_id = query.get("target_id", [None])[0] or query.get("target", [None])[0]
            self.send_json_response({"comments": get_comments(self.root_dir, target_id)})
        elif path == "/api/turn-summary":
            summary_file = self.root_dir / "workforces" / "tmp" / "turn-summary.txt"
            content = ""
            if summary_file.exists():
                try:
                    content = summary_file.read_text(encoding="utf-8")
                except Exception:
                    pass
            self.send_json_response({"content": content, "exists": summary_file.exists()})
        elif path == "/api/document":
            doc_path = query.get("path", [None])[0]
            if not doc_path:
                self.send_error(400, "Missing 'path' parameter")
                return
            target = (self.root_dir / doc_path.lstrip("/")).resolve()
            root_resolved = self.root_dir.resolve()
            if target.exists() and (str(target).startswith(str(root_resolved)) or str(target).startswith(str(self.root_dir))):
                try:
                    content = target.read_text(encoding="utf-8")
                    self.send_json_response({
                        "path": doc_path,
                        "name": target.name,
                        "size": target.stat().st_size,
                        "content": content,
                        "type": "markdown" if target.suffix == ".md" else "text"
                    })
                except Exception as e:
                    self.send_error(500, f"Error reading document: {e}")
            else:
                self.send_error(404, "Document Not Found")
        elif path == "/api/commit":
            commit_hash = query.get("hash", [None])[0]
            self.send_json_response(get_commit_details(self.root_dir, commit_hash))
        elif path == "/api/impact":
            symbol = query.get("symbol", [None])[0]
            file_param = query.get("file", [None])[0]
            self.send_json_response(get_code_blast_radius(self.root_dir, symbol, file_param))
        elif path == "/" or path == "/index.html":
            self.serve_file(self.web_dir / "index.html", "text/html")
        elif path == "/canvas.css":
            self.serve_file(self.web_dir / "canvas.css", "text/css")
        elif path == "/canvas.js":
            self.serve_file(self.web_dir / "canvas.js", "application/javascript")
        elif path.startswith("/workforces/"):
            target = (self.root_dir / path.lstrip("/")).resolve()
            root_resolved = self.root_dir.resolve()
            if target.exists() and (str(target).startswith(str(root_resolved)) or str(target).startswith(str(self.root_dir))):
                if target.suffix == ".md":
                    content = target.read_text(encoding="utf-8")
                    html_content = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{target.name}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
body {{ background: #faf9f5; color: #4d4d4d; font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px 24px; max-width: 820px; margin: 0 auto; line-height: 1.65; }}
a {{ color: #c2410c; text-decoration: underline; text-underline-offset: 2px; }}
a:hover {{ color: #9a3412; }}
code {{ background: #f4f4f5; color: #c2410c; padding: 2px 6px; border-radius: 2px; font-family: monospace; font-size: 13px; }}
pre {{ background: #f8f8f8; border: 1px solid #e2e0dc; padding: 14px; border-radius: 4px; overflow-x: auto; margin: 16px 0; }}
pre code {{ background: transparent; padding: 0; color: #202020; }}
h1, h2, h3, h4 {{ color: #202020; font-weight: 600; margin-top: 24px; margin-bottom: 8px; }}
h1 {{ font-size: 22px; }}
h2 {{ font-size: 18px; }}
h3 {{ font-size: 15px; }}
hr {{ border-color: #e2e0dc; margin: 24px 0; }}
ul, ol {{ padding-left: 20px; margin: 10px 0; }}
li {{ margin: 4px 0; }}
</style></head>
<body>
<div class="mb-6 flex items-center justify-between pb-3 border-b border-[#e2e0dc] text-xs text-[#828282]">
  <span>📄 {target.name}</span>
  <a href="javascript:window.close()" class="no-underline text-[#828282] hover:text-[#202020]">&larr; Close</a>
</div>
<div id="content"></div>
<script>
  document.getElementById('content').innerHTML = marked.parse({json.dumps(content)});
</script>
</body></html>"""
                    body_bytes = html_content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body_bytes)))
                    self.end_headers()
                    self.wfile.write(body_bytes)
                    return
                else:
                    self.serve_file(target, "text/plain")
                    return
            else:
                self.send_error(404, "File Not Found")
        else:
            # Fallback to serving files from web_dir
            target = (self.web_dir / path.lstrip("/")).resolve()
            if target.exists() and str(target).startswith(str(self.web_dir)):
                mime = "text/plain"
                if target.suffix == ".html":
                    mime = "text/html"
                elif target.suffix == ".css":
                    mime = "text/css"
                elif target.suffix == ".js":
                    mime = "application/javascript"
                elif target.suffix == ".svg":
                    mime = "image/svg+xml"
                self.serve_file(target, mime)
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        self.record_activity()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/api/heartbeat", "/api/ping"):
            elapsed = time.time() - self.last_activity_time
            time_remaining = max(0, self.idle_timeout - elapsed) if self.idle_timeout > 0 else -1
            self.send_json_response({
                "status": "alive",
                "idle_timeout": self.idle_timeout,
                "time_remaining": int(time_remaining),
                "server_pid": os.getpid(),
                "timestamp": datetime.datetime.now().isoformat(),
            })
            return

        elif path == "/api/shutdown":
            self.send_json_response({
                "success": True,
                "message": "Canvas server is shutting down. Port will be released.",
                "server_pid": os.getpid(),
            })
            self.trigger_shutdown(delay=0.3)
            return

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        try:
            data = json.loads(post_body) if post_body else {}
        except Exception:
            self.send_error(400, "Invalid JSON body")
            return

        if path == "/api/task/update":
            file_rel = data.get("file")
            updates = data.get("updates", {})
            if not file_rel:
                self.send_error(400, "Missing 'file' parameter")
                return
            try:
                res = update_task_file(self.root_dir, file_rel, updates)
                self.send_json_response({"success": True, "task": res})
            except Exception as err:
                self.send_error(500, f"Update failed: {err}")

        elif path == "/api/task/connect":
            blocker_id = data.get("blocker_id")
            blocked_id = data.get("blocked_id")
            if not blocker_id or not blocked_id:
                self.send_error(400, "Missing 'blocker_id' or 'blocked_id'")
                return
            try:
                all_tasks = get_all_tasks(self.root_dir)
                target_task = next((t for t in all_tasks if t["id"] == blocked_id), None)
                if not target_task:
                    self.send_error(404, f"Task {blocked_id} not found")
                    return
                current_blocked_by = target_task.get("blocked_by") or []
                if blocker_id not in current_blocked_by:
                    current_blocked_by.append(blocker_id)
                    update_task_file(self.root_dir, target_task["file"], {"blocked_by": current_blocked_by})
                self.send_json_response({"success": True, "blocked_by": current_blocked_by})
            except Exception as err:
                self.send_error(500, f"Connect failed: {err}")

        elif path == "/api/task/order":
            order = data.get("order", [])
            order_file = self.root_dir / "workforces" / ".canvas-order.json"
            order_file.write_text(json.dumps(order, indent=2), encoding="utf-8")
            self.send_json_response({"success": True, "order": order})

        elif path == "/api/sync":
            if sync_workstate_from_tasks:
                try:
                    sync_workstate_from_tasks(str(self.root_dir))
                except Exception as err:
                    sys.stderr.write(f"Sync error: {err}\n")
            fresh_state = self.handle_get_state()
            self.send_json_response({"success": True, "message": "Workstate synchronized from tasks", "state": fresh_state})

        elif path == "/api/task/create":
            try:
                task_res = create_task_file(self.root_dir, data)
                self.send_json_response({"success": True, "task": task_res, "state": self.handle_get_state()})
            except Exception as err:
                self.send_error(500, f"Task creation failed: {err}")

        elif path == "/api/inbox/action":
            item_id = data.get("item_id")
            action = data.get("action", "approve")
            priority = data.get("priority", "P1")
            task_type = data.get("type", "feature")
            if not item_id:
                self.send_error(400, "Missing 'item_id'")
                return
            try:
                res = resolve_inbox_item(self.root_dir, item_id, action, priority, task_type)
                self.send_json_response({"success": True, "result": res, "state": self.handle_get_state()})
            except Exception as err:
                self.send_error(500, f"Inbox action failed: {err}")

        elif path == "/api/inbox/submit":
            now_ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            raw_title = data.get("title") or "Untitled Capture"
            clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", raw_title.lower()).strip("-")[:40] or "item"
            item_id = data.get("id") or f"inbox-{now_ts}-{clean_slug}"
            auto_dispatch = data.get("auto_dispatch", False)

            payload = {
                "id": item_id,
                "title": raw_title,
                "content": data.get("content", ""),
                "type": data.get("type", "general"),
                "source_url": data.get("source_url", ""),
                "selection": data.get("selection", ""),
                "auto_dispatch": auto_dispatch,
                "requires_human": data.get("requires_human", not auto_dispatch),
                "task_id": data.get("task_id", ""),
                "tags": data.get("tags", []),
                "captured_at": datetime.datetime.now().isoformat(),
                "status": "pending"
            }

            inbox_dir = self.root_dir / "workforces" / "inbox" / "pending"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            out_file = inbox_dir / f"{item_id}.json"
            out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            self.send_json_response({
                "success": True,
                "id": item_id,
                "file": str(out_file.relative_to(self.root_dir)),
                "item": payload
            })

        elif path == "/api/comments":
            comment_text = data.get("comment", "").strip()
            if not comment_text:
                self.send_error(400, "Missing 'comment' parameter")
                return
            try:
                res = save_comment(self.root_dir, data)
                self.send_json_response({"success": True, "comment": res})
            except Exception as err:
                self.send_error(500, f"Failed to save comment: {err}")
        else:
            self.send_error(404, "Not Found")

    def handle_get_state(self) -> Dict[str, Any]:
        """Aggregate full workforce state for the canvas."""
        tasks = get_all_tasks(self.root_dir)
        hypotheses = get_all_hypotheses(self.root_dir)
        goals = get_all_goals(self.root_dir)

        # Read saved custom layout coordinates if present
        order_file = self.root_dir / "workforces" / ".canvas-order.json"
        custom_order = []
        if order_file.exists():
            try:
                custom_order = json.loads(order_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Build dependency edges
        edges = []
        task_id_set = {t["id"] for t in tasks}
        for t in tasks:
            for blocker in t.get("blocked_by", []):
                if blocker in task_id_set:
                    edges.append({
                        "source": blocker,
                        "target": t["id"],
                        "type": "dependency",
                        "label": "blocks"
                    })

        # Extract available symbols across internal repositories
        available_symbols = load_multi_repo_symbols(self.root_dir)

        # Correlate linked commits, docs, and code symbols for each task
        commits = get_recent_commits(self.root_dir)
        link_task_relationships(tasks, available_symbols, commits)

        # Scan all session context notes
        sessions = get_all_sessions(self.root_dir)

        # Inbox items
        inbox_items = get_inbox_items(self.root_dir)

        # Comments
        comments = get_comments(self.root_dir)

        # Turn summary
        turn_summary_text = ""
        summary_file = self.root_dir / "workforces" / "tmp" / "turn-summary.txt"
        if summary_file.exists():
            try:
                turn_summary_text = summary_file.read_text(encoding="utf-8")
            except Exception:
                pass

        # Compile standup and executive productivity data
        standup = get_standup_data(self.root_dir, tasks, inbox_items, sessions)

        # Summary telemetry
        stats = {
            "total_tasks": len(tasks),
            "todo": len([t for t in tasks if t["status"] == "todo"]),
            "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
            "blocked": len([t for t in tasks if t["status"] == "blocked" or t.get("blocked_by")]),
            "done": len([t for t in tasks if t["status"] == "done"]),
            "sessions_count": len(sessions),
            "hypotheses_count": len(hypotheses),
            "goals_count": len(goals),
            "symbols_count": len(available_symbols),
            "inbox_count": len(inbox_items),
            "needs_attention_count": len(standup.get("needs_attention", [])),
            "wins_count": len(standup.get("wins_24h", [])),
            "comments_count": len(comments),
        }

        return {
            "tasks": tasks,
            "sessions": sessions,
            "hypotheses": hypotheses,
            "goals": goals,
            "symbols": available_symbols,
            "edges": edges,
            "custom_order": custom_order,
            "inbox": inbox_items,
            "comments": comments,
            "turn_summary": turn_summary_text,
            "standup": standup,
            "git": standup.get("git", {}),
            "installed_teams": standup.get("installed_teams", []),
            "workstate_markdown": standup.get("workstate_markdown", ""),
            "stats": stats,
            "timestamp": datetime.datetime.now().isoformat(),
        }

    def send_json_response(self, data: Any):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, file_path: Path, content_type: str):
        if not file_path.exists():
            self.send_error(404, "File Not Found")
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Clean compact logging
        sys.stderr.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {format % args}\n")


def run_server(
    port: int = 8765,
    host: str = "127.0.0.1",
    root_dir: Optional[str] = None,
    open_browser: bool = False,
    idle_timeout: int = 300,
):
    resolved_root = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()
    WorkforceCanvasHandler.root_dir = resolved_root
    WorkforceCanvasHandler.idle_timeout = idle_timeout
    WorkforceCanvasHandler.last_activity_time = time.time()
    WorkforceCanvasHandler.is_shutting_down = False

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = None
    selected_port = port
    for p in range(port, port + 50):
        try:
            httpd = ReusableTCPServer((host, p), WorkforceCanvasHandler)
            selected_port = p
            break
        except OSError as e:
            if e.errno in (48, 98):  # macOS 48 / Linux 98: Address already in use
                continue
            raise

    if not httpd:
        sys.stderr.write(f"Error: Could not find an available port in range {port}-{port+50}.\n")
        sys.exit(1)

    WorkforceCanvasHandler.httpd_instance = httpd
    WorkforceCanvasHandler.server_port = selected_port

    # Record active session state to workforces/.canvas-session.json
    write_session_state(resolved_root, "running", selected_port, os.getpid(), {"started_at": datetime.datetime.now().isoformat()})

    # Start Inbox Heartbeat Watcher for background task routing
    watcher = InboxHeartbeatWatcher(resolved_root)
    watcher.start()
    WorkforceCanvasHandler.watcher_instance = watcher

    # Start background idle watchdog thread
    if idle_timeout > 0:
        def _idle_watchdog():
            while not WorkforceCanvasHandler.is_shutting_down:
                time.sleep(2)
                if WorkforceCanvasHandler.is_shutting_down:
                    break
                if WorkforceCanvasHandler.idle_timeout > 0:
                    elapsed = time.time() - WorkforceCanvasHandler.last_activity_time
                    if elapsed >= WorkforceCanvasHandler.idle_timeout:
                        print(f"\n⏰ Idle timeout ({int(elapsed)}s with no active browser tab).")
                        print(f"🛑 Automatically shutting down canvas server to release port {selected_port}.\n")
                        WorkforceCanvasHandler.trigger_shutdown(delay=0.1)
                        break

        watchdog_thread = threading.Thread(target=_idle_watchdog, daemon=True)
        watchdog_thread.start()

    with httpd:
        url = f"http://{host}:{selected_port}/"
        if selected_port != port:
            print(f"\n⚠️  Port {port} is occupied by another instance.")
            print(f"👉 Automatically allocated port: {selected_port}")
        print(f"\n🚀 Workforce Command Canvas active at: {url}")
        print(f"📁 Root workspace: {resolved_root}")
        print(f"📥 Inbox Watcher: active (monitoring workforces/inbox/pending/)")
        if idle_timeout > 0:
            print(f"⏱️  Auto-shutdown watchdog: {idle_timeout}s idle timeout (auto-stops when browser tab closes)")
        else:
            print("⏱️  Auto-shutdown watchdog: disabled (runs continuously)")
        print("Press Ctrl+C or use the canvas UI power button to stop the server.\n")

        if open_browser:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down canvas server.")
        finally:
            WorkforceCanvasHandler.is_shutting_down = True
            if watcher:
                watcher.stop()
            write_session_state(resolved_root, "stopped", selected_port, os.getpid(), {"stopped_at": datetime.datetime.now().isoformat()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workforce Command Canvas Server")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--root", type=str, default="./", help="Root workforce directory")
    parser.add_argument("--open", action="store_true", help="Automatically open canvas in default browser")
    parser.add_argument("--idle-timeout", type=int, default=300, help="Idle timeout in seconds before auto-shutdown (default: 300 / 5 minutes, 0 to disable)")

    args = parser.parse_args()
    run_server(port=args.port, host=args.host, root_dir=args.root, open_browser=args.open, idle_timeout=args.idle_timeout)
