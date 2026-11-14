#!/usr/bin/env python3
"""
PreToolUse Deploy & Protected-Branch Safety Hook

Enforces Option A consent gating on shell execution tools:
- Allows local commits, feature branch pushes (`feat/*`, `fix/*`, etc.), and Draft PRs.
- Requires explicit human confirmation (`force_ask` / `ask`) before:
  1. Cloud deployments (`sam deploy`, `ampx`, `serverless deploy`, `cdk deploy`, `terraform apply`, `kubectl apply`, etc.)
  2. Production GitHub actions (`gh pr merge`, `gh workflow run`, `gh release create`)
  3. Force pushes or pushes targeting protected branches (`main`, `master`, `prod`, `production`, `staging`, `develop`, `release/*`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


PROTECTED_BRANCHES = frozenset({
    "main",
    "master",
    "prod",
    "production",
    "staging",
    "stage",
    "develop",
    "dev",
})
PROTECTED_PREFIXES = ("release/", "hotfix/", "prod/", "production/")

_DEPLOY_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsam\s+deploy\b"), "AWS SAM deployment (`sam deploy`)"),
    (re.compile(r"\bampx\s+(?:sandbox|pipeline-deploy|deploy)\b"), "AWS Amplify Gen2 deployment (`ampx`)"),
    (re.compile(r"\bamplify\s+(?:push|publish)\b"), "AWS Amplify deployment (`amplify push/publish`)"),
    (re.compile(r"\b(?:serverless|sls)\s+(?:deploy|remove)\b"), "Serverless Framework deployment/removal"),
    (re.compile(r"\b(?:cdk|sst)\s+(?:deploy|destroy|remove)\b"), "CDK/SST infrastructure deployment"),
    (re.compile(r"\b(?:terraform|tofu)\s+(?:apply|destroy)\b"), "Terraform/OpenTofu state mutation"),
    (re.compile(r"\bpulumi\s+(?:up|destroy)\b"), "Pulumi infrastructure deployment"),
    (re.compile(r"\bkubectl\s+(?:apply|delete|replace|rollout|patch)\b"), "Kubernetes cluster mutation (`kubectl`)"),
    (re.compile(r"\bhelm\s+(?:install|upgrade|uninstall|rollback)\b"), "Helm release mutation"),
    (re.compile(r"\baws\s+cloudformation\s+(?:deploy|create-stack|update-stack|delete-stack)\b"), "AWS CloudFormation stack change"),
    (re.compile(r"\baws\s+(?:lambda|ecs|apprunner)\s+update-"), "AWS live service update"),
    (re.compile(r"\bgcloud\s+(?:app|run|functions)\s+deploy\b"), "Google Cloud deployment (`gcloud`)"),
    (re.compile(r"\b(?:vercel|netlify)\b.*--prod\b"), "Production edge deployment (`--prod`)"),
    (re.compile(r"\b(?:fly|flyctl|eb)\s+deploy\b"), "Application platform deployment"),
    (re.compile(r"\brailway\s+up\b"), "Railway deployment (`railway up`)"),
]

_GH_DANGEROUS_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgh\s+pr\s+merge\b"), "Pull Request merge (`gh pr merge`)"),
    (re.compile(r"\bgh\s+workflow\s+run\b"), "GitHub Actions workflow dispatch (`gh workflow run`)"),
    (re.compile(r"\bgh\s+release\s+(?:create|delete)\b"), "GitHub release mutation (`gh release`)"),
]

_BENIGN_OUTER_COMMANDS = frozenset({
    "echo", "printf", "grep", "rg", "ag", "awk", "sed", "cat", "head", "tail",
})
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPER_PREFIXES = frozenset({"sudo", "env", "npx", "bunx", "pnpm", "yarn", "command", "exec", "time"})


def _split_shell_segments(command: str) -> List[str]:
    """Split a shell command string on `&&`, `||`, `;`, `|` outside quotes."""
    segments: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    escaped = False
    i = 0
    while i < len(command):
        ch = command[i]
        if escaped:
            buf.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\" and quote != "'":
            buf.append(ch)
            escaped = True
            i += 1
            continue
        if ch in ("'", '"'):
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
            buf.append(ch)
            i += 1
            continue
        if quote is None:
            if command[i:i + 2] in ("&&", "||"):
                segments.append("".join(buf).strip())
                buf = []
                i += 2
                continue
            if ch in (";", "|", "\n"):
                segments.append("".join(buf).strip())
                buf = []
                i += 1
                continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        segments.append(tail)
    return [s for s in segments if s]


def _unwrap_segment_tokens(segment: str) -> List[str]:
    """Tokenize a command segment and strip env assignments and runner wrappers."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if _ENV_ASSIGN_RE.match(tok) or tok in _WRAPPER_PREFIXES:
            idx += 1
            continue
        break
    return tokens[idx:]


def _is_protected_branch_name(branch: str) -> bool:
    """Return True if a branch name matches protected integration/release targets."""
    clean = branch.strip().lstrip("origin/").removeprefix("refs/heads/")
    lowered = clean.lower()
    if lowered in PROTECTED_BRANCHES:
        return True
    return any(lowered.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def _current_git_branch(cwd: Optional[str]) -> Optional[str]:
    """Inspect current Git branch under `cwd` using a fast read-only check."""
    work_dir = cwd if cwd and os.path.isdir(cwd) else os.getcwd()
    try:
        res = subprocess.run(
            ["git", "-C", work_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _check_git_push(tokens: List[str], cwd: Optional[str]) -> Optional[str]:
    """Evaluate a `git push` command for force flags or protected target branches."""
    if len(tokens) < 2 or os.path.basename(tokens[0]) != "git":
        return None
    sub_idx = 1
    while sub_idx < len(tokens) and tokens[sub_idx].startswith("-"):
        sub_idx += 2 if tokens[sub_idx] in ("-C", "-c", "--git-dir", "--work-tree") else 1
    if sub_idx >= len(tokens) or tokens[sub_idx] != "push":
        return None

    args = tokens[sub_idx + 1:]
    positional: List[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in ("-o", "--push-option", "--repo", "--receive-pack", "--exec"):
            skip_next = True
            continue
        if arg in ("-f", "--force", "--force-with-lease", "--force-if-includes"):
            return f"Force push detected (`{' '.join(tokens)}`). Explicit user consent required."
        if arg in ("--all", "--mirror", "--delete", "-d"):
            return f"Broad or destructive Git push flag (`{arg}`). Explicit user consent required."
        if arg.startswith("-"):
            continue
        positional.append(arg)

    refspecs = positional[1:] if len(positional) >= 2 else []
    for ref in refspecs:
        if ref.startswith("+"):
            return f"Force-refspec push (`{ref}`). Explicit user consent required."
        if ref.startswith(":"):
            return f"Remote branch deletion via push (`{ref}`). Explicit user consent required."
        target_branch = ref.split(":", 1)[1] if ":" in ref else ref
        if target_branch == "HEAD":
            target_branch = _current_git_branch(cwd) or "HEAD"
        if _is_protected_branch_name(target_branch):
            return f"Push targets protected branch `{target_branch}`. Push an isolated feature branch (`feat/*`, `fix/*`) and open a Draft PR instead, or obtain explicit consent."

    if len(positional) <= 1:
        current = _current_git_branch(cwd)
        if current and _is_protected_branch_name(current):
            return f"Implicit `git push` while on protected branch `{current}`. Switch to a feature branch and open a Draft PR, or obtain explicit consent."
    return None


def inspect_command(command: str, cwd: Optional[str] = None) -> Optional[str]:
    """
    Analyze a shell command string and return an escalation reason if explicit user
    confirmation is required; otherwise return None to allow execution.
    """
    if not command or not command.strip():
        return None

    for segment in _split_shell_segments(command):
        tokens = _unwrap_segment_tokens(segment)
        if not tokens:
            continue
        head = os.path.basename(tokens[0])

        # Never flag benign search/print commands or local git commit messages
        if head in _BENIGN_OUTER_COMMANDS:
            continue
        if head == "git" and len(tokens) >= 2 and tokens[1] in ("commit", "status", "diff", "log", "branch", "checkout", "switch", "add", "fetch"):
            continue

        normalized_cmd = " ".join(tokens)
        if head in ("sh", "bash", "zsh") and len(tokens) >= 3 and tokens[1] == "-c":
            nested = inspect_command(tokens[2], cwd=cwd)
            if nested:
                return nested

        push_reason = _check_git_push(tokens, cwd=cwd)
        if push_reason:
            return push_reason

        for pattern, label in _DEPLOY_PATTERNS + _GH_DANGEROUS_PATTERNS:
            if pattern.search(normalized_cmd):
                return f"{label} requires explicit user consent before executing."

    return None


def format_hook_response(reason: Optional[str], tool_name: str = "") -> Dict[str, object]:
    """Format hook JSON response for Claude/Grok (`Bash`) or Antigravity (`run_command`)."""
    is_claude_family = tool_name == "Bash" or bool(os.environ.get("CLAUDE_PROJECT_DIR"))
    if reason:
        message = f"🛑 Consent Gate: {reason}"
        if is_claude_family:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": message,
                }
            }
        return {"decision": "force_ask", "reason": message}

    if is_claude_family:
        return {}
    return {"decision": "allow"}


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return 0

    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, str):
        command = tool_input
        cwd = None
    else:
        command = str(
            tool_input.get("CommandLine")
            or tool_input.get("command")
            or tool_input.get("cmd")
            or ""
        )
        cwd = tool_input.get("Cwd") or tool_input.get("cwd") or payload.get("cwd")

    reason = inspect_command(command, cwd=cwd)
    print(json.dumps(format_hook_response(reason, tool_name=tool_name)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
