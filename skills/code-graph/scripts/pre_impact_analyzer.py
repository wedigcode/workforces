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

def resolve_target_dir(
    root_arg: str = "./",
    target_dir_arg: Optional[str] = None,
    target_file_hint: Optional[str] = None
) -> Path:
    """
    Intelligently resolve the target codebase root path when running in a workforce or project repo.
    """
    root_path = Path(root_arg).resolve()

    # 1. Explicit CLI argument override (--target-dir or --project-root)
    if target_dir_arg:
        td = Path(target_dir_arg)
        if not td.is_absolute():
            td = (root_path / td).resolve()
        if td.exists():
            return td

    # 2. Environment variable overrides
    for env_var in ["WORKFORCE_TARGET_DIR", "TARGET_REPO_ROOT", "PROJECT_ROOT"]:
        env_val = os.getenv(env_var)
        if env_val:
            td = Path(env_val)
            if not td.is_absolute():
                td = (root_path / td).resolve()
            if td.exists():
                return td

    # 3. Read workforce configuration files (workrules.md, workstate.md)
    config_files = [
        root_path / "workforces" / "workrules.md",
        root_path / "workforces" / "workstate.md",
        root_path / "workrules.md",
        root_path / "workstate.md",
    ]
    for cfg in config_files:
        if cfg.exists():
            try:
                content = cfg.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    match = re.search(
                        r"^\s*(?:-\s*)?(?:target_dir|project_root|target_repo|repo_root|active_project)\s*:\s*[`'\"]?([^`'\"]+)[`'\"]?",
                        line,
                        re.IGNORECASE,
                    )
                    if match:
                        target_val = match.group(1).strip()
                        td = Path(target_val)
                        if not td.is_absolute():
                            td = (root_path / td).resolve()
                        if td.exists():
                            return td
            except Exception:
                pass

    # 4. Target file hint (e.g. apps/chcked/app/api/... or /path/to/apps/chcked/...)
    if target_file_hint:
        hint_path = Path(target_file_hint)
        if hint_path.is_absolute():
            try:
                rel_parts = hint_path.relative_to(root_path).parts
            except Exception:
                rel_parts = hint_path.parts
        else:
            rel_parts = hint_path.parts

        if len(rel_parts) >= 2 and rel_parts[0] in ("apps", "packages", "services", "projects"):
            cand = root_path / rel_parts[0] / rel_parts[1]
            if cand.exists():
                return cand

    # 5. Code presence auto-detection:
    # If root_path contains NO source code files, check subfolders like apps/*, packages/*, services/*, src/*
    source_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs", ".php", ".rb"}
    ignore_top_dirs = {".git", ".agents", ".grok", ".claude", ".github", "workforces", "teams", "workflows", "skills", "rules", "docs", "plugins", "node_modules", "vendor", "__pycache__"}
    
    has_top_level_code = False
    for root, dirs, files in os.walk(root_path):
        rel_to_root = Path(root).relative_to(root_path)
        if any(part in ignore_top_dirs for part in rel_to_root.parts):
            dirs[:] = []
            continue
        for file in files:
            if Path(file).suffix.lower() in source_exts:
                has_top_level_code = True
                break
        if has_top_level_code:
            break

    if not has_top_level_code:
        for parent_sub in ("apps", "packages", "services", "src", "projects"):
            sub_dir = root_path / parent_sub
            if sub_dir.exists() and sub_dir.is_dir():
                for child in sub_dir.iterdir():
                    if child.is_dir() and not child.name.startswith("."):
                        return child

    return root_path


def load_code_graph(root_dir: Path, target_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load or generate code-graph.json symbols."""
    candidate_paths = []
    if target_dir:
        candidate_paths.extend([
            target_dir / "workforces" / "code-graph.json",
            target_dir / "code-graph.json"
        ])
    candidate_paths.extend([
        root_dir / "workforces" / "code-graph.json",
        root_dir / "code-graph.json"
    ])
    
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root_dir, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            git_root = Path(res.stdout.strip())
            candidate_paths.extend([
                git_root / "workforces" / "code-graph.json",
                git_root / "code-graph.json"
            ])
    except Exception:
        pass

    for graph_path in candidate_paths:
        if graph_path.exists():
            try:
                data = json.loads(graph_path.read_text(encoding="utf-8"))
                symbols = data.get("symbols", [])
                if symbols:
                    return symbols
            except Exception:
                pass

    # Fallback to invoking graph_indexer script if available
    indexer_script = root_dir / "skills" / "code-graph" / "scripts" / "graph_indexer.py"
    if not indexer_script.exists():
        indexer_script = root_dir / ".agents" / "skills" / "code-graph" / "scripts" / "graph_indexer.py"

    if indexer_script.exists():
        try:
            cmd = [sys.executable, str(indexer_script), "--scan", str(target_dir or root_dir)]
            subprocess.run(cmd, capture_output=True, timeout=10)
            return load_code_graph(root_dir, target_dir)
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
    parser.add_argument("--target-dir", help="Target project codebase directory")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    target_file = args.file
    target_dir = resolve_target_dir(root_arg=args.root, target_dir_arg=args.target_dir, target_file_hint=target_file)
    
    symbols = load_code_graph(root_dir, target_dir)

    if not target_file:
        modified_files = get_git_modified_files(target_dir)
        if modified_files:
            target_file = modified_files[0]

    if target_file:
        report = analyze_target_file(target_file, target_dir, symbols)
        print(report)
    else:
        print(f"### 🔍 [Pre-Hook Impact Analysis]\nNo target file specified or modified in `{target_dir}`.")

if __name__ == "__main__":
    main()

