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


def find_sibling_script(script_name: str) -> Optional[Path]:
    """Locate a sibling script within code-graph/scripts or standard fallback locations."""
    self_dir = Path(__file__).resolve().parent
    candidate = self_dir / script_name
    if candidate.is_file():
        return candidate

    for base in [Path.cwd(), Path.cwd() / ".agents"]:
        p = base / "skills" / "code-graph" / "scripts" / script_name
        if p.is_file():
            return p
    return None


def parse_pre_tool_stdin() -> Tuple[Dict[str, Any], Optional[str], Path]:
    """
    Read and parse JSON from sys.stdin.
    Returns: (payload_dict, target_file_path_or_None, root_directory_path)
    """
    raw_input = ""
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Warning reading stdin: {err}\n")

    if not raw_input.strip():
        return {}, None, Path.cwd()

    try:
        data = json.loads(raw_input)
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Non-JSON or malformed stdin received: {err}\n")
        return {}, None, Path.cwd()

    if not isinstance(data, dict):
        return {}, None, Path.cwd()

    # Determine root directory from workspacePaths
    root_dir = Path.cwd()
    workspace_paths = data.get("workspacePaths")
    if workspace_paths and isinstance(workspace_paths, list) and len(workspace_paths) > 0:
        candidate_ws = Path(workspace_paths[0]).resolve()
        if candidate_ws.exists():
            root_dir = candidate_ws

    # Determine target file from toolCall or toolUse
    target_file = None
    tool_call = data.get("toolCall") or data.get("toolUse") or data.get("call") or {}
    if isinstance(tool_call, dict):
        args = tool_call.get("args") or tool_call.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if isinstance(args, dict):
            target_file = (
                args.get("TargetFile")
                or args.get("target_file")
                or args.get("file")
                or args.get("path")
                or args.get("filePath")
                or args.get("targetFile")
            )

    return data, target_file, root_dir


def run_code_graph_analysis(target_file: str, root_dir: Path) -> None:
    """Execute code-graph symbol indexing and pre-impact analysis."""
    # 1. Invoke symbol indexer to keep code-graph.json fresh
    indexer_script = find_sibling_script("graph_indexer.py")
    if indexer_script:
        try:
            res_idx = subprocess.run(
                [sys.executable, str(indexer_script), "--scan", str(root_dir)],
                cwd=root_dir,
                capture_output=True,
                text=True,
                timeout=25,
            )
            if res_idx.returncode != 0 and res_idx.stderr:
                sys.stderr.write(f"[pre_tool_hook] Indexer notice: {res_idx.stderr.strip()}\n")
        except Exception as err:
            sys.stderr.write(f"[pre_tool_hook] Indexer execution failed: {err}\n")

    # 2. Invoke pre-impact analyzer for the target file
    analyzer_script = find_sibling_script("pre_impact_analyzer.py")
    if analyzer_script:
        try:
            res_ana = subprocess.run(
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
            if res_ana.stdout:
                sys.stderr.write(f"\n{res_ana.stdout.strip()}\n\n")
            if res_ana.returncode != 0 and res_ana.stderr:
                sys.stderr.write(f"[pre_tool_hook] Analyzer notice: {res_ana.stderr.strip()}\n")
        except Exception as err:
            sys.stderr.write(f"[pre_tool_hook] Impact analysis failed: {err}\n")


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
