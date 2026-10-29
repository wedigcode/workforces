#!/usr/bin/env python3
"""
Pre-Tool Lifecycle Hook for Workforces
Zero external dependencies (Python 3 standard library: json, os, sys, subprocess, pathlib).

Adheres to the Antigravity PreToolUse lifecycle hook protocol:
1. Reads context JSON from sys.stdin (handles missing/empty stdin gracefully).
2. Parses toolCall or toolUse; if TargetFile or target_file is present, invokes
   the wf-code-graph symbol indexer and pre-impact analyzer.
3. Emits valid JSON `{"decision": "allow"}` on sys.stdout.
4. Exits with return code 0.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

EDITOR_BASES = (".agents", ".claude", ".grok", ".github", ".github/copilot", ".cursor", "")
_TARGET_FILE_KEYS = (
    "TargetFile", "target_file", "file_path", "filePath", "notebook_path", "notebookPath", "file", "path", "targetFile"
)


def find_sibling_script(script_name: str, root_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate a sibling script within wf-code-graph/scripts or multi-editor fallback locations."""
    candidate = Path(__file__).resolve().parent / script_name
    if candidate.is_file():
        return candidate

    roots = [r for r in (root_dir, Path.cwd()) if r is not None]
    for r in roots:
        for eb in EDITOR_BASES:
            base = r / eb if eb else r
            p = base / "skills" / "wf-code-graph" / "scripts" / script_name
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
    """Determine root directory from workspacePaths, payload cwd, or plugin cwd ancestry."""
    workspace_paths = data.get("workspacePaths")
    if isinstance(workspace_paths, list) and workspace_paths:
        candidate_ws = Path(str(workspace_paths[0])).resolve()
        if candidate_ws.exists():
            return candidate_ws
    raw_cwd = data.get("cwd")
    if isinstance(raw_cwd, str) and raw_cwd.strip():
        cand_cwd = Path(raw_cwd).resolve()
        if cand_cwd.exists():
            return cand_cwd if cand_cwd.is_dir() else cand_cwd.parent
    cwd = Path.cwd().resolve()
    if cwd.parent.name == "plugins":
        p2 = cwd.parent.parent
        if p2.name == "copilot" and p2.parent.name == ".github":
            return p2.parent.parent
        if p2.name in (".agents", ".claude", ".grok", ".github", ".cursor"):
            return p2.parent
        return p2
    return cwd


def _extract_args_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract tool argument dictionary across Antigravity, Claude Code, and Grok Build payloads."""
    raw_args: Any = data.get("tool_input")
    if raw_args is None:
        tool_call = data.get("toolCall") or data.get("toolUse") or data.get("call")
        if isinstance(tool_call, dict):
            raw_args = tool_call.get("args") or tool_call.get("arguments") or tool_call.get("input")
    if raw_args is None and isinstance(data.get("input"), dict):
        raw_args = data["input"]
    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args)
        except json.JSONDecodeError:
            raw_args = {}
    return raw_args if isinstance(raw_args, dict) else {}


def _extract_target_file(data: Dict[str, Any]) -> Optional[str]:
    """Determine target file from tool_input, toolCall, or toolUse."""
    args = _extract_args_dict(data)
    for key in _TARGET_FILE_KEYS:
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


def _run_impact_analysis(target_file: str, root_dir: Path) -> str:
    """Invoke pre-impact analyzer for target file and return analysis text."""
    analyzer_script = find_sibling_script("pre_impact_analyzer.py", root_dir)
    if not analyzer_script:
        return ""
    try:
        res = subprocess.run(
            [sys.executable, str(analyzer_script), "--file", str(target_file), "--root", str(root_dir)],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=25,
        )
        out_text = res.stdout.strip() if res.stdout else ""
        if out_text:
            sys.stderr.write(f"\n{out_text}\n\n")
        if res.returncode != 0 and res.stderr:
            sys.stderr.write(f"[pre_tool_hook] Analyzer notice: {res.stderr.strip()}\n")
        return out_text
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Impact analysis failed: {err}\n")
        return ""


def run_code_graph_analysis(target_file: str, root_dir: Path) -> str:
    """Execute wf-code-graph symbol indexing and pre-impact analysis."""
    _run_symbol_indexing(root_dir)
    return _run_impact_analysis(target_file, root_dir)


def _build_pre_hook_stdout(data: Dict[str, Any], impact_text: str) -> Dict[str, Any]:
    """Build host-compatible PreToolUse stdout JSON payload."""
    parts = Path(__file__).resolve().parts
    is_claude = ".claude" in parts or (
        data.get("hook_event_name") == "PreToolUse" and ".grok" not in parts and "toolCall" not in data
    )
    if is_claude:
        if impact_text:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": impact_text}}
        return {}
    return {"decision": "allow"}


def main() -> None:
    """Entry point for PreToolUse lifecycle hook."""
    data: Dict[str, Any] = {}
    impact_text = ""
    try:
        data, target_file, root_dir = parse_pre_tool_stdin()
        if target_file:
            impact_text = run_code_graph_analysis(target_file, root_dir)
    except Exception as err:
        sys.stderr.write(f"[pre_tool_hook] Unexpected hook error: {err}\n")

    sys.stdout.write(json.dumps(_build_pre_hook_stdout(data, impact_text)) + "\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()

