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
            "blocked_by": meta.get("blocked_by") or [],
            "delegated_to": meta.get("delegated_to") or "",
            "deciding_factors": meta.get("deciding_factors") or [],
            "body": meta.get("_body") or "",
            "updated_at": meta.get("updated_at") or meta.get("created_at") or "",
        }
        tasks.append(task_node)
    return tasks


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


def get_code_blast_radius(root_dir: Path, symbol_name: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract upstream callers and downstream blast radius for a given symbol or file.
    Reuses symbols from code-graph.json and logic aligned with pre_impact_analyzer.
    """
    code_graph_file = root_dir / "workforces" / "code-graph.json"
    if not code_graph_file.exists():
        code_graph_file = root_dir / "code-graph.json"

    symbols = []
    if code_graph_file.exists():
        try:
            data = json.loads(code_graph_file.read_text(encoding="utf-8"))
            symbols = data.get("symbols", [])
        except Exception as err:
            sys.stderr.write(f"Failed to read code-graph: {err}\n")

    # Map by name for fast lookup
    symbol_map = {s.get("name"): s for s in symbols if s.get("name")}

    target_symbol = None
    if symbol_name and symbol_name in symbol_map:
        target_symbol = symbol_map[symbol_name]
    elif file_path:
        # Find first symbol in target file
        for s in symbols:
            if s.get("file") == file_path:
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

    # Upstream: functions called BY target_symbol
    upstream_callees = []
    calls = target_symbol.get("calls", [])
    for call_name in calls:
        if call_name in symbol_map:
            upstream_callees.append(symbol_map[call_name])
        else:
            upstream_callees.append({
                "name": call_name,
                "kind": "external",
                "file": "standard_lib_or_external",
                "line": 0
            })

    # Downstream: other functions that CALL target_name (Blast Radius)
    downstream_callers = []
    affected_files = set()
    for s in symbols:
        if s.get("name") == target_name and s.get("file") == target_file:
            continue
        if target_name in s.get("calls", []):
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

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/state":
            self.send_json_response(self.handle_get_state())
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
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

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

        # Summary telemetry
        stats = {
            "total_tasks": len(tasks),
            "todo": len([t for t in tasks if t["status"] == "todo"]),
            "in_progress": len([t for t in tasks if t["status"] == "in_progress"]),
            "blocked": len([t for t in tasks if t["status"] == "blocked"]),
            "done": len([t for t in tasks if t["status"] == "done"]),
            "hypotheses_count": len(hypotheses),
            "goals_count": len(goals),
        }

        return {
            "tasks": tasks,
            "hypotheses": hypotheses,
            "goals": goals,
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


def run_server(port: int = 8765, host: str = "127.0.0.1", root_dir: Optional[str] = None, open_browser: bool = False):
    resolved_root = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()
    WorkforceCanvasHandler.root_dir = resolved_root

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

    with httpd:
        url = f"http://{host}:{selected_port}/"
        if selected_port != port:
            print(f"\n⚠️  Port {port} is occupied by another instance.")
            print(f"👉 Automatically allocated port: {selected_port}")
        print(f"\n🚀 Workforce Command Canvas active at: {url}")
        print(f"📁 Root workspace: {resolved_root}")
        print("Press Ctrl+C to stop the server.\n")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workforce Command Canvas Server")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--root", type=str, default="./", help="Root workforce directory")
    parser.add_argument("--open", action="store_true", help="Automatically open canvas in default browser")

    args = parser.parse_args()
    run_server(port=args.port, host=args.host, root_dir=args.root, open_browser=args.open)
