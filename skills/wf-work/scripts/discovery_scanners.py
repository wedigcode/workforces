#!/usr/bin/env python3
"""
Read-Only Discovery Scanners for `/wf-work`

Provides bounded, zero-dependency discovery passes for:
- `docs`: non-destructive `<repo>/docs/` OKF scaffolding + stray/spec hygiene
- `debt`: `TODO`/`FIXME`/`HACK`/`XXX` harvesting & giant file rolling-slice candidates
- `security`: exposed secrets, `"production"` defaults, unsafe sinks, IaC parity gaps
- `design`: missing `alt` / ARIA roles, missing viewport meta, CSS `!important`
- `optimization`: sequential `await` / queries in loops, unbounded SQL, blocking I/O
- `housekeeping`: unpinned deps, runtime version drift, missing `.env.example` keys
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple


SCAN_IGNORE_DIRS: FrozenSet[str] = frozenset({
    ".git", ".worktrees", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "dist", "build", ".next", "target", "workforces",
})
CODE_EXTS: FrozenSet[str] = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs", ".java", ".rb"})
SEC_EXTS: FrozenSet[str] = CODE_EXTS | frozenset({".yaml", ".yml", ".toml", ".env", ".json", ".sh"})
UI_EXTS: FrozenSet[str] = frozenset({".tsx", ".jsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss"})

TODO_RE = re.compile(r"(?:#|//|/\*|\*)\s*\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.*)", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?:api[_-]?key|secret[_-]?key|password|auth[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_/+=-]{16,}['\"])"
)
PROD_FALLBACK_CALL_RE = re.compile(
    r"(?i)(?:os\.getenv|os\.environ\.get|getenv|env)\s*\(\s*['\"][A-Z0-9_]+['\"]\s*,\s*['\"](?:prod|production|live)['\"]\s*\)"
)
PROD_FALLBACK_OR_RE = re.compile(
    r"(?i)(?:process\.env\.[A-Z0-9_]+|os\.getenv\([^)]+\)|\$_ENV\[[^\]]+\]|getenv\([^)]+\))\s*(?:\|\||\?\?|\bor\b|\?:)\s*['\"](?:prod|production|live)['\"]"
)
SINK_RE = re.compile(r"(?:shell\s*=\s*True|\beval\s*\(|innerHTML\s*=|dangerouslySetInnerHTML)")
IMG_NO_ALT_RE = re.compile(r"<img\b(?![^>]*\balt=)[^>]*>", re.IGNORECASE)
CLICKABLE_DIV_RE = re.compile(r"<(?:div|span)\b[^>]*\bonClick\b(?![^>]*\brole=)[^>]*>", re.IGNORECASE)
LOOP_RE = re.compile(r"^\s*(?:for\b|while\b)|\.(?:forEach|map)\s*\(")
LOOP_AWAIT_QUERY_RE = re.compile(r"(?:\bawait\b|\bfetch\s*\(|axios\.|requests\.|\.(?:query|execute)\s*\()")
SELECT_STAR_RE = re.compile(r"\bSELECT\s+\*\s+FROM\b", re.IGNORECASE)
ENV_LOOKUP_RE = re.compile(r"(?:process\.env\.([A-Z][A-Z0-9_]{2,})|os\.(?:getenv|environ\.get)\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"])")
_BUILTIN_ENV_VARS = frozenset({"PATH", "HOME", "PWD", "USER", "SHELL", "TERM", "LANG", "TMPDIR", "CI", "NODE_ENV", "PYTHONPATH", "AWS_REGION"})


def _is_test_relpath(rel: str) -> bool:
    """Return True if repo-relative POSIX path points to a test fixture or test directory."""
    parts = rel.lower().split("/")
    base = parts[-1]
    return any(p in ("tests", "test", "__tests__", "spec") for p in parts[:-1]) or base.startswith("test_") or ".test." in base or ".spec." in base


def _iter_repo_files(
    repo_root: Path, exts: FrozenSet[str], max_files: int = 200, include_tests: bool = False
) -> Iterator[Tuple[Path, str]]:
    """Yield `(path, rel_posix)` for bounded repository scanning."""
    count = 0
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in SCAN_IGNORE_DIRS and not d.startswith("."))
        for fname in sorted(files):
            if Path(fname).suffix.lower() not in exts:
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(repo_root).as_posix()
            if not include_tests and _is_test_relpath(rel):
                continue
            yield fpath, rel
            count += 1
            if count >= max_files:
                return


def _read_lines(fpath: Path) -> List[str]:
    """Read file lines safely, returning empty list on OS error."""
    try:
        return fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def _format_doc_rec_candidate(rec: Dict[str, Any], prefix: str, repo_label: str) -> Dict[str, Any]:
    """Format a ranked module documentation gap as a PM inbox recommendation."""
    mod = str(rec.get("module") or ".")
    card_path = str(rec.get("card_path") or "docs/index.md")
    status = str(rec.get("doc_status") or "missing")
    callers = int(rec.get("inbound_callers") or 0)
    undoc = int(rec.get("undocumented_symbols") or 0)
    sym_total = int(rec.get("symbol_count") or 0)
    env_vars = rec.get("env_vars") or []
    tests = rec.get("test_files") or []
    undoc_names = rec.get("undocumented_symbol_names") or []
    caller_files = rec.get("caller_files") or []

    facts = [
        f"Module `{mod}` (`doc_status: {status}`, {rec.get('file_count', 0)} files, {rec.get('total_lines', 0)} lines).",
        f"Blast radius: {callers} external caller file(s)" + (f" (e.g. {', '.join(f'`{c}`' for c in caller_files[:3])})." if caller_files else "."),
        f"Inline docblocks: {undoc}/{sym_total} public symbol(s) undocumented" + (f" (e.g. {', '.join(f'`{n}`' for n in undoc_names[:5])})." if undoc_names else "."),
    ]
    if env_vars:
        facts.append(f"Env vars: {', '.join(f'`{v}`' for v in env_vars[:6])}.")
    if tests:
        facts.append(f"Tests: {', '.join(f'`{t}`' for t in tests[:4])}.")

    return {
        "title": f"{prefix}Document module `{mod}`: OKF architecture card + inline docblocks",
        "type": "docs",
        "severity": str(rec.get("severity") or "P2"),
        "file": mod,
        "repo": repo_label,
        "description": " ".join(facts),
        "suggested_action": (
            f"Promote via `report-task.py --promote-issue <issue> --approve`. Then: "
            f"(1) author/enrich `{card_path}` (`doc_status: documented`, refactor-ready OKF schema) and refresh `docs/index.md` via `scaffold_repo_okf.py --scan`, "
            f"(2) add concise 2-4 line module/class docblocks, public docstrings, and inline 'why' comments in `{mod}`, "
            f"and (3) run `post_code_reviewer.py --run-checks --strict` and open a Draft PR."
        ),
    }


def _build_docs_issue_candidates(hygiene: Dict[str, Any], repo_label: str = "") -> List[Dict[str, Any]]:
    """Convert doc recommendations, stale cards, and hygiene findings into PM inbox candidates."""
    prefix = f"[{repo_label}] " if repo_label else ""
    protected_dirty = set(hygiene.get("protected_dirty_files", []))
    candidates: List[Dict[str, Any]] = []

    for rec in hygiene.get("doc_recommendations", [])[:3]:
        candidates.append(_format_doc_rec_candidate(rec, prefix, repo_label))

    for stale in hygiene.get("stale_cards", [])[:2]:
        rel_card = stale.get("file", "")
        if not rel_card:
            continue
        candidates.append({
            "title": f"{prefix}Refresh stale architecture doc: {rel_card}",
            "type": "docs",
            "severity": "P2",
            "file": rel_card,
            "repo": repo_label,
            "description": f"`{rel_card}` is out of sync ({stale.get('reason', 'drift detected')}).",
            "suggested_action": "Verify `affected_files:` globs, refresh `last_verified_commit` and `## Constraints, Invariants & Gotchas`, and run `scaffold_repo_okf.py --scan`.",
        })

    for fname in hygiene.get("stray_root_files", [])[:3]:
        dirty_note = f" `{fname}` has uncommitted or untracked changes and MUST NOT be deleted or overwritten without explicit user consent." if fname in protected_dirty else ""
        candidates.append({
            "title": f"{prefix}Review non-standard root file placement: {fname}", "type": "chore", "severity": "P2", "file": fname, "repo": repo_label,
            "description": f"`{fname}` looks like a temporary/artifact file at repository root.{dirty_note}",
            "suggested_action": f"Confirm with user whether `{fname}` belongs at repository root or under `docs/`. NEVER delete without explicit user approval, and never touch files with uncommitted changes.",
        })
    for spec in hygiene.get("un_dehydrated_specs", [])[:3]:
        rel = spec.get("file", "")
        if not rel:
            continue
        candidates.append({
            "title": f"{prefix}Dehydrate bulky spec to commit-linked stub: {rel}", "type": "docs", "severity": "P3", "file": rel, "repo": repo_label,
            "description": f"`{rel}` has {spec.get('lines', spec.get('body_lines', 0))} lines without a dehydrated Git-commit stub.",
            "suggested_action": f"Run `scaffold_repo_okf.py --dehydrate-spec {rel} --living-doc docs/index.md` only once shipped and cleanly committed in Git HEAD (zero uncommitted edits).",
        })
    return candidates


def run_docs_sweep(repo_root: Path, okf_mod: Any, repo_label: str = "") -> Dict[str, Any]:
    """Run non-destructive `<repo>/docs/` OKF scaffolding together with doc-gap & hygiene audits."""
    scaffold: Dict[str, Any] = {}
    hygiene: Dict[str, Any] = {"stray_root_files": [], "un_dehydrated_specs": [], "stale_cards": [], "doc_recommendations": []}
    if okf_mod is not None:
        scaffold = okf_mod.scan_and_scaffold(repo_root)
        hygiene = okf_mod.audit_hygiene(repo_root)
    else:
        docs_index = repo_root / "docs" / "index.md"
        if not docs_index.exists():
            docs_index.parent.mkdir(parents=True, exist_ok=True)
            docs_index.write_text("# Repository Architecture Index\n\n_Created by `/wf-work docs`._\n", encoding="utf-8")
            scaffold = {"created_cards": [], "preserved_cards": [], "index_file": "docs/index.md"}
    return {**hygiene, "scaffold": scaffold, "issue_candidates": _build_docs_issue_candidates(hygiene, repo_label=repo_label)}


def run_debt_sweep(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Bounded read-only scan for `TODO`/`FIXME` items and giant files (>=600 lines)."""
    todos: List[Dict[str, Any]] = []
    giant_files: List[Dict[str, Any]] = []
    scanned = 0
    for fpath, rel in _iter_repo_files(repo_root, CODE_EXTS, max_files=max_files):
        scanned += 1
        lines = _read_lines(fpath)
        if len(lines) >= 600:
            giant_files.append({"file": rel, "lines": len(lines)})
        for lineno, line in enumerate(lines, 1):
            match = TODO_RE.search(line)
            if match and len(todos) < 30:
                todos.append({"file": rel, "line": lineno, "tag": match.group(1).upper(), "text": match.group(2).strip()[:120]})

    giant_sorted = sorted(giant_files, key=lambda x: x["lines"], reverse=True)[:10]
    candidates: List[Dict[str, Any]] = []
    for gf in giant_sorted[:2]:
        candidates.append({
            "title": f"Rolling 1-bite/day refactor: {gf['file']}",
            "type": "refactor",
            "severity": "P2",
            "file": gf["file"],
            "description": f"`{gf['file']}` is {gf['lines']} lines. Propose rolling 1-slice-per-day decomposition (1-3 helpers per Draft PR).",
            "suggested_action": "Promote via report-task.py --promote-issue --cadence rolling_slice --approve once approved.",
        })
    if todos:
        top = todos[0]
        candidates.append({
            "title": f"Resolve {top['tag']} in {top['file']}:{top['line']}",
            "type": "debt",
            "severity": "P3",
            "file": top["file"],
            "description": f"`{top['file']}:{top['line']}` contains `{top['tag']}`: {top['text']}",
            "suggested_action": "Inspect surrounding context and clean up or promote if still relevant.",
        })
    return {"files_scanned": scanned, "todo_hits": todos[:15], "giant_files": giant_sorted, "issue_candidates": candidates}


def _scan_security_line(rel: str, lineno: int, line: str) -> Optional[Dict[str, Any]]:
    """Inspect one source line for secrets, production defaults, or dangerous sinks."""
    stripped = line.strip()
    is_regex_def = "re.compile" in stripped or "re.search" in stripped or stripped.startswith(("r\"", "r'"))
    if SECRET_RE.search(line):
        return {"file": rel, "line": lineno, "kind": "hardcoded_secret", "severity": "P0", "detail": "Possible hardcoded secret or private key."}
    if not is_regex_def and (PROD_FALLBACK_CALL_RE.search(line) or PROD_FALLBACK_OR_RE.search(line)):
        return {"file": rel, "line": lineno, "kind": "production_default", "severity": "P1", "detail": "Hardcoded `prod`/`production`/`live` fallback default."}
    if not is_regex_def and SINK_RE.search(line):
        return {"file": rel, "line": lineno, "kind": "unsafe_sink", "severity": "P1", "detail": f"Potentially unsafe execution/DOM sink: `{stripped[:80]}`."}
    return None


def _check_sam_param_drift(repo_root: Path) -> List[Dict[str, Any]]:
    """Flag AWS SAM `template.yaml` parameters missing from adjacent `samconfig.toml`."""
    tpl = repo_root / "template.yaml"
    sam = repo_root / "samconfig.toml"
    if not (tpl.is_file() and sam.is_file()):
        return []
    tpl_text = "\n".join(_read_lines(tpl))
    sam_text = "\n".join(_read_lines(sam))
    defined_sam = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]{2,})\s*=", sam_text))
    missing: List[Dict[str, Any]] = []
    in_params = False
    for line in tpl_text.splitlines():
        if re.match(r"^Parameters:\s*$", line):
            in_params = True
            continue
        if in_params and re.match(r"^[A-Za-z]", line):
            break
        m = re.match(r"^\s{2}([A-Z][A-Za-z0-9_]{2,}):\s*$", line) if in_params else None
        if m and m.group(1) not in defined_sam:
            missing.append({"file": "samconfig.toml", "line": 1, "kind": "iac_param_drift", "severity": "P1", "detail": f"Template parameter `{m.group(1)}` absent from `samconfig.toml`."})
    return missing


def run_security_sweep(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Read-only security audit for secrets, `prod` fallbacks, unsafe sinks, and IaC drift."""
    findings: List[Dict[str, Any]] = []
    scanned = 0
    for fpath, rel in _iter_repo_files(repo_root, SEC_EXTS, max_files=max_files):
        scanned += 1
        for lineno, line in enumerate(_read_lines(fpath), 1):
            hit = _scan_security_line(rel, lineno, line)
            if hit:
                findings.append(hit)
                if len(findings) >= 25:
                    break
    findings.extend(_check_sam_param_drift(repo_root))
    candidates = [
        {
            "title": f"Security [{h['kind']}] in {h['file']}:{h['line']}",
            "type": "security",
            "severity": h["severity"],
            "file": h["file"],
            "description": f"{h['detail']} (detected at `{h['file']}:{h['line']}`).",
            "suggested_action": "Audit line and fix cleanly (or update deployment config without adding production fallbacks).",
        }
        for h in findings[:3]
    ]
    return {"files_scanned": scanned, "findings": findings[:25], "issue_candidates": candidates}


def run_design_sweep(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Read-only frontend/UX sweep for a11y attributes, viewport tags, and `!important` clutter."""
    findings: List[Dict[str, Any]] = []
    scanned = 0
    for fpath, rel in _iter_repo_files(repo_root, UI_EXTS, max_files=max_files):
        scanned += 1
        lines = _read_lines(fpath)
        text = "\n".join(lines)
        if fpath.suffix.lower() in (".html", ".htm") and "<html" in text.lower() and 'name="viewport"' not in text.lower():
            findings.append({"file": rel, "line": 1, "kind": "missing_viewport", "severity": "P2", "detail": "HTML entrypoint missing `<meta name=\"viewport\">`."})
        for lineno, line in enumerate(lines, 1):
            if IMG_NO_ALT_RE.search(line):
                findings.append({"file": rel, "line": lineno, "kind": "img_missing_alt", "severity": "P2", "detail": "`<img>` element missing `alt` attribute."})
            elif CLICKABLE_DIV_RE.search(line):
                findings.append({"file": rel, "line": lineno, "kind": "non_semantic_click", "severity": "P2", "detail": "Clickable `<div>`/`<span>` missing ARIA `role`."})
            elif "!important" in line and fpath.suffix.lower() in (".css", ".scss"):
                findings.append({"file": rel, "line": lineno, "kind": "css_important", "severity": "P3", "detail": "Overuse of `!important` complicates styling specificity."})
    candidates = [
        {
            "title": f"Design/a11y [{h['kind']}] in {h['file']}:{h['line']}",
            "type": "ux",
            "severity": h["severity"],
            "file": h["file"],
            "description": h["detail"],
            "suggested_action": "Apply semantic HTML / accessible attributes per `wf-ui-ux-design`.",
        }
        for h in findings[:3]
    ]
    return {"files_scanned": scanned, "findings": findings[:25], "issue_candidates": candidates}


def _scan_perf_file(rel: str, lines: List[str]) -> List[Dict[str, Any]]:
    """Scan one code file for N+1 queries, sequential awaits in loops, or unbounded selects."""
    hits: List[Dict[str, Any]] = []
    loop_indent: Optional[int] = None
    has_async = any("async def " in ln or "async function" in ln for ln in lines)
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "*")):
            continue
        indent = len(line) - len(line.lstrip())
        if loop_indent is not None and indent <= loop_indent and not LOOP_RE.search(line):
            loop_indent = None
        if LOOP_RE.search(line):
            loop_indent = indent
            continue
        if loop_indent is not None and LOOP_AWAIT_QUERY_RE.search(line):
            hits.append({"file": rel, "line": lineno, "kind": "loop_io_n_plus_1", "severity": "P2", "detail": "Potential N+1 query or sequential `await`/HTTP call inside loop."})
        elif SELECT_STAR_RE.search(line) and "limit" not in line.lower():
            hits.append({"file": rel, "line": lineno, "kind": "unbounded_select", "severity": "P2", "detail": "`SELECT *` query without `LIMIT`."})
        elif has_async and any(tok in line for tok in ("readFileSync(", "execSync(", "time.sleep(")):
            hits.append({"file": rel, "line": lineno, "kind": "blocking_sync_io", "severity": "P2", "detail": "Synchronous blocking call in async module."})
    return hits


def run_optimization_sweep(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Read-only performance audit for loop I/O, sequential awaits, and blocking calls."""
    findings: List[Dict[str, Any]] = []
    scanned = 0
    for fpath, rel in _iter_repo_files(repo_root, CODE_EXTS, max_files=max_files):
        scanned += 1
        findings.extend(_scan_perf_file(rel, _read_lines(fpath)))
        if len(findings) >= 25:
            break
    candidates = [
        {
            "title": f"Perf [{h['kind']}] in {h['file']}:{h['line']}",
            "type": "perf",
            "severity": h["severity"],
            "file": h["file"],
            "description": f"{h['detail']} (at `{h['file']}:{h['line']}`).",
            "suggested_action": "Batch queries (`Promise.all` / bulk fetch) or bound result sizes.",
        }
        for h in findings[:3]
    ]
    return {"files_scanned": scanned, "findings": findings[:25], "issue_candidates": candidates}


def _check_dependency_pins(repo_root: Path) -> List[Dict[str, Any]]:
    """Inspect `package.json`, `.nvmrc`, and `requirements.txt` for unpinned deps or drift."""
    hits: List[Dict[str, Any]] = []
    pkg = repo_root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            for section in ("dependencies", "devDependencies"):
                for dep, ver in (data.get(section) or {}).items():
                    if str(ver).strip() in ("*", "latest", "x"):
                        hits.append({"file": "package.json", "line": 1, "kind": "unpinned_dep", "severity": "P2", "detail": f"Dependency `{dep}` uses floating version `{ver}`."})
            nvmrc = repo_root / ".nvmrc"
            eng_node = ((data.get("engines") or {}).get("node") or "")
            if nvmrc.is_file() and eng_node:
                pin = "".join(_read_lines(nvmrc)).strip().lstrip("v")
                if pin and pin.split(".")[0] not in eng_node:
                    hits.append({"file": ".nvmrc", "line": 1, "kind": "runtime_drift", "severity": "P2", "detail": f"`.nvmrc` ({pin}) diverges from `package.json` `engines.node` ({eng_node})."})
        except (OSError, ValueError):
            pass
    reqs = repo_root / "requirements.txt"
    if reqs.is_file():
        for lineno, line in enumerate(_read_lines(reqs), 1):
            pkg_line = line.strip()
            if pkg_line and not pkg_line.startswith(("#", "-")) and not any(op in pkg_line for op in ("==", "~=", ">=", "<=")):
                hits.append({"file": "requirements.txt", "line": lineno, "kind": "unpinned_dep", "severity": "P2", "detail": f"Unpinned Python requirement `{pkg_line}`."})
    return hits


def _check_env_example_drift(repo_root: Path, max_files: int = 120) -> List[Dict[str, Any]]:
    """Check if code env lookups are undocumented in `.env.example` when `.env.example` exists."""
    env_ex = repo_root / ".env.example"
    if not env_ex.is_file():
        return []
    defined: Set[str] = set()
    for line in _read_lines(env_ex):
        m = re.match(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=", line)
        if m:
            defined.add(m.group(1))
    hits: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for fpath, rel in _iter_repo_files(repo_root, CODE_EXTS, max_files=max_files):
        for lineno, line in enumerate(_read_lines(fpath), 1):
            for m in ENV_LOOKUP_RE.finditer(line):
                var = m.group(1) or m.group(2)
                if var and var not in defined and var not in _BUILTIN_ENV_VARS and var not in seen:
                    seen.add(var)
                    hits.append({"file": rel, "line": lineno, "kind": "env_example_drift", "severity": "P2", "detail": f"Env var `{var}` used in `{rel}:{lineno}` is missing from `.env.example`."})
    return hits


def run_housekeeping_sweep(repo_root: Path, max_files: int = 200) -> Dict[str, Any]:
    """Read-only housekeeping sweep for dependency pinning, runtime drift, and `.env.example`."""
    findings = _check_dependency_pins(repo_root) + _check_env_example_drift(repo_root, max_files=max_files)
    candidates = [
        {
            "title": f"Housekeeping [{h['kind']}] in {h['file']}",
            "type": "chore",
            "severity": h["severity"],
            "file": h["file"],
            "description": h["detail"],
            "suggested_action": "Align version pins or `.env.example` keys for environment parity.",
        }
        for h in findings[:3]
    ]
    return {"findings": findings[:25], "issue_candidates": candidates}
