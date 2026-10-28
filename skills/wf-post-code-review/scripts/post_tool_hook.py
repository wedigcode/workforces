#!/usr/bin/env python3
"""
Post-Tool Lifecycle Hook for Workforces
Zero external dependencies (Python 3 standard library: json, os, sys, subprocess, pathlib).

Adheres to the Antigravity PostToolUse lifecycle hook protocol:
1. Reads context JSON from sys.stdin (handles missing/empty stdin gracefully).
2. Invokes post_code_reviewer.py --root ./ to check diffs and report issues.
3. Emits valid JSON `{}` on sys.stdout.
4. Exits with return code 0.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


EDITOR_BASES = (".agents", ".claude", ".grok", ".github/copilot", "")


def find_reviewer_script(root_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate post_code_reviewer.py in wf-post-code-review/scripts or multi-editor fallback locations."""
    candidate = Path(__file__).resolve().parent / "post_code_reviewer.py"
    if candidate.is_file():
        return candidate

    roots = [r for r in (root_dir, Path.cwd()) if r is not None]
    for r in roots:
        for eb in EDITOR_BASES:
            base = r / eb if eb else r
            p = base / "skills" / "wf-post-code-review" / "scripts" / "post_code_reviewer.py"
            if p.is_file():
                return p
    return None


def _default_workspace_root() -> Path:
    """Resolve workspace root when cwd may be inside an editor plugin folder."""
    cwd = Path.cwd().resolve()
    if cwd.parent.name == "plugins":
        p2 = cwd.parent.parent
        if p2.name == "copilot" and p2.parent.name == ".github":
            return p2.parent.parent
        if p2.name in (".agents", ".claude", ".grok"):
            return p2.parent
        return p2
    return cwd


def parse_post_tool_stdin() -> Tuple[Dict[str, Any], Path]:
    """
    Read and parse JSON from sys.stdin adhering to Antigravity PostToolUse protocol.
    Returns: (payload_dict, root_directory_path)
    """
    default_root = _default_workspace_root()
    raw_input = ""
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
    except Exception as err:
        sys.stderr.write(f"[post_tool_hook] Warning reading stdin: {err}\n")

    if not raw_input.strip():
        return {}, default_root

    try:
        data = json.loads(raw_input)
    except Exception as err:
        sys.stderr.write(f"[post_tool_hook] Non-JSON or malformed stdin received: {err}\n")
        return {}, default_root

    if not isinstance(data, dict):
        return {}, default_root

    workspace_paths = data.get("workspacePaths")
    if workspace_paths and isinstance(workspace_paths, list) and len(workspace_paths) > 0:
        candidate_ws = Path(workspace_paths[0]).resolve()
        if candidate_ws.exists():
            return data, candidate_ws

    return data, default_root


def run_post_code_review(root_dir: Path) -> None:
    """Invoke post_code_reviewer.py against the target root directory."""
    reviewer_script = find_reviewer_script(root_dir)
    if not reviewer_script:
        sys.stderr.write("[post_tool_hook] post_code_reviewer.py script not found.\n")
        return

    try:
        res = subprocess.run(
            [sys.executable, str(reviewer_script), "--root", str(root_dir)],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res.stdout:
            sys.stderr.write(f"\n{res.stdout.strip()}\n\n")
        if res.returncode != 0 and res.stderr:
            sys.stderr.write(f"[post_tool_hook] Reviewer notice: {res.stderr.strip()}\n")
    except Exception as err:
        sys.stderr.write(f"[post_tool_hook] Reviewer execution failed: {err}\n")


def main() -> None:
    """Entry point for PostToolUse lifecycle hook."""
    try:
        _, root_dir = parse_post_tool_stdin()
        run_post_code_review(root_dir)
    except Exception as err:
        sys.stderr.write(f"[post_tool_hook] Unexpected hook error: {err}\n")

    # Strictly adhere to Antigravity PostToolUse contract:
    # Must emit empty JSON object on stdout and exit 0
    sys.stdout.write("{}\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
