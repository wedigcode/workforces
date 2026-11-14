#!/usr/bin/env python3
"""
Repository Living OKF Documentation & Hygiene Tool (`<repo>/docs/`)

Maintains agent-readable Open Knowledge Format (OKF) architecture docs directly
inside `<repo>/docs/` so any AI coding harness benefits—even without Workforces installed.

Subcommands / Modes:
  --scan <repo>            Non-destructively scaffold/update `<repo>/docs/index.md` and
                           starter `docs/architecture/*.md` cards with `affected_files:`.
  --audit-hygiene <repo>   Audit stray root files, bulky shipped PRDs needing dehydration,
                           and architecture directories missing OKF `affected_files` coverage.
  --dehydrate-spec <file>  Collapse a shipped PRD/spec into a compact stub linking to
                           the exact pre-dehydration Git commit SHA and living docs.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


IGNORE_DIRS = frozenset({
    ".git", ".worktrees", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "dist", "build", ".next", "target", ".agents",
    ".claude", ".grok", ".github", "workforces",
})

STANDARD_ROOT_FILES = frozenset({
    "readme.md", "license", "license.md", "license.txt", "contributing.md",
    "code_of_conduct.md", "security.md", "changelog.md", "agents.md",
    "gemini.md", "claude.md", "makefile", "dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "template.yaml", "template.yml", "samconfig.toml",
    "serverless.yml", "serverless.yaml", "package.json", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "tsconfig.json", "composer.json", "composer.lock",
    "go.mod", "go.sum", "cargo.toml", "cargo.lock", "pyproject.toml", "setup.py",
    "requirements.txt", "update.sh", "install.sh",
})

AUTO_START = "<!-- wf-okf:auto-start -->"
AUTO_END = "<!-- wf-okf:auto-end -->"


def _load_git_link_resolver():
    """Dynamically load sibling `git_link_resolver` without requiring package installs."""
    here = Path(__file__).resolve().parent
    candidate = here.parent.parent / "wf-management" / "scripts" / "git_link_resolver.py"
    if not candidate.is_file():
        return None
    spec = importlib.util.spec_from_file_location("wf_git_link_resolver", str(candidate))
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _run_git(repo_root: Path, args: List[str]) -> Optional[str]:
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_root)] + args,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _detect_stacks(repo_root: Path) -> List[Dict[str, Any]]:
    """Identify primary code stacks and IaC descriptors in `repo_root`."""
    stacks: List[Dict[str, Any]] = []

    if (repo_root / "composer.json").is_file():
        globs = ["src/**/*.php", "app/**/*.php", "config/**/*"]
        subscriber_hits = _find_matching_files(repo_root, ("*Subscriber*.php", "*Listener*.php", "*Notifier*.php"))
        stacks.append({
            "slug": "php-backend",
            "title": "PHP Services & Event Subscribers",
            "description": "PHP domain services, controllers, and event subscribers/listeners.",
            "globs": globs,
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
            "entrypoints": [p for p in py_files if not p.startswith("tests/")][:10],
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


def _render_card_markdown(stack: Dict[str, Any], repo_root: Path, resolver_mod: Any) -> str:
    """Build a starter `<repo>/docs/architecture/<slug>.md` OKF card."""
    today = datetime.date.today().isoformat()
    affected_yaml = "\n".join(f'  - "{g}"' for g in stack["globs"])
    tags_yaml = ", ".join(stack["tags"])

    entry_lines: List[str] = []
    for rel in stack["entrypoints"]:
        abs_target = repo_root / rel
        href = resolver_mod.resolve_portable_link(str(abs_target), repo_root=str(repo_root)) if resolver_mod else rel
        doc_hint = _extract_summary_docblock(abs_target) if abs_target.is_file() else ""
        suffix = f" — {doc_hint}" if doc_hint else ""
        entry_lines.append(f"- [`{rel}`]({href}){suffix}")
    entries_block = "\n".join(entry_lines) if entry_lines else "- _No matching entrypoints auto-detected yet._"

    return f"""---
type: Architecture Component
title: "{stack['title']}"
description: "{stack['description']}"
affected_files:
{affected_yaml}
tags: [{tags_yaml}]
updated_at: "{today}"
---

# {stack['title']}

## Overview
{stack['description']}

## Key Entrypoints & Subscribers
{entries_block}

## Environment & Deployment Config
- Verify all required environment variables against IaC / deployment manifests (`template.yaml`, `samconfig.toml`, `.env.example`) before deploying.
- Never hardcode `"prod"` or `"production"` fallback values in application code.

## Constraints & Why
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

Start here before planning cross-service changes, event subscribers, or environment config updates.

## Auto-Discovered Architecture Map

{wrapped}

## Human Architecture Notes
_Add system diagrams, ownership notes, and cross-service conventions here; automated scans preserve this section._
"""


def scan_and_scaffold(repo_root: Path) -> Dict[str, Any]:
    """Scan `repo_root` and non-destructively scaffold `<repo>/docs/index.md` and starter cards."""
    resolver_mod = _load_git_link_resolver()
    stacks = _detect_stacks(repo_root)
    docs_dir = repo_root / "docs"
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)

    created_cards: List[str] = []
    preserved_cards: List[str] = []
    table_rows = [
        "| Component | Description | Affected Files | Card |",
        "|---|---|---|---|",
    ]

    for stack in stacks:
        card_rel = f"docs/architecture/{stack['slug']}.md"
        card_path = repo_root / card_rel
        if not card_path.exists():
            card_path.write_text(_render_card_markdown(stack, repo_root, resolver_mod), encoding="utf-8")
            created_cards.append(card_rel)
        else:
            preserved_cards.append(card_rel)
        card_href = (
            resolver_mod.resolve_portable_link(str(card_path), repo_root=str(repo_root))
            if resolver_mod
            else f"architecture/{stack['slug']}.md"
        )
        globs_str = ", ".join(f"`{g}`" for g in stack["globs"][:3])
        table_rows.append(f"| **{stack['title']}** | {stack['description']} | {globs_str} | [{stack['slug']}.md]({card_href}) |")

    index_path = docs_dir / "index.md"
    existing_index = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    auto_block = "\n".join(table_rows) if stacks else "_No standard language or IaC manifests detected yet._"
    updated_index = _merge_index_auto_section(existing_index, auto_block)
    index_path.write_text(updated_index, encoding="utf-8")

    return {
        "repo_root": str(repo_root),
        "index_file": "docs/index.md",
        "created_cards": created_cards,
        "preserved_cards": preserved_cards,
        "detected_stacks": [s["slug"] for s in stacks],
    }


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


def audit_hygiene(repo_root: Path) -> Dict[str, Any]:
    """Identify stray root clutter, bulky shipped PRDs needing dehydration, and missing OKF docs."""
    stray_root_files: List[str] = []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        lower = entry.name.lower()
        if lower in STANDARD_ROOT_FILES:
            continue
        if lower.endswith((".md", ".txt", ".log", ".bak", ".tmp")):
            stray_root_files.append(entry.name)

    bulky_specs: List[Dict[str, Any]] = []
    docs_dir = repo_root / "docs"
    search_roots = [docs_dir, repo_root / "workforces"]
    for base in search_roots:
        if not base.is_dir():
            continue
        for md_path in sorted(base.rglob("*.md")):
            if "node_modules" in md_path.parts or ".worktrees" in md_path.parts:
                continue
            rel = md_path.relative_to(repo_root).as_posix()
            name_lower = md_path.name.lower()
            try:
                content = md_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            meta, body = _parse_simple_frontmatter(content)
            if meta.get("dehydrated") is True:
                continue
            is_spec_like = any(tok in name_lower for tok in ("prd", "spec", "proposal", "rfc")) or (
                str(meta.get("status", "")).lower() in ("shipped", "completed", "implemented", "archived")
            )
            line_count = len(body.splitlines())
            if is_spec_like and line_count > 60:
                bulky_specs.append({"file": rel, "body_lines": line_count, "status": meta.get("status", "unknown")})

    missing_okf: List[str] = []
    if not (docs_dir / "index.md").is_file():
        missing_okf.append("Missing `<repo>/docs/index.md` repository architecture index.")
    arch_dir = docs_dir / "architecture"
    covered_globs: List[str] = []
    if arch_dir.is_dir():
        for card in arch_dir.rglob("*.md"):
            meta, _ = _parse_simple_frontmatter(card.read_text(encoding="utf-8", errors="ignore"))
            aff = meta.get("affected_files") or []
            if isinstance(aff, list):
                covered_globs.extend(aff)

    key_dirs = ["src/Service", "src/EventSubscriber", "src/EventListener", "internal", "cmd", "apps"]
    for kd in key_dirs:
        if (repo_root / kd).exists():
            sample = f"{kd}/sample.file"
            if not any(fnmatch(sample, g) or fnmatch(kd, g.rstrip("/*")) for g in covered_globs):
                missing_okf.append(f"Directory `{kd}` has no matching `affected_files:` card under `docs/architecture/`.")

    return {
        "repo_root": str(repo_root),
        "stray_root_files": stray_root_files,
        "un_dehydrated_specs": bulky_specs,
        "missing_okf_coverage": missing_okf,
        "total_findings": len(stray_root_files) + len(bulky_specs) + len(missing_okf),
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


def dehydrate_spec(
    spec_path: Path,
    repo_root: Optional[Path] = None,
    living_doc: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Collapse a shipped PRD/spec markdown file into a compact commit-linked stub."""
    abs_spec = spec_path.resolve()
    if not abs_spec.is_file():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    resolved_root = repo_root.resolve() if repo_root else None
    if not resolved_root:
        git_top = _run_git(abs_spec.parent, ["rev-parse", "--show-toplevel"])
        resolved_root = Path(git_top).resolve() if git_top else abs_spec.parent

    try:
        rel_spec = abs_spec.relative_to(resolved_root).as_posix()
    except ValueError:
        rel_spec = abs_spec.name

    raw_text = abs_spec.read_text(encoding="utf-8")
    meta, body = _parse_simple_frontmatter(raw_text)

    heading_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = str(meta.get("title") or (heading_match.group(1).strip() if heading_match else abs_spec.stem))
    summary = _extract_first_summary(body)

    commit_sha = _run_git(resolved_root, ["log", "-n", "1", "--format=%H", "--", rel_spec])
    if not commit_sha:
        commit_sha = _run_git(resolved_root, ["rev-parse", "HEAD"]) or "HEAD"

    resolver_mod = _load_git_link_resolver()
    if resolver_mod:
        snapshot_url = resolver_mod.resolve_portable_link(
            rel_spec, repo_root=str(resolved_root), ref=commit_sha
        )
    else:
        snapshot_url = f"{rel_spec}@{commit_sha[:12]}"

    today = datetime.date.today().isoformat()
    living_line = (
        f"- **Living Architecture Docs:** [`{living_doc}`]({living_doc})\n"
        if living_doc
        else "- **Living Architecture Docs:** See [`docs/index.md`](docs/index.md)\n"
    )
    living_yaml = f'"{living_doc}"' if living_doc else '"docs/index.md"'

    stub = f"""---
type: Dehydrated Spec Stub
title: "{title.replace('"', '\\"')}"
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

    original_lines = len(raw_text.splitlines())
    stub_lines = len(stub.splitlines())
    if not dry_run:
        abs_spec.write_text(stub, encoding="utf-8")

    return {
        "spec_file": rel_spec,
        "title": title,
        "last_full_commit": commit_sha,
        "historical_snapshot": snapshot_url,
        "original_lines": original_lines,
        "stub_lines": stub_lines,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold and audit repo-local `<repo>/docs/` OKF architecture docs.")
    parser.add_argument("--scan", nargs="?", const=".", help="Scan repo and scaffold/update `<repo>/docs/`")
    parser.add_argument("--audit-hygiene", nargs="?", const=".", help="Audit stray root files, bulky specs, and OKF gaps")
    parser.add_argument("--dehydrate-spec", help="Collapse a shipped PRD/spec file into a commit-linked stub")
    parser.add_argument("--living-doc", help="Optional path to replacement living doc card under `docs/architecture/`")
    parser.add_argument("--repo-root", default=None, help="Explicit repository root path")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    if args.dehydrate_spec:
        root_p = Path(args.repo_root).resolve() if args.repo_root else None
        result = dehydrate_spec(Path(args.dehydrate_spec), repo_root=root_p, living_doc=args.living_doc, dry_run=args.dry_run)
        print(json.dumps(result, indent=2) if args.json else f"✅ Dehydrated `{result['spec_file']}` ({result['original_lines']} -> {result['stub_lines']} lines, commit `{result['last_full_commit'][:12]}`).")
        return 0

    if args.audit_hygiene is not None:
        target = Path(args.repo_root or args.audit_hygiene).resolve()
        report = audit_hygiene(target)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"📋 Repo Hygiene Audit (`{target.name}`): {report['total_findings']} finding(s)")
            for f in report["stray_root_files"]:
                print(f"  - Stray root file: `{f}`")
            for s in report["un_dehydrated_specs"]:
                print(f"  - Bulky spec ({s['body_lines']} lines): `{s['file']}`")
            for m in report["missing_okf_coverage"]:
                print(f"  - OKF gap: {m}")
        return 0

    scan_target = Path(args.repo_root or args.scan or ".").resolve()
    result = scan_and_scaffold(scan_target)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"✅ Scaffolded OKF docs in `{result['index_file']}` (stacks: {', '.join(result['detected_stacks']) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
