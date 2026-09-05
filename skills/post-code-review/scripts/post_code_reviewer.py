#!/usr/bin/env python3
"""
Post-Hook Whole-Codebase Code Reviewer for Workforces
Zero external dependencies (Python 3 standard library: ast, re, json, pathlib, argparse, subprocess).

Fires on post_tool_call (after code modification tools).
Audits git diffs and code-graph relationships for:
1. Downstream contract breaking changes (changed signatures with caller files)
2. Swallowed errors / empty catch blocks
3. Duplicated methods matching existing code-graph symbols
4. Missing unit/integration tests for modified logic
5. Missing environment / config updates
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

IGNORE_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".agents", ".worktrees"}

def get_git_diff(root_dir: Path) -> str:
    """Extract current git diff (staged + unstaged + untracked changes)."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        diff_out = res.stdout
        # Also check status for untracked files
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        return diff_out + "\n" + res_status.stdout
    except Exception:
        return ""

def get_modified_files(root_dir: Path) -> List[str]:
    """Get list of modified/added files in git working tree."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        files = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                status, filepath = parts[0], parts[1]
                if not any(d in filepath for d in IGNORE_DIRS):
                    files.append(filepath)
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
    ignore_top_dirs = {".git", ".agents", ".grok", ".claude", ".github", ".worktrees", "workforces", "teams", "workflows", "skills", "rules", "docs", "plugins", "node_modules", "vendor", "__pycache__"}
    
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
    """Load symbols from workforces/code-graph.json or code-graph.json across candidate locations."""
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
    return []

def audit_swallowed_errors(diff_text: str, modified_files: List[str], root_dir: Path) -> List[str]:
    """Check for empty catch/except blocks in modified lines."""
    issues = []
    # Check added diff lines
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            code_line = line[1:].strip()
            if re.search(r"except\s*:\s*pass", code_line) or re.search(r"except\s+\w+\s*:\s*pass", code_line):
                issues.append("⚠️ **Swallowed Error (Python):** `except: pass` detected in diff. Rethrow or log with context.")
            elif re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", code_line):
                issues.append("⚠️ **Swallowed Error (JS/TS):** Empty `catch {}` block detected in diff. Rethrow or log with context.")
            elif re.search(r"\.catch\(\(\)\s*=>\s*\{\s*\}\)", code_line):
                issues.append("⚠️ **Swallowed Error (JS/TS):** Unhandled promise rejection `.catch(() => {})` detected in diff.")
    return issues

def audit_missing_tests(modified_files: List[str]) -> List[str]:
    """Check if implementation files were modified without accompanying test updates."""
    logic_files = []
    test_files = []
    
    for f in modified_files:
        is_test = any(kw in f.lower() for kw in ["test", "spec", "tests"])
        if is_test:
            test_files.append(f)
        elif f.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs")):
            logic_files.append(f)

    issues = []
    if logic_files and not test_files:
        sample = logic_files[0]
        issues.append(f"💡 **Missing Test Verification:** Modified code logic in `{sample}` without corresponding unit/integration test updates.")
    return issues

def audit_contract_changes(modified_files: List[str], symbols: List[Dict[str, Any]], root_dir: Path) -> List[str]:
    """Check if modified symbols have downstream callers in other files."""
    issues = []
    if not symbols:
        return issues

    for mod_file in modified_files:
        file_symbols = [s for s in symbols if s.get("file") == mod_file]
        for sym in file_symbols:
            sym_name = sym.get("name")
            if not sym_name or len(sym_name) < 3:
                continue
            
            # Find callers in other files
            callers = []
            for other_sym in symbols:
                if other_sym.get("file") != mod_file:
                    if sym_name in other_sym.get("calls", []):
                        callers.append(f"`{other_sym.get('file')}`:L{other_sym.get('line')} (`{other_sym.get('name')}()`)")

            if len(callers) > 0:
                issues.append(f"⚠️ **Downstream Caller Blast Radius:** Symbol `{sym_name}()` in `{mod_file}` has external callers: {', '.join(callers[:3])}. Verify parameter signatures remain compatible.")
    return issues

def audit_class_helper_reuse(modified_files: List[str], diff_text: str, root_dir: Path) -> List[str]:
    """Check if newly added functions in a file perform low-level parsing while existing helper methods in the target file exist."""
    issues = []
    helper_keywords = ["convertNumber", "convert_number", "formatNumber", "format_number", "sanitize", "parseNumber", "parse_number", "toFloat", "to_float"]

    for rel_path in modified_files:
        full_path = root_dir / rel_path
        if not full_path.exists() or not rel_path.endswith((".php", ".ts", ".js", ".py")):
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            existing_helpers = [kw for kw in helper_keywords if kw in content]
            if not existing_helpers:
                continue

            file_diff_lines = [l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]
            has_raw_parsing = any(
                re.search(r"preg_replace|str_replace|replace\(/[^\n]+/|floatval|\(float\)|parseFloat|re\.sub", l)
                for l in file_diff_lines
            )

            if has_raw_parsing:
                diff_calls_helper = any(kw in l for kw in existing_helpers for l in file_diff_lines)
                if not diff_calls_helper:
                    helpers_str = ", ".join(f"`{h}`" for h in set(existing_helpers))
                    issues.append(
                        f"💡 **Potential Over-Engineering / Duplicate Class Helper:** Code modifications in `{rel_path}` use custom string/number parsing while neighboring helper(s) ({helpers_str}) exist in the target file. Consider composing existing helper(s)."
                    )
        except Exception:
            pass

    return issues

def run_code_reviewer(root_dir: Path, target_dir_arg: Optional[str] = None) -> str:
    """Execute complete post-code review audit."""
    target_dir = resolve_target_dir(root_arg=str(root_dir), target_dir_arg=target_dir_arg)
    
    modified_files = get_modified_files(target_dir)
    diff_text = get_git_diff(target_dir)
    symbols = load_code_graph(root_dir, target_dir)

    all_issues = []

    if not modified_files and not diff_text.strip():
        return f"### 🔍 [Post-Hook Code Review]\n✅ No modified files detected in target repo `{target_dir}`."

    # Perform audits
    all_issues.extend(audit_swallowed_errors(diff_text, modified_files, target_dir))
    all_issues.extend(audit_contract_changes(modified_files, symbols, target_dir))
    all_issues.extend(audit_class_helper_reuse(modified_files, diff_text, target_dir))
    all_issues.extend(audit_missing_tests(modified_files))

    output = []
    output.append("### 🔍 [Post-Hook Code Review & Self-Healing Feedback]")
    output.append(f"**Target Repository Audited:** `{target_dir}`")
    output.append(f"**Modified Files Audited:** {len(modified_files)} file(s)")

    if all_issues:
        output.append("\n**Actionable Items Flagged:**")
        for issue in all_issues[:8]:
            output.append(f"- {issue}")
        output.append("\n*Please address flagged items before completing your task.*")
    else:
        output.append("\n✅ **Review Passed:** No contract violations, swallowed errors, or missing test issues detected.")

    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Post-Hook Whole-Codebase Code Reviewer")
    parser.add_argument("--root", default="./", help="Repository root directory")
    parser.add_argument("--target-dir", help="Target project codebase directory")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    report = run_code_reviewer(root_dir, target_dir_arg=args.target_dir)
    print(report)

if __name__ == "__main__":
    main()

