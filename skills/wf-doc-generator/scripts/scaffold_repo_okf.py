#!/usr/bin/env python3
"""
Repository Living OKF Documentation & Hygiene Tool (`<repo>/docs/`)

Maintains agent-readable Open Knowledge Format (OKF) architecture docs directly
inside `<repo>/docs/` so any AI coding harness benefits—even without Workforces installed.

Subcommands / Modes:
  --scan <repo>            Non-destructively scaffold/update `<repo>/docs/index.md` and
                           starter `docs/architecture/*.md` cards with `affected_files:`.
  --audit-hygiene <repo>   Audit stray root files, bulky shipped PRDs needing dehydration,
                           stale cards, and module doc gaps (with blast-radius priority).
  --recommend-docs <repo>  Output ranked documentation recommendations (OKF cards +
                           inline code docblocks) by blast radius and complexity.
  --dehydrate-spec <file>  Collapse a shipped PRD/spec into a compact stub linking to
                           the exact pre-dehydration Git commit SHA and living docs.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


IGNORE_DIRS: FrozenSet[str] = frozenset({
    ".git", ".worktrees", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "dist", "build", ".next", "target", ".agents",
    ".claude", ".grok", ".github", "workforces", "coverage", ".cache",
})

CODE_EXTS: FrozenSet[str] = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs", ".java", ".rb",
})
MONOREPO_CONTAINERS: FrozenSet[str] = frozenset({"apps", "services", "packages", "crates", "modules"})
SRC_CONTAINERS: FrozenSet[str] = frozenset({"src", "app", "internal", "pkg", "cmd", "lib", "skills"})
ENTRYPOINT_HINTS: Tuple[str, ...] = (
    "controller", "handler", "subscriber", "listener", "notifier", "worker",
    "router", "route", "service", "command", "webhook", "index.", "main.", "app.", "server.",
)

ENV_LOOKUP_RE = re.compile(
    r"(?:process\.env\.([A-Z][A-Z0-9_]{2,})"
    r"|os\.(?:getenv|environ\.get)\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]"
    r"|os\.environ\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]\s*\]"
    r"|\$_ENV\[\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]\s*\]"
    r"|getenv\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]\s*\)"
    r"|os\.Getenv\(\s*\"([A-Z][A-Z0-9_]{2,})\"\s*\))"
)
_BUILTIN_ENV_VARS: FrozenSet[str] = frozenset({
    "PATH", "HOME", "PWD", "USER", "SHELL", "TERM", "LANG", "TMPDIR", "CI", "PYTHONPATH",
})

_CATCHALL_STACK_GLOBS: FrozenSet[str] = frozenset({
    "src/**/*.php", "app/**/*.php", "config/**/*",
    "cmd/**/*.go", "internal/**/*.go", "pkg/**/*.go", "*.go",
    "src/**/*.ts", "src/**/*.tsx", "src/**/*.js", "apps/**/*",
    "src/**/*.py", "app/**/*.py", "*.py",
    "src/**/*.rs", "crates/**/*.rs",
})

STANDARD_ROOT_FILES = frozenset((
    "readme.md readme-deploy.md deploy.md deployment.md architecture.md runbook.md install.md "
    "upgrading.md migration.md development.md testing.md governance.md maintainers.md authors "
    "authors.md authors.txt notice notice.md notice.txt version version.txt llms.txt llms-full.txt "
    "ai.txt robots.txt humans.txt security.txt license license.md license.txt contributing.md "
    "code_of_conduct.md security.md changelog.md agents.md gemini.md claude.md makefile dockerfile "
    "docker-compose.yml docker-compose.yaml procfile justfile rakefile gemfile gemfile.lock pipfile "
    "pipfile.lock poetry.lock uv.lock bun.lock bun.lockb template.yaml template.yml samconfig.toml "
    "serverless.yml serverless.yaml package.json package-lock.json pnpm-lock.yaml yarn.lock "
    "tsconfig.json composer.json composer.lock go.mod go.sum cargo.toml cargo.lock pyproject.toml "
    "setup.py requirements.txt update.sh install.sh"
).split())

_README_VARIANT_RE = re.compile(r"^readme[-_.].+\.(?:md|txt)$")
_HOST_BASES = (".agents", ".claude", ".grok", ".github", ".github/copilot", ".cursor", "")

AUTO_START = "<!-- wf-okf:auto-start -->"
AUTO_END = "<!-- wf-okf:auto-end -->"


def _is_standard_root_file(lower_name: str) -> bool:
    """Return True if a lowercase filename is a standard root repository file or README variant."""
    return lower_name in STANDARD_ROOT_FILES or bool(_README_VARIANT_RE.match(lower_name))


def _is_test_relpath(rel: str) -> bool:
    """Return True if repo-relative POSIX path points to a test fixture or test suite."""
    parts = rel.lower().split("/")
    base = parts[-1]
    if any(p in ("tests", "test", "__tests__", "spec", "specs") for p in parts[:-1]):
        return True
    if base.startswith(("test_", "spec_")) or ".test." in base or ".spec." in base:
        return True
    return base.endswith(("test.php", "tests.php", "testcase.php"))


def _load_sibling_module(skill_name: str, script_name: str, mod_alias: str, repo_root: Optional[Path] = None):
    """Dynamically load a sibling skill script without requiring package installation."""
    here = Path(__file__).resolve()
    candidates: List[Path] = []
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / skill_name / "scripts" / script_name)
    if repo_root is not None:
        for base in _HOST_BASES:
            root_base = (repo_root / base) if base else repo_root
            candidates.append(root_base / "skills" / skill_name / "scripts" / script_name)
    target = next((p for p in candidates if p.is_file()), None)
    if target is None:
        return None
    spec = importlib.util.spec_from_file_location(mod_alias, str(target))
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _load_git_link_resolver(repo_root: Optional[Path] = None):
    """Load `git_link_resolver.py` from sibling `wf-management` skill."""
    return _load_sibling_module("wf-management", "git_link_resolver.py", "wf_git_link_resolver", repo_root=repo_root)


def _run_git(repo_root: Path, args: List[str]) -> Optional[str]:
    """Run a read-only git subcommand inside `repo_root` and return stripped stdout."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_root)] + args,
            capture_output=True, text=True, timeout=5, check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _git_porcelain_for_path(repo_root: Path, rel_path: str) -> Optional[str]:
    """Return `git status --porcelain=v1 --ignored=matching` output for `rel_path`, or None on error."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--ignored=matching", "--", rel_path],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if res.returncode == 0:
            return res.stdout.rstrip("\r\n")
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _find_matching_files(repo_root: Path, patterns: Tuple[str, ...]) -> List[str]:
    """Walk `repo_root` safely returning repo-relative POSIX paths matching `patterns`."""
    matches: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
        rel_dir = Path(root).relative_to(repo_root)
        for fname in sorted(files):
            if any(fnmatch(fname, pat) for pat in patterns):
                rel = (rel_dir / fname).as_posix()
                matches.append(rel.lstrip("./"))
    return matches


def _collect_repo_files(repo_root: Path) -> Tuple[List[str], List[str], List[str]]:
    """Collect `(non_test_code_files, test_files, all_files)` inside `repo_root`."""
    code_files: List[str] = []
    test_files: List[str] = []
    all_files: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not d.startswith("."))
        rel_dir = Path(root).relative_to(repo_root)
        for fname in sorted(files):
            rel = (rel_dir / fname).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            all_files.append(rel)
            if Path(fname).suffix.lower() not in CODE_EXTS:
                continue
            if _is_test_relpath(rel):
                test_files.append(rel)
            elif not rel.startswith("docs/"):
                code_files.append(rel)
    return code_files, test_files, all_files


def _extract_summary_docblock(file_path: Path) -> str:
    """Extract the first 1-2 meaningful lines of a leading comment/docblock if present."""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:25]
    except OSError:
        return ""
    for line in lines:
        s = line.strip()
        if not s or s.startswith(("#!", "<?php", "package ", "---")):
            continue
        cleaned = re.sub(r"^(?:/\*\*?|//|#|\*)\s?", "", s).rstrip("*/").strip()
        if cleaned and not cleaned.startswith(("@", "declare(", "use ", "import ", "from ")):
            return cleaned[:140]
    return ""


def _read_lines_cached(repo_root: Path, rel: str, cache: Dict[str, List[str]]) -> List[str]:
    """Read and cache lines for a repo-relative file path."""
    if rel not in cache:
        try:
            cache[rel] = (repo_root / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            cache[rel] = []
    return cache[rel]


def _extract_env_vars_from_lines(lines: List[str]) -> Set[str]:
    """Extract referenced environment variable names from source lines."""
    found: Set[str] = set()
    for line in lines:
        for match in ENV_LOOKUP_RE.finditer(line):
            var = next((g for g in match.groups() if g), "")
            if var and var not in _BUILTIN_ENV_VARS:
                found.add(var)
    return found


def _detect_stacks(repo_root: Path) -> List[Dict[str, Any]]:
    """Identify primary code stacks and IaC descriptors in `repo_root`."""
    stacks: List[Dict[str, Any]] = []

    if (repo_root / "composer.json").is_file():
        subscriber_hits = _find_matching_files(repo_root, ("*Subscriber*.php", "*Listener*.php", "*Notifier*.php"))
        stacks.append({
            "slug": "php-backend",
            "title": "PHP Services & Event Subscribers",
            "description": "PHP domain services, controllers, and event subscribers/listeners.",
            "globs": ["src/**/*.php", "app/**/*.php", "config/**/*"],
            "entrypoints": subscriber_hits[:10],
            "tags": ["php", "services", "events"],
        })

    if (repo_root / "go.mod").is_file():
        go_files = _find_matching_files(repo_root, ("*.go",))
        stacks.append({
            "slug": "go-services",
            "title": "Go Services & Handlers",
            "description": "Go packages, HTTP/queue handlers, and background workers.",
            "globs": ["cmd/**/*.go", "internal/**/*.go", "pkg/**/*.go", "*.go"],
            "entrypoints": go_files[:10],
            "tags": ["go", "backend"],
        })

    if (repo_root / "package.json").is_file() or (repo_root / "tsconfig.json").is_file():
        js_files = _find_matching_files(repo_root, ("*.ts", "*.tsx", "*.js", "*.mjs"))
        stacks.append({
            "slug": "node-typescript",
            "title": "Node.js / TypeScript Modules",
            "description": "TypeScript/JavaScript APIs, frontend apps, and webhook/worker handlers.",
            "globs": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.js", "apps/**/*"],
            "entrypoints": js_files[:10],
            "tags": ["typescript", "nodejs"],
        })

    if any((repo_root / f).is_file() for f in ("pyproject.toml", "setup.py", "requirements.txt")):
        py_files = _find_matching_files(repo_root, ("*.py",))
        stacks.append({
            "slug": "python-modules",
            "title": "Python Services & Automation",
            "description": "Python packages, handlers, and automation scripts.",
            "globs": ["src/**/*.py", "app/**/*.py", "*.py"],
            "entrypoints": [p for p in py_files if not _is_test_relpath(p)][:10],
            "tags": ["python"],
        })

    if (repo_root / "Cargo.toml").is_file():
        rs_files = _find_matching_files(repo_root, ("*.rs",))
        stacks.append({
            "slug": "rust-crates",
            "title": "Rust Crates & Binaries",
            "description": "Rust library crates and binaries.",
            "globs": ["src/**/*.rs", "crates/**/*.rs"],
            "entrypoints": rs_files[:10],
            "tags": ["rust"],
        })

    iac_files = [
        name for name in ("template.yaml", "template.yml", "samconfig.toml", "serverless.yml", "serverless.yaml")
        if (repo_root / name).is_file()
    ]
    if iac_files:
        stacks.append({
            "slug": "iac-deployment",
            "title": "IaC & Environment Configuration",
            "description": "Deployment templates, Lambda/SAM parameter overrides, and environment contracts.",
            "globs": ["**/template.yaml", "**/template.yml", "**/samconfig.toml", "**/serverless.yml"],
            "entrypoints": iac_files,
            "tags": ["iac", "sam", "env", "deployment"],
        })

    return stacks


def _parse_simple_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract simple YAML frontmatter keys and markdown body."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for line in parts[1].splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("- ") and current_key:
            meta.setdefault(current_key, [])
            if isinstance(meta[current_key], list):
                meta[current_key].append(s[2:].strip().strip("'\""))
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not v:
                meta[k] = []
                current_key = k
            elif v.startswith("[") and v.endswith("]"):
                current_key = None
                meta[k] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            elif v.lower() == "true":
                current_key = None
                meta[k] = True
            elif v.lower() == "false":
                current_key = None
                meta[k] = False
            else:
                current_key = None
                meta[k] = v.strip("'\"")
    return meta, parts[2].lstrip("\r\n")


def _infer_card_status(meta: Dict[str, Any], body: str) -> str:
    """Infer card lifecycle state (`scaffold` | `documented` | `stale`) from frontmatter/body."""
    explicit = str(meta.get("doc_status") or "").strip().lower()
    if explicit in ("scaffold", "documented", "stale"):
        return explicit
    if "Initial OKF architecture card scaffolded" in body:
        return "scaffold"
    return "documented"


def _read_existing_arch_cards(repo_root: Path) -> List[Dict[str, Any]]:
    """Read metadata and status for all `<repo>/docs/architecture/*.md` cards."""
    arch_dir = repo_root / "docs" / "architecture"
    if not arch_dir.is_dir():
        return []
    cards: List[Dict[str, Any]] = []
    for card in sorted(arch_dir.rglob("*.md")):
        try:
            text = card.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta, body = _parse_simple_frontmatter(text)
        aff = meta.get("affected_files") or []
        globs = [str(g) for g in aff] if isinstance(aff, list) else []
        is_catchall = bool(globs) and all(g in _CATCHALL_STACK_GLOBS for g in globs)
        cards.append({
            "rel": card.relative_to(repo_root).as_posix(),
            "slug": card.stem,
            "title": str(meta.get("title") or card.stem),
            "description": str(meta.get("description") or ""),
            "affected_files": globs,
            "doc_status": _infer_card_status(meta, body),
            "last_verified_commit": str(meta.get("last_verified_commit") or "").strip(),
            "is_catchall": is_catchall,
        })
    return cards


def _group_module_dirs(code_files: List[str]) -> Dict[str, List[str]]:
    """Group non-test code files into logical domain modules."""
    nested_srcs = {
        f.split("/")[0] for f in code_files
        if f.split("/")[0] in SRC_CONTAINERS and len(f.split("/")) >= 3
    }
    grouped: Dict[str, List[str]] = {}
    root_files: List[str] = []
    for rel in code_files:
        parts = rel.split("/")
        if len(parts) == 1:
            root_files.append(rel)
            continue
        top = parts[0]
        if top in MONOREPO_CONTAINERS:
            mod = f"{top}/{parts[1]}" if len(parts) >= 3 else top
        elif top in SRC_CONTAINERS:
            mod = f"{top}/{parts[1]}" if (top in nested_srcs and len(parts) >= 3) else top
        else:
            mod = top
        grouped.setdefault(mod, []).append(rel)

    if not grouped and root_files:
        grouped["."] = root_files
    return grouped


def _slugify_module(module: str) -> str:
    """Convert a module relative path into a deterministic kebab-case card slug."""
    if module == ".":
        return "root"
    return re.sub(r"[^a-z0-9]+", "-", module.lower()).strip("-") or "module"


def _has_inline_docblock(lines: List[str], sym: Dict[str, Any]) -> bool:
    """Return True if a Python docstring or leading comment block precedes `sym`."""
    if sym.get("docstring"):
        return True
    line_no = int(sym.get("line") or 0)
    if line_no <= 1 or line_no > len(lines):
        return False
    start = max(0, line_no - 6)
    preceding = [ln.strip() for ln in lines[start:line_no - 1] if ln.strip()]
    return any(ln.startswith(("/**", "/*", "*/", "*", "///", "//", "#")) for ln in preceding[-3:])


_SYMBOL_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"^\s*(?:(?:public|private|protected|static|final|abstract)\s+)*function\s+([a-zA-Z0-9_]+)\s*\(", "method"),
    (r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(", "function"),
    (r"^\s*(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", "function"),
    (r"^\s*(?:public|private|protected|async|static|\s)*\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?::|\{)", "method"),
    (r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(", "function"),
    (r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(", "function"),
    (r"^\s*(?:public|private|protected|static|async|override|\s)+\s+[\w<>]+\s+([a-zA-Z0-9_]+)\s*\(", "method"),
    (r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+|final\s+)?(?:class|interface|struct)\s+([a-zA-Z0-9_]+)", "class"),
)
_CALL_STOP_KEYWORDS: FrozenSet[str] = frozenset({
    "if", "for", "while", "switch", "catch", "return", "function", "func", "fn", "class", "new", "typeof", "constructor",
})
_RESOLVE_EXTS: Tuple[str, ...] = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".php", ".go", ".rs")
_RESOLVE_INDEX_TAILS: Tuple[str, ...] = ("/__init__.py", "/index.ts", "/index.tsx", "/index.js", "/mod.rs")
_JS_IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]|(?:require|import)\s*\(\s*['"]([^'"]+)['"]\s*\)"""
)
_PHP_USE_RE = re.compile(r"^\s*use\s+([A-Za-z0-9_\\]+)\s*(?:as\s+\w+)?;", re.MULTILINE)
_PHP_REQ_RE = re.compile(r"""(?:require|include)(?:_once)?\s*\(?\s*['"]([^'"]+)['"]\s*\)?""")
_GO_IMPORT_RE = re.compile(r'^\s*(?:import\s+)?(?:[a-zA-Z0-9_.]+\s+)?"([^"\s]+)"', re.MULTILINE)
_RUST_USE_RE = re.compile(r"^\s*(?:pub\s+)?use\s+(?:crate|super|self)::([A-Za-z0-9_:]+)", re.MULTILINE)
_RUST_MOD_RE = re.compile(r"^\s*(?:pub\s+)?mod\s+([A-Za-z0-9_]+)\s*;", re.MULTILINE)


def _parse_python_symbols(content: str, rel_path: str) -> List[Dict[str, Any]]:
    """Parse Python classes and functions in memory using stdlib `ast`."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _parse_regex_symbols(content.splitlines(), rel_path)
    out: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append({
                "name": node.name, "kind": "function", "file": rel_path,
                "line": node.lineno, "docstring": (ast.get_docstring(node) or "").strip(),
            })
        elif isinstance(node, ast.ClassDef):
            out.append({
                "name": node.name, "kind": "class", "file": rel_path,
                "line": node.lineno, "docstring": (ast.get_docstring(node) or "").strip(),
            })
    return out


def _parse_regex_symbols(lines: List[str], rel_path: str) -> List[Dict[str, Any]]:
    """Parse classes, functions, and methods from non-Python source lines."""
    out: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines, 1):
        for pat, kind in _SYMBOL_PATTERNS:
            match = re.search(pat, line)
            if not match:
                continue
            name = match.group(1)
            if name in _CALL_STOP_KEYWORDS:
                continue
            out.append({"name": name, "kind": kind, "file": rel_path, "line": idx, "docstring": ""})
            break
    return out


def _scan_symbols_once(
    repo_root: Path,
    code_files: List[str],
    lines_cache: Dict[str, List[str]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Parse `code_files` in memory for docblock coverage and symbol inventories."""
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for rel in code_files:
        lines = _read_lines_cached(repo_root, rel, lines_cache)
        syms = _parse_python_symbols("\n".join(lines), rel) if rel.endswith(".py") else _parse_regex_symbols(lines, rel)
        if syms:
            by_file[rel] = syms
    return by_file


def _extract_dynamic_loader_spec(call_node: ast.Call) -> Optional[str]:
    """Extract repo-relative script path from `_load_sibling_*` or `_load_module` calls."""
    if not isinstance(call_node.func, ast.Name):
        return None
    fn = call_node.func.id
    if fn in ("_load_sibling_script", "_load_sibling_module") and len(call_node.args) >= 2:
        a0, a1 = call_node.args[0], call_node.args[1]
        if isinstance(a0, ast.Constant) and isinstance(a1, ast.Constant):
            if isinstance(a0.value, str) and isinstance(a1.value, str):
                return f"skills/{a0.value}/scripts/{a1.value}"
    if fn == "_load_module" and len(call_node.args) >= 2:
        a1 = call_node.args[1]
        if isinstance(a1, ast.Constant) and isinstance(a1.value, str) and "/" in a1.value:
            return a1.value
    return None


def _extract_python_imports(content: str) -> List[str]:
    """Extract module import specifiers and dynamic sibling script references from Python AST."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    specs: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            specs.extend(alias.name for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            base = f"{prefix}{node.module}" if node.module else prefix
            if base:
                specs.append(base)
            for alias in node.names:
                if alias.name and alias.name != "*":
                    specs.append(f"{base}{'.' if node.module else ''}{alias.name}")
        elif isinstance(node, ast.Call):
            dyn = _extract_dynamic_loader_spec(node)
            if dyn:
                specs.append(dyn)
    return specs


def _extract_raw_imports(rel: str, lines: List[str]) -> List[str]:
    """Extract raw import/use/require specifiers for supported languages."""
    ext = Path(rel).suffix.lower()
    text = "\n".join(lines)
    if ext == ".py":
        return _extract_python_imports(text)
    if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
        return [m.group(1) or m.group(2) for m in _JS_IMPORT_RE.finditer(text) if (m.group(1) or m.group(2))]
    if ext == ".php":
        uses = [m.group(1).lstrip("\\").replace("\\", "/") for m in _PHP_USE_RE.finditer(text)]
        reqs = [m.group(1) for m in _PHP_REQ_RE.finditer(text)]
        return uses + reqs
    if ext == ".go":
        return [m.group(1) for m in _GO_IMPORT_RE.finditer(text) if "/" in m.group(1)]
    if ext == ".rs":
        uses = [f"./{m.group(1).replace('::', '/')}" for m in _RUST_USE_RE.finditer(text)]
        mods = [f"./{m.group(1)}" for m in _RUST_MOD_RE.finditer(text)]
        return uses + mods
    return []


def _build_target_lookup(code_files: List[str]) -> Tuple[Set[str], Dict[str, Set[str]], Dict[str, Set[str]]]:
    """Build exact-path, stem, and multi-segment suffix indexes for import resolution."""
    code_set = set(code_files)
    noext_index: Dict[str, Set[str]] = {}
    suffix_index: Dict[str, Set[str]] = {}
    for rel in code_files:
        p = Path(rel)
        noext = p.with_suffix("").as_posix()
        noext_index.setdefault(noext, set()).add(rel)
        noext_index.setdefault(noext.lower(), set()).add(rel)
        if p.name in ("__init__.py", "index.ts", "index.tsx", "index.js", "mod.rs"):
            parent = p.parent.as_posix()
            noext_index.setdefault(parent, set()).add(rel)
            noext_index.setdefault(parent.lower(), set()).add(rel)
        elif p.suffix == ".go":
            parent = p.parent.as_posix()
            noext_index.setdefault(parent, set()).add(rel)
        parts = noext.lower().split("/")
        for start in range(len(parts) - 1):
            tail = "/".join(parts[start:])
            suffix_index.setdefault(tail, set()).add(rel)
    return code_set, noext_index, suffix_index


def _resolve_relative_spec(
    importer_rel: str, spec: str, code_set: Set[str], noext_index: Dict[str, Set[str]]
) -> Set[str]:
    """Resolve `./`, `../`, or Python leading-dot relative import specifiers."""
    parent = Path(importer_rel).parent
    if spec.startswith((".", "/")) and not spec.startswith(("./", "../", "/")):
        dots = len(spec) - len(spec.lstrip("."))
        tail = spec[dots:].replace(".", "/")
        base_dir = parent
        for _ in range(max(0, dots - 1)):
            base_dir = base_dir.parent
        candidate = (base_dir / tail) if tail else base_dir
    else:
        clean = spec.lstrip("/")
        base = clean[:-3] if clean.endswith(".js") and not (parent / clean).as_posix() in code_set else clean
        candidate = Path(base) if spec.startswith("/") else (parent / base)

    norm = Path(os.path.normpath(candidate.as_posix())).as_posix().lstrip("./")
    if norm in code_set:
        return {norm}
    hits: Set[str] = set(noext_index.get(norm, set()))
    for ext in _RESOLVE_EXTS:
        if f"{norm}{ext}" in code_set:
            hits.add(f"{norm}{ext}")
    for idx_tail in _RESOLVE_INDEX_TAILS:
        if f"{norm}{idx_tail}" in code_set:
            hits.add(f"{norm}{idx_tail}")
    return hits


def _resolve_import_targets(
    importer_rel: str,
    spec: str,
    code_set: Set[str],
    noext_index: Dict[str, Set[str]],
    suffix_index: Dict[str, Set[str]],
) -> Set[str]:
    """Resolve one raw import/use/require specifier to concrete repo code files."""
    clean = spec.strip()
    if not clean:
        return set()
    if clean.startswith((".", "/")):
        return _resolve_relative_spec(importer_rel, clean, code_set, noext_index)
    norm = clean.replace(".", "/") if "/" not in clean and "\\" not in clean else clean.replace("\\", "/")
    norm = norm.lstrip("@/").strip("/")
    if norm in code_set:
        return {norm}
    if norm in noext_index:
        return set(noext_index[norm])
    low = norm.lower()
    if low in noext_index:
        return set(noext_index[low])
    if "/" in low and low in suffix_index:
        return set(suffix_index[low])
    parts = [p for p in low.split("/") if p]
    for start in range(1, max(1, len(parts) - 1)):
        tail = "/".join(parts[start:])
        if tail in suffix_index:
            return set(suffix_index[tail])
    return set()


def _build_import_graph(
    repo_root: Path,
    code_files: List[str],
    test_files: List[str],
    lines_cache: Dict[str, List[str]],
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """Build `(importers_by_file, test_importers_by_file)` from real import/use/require statements."""
    code_set, noext_index, suffix_index = _build_target_lookup(code_files)
    importers_by_file: Dict[str, Set[str]] = {}
    test_importers_by_file: Dict[str, Set[str]] = {}
    for importer_rel, is_test in [(f, False) for f in code_files] + [(f, True) for f in test_files]:
        lines = _read_lines_cached(repo_root, importer_rel, lines_cache)
        bucket = test_importers_by_file if is_test else importers_by_file
        for spec in _extract_raw_imports(importer_rel, lines):
            for target in _resolve_import_targets(importer_rel, spec, code_set, noext_index, suffix_index):
                if target != importer_rel:
                    bucket.setdefault(target, set()).add(importer_rel)
    return importers_by_file, test_importers_by_file


def _clean_commit_files(block: str) -> List[str]:
    """Extract sorted, non-ignored repo-relative file paths from a git log commit block."""
    files: Set[str] = set()
    for line in block.splitlines():
        rel = line.strip().replace("\\", "/")
        if not rel or any(part in IGNORE_DIRS for part in Path(rel).parts):
            continue
        files.add(rel)
    return sorted(files)


def _build_git_cochanges(
    repo_root: Path, in_git: bool, max_commits: int = 200
) -> Tuple[Dict[str, Dict[str, int]], int]:
    """Build pairwise file co-change counts across recent non-merge Git commits."""
    if not in_git:
        return {}, 0
    raw = _run_git(
        repo_root,
        ["log", "--name-only", "--pretty=format:---COMMIT---", f"-n{max_commits}", "--no-merges"],
    )
    if not raw:
        return {}, 0
    counts: Dict[str, Dict[str, int]] = {}
    valid_commits = 0
    for block in raw.split("---COMMIT---"):
        files = _clean_commit_files(block)
        if len(files) < 2 or len(files) > 25:
            continue
        valid_commits += 1
        for src in files:
            peer_map = counts.setdefault(src, {})
            for dst in files:
                if dst != src:
                    peer_map[dst] = peer_map.get(dst, 0) + 1
    return counts, valid_commits


def _top_cochanged_for_files(
    target_files: Set[str],
    cochanges: Dict[str, Dict[str, int]],
    commit_count: int,
    existing_files: Optional[Set[str]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return top co-changed files outside `target_files` ordered by co-change frequency."""
    agg: Dict[str, int] = {}
    for tf in target_files:
        for peer, count in cochanges.get(tf, {}).items():
            if peer in target_files:
                continue
            if existing_files is not None and peer not in existing_files:
                continue
            agg[peer] = agg.get(peer, 0) + count
    min_threshold = 2 if commit_count >= 10 else 1
    ranked = [
        {"file": f, "cochanges": c}
        for f, c in sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))
        if c >= min_threshold
    ]
    return ranked[:limit]


def _compute_module_metrics(
    repo_root: Path,
    mod_files: List[str],
    symbols_by_file: Dict[str, List[Dict[str, Any]]],
    importers_by_file: Dict[str, Set[str]],
    lines_cache: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Compute public docblock coverage and cross-module direct import fan-in."""
    mod_file_set = set(mod_files)
    public_syms: List[Dict[str, Any]] = []
    undoc_names: List[str] = []
    documented_count = 0

    for rel in mod_files:
        file_lines = _read_lines_cached(repo_root, rel, lines_cache)
        for sym in symbols_by_file.get(rel, []):
            name = str(sym.get("name") or "")
            if not name or (name.startswith("_") and sym.get("kind") != "class"):
                continue
            public_syms.append(sym)
            if _has_inline_docblock(file_lines, sym):
                documented_count += 1
            elif name not in undoc_names and len(undoc_names) < 8:
                undoc_names.append(name)

    direct_importers: Set[str] = set()
    for rel in mod_files:
        for imp in importers_by_file.get(rel, set()):
            if imp not in mod_file_set:
                direct_importers.add(imp)

    return {
        "symbol_count": len(public_syms),
        "documented_symbol_count": documented_count,
        "undocumented_symbols": len(public_syms) - documented_count,
        "undocumented_symbol_names": undoc_names,
        "inbound_callers": len(direct_importers),
        "caller_files": sorted(direct_importers)[:5],
    }


_GENERIC_DIR_NAMES: FrozenSet[str] = frozenset({
    "skills", "scripts", "src", "app", "lib", "pkg", "cmd", "internal", "utils", "helpers", "services", "models", "controllers",
})


def _match_module_tests(module: str, mod_files: List[str], test_files: List[str]) -> List[str]:
    """Identify test files likely covering `module` by non-generic directory or filename stem."""
    mod_parts = [p.lower() for p in Path(module).parts if p not in (".", "") and p.lower() not in _GENERIC_DIR_NAMES]
    mod_tokens = {p for p in mod_parts if len(p) >= 3}
    stems = {Path(f).stem.lower() for f in mod_files[:15] if len(Path(f).stem) >= 3}
    matched: List[str] = []
    for tf in test_files:
        low = tf.lower()
        if any(tok in low for tok in mod_tokens) or any(st in low for st in stems):
            matched.append(tf)
        if len(matched) >= 10:
            break
    return matched


def _commits_since_for_paths(repo_root: Path, sha: str, paths: List[str]) -> int:
    """Count Git commits touching `paths` since `sha`, returning 0 when unavailable."""
    if not sha or not paths:
        return 0
    if _run_git(repo_root, ["cat-file", "-e", f"{sha}^{{commit}}"]) is None:
        return 0
    out = _run_git(repo_root, ["rev-list", "--count", f"{sha}..HEAD", "--"] + paths[:25])
    try:
        return int(out) if out else 0
    except ValueError:
        return 0


def _glob_matches(rel_path: str, pattern: str) -> bool:
    """Match a repo-relative POSIX path against a glob pattern, allowing `**/` for zero subdirs."""
    if fnmatch(rel_path, pattern):
        return True
    if "/**/" in pattern and fnmatch(rel_path, pattern.replace("/**/", "/")):
        return True
    if pattern.startswith("**/") and fnmatch(rel_path, pattern[3:]):
        return True
    return False


def _evaluate_module_doc_status(
    repo_root: Path,
    in_git: bool,
    module: str,
    mod_files: List[str],
    cards: List[Dict[str, Any]],
) -> Tuple[str, Optional[str]]:
    """Determine `(doc_status, matched_card_rel)` for a module across existing cards."""
    dedicated: List[Dict[str, Any]] = []
    catchall: List[Dict[str, Any]] = []
    for card in cards:
        globs = card["affected_files"]
        if any(_glob_matches(mf, g) for mf in mod_files for g in globs):
            (catchall if card["is_catchall"] else dedicated).append(card)

    chosen = dedicated[0] if dedicated else (catchall[0] if (catchall and module == ".") else None)
    if chosen is None:
        return "missing", None
    status = chosen["doc_status"]
    if status == "documented" and in_git and chosen["last_verified_commit"]:
        if _commits_since_for_paths(repo_root, chosen["last_verified_commit"], mod_files) >= 5:
            status = "stale"
    return status, chosen["rel"]


def _analyze_single_module(
    repo_root: Path,
    in_git: bool,
    module: str,
    mod_files: List[str],
    test_files: List[str],
    all_file_set: Set[str],
    cards: List[Dict[str, Any]],
    symbols_by_file: Dict[str, List[Dict[str, Any]]],
    importers_by_file: Dict[str, Set[str]],
    test_importers_by_file: Dict[str, Set[str]],
    cochanges: Dict[str, Dict[str, int]],
    commit_count: int,
    lines_cache: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Assemble static metrics, import fan-in, co-change coupling, and doc score for one module."""
    total_lines = 0
    giant_files: List[Dict[str, Any]] = []
    env_vars: Set[str] = set()
    entrypoints: List[str] = []

    for rel in mod_files:
        lines = _read_lines_cached(repo_root, rel, lines_cache)
        total_lines += len(lines)
        if len(lines) >= 400:
            giant_files.append({"file": rel, "lines": len(lines)})
        env_vars.update(_extract_env_vars_from_lines(lines))
        if any(hint in Path(rel).name.lower() for hint in ENTRYPOINT_HINTS):
            entrypoints.append(rel)

    giant_files.sort(key=lambda item: item["lines"], reverse=True)
    if not entrypoints:
        entrypoints = mod_files[:5]

    sym_metrics = _compute_module_metrics(repo_root, mod_files, symbols_by_file, importers_by_file, lines_cache)
    co_change_items = _top_cochanged_for_files(set(mod_files), cochanges, commit_count, existing_files=all_file_set, limit=5)
    co_change_files = [item["file"] for item in co_change_items]
    direct_tests = {tf for mf in mod_files for tf in test_importers_by_file.get(mf, set())}
    matched_tests = sorted(direct_tests | set(_match_module_tests(module, mod_files, test_files)))[:10]

    doc_status, matched_card = _evaluate_module_doc_status(repo_root, in_git, module, mod_files, cards)
    slug = _slugify_module(module)
    card_path = matched_card or f"docs/architecture/{slug}.md"
    globs = [f"{module}/**/*"] if module != "." else [f"*{ext}" for ext in sorted(CODE_EXTS)[:4]]

    status_weight = {"missing": 15, "scaffold": 10, "stale": 8, "documented": 0}.get(doc_status, 0)
    priority_score = (
        sym_metrics["inbound_callers"] * 4
        + len(co_change_files) * 2
        + len(giant_files) * 10
        + sym_metrics["undocumented_symbols"] * 2
        + (total_lines // 100)
        + status_weight
    )
    severity = "P1" if (sym_metrics["inbound_callers"] >= 3 or giant_files or total_lines >= 800) else "P2"

    return {
        "module": module,
        "slug": slug,
        "card_path": card_path,
        "doc_status": doc_status,
        "globs": globs,
        "file_count": len(mod_files),
        "total_lines": total_lines,
        "giant_files": giant_files[:5],
        "entrypoints": entrypoints[:10],
        "env_vars": sorted(env_vars),
        "test_files": matched_tests,
        "co_change_files": co_change_files,
        **sym_metrics,
        "priority_score": priority_score,
        "severity": severity,
    }


def discover_modules(repo_root: Path) -> List[Dict[str, Any]]:
    """Discover code modules with import fan-in, Git co-change coupling, env vars, and doc status."""
    code_files, test_files, all_files = _collect_repo_files(repo_root)
    if not code_files:
        return []
    in_git = _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"]) == "true"
    cards = _read_existing_arch_cards(repo_root)
    lines_cache: Dict[str, List[str]] = {}
    symbols_by_file = _scan_symbols_once(repo_root, code_files, lines_cache)
    importers_by_file, test_importers_by_file = _build_import_graph(repo_root, code_files, test_files, lines_cache)
    cochanges, commit_count = _build_git_cochanges(repo_root, in_git)
    grouped = _group_module_dirs(code_files)
    all_file_set = set(all_files)

    modules = [
        _analyze_single_module(
            repo_root, in_git, mod, mod_files, test_files, all_file_set, cards,
            symbols_by_file, importers_by_file, test_importers_by_file, cochanges, commit_count, lines_cache,
        )
        for mod, mod_files in sorted(grouped.items())
    ]
    modules.sort(key=lambda item: (-item["priority_score"], item["module"]))
    return modules


def analyze_file_impact(repo_root: Path, target_file: str) -> Dict[str, Any]:
    """Compute pre-edit blast radius for `target_file` using OKF cards, direct imports, tests, and Git co-changes."""
    resolved_root = repo_root.resolve()
    cand = Path(target_file)
    abs_target = cand.resolve() if cand.is_absolute() else (resolved_root / cand).resolve()
    try:
        rel_target = abs_target.relative_to(resolved_root).as_posix()
    except ValueError:
        rel_target = target_file.replace("\\", "/").lstrip("./")

    code_files, test_files, all_files = _collect_repo_files(resolved_root)
    in_git = _run_git(resolved_root, ["rev-parse", "--is-inside-work-tree"]) == "true"
    cards = _read_existing_arch_cards(resolved_root)
    lines_cache: Dict[str, List[str]] = {}
    symbols_by_file = _scan_symbols_once(resolved_root, code_files, lines_cache)
    importers_by_file, test_importers_by_file = _build_import_graph(resolved_root, code_files, test_files, lines_cache)
    cochanges, commit_count = _build_git_cochanges(resolved_root, in_git)

    matching_cards = [
        {"file": c["rel"], "title": c["title"], "doc_status": c["doc_status"]}
        for c in cards
        if any(_glob_matches(rel_target, g) for g in c["affected_files"])
    ]
    target_lines = _read_lines_cached(resolved_root, rel_target, lines_cache) if abs_target.is_file() else []
    mod_parent = Path(rel_target).parent.as_posix() or "."
    direct_tests = test_importers_by_file.get(rel_target, set())
    heuristic_tests = _match_module_tests(mod_parent, [rel_target], test_files)

    return {
        "repo_root": str(resolved_root),
        "target_file": rel_target,
        "matching_okf_cards": matching_cards,
        "direct_importers": sorted(importers_by_file.get(rel_target, set())),
        "matching_tests": sorted(set(direct_tests) | set(heuristic_tests))[:10],
        "git_co_changed_files": _top_cochanged_for_files(
            {rel_target}, cochanges, commit_count, existing_files=set(all_files), limit=8
        ),
        "env_vars": sorted(_extract_env_vars_from_lines(target_lines)),
        "exported_symbols": [
            str(s["name"]) for s in symbols_by_file.get(rel_target, [])
            if s.get("name") and not str(s["name"]).startswith("_")
        ][:15],
    }


def _render_card_markdown(stack: Dict[str, Any], repo_root: Path, resolver_mod: Any) -> str:
    """Build a starter `<repo>/docs/architecture/<slug>.md` refactor-ready OKF card."""
    today = datetime.date.today().isoformat()
    head_sha = _run_git(repo_root, ["rev-parse", "HEAD"]) or ""
    affected_yaml = "\n".join(f'  - "{g}"' for g in stack["globs"])
    tags_yaml = ", ".join(stack["tags"])

    entry_lines: List[str] = []
    env_vars: Set[str] = set()
    for rel in stack["entrypoints"]:
        abs_target = repo_root / rel
        href = resolver_mod.resolve_portable_link(str(abs_target), repo_root=str(repo_root)) if resolver_mod else rel
        doc_hint = _extract_summary_docblock(abs_target) if abs_target.is_file() else ""
        if abs_target.is_file():
            env_vars.update(_extract_env_vars_from_lines(abs_target.read_text(encoding="utf-8", errors="ignore").splitlines()))
        suffix = f" — {doc_hint}" if doc_hint else ""
        entry_lines.append(f"- [`{rel}`]({href}){suffix}")
    entries_block = "\n".join(entry_lines) if entry_lines else "- _No matching entrypoints auto-detected yet._"
    env_block = "\n".join(f"- `{v}` — verify parity across deployment manifests / `.env.example`" for v in sorted(env_vars))
    if not env_block:
        env_block = "- Verify required environment variables against IaC manifests (`template.yaml`, `samconfig.toml`, `.env.example`)."

    return f"""---
type: Architecture Component
title: "{stack['title']}"
description: "{stack['description']}"
doc_status: "scaffold"
last_verified_commit: "{head_sha}"
affected_files:
{affected_yaml}
tags: [{tags_yaml}]
updated_at: "{today}"
---

# {stack['title']}

## Purpose & Boundaries
{stack['description']}
- _Enrich this card via `/wf-work docs` with explicit ownership boundaries (owns vs. does NOT own)._

## Entrypoints, Events & Data Flow
{entries_block}

## Key Dependencies & Blast Radius
- _Run `scaffold_repo_okf.py --recommend-docs` and `grep_search` to map upstream services and high-fan-in callers before refactoring._

## Environment & Deployment Config
{env_block}
- Never hardcode `"prod"` or `"production"` fallback values in application code.

## Test Coverage & Verification
- _List unit/integration test files and verification commands covering this component._

## Constraints, Invariants & Gotchas
- **{today}:** Initial OKF architecture card scaffolded; append non-obvious architectural constraints and *why* choices were made here instead of keeping a separate `CHANGELOG.md`.
"""


def _merge_index_auto_section(existing_text: str, auto_block: str, title: str = "Repository Architecture Index") -> str:
    """Non-destructively insert or refresh only the `AUTO_START..AUTO_END` block in `docs/index.md`."""
    wrapped = f"{AUTO_START}\n{auto_block.strip()}\n{AUTO_END}"
    if AUTO_START in existing_text and AUTO_END in existing_text:
        pattern = re.compile(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END), re.DOTALL)
        return pattern.sub(wrapped, existing_text, count=1)

    if existing_text.strip():
        return existing_text.rstrip() + "\n\n## Auto-Discovered Architecture Map\n\n" + wrapped + "\n"

    return f"""---
type: OKF Index
title: "{title}"
description: "Living architecture knowledge index for human developers and AI agents."
---

# {title}

Start here before planning cross-service changes, event subscribers, refactoring, or environment config updates.

## Auto-Discovered Architecture Map

{wrapped}

## Human Architecture Notes
_Add system diagrams, ownership notes, and cross-service conventions here; automated scans preserve this section._
"""


def scan_and_scaffold(repo_root: Path) -> Dict[str, Any]:
    """Scan `repo_root` and non-destructively scaffold `<repo>/docs/index.md` and starter cards."""
    resolver_mod = _load_git_link_resolver(repo_root=repo_root)
    stacks = _detect_stacks(repo_root)
    docs_dir = repo_root / "docs"
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)

    created_cards: List[str] = []
    preserved_cards: List[str] = []

    for stack in stacks:
        card_rel = f"docs/architecture/{stack['slug']}.md"
        card_path = repo_root / card_rel
        if not card_path.exists():
            card_path.write_text(_render_card_markdown(stack, repo_root, resolver_mod), encoding="utf-8")
            created_cards.append(card_rel)
        else:
            preserved_cards.append(card_rel)

    all_cards = _read_existing_arch_cards(repo_root)
    table_rows = [
        "| Component | Status | Description | Affected Files | Card |",
        "|---|---|---|---|---|",
    ]
    for card in all_cards:
        card_path = repo_root / card["rel"]
        card_href = (
            resolver_mod.resolve_portable_link(str(card_path), repo_root=str(repo_root))
            if resolver_mod
            else f"architecture/{card['slug']}.md"
        )
        globs_str = ", ".join(f"`{g}`" for g in card["affected_files"][:3]) or "_none_"
        desc = card["description"] or "Architecture component card."
        table_rows.append(
            f"| **{card['title']}** | `{card['doc_status']}` | {desc} | {globs_str} | [{card['slug']}.md]({card_href}) |"
        )

    index_path = docs_dir / "index.md"
    existing_index = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    auto_block = "\n".join(table_rows) if all_cards else "_No architecture cards or language manifests detected yet._"
    index_path.write_text(_merge_index_auto_section(existing_index, auto_block), encoding="utf-8")

    return {
        "repo_root": str(repo_root),
        "index_file": "docs/index.md",
        "created_cards": created_cards,
        "preserved_cards": preserved_cards,
        "indexed_cards": [c["rel"] for c in all_cards],
        "detected_stacks": [s["slug"] for s in stacks],
    }


def _should_skip_git_root_entry(repo_root: Path, name: str, lower: str, protected_dirty: List[str]) -> bool:
    """Return True when Git status marks a root file as ignored, dirty, or untracked prose."""
    porcelain = _git_porcelain_for_path(repo_root, name)
    if porcelain is None:
        protected_dirty.append(name)
        return True
    if porcelain.startswith("!!"):
        return True
    if not porcelain:
        return False
    protected_dirty.append(name)
    return not porcelain.startswith("??") or lower.endswith((".md", ".txt"))


def _scan_stray_root_files(repo_root: Path, in_git: bool, protected_dirty: List[str]) -> List[str]:
    """Find non-standard root text/temp files while protecting dirty, untracked docs, and ignored files."""
    stray: List[str] = []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        lower = entry.name.lower()
        if _is_standard_root_file(lower) or not lower.endswith((".md", ".txt", ".log", ".bak", ".tmp")):
            continue
        if in_git and _should_skip_git_root_entry(repo_root, entry.name, lower, protected_dirty):
            continue
        stray.append(entry.name)
    return stray


def _scan_bulky_specs(repo_root: Path, in_git: bool, protected_dirty: List[str]) -> List[Dict[str, Any]]:
    """Find committed clean PRDs/specs over 60 body lines while protecting uncommitted specs."""
    bulky: List[Dict[str, Any]] = []
    for base in (repo_root / "docs", repo_root / "workforces"):
        if not base.is_dir():
            continue
        for md_path in sorted(base.rglob("*.md")):
            if "node_modules" in md_path.parts or ".worktrees" in md_path.parts:
                continue
            rel = md_path.relative_to(repo_root).as_posix()
            try:
                meta, body = _parse_simple_frontmatter(md_path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            is_spec = any(tok in md_path.name.lower() for tok in ("prd", "spec", "proposal", "rfc")) or str(meta.get("status", "")).lower() in ("shipped", "completed", "implemented", "archived")
            line_count = len(body.splitlines())
            if meta.get("dehydrated") is True or not (is_spec and line_count > 60):
                continue
            if in_git and _git_porcelain_for_path(repo_root, rel) != "":
                protected_dirty.append(rel)
                continue
            bulky.append({"file": rel, "body_lines": line_count, "status": meta.get("status", "unknown")})
    return bulky


def _scan_missing_okf(repo_root: Path) -> List[str]:
    """Identify missing `<repo>/docs/index.md` or key directories lacking OKF card coverage."""
    docs_dir = repo_root / "docs"
    missing: List[str] = []
    if not (docs_dir / "index.md").is_file():
        missing.append("Missing `<repo>/docs/index.md` repository architecture index.")
    covered_globs: List[str] = []
    arch_dir = docs_dir / "architecture"
    if arch_dir.is_dir():
        for card in arch_dir.rglob("*.md"):
            meta, _ = _parse_simple_frontmatter(card.read_text(encoding="utf-8", errors="ignore"))
            aff = meta.get("affected_files") or []
            if isinstance(aff, list):
                covered_globs.extend(aff)
    for kd in ("src/Service", "src/EventSubscriber", "src/EventListener", "internal", "cmd", "apps"):
        if (repo_root / kd).exists():
            sample = f"{kd}/sample.file"
            if not any(_glob_matches(sample, g) or _glob_matches(kd, g.rstrip("/*")) for g in covered_globs):
                missing.append(f"Directory `{kd}` has no matching `affected_files:` card under `docs/architecture/`.")
    return missing


def _scan_stale_cards(repo_root: Path, in_git: bool, all_files: List[str]) -> List[Dict[str, Any]]:
    """Detect `docs/architecture/*.md` cards with broken `affected_files` globs or code drift."""
    stale: List[Dict[str, Any]] = []
    for card in _read_existing_arch_cards(repo_root):
        globs = card["affected_files"]
        broken = [g for g in globs if not any(_glob_matches(fp, g) for fp in all_files)]
        matched_files = [fp for fp in all_files if any(_glob_matches(fp, g) for g in globs)]
        commits_behind = 0
        if in_git and card["doc_status"] == "documented" and card["last_verified_commit"] and matched_files:
            commits_behind = _commits_since_for_paths(repo_root, card["last_verified_commit"], matched_files)

        reasons: List[str] = []
        if broken:
            reasons.append(f"broken affected_files globs: {', '.join(broken[:3])}")
        if commits_behind >= 5:
            reasons.append(f"{commits_behind} commits behind `{card['last_verified_commit'][:8]}`")
        if card["doc_status"] == "stale" and not reasons:
            reasons.append("marked doc_status: stale")
        if reasons:
            stale.append({
                "file": card["rel"],
                "doc_status": card["doc_status"],
                "broken_globs": broken,
                "commits_behind": commits_behind,
                "reason": "; ".join(reasons),
            })
    return stale


def _filter_doc_recommendations(modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return prioritized modules needing architecture docs or inline docblock enrichment."""
    recs: List[Dict[str, Any]] = []
    for mod in modules:
        sym_count = int(mod.get("symbol_count", 0))
        doc_count = int(mod.get("documented_symbol_count", 0))
        undoc_count = int(mod.get("undocumented_symbols", 0))
        low_docblocks = sym_count > 0 and undoc_count >= 3 and (doc_count / sym_count) < 0.5
        if mod["doc_status"] in ("missing", "scaffold", "stale") or low_docblocks:
            reason = f"doc_status={mod['doc_status']}" if mod["doc_status"] != "documented" else "low_inline_docblocks"
            recs.append({**mod, "recommendation_reason": reason})
    return recs


def audit_hygiene(repo_root: Path) -> Dict[str, Any]:
    """Identify stray root clutter, bulky specs, stale cards, and prioritized doc gaps."""
    in_git = _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"]) == "true"
    protected_dirty: List[str] = []
    stray_root_files = _scan_stray_root_files(repo_root, in_git, protected_dirty)
    bulky_specs = _scan_bulky_specs(repo_root, in_git, protected_dirty)
    missing_okf = _scan_missing_okf(repo_root)
    _, _, all_files = _collect_repo_files(repo_root)
    stale_cards = _scan_stale_cards(repo_root, in_git, all_files)
    doc_recommendations = _filter_doc_recommendations(discover_modules(repo_root))
    return {
        "repo_root": str(repo_root),
        "stray_root_files": stray_root_files,
        "un_dehydrated_specs": bulky_specs,
        "missing_okf_coverage": missing_okf,
        "stale_cards": stale_cards,
        "doc_recommendations": doc_recommendations,
        "protected_dirty_files": sorted(set(protected_dirty)),
        "total_findings": len(stray_root_files) + len(bulky_specs) + len(missing_okf) + len(stale_cards),
        "recommendation_count": len(doc_recommendations),
    }


def _extract_first_summary(body: str) -> str:
    """Pull a concise 1-2 sentence summary from a spec markdown body."""
    cleaned_lines: List[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "---", "```", "|", "<!--")):
            continue
        cleaned_lines.append(re.sub(r"^\s*[-*]\s+", "", s))
        if len(" ".join(cleaned_lines)) >= 220:
            break
    summary = " ".join(cleaned_lines).strip()
    if len(summary) > 260:
        summary = summary[:257].rstrip() + "..."
    return summary or "Original specification archived to Git history; inspect historical commit for full details."


def _verify_spec_committed_and_clean(resolved_root: Path, rel_spec: str) -> str:
    """Verify `rel_spec` is clean and committed in Git, returning its latest commit SHA."""
    in_git = _run_git(resolved_root, ["rev-parse", "--is-inside-work-tree"]) == "true"
    porcelain = _git_porcelain_for_path(resolved_root, rel_spec) if in_git else None
    commit_sha = _run_git(resolved_root, ["log", "-n", "1", "--format=%H", "--", rel_spec]) if in_git else None
    if not commit_sha and in_git:
        commit_sha = _run_git(resolved_root, ["rev-parse", "HEAD"])
    in_blob = bool(commit_sha and _run_git(resolved_root, ["cat-file", "-e", f"{commit_sha}:{rel_spec}"]) is not None)
    if not in_git or porcelain != "" or not commit_sha or not in_blob:
        raise ValueError(f"Refusing to dehydrate '{rel_spec}': uncommitted changes or not in Git HEAD.")
    return commit_sha


def _build_dehydrated_stub(title: str, summary: str, rel_spec: str, commit_sha: str, snapshot_url: str, living_doc: Optional[str]) -> str:
    """Render compact commit-linked stub markdown replacing a dehydrated spec."""
    today = datetime.date.today().isoformat()
    living_line = f"- **Living Architecture Docs:** [`{living_doc}`]({living_doc})\n" if living_doc else "- **Living Architecture Docs:** See [`docs/index.md`](docs/index.md)\n"
    living_yaml = f'"{living_doc}"' if living_doc else '"docs/index.md"'
    escaped_title = title.replace('"', '\\"')
    return f"""---
type: Dehydrated Spec Stub
title: "{escaped_title}"
status: archived
dehydrated: true
archived_at: "{today}"
last_full_commit: "{commit_sha}"
historical_snapshot: "{snapshot_url}"
living_docs: {living_yaml}
---

# {title} *(Archived Spec Stub)*

> **Status:** Shipped & dehydrated on `{today}`. Full historical spec removed to keep repository docs concise.

## Summary
{summary}

## Recovery & Living Context
- **Last Full Spec Commit:** `{commit_sha}` ([Historical Snapshot]({snapshot_url}))
- **Restore via Git:** `git show {commit_sha}:{rel_spec}`
{living_line}"""


def _resolve_spec_target(abs_spec: Path, repo_root: Optional[Path]) -> Tuple[Path, str]:
    """Resolve repository root and POSIX relative spec path for dehydration."""
    if repo_root:
        resolved_root = repo_root.resolve()
    else:
        git_top = _run_git(abs_spec.parent, ["rev-parse", "--show-toplevel"])
        resolved_root = Path(git_top).resolve() if git_top else abs_spec.parent
    try:
        return resolved_root, abs_spec.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_root, abs_spec.name


def dehydrate_spec(spec_path: Path, repo_root: Optional[Path] = None, living_doc: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Collapse a shipped PRD/spec markdown file into a compact commit-linked stub."""
    abs_spec = spec_path.resolve()
    if not abs_spec.is_file():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    resolved_root, rel_spec = _resolve_spec_target(abs_spec, repo_root)
    commit_sha = _verify_spec_committed_and_clean(resolved_root, rel_spec)
    raw_text = abs_spec.read_text(encoding="utf-8")
    meta, body = _parse_simple_frontmatter(raw_text)
    heading_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = str(meta.get("title") or (heading_match.group(1).strip() if heading_match else abs_spec.stem))
    resolver_mod = _load_git_link_resolver(repo_root=resolved_root)
    snapshot_url = resolver_mod.resolve_portable_link(rel_spec, repo_root=str(resolved_root), ref=commit_sha) if resolver_mod else f"{rel_spec}@{commit_sha[:12]}"
    stub = _build_dehydrated_stub(title, _extract_first_summary(body), rel_spec, commit_sha, snapshot_url, living_doc)
    if not dry_run:
        abs_spec.write_text(stub, encoding="utf-8")
    return {"spec_file": rel_spec, "title": title, "last_full_commit": commit_sha, "historical_snapshot": snapshot_url, "original_lines": len(raw_text.splitlines()), "stub_lines": len(stub.splitlines()), "dry_run": dry_run}


def _print_hygiene_report(target: Path, report: Dict[str, Any], as_json: bool) -> None:
    """Print JSON or human-readable hygiene audit findings."""
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"📋 Repo Hygiene Audit (`{target.name}`): {report['total_findings']} finding(s), {report.get('recommendation_count', 0)} doc recommendation(s)")
    for key, label in (("stray_root_files", "Stray root file"), ("missing_okf_coverage", "OKF gap"), ("protected_dirty_files", "Protected dirty/untracked file")):
        for val in report[key]:
            print(f"  - {label}: `{val}`" if key != "missing_okf_coverage" else f"  - {label}: {val}")
    for spec in report["un_dehydrated_specs"]:
        print(f"  - Bulky spec ({spec['body_lines']} lines): `{spec['file']}`")
    for stale in report.get("stale_cards", []):
        print(f"  - Stale card: `{stale['file']}` ({stale['reason']})")
    for rec in report.get("doc_recommendations", [])[:5]:
        print(f"  - [{rec['severity']}] Doc gap `{rec['module']}` (status={rec['doc_status']}, callers={rec['inbound_callers']}, undoc_syms={rec['undocumented_symbols']})")


def _print_recommend_docs(target: Path, as_json: bool) -> None:
    """Run module discovery and print ranked documentation recommendations."""
    modules = discover_modules(target)
    recs = _filter_doc_recommendations(modules)
    report = {
        "repo_root": str(target),
        "modules_analyzed": len(modules),
        "recommendation_count": len(recs),
        "doc_recommendations": recs,
    }
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"📚 Documentation Recommendations (`{target.name}`): {len(recs)} of {len(modules)} modules need docs")
    for rec in recs:
        print(
            f"  - [{rec['severity']}] `{rec['module']}` -> `{rec['card_path']}` "
            f"(score={rec['priority_score']}, status={rec['doc_status']}, callers={rec['inbound_callers']}, undoc_syms={rec['undocumented_symbols']}/{rec['symbol_count']})"
        )


def _print_impact_report(report: Dict[str, Any], as_json: bool) -> None:
    """Print JSON or human-readable pre-edit file impact summary."""
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"🎯 Pre-Edit Impact (`{report['target_file']}`):")
    print(f"  - OKF cards: {', '.join(c['file'] for c in report['matching_okf_cards']) or 'none'}")
    print(f"  - Direct importers ({len(report['direct_importers'])}): {', '.join(report['direct_importers'][:8]) or 'none'}")
    print(f"  - Matching tests: {', '.join(report['matching_tests'][:6]) or 'none'}")
    co_str = ", ".join(f"{item['file']} ({item['cochanges']}x)" for item in report["git_co_changed_files"][:6])
    print(f"  - Git co-changed files: {co_str or 'none'}")
    print(f"  - Env vars: {', '.join(report['env_vars']) or 'none'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold and audit repo-local `<repo>/docs/` OKF architecture docs.")
    parser.add_argument("--scan", nargs="?", const=".", help="Scan repo and scaffold/update `<repo>/docs/`")
    parser.add_argument("--audit-hygiene", nargs="?", const=".", help="Audit stray root files, bulky specs, stale cards, and OKF gaps")
    parser.add_argument("--recommend-docs", nargs="?", const=".", help="Rank undocumented modules by import fan-in, co-change, and doc coverage")
    parser.add_argument("--impact", help="Analyze pre-edit blast radius (OKF cards, direct importers, tests, Git co-changes) for a file")
    parser.add_argument("--dehydrate-spec", help="Collapse a shipped PRD/spec file into a commit-linked stub")
    parser.add_argument("--living-doc", help="Optional path to replacement living doc card under `docs/architecture/`")
    parser.add_argument("--repo-root", default=None, help="Explicit repository root path")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()
    if args.dehydrate_spec:
        root_p = Path(args.repo_root).resolve() if args.repo_root else None
        try:
            res = dehydrate_spec(Path(args.dehydrate_spec), repo_root=root_p, living_doc=args.living_doc, dry_run=args.dry_run)
        except (ValueError, FileNotFoundError) as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 2
        print(json.dumps(res, indent=2) if args.json else f"✅ Dehydrated `{res['spec_file']}` ({res['original_lines']} -> {res['stub_lines']} lines, commit `{res['last_full_commit'][:12]}`).")
        return 0
    if args.impact:
        target = Path(args.repo_root or ".").resolve()
        _print_impact_report(analyze_file_impact(target, args.impact), args.json)
        return 0
    if args.recommend_docs is not None:
        target = Path(args.repo_root or args.recommend_docs).resolve()
        _print_recommend_docs(target, args.json)
        return 0
    if args.audit_hygiene is not None:
        target = Path(args.repo_root or args.audit_hygiene).resolve()
        _print_hygiene_report(target, audit_hygiene(target), args.json)
        return 0
    result = scan_and_scaffold(Path(args.repo_root or args.scan or ".").resolve())
    print(json.dumps(result, indent=2) if args.json else f"✅ Scaffolded OKF docs in `{result['index_file']}` (stacks: {', '.join(result['detected_stacks']) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
