#!/usr/bin/env python3
"""
Portable Git Link Resolver

Converts local file paths and Git metadata into host-agnostic remote source URLs
(GitHub, GitLab, Bitbucket, Azure DevOps, Gitea/Codeberg/Forgejo) or clean
repository-relative POSIX paths. Never emits `file://` URIs or OS home paths.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import Dict, Optional
from urllib.parse import urlparse


_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_SCP_RE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(.+)$")


def _classify_provider(host: str) -> str:
    """Determine Git forge provider from hostname."""
    lowered = host.lower()
    if "github" in lowered:
        return "github"
    if "gitlab" in lowered:
        return "gitlab"
    if "bitbucket" in lowered:
        return "bitbucket"
    if "dev.azure.com" in lowered or "visualstudio.com" in lowered:
        return "azure"
    if "gitea" in lowered or "codeberg" in lowered or "forgejo" in lowered:
        return "gitea"
    return "github"


def _strip_git_suffix(path: str) -> str:
    """Normalize repository path by stripping leading/trailing slashes and `.git`."""
    cleaned = path.strip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned.strip("/")


def _parse_azure_path(host: str, raw_path: str) -> Optional[Dict[str, str]]:
    """Parse Azure DevOps SSH or HTTPS remote paths."""
    cleaned = _strip_git_suffix(raw_path)
    parts = [p for p in cleaned.split("/") if p]
    if "ssh.dev.azure.com" in host.lower() or "vs-ssh.visualstudio.com" in host.lower():
        if len(parts) >= 4 and parts[0] == "v3":
            org, proj, repo = parts[1], parts[2], parts[3]
            return {
                "provider": "azure",
                "host": "dev.azure.com",
                "owner_repo": f"{org}/{proj}/_git/{repo}",
                "scheme": "https",
            }
        return None

    if "visualstudio.com" in host.lower():
        org = host.split(".")[0]
        if "_git" in parts:
            idx = parts.index("_git")
            proj = parts[idx - 1] if idx >= 1 else "DefaultProject"
            repo = parts[idx + 1] if idx + 1 < len(parts) else ""
        elif len(parts) >= 2:
            proj, repo = parts[0], parts[1]
        else:
            return None
        if not repo:
            return None
        return {
            "provider": "azure",
            "host": "dev.azure.com",
            "owner_repo": f"{org}/{proj}/_git/{repo}",
            "scheme": "https",
        }

    if "_git" in parts:
        idx = parts.index("_git")
        if idx >= 2 and idx + 1 < len(parts):
            org, proj, repo = parts[idx - 2], parts[idx - 1], parts[idx + 1]
            return {
                "provider": "azure",
                "host": "dev.azure.com",
                "owner_repo": f"{org}/{proj}/_git/{repo}",
                "scheme": "https",
            }
    return None


def parse_git_remote_url(remote_url: str) -> Optional[Dict[str, str]]:
    """
    Parse a Git remote URL into normalized provider metadata.

    Returns None for local filesystem paths and `file://` remotes.
    """
    raw = (remote_url or "").strip()
    if not raw or raw.startswith("file://") or raw.startswith("/") or raw.startswith("."):
        return None
    if re.match(r"^[A-Za-z]:[/\\]", raw):
        return None

    host = ""
    raw_path = ""
    scheme = "https"

    if "://" in raw:
        parsed = urlparse(raw)
        if parsed.scheme in ("file", ""):
            return None
        host = parsed.hostname or ""
        raw_path = parsed.path or ""
        if parsed.scheme in ("http", "https"):
            scheme = parsed.scheme
    else:
        match = _SCP_RE.match(raw)
        if not match:
            return None
        host, raw_path = match.group(1), match.group(2)

    if not host or not raw_path:
        return None

    provider = _classify_provider(host)
    if provider == "azure":
        return _parse_azure_path(host, raw_path)

    owner_repo = _strip_git_suffix(raw_path)
    if "/" not in owner_repo:
        return None

    return {
        "provider": provider,
        "host": host.lower(),
        "owner_repo": owner_repo,
        "scheme": scheme,
    }


def _run_git(repo_root: str, args: list[str]) -> Optional[str]:
    """Run a quick read-only git command, returning stripped stdout or None."""
    try:
        res = subprocess.run(
            ["git", "-C", repo_root] + args,
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


def find_git_root(start_path: str) -> Optional[str]:
    """Discover the enclosing Git repository root for `start_path`."""
    probe = start_path if os.path.isdir(start_path) else os.path.dirname(os.path.abspath(start_path))
    if not os.path.isdir(probe):
        return None
    return _run_git(probe, ["rev-parse", "--show-toplevel"])


def detect_repo_remote(repo_root: str, remote_name: str = "origin") -> Optional[Dict[str, str]]:
    """Inspect git remotes under `repo_root` and parse the preferred remote URL."""
    url = _run_git(repo_root, ["remote", "get-url", remote_name])
    if url:
        parsed = parse_git_remote_url(url)
        if parsed:
            return parsed

    remotes_out = _run_git(repo_root, ["remote"])
    if not remotes_out:
        return None
    for name in remotes_out.splitlines():
        candidate = _run_git(repo_root, ["remote", "get-url", name.strip()])
        if candidate:
            parsed = parse_git_remote_url(candidate)
            if parsed:
                return parsed
    return None


def detect_default_ref(repo_root: str) -> str:
    """Resolve remote default branch, current branch, HEAD SHA, or `main`."""
    sym = _run_git(repo_root, ["symbolic-ref", "refs/remotes/origin/HEAD"])
    if sym and sym.startswith("refs/remotes/origin/"):
        return sym[len("refs/remotes/origin/"):]
    branch = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch and branch != "HEAD":
        return branch
    sha = _run_git(repo_root, ["rev-parse", "HEAD"])
    if sha:
        return sha
    return "main"


def _strip_local_uri_prefix(target_path: str) -> str:
    """Remove accidental `file://` prefix if passed by legacy callers."""
    if target_path.startswith("file://"):
        return target_path[len("file://"):]
    return target_path


def to_repo_relative_path(target_path: str, repo_root: Optional[str] = None) -> str:
    """
    Normalize `target_path` to a clean POSIX path relative to `repo_root`.

    Never returns `file://` or machine-local home directories.
    """
    cleaned = _strip_local_uri_prefix(target_path).strip()
    if not cleaned:
        return ""

    effective_root = repo_root or find_git_root(cleaned)
    if effective_root:
        real_root = os.path.realpath(effective_root)
        candidate = cleaned if os.path.isabs(cleaned) else os.path.join(real_root, cleaned)
        real_target = os.path.realpath(candidate)
        if real_target == real_root:
            return "."
        if real_target.startswith(real_root + os.sep):
            return os.path.relpath(real_target, real_root).replace(os.sep, "/")

    posix = cleaned.replace("\\", "/")
    if posix.startswith("./"):
        posix = posix[2:]
    if os.path.isabs(posix):
        return os.path.basename(posix) or posix.lstrip("/")
    return posix


def build_blob_url(
    remote_info: Dict[str, str],
    ref: str,
    rel_path: str,
    line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> str:
    """Build a provider-specific web URL pointing to a file blob and optional line range."""
    provider = remote_info["provider"]
    scheme = remote_info.get("scheme", "https")
    host = remote_info["host"]
    owner_repo = remote_info["owner_repo"]
    clean_rel = rel_path.lstrip("/")
    base = f"{scheme}://{host}/{owner_repo}"

    if provider == "gitlab":
        url = f"{base}/-/blob/{ref}/{clean_rel}"
        if line is not None:
            url += f"#L{line}-{end_line}" if end_line and end_line > line else f"#L{line}"
        return url

    if provider == "bitbucket":
        url = f"{base}/src/{ref}/{clean_rel}"
        if line is not None:
            url += f"#lines-{line}:{end_line}" if end_line and end_line > line else f"#lines-{line}"
        return url

    if provider == "azure":
        version_prefix = "GC" if _SHA_RE.match(ref) else "GB"
        url = f"{base}?path=/{clean_rel}&version={version_prefix}{ref}"
        if line is not None:
            end_val = end_line if end_line and end_line >= line else line
            url += f"&line={line}&lineEnd={end_val}&lineStartColumn=1&lineEndColumn=1"
        return url

    if provider == "gitea":
        ref_kind = "commit" if _SHA_RE.match(ref) else "branch"
        url = f"{base}/src/{ref_kind}/{ref}/{clean_rel}"
        if line is not None:
            url += f"#L{line}-L{end_line}" if end_line and end_line > line else f"#L{line}"
        return url

    url = f"{base}/blob/{ref}/{clean_rel}"
    if line is not None:
        url += f"#L{line}-L{end_line}" if end_line and end_line > line else f"#L{line}"
    return url


def build_commit_url(remote_info: Dict[str, str], commit_sha: str) -> str:
    """Build a provider-specific web URL pointing to a Git commit."""
    provider = remote_info["provider"]
    scheme = remote_info.get("scheme", "https")
    base = f"{scheme}://{remote_info['host']}/{remote_info['owner_repo']}"

    if provider == "gitlab":
        return f"{base}/-/commit/{commit_sha}"
    if provider == "bitbucket":
        return f"{base}/commits/{commit_sha}"
    return f"{base}/commit/{commit_sha}"


def resolve_portable_link(
    target_path: str,
    repo_root: Optional[str] = None,
    ref: Optional[str] = None,
    line: Optional[int] = None,
    end_line: Optional[int] = None,
    prefer_remote: bool = True,
    relative_from: Optional[str] = None,
) -> str:
    """
    Resolve a file target to a portable remote Git host URL or repo-relative POSIX path.

    Falls back cleanly to a relative POSIX path if offline or outside a Git repository.
    """
    cleaned = _strip_local_uri_prefix(target_path).strip()
    if not cleaned:
        return "#"

    effective_root = repo_root or find_git_root(cleaned)
    if not effective_root and not os.path.isabs(cleaned):
        cwd_git = find_git_root(os.getcwd())
        if cwd_git:
            effective_root = cwd_git

    if effective_root:
        rel_path = to_repo_relative_path(cleaned, effective_root)
        if not rel_path:
            return "#"
        if prefer_remote:
            remote_info = detect_repo_remote(effective_root)
            if remote_info:
                resolved_ref = ref or detect_default_ref(effective_root)
                return build_blob_url(remote_info, resolved_ref, rel_path, line=line, end_line=end_line)
        target_for_rel = os.path.join(effective_root, rel_path)
    else:
        rel_path = os.path.basename(cleaned) if os.path.isabs(cleaned) else cleaned.replace("\\", "/")
        target_for_rel = cleaned

    if relative_from:
        from_dir = relative_from if os.path.isdir(relative_from) else os.path.dirname(os.path.abspath(relative_from))
        try:
            computed = os.path.relpath(os.path.abspath(target_for_rel), from_dir).replace(os.sep, "/")
            if not computed.startswith("/"):
                rel_path = computed
        except ValueError:
            pass

    if line is not None:
        suffix = f"#L{line}-L{end_line}" if end_line and end_line > line else f"#L{line}"
        return f"{rel_path}{suffix}"
    return rel_path


def resolve_commit_link(commit_sha: str, repo_root: Optional[str] = None) -> str:
    """Return remote commit URL if available, otherwise short SHA reference."""
    effective_root = repo_root or os.getcwd()
    remote_info = detect_repo_remote(effective_root)
    if remote_info:
        return build_commit_url(remote_info, commit_sha)
    return f"commit:{commit_sha[:12]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve portable Git host URLs or repo-relative paths.")
    parser.add_argument("path", help="Target file path")
    parser.add_argument("--repo-root", default=None, help="Repository root path")
    parser.add_argument("--ref", default=None, help="Git ref, branch, or commit SHA")
    parser.add_argument("--line", type=int, default=None, help="Start line number")
    parser.add_argument("--end-line", type=int, default=None, help="End line number")
    parser.add_argument("--relative-only", action="store_true", help="Return repo-relative POSIX path only")
    args = parser.parse_args()

    print(
        resolve_portable_link(
            args.path,
            repo_root=args.repo_root,
            ref=args.ref,
            line=args.line,
            end_line=args.end_line,
            prefer_remote=not args.relative_only,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
