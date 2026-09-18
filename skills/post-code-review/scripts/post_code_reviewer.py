#!/usr/bin/env python3
"""
Post-Hook Whole-Codebase Code Reviewer for Workforces
Zero external dependencies (Python 3 standard library: ast, re, json, pathlib, argparse, subprocess, datetime).

Fires on post_tool_call and pre-handoff quality gates.
Audits git diffs and code-graph relationships for:
1. PR-style review verification form ([x] DRY, [x] <= 35 lines, [x] method scoping, [x] simplicity, [x] maintainability)
2. AI pushback on skipped coding principles & candidate issue logging
3. Persistent 3rd-party security bypass caching with weekly retry intervals
4. Quality triad execution (unit tests, static analysis/type checks, linters)
"""

import argparse
import ast
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

IGNORE_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".agents", ".worktrees"}

def is_test_file(path_str: str) -> bool:
    """Determine if a file path belongs to a test suite or test specification."""
    if not path_str or path_str == "unknown":
        return False
    normalized = path_str.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    test_dirs = {"tests", "test", "__tests__", "spec", "specs"}
    if any(p.lower() in test_dirs for p in parts[:-1]):
        return True
    orig_fname = parts[-1] if parts else normalized
    fname_lower = orig_fname.lower()
    if fname_lower.startswith(("test_", "spec_")):
        return True
    if orig_fname.endswith(("Test.php", "Tests.php", "TestCase.php", "Spec.php")):
        return True
    if re.search(r"[-._](?:test|spec)\.[a-zA-Z0-9]+$", orig_fname, re.IGNORECASE):
        return True
    return False

def _generate_untracked_diff(root_dir: Path) -> str:
    """Generate synthetic diff hunks for untracked files."""
    try:
        res = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root_dir, capture_output=True, text=True, timeout=5
        )
        if res.returncode != 0 or not res.stdout.strip():
            return ""
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] untracked diff notice: {err}\n")
        return ""

    hunks = []
    for rel_path in res.stdout.splitlines():
        rel_path = rel_path.strip()
        if not rel_path or any(part in IGNORE_DIRS for part in Path(rel_path).parts):
            continue
        full_path = root_dir / rel_path
        if not full_path.is_file() or full_path.stat().st_size > 1_000_000:
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            hunk = [f"diff --git a/{rel_path} b/{rel_path}", "--- /dev/null", f"+++ b/{rel_path}", f"@@ -0,0 +1,{len(lines)} @@"]
            hunk.extend([f"+{line}" for line in lines])
            hunks.append("\n".join(hunk))
        except Exception:
            continue
    return "\n".join(hunks)

def _git_stdout(root_dir: Path, *args: str) -> str:
    """Run a git command and return stripped stdout on success."""
    res = subprocess.run(["git", *args], cwd=root_dir, capture_output=True, text=True, timeout=5)
    if res.returncode != 0:
        return ""
    return res.stdout.strip()

def _find_branch_diff_base(root_dir: Path) -> str:
    """Find a reasonable base ref for committed branch diff review."""
    env_base = os.getenv("GITHUB_BASE_REF") or os.getenv("COPILOT_BASE_REF") or os.getenv("BASE_REF")
    ref_candidates = []
    if env_base:
        ref_candidates.extend([f"origin/{env_base}", env_base])
    ref_candidates.extend(["origin/main", "origin/master", "origin/trunk", "origin/develop"])

    remote_head = _git_stdout(root_dir, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if remote_head:
        ref_candidates.insert(0, remote_head)

    for ref in ref_candidates:
        if ref and _git_stdout(root_dir, "rev-parse", "--verify", ref):
            merge_base = _git_stdout(root_dir, "merge-base", "HEAD", ref)
            if merge_base:
                return merge_base

    return _git_stdout(root_dir, "rev-parse", "--verify", "HEAD~1")

def _get_branch_diff(root_dir: Path) -> str:
    """Extract committed branch diff against merge-base when working tree is clean."""
    base = _find_branch_diff_base(root_dir)
    if not base:
        return ""
    return _git_stdout(root_dir, "diff", base, "HEAD")

def _get_branch_modified_files(root_dir: Path) -> List[str]:
    """List committed files changed on the current branch when working tree is clean."""
    base = _find_branch_diff_base(root_dir)
    if not base:
        return []
    output = _git_stdout(root_dir, "diff", "--name-only", base, "HEAD")
    return [line for line in output.splitlines() if line]

def get_git_diff(root_dir: Path) -> str:
    """Extract current git diff (staged + unstaged + untracked changes)."""
    try:
        res = subprocess.run(["git", "diff", "HEAD"], cwd=root_dir, capture_output=True, text=True, timeout=5)
        res_status = subprocess.run(["git", "status", "--porcelain"], cwd=root_dir, capture_output=True, text=True, timeout=5)
        untracked = _generate_untracked_diff(root_dir)
        parts = [res.stdout, untracked, res_status.stdout]
        working_tree_diff = "\n".join(p for p in parts if p.strip())
        if working_tree_diff.strip():
            return working_tree_diff
        return _get_branch_diff(root_dir)
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] get_git_diff notice: {err}\n")
        return ""

def get_modified_files(root_dir: Path) -> List[str]:
    """Get list of modified/added files in git working tree."""
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=root_dir, capture_output=True, text=True, timeout=5)
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] get_modified_files notice: {err}\n")
        return []

    files = []
    for line in res.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1].split(" -> ")[-1])
    if files:
        return files
    return _get_branch_modified_files(root_dir)

def resolve_target_dir(root_arg: str = "./", target_dir_arg: Optional[str] = None) -> Path:
    """Resolve target project directory from args, env, or configuration."""
    root_path = Path(root_arg).resolve()

    if target_dir_arg:
        td = Path(target_dir_arg)
        if not td.is_absolute():
            td = (root_path / td).resolve()
        if td.exists():
            return td

    for env_var in ["WORKFORCE_TARGET_DIR", "TARGET_REPO_ROOT", "PROJECT_ROOT"]:
        env_val = os.getenv(env_var)
        if env_val:
            ev_p = Path(env_val)
            if not ev_p.is_absolute():
                ev_p = (root_path / ev_p).resolve()
            if ev_p.exists():
                return ev_p

    for fname in ["workforces/workrules.md", "workforces/workstate.md"]:
        s_file = root_path / fname
        if not s_file.exists():
            continue
        m = re.search(r"target_dir:\s*[\"']?([^\"'\n]+)[\"']?", s_file.read_text(encoding="utf-8", errors="ignore"))
        if m and Path(m.group(1)).resolve().exists():
            return Path(m.group(1)).resolve()

    return root_path

def load_code_graph(root_dir: Path, target_dir: Path) -> List[Dict[str, Any]]:
    """Load symbols from code-graph.json if available."""
    candidates = [
        target_dir / "workforces" / "code-graph.json",
        target_dir / "code-graph.json",
        root_dir / "workforces" / "code-graph.json",
        root_dir / "code-graph.json",
        target_dir / ".agents" / "workforces" / "code-graph.json"
    ]
    for graph_path in candidates:
        if not graph_path.exists():
            continue
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            return data.get("symbols", [])
        except Exception as err:
            sys.stderr.write(f"[post_code_reviewer] load_code_graph notice: {err}\n")
    return []

def audit_swallowed_errors(diff_text: str, modified_files: List[str], root_dir: Path) -> List[str]:
    """Check for empty catch/except blocks in code files, ignoring test and doc files."""
    issues = []
    curr = "unknown"
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr = line[6:].strip()
            continue
        if not curr.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".php")):
            continue
        if is_test_file(curr):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            if any(kw in code for kw in ["re.search", "r\"", "r'", "sys.stderr.write", "except\\s"]):
                continue
            if re.search(r"except\s*:\s*pass", code) or re.search(r"except\s+\w+\s*:\s*pass", code):
                issues.append("⚠️ **Swallowed Error (Python):** `except: pass` detected in diff. Rethrow or log with context.")
            elif re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", code):
                issues.append("⚠️ **Swallowed Error (JS/TS):** Empty `catch {}` block detected in diff. Rethrow or log with context.")
            elif re.search(r"\.catch\(\(\)\s*=>\s*\{\s*\}\)", code):
                issues.append("⚠️ **Swallowed Error (JS/TS):** Unhandled promise rejection `.catch(() => {})` detected in diff.")
    return issues

def audit_missing_tests(modified_files: List[str]) -> List[str]:
    """Check if implementation files were modified without accompanying test updates."""
    logic_files = [f for f in modified_files if f.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs")) and not is_test_file(f)]
    test_files = [f for f in modified_files if is_test_file(f)]
    if logic_files and not test_files:
        return [f"💡 **Missing Test Verification:** Modified code in `{logic_files[0]}` without corresponding test updates."]
    return []

def audit_contract_changes(modified_files: List[str], symbols: List[Dict[str, Any]], root_dir: Path) -> List[str]:
    """Check if modified symbols have downstream callers in other files."""
    issues = []
    if not symbols:
        return issues

    for mod_file in modified_files:
        for sym in [s for s in symbols if s.get("file") == mod_file]:
            sym_name = sym.get("name")
            if not sym_name or len(sym_name) < 3:
                continue
            callers = [f"`{o['file']}`:L{o['line']}" for o in symbols if o.get("file") != mod_file and sym_name in o.get("calls", [])]
            if callers:
                issues.append(f"⚠️ **Downstream Blast Radius:** `{sym_name}()` in `{mod_file}` has external callers: {', '.join(callers[:3])}.")
    return issues

def _get_added_lines_by_file(diff_text: str) -> Dict[str, List[str]]:
    """Parse git diff into a mapping of filename to added (+) lines."""
    lines_by_file: Dict[str, List[str]] = {}
    curr_file: Optional[str] = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr_file = line[6:].strip()
            lines_by_file.setdefault(curr_file, [])
        elif line.startswith("+") and not line.startswith("+++") and curr_file:
            lines_by_file[curr_file].append(line)
    return lines_by_file

def audit_class_helper_reuse(modified_files: List[str], diff_text: str, root_dir: Path) -> List[str]:
    """Check if new code in a file performs manual parsing while class helper exists."""
    issues = []
    helper_kws = ["convertNumber", "convert_number", "formatNumber", "format_number", "sanitize", "parseNumber", "toFloat"]
    added_by_file = _get_added_lines_by_file(diff_text)

    for rel_path in modified_files:
        full_path = root_dir / rel_path
        if not full_path.exists() or not rel_path.endswith((".php", ".ts", ".js", ".py")):
            continue
        if "post_code_reviewer" in rel_path or is_test_file(rel_path):
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            existing = [kw for kw in helper_kws if re.search(r"(?:def|function|\bpublic|\bprivate|\bprotected)\s+" + kw, content)]
            if not existing:
                continue
            diff_lines = added_by_file.get(rel_path, [])
            if not diff_lines:
                continue
            has_raw = any(re.search(r"preg_replace|str_replace|floatval|\(float\)|parseFloat|re\.sub", l) for l in diff_lines)
            if has_raw and not any(kw in l for kw in existing for l in diff_lines):
                helpers_str = ", ".join(f"`{h}`" for h in set(existing))
                issues.append(f"💡 **Class Helper Reuse:** Code in `{rel_path}` uses manual parsing when helper ({helpers_str}) exists.")
        except Exception as err:
            sys.stderr.write(f"[post_code_reviewer] audit_class_helper_reuse notice: {err}\n")
    return issues

# --- Security Bypass Cache & Weekly Retry Management ---

def get_security_bypass_path(target_dir: Path) -> Path:
    """Resolve security bypass JSON path."""
    p1 = target_dir / "workforces" / "memory" / "security-bypass.json"
    p2 = target_dir / ".agents" / "memory" / "security-bypass.json"
    return p1 if (target_dir / "workforces").exists() else (p2 if (target_dir / ".agents").exists() else p1)

def load_security_bypass_cache(target_dir: Path) -> Dict[str, Any]:
    """Load cached security bypass entries safely."""
    path = get_security_bypass_path(target_dir)
    if not path.exists():
        return {"bypasses": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("bypasses"), dict):
            return data
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] load_security_bypass_cache notice: {err}\n")
    return {"bypasses": {}}

def save_security_bypass_cache(target_dir: Path, cache_data: Dict[str, Any]) -> None:
    """Save security bypass entries to disk."""
    path = get_security_bypass_path(target_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] save_security_bypass_cache notice: {err}\n")

def find_bypass_entry(ecosystem: str, summary: str, bypasses: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]], bool]:
    """Find matching bypass entry and check if unexpired."""
    key = f"{ecosystem}:{summary.strip()}"
    now_dt = datetime.datetime.now()
    for k, v in bypasses.items():
        if v.get("ecosystem") == ecosystem and (k in key or key in k):
            try:
                is_expired = now_dt >= datetime.datetime.fromisoformat(v.get("next_retry", ""))
            except Exception:
                is_expired = True
            return k, v, is_expired
    return None, None, True

def attempt_remediation(ecosystem: str, target_dir: Path) -> bool:
    """Attempt automated remediation (e.g. npm audit fix). Return True if command succeeded."""
    if ecosystem == "npm" and shutil.which("npm"):
        try:
            res = subprocess.run(["npm", "audit", "fix"], cwd=target_dir, capture_output=True, text=True, timeout=30)
            return res.returncode == 0
        except Exception as err:
            sys.stderr.write(f"[post_code_reviewer] remediation attempt error: {err}\n")
    return False

def record_security_bypass(ecosystem: str, summary: str, bypasses: Dict[str, Any], target_dir: Path, cache: Dict[str, Any]) -> str:
    """Record unresolvable security failure to bypass cache for 7-day retry."""
    key = f"{ecosystem}:{summary.strip()}"
    now_dt = datetime.datetime.now()
    now_iso = now_dt.isoformat()
    retry_iso = (now_dt + datetime.timedelta(days=7)).isoformat()
    attempt_cmd = "npm audit fix" if ecosystem == "npm" else f"{ecosystem} automated fix"

    bypasses[key] = {
        "ecosystem": ecosystem, "summary": summary, "first_detected": now_iso,
        "last_tried": now_iso, "next_retry": retry_iso, "status": "bypassed",
        "attempt": attempt_cmd,
        "learnings": f"Remediation attempt ({attempt_cmd}) unable to resolve 3rd-party vulnerability; bypassed for 7 days."
    }
    save_security_bypass_cache(target_dir, cache)
    return f"⚠️ **Security Notice (3rd-Party Tool / Deprecation):** Fix attempted but `{summary}` unresolvable. Logged to bypass cache (weekly retry: {retry_iso})."

def handle_security_failure(ecosystem: str, summary: str, bypasses: Dict[str, Any], target_dir: Path, cache: Dict[str, Any]) -> str:
    """Process failure against weekly bypass cache with remediation attempt."""
    match_key, matched, is_expired = find_bypass_entry(ecosystem, summary, bypasses)
    now_dt = datetime.datetime.now()
    now_iso = now_dt.isoformat()
    retry_iso = (now_dt + datetime.timedelta(days=7)).isoformat()

    if matched and not is_expired:
        return f"ℹ️ **Security Bypass Active (Weekly Re-check):** `{summary}` bypassed (next retry: {matched.get('next_retry')})."

    if attempt_remediation(ecosystem, target_dir):
        if match_key:
            bypasses.pop(match_key, None)
            save_security_bypass_cache(target_dir, cache)
        return f"✅ **Security Remediation Succeeded:** Automated fix resolved `{summary}`. Returned to normal routine."

    if matched:
        matched["last_tried"] = now_iso
        matched["next_retry"] = retry_iso
        save_security_bypass_cache(target_dir, cache)
        return f"⚠️ **Security Notice (Weekly Re-try):** Re-attempted fix for `{summary}` after 7 days; upstream unpatched. Extended to {retry_iso}."

    return record_security_bypass(ecosystem, summary, bypasses, target_dir, cache)

def _parse_npm_audit_payload(raw_json: str) -> Dict[str, Any]:
    """Safely parse npm audit JSON output."""
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        idx1, idx2 = raw_json.find("{"), raw_json.rfind("}")
        if idx1 != -1 and idx2 != -1:
            return json.loads(raw_json[idx1:idx2 + 1])
        raise

def _process_npm_vulnerabilities(
    vulns: Dict[str, Any],
    bypasses: Dict[str, Any],
    target_dir: Path,
    cache: Dict[str, Any]
) -> List[str]:
    """Process vulnerabilities distinguishing direct (blocking) vs transitive (bypassed)."""
    issues = []
    for pkg, info in vulns.items():
        is_direct = info.get("isDirect", False) if isinstance(info, dict) else False
        severity = info.get("severity", "high") if isinstance(info, dict) else "high"
        summary = f"vulnerability in {pkg}"
        if is_direct:
            issues.append(
                f"❌ **Direct Security Vulnerability (npm):** Direct dependency `{pkg}` has {severity} vulnerability. Direct dependencies cannot be bypassed; update or replace `{pkg}`."
            )
        else:
            issues.append(handle_security_failure("npm", summary, bypasses, target_dir, cache))
    return issues

def _run_node_audit(touched: List[str], target_dir: Path, bypasses: Dict[str, Any], cache: Dict[str, Any]) -> List[str]:
    """Execute npm audit --json and process findings."""
    if not any(m.endswith(("package.json", "package-lock.json", "pnpm-lock.yaml")) for m in touched) or not shutil.which("npm"):
        return []
    try:
        res = subprocess.run(["npm", "audit", "--json"], cwd=target_dir, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return []
        data = _parse_npm_audit_payload(res.stdout or res.stderr)
        if "error" in data:
            err_msg = data["error"].get("summary") or data["error"].get("detail") or "npm audit error"
            return [f"❌ **Security Audit Failed (npm):** {err_msg}"]
        vulns = data.get("vulnerabilities", {})
        if not vulns:
            return []
        return _process_npm_vulnerabilities(vulns, bypasses, target_dir, cache)
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] npm audit notice: {err}\n")
        return [f"❌ **Security Audit Failed (npm):** {err}"]

def _run_python_audit(touched: List[str], target_dir: Path, bypasses: Dict[str, Any], cache: Dict[str, Any]) -> List[str]:
    """Execute pip-audit and process findings."""
    if not any(m.endswith(("requirements.txt", "poetry.lock")) for m in touched) or not shutil.which("pip-audit"):
        return []
    try:
        res = subprocess.run(["pip-audit"], cwd=target_dir, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            return [handle_security_failure("python", "pip-audit vulnerabilities", bypasses, target_dir, cache)]
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] pip-audit notice: {err}\n")
        return [f"❌ **Security Audit Failed (python):** {err}"]
    return []

def audit_dependency_security(modified_files: List[str], target_dir: Path) -> List[str]:
    """Audit modified package manifests with weekly 3rd-party bypass caching."""
    manifests = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "requirements.txt", "Pipfile.lock", "poetry.lock", "composer.json", "composer.lock"}
    touched = [f for f in modified_files if Path(f).name in manifests]
    if not touched:
        return []

    cache = load_security_bypass_cache(target_dir)
    bypasses = cache.setdefault("bypasses", {})
    return _run_node_audit(touched, target_dir, bypasses, cache) + _run_python_audit(touched, target_dir, bypasses, cache)

# --- PR Review Verification Form & Heuristic Checks ---

def _parse_hunk_line(line: str, curr_line: int, touched: Set[int]) -> int:
    """Process a single diff hunk line and update line tracking."""
    if line.startswith("+") and not line.startswith("+++"):
        touched.add(curr_line)
        return curr_line + 1
    if line.startswith("-") and not line.startswith("---"):
        return curr_line
    if line.startswith(" ") or line == "":
        return curr_line + 1
    return curr_line

def _get_touched_lines(diff_text: str) -> Dict[str, Set[int]]:
    """Parse git diff to extract specifically added line numbers per file."""
    lines_by_file: Dict[str, Set[int]] = {}
    curr_file: Optional[str] = None
    curr_line = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr_file = line[6:].strip()
            lines_by_file.setdefault(curr_file, set())
        elif line.startswith("@@ ") and curr_file:
            m = re.search(r"\+(\d+)", line)
            curr_line = int(m.group(1)) if m else 0
        elif curr_file and curr_line > 0:
            curr_line = _parse_hunk_line(line, curr_line, lines_by_file[curr_file])

    return lines_by_file

def _check_py_function_lengths(path: Path, rel: str, touched: Set[int], max_lines: int) -> Tuple[List[str], List[str]]:
    """Inspect Python AST for functions exceeding max_lines."""
    viols, cands = [], []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            length = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
            if length <= max_lines:
                continue
            func_range = set(range(node.lineno, getattr(node, "end_lineno", node.lineno) + 1))
            if (not touched) or bool(func_range.intersection(touched)):
                viols.append(f"Function `{node.name}()` in `{rel}`:L{node.lineno} is {length} lines (> {max_lines} limit).")
            else:
                cands.append(f"Pre-existing `{node.name}()` in `{rel}`:L{node.lineno} is {length} lines.")
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] AST parse notice: {err}\n")
    return viols, cands

def audit_function_length(diff_text: str, modified_files: List[str], target_dir: Path, max_lines: int = 35) -> Tuple[bool, List[str], List[str]]:
    """Check whether modified functions exceed max_lines limit."""
    touched_by_file = _get_touched_lines(diff_text)
    violations, candidates = [], []

    for rel in modified_files:
        if is_test_file(rel):
            continue
        full = target_dir / rel
        if full.exists() and rel.endswith(".py"):
            v, c = _check_py_function_lengths(full, rel, touched_by_file.get(rel, set()), max_lines)
            violations.extend(v)
            candidates.extend(c)

    return len(violations) == 0, violations, candidates

def _extract_added_functions(diff_text: str) -> List[str]:
    """Extract newly added function names from non-test file diff hunks."""
    curr, fns = "unknown", []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr = line[6:].strip()
        elif line.startswith("+") and not line.startswith("+++") and not is_test_file(curr):
            m = re.search(r"^\+\s*(?:def|(?:const|let|var|function))\s+([a-zA-Z_]\w*)", line)
            if m and not m.group(1).startswith("test_") and m.group(1) not in {"setUp", "tearDown", "main", "__init__"}:
                fns.append(m.group(1))
    return fns

def audit_dry_principles(diff_text: str, modified_files: List[str], symbols: List[Dict[str, Any]], target_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Check duplicate functions and class helper reuse against code graph."""
    violations = audit_class_helper_reuse(modified_files, diff_text, target_dir)
    candidates = []

    for fn in set(_extract_added_functions(diff_text)):
        matching = [s for s in symbols if s.get("name") == fn and s.get("file") not in modified_files and not is_test_file(s.get("file", ""))]
        if matching:
            violations.append(f"Function `{fn}()` matches existing symbol in `{matching[0].get('file')}`:L{matching[0].get('line')}.")

    return len(violations) == 0, violations, candidates

def audit_method_scoping(diff_text: str, modified_files: List[str], target_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Check for deeply nested control flow blocks (indent >= 16 spaces / 4 levels)."""
    violations = []
    curr = "unknown"
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr = line[6:].strip()
        elif line.startswith("+") and not line.startswith("+++"):
            if is_test_file(curr):
                continue
            stripped = line[1:].strip()
            indent = len(line[1:]) - len(line[1:].lstrip(" "))
            if indent >= 16 and any(stripped.startswith(kw) for kw in ["if ", "for ", "while ", "try:", "match "]):
                violations.append(f"Deeply nested control flow (indent depth >= 4) in `{curr}`: `{stripped[:35]}...`.")
    return len(violations) == 0, violations, []

def audit_simplicity_and_verbosity(diff_text: str, modified_files: List[str]) -> Tuple[bool, List[str], List[str]]:
    """Detect verbose anti-patterns like redundant ternary or boolean returns."""
    violations = []
    curr = "unknown"
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            curr = line[6:].strip()
            continue
        if is_test_file(curr):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            code = line[1:].strip()
            if code.startswith(("#", "//", "/*", "*", '"""', "'''")):
                continue
            if any(kw in code for kw in ["re.search", "r\"", "r'", "violations.append"]):
                continue
            if re.search(r"\?\s*true\s*:\s*false", code, re.IGNORECASE):
                violations.append(f"Redundant boolean ternary (`? true : false`) in `{code[:35]}`.")
            if re.search(r"if\s+.*:\s*return\s+True", code):
                violations.append(f"Verbose boolean conditional in `{code[:35]}`.")
    return len(violations) == 0, violations, []

def audit_code_maintainability(diff_text: str, modified_files: List[str], symbols: List[Dict[str, Any]], target_dir: Path) -> Tuple[bool, List[str], List[str]]:
    """Check maintainability: swallowed errors, caller blast radius, and test presence."""
    violations = audit_swallowed_errors(diff_text, modified_files, target_dir)
    candidates = audit_missing_tests(modified_files)
    blast_radius = audit_contract_changes(modified_files, symbols, target_dir)
    candidates.extend(blast_radius)
    return len(violations) == 0, violations, candidates

def evaluate_justification(justification: Optional[str]) -> Tuple[bool, str]:
    """Validate whether provided justification gives an acceptable technical reason."""
    if not justification or not justification.strip():
        return False, "No explanation provided."
    clean = justification.strip().lower()
    bad_reasons = {"none", "skip", "idk", "lazy", "pass", "todo", "no reason", "ignore", "n/a", "no"}
    if clean in bad_reasons or len(clean) < 10:
        return False, f"'{justification.strip()}' is not an acceptable technical justification."
    return True, justification.strip()

def extract_diff_justifications(diff_text: str) -> Dict[str, str]:
    """Extract in-line justifications from diff comments."""
    justs: Dict[str, str] = {}
    pattern = re.compile(r"^\+\s*(?:#|//|/\*|\*)\s*justification(?:\(([^)]+)\))?:\s*(.+)", re.IGNORECASE | re.MULTILINE)
    for match in pattern.finditer(diff_text):
        scope = (match.group(1) or "global").strip().lower()
        reason = match.group(2).strip().rstrip("*/").strip()
        justs[scope] = reason
    return justs

def find_criterion_justification(name: str, diff_justs: Dict[str, str], cli_just: Optional[str]) -> Optional[str]:
    """Resolve justification for a specific criterion."""
    if cli_just and cli_just.strip():
        if ":" in cli_just and cli_just.split(":", 1)[0].strip().lower() in name.lower():
            return cli_just.split(":", 1)[1].strip()
        return cli_just.strip()
    for scope, text in diff_justs.items():
        if scope in name.lower() or scope == "global":
            return text
    return None

def _eval_badge(
    ok: bool,
    label: str,
    viols: List[str],
    hint: str,
    diff_justs: Dict[str, str],
    cli_just: Optional[str]
) -> Tuple[str, bool, Optional[str]]:
    """Evaluate badge display and handle justified exceptions vs pushbacks."""
    if ok:
        return f"- [x] **{label}:** {hint}", True, None
    just_str = find_criterion_justification(label, diff_justs, cli_just)
    is_valid, reason = evaluate_justification(just_str)
    if is_valid:
        return f"- [x] **{label}:** [Justified: {reason}]", True, None
    pushback = f"Criterion '{label}' violated ({viols[0]}). Pushback: {reason}. Advisory recommendation: Review and refactor if beneficial."
    return f"- [ ] **{label}:** {viols[0]}", False, pushback

def _build_pr_checks_list(
    diff_text: str,
    modified_files: List[str],
    symbols: List[Dict[str, Any]],
    target_dir: Path
) -> Tuple[List[Tuple[bool, str, List[str], str]], List[str]]:
    """Audit diff against 5 PR criteria and return checklist definitions with candidates."""
    dry_ok, dry_v, dry_c = audit_dry_principles(diff_text, modified_files, symbols, target_dir)
    len_ok, len_v, len_c = audit_function_length(diff_text, modified_files, target_dir, max_lines=35)
    scop_ok, scop_v, scop_c = audit_method_scoping(diff_text, modified_files, target_dir)
    simp_ok, simp_v, simp_c = audit_simplicity_and_verbosity(diff_text, modified_files)
    maint_ok, maint_v, maint_c = audit_code_maintainability(diff_text, modified_files, symbols, target_dir)

    checks = [
        (dry_ok, "is it dry", dry_v, "Verified clean. No duplicate helper logic detected."),
        (len_ok, "no new code exceeds 35 lines", len_v, "All modified functions within line limits."),
        (scop_ok, "should any new code be in its own method", scop_v, "Method granularity is clean; no deeply nested blocks."),
        (simp_ok, "is any of it too verbose or can it be simplified", simp_v, "Clean, idiomatic expressions without redundant boilerplate."),
        (maint_ok, "code maintainability", maint_v, "Error propagation preserved, caller contracts intact.")
    ]
    return checks, dry_c + len_c + scop_c + simp_c + maint_c

def evaluate_pr_verification_form(
    diff_text: str,
    modified_files: List[str],
    symbols: List[Dict[str, Any]],
    target_dir: Path,
    justification: Optional[str] = None
) -> Tuple[str, bool, List[str], List[str]]:
    """Generate and evaluate the 5-point PR-style verification form with pushback."""
    checks, candidates = _build_pr_checks_list(diff_text, modified_files, symbols, target_dir)
    diff_justs = extract_diff_justifications(diff_text)
    badges, pushbacks = [], []
    all_passed = True

    for ok, label, viols, hint in checks:
        line, passed, pushback = _eval_badge(ok, label, viols, hint, diff_justs, justification)
        badges.append(line)
        if not passed:
            all_passed = False
            if pushback:
                pushbacks.append(pushback)

    lines = ["### 📋 PR-Style Code Review Verification Form"] + badges
    return "\n".join(lines), all_passed, pushbacks, candidates

# --- Quality Toolchain Detection & Execution ---

def _detect_node_commands(target_dir: Path, commands: Dict[str, str]) -> None:
    """Detect Node/TS test, lint, and typecheck commands."""
    pkg_json = target_dir / "package.json"
    if not pkg_json.exists():
        return
    try:
        s = json.loads(pkg_json.read_text(encoding="utf-8")).get("scripts", {})
        if "typecheck" in s or "type-check" in s or "tsc" in s:
            commands["typecheck"] = "npm run " + next(k for k in ["typecheck", "type-check", "tsc"] if k in s)
        elif (target_dir / "tsconfig.json").exists() and shutil.which("npx"):
            commands["typecheck"] = "npx --no-install tsc --noEmit"
        if "lint" in s:
            commands["lint"] = "npm run lint"
        elif (target_dir / "biome.json").exists() and shutil.which("npx"):
            commands["lint"] = "npx --no-install @biomejs/biome check ."
        if "test" in s and "no test specified" not in str(s.get("test", "")).lower():
            commands["test"] = "npm test"
    except Exception as err:
        sys.stderr.write(f"[post_code_reviewer] node command detection notice: {err}\n")

def _detect_python_commands(target_dir: Path, commands: Dict[str, str]) -> None:
    """Detect Python test, lint, and typecheck commands."""
    has_py = any(target_dir.glob("*.py")) or (target_dir / "requirements.txt").exists() or (target_dir / "pyproject.toml").exists()
    if not has_py and not (target_dir / "tests").is_dir():
        return
    if "test" not in commands:
        if (target_dir / "pytest.ini").exists() or (target_dir / "tests").is_dir():
            if shutil.which("pytest"):
                commands["test"] = "pytest"
            elif any((target_dir / "tests").glob("test_*.py")):
                commands["test"] = "python3 -m unittest discover -s tests -p 'test_*.py'"
    if "lint" not in commands and shutil.which("ruff"):
        commands["lint"] = "ruff check ."
    if "typecheck" not in commands and ((target_dir / "mypy.ini").exists() or (target_dir / ".mypy.ini").exists() or (target_dir / "pyproject.toml").exists()):
        if shutil.which("mypy"):
            commands["typecheck"] = "mypy ."

def _detect_php_commands(target_dir: Path, commands: Dict[str, str]) -> None:
    """Detect PHP test, typecheck, and lint commands."""
    if not (target_dir / "composer.json").exists():
        return
    vbin = target_dir / "vendor" / "bin"
    if (vbin / "pest").exists():
        commands.setdefault("test", "./vendor/bin/pest")
    elif (vbin / "phpunit").exists():
        commands.setdefault("test", "./vendor/bin/phpunit")
    if (vbin / "phpstan").exists():
        commands.setdefault("typecheck", "./vendor/bin/phpstan analyse")
    if (vbin / "pint").exists():
        commands.setdefault("lint", "./vendor/bin/pint --test")

def _detect_rust_commands(target_dir: Path, commands: Dict[str, str]) -> None:
    """Detect Rust test, typecheck, and lint commands."""
    if (target_dir / "Cargo.toml").exists() and shutil.which("cargo"):
        commands.setdefault("test", "cargo test")
        commands.setdefault("typecheck", "cargo check")
        commands.setdefault("lint", "cargo clippy -- -D warnings")

def _detect_go_commands(target_dir: Path, commands: Dict[str, str]) -> None:
    """Detect Go test, typecheck (vet), and lint commands."""
    if (target_dir / "go.mod").exists() and shutil.which("go"):
        commands.setdefault("test", "go test ./...")
        commands.setdefault("typecheck", "go vet ./...")
        if shutil.which("golangci-lint"):
            commands.setdefault("lint", "golangci-lint run")

def detect_quality_commands(target_dir: Path) -> Dict[str, str]:
    """Auto-detect configured test, static analysis, and linter commands across stacks."""
    commands: Dict[str, str] = {}
    _detect_node_commands(target_dir, commands)
    _detect_python_commands(target_dir, commands)
    _detect_php_commands(target_dir, commands)
    _detect_rust_commands(target_dir, commands)
    _detect_go_commands(target_dir, commands)
    return commands

def _execute_single_check(target_dir: Path, check_type: str, cmd: str) -> Optional[str]:
    """Execute a single quality gate command and return error message if failed."""
    try:
        res = subprocess.run(cmd, shell=True, cwd=target_dir, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            tail = "\n".join([l for l in (res.stderr + "\n" + res.stdout).splitlines() if l.strip()][-6:])
            return f"❌ **Quality Gate Failed ({check_type.title()}):** `{cmd}` failed:\n```\n{tail}\n```"
    except Exception as e:
        return f"❌ **Quality Gate Error ({check_type.title()}):** `{cmd}` failed: {e}"
    return None

def run_quality_gate_checks(target_dir: Path, commands: Dict[str, str]) -> Tuple[List[str], bool]:
    """Execute detected quality triad checks."""
    issues = []
    all_passed = True
    for check_type in ["typecheck", "lint", "test"]:
        if check_type in commands:
            err_msg = _execute_single_check(target_dir, check_type, commands[check_type])
            if err_msg:
                all_passed = False
                issues.append(err_msg)
    return issues, all_passed

def _format_candidate_backlog_items(candidates: List[str], target_dir: Optional[Path] = None) -> List[str]:
    """Format candidate backlog items with suggested reporting commands."""
    lines = ["\n### 💡 Discovered Code Issues (Candidate Backlog Items)"]
    if target_dir:
        use_dot_agents = (target_dir / ".agents").exists() or not (target_dir / "skills").exists()
    else:
        use_dot_agents = (Path.cwd() / ".agents").exists() or not (Path.cwd() / "skills").exists()
    script_path = ".agents/skills/task-tracker/scripts/report-task.py" if use_dot_agents else "skills/task-tracker/scripts/report-task.py"
    for c in set(candidates[:6]):
        clean_title = re.sub(r"[^\w\s-]", "", c)[:50].strip()
        lines.append(f"- {c}\n  👉 Track via: `python3 {script_path} --title \"{clean_title}\" --type dev --priority P2`")
    return lines

def _build_review_report_output(
    target_dir: Path,
    modified_files: List[str],
    form_md: str,
    pushbacks: List[str],
    all_issues: List[str],
    candidates: List[str],
    has_blockers: bool
) -> str:
    """Format final review and quality gate markdown output."""
    output = [
        "### 🔍 [Post-Hook Code Review & Quality Gate Feedback]",
        f"**Target Repository Audited:** `{target_dir}`",
        f"**Modified Files Audited:** {len(modified_files)} file(s)\n",
        form_md
    ]
    if pushbacks:
        output.extend(["\n⚠️ **ADVISORY REVIEW FEEDBACK — Coding Principles & Heuristics:**", "The following heuristic checks surfaced recommendations:"])
        output.extend([f"- {p}" for p in pushbacks[:6]])
        output.append("\n👉 **Advisory Guidance:** Review recommendations and refactor if beneficial. Checklist heuristics are advisory and non-blocking.")

    if all_issues:
        output.extend(["\n**Actionable Items Flagged:**"] + [f"- {i}" for i in all_issues[:10]])
        if has_blockers:
            output.append("\n🛑 **PRE-HANDOFF BLOCKER:** Quality gates failed (test, lint, typecheck, or security errors). You MUST resolve all errors before handoff.")
    elif not pushbacks:
        output.append("\n✅ **Review & Quality Gate Passed:** All design principles, tests, and verification checks clean.")

    if candidates:
        output.extend(_format_candidate_backlog_items(candidates, target_dir))

    return "\n".join(output)

def run_code_review_gate(
    root_dir: Path,
    target_dir_arg: Optional[str] = None,
    run_checks: bool = False,
    strict: bool = False,
    justification: Optional[str] = None
) -> Tuple[str, bool]:
    """Execute complete post-code review audit, PR verification form, and quality gates."""
    target_dir = resolve_target_dir(root_arg=str(root_dir), target_dir_arg=target_dir_arg)
    modified_files = get_modified_files(target_dir)
    diff_text = get_git_diff(target_dir)
    symbols = load_code_graph(root_dir, target_dir)

    if not modified_files and not diff_text.strip() and not run_checks:
        return (f"### 🔍 [Post-Hook Code Review]\n✅ No modified files detected in target repo `{target_dir}`.", True)

    just = justification or os.getenv("WORKFORCE_REVIEW_JUSTIFICATION")
    form_md, _pr_passed, pushbacks, candidates = evaluate_pr_verification_form(diff_text, modified_files, symbols, target_dir, justification=just)
    sec_issues = audit_dependency_security(modified_files, target_dir)
    detected_cmds = detect_quality_commands(target_dir)

    all_issues = list(sec_issues)
    if run_checks and detected_cmds:
        q_issues, _q_passed = run_quality_gate_checks(target_dir, detected_cmds)
        all_issues.extend(q_issues)

    has_blockers = any("❌" in i for i in all_issues)
    overall_passed = not has_blockers

    report = _build_review_report_output(target_dir, modified_files, form_md, pushbacks, all_issues, candidates, has_blockers)
    return report, overall_passed

def run_code_reviewer(root_dir: Path, target_dir_arg: Optional[str] = None, run_checks: bool = False) -> str:
    """Backward-compatible entry point returning markdown report string."""
    report, _ = run_code_review_gate(root_dir, target_dir_arg=target_dir_arg, run_checks=run_checks)
    return report

def main():
    parser = argparse.ArgumentParser(description="Post-Hook Whole-Codebase Code Reviewer & Quality Gate")
    parser.add_argument("--root", default="./", help="Repository root directory")
    parser.add_argument("--target-dir", help="Target project codebase directory")
    parser.add_argument("--run-checks", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true", default=False)
    parser.add_argument("--justification", "-j", help="Documented technical justification for skipped principles")
    args = parser.parse_args()

    run_checks = args.run_checks or (os.getenv("WORKFORCE_RUN_CHECKS", "0") in ("1", "true", "True"))
    report, passed = run_code_review_gate(
        Path(args.root).resolve(),
        target_dir_arg=args.target_dir,
        run_checks=run_checks,
        strict=args.strict,
        justification=args.justification
    )
    print(report)
    if args.strict and not passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
