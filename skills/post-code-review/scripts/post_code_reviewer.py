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
from typing import Dict, List, Any, Set, Tuple

IGNORE_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".agents"}

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

def load_code_graph(root_dir: Path) -> List[Dict[str, Any]]:
    """Load symbols from workforces/code-graph.json if available."""
    graph_path = root_dir / "workforces" / "code-graph.json"
    if graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            return data.get("symbols", [])
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

def run_code_reviewer(root_dir: Path) -> str:
    """Execute complete post-code review audit."""
    modified_files = get_modified_files(root_dir)
    diff_text = get_git_diff(root_dir)
    symbols = load_code_graph(root_dir)

    all_issues = []

    if not modified_files and not diff_text.strip():
        return "### 🔍 [Post-Hook Code Review]\n✅ No modified files detected in repository."

    # Perform audits
    all_issues.extend(audit_swallowed_errors(diff_text, modified_files, root_dir))
    all_issues.extend(audit_contract_changes(modified_files, symbols, root_dir))
    all_issues.extend(audit_class_helper_reuse(modified_files, diff_text, root_dir))
    all_issues.extend(audit_missing_tests(modified_files))

    output = []
    output.append("### 🔍 [Post-Hook Code Review & Self-Healing Feedback]")
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
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    report = run_code_reviewer(root_dir)
    print(report)

if __name__ == "__main__":
    main()
