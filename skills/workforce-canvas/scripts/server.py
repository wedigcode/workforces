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
    task_path = root_dir / relative_file
    if not task_path.exists():
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


class WorkforceCanvasHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler serving the interactive canvas and REST APIs."""

    root_dir: Path = Path.cwd()
    web_dir: Path = Path(__file__).resolve().parent.parent / "web"
    last_activity_time: float = 0.0
    idle_timeout: int = 300  # Default 5 minutes (300 seconds)
    httpd_instance: Any = None
    is_shutting_down: bool = False

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
            if target.exists() and str(target).startswith(str(self.root_dir)):
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

        # Summary telemetry
        stats = {
            "total_tasks": len(tasks),
            "todo": len([t for t in tasks if t["status"] == "todo"]),
            "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
            "blocked": len([t for t in tasks if t["status"] == "blocked"]),
            "done": len([t for t in tasks if t["status"] == "done"]),
            "sessions_count": len(sessions),
            "hypotheses_count": len(hypotheses),
            "goals_count": len(goals),
            "symbols_count": len(available_symbols),
        }

        return {
            "tasks": tasks,
            "sessions": sessions,
            "hypotheses": hypotheses,
            "goals": goals,
            "symbols": available_symbols,
            "edges": edges,
            "custom_order": custom_order,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workforce Command Canvas Server")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--root", type=str, default="./", help="Root workforce directory")
    parser.add_argument("--open", action="store_true", help="Automatically open canvas in default browser")
    parser.add_argument("--idle-timeout", type=int, default=300, help="Idle timeout in seconds before auto-shutdown (default: 300 / 5 minutes, 0 to disable)")

    args = parser.parse_args()
    run_server(port=args.port, host=args.host, root_dir=args.root, open_browser=args.open, idle_timeout=args.idle_timeout)
