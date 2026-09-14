#!/usr/bin/env python3
"""
Pre-Tool Lifecycle Hook for Workforces
Zero external dependencies (Python 3 standard library: json, os, sys, subprocess, pathlib).

Adheres to the Antigravity PreToolUse lifecycle hook protocol:
1. Reads context JSON from sys.stdin (handles missing/empty stdin gracefully).
2. Parses toolCall or toolUse; if TargetFile or target_file is present, invokes
   the code-graph symbol indexer and pre-impact analyzer.
3. Emits valid JSON `{"decision": "allow"}` on sys.stdout.
4. Exits with return code 0.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def find_sibling_script(script_name: str, root_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate a sibling script within code-graph/scripts or standard fallback locations."""
    self_dir = Path(__file__).resolve().parent
    candidate = self_dir / script_name
    if candidate.is_file():
        return candidate

    search_bases = []
    if root_dir:
        search_bases.extend([root_dir / ".agents", root_dir])
    search_bases.extend([Path.cwd() / ".agents", Path.cwd()])

    for base in search_bases:
        p = base / "skills" / "code-graph" / "scripts" / script_name
        if p.is_file():
            return p
    return None


def _read_stdin_json(hook_name: str) -> Dict[str, Any]:
    """Read and parse JSON from sys.stdin."""
    raw_input = ""
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
    except Exception as err:
        sys.stderr.write(f"[{hook_name}] Warning reading stdin: {err}\n")

    if not raw_input.strip():
        return {}

    try:
        data = json.loads(raw_input)
        return data if isinstance(data, dict) else {}
    except Exception as err:
        sys.stderr.write(f"[{hook_name}] Non-JSON or malformed stdin received: {err}\n")
        return {}


def _resolve_root_dir(data: Dict[str, Any]) -> Path:
    """Determine root directory from workspacePaths in hook payload."""
    workspace_paths = data.get("workspacePaths")
    if workspace_paths and isinstance(workspace_paths, list) and len(workspace_paths) > 0:
        candidate_ws = Path(workspace_paths[0]).resolve()
        if candidate_ws.exists():
            return candidate_ws
    return Path.cwd()


def _extract_target_file(data: Dict[str, Any]) -> Optional[str]:
    """Determine target file from toolCall or toolUse."""
    tool_call = data.get("toolCall") or data.get("toolUse") or data.get("call") or {}
    if not isinstance(tool_call, dict):
        return None
    args = tool_call.get("args") or tool_call.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        return None
    for key in ("TargetFile", "target_file", "file", "path", "filePath", "targetFile"):
        val = args.get(key)
        if val:
            return str(val)
    return None


def parse_pre_tool_stdin() -> Tuple[Dict[str, Any], Optional[str], Path]:
    """
    Read and parse JSON from sys.stdin.
    Returns: (payload_dict, target_file_path_or_None, root_directory_path)
    """
    data = _read_stdin_json("pre_tool_hook")
    root_dir = _resolve_root_dir(data)
    target_file = _extract_target_file(data)
    return data, target_file, root_dir


def _run_symbol_indexing(root_dir: Path) -> None:
    """Invoke symbol indexer to keep code-graph.json fresh."""
    indexer_script = find_sibling_script("graph_indexer.py", root_dir)
    if not indexer_script:
        return
    try:
        res = subprocess.run(
            [sys.executable, str(indexer_script), "--scan", str(root_dir)],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res.returncode != 0 and res.stderr:
            sys.stderr.write(f"[pre_tool_hook] Indexer notice: {res.stderr.strip()}\n")
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Indexer execution failed: {err}\n")


def _run_impact_analysis(target_file: str, root_dir: Path) -> None:
    """Invoke pre-impact analyzer for target file."""
    analyzer_script = find_sibling_script("pre_impact_analyzer.py", root_dir)
    if not analyzer_script:
        return
    try:
        res = subprocess.run(
            [
                sys.executable,
                str(analyzer_script),
                "--file",
                str(target_file),
                "--root",
                str(root_dir),
            ],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res.stdout:
            sys.stderr.write(f"\n{res.stdout.strip()}\n\n")
        if res.returncode != 0 and res.stderr:
            sys.stderr.write(f"[pre_tool_hook] Analyzer notice: {res.stderr.strip()}\n")
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Impact analysis failed: {err}\n")


def run_code_graph_analysis(target_file: str, root_dir: Path) -> None:
    """Execute code-graph symbol indexing and pre-impact analysis."""
    _run_symbol_indexing(root_dir)
    _run_impact_analysis(target_file, root_dir)


def main() -> None:
    """Entry point for PreToolUse lifecycle hook."""
    try:
        _, target_file, root_dir = parse_pre_tool_stdin()
        if target_file:
            run_code_graph_analysis(target_file, root_dir)
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Unexpected hook error: {err}\n")

    # Strictly adhere to Antigravity PreToolUse contract:
    # Must emit valid JSON on stdout and exit 0
    sys.stdout.write(json.dumps({"decision": "allow"}) + "\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
