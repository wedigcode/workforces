#!/usr/bin/env python3
"""
Configured & Sibling Repository Resolver for `/wf-work`

Resolves target repositories strictly from explicit workspace configuration
(`workforces/config.json`, `workforces/workrules.md`, `workforces/workstate.md`,
and `workforces/projects/*.md`) plus the active workspace Git repo when applicable.
Never scans unconfigured directories on disk.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_CODE_EXTS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".php", ".rs", ".java", ".rb"})
_IGNORE_CODE_DIRS = frozenset({
    ".git", ".agents", ".claude", ".grok", ".github", ".cursor", ".worktrees",
    "workforces", "node_modules", "vendor", "__pycache__", "docs",
})
_REPO_KEY_RE = re.compile(
    r"^(?:-\s+)?(?:tracked_repos|sibling_repos|repos|repositories|projects)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_PATH_KEY_RE = re.compile(
    r"^(?:-\s+)?(?:target_dir|local_path|repo_root|project_root)\s*:\s*[`'\"]?([^`'\"]+)[`'\"]?$",
    re.IGNORECASE,
)
_REMOTE_SLUG_RE = re.compile(r"[:/]([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+?)(?:\.git)?$")


def _git_remote_slug(repo_dir: Path) -> str:
    """Return `owner/repo` from `git remote.origin.url` if available, else empty string."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            m = _REMOTE_SLUG_RE.search(res.stdout.strip().rstrip("/"))
            if m:
                return m.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _workspace_has_code(workspace_root: Path) -> bool:
    """Return True if `workspace_root` contains non-toolkit source code files."""
    for root, dirs, files in os.walk(workspace_root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_CODE_DIRS and not d.startswith(".")]
        if any(Path(fname).suffix.lower() in _CODE_EXTS for fname in files):
            return True
    return False


def _parse_simple_frontmatter(text: str) -> Dict[str, Any]:
    """Extract simple YAML frontmatter keys (scalars, inline lists, and simple dicts)."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_dict: Optional[Dict[str, str]] = None
    for line in parts[1].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            item = stripped[2:].strip()
            meta.setdefault(current_key, [])
            if ":" in item:
                sk, sv = item.split(":", 1)
                current_dict = {sk.strip(): sv.strip().strip("'\"")}
                meta[current_key].append(current_dict)
            else:
                current_dict = None
                meta[current_key].append(item.strip("'\""))
            continue
        if (line.startswith("  ") or line.startswith("\t")) and current_dict is not None and ":" in stripped:
            sk, sv = stripped.split(":", 1)
            current_dict[sk.strip()] = sv.strip().strip("'\"")
            continue
        if ":" in stripped:
            current_dict = None
            k, v = stripped.split(":", 1)
            k, v = k.strip(), v.strip()
            if not v:
                meta[k] = []
                current_key = k
            elif v.startswith("[") and v.endswith("]"):
                current_key = None
                meta[k] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            else:
                current_key = None
                meta[k] = v.strip("'\"")
    return meta


def _parse_markdown_repo_entries(md_path: Path) -> List[Dict[str, str]]:
    """Extract repo entries (`slug` / `path` / `name`) from `workrules.md` or `workstate.md`."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    entries: List[Dict[str, str]] = []
    meta = _parse_simple_frontmatter(text)
    for key in ("tracked_repos", "sibling_repos", "repos", "repositories", "projects"):
        val = meta.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    entries.append({"raw": item.strip()})
                elif isinstance(item, dict):
                    entries.append({
                        "raw": str(item.get("repo") or item.get("slug") or item.get("name") or ""),
                        "path": str(item.get("path") or item.get("local_path") or ""),
                        "name": str(item.get("name") or ""),
                    })
    for key in ("target_dir", "local_path", "repo_root", "project_root"):
        if isinstance(meta.get(key), str) and meta[key].strip():
            entries.append({"path": meta[key].strip()})

    in_repo_section = False
    in_tracked_key = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#+\s*.*(?:tracked\s+repo|sibling\s+repo|repositories|projects)", stripped, re.IGNORECASE):
            in_repo_section = True
            in_tracked_key = False
            continue
        if stripped.startswith("##"):
            in_repo_section = False
            in_tracked_key = False
            continue
        if stripped.startswith("#"):
            continue
        m_key = _REPO_KEY_RE.match(stripped)
        if m_key:
            in_tracked_key = True
            inline = m_key.group(1).strip()
            if inline.startswith("[") and inline.endswith("]"):
                for tok in inline[1:-1].split(","):
                    if tok.strip().strip("'\"`"):
                        entries.append({"raw": tok.strip().strip("'\"`")})
                in_tracked_key = False
            elif inline and not inline.startswith("#"):
                entries.append({"raw": inline.strip("'\"`")})
                in_tracked_key = False
            continue
        m_path = _PATH_KEY_RE.match(stripped)
        if m_path:
            entries.append({"path": m_path.group(1).strip()})
            continue
        if in_tracked_key or in_repo_section:
            m_bullet = re.match(r"^\s*-\s+[`'\"]?([^\s`'\"]+)[`'\"]?", line)
            if m_bullet:
                entries.append({"raw": m_bullet.group(1).strip()})
            elif stripped and not line.startswith((" ", "\t")):
                in_tracked_key = False
    return entries


def _collect_raw_config_entries(workspace_root: Path) -> List[Dict[str, str]]:
    """Collect configured repo descriptors across JSON, markdown, and `workforces/projects/`."""
    entries: List[Dict[str, str]] = []
    cfg_path = workspace_root / "workforces" / "config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}
        if isinstance(cfg, dict):
            for key in ("tracked_repos", "sibling_repos", "repos"):
                items = cfg.get(key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, str) and item.strip():
                        entries.append({"raw": item.strip()})
                    elif isinstance(item, dict):
                        entries.append({
                            "raw": str(item.get("slug") or item.get("repo") or item.get("name") or ""),
                            "path": str(item.get("path") or item.get("local_path") or ""),
                            "name": str(item.get("name") or ""),
                        })

    for rel in ("workforces/workrules.md", "workforces/workstate.md", "workrules.md", "workstate.md"):
        cand = workspace_root / rel
        if cand.is_file():
            entries.extend(_parse_markdown_repo_entries(cand))

    proj_dir = workspace_root / "workforces" / "projects"
    if proj_dir.is_dir():
        for pfile in sorted(proj_dir.glob("*.md")):
            if pfile.name.lower() == "readme.md":
                continue
            try:
                meta = _parse_simple_frontmatter(pfile.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            raw_repo = str(meta.get("repo") or meta.get("slug") or "")
            raw_path = str(meta.get("local_path") or meta.get("path") or meta.get("target_dir") or "")
            if raw_repo or raw_path:
                entries.append({"raw": raw_repo, "path": raw_path, "name": str(meta.get("name") or pfile.stem)})
    return entries


def _normalize_slug(raw: str) -> str:
    """Normalize a GitHub/Git URL or `owner/repo` reference into a slug when present."""
    clean = raw.strip().strip("'\"`").rstrip("/")
    if not clean:
        return ""
    if "github.com" in clean or clean.startswith(("git@", "http://", "https://")):
        m = _REMOTE_SLUG_RE.search(clean)
        return m.group(1) if m else ""
    if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", clean) and not clean.startswith(("./", "../", "/")):
        return clean
    return ""


def _match_child_ci(parent: Path, target_name: str, require_git: bool = False) -> Optional[Path]:
    """Find a direct child directory of `parent` matching `target_name` case-insensitively."""
    try:
        entries = sorted(parent.iterdir())
    except OSError:
        return None
    target_low = target_name.lower()
    for child in entries:
        if not child.is_dir() or child.name.lower() != target_low:
            continue
        if require_git and not (child / ".git").exists():
            continue
        return child.resolve()
    return None


def _find_sibling_org_repo(workspace_root: Path, owner: str, repo_name: str) -> Optional[Path]:
    """Locate configured `<owner>/<repo>` under workspace, parent, or sibling-org grandparent dirs."""
    grandparent = workspace_root.parent.parent
    exact_candidates = [
        workspace_root / owner / repo_name,
        workspace_root / "projects" / owner / repo_name,
        workspace_root.parent / owner / repo_name,
    ]
    if grandparent != workspace_root.parent:
        exact_candidates.append(grandparent / owner / repo_name)
    for cand in exact_candidates:
        if cand.is_dir():
            return cand.resolve()

    org_parents = [workspace_root.parent]
    if grandparent != workspace_root.parent:
        org_parents.append(grandparent)
    for org_parent in org_parents:
        org_dir = _match_child_ci(org_parent, owner)
        if org_dir is None:
            continue
        sib = _match_child_ci(org_dir, repo_name, require_git=True)
        if sib is not None:
            return sib
    return None


def _resolve_entry_dir(workspace_root: Path, entry: Dict[str, str], root_slug: str) -> Tuple[Optional[Path], str, str]:
    """Resolve one configured entry to `(existing_dir, slug, display_name)` or `(None, '', '')`."""
    raw = entry.get("raw", "").strip()
    path_hint = entry.get("path", "").strip()
    explicit_name = entry.get("name", "").strip()
    slug = _normalize_slug(raw)

    if not path_hint and raw and (raw.startswith(("/", "./", "../")) or Path(raw).name == raw and not slug):
        path_hint = raw

    if path_hint:
        p = Path(path_hint)
        cand = p.resolve() if p.is_absolute() else (workspace_root / p).resolve()
        if not cand.is_dir() and not p.is_absolute():
            for base in (workspace_root.parent, workspace_root.parent.parent):
                sib = (base / p).resolve()
                if sib.is_dir():
                    cand = sib
                    break
        if cand.is_dir():
            resolved_slug = slug or _git_remote_slug(cand)
            return cand, resolved_slug, explicit_name or cand.name
        return None, "", ""

    if not slug:
        return None, "", ""

    owner, repo_name = slug.split("/", 1)
    if root_slug.lower() == slug.lower() or workspace_root.name.lower() == repo_name.lower():
        return workspace_root.resolve(), slug, explicit_name or workspace_root.name

    for cand in (
        workspace_root / repo_name,
        workspace_root / "projects" / repo_name,
        workspace_root.parent / repo_name,
    ):
        if cand.is_dir():
            return cand.resolve(), slug, explicit_name or cand.name

    sib = _match_child_ci(workspace_root.parent, repo_name, require_git=True)
    if sib is not None:
        return sib, slug, explicit_name or sib.name

    org_match = _find_sibling_org_repo(workspace_root, owner, repo_name)
    if org_match is not None:
        return org_match, slug, explicit_name or org_match.name
    return None, "", ""


def _build_repo_record(resolved_dir: Path, workspace_root: Path, slug: str, name: str) -> Dict[str, Any]:
    """Build normalized metadata dictionary for one resolved repository directory."""
    final_slug = slug or _git_remote_slug(resolved_dir) or resolved_dir.name
    return {
        "name": name or resolved_dir.name,
        "slug": final_slug,
        "path": str(resolved_dir),
        "is_workspace_root": resolved_dir == workspace_root.resolve(),
        "has_docs_index": (resolved_dir / "docs" / "index.md").is_file(),
    }


def discover_configured_repos(workspace_root: Path) -> List[Dict[str, Any]]:
    """Return deduplicated local repositories configured for `workspace_root`."""
    ws_resolved = workspace_root.resolve()
    root_slug = _git_remote_slug(ws_resolved)
    raw_entries = _collect_raw_config_entries(ws_resolved)

    discovered: List[Dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for entry in raw_entries:
        resolved_dir, slug, name = _resolve_entry_dir(ws_resolved, entry, root_slug)
        if resolved_dir is None or resolved_dir in seen_paths:
            continue
        seen_paths.add(resolved_dir)
        discovered.append(_build_repo_record(resolved_dir, ws_resolved, slug, name))

    if ws_resolved not in seen_paths and (not discovered or _workspace_has_code(ws_resolved)):
        discovered.insert(0, _build_repo_record(ws_resolved, ws_resolved, root_slug, ws_resolved.name))
    return discovered


def _match_single_repo(candidates: List[Dict[str, Any]], workspace_root: Path, repo_arg: str) -> Optional[Dict[str, Any]]:
    """Match `repo_arg` against `candidates` by name, slug, repo basename, or local path."""
    needle = repo_arg.strip()
    low = needle.lower().rstrip("/")
    cand_paths = {
        Path(needle).resolve() if Path(needle).is_absolute() else (workspace_root / needle).resolve(),
        (workspace_root.parent / needle).resolve(),
        (workspace_root.parent.parent / needle).resolve(),
    }
    for item in candidates:
        item_path = Path(item["path"]).resolve()
        slug_tail = item["slug"].split("/")[-1].lower()
        if (
            item["name"].lower() == low
            or item["slug"].lower() == low
            or slug_tail == low
            or item_path in cand_paths
        ):
            return item
    return None


def resolve_repo_targets(workspace_root: Path, repo_arg: Optional[str] = None) -> Dict[str, Any]:
    """Resolve target repository list or signal multi-repo ambiguity for user clarification."""
    ws_resolved = workspace_root.resolve()
    candidates = discover_configured_repos(ws_resolved)

    if repo_arg and repo_arg.strip():
        cleaned = repo_arg.strip()
        if cleaned.lower() == "all":
            return {"status": "resolved", "targets": candidates, "scope": "all"}
        matched = _match_single_repo(candidates, ws_resolved, cleaned)
        if matched is not None:
            return {"status": "resolved", "targets": [matched], "scope": "single"}
        return {
            "status": "ambiguous",
            "reason": "unknown_repo",
            "requested": cleaned,
            "available_repos": candidates,
        }

    if len(candidates) <= 1:
        return {"status": "resolved", "targets": candidates, "scope": "single"}

    return {
        "status": "ambiguous",
        "reason": "multiple_repos_configured",
        "available_repos": candidates,
    }
