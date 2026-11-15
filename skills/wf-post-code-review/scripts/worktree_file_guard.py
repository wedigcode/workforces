#!/usr/bin/env python3
"""
Worktree & Uncommitted File Protection Guard

Inspects Git porcelain state (including untracked `??` and Git-ignored `!!` files)
to gate shell or Git operations that would permanently delete, truncate, overwrite,
or discard uncommitted or unbacked local files.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


_EPHEMERAL_DIR_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
})
_EPHEMERAL_FILE_SUFFIXES = (".pyc", ".pyo")
_INLINE_DELETE_TOKENS = (
    "os.remove",
    "os.unlink",
    "shutil.rmtree",
    ".unlink(",
    "fs.unlink",
    "fs.rmSync",
    "fs.rm(",
)
_STRING_LITERAL_RE = re.compile(r"""(['"])((?:\\.|(?!\1).)+)\1""")
_CHECKOUT_VAL_FLAGS = frozenset({
    "-b", "-B", "--orphan", "-U", "--unified", "--conflict", "--pathspec-from-file",
})
_RESTORE_VAL_FLAGS = frozenset({"-s", "--source", "--conflict", "--pathspec-from-file"})
_SWITCH_VAL_FLAGS = frozenset({"-c", "-C", "--create", "--force-create", "--orphan"})
_TRUNCATE_VAL_FLAGS = frozenset({"-s", "-r", "--size", "--reference"})
_MV_CP_VAL_FLAGS = frozenset({"-t", "--target-directory", "-S", "--suffix"})


def _resolve_git_toplevel(cwd: Optional[str]) -> Optional[str]:
    """Return canonical Git repository root for `cwd`, or None if outside a repo."""
    work_dir = cwd if cwd is not None else os.getcwd()
    if not work_dir or not os.path.isdir(work_dir):
        return None
    try:
        res = subprocess.run(
            ["git", "-C", work_dir, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return os.path.realpath(res.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _is_ephemeral_cache_path(rel_posix: str) -> bool:
    """Return True only for disposable cache artifacts that never hold human edits."""
    clean = rel_posix.strip("./")
    if not clean:
        return False
    parts = clean.split("/")
    if any(seg in _EPHEMERAL_DIR_NAMES for seg in parts):
        return True
    name = parts[-1]
    if name == ".coverage" or name.endswith(_EPHEMERAL_FILE_SUFFIXES):
        return True
    if clean == "workforces/tasks/.claim.lock":
        return True
    return clean.startswith("workforces/tmp/")


def _repo_relative_posix(target_abs: str, repo_top: str) -> Optional[str]:
    """Compute POSIX path relative to `repo_top`, preserving symlink leaf names."""
    parent_real = os.path.realpath(os.path.dirname(target_abs))
    if os.path.islink(target_abs):
        resolved = os.path.join(parent_real, os.path.basename(target_abs))
    else:
        resolved = os.path.realpath(target_abs)
    try:
        rel = os.path.relpath(resolved, repo_top)
    except ValueError:
        return None
    if rel == ".." or rel.startswith(".." + os.sep):
        return None
    return "." if rel == "." else Path(rel).as_posix()


def _extract_porcelain_entry_path(line: str) -> str:
    """Extract the unquoted path portion from a `git status --porcelain=v1` line."""
    raw = line[3:].strip()
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1].strip()
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        raw = raw[1:-1]
    return raw.rstrip("/")


def describe_uncommitted_state(target_abs: str, repo_top: str) -> Optional[str]:
    """Return human-readable risk label if `target_abs` has uncommitted/untracked/ignored data."""
    rel_posix = _repo_relative_posix(target_abs, repo_top)
    if rel_posix is None or _is_ephemeral_cache_path(rel_posix):
        return None
    try:
        res = subprocess.run(
            ["git", "-C", repo_top, "status", "--porcelain=v1", "--ignored=matching", "--", rel_posix],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return f"file `{rel_posix}` whose Git status could not be verified clean"
    if res.returncode != 0:
        return f"file `{rel_posix}` whose Git status could not be verified clean"
    if not res.stdout.strip():
        return None
    return _classify_porcelain_lines(res.stdout.splitlines(), rel_posix)


def _classify_porcelain_lines(lines: Sequence[str], rel_posix: str) -> Optional[str]:
    """Classify non-ephemeral Git porcelain status lines into risk descriptions."""
    saw_untracked = False
    saw_ignored = False
    for line in lines:
        if len(line) < 4:
            continue
        entry_path = _extract_porcelain_entry_path(line)
        if entry_path and _is_ephemeral_cache_path(entry_path):
            continue
        xy = line[:2]
        if xy not in ("??", "!!"):
            return f"file with uncommitted changes (`{rel_posix}`)"
        if xy == "??":
            saw_untracked = True
        elif xy == "!!":
            saw_ignored = True
    if saw_untracked:
        return f"untracked local file (`{rel_posix}`) not backed up in Git"
    if saw_ignored:
        return f"Git-ignored local file (`{rel_posix}`) not backed up in Git"
    return None


def _resolve_candidate_path(raw_arg: str, eff_cwd: Optional[str]) -> str:
    """Resolve `raw_arg` relative to `eff_cwd` with `~` expansion."""
    base = eff_cwd if eff_cwd and os.path.isdir(eff_cwd) else os.getcwd()
    expanded = os.path.expanduser(raw_arg)
    return expanded if os.path.isabs(expanded) else os.path.join(base, expanded)


def _expand_existing_targets(raw_arg: str, eff_cwd: Optional[str]) -> List[str]:
    """Expand a CLI path or glob argument to existing paths (or symlinks) on disk."""
    if not raw_arg:
        return []
    cand = _resolve_candidate_path(raw_arg, eff_cwd)
    if any(ch in raw_arg for ch in "*?["):
        matches = sorted(glob.glob(cand, recursive=True))[:50]
    else:
        matches = [cand]
    return [os.path.abspath(p) for p in matches if os.path.exists(p) or os.path.islink(p)]


def inspect_paths_for_deletion(
    raw_paths: Sequence[str], eff_cwd: Optional[str], action_label: str
) -> Optional[str]:
    """Return escalation reason if deleting/truncating any path destroys uncommitted or local work."""
    for raw_arg in raw_paths:
        for abs_p in _expand_existing_targets(raw_arg, eff_cwd):
            probe_dir = abs_p if (os.path.isdir(abs_p) and not os.path.islink(abs_p)) else os.path.dirname(abs_p)
            repo_top = _resolve_git_toplevel(probe_dir)
            if not repo_top:
                continue
            if os.path.realpath(abs_p) == repo_top:
                return f"{action_label} targets entire repository root (`{raw_arg}`). Explicit user consent required."
            state = describe_uncommitted_state(abs_p, repo_top)
            if state:
                return f"{action_label} would permanently destroy {state}. Explicit user consent required."
    return None


def _is_broad_worktree_spec(raw_path: str) -> bool:
    """Return True if a Git pathspec targets the full repository or current directory."""
    stripped = raw_path.strip()
    if stripped in (".", "./", ":/", ":(top)"):
        return True
    return os.path.normpath(stripped) == "."


def _inspect_single_worktree_path(abs_p: str, action_label: str) -> Optional[str]:
    """Check one resolved path for tracked uncommitted modifications."""
    probe_dir = abs_p if (os.path.isdir(abs_p) and not os.path.islink(abs_p)) else os.path.dirname(abs_p)
    repo_top = _resolve_git_toplevel(probe_dir)
    if not repo_top:
        return None
    rel_posix = _repo_relative_posix(abs_p, repo_top)
    if rel_posix is None or _is_ephemeral_cache_path(rel_posix):
        return None
    try:
        res = subprocess.run(
            ["git", "-C", repo_top, "status", "--porcelain=v1", "--", rel_posix],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return f"{action_label} targets `{rel_posix}` whose Git status could not be verified. Explicit user consent required."
    if res.returncode != 0:
        return f"{action_label} targets `{rel_posix}` whose Git status could not be verified. Explicit user consent required."
    for line in res.stdout.splitlines():
        if len(line) >= 4 and line[:2] != "??":
            return f"{action_label} would discard uncommitted changes in `{rel_posix}`. Explicit user consent required."
    return None


def _inspect_worktree_discard_targets(
    raw_paths: Sequence[str], eff_cwd: Optional[str], action_label: str
) -> Optional[str]:
    """Check paths passed to `git checkout` / `git restore` for uncommitted tracked changes."""
    for raw in raw_paths:
        if _is_broad_worktree_spec(raw):
            return f"{action_label} across `{raw}` discards uncommitted working-tree changes. Explicit user consent required."
        targets = _expand_existing_targets(raw, eff_cwd)
        if not targets:
            targets = [os.path.abspath(_resolve_candidate_path(raw, eff_cwd))]
        for abs_p in targets:
            reason = _inspect_single_worktree_path(abs_p, action_label)
            if reason:
                return reason
    return None


def _split_git_args(
    args: Sequence[str], val_flags: frozenset[str] = frozenset()
) -> Tuple[List[str], List[str], List[str]]:
    """Split git subcommand args into `(flags_before_dash, positionals_before_dash, after_dashdash)`."""
    flags: List[str] = []
    positionals: List[str] = []
    after_dashdash: List[str] = []
    skip_next = False
    for idx, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            after_dashdash = list(args[idx + 1:])
            break
        if arg.startswith("-") and arg != "-":
            flags.append(arg)
            if arg in val_flags:
                skip_next = True
        else:
            positionals.append(arg)
    return flags, positionals, after_dashdash


def _has_short_flag_char(flag: str, char: str) -> bool:
    """Return True if a short-option bundle like `-rf` contains `char`."""
    return flag.startswith("-") and not flag.startswith("--") and char in flag[1:]


def _check_git_reset(args: Sequence[str]) -> Optional[str]:
    """Gate `git reset --hard` and `git reset --merge`."""
    flags, _, _ = _split_git_args(args)
    if any(f in ("--hard", "--merge") for f in flags):
        return "Destructive Git reset (`--hard`/`--merge`) discards uncommitted changes. Explicit user consent required."
    return None


def _check_git_clean(args: Sequence[str]) -> Optional[str]:
    """Gate forced `git clean` (`-f` / `--force`) unless `-n`/`--dry-run` is passed."""
    flags, _, _ = _split_git_args(args)
    if any(f in ("-n", "--dry-run") or _has_short_flag_char(f, "n") for f in flags):
        return None
    if any(f == "--force" or _has_short_flag_char(f, "f") for f in flags):
        return "Destructive Git clean (`git clean -f`) deletes untracked or ignored files. Explicit user consent required."
    return None


def _check_git_switch(args: Sequence[str]) -> Optional[str]:
    """Gate `git switch --force` / `--discard-changes`."""
    flags, _, _ = _split_git_args(args, _SWITCH_VAL_FLAGS)
    if any(f in ("--force", "--discard-changes") or _has_short_flag_char(f, "f") for f in flags):
        return "Destructive Git switch (`--force`/`--discard-changes`) discards uncommitted changes. Explicit user consent required."
    return None


def _check_git_checkout(args: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `git checkout` flags or path overwrites that discard uncommitted changes."""
    flags, positionals, after_dashdash = _split_git_args(args, _CHECKOUT_VAL_FLAGS)
    for flag in flags:
        if flag in ("--force", "--ours", "--theirs", "--pathspec-from-file") or flag.startswith("--pathspec-from-file="):
            return f"Destructive Git checkout flag (`{flag}`) discards uncommitted changes. Explicit user consent required."
        if _has_short_flag_char(flag, "f"):
            return f"Forced Git checkout (`{flag}`) discards uncommitted changes. Explicit user consent required."
    if after_dashdash:
        return _inspect_worktree_discard_targets(after_dashdash, eff_cwd, "Git checkout overwrite (`git checkout --`)")
    path_hits = [p for p in positionals if _is_broad_worktree_spec(p) or _expand_existing_targets(p, eff_cwd)]
    if path_hits:
        return _inspect_worktree_discard_targets(path_hits, eff_cwd, "Git checkout overwrite (`git checkout`)")
    return None


def _check_git_restore(args: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `git restore` unless strictly unstaging (`--staged` without `--worktree`)."""
    flags, positionals, after_dashdash = _split_git_args(args, _RESTORE_VAL_FLAGS)
    for flag in flags:
        if flag == "--pathspec-from-file" or flag.startswith("--pathspec-from-file="):
            return "Git restore with `--pathspec-from-file` discards working-tree changes. Explicit user consent required."
    has_staged = any(f == "--staged" or _has_short_flag_char(f, "S") for f in flags)
    has_worktree = any(f == "--worktree" or _has_short_flag_char(f, "W") for f in flags)
    if has_staged and not has_worktree:
        return None
    targets = list(positionals) + list(after_dashdash)
    if targets:
        return _inspect_worktree_discard_targets(targets, eff_cwd, "Git restore (`git restore`)")
    return None


def _check_git_rm(args: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `git rm -f` or `git rm` targeting uncommitted/untracked/ignored files."""
    flags, positionals, after_dashdash = _split_git_args(args)
    if any(f in ("--cached", "-n", "--dry-run") or _has_short_flag_char(f, "n") for f in flags):
        return None
    if any(f == "--force" or _has_short_flag_char(f, "f") for f in flags):
        return "Forced Git file removal (`git rm -f`) discards uncommitted or local content. Explicit user consent required."
    targets = list(positionals) + list(after_dashdash)
    if targets:
        return inspect_paths_for_deletion(targets, eff_cwd, "Git file removal (`git rm`)")
    return None


def _check_git_worktree_and_stash(subcmd: str, args: Sequence[str]) -> Optional[str]:
    """Gate `git worktree remove --force` and `git stash drop`/`clear`."""
    flags, positionals, _ = _split_git_args(args)
    action = positionals[0] if positionals else ""
    if subcmd == "worktree" and action == "remove":
        if any(f == "--force" or _has_short_flag_char(f, "f") for f in flags):
            return "Forced Git worktree removal (`git worktree remove --force`) discards uncommitted work. Explicit user consent required."
    if subcmd == "stash" and action in ("drop", "clear"):
        return f"Destructive Git stash operation (`git stash {action}`) permanently deletes stashed work. Explicit user consent required."
    return None


def check_git_destructive(
    tokens: Sequence[str], sub_idx: int, eff_cwd: Optional[str]
) -> Optional[str]:
    """Analyze a `git` command for destructive working-tree or uncommitted-file mutations."""
    if sub_idx >= len(tokens):
        return None
    subcmd = tokens[sub_idx]
    args = tokens[sub_idx + 1:]
    if subcmd == "reset":
        return _check_git_reset(args)
    if subcmd == "clean":
        return _check_git_clean(args)
    if subcmd == "switch":
        return _check_git_switch(args)
    if subcmd == "checkout":
        return _check_git_checkout(args, eff_cwd)
    if subcmd == "restore":
        return _check_git_restore(args, eff_cwd)
    if subcmd == "rm":
        return _check_git_rm(args, eff_cwd)
    if subcmd in ("worktree", "stash"):
        return _check_git_worktree_and_stash(subcmd, args)
    return None


def _read_redirect_target(segment: str, start: int) -> Tuple[str, int]:
    """Read one shell redirection target token starting at `start`, respecting quotes."""
    i = start
    while i < len(segment) and segment[i].isspace():
        i += 1
    buf: List[str] = []
    quote: Optional[str] = None
    escaped = False
    while i < len(segment):
        ch = segment[i]
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif ch in ("'", '"'):
            quote = None if quote == ch else (ch if quote is None else quote)
        elif quote is None and (ch.isspace() or ch in ";&|<>()"):
            break
        else:
            buf.append(ch)
        i += 1
    return "".join(buf), i


def check_truncating_redirections(segment: str, eff_cwd: Optional[str]) -> Optional[str]:
    """Gate shell `>` or `>|` output redirections that truncate existing uncommitted/local files."""
    quote: Optional[str] = None
    escaped = False
    i = 0
    while i < len(segment):
        ch = segment[i]
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
        if quote is not None or ch != ">":
            i += 1
            continue
        if segment[i:i + 2] in (">>", ">&") or (i > 0 and segment[i - 1] == "<"):
            i += 2
            continue
        op_end = i + 2 if segment[i:i + 2] == ">|" else i + 1
        target, i = _read_redirect_target(segment, op_end)
        if target and target != "/dev/null" and not target.startswith("&"):
            reason = inspect_paths_for_deletion([target], eff_cwd, "Shell output truncation (`>`)")
            if reason:
                return reason
    return None


def _extract_positional_args(
    args: Sequence[str], val_flags: frozenset[str] = frozenset()
) -> List[str]:
    """Extract non-flag positional arguments while skipping option values and honoring `--`."""
    positionals: List[str] = []
    skip_next = False
    end_of_opts = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if not end_of_opts and arg == "--":
            end_of_opts = True
            continue
        if not end_of_opts and arg.startswith("-") and arg != "-":
            if arg in val_flags:
                skip_next = True
            continue
        positionals.append(arg)
    return positionals


def _parse_mv_cp_destinations(args: Sequence[str], eff_cwd: Optional[str]) -> List[str]:
    """Compute existing destination file paths that `mv`/`cp` would overwrite."""
    target_dir_opt: Optional[str] = None
    positionals: List[str] = []
    skip_val_for: Optional[str] = None
    end_of_opts = False
    for arg in args:
        if skip_val_for is not None:
            if skip_val_for in ("-t", "--target-directory"):
                target_dir_opt = arg
            skip_val_for = None
            continue
        if not end_of_opts and arg == "--":
            end_of_opts = True
            continue
        if not end_of_opts and arg.startswith("-") and arg != "-":
            if arg.startswith("--target-directory="):
                target_dir_opt = arg.split("=", 1)[1]
            elif arg in _MV_CP_VAL_FLAGS:
                skip_val_for = arg
            continue
        positionals.append(arg)
    return _collect_overwritten_destinations(positionals, target_dir_opt, eff_cwd)


def _collect_overwritten_destinations(
    positionals: Sequence[str], target_dir_opt: Optional[str], eff_cwd: Optional[str]
) -> List[str]:
    """Filter `mv`/`cp` destination candidates to distinct pre-existing files on disk."""
    if target_dir_opt is not None:
        sources = list(positionals)
        dest_dir = _resolve_candidate_path(target_dir_opt, eff_cwd)
        return _map_sources_into_dir(sources, dest_dir, eff_cwd)
    if len(positionals) < 2:
        return []
    sources, dest_raw = list(positionals[:-1]), positionals[-1]
    dest_abs = os.path.abspath(_resolve_candidate_path(dest_raw, eff_cwd))
    if os.path.isdir(dest_abs):
        return _map_sources_into_dir(sources, dest_abs, eff_cwd)
    if not (os.path.exists(dest_abs) or os.path.islink(dest_abs)):
        return []
    if len(sources) == 1:
        src_abs = os.path.abspath(_resolve_candidate_path(sources[0], eff_cwd))
        if os.path.realpath(src_abs) == os.path.realpath(dest_abs):
            return []
    return [dest_abs]


def _map_sources_into_dir(
    sources: Sequence[str], dest_dir: str, eff_cwd: Optional[str]
) -> List[str]:
    """Return destination paths inside `dest_dir` that already exist and differ from source."""
    overwrites: List[str] = []
    for src in sources:
        src_paths = _expand_existing_targets(src, eff_cwd) or [os.path.abspath(_resolve_candidate_path(src, eff_cwd))]
        for src_abs in src_paths:
            cand = os.path.abspath(os.path.join(dest_dir, os.path.basename(src_abs.rstrip(os.sep))))
            if (os.path.exists(cand) or os.path.islink(cand)) and os.path.realpath(cand) != os.path.realpath(src_abs):
                overwrites.append(cand)
    return overwrites


def _check_find_delete(args: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `find ... -delete` or `find ... -exec rm/unlink` targeting uncommitted paths."""
    has_exec_rm = any(
        args[i] in ("-exec", "-execdir") and i + 1 < len(args) and os.path.basename(args[i + 1]) in ("rm", "unlink")
        for i in range(len(args))
    )
    if "-delete" not in args and not has_exec_rm:
        return None
    roots: List[str] = []
    for arg in args:
        if arg.startswith("-") or arg in ("(", "!", "\\("):
            break
        roots.append(arg)
    return inspect_paths_for_deletion(roots or ["."], eff_cwd, "Bulk `find` deletion")


def _check_dehydrate_command(tokens: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `scaffold_repo_okf.py --dehydrate-spec` (without `--dry-run`) on uncommitted files."""
    if not any(os.path.basename(t) == "scaffold_repo_okf.py" for t in tokens):
        return None
    if "--dry-run" in tokens:
        return None
    for idx, tok in enumerate(tokens):
        if tok == "--dehydrate-spec" and idx + 1 < len(tokens):
            return inspect_paths_for_deletion([tokens[idx + 1]], eff_cwd, "Spec dehydration (`--dehydrate-spec`)")
        if tok.startswith("--dehydrate-spec="):
            return inspect_paths_for_deletion([tok.split("=", 1)[1]], eff_cwd, "Spec dehydration (`--dehydrate-spec`)")
    return None


def _check_inline_interpreter_delete(head: str, args: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Gate `python -c` or `node -e` file deletion snippets targeting uncommitted/local paths."""
    code_flag = "-e" if head == "node" else "-c"
    code_arg: Optional[str] = None
    for idx, tok in enumerate(args):
        if tok == code_flag and idx + 1 < len(args):
            code_arg = args[idx + 1]
            break
        if tok.startswith(code_flag) and len(tok) > 2:
            code_arg = tok[2:]
            break
    if not code_arg or not any(marker in code_arg for marker in _INLINE_DELETE_TOKENS):
        return None
    literals = [match[1] for match in _STRING_LITERAL_RE.findall(code_arg)]
    if not literals:
        return None
    return inspect_paths_for_deletion(literals, eff_cwd, f"Inline `{head}` file deletion")


def check_file_command(tokens: Sequence[str], eff_cwd: Optional[str]) -> Optional[str]:
    """Analyze file-mutating shell commands for deletions/overwrites of uncommitted work."""
    if not tokens:
        return None
    head = os.path.basename(tokens[0])
    args = tokens[1:]
    if head in ("rm", "unlink", "trash"):
        return inspect_paths_for_deletion(_extract_positional_args(args), eff_cwd, f"File deletion (`{head}`)")
    if head == "truncate":
        return inspect_paths_for_deletion(
            _extract_positional_args(args, _TRUNCATE_VAL_FLAGS), eff_cwd, "File truncation (`truncate`)"
        )
    if head in ("mv", "cp"):
        dests = _parse_mv_cp_destinations(args, eff_cwd)
        return inspect_paths_for_deletion(dests, eff_cwd, f"File overwrite (`{head}`)") if dests else None
    if head == "find":
        return _check_find_delete(args, eff_cwd)
    if head in ("python", "python3", "node"):
        dehydrate_reason = _check_dehydrate_command(tokens, eff_cwd)
        if dehydrate_reason:
            return dehydrate_reason
        return _check_inline_interpreter_delete(head, args, eff_cwd)
    return _check_dehydrate_command(tokens, eff_cwd)
