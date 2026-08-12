#!/usr/bin/env python3
"""
Pre-Hook Impact & Context Analyzer for Workforces
Zero external dependencies (Python 3 standard library: ast, re, json, pathlib, argparse, subprocess).

Fires on pre_tool_call (before code modification tools).
Scans target files/symbols using code-graph data to report:
1. Defined symbols in target file
2. Downstream callers (blast radius: files calling these symbols)
3. Upstream dependencies (symbols/files called by target file)
4. Existing helper functions in repository to prevent duplicate code
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

def get_git_modified_files(root_dir: Path) -> List[str]:
    """Get list of modified or untracked files via git status/diff."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode != 0:
            return []
        files = []
        for line in res.stdout.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])
        return files
    except Exception:
        return []

def load_code_graph(root_dir: Path) -> List[Dict[str, Any]]:
    """Load or generate code-graph.json symbols."""
    graph_path = root_dir / "workforces" / "code-graph.json"
    if graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            return data.get("symbols", [])
        except Exception:
            pass

    # Fallback to invoking graph_indexer script if available
    indexer_script = root_dir / "skills" / "code-graph" / "scripts" / "graph_indexer.py"
    if not indexer_script.exists():
        indexer_script = root_dir / ".agents" / "skills" / "code-graph" / "scripts" / "graph_indexer.py"

    if indexer_script.exists():
        try:
            subprocess.run([sys.executable, str(indexer_script), "--scan", str(root_dir)], capture_output=True, timeout=10)
            if graph_path.exists():
                data = json.loads(graph_path.read_text(encoding="utf-8"))
                return data.get("symbols", [])
        except Exception:
            pass
    return []

def analyze_target_file(target_path_str: str, root_dir: Path, symbols: List[Dict[str, Any]]) -> str:
    """Analyze blast radius, callers, and existing helpers for a target file."""
    try:
        target_path = Path(target_path_str).resolve()
        rel_target = str(target_path.relative_to(root_dir.resolve()))
    except Exception:
        rel_target = target_path_str

    # 1. Defined symbols in target file
    target_symbols = [s for s in symbols if s.get("file") == rel_target]
    defined_symbol_names = {s.get("name") for s in target_symbols if s.get("name")}

    # 2. Downstream Callers (files calling target_symbols)
    downstream_callers = []
    if defined_symbol_names:
        for s in symbols:
            if s.get("file") == rel_target:
                continue
            calls = s.get("calls", [])
            matched_calls = [c for c in calls if c in defined_symbol_names]
            if matched_calls:
                downstream_callers.append({
                    "file": s.get("file"),
                    "caller_symbol": s.get("name"),
                    "called_symbols": matched_calls,
                    "line": s.get("line")
                })

    # 3. Existing Helpers in codebase
    helper_suggestions = []
    for s in symbols:
        if s.get("file") != rel_target and s.get("kind") in ("function", "method"):
            name = s.get("name", "")
            if any(kw in name.lower() for kw in ["format", "parse", "validate", "filter", "transform", "fetch", "check", "clean"]):
                helper_suggestions.append(f"`{name}()` ({s.get('file')}:L{s.get('line')})")

    # Construct Markdown Report
    output = []
    output.append("### 🔍 [Pre-Hook Impact & Context Analysis]")
    output.append(f"**Target File:** `{rel_target}`")
    
    if target_symbols:
        symbol_list = ", ".join([f"`{s.get('name')}` ({s.get('kind')})" for s in target_symbols[:8]])
        output.append(f"- **Defined Symbols:** {symbol_list}")
    else:
        output.append("- **Defined Symbols:** None indexed (new or unparsed file)")

    if downstream_callers:
        output.append("\n⚠️ **Downstream Blast Radius (Dependent Callers):**")
        for dc in downstream_callers[:5]:
            output.append(f"  - `{dc['file']}` (line {dc['line']}): `{dc['caller_symbol']}()` calls {', '.join([f'`{c}`' for c in dc['called_symbols']])}")
        if len(downstream_callers) > 5:
            output.append(f"  - *...and {len(downstream_callers) - 5} more callers*")
    else:
        output.append("\n✅ **Downstream Blast Radius:** No direct external caller references found.")

    if helper_suggestions:
        output.append(f"\n💡 **Existing Helper Utilities Available:** {', '.join(helper_suggestions[:5])}")

    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Pre-Hook Impact Analyzer")
    parser.add_argument("--file", help="Target file path to analyze")
    parser.add_argument("--root", default="./", help="Repository root directory")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    symbols = load_code_graph(root_dir)

    target_file = args.file
    if not target_file:
        modified_files = get_git_modified_files(root_dir)
        if modified_files:
            target_file = modified_files[0]

    if target_file:
        report = analyze_target_file(target_file, root_dir, symbols)
        print(report)
    else:
        print("### 🔍 [Pre-Hook Impact Analysis]\nNo target file specified or modified.")

if __name__ == "__main__":
    main()
