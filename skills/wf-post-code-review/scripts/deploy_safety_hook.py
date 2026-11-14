#!/usr/bin/env python3
"""
PreToolUse Deploy & Protected-Branch Safety Hook

Enforces Option A consent gating on shell execution tools across Antigravity,
Claude Code, and Grok:
- Allows local commits, isolated feature branch pushes (`feat/*`, `fix/*`, etc.), and Draft PRs.
- Fails closed (`force_ask` / `ask`) on malformed/empty hook payloads or unrecognized schemas.
- Requires explicit human confirmation (`force_ask` / `ask`) before:
  1. Cloud deployments (`sam deploy`, `ampx`, `serverless deploy`, `cdk deploy`, `terraform apply`, `kubectl apply`, etc.)
  2. Production GitHub actions (`gh pr merge`, `gh workflow run`, `gh release create`)
  3. Force pushes (`-f`, `--force`, `--force-with-lease=...`) or pushes targeting protected branches (`main`, `master`, `prod`, `production`, `staging`, `develop`, `release/*`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


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
_SAFE_GIT_SUBCOMMANDS = frozenset({
    "commit", "status", "diff", "log", "branch", "checkout", "switch", "add", "fetch", "show",
})
_SHELL_BINARIES = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_COMMAND_KEYS = ("CommandLine", "command", "cmd", "command_line")

_SUDO_VAL_FLAGS = frozenset({
    "-u", "-g", "-C", "-D", "-R", "-T", "-h", "-p", "-r", "-t",
    "--user", "--group", "--chdir", "--chroot", "--other-user", "--prompt", "--role", "--type",
})
_NPX_VAL_FLAGS = frozenset({"-p", "--package", "--cache", "--userconfig", "--registry"})
_PKG_MGR_VAL_FLAGS = frozenset({"-C", "--prefix", "--dir", "--cwd", "-F", "--filter", "-w", "--workspace", "-p", "--package"})
_XARGS_VAL_FLAGS = frozenset({"-n", "-L", "-P", "-I", "-d", "-s", "-E", "--max-args", "--max-lines", "--max-procs", "--replace", "--delimiter"})


def _read_balanced_paren_body(text: str, start: int) -> Tuple[str, int]:
    """Read inside balanced `(...)` starting just after `(`, respecting quotes."""
    depth = 1
    quote: Optional[str] = None
    escaped = False
    i = start
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif ch in ("'", '"'):
            quote = None if quote == ch else (ch if quote is None else quote)
        elif quote != "'":
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i], i + 1
        i += 1
    return text[start:], len(text)


def _read_backtick_body(text: str, start: int) -> Tuple[str, int]:
    """Read inside backtick command substitution starting just after opening backtick."""
    escaped = False
    buf: List[str] = []
    i = start
    while i < len(text):
        ch = text[i]
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "`":
            return "".join(buf), i + 1
        else:
            buf.append(ch)
        i += 1
    return "".join(buf), len(text)


def _extract_command_substitutions(text: str) -> List[str]:
    """Extract shell-expanded `$()`, backtick, and `<()`/`>()` subcommands outside single quotes."""
    subs: List[str] = []
    quote: Optional[str] = None
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if ch == "\\" and quote != "'":
            escaped = True
            i += 1
            continue
        if ch in ("'", '"'):
            quote = None if quote == ch else (ch if quote is None else quote)
            i += 1
            continue
        if quote == "'":
            i += 1
            continue
        if text[i:i + 3] == "$((":
            i += 3
            continue
        if text[i:i + 2] == "$(" or (quote is None and text[i:i + 2] in ("<(", ">(")):
            inner, i = _read_balanced_paren_body(text, i + 2)
            if inner.strip():
                subs.append(inner)
            continue
        if ch == "`":
            inner, i = _read_backtick_body(text, i + 1)
            if inner.strip():
                subs.append(inner)
            continue
        i += 1
    return subs


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
            quote = None if quote == ch else (ch if quote is None else quote)
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


def _consume_generic_options(
    tokens: List[str], idx: int, val_flags: FrozenSet[str] = frozenset()
) -> int:
    """Advance past wrapper `-flag` options and known value-taking option pairs."""
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "--":
            return idx + 1
        if not tok.startswith("-") or tok == "-":
            break
        if tok in val_flags and idx + 1 < len(tokens):
            idx += 2
            continue
        idx += 1
    return idx


def _consume_env_wrapper(tokens: List[str], idx: int) -> List[str]:
    """Consume `env` options (`-i`, `-u VAR`, `-C dir`, `-S str`, `--`) and inline VAR=val."""
    extra_tokens: List[str] = []
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "--":
            idx += 1
            break
        if tok in ("-u", "--unset", "-C", "--chdir") and idx + 1 < len(tokens):
            idx += 2
            continue
        if tok in ("-S", "--split-string") and idx + 1 < len(tokens):
            try:
                extra_tokens = shlex.split(tokens[idx + 1])
            except ValueError:
                extra_tokens = tokens[idx + 1].split()
            idx += 2
            break
        if tok.startswith("--split-string="):
            raw_s = tok.split("=", 1)[1]
            try:
                extra_tokens = shlex.split(raw_s)
            except ValueError:
                extra_tokens = raw_s.split()
            idx += 1
            break
        if tok.startswith("-") and tok != "-":
            idx += 1
            continue
        break
    merged = extra_tokens + tokens[idx:]
    while merged and _ENV_ASSIGN_RE.match(merged[0]):
        merged.pop(0)
    return merged


def _consume_npx_wrapper(
    tokens: List[str], idx: int, extra_cmds: List[str]
) -> int:
    """Consume `npx`/`bunx` flags and capture `-c`/`--call` subcommands."""
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "--":
            return idx + 1
        if tok in ("-c", "--call") and idx + 1 < len(tokens):
            extra_cmds.append(tokens[idx + 1])
            return len(tokens)
        if tok.startswith("--call="):
            extra_cmds.append(tok.split("=", 1)[1])
            return len(tokens)
        if tok in _NPX_VAL_FLAGS and idx + 1 < len(tokens):
            idx += 2
            continue
        if tok.startswith("-") and tok != "-":
            idx += 1
            continue
        break
    return idx


def _try_unwrap_pkg_exec(tokens: List[str]) -> Optional[List[str]]:
    """Unwrap `npm|pnpm|yarn [flags] exec|dlx [command]` if an exec/dlx subcommand is used."""
    probe = _consume_generic_options(tokens, 1, _PKG_MGR_VAL_FLAGS)
    if probe < len(tokens) and tokens[probe] in ("exec", "dlx"):
        after = probe + 1
        if after < len(tokens) and tokens[after] == "--":
            after += 1
        return tokens[after:]
    return None


def _unwrap_segment_tokens(segment: str) -> Tuple[List[str], List[str]]:
    """Strip env assignments and runner wrappers with their options, returning `(tokens, extra_cmds)`."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    extra_cmds: List[str] = []
    while tokens:
        head = os.path.basename(tokens[0])
        if _ENV_ASSIGN_RE.match(tokens[0]):
            tokens.pop(0)
        elif head == "sudo":
            tokens = tokens[_consume_generic_options(tokens, 1, _SUDO_VAL_FLAGS):]
        elif head == "env":
            tokens = _consume_env_wrapper(tokens, 1)
        elif head in ("npx", "bunx"):
            tokens = tokens[_consume_npx_wrapper(tokens, 1, extra_cmds):]
        elif head in ("npm", "pnpm", "yarn"):
            unwrapped = _try_unwrap_pkg_exec(tokens)
            if unwrapped is None:
                break
            tokens = unwrapped
        elif head in ("command", "exec", "nohup", "time", "nice", "timeout", "xargs"):
            val_flags = _XARGS_VAL_FLAGS if head == "xargs" else frozenset({"-a", "-f", "-o", "-n", "-k", "-s"})
            nxt = _consume_generic_options(tokens, 1, val_flags)
            if head == "timeout" and nxt < len(tokens) and re.match(r"^\d+[smhd]?$", tokens[nxt]):
                nxt += 1
            tokens = tokens[nxt:]
        else:
            break
    return tokens, extra_cmds


def _is_protected_branch_name(branch: str) -> bool:
    """Return True if a branch name matches protected integration/release targets."""
    clean = branch.strip().removeprefix("refs/heads/").removeprefix("refs/remotes/").removeprefix("remotes/")
    for remote_prefix in ("origin/", "upstream/"):
        if clean.startswith(remote_prefix):
            clean = clean.removeprefix(remote_prefix)
            break
    clean = clean.removeprefix("refs/heads/")
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


def _git_subcommand_index(tokens: List[str], cwd: Optional[str]) -> Tuple[int, Optional[str]]:
    """Locate the `git` subcommand index while skipping global flags and tracking `-C` cwd."""
    sub_idx = 1
    eff_cwd = cwd
    while sub_idx < len(tokens) and tokens[sub_idx].startswith("-"):
        flag = tokens[sub_idx]
        if flag == "-C" and sub_idx + 1 < len(tokens):
            eff_cwd = tokens[sub_idx + 1]
            sub_idx += 2
        elif flag in ("-c", "--git-dir", "--work-tree", "--namespace"):
            sub_idx += 2
        else:
            sub_idx += 1
    return sub_idx, eff_cwd


def _classify_push_flag(arg: str, tokens: List[str]) -> Tuple[Optional[str], bool]:
    """Check one `git push` flag token; returns `(escalation_reason, takes_next_arg)`."""
    if arg in ("-o", "--push-option", "--repo", "--receive-pack", "--exec"):
        return None, True
    if arg in ("-f", "--force", "--force-with-lease", "--force-if-includes") or arg.startswith(
        ("--force-with-lease=", "--force-if-includes=")
    ):
        return f"Force push detected (`{' '.join(tokens)}`). Explicit user consent required.", False
    if arg in ("--all", "--mirror", "--delete", "-d"):
        return f"Broad or destructive Git push flag (`{arg}`). Explicit user consent required.", False
    if arg.startswith("-") and not arg.startswith("--") and not arg.startswith("-o"):
        if "f" in arg[1:]:
            return f"Force push detected (`{' '.join(tokens)}`). Explicit user consent required.", False
        if "d" in arg[1:]:
            return f"Branch deletion via push flag (`{arg}`). Explicit user consent required.", False
    return None, False


def _check_git_push(tokens: List[str], cwd: Optional[str]) -> Optional[str]:
    """Evaluate a `git push` command for force flags or protected target branches."""
    if len(tokens) < 2 or os.path.basename(tokens[0]) != "git":
        return None
    sub_idx, eff_cwd = _git_subcommand_index(tokens, cwd)
    if sub_idx >= len(tokens) or tokens[sub_idx] != "push":
        return None

    positional: List[str] = []
    skip_next = False
    end_of_opts = False
    for arg in tokens[sub_idx + 1:]:
        if skip_next:
            skip_next = False
            continue
        if not end_of_opts and arg == "--":
            end_of_opts = True
            continue
        if not end_of_opts and arg.startswith("-"):
            reason, takes_val = _classify_push_flag(arg, tokens)
            if reason:
                return reason
            skip_next = takes_val
            continue
        positional.append(arg)

    for ref in (positional[1:] if len(positional) >= 2 else []):
        if ref.startswith("+"):
            return f"Force-refspec push (`{ref}`). Explicit user consent required."
        if ref.startswith(":"):
            return f"Remote branch deletion via push (`{ref}`). Explicit user consent required."
        target_branch = ref.split(":", 1)[1] if ":" in ref else ref
        if target_branch == "HEAD":
            target_branch = _current_git_branch(eff_cwd) or "HEAD"
        if _is_protected_branch_name(target_branch):
            return f"Push targets protected branch `{target_branch}`. Push an isolated feature branch (`feat/*`, `fix/*`) and open a Draft PR instead, or obtain explicit consent."

    if len(positional) <= 1:
        current = _current_git_branch(eff_cwd)
        if current and _is_protected_branch_name(current):
            return f"Implicit `git push` while on protected branch `{current}`. Switch to a feature branch and open a Draft PR, or obtain explicit consent."
    return None


def _extract_shell_c_command(tokens: List[str]) -> Optional[str]:
    """Return nested script passed via `sh|bash|zsh [-flags] -c <script>` if present."""
    if not tokens or os.path.basename(tokens[0]) not in _SHELL_BINARIES:
        return None
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--":
            break
        if tok == "-c" or (tok.startswith("-") and not tok.startswith("--") and "c" in tok[1:]):
            return tokens[i + 1] if i + 1 < len(tokens) else None
        i += 1
    return None


def inspect_command(command: str, cwd: Optional[str] = None) -> Optional[str]:
    """Analyze a shell command string and return an escalation reason if consent is required."""
    if not command or not command.strip():
        return None

    for segment in _split_shell_segments(command):
        for sub_cmd in _extract_command_substitutions(segment):
            nested = inspect_command(sub_cmd, cwd=cwd)
            if nested:
                return nested

        tokens, extra_cmds = _unwrap_segment_tokens(segment)
        for sub_cmd in extra_cmds:
            nested = inspect_command(sub_cmd, cwd=cwd)
            if nested:
                return nested
        if not tokens:
            continue

        head = os.path.basename(tokens[0])
        if head in _BENIGN_OUTER_COMMANDS:
            continue
        if head == "git":
            sub_idx, _ = _git_subcommand_index(tokens, cwd)
            if sub_idx < len(tokens) and tokens[sub_idx] in _SAFE_GIT_SUBCOMMANDS:
                continue

        shell_c = _extract_shell_c_command(tokens)
        if shell_c:
            nested = inspect_command(shell_c, cwd=cwd)
            if nested:
                return nested

        push_reason = _check_git_push(tokens, cwd=cwd)
        if push_reason:
            return push_reason

        normalized_cmd = " ".join(tokens)
        for pattern, label in _DEPLOY_PATTERNS + _GH_DANGEROUS_PATTERNS:
            if pattern.search(normalized_cmd):
                return f"{label} requires explicit user consent before executing."

    return None


def format_hook_response(reason: Optional[str], tool_name: str = "") -> Dict[str, object]:
    """Format hook JSON response for Claude/Grok (`Bash`) or Antigravity (`run_command`)."""
    is_claude_family = tool_name == "Bash" or bool(
        os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_CODE")
    )
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


def extract_hook_command_context(payload: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str]]:
    """Extract `(tool_name, command_or_None, cwd)` across Claude, Grok, and Antigravity payloads."""
    tool_call = payload.get("toolCall") or payload.get("toolUse") or payload.get("call")
    tc = tool_call if isinstance(tool_call, dict) else {}
    tool_name = str(
        payload.get("tool_name") or payload.get("toolName") or tc.get("name") or tc.get("toolName") or ""
    )

    raw_args: Any = payload.get("tool_input")
    from_tool_input_str = isinstance(raw_args, str) and not raw_args.strip().startswith("{")
    if raw_args is None:
        raw_args = tc.get("args") or tc.get("arguments") or tc.get("input")
    if raw_args is None:
        raw_args = payload.get("input") or payload.get("args") or payload.get("arguments")

    if isinstance(raw_args, str):
        if raw_args.strip().startswith("{"):
            try:
                raw_args = json.loads(raw_args)
            except ValueError:
                return tool_name, None, None
        elif from_tool_input_str:
            return tool_name, raw_args, payload.get("cwd")
        else:
            return tool_name, None, None

    if not isinstance(raw_args, dict):
        return tool_name, None, payload.get("cwd")

    command: Optional[str] = None
    for key in _COMMAND_KEYS:
        if key in raw_args and raw_args[key] is not None:
            command = str(raw_args[key])
            break
    ws_paths = payload.get("workspacePaths")
    fallback_ws = ws_paths[0] if isinstance(ws_paths, list) and ws_paths else None
    cwd = (
        raw_args.get("Cwd")
        or raw_args.get("cwd")
        or raw_args.get("working_directory")
        or raw_args.get("workdir")
        or payload.get("cwd")
        or fallback_ws
    )
    return tool_name, command, str(cwd) if cwd else None


def main() -> int:
    """Read PreToolUse payload from stdin and emit consent gate JSON (fail-closed on errors)."""
    try:
        raw = sys.stdin.read()
        if not raw or not raw.strip():
            print(json.dumps(format_hook_response("Empty PreToolUse hook payload; manual confirmation required.")))
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            print(json.dumps(format_hook_response("Malformed PreToolUse hook payload; manual confirmation required.")))
            return 0
        tool_name, command, cwd = extract_hook_command_context(payload)
        if command is None:
            print(
                json.dumps(
                    format_hook_response(
                        "Unrecognized PreToolUse execution payload schema; manual confirmation required.",
                        tool_name=tool_name,
                    )
                )
            )
            return 0
        reason = inspect_command(command, cwd=cwd)
        print(json.dumps(format_hook_response(reason, tool_name=tool_name)))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                format_hook_response(f"PreToolUse consent gate error ({type(exc).__name__}); manual confirmation required.")
            )
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
