#!/usr/bin/env python3
"""
Workforces Multi-AI Frontmatter & Asset Compiler
Compiles canonical sidecar JSON metadata + Markdown bodies into host-specific
YAML frontmatter, directory layouts, file extensions, relative links, and lifecycle
hooks across Antigravity/Gemini, Claude Code, Grok Build, GitHub Copilot, and Cursor.
"""

import argparse
import copy
import datetime
import json
import os
import posixpath
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

INSTALL_CONFIG_REL_PATH = os.path.join("workforces", "config.json")
SUPPORTED_HOST_ORDER = ("antigravity", "claude", "grok", "copilot", "cursor")
_YAML_RESERVED = frozenset({"true", "false", "null", "yes", "no", "on", "off", "~"})
_YAML_LEAD_CHARS = ("*", "&", "!", "%", "@", "`", "[", "]", "{", "}", ">", "|", "'", '"', "#", "?", ":")
_HOOK_SEARCH_BASES = (".agents", ".claude", ".grok", ".github", ".cursor", ".github/copilot", "", "../..")


def _order_hosts(host_ids: Iterable[str]) -> List[str]:
    """Order host IDs canonically according to SUPPORTED_HOST_ORDER."""
    unique = set(host_ids)
    ordered = [h for h in SUPPORTED_HOST_ORDER if h in unique]
    extras = sorted(unique - set(ordered))
    return ordered + extras


def find_hosts_dir(toolkit_root: str) -> str:
    """Locate the directory containing host adapter JSON profiles."""
    root = os.path.abspath(toolkit_root)
    candidates = [
        os.path.join(root, "config", "hosts"),
        os.path.join(root, "skills", "wf-management", "hosts"),
    ]
    for base in (".agents", ".claude", ".grok", ".github", ".cursor", os.path.join(".github", "copilot")):
        candidates.append(os.path.join(root, base, "skills", "wf-management", "hosts"))
    candidates.append(str(Path(__file__).resolve().parent.parent / "hosts"))
    for cand in candidates:
        if os.path.isdir(cand):
            return cand
    raise FileNotFoundError(f"Host adapter profiles directory not found under {toolkit_root}")


def load_host_profiles(toolkit_root: str) -> Dict[str, Dict[str, Any]]:
    """Load all host adapter JSON definitions keyed by canonical host id."""
    hosts_dir = find_hosts_dir(toolkit_root)
    raw_profiles: Dict[str, Dict[str, Any]] = {}
    for entry in sorted(os.listdir(hosts_dir)):
        if not entry.endswith(".json"):
            continue
        full_path = os.path.join(hosts_dir, entry)
        with open(full_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "id" in data and "base_dir" in data:
            raw_profiles[str(data["id"])] = data
    return {hid: raw_profiles[hid] for hid in _order_hosts(raw_profiles.keys())}


def resolve_host_alias(name: str, profiles: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Resolve a host id or alias (e.g. 'gemini' -> 'antigravity', 'vscode' -> 'copilot')."""
    cleaned = (name or "").strip().lower()
    if not cleaned:
        return None
    if cleaned in profiles:
        return cleaned
    for host_id, profile in profiles.items():
        aliases = [str(a).strip().lower() for a in profile.get("aliases", [])]
        if cleaned in aliases:
            return host_id
    return None


def load_install_config(target_dir: str) -> Optional[Dict[str, Any]]:
    """Load workforces/config.json if present and valid."""
    cfg_path = os.path.join(os.path.abspath(target_dir), INSTALL_CONFIG_REL_PATH)
    if not os.path.isfile(cfg_path):
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"[compile_assets] Warning: failed to read {cfg_path}: {exc}\n")
        return None
    return data if isinstance(data, dict) else None


def infer_repo_type(target_dir: str) -> Optional[str]:
    """Infer existing repo_type ('workforce', 'project', 'personal') from config.json or workrules.md."""
    cfg = load_install_config(target_dir) or {}
    cfg_type = str(cfg.get("repo_type") or "").strip().lower()
    if cfg_type in ("workforce", "project", "personal"):
        return cfg_type
    wr_path = os.path.join(os.path.abspath(target_dir), "workforces", "workrules.md")
    if not os.path.isfile(wr_path):
        return None
    try:
        with open(wr_path, "r", encoding="utf-8") as fh:
            match = re.search(r"(?m)^-\s*type:\s*(workforce|project|personal)\b", fh.read())
    except OSError:
        return None
    return match.group(1) if match else None


def save_install_config(
    target_dir: str,
    hosts: Sequence[str],
    repo_type: str,
    installed_teams: Sequence[str],
    profiles: Dict[str, Dict[str, Any]],
    auto_detect_hosts: bool = True,
) -> str:
    """Persist multi-host installation settings to workforces/config.json."""
    resolved = [resolve_host_alias(h, profiles) or h for h in hosts]
    ordered = _order_hosts([h for h in resolved if h in profiles])
    cfg_path = os.path.join(os.path.abspath(target_dir), INSTALL_CONFIG_REL_PATH)
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    payload = {
        "schema_version": 1,
        "repo_type": repo_type or "project",
        "hosts": ordered,
        "auto_detect_hosts": bool(auto_detect_hosts),
        "installed_teams": sorted({str(t).strip() for t in installed_teams if str(t).strip()}),
        "host_dirs": {h: profiles[h]["base_dir"] for h in ordered},
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    return cfg_path


def detect_workspace_hosts(
    target_dir: str, profiles: Dict[str, Dict[str, Any]]
) -> List[str]:
    """Auto-detect all AI host folders/markers present in target_dir."""
    root = os.path.abspath(target_dir)
    detected: List[str] = []
    for host_id in _order_hosts(profiles.keys()):
        profile = profiles[host_id]
        markers = profile.get("detect_any") or profile.get("detect_paths") or []
        if any(os.path.exists(os.path.join(root, m)) for m in markers):
            detected.append(host_id)
    return detected


def _parse_explicit_hosts(arg_clean: str, profiles: Dict[str, Dict[str, Any]]) -> List[str]:
    """Parse an explicit CLI --hosts string ('all' or CSV aliases) into canonical host IDs."""
    if arg_clean.lower() in ("all", "*"):
        return _order_hosts(profiles.keys())
    chosen: List[str] = []
    for token in arg_clean.split(","):
        resolved = resolve_host_alias(token, profiles)
        if not resolved:
            raise ValueError(f"Unknown AI host '{token.strip()}'. Supported: {', '.join(profiles)}")
        chosen.append(resolved)
    return _order_hosts(chosen)


def resolve_active_hosts(
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    hosts_arg: Optional[str] = None,
    auto_detect: bool = True,
    force_auto_detect: bool = False,
) -> List[str]:
    """Resolve ordered list of active host ids from CLI arg, saved config, and auto-detection."""
    arg_clean = (hosts_arg or "").strip()
    if arg_clean and arg_clean.lower() != "auto":
        return _parse_explicit_hosts(arg_clean, profiles)
    cfg = load_install_config(target_dir)
    saved_raw = cfg.get("hosts") if cfg and isinstance(cfg.get("hosts"), list) else []
    active = {h for h in (resolve_host_alias(str(r), profiles) for r in saved_raw) if h}
    cfg_allows = True if force_auto_detect else (bool(cfg.get("auto_detect_hosts", True)) if cfg else True)
    if auto_detect and cfg_allows:
        active.update(detect_workspace_hosts(target_dir, profiles))
    if not active:
        detected = detect_workspace_hosts(target_dir, profiles) if auto_detect else []
        if detected:
            return detected
        return ["antigravity" if "antigravity" in profiles else next(iter(profiles))]
    return _order_hosts(active)


def strip_markdown_frontmatter(content: str) -> str:
    """Remove leading YAML frontmatter block (--- ... ---) from markdown content."""
    match = re.match(r"^---[ \t]*\r?\n(?:.*?\r?\n)?---[ \t]*(?:\r?\n)*", content, re.DOTALL)
    return content[match.end():] if match else content


def _needs_yaml_quotes(val: str) -> bool:
    """Return True when a YAML scalar string requires double-quoting."""
    if not val or val != val.strip() or "\n" in val or "\r" in val:
        return True
    if val.lower() in _YAML_RESERVED or val.startswith(_YAML_LEAD_CHARS):
        return True
    if val == "-" or val.startswith("- "):
        return True
    return ": " in val or val.endswith(":") or " #" in val


def _format_yaml_scalar(val: Any) -> str:
    """Format a Python scalar into a safe YAML 1.2 literal."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if val is None:
        return "null"
    if isinstance(val, (int, float)):
        return str(val)
    text = str(val)
    return json.dumps(text, ensure_ascii=False) if _needs_yaml_quotes(text) else text


def _emit_yaml_list_item(lines: List[str], item: Any, pad: str) -> None:
    """Append serialized YAML lines for a single list item."""
    if not isinstance(item, dict):
        lines.append(f"{pad}  - {_format_yaml_scalar(item)}")
        return
    for idx, (sub_k, sub_v) in enumerate(item.items()):
        prefix = f"{pad}  - " if idx == 0 else f"{pad}    "
        lines.append(f"{prefix}{sub_k}: {_format_yaml_scalar(sub_v)}")


def _use_folded_block(key: str, val: Any) -> bool:
    """Return True when description should be emitted as a folded YAML block scalar (>-)."""
    if key != "description" or not isinstance(val, str) or "\n" in val or "\r" in val:
        return False
    return ": " in val or val.endswith(":") or " #" in val


def _emit_yaml_entry(lines: List[str], key: str, val: Any, indent: int = 0) -> None:
    """Append serialized YAML lines for a key-value pair at the given indentation."""
    pad = " " * indent
    if isinstance(val, list):
        if not val:
            lines.append(f"{pad}{key}: []")
            return
        lines.append(f"{pad}{key}:")
        for item in val:
            _emit_yaml_list_item(lines, item, pad)
    elif isinstance(val, dict):
        if not val:
            lines.append(f"{pad}{key}: {{}}")
            return
        lines.append(f"{pad}{key}:")
        for sub_k, sub_v in val.items():
            _emit_yaml_entry(lines, str(sub_k), sub_v, indent + 2)
    elif _use_folded_block(key, val):
        lines.append(f"{pad}{key}: >-")
        lines.append(f"{pad}  {val}")
    else:
        lines.append(f"{pad}{key}: {_format_yaml_scalar(val)}")


def serialize_yaml_frontmatter(
    data: Dict[str, Any], field_order: Optional[Sequence[str]] = None
) -> str:
    """Serialize an ordered dictionary into deterministic YAML frontmatter without PyYAML."""
    if not data:
        return ""
    ordered_keys: List[str] = []
    if field_order:
        ordered_keys.extend([k for k in field_order if k in data and data[k] is not None])
    ordered_keys.extend([k for k in data if k not in ordered_keys and data[k] is not None])
    if not ordered_keys:
        return ""
    lines = ["---"]
    for key in ordered_keys:
        _emit_yaml_entry(lines, key, data[key])
    lines.append("---")
    return "\n".join(lines)


def _map_capabilities(capabilities: Sequence[str], cap_map: Dict[str, List[str]]) -> List[str]:
    """Translate canonical capabilities into deduplicated host-native tool names."""
    flat = [tool for cap in (capabilities or []) for tool in cap_map.get(cap, [])]
    return list(dict.fromkeys(flat))


def _merge_host_overrides(
    raw: Dict[str, Any],
    sidecar: Dict[str, Any],
    host_id: str,
    tools_field: Optional[str] = None,
) -> None:
    """Apply explicit sidecar hosts.<host_id> overrides onto synthesized frontmatter."""
    overrides = (sidecar.get("hosts") or {}).get(host_id)
    if not isinstance(overrides, dict):
        return
    for key, val in overrides.items():
        if key == "extra_tools" and tools_field and isinstance(val, list):
            raw[tools_field] = list(dict.fromkeys(list(raw.get(tools_field) or []) + val))
        elif val is None:
            raw.pop(key, None)
        else:
            raw[key] = copy.deepcopy(val)


def _order_dict_by_fields(
    raw: Dict[str, Any], field_order: Optional[Sequence[str]] = None
) -> Dict[str, Any]:
    """Return a dict ordered by field_order followed by any remaining keys."""
    ordered: Dict[str, Any] = {}
    for key in field_order or []:
        if key in raw and raw[key] is not None:
            ordered[key] = raw[key]
    for key, val in raw.items():
        if key not in ordered and val is not None:
            ordered[key] = val
    return ordered


def compile_agent_frontmatter(
    sidecar: Dict[str, Any], host_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Synthesize host-native frontmatter dict for an agent from sidecar JSON + host profile."""
    schema = host_profile.get("agent_schema", {})
    host_id = host_profile["id"]
    raw: Dict[str, Any] = {
        "name": sidecar["name"],
        "description": sidecar["description"],
    }
    raw.update(copy.deepcopy(schema.get("defaults", {})))
    if sidecar.get("background_only"):
        raw.update(copy.deepcopy(schema.get("when_background_only", {})))
    if schema.get("derive_readonly_from_capabilities"):
        caps = set(sidecar.get("capabilities") or [])
        raw["readonly"] = not bool(caps & {"edit", "multi_edit", "execute"})
    tools_field = schema.get("tools_field")
    if tools_field:
        raw[tools_field] = _map_capabilities(
            sidecar.get("capabilities") or [], host_profile.get("capability_map", {})
        )
    if schema.get("include_skills"):
        skills = list(sidecar.get("skills") or [])
        if skills or host_id == "antigravity":
            raw["skills"] = skills
    _merge_host_overrides(raw, sidecar, host_id, tools_field=tools_field)
    return _order_dict_by_fields(raw, schema.get("field_order"))


def _format_rule_globs(globs: List[str], fmt: str) -> Any:
    """Format a rule's glob list according to host rule_schema globs_format."""
    if fmt == "csv":
        return ", ".join(globs)
    if fmt == "csv_or_list":
        return globs[0] if len(globs) == 1 else list(globs)
    return list(globs)


def compile_rule_frontmatter(
    sidecar: Dict[str, Any], host_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Synthesize host-native frontmatter dict for a rule from sidecar JSON + host profile."""
    schema = host_profile.get("rule_schema", {})
    host_id = host_profile["id"]
    raw: Dict[str, Any] = {}
    if schema.get("include_description") and sidecar.get("description"):
        raw["description"] = sidecar["description"]
    globs = [str(g) for g in (sidecar.get("globs") or []) if str(g).strip()]
    if sidecar.get("always_on"):
        raw.update(copy.deepcopy(schema.get("emit_when_always_on", {})))
    else:
        globs_field = schema.get("globs_field_when_scoped")
        if globs and globs_field:
            raw[globs_field] = _format_rule_globs(globs, schema.get("globs_format", "list"))
        raw.update(copy.deepcopy(schema.get("emit_when_scoped", {})))
    _merge_host_overrides(raw, sidecar, host_id)
    return raw


def compile_skill_frontmatter(
    sidecar: Dict[str, Any], host_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Synthesize host-native frontmatter dict for a skill from sidecar JSON + host profile."""
    schema = host_profile.get("skill_schema", {})
    host_id = host_profile["id"]
    fields = schema.get("fields", ["name", "description"])
    raw: Dict[str, Any] = {}
    for field in fields:
        val = sidecar.get(field)
        if val is None:
            val = sidecar.get(field.replace("-", "_"))
        if val is not None:
            raw[field] = val
    tools_field = schema.get("tools_field")
    if tools_field and sidecar.get("capabilities"):
        mapped = _map_capabilities(sidecar["capabilities"], host_profile.get("capability_map", {}))
        if mapped:
            raw[tools_field] = mapped
    _merge_host_overrides(raw, sidecar, host_id, tools_field=tools_field)
    return _order_dict_by_fields(raw, fields)


def _compile_workflow_frontmatter(
    sidecar: Dict[str, Any], host_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Synthesize host-native frontmatter dict for a workflow/prompt/command asset."""
    schema = host_profile.get("workflow_schema", {})
    fields = schema.get("fields", ["description"])
    raw: Dict[str, Any] = {}
    for field in fields:
        val = sidecar.get(field)
        if val is None:
            val = sidecar.get(field.replace("-", "_"))
        if val is not None:
            raw[field] = val
    _merge_host_overrides(raw, sidecar, host_profile["id"])
    return _order_dict_by_fields(raw, fields)


def _resolve_virtual_dirs(source_category: str, dirs_cfg: Dict[str, Any]) -> Tuple[str, str]:
    """Return (source_virtual_dir, target_virtual_dir) relative to toolkit/host base."""
    clean_cat = source_category.strip("/")
    parts = clean_cat.split("/", 1)
    top = parts[0]
    target_base = dirs_cfg.get(top, {}).get("path", top)
    if len(parts) == 2:
        return clean_cat, f"{target_base}/{parts[1]}"
    if top in ("skills", "teams"):
        return f"{top}/_item", f"{target_base}/_item"
    return top, target_base


def _map_target_virtual_path(norm_src: str, dirs_cfg: Dict[str, Any]) -> Optional[str]:
    """Map a normalized source virtual path (e.g. rules/wf-base.md) to host virtual path."""
    segs = norm_src.split("/")
    top = segs[0]
    if top in ("agents", "rules", "workflows") and len(segs) == 2 and segs[1].endswith(".md"):
        cfg = dirs_cfg.get(top)
        if not cfg:
            return None
        stem = segs[1][:-3]
        return f"{cfg['path']}/{stem}{cfg.get('ext', '.md')}"
    if top in ("skills", "teams") and len(segs) >= 2 and segs[1] != "_item":
        cfg = dirs_cfg.get(top)
        if not cfg:
            return None
        rest = "/".join(segs[1:])
        return f"{cfg['path']}/{rest}"
    return None


def _rewrite_link_url(
    raw_url: str, src_vdir: str, dst_vdir: str, dirs_cfg: Dict[str, Any]
) -> str:
    """Rewrite a single markdown link target if it resolves to an intra-toolkit asset."""
    url = raw_url.strip()
    if not url or url.startswith(("http://", "https://", "mailto:", "#", "file://", "/")):
        return raw_url
    if "://" in url or "{{" in url or "..." in url:
        return raw_url
    path_part, sep, frag = url.partition("#")
    if not path_part.endswith(".md"):
        return raw_url
    norm_src = posixpath.normpath(posixpath.join(src_vdir, path_part))
    mapped_dst = _map_target_virtual_path(norm_src, dirs_cfg)
    if not mapped_dst:
        return raw_url
    rel_dst = posixpath.relpath(mapped_dst, dst_vdir)
    return f"{rel_dst}{sep}{frag}" if sep else rel_dst


def _rewrite_base_dir_refs(body: str, host_profile: Dict[str, Any]) -> str:
    """Rewrite explicit .agents/<category>/ path references for non-Antigravity hosts."""
    base_dir = host_profile.get("base_dir", ".agents")
    if base_dir == ".agents":
        return body
    dirs_cfg = host_profile.get("dirs", {})
    updated = body
    for cat in ("agents", "rules", "workflows"):
        cfg = dirs_cfg.get(cat)
        if not cfg:
            continue
        ext = cfg.get("ext", ".md")
        target_prefix = f"{base_dir}/{cfg['path']}/"
        updated = re.sub(
            rf"(?<![\w/])\.agents/{cat}/([A-Za-z0-9_-]+)\.md\b",
            lambda m, tp=target_prefix, ex=ext: f"{tp}{m.group(1)}{ex}",
            updated,
        )
        updated = updated.replace(f".agents/{cat}/", target_prefix)
    for cat in ("skills", "teams"):
        cfg = dirs_cfg.get(cat)
        if cfg:
            updated = updated.replace(f".agents/{cat}/", f"{base_dir}/{cfg['path']}/")
    return updated


def rewrite_relative_links_for_host(
    body: str, source_category: str, host_profile: Dict[str, Any]
) -> str:
    """Rewrite intra-toolkit relative markdown links and base dir paths for target host."""
    dirs_cfg = host_profile.get("dirs", {})
    src_vdir, dst_vdir = _resolve_virtual_dirs(source_category, dirs_cfg)
    rewritten = re.sub(
        r"(\[[^\]]+\]\()([^)\s]+)(\))",
        lambda m: f"{m.group(1)}{_rewrite_link_url(m.group(2), src_vdir, dst_vdir, dirs_cfg)}{m.group(3)}",
        body,
    )
    return _rewrite_base_dir_refs(rewritten, host_profile)


def compile_markdown_asset(
    md_content: str,
    sidecar: Dict[str, Any],
    source_category: str,
    host_profile: Dict[str, Any],
) -> str:
    """Compile a full markdown file (frontmatter + link-rewritten body) for a host."""
    cat_top = source_category.strip("/").split("/", 1)[0]
    field_order: Optional[Sequence[str]] = None
    if cat_top == "agents":
        fm_dict = compile_agent_frontmatter(sidecar, host_profile)
        field_order = host_profile.get("agent_schema", {}).get("field_order")
    elif cat_top == "rules":
        fm_dict = compile_rule_frontmatter(sidecar, host_profile)
    elif cat_top == "skills":
        fm_dict = compile_skill_frontmatter(sidecar, host_profile)
        field_order = host_profile.get("skill_schema", {}).get("fields")
    elif cat_top == "workflows":
        fm_dict = _compile_workflow_frontmatter(sidecar, host_profile)
        field_order = host_profile.get("workflow_schema", {}).get("fields")
    else:
        fm_dict = {}

    had_compact_fm = bool(
        re.match(r"^---[ \t]*\r?\n(?:.*?\r?\n)?---[ \t]*\r?\n(?=[^\r\n])", md_content, re.DOTALL)
    )
    raw_body = strip_markdown_frontmatter(md_content).lstrip("\r\n")
    rewritten_body = rewrite_relative_links_for_host(raw_body, source_category, host_profile)
    if rewritten_body and not rewritten_body.endswith("\n"):
        rewritten_body += "\n"
    fm_block = serialize_yaml_frontmatter(fm_dict, field_order=field_order)
    if not fm_block:
        return rewritten_body
    sep = "\n" if had_compact_fm else "\n\n"
    return f"{fm_block}{sep}{rewritten_body}"


def _ordered_hook_bases(host_profile: Dict[str, Any]) -> Tuple[str, ...]:
    """Return candidate search bases with the host's own base_dir prioritized first."""
    primary = host_profile.get("base_dir", ".agents")
    seen: List[str] = [primary]
    for cand in _HOOK_SEARCH_BASES:
        if cand not in seen:
            seen.append(cand)
    return tuple(seen)


def _wrap_python_with_fallback(py_code: str) -> str:
    """Wrap inline Python one-liner with python3 -> python fallback for Windows/POSIX."""
    return f'python3 -c "{py_code}" || python -c "{py_code}"'


def _build_integrity_hook_cmd(script_rel: str, host_profile: Dict[str, Any]) -> str:
    """Build cross-workspace integrity validator hook command."""
    ws_bases = repr(tuple(b for b in _ordered_hook_bases(host_profile) if b != "../.."))
    py_code = (
        "import os, json, sys, subprocess; from pathlib import Path; "
        "sys.excepthook = lambda *_: (print('{}'), sys.stdout.flush(), os._exit(0)); "
        "raw = sys.stdin.read() if not sys.stdin.isatty() else ''; "
        "data = json.loads(raw) if raw.strip().startswith('{') else {}; "
        "wp = data.get('workspacePaths') or ([data['cwd']] if data.get('cwd') else []); "
        "cwd = Path.cwd().resolve(); "
        "p2 = cwd.parent.parent if cwd.parent.name == 'plugins' else None; "
        "ws = Path(wp[0]).resolve() if (wp and Path(str(wp[0])).exists()) else "
        "((p2.parent.parent if (p2.name == 'copilot' and p2.parent.name == '.github') else "
        "(p2.parent if p2.name in ('.agents', '.claude', '.grok', '.github', '.cursor') else p2)) if p2 else cwd); "
        f"rel = '{script_rel}'; "
        f"cands = [ws / b / rel for b in {ws_bases}] + [cwd / '../../' / rel]; "
        "script = next((str(p) for p in cands if p.is_file()), None); "
        "res = subprocess.run([sys.executable, script, str(ws), '--fix'], capture_output=True, text=True) if script else None; "
        "sys.stderr.write(res.stdout) if (res and res.stdout) else None; print('{}')"
    )
    return _wrap_python_with_fallback(py_code)


def _build_hook_command(rule: Dict[str, Any], host_profile: Dict[str, Any]) -> str:
    """Build cross-workspace Python hook command string for a canonical hook rule."""
    if rule.get("command"):
        return str(rule["command"])
    script_rel = str(rule["script_rel"])
    if rule.get("runner", "script_rel") == "integrity_validator":
        return _build_integrity_hook_cmd(script_rel, host_profile)
    bases_repr = repr(_ordered_hook_bases(host_profile))
    raw_fb = str(rule.get("fallback_stdout", "{}")).replace('\\"', '"')
    if host_profile.get("id") == "claude" and '"decision"' in raw_fb:
        raw_fb = "{}"
    escaped_fb = raw_fb.replace('"', '\\"')
    py_code = (
        f"import os, sys, subprocess; rel = '{script_rel}'; "
        f"cands = [f'{{b}}/{{rel}}' if b else rel for b in {bases_repr}]; "
        "script = next((p for p in cands if os.path.exists(p)), None); "
        f"sys.exit(subprocess.call([sys.executable, script])) if script else (print('{escaped_fb}'), sys.exit(0))"
    )
    return _wrap_python_with_fallback(py_code)


def _compile_single_hook_rule(
    rule: Dict[str, Any], hook_cap_map: Dict[str, List[str]], host_profile: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Compile one canonical hook rule into a matcher + command hook object."""
    if rule.get("matcher"):
        matcher_str = str(rule["matcher"])
    else:
        tools = _map_capabilities(rule.get("matcher_capabilities") or [], hook_cap_map)
        if not tools:
            return None
        matcher_str = "|".join(tools)
    action: Dict[str, Any] = {
        "type": "command",
        "command": _build_hook_command(rule, host_profile),
    }
    if "timeout" in rule:
        action["timeout"] = int(rule["timeout"])
    return {"matcher": matcher_str, "hooks": [action]}


def compile_plugin_hooks_for_host(
    plugin_meta: Dict[str, Any], host_profile: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """Compile canonical plugin hook rules into host-native PreToolUse/PostToolUse structures."""
    if host_profile.get("hooks_mode") == "none":
        return {}
    hook_cap_map = host_profile.get("hook_capability_map", {})
    compiled: Dict[str, List[Dict[str, Any]]] = {}
    for phase, rules in (plugin_meta.get("hooks") or {}).items():
        built = [_compile_single_hook_rule(r, hook_cap_map, host_profile) for r in (rules or [])]
        entries = [e for e in built if e is not None]
        if entries:
            compiled[phase] = entries
    return compiled


def _is_workforces_hook_rule(rule: Any) -> bool:
    """Return True if a Claude settings.json hook rule belongs to Workforces."""
    if not isinstance(rule, dict):
        return False
    if rule.get("_workforces_plugin"):
        return True
    for action in rule.get("hooks") or []:
        if isinstance(action, dict) and "skills/wf-" in str(action.get("command", "")):
            return True
    return False


def _merge_claude_hook_phases(
    original: Dict[str, Any], desired_by_phase: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Return updated settings dict with non-Workforces hooks preserved and desired merged."""
    updated = copy.deepcopy(original)
    hooks_obj = updated.get("hooks")
    hooks_dict: Dict[str, Any] = copy.deepcopy(hooks_obj) if isinstance(hooks_obj, dict) else {}
    all_phases = list(dict.fromkeys(list(hooks_dict.keys()) + list(desired_by_phase.keys())))
    for phase in all_phases:
        preserved = [r for r in (hooks_dict.get(phase) or []) if not _is_workforces_hook_rule(r)]
        combined = preserved + desired_by_phase.get(phase, [])
        if combined:
            hooks_dict[phase] = combined
        else:
            hooks_dict.pop(phase, None)
    if hooks_dict or "hooks" in original:
        updated["hooks"] = hooks_dict
    return updated


def _load_claude_settings_dict(settings_path: str) -> Optional[Dict[str, Any]]:
    """Read .claude/settings.json as a JSON object; warn and return None if malformed."""
    try:
        raw_text = Path(settings_path).read_text(encoding="utf-8").strip()
        parsed = json.loads(raw_text) if raw_text else {}
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"[compile_assets] Warning: skipping malformed {settings_path}: {exc}\n")
        return None
    if not isinstance(parsed, dict):
        sys.stderr.write(f"[compile_assets] Warning: skipping non-object {settings_path}\n")
        return None
    return parsed


def sync_claude_settings_hooks(
    target_dir: str,
    active_plugin_metas: Sequence[Dict[str, Any]],
    claude_profile: Dict[str, Any],
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """Idempotently merge or prune Workforces hooks inside .claude/settings.json."""
    rel_target = claude_profile.get("hooks_target", os.path.join(".claude", "settings.json"))
    settings_path = os.path.join(os.path.abspath(target_dir), rel_target)
    desired_by_phase: Dict[str, List[Dict[str, Any]]] = {}
    for meta in active_plugin_metas:
        for phase, entries in compile_plugin_hooks_for_host(meta, claude_profile).items():
            desired_by_phase.setdefault(phase, []).extend(entries)
    if os.path.isfile(settings_path):
        loaded = _load_claude_settings_dict(settings_path)
        if loaded is None:
            return False, settings_path
        original = loaded
    elif not desired_by_phase:
        return False, settings_path
    else:
        original = {}
    updated = _merge_claude_hook_phases(original, desired_by_phase)
    if updated == original:
        return False, settings_path
    if not dry_run:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        Path(settings_path).write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return True, settings_path


def _write_text_if_changed(dst_path: str, content: str, dry_run: bool = False) -> bool:
    """Write UTF-8 text to dst_path only when content differs; return True if changed."""
    dst = Path(dst_path)
    if dst.is_file() and dst.read_text(encoding="utf-8") == content:
        return False
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
    return True


def _copy_binary_if_changed(src_path: str, dst_path: str, dry_run: bool = False) -> bool:
    """Copy a non-compiled file to dst_path when bytes differ; preserve executable bit."""
    src_bytes = Path(src_path).read_bytes()
    dst = Path(dst_path)
    if dst.is_file() and dst.read_bytes() == src_bytes:
        return False
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
    return True


def _find_source_dir(toolkit_root: str, category: str) -> Optional[str]:
    """Locate source directory for an asset category under toolkit_root."""
    root = os.path.abspath(toolkit_root)
    direct = os.path.join(root, category)
    if os.path.isdir(direct):
        return direct
    fallback = os.path.join(root, ".agents", category)
    return fallback if os.path.isdir(fallback) else None


def _load_json_file(path: str) -> Dict[str, Any]:
    """Load and validate a JSON object from path."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _compile_flat_category(
    src_dir: Optional[str],
    items: Sequence[str],
    category: str,
    host_root: str,
    target_dir: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile flat markdown assets (agents, rules, workflows) for one host."""
    cfg = profile.get("dirs", {}).get(category)
    if not cfg or not src_dir:
        return 0, []
    written = 0
    installed: List[str] = []
    ext = cfg.get("ext", ".md")
    out_dir = os.path.join(host_root, cfg["path"])
    for item in items:
        stem = item[:-3] if item.endswith(".md") else item
        md_path = os.path.join(src_dir, f"{stem}.md")
        if not os.path.isfile(md_path):
            continue
        sidecar_path = os.path.join(src_dir, f"{stem}.json")
        sidecar = _load_json_file(sidecar_path) if os.path.isfile(sidecar_path) else {"name": stem, "description": stem}
        with open(md_path, "r", encoding="utf-8") as fh:
            compiled = compile_markdown_asset(fh.read(), sidecar, category, profile)
        dst_path = os.path.join(out_dir, f"{stem}{ext}")
        if _write_text_if_changed(dst_path, compiled, dry_run=dry_run):
            written += 1
        installed.append(os.path.relpath(dst_path, target_dir))
    return written, installed


def _collect_bundled_plugins_map(toolkit_root: str) -> Optional[Dict[str, Any]]:
    """Collect canonical plugin.json specs from toolkit_root/plugins for offline hook resync."""
    plugins_dir = os.path.join(os.path.abspath(toolkit_root), "plugins")
    if not os.path.isdir(plugins_dir):
        return None
    plugins_map: Dict[str, Any] = {}
    for pl_name in sorted(os.listdir(plugins_dir)):
        pjson = os.path.join(plugins_dir, pl_name, "plugin.json")
        if os.path.isfile(pjson):
            meta = _load_json_file(pjson)
            plugins_map[str(meta.get("name", pl_name))] = meta
    return {"plugins": plugins_map} if plugins_map else None


def _collect_bundled_teams_map(toolkit_root: str) -> Optional[Dict[str, Any]]:
    """Collect canonical team pack.json specs from toolkit_root/teams for offline fallback."""
    teams_dir = os.path.join(os.path.abspath(toolkit_root), "teams")
    if not os.path.isdir(teams_dir):
        return None
    teams_map: Dict[str, Any] = {}
    for team_name in sorted(os.listdir(teams_dir)):
        pjson = os.path.join(teams_dir, team_name, "pack.json")
        if os.path.isfile(pjson):
            teams_map[team_name] = _load_json_file(pjson)
    return {"teams": teams_map} if teams_map else None


def _bundle_hosts_into_skill(
    toolkit_root: str, dst_skill_dir: str, target_dir: str, dry_run: bool
) -> Tuple[int, List[str]]:
    """Ensure host adapter JSON profiles, plugins, and teams are bundled into wf-management/hosts/."""
    hosts_src = find_hosts_dir(toolkit_root)
    hosts_dst = os.path.join(dst_skill_dir, "hosts")
    written = 0
    installed: List[str] = []
    handled: Set[str] = set()
    cap_src = os.path.join(os.path.abspath(toolkit_root), "config", "capabilities.json")
    if os.path.isfile(cap_src):
        cap_dst = os.path.join(hosts_dst, "capabilities.json")
        written += int(_copy_binary_if_changed(cap_src, cap_dst, dry_run=dry_run))
        installed.append(os.path.relpath(cap_dst, target_dir))
        handled.add("capabilities.json")
    for out_name, payload in (
        ("plugins.json", _collect_bundled_plugins_map(toolkit_root)),
        ("teams.json", _collect_bundled_teams_map(toolkit_root)),
    ):
        if payload is not None:
            out_dst = os.path.join(hosts_dst, out_name)
            written += int(_write_text_if_changed(out_dst, json.dumps(payload, indent=2) + "\n", dry_run=dry_run))
            installed.append(os.path.relpath(out_dst, target_dir))
            handled.add(out_name)
    for fn in sorted(os.listdir(hosts_src)):
        if fn.endswith(".json") and fn not in handled:
            dst_file = os.path.join(hosts_dst, fn)
            written += int(_copy_binary_if_changed(os.path.join(hosts_src, fn), dst_file, dry_run=dry_run))
            installed.append(os.path.relpath(dst_file, target_dir))
    return written, list(dict.fromkeys(installed))


def _sync_single_skill_file(
    src_file: str,
    src_skill_dir: str,
    dst_skill_dir: str,
    skill_filename: str,
    skill_name: str,
    sidecar: Dict[str, Any],
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, str]:
    """Compile SKILL.md or copy one supporting file inside a skill directory."""
    rel_in_skill = os.path.relpath(src_file, src_skill_dir)
    out_rel = skill_filename if rel_in_skill == "SKILL.md" else rel_in_skill
    dst_file = os.path.join(dst_skill_dir, out_rel)
    if rel_in_skill == "SKILL.md":
        with open(src_file, "r", encoding="utf-8") as fh:
            compiled = compile_markdown_asset(fh.read(), sidecar, f"skills/{skill_name}", profile)
        changed = _write_text_if_changed(dst_file, compiled, dry_run=dry_run)
    else:
        changed = _copy_binary_if_changed(src_file, dst_file, dry_run=dry_run)
    return int(changed), dst_file


def _iter_asset_files(
    root_dir: str, ignored_names: Sequence[str], ignored_dirs: Sequence[str] = ()
) -> List[str]:
    """Return sorted file paths under root_dir, skipping __pycache__, .pyc, ignored_dirs, and ignored_names."""
    collected: List[str] = []
    skip_set = set(ignored_names)
    skip_dirs = {"__pycache__", *ignored_dirs}
    for root, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        collected.extend(
            os.path.join(root, fn)
            for fn in sorted(filenames)
            if fn not in skip_set and not fn.endswith(".pyc")
        )
    return collected


def _compile_single_skill(
    toolkit_root: str,
    src_skill_dir: str,
    dst_skill_dir: str,
    skill_name: str,
    skill_filename: str,
    target_dir: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile one skill folder (and bundle host profiles into wf-management)."""
    sidecar_path = os.path.join(src_skill_dir, "skill.json")
    sidecar = _load_json_file(sidecar_path) if os.path.isfile(sidecar_path) else {"name": skill_name, "description": skill_name}
    written = 0
    installed: List[str] = []
    ignored_subdirs = ("hosts",) if skill_name == "wf-management" else ()
    for src_file in _iter_asset_files(src_skill_dir, (".DS_Store", "skill.json"), ignored_subdirs):
        w, dst_file = _sync_single_skill_file(
            src_file, src_skill_dir, dst_skill_dir, skill_filename, skill_name, sidecar, profile, dry_run
        )
        written += w
        installed.append(os.path.relpath(dst_file, target_dir))
    if skill_name == "wf-management":
        b_written, b_files = _bundle_hosts_into_skill(toolkit_root, dst_skill_dir, target_dir, dry_run)
        written += b_written
        installed.extend(b_files)
    return written, installed


def _compile_skills_for_host(
    toolkit_root: str,
    skills_src: Optional[str],
    skill_names: Sequence[str],
    host_root: str,
    target_dir: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile SKILL.md and copy supporting skill files for one host."""
    cfg = profile.get("dirs", {}).get("skills")
    if not cfg or not skills_src:
        return 0, []
    written = 0
    installed: List[str] = []
    skill_filename = cfg.get("filename", "SKILL.md")
    for skill_name in skill_names:
        src_skill_dir = os.path.join(skills_src, skill_name)
        if not os.path.isdir(src_skill_dir):
            continue
        dst_skill_dir = os.path.join(host_root, cfg["path"], skill_name)
        w, files = _compile_single_skill(
            toolkit_root, src_skill_dir, dst_skill_dir, skill_name, skill_filename, target_dir, profile, dry_run
        )
        written += w
        installed.extend(files)
    return written, installed


def _sync_single_team_file(
    src_file: str,
    src_team_dir: str,
    dst_team_dir: str,
    team_name: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, str]:
    """Rewrite markdown links or copy a manifest file inside a team pack directory."""
    rel_in_team = os.path.relpath(src_file, src_team_dir)
    dst_file = os.path.join(dst_team_dir, rel_in_team)
    if src_file.endswith(".md"):
        with open(src_file, "r", encoding="utf-8") as fh:
            rewritten = rewrite_relative_links_for_host(fh.read(), f"teams/{team_name}", profile)
        changed = _write_text_if_changed(dst_file, rewritten, dry_run=dry_run)
    else:
        changed = _copy_binary_if_changed(src_file, dst_file, dry_run=dry_run)
    return int(changed), dst_file


def _compile_teams_for_host(
    teams_src: Optional[str],
    team_names: Sequence[str],
    host_root: str,
    target_dir: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile team pack markdown links and copy pack manifests for one host."""
    cfg = profile.get("dirs", {}).get("teams")
    if not cfg or not teams_src:
        return 0, []
    written = 0
    installed: List[str] = []
    for team_name in team_names:
        src_team_dir = os.path.join(teams_src, team_name)
        if not os.path.isdir(src_team_dir):
            continue
        dst_team_dir = os.path.join(host_root, cfg["path"], team_name)
        for src_file in _iter_asset_files(src_team_dir, (".DS_Store",)):
            w, dst_file = _sync_single_team_file(src_file, src_team_dir, dst_team_dir, team_name, profile, dry_run)
            written += w
            installed.append(os.path.relpath(dst_file, target_dir))
    return written, installed


def is_workforces_grok_ns(ns: str, val: Any) -> bool:
    """Return True if a top-level .grok/hooks.json entry belongs to Workforces."""
    if str(ns).startswith(("wf-", "workforce-")):
        return True
    if not isinstance(val, dict):
        return False
    return any(isinstance(rules, list) and any(_is_workforces_hook_rule(r) for r in rules) for rules in val.values())


def _sync_compiled_grok_hooks(
    grok_hooks_dst: str, aggregated_hooks: Dict[str, Any], dry_run: bool
) -> int:
    """Merge compiled Workforces namespaces into .grok/hooks.json while preserving user keys."""
    preserved: Dict[str, Any] = {}
    if os.path.isfile(grok_hooks_dst):
        try:
            raw = Path(grok_hooks_dst).read_text(encoding="utf-8").strip()
            existing = json.loads(raw) if raw else {}
            if isinstance(existing, dict):
                preserved = {k: v for k, v in existing.items() if not is_workforces_grok_ns(k, v)}
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"[compile_assets] Warning: invalid Grok hooks JSON {grok_hooks_dst}: {exc}\n")
            preserved = {}
    merged = {**preserved, **aggregated_hooks}
    if merged:
        return int(_write_text_if_changed(grok_hooks_dst, json.dumps(merged, indent=2) + "\n", dry_run))
    if os.path.isfile(grok_hooks_dst):
        if not dry_run:
            os.remove(grok_hooks_dst)
        return 1
    return 0


def _emit_plugin_bundle(
    meta: Dict[str, Any],
    host_root: str,
    plugins_sub: str,
    target_dir: str,
    profile: Dict[str, Any],
    aggregated_hooks: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Emit plugin.json and optional hooks.json for one plugin bundle."""
    pl_name = meta["name"]
    pl_out_dir = os.path.join(host_root, plugins_sub, pl_name)
    manifest_out = {
        "name": pl_name,
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
    }
    pjson_dst = os.path.join(pl_out_dir, "plugin.json")
    written = int(_write_text_if_changed(pjson_dst, json.dumps(manifest_out, indent=2) + "\n", dry_run))
    installed = [os.path.relpath(pjson_dst, target_dir)]
    compiled_hooks = compile_plugin_hooks_for_host(meta, profile)
    if compiled_hooks:
        ns = meta.get("hook_namespace", pl_name)
        aggregated_hooks[ns] = compiled_hooks
        hjson_dst = os.path.join(pl_out_dir, "hooks.json")
        written += int(_write_text_if_changed(hjson_dst, json.dumps({ns: compiled_hooks}, indent=2) + "\n", dry_run))
        installed.append(os.path.relpath(hjson_dst, target_dir))
    return written, installed


def _compile_plugins_for_host(
    plugins_src: Optional[str],
    plugin_names: Sequence[str],
    host_root: str,
    target_dir: str,
    profile: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile plugin manifests and host-native lifecycle hooks for one host."""
    mode = profile.get("hooks_mode", "none")
    if mode == "none" or not plugins_src:
        return 0, []
    metas = [
        _load_json_file(os.path.join(plugins_src, pl_name, "plugin.json"))
        for pl_name in plugin_names
        if os.path.isfile(os.path.join(plugins_src, pl_name, "plugin.json"))
    ]
    if mode == "claude_settings_json":
        changed, _ = sync_claude_settings_hooks(target_dir, metas, profile, dry_run=dry_run)
        return int(changed), []
    written = 0
    installed: List[str] = []
    plugins_sub = profile.get("dirs", {}).get("plugins", {}).get("path", "plugins")
    aggregated_hooks: Dict[str, Any] = {}
    for meta in metas:
        b_written, b_files = _emit_plugin_bundle(meta, host_root, plugins_sub, target_dir, profile, aggregated_hooks, dry_run)
        written += b_written
        installed.extend(b_files)
    if mode == "grok_hooks_and_plugins":
        grok_hooks_dst = os.path.join(target_dir, profile.get("hooks_target", os.path.join(".grok", "hooks.json")))
        written += _sync_compiled_grok_hooks(grok_hooks_dst, aggregated_hooks, dry_run)
        if aggregated_hooks:
            installed.append(os.path.relpath(grok_hooks_dst, target_dir))
    return written, installed


def _install_single_host(
    root: str,
    target: str,
    profile: Dict[str, Any],
    src_dirs: Dict[str, Optional[str]],
    manifest: Dict[str, Any],
    dry_run: bool,
) -> Tuple[int, List[str]]:
    """Compile and write all categories for a single resolved AI host."""
    host_root = os.path.join(target, profile["base_dir"])
    host_written = 0
    installed: List[str] = []
    for cat in ("agents", "rules", "workflows"):
        w, files = _compile_flat_category(src_dirs[cat], manifest.get(cat, []), cat, host_root, target, profile, dry_run)
        host_written += w
        installed.extend(files)
    steps = (
        _compile_skills_for_host(root, src_dirs["skills"], manifest.get("skills", []), host_root, target, profile, dry_run),
        _compile_teams_for_host(src_dirs["teams"], manifest.get("teams", []), host_root, target, profile, dry_run),
        _compile_plugins_for_host(src_dirs["plugins"], manifest.get("plugins", []), host_root, target, profile, dry_run),
    )
    for w, files in steps:
        host_written += w
        installed.extend(files)
    return host_written, installed


def install_compiled_hosts(
    toolkit_root: str,
    target_dir: str,
    hosts: Sequence[str],
    manifest: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Compile and write all resolved toolkit assets across all active AI hosts."""
    root = os.path.abspath(toolkit_root)
    target = os.path.abspath(target_dir)
    profiles = load_host_profiles(root)
    resolved_hosts = _order_hosts([resolve_host_alias(h, profiles) or h for h in hosts if (resolve_host_alias(h, profiles) or h) in profiles])
    src_dirs = {cat: _find_source_dir(root, cat) for cat in ("agents", "rules", "workflows", "skills", "teams", "plugins")}
    total_written = 0
    all_installed: List[str] = []
    per_host: Dict[str, int] = {}
    for host_id in resolved_hosts:
        w, files = _install_single_host(root, target, profiles[host_id], src_dirs, manifest, dry_run)
        per_host[host_id] = w
        total_written += w
        all_installed.extend(files)
    return {
        "hosts": resolved_hosts,
        "written": total_written,
        "per_host_written": per_host,
        "installed_files": sorted(set(all_installed)),
    }


def _sync_source_category_files(
    src_dir: str, category: str, ag_profile: Dict[str, Any], dry_run: bool
) -> int:
    """Sync source .md files in agents/ or rules/ from adjacent sidecar .json files."""
    if not os.path.isdir(src_dir):
        return 0
    updated = 0
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".json"):
            continue
        stem = fn[:-5]
        md_path = os.path.join(src_dir, f"{stem}.md")
        if not os.path.isfile(md_path):
            continue
        sidecar = _load_json_file(os.path.join(src_dir, fn))
        with open(md_path, "r", encoding="utf-8") as fh:
            compiled = compile_markdown_asset(fh.read(), sidecar, category, ag_profile)
        updated += int(_write_text_if_changed(md_path, compiled, dry_run=dry_run))
    return updated


def _sync_source_skills(root: str, ag_profile: Dict[str, Any], dry_run: bool) -> int:
    """Sync source skills/*/SKILL.md files and wf-management bundled hosts."""
    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        return 0
    updated = 0
    for skill_name in sorted(os.listdir(skills_dir)):
        sdir = os.path.join(skills_dir, skill_name)
        sjson = os.path.join(sdir, "skill.json")
        smd = os.path.join(sdir, "SKILL.md")
        if os.path.isfile(sjson) and os.path.isfile(smd):
            sidecar = _load_json_file(sjson)
            with open(smd, "r", encoding="utf-8") as fh:
                compiled = compile_markdown_asset(fh.read(), sidecar, f"skills/{skill_name}", ag_profile)
            updated += int(_write_text_if_changed(smd, compiled, dry_run=dry_run))
    wf_mgmt_dir = os.path.join(skills_dir, "wf-management")
    if os.path.isdir(wf_mgmt_dir) and os.path.isdir(os.path.join(root, "config", "hosts")):
        w_hosts, _ = _bundle_hosts_into_skill(root, wf_mgmt_dir, root, dry_run=dry_run)
        updated += w_hosts
    return updated


def _sync_source_plugins(root: str, ag_profile: Dict[str, Any], dry_run: bool) -> int:
    """Sync source plugins/*/hooks.json files from canonical plugin.json specs."""
    plugins_dir = os.path.join(root, "plugins")
    if not os.path.isdir(plugins_dir):
        return 0
    updated = 0
    for pl_name in sorted(os.listdir(plugins_dir)):
        pdir = os.path.join(plugins_dir, pl_name)
        pjson = os.path.join(pdir, "plugin.json")
        if not os.path.isfile(pjson):
            continue
        meta = _load_json_file(pjson)
        compiled_hooks = compile_plugin_hooks_for_host(meta, ag_profile)
        hjson = os.path.join(pdir, "hooks.json")
        if compiled_hooks:
            ns = meta.get("hook_namespace", pl_name)
            payload = json.dumps({ns: compiled_hooks}, indent=2) + "\n"
            updated += int(_write_text_if_changed(hjson, payload, dry_run=dry_run))
        elif os.path.isfile(hjson) and not dry_run:
            os.remove(hjson)
            updated += 1
    return updated


def sync_source_frontmatter(toolkit_root: str, dry_run: bool = False) -> int:
    """Synchronize source repository .md files with canonical Antigravity frontmatter & hooks."""
    root = os.path.abspath(toolkit_root)
    ag_profile = load_host_profiles(root)["antigravity"]
    updated = _sync_source_category_files(os.path.join(root, "agents"), "agents", ag_profile, dry_run)
    updated += _sync_source_category_files(os.path.join(root, "rules"), "rules", ag_profile, dry_run)
    updated += _sync_source_skills(root, ag_profile, dry_run)
    updated += _sync_source_plugins(root, ag_profile, dry_run)
    return updated


def _resolve_cli_manifest(
    toolkit_root: str, target_dir: str, teams_arg: Optional[str], manifest_json_arg: Optional[str]
) -> Dict[str, Any]:
    """Load manifest from --manifest-json (file or inline JSON) or resolve via resolve_manifest."""
    if manifest_json_arg:
        cand = manifest_json_arg.strip()
        if os.path.isfile(cand):
            return _load_json_file(cand)
        parsed = json.loads(cand)
        if not isinstance(parsed, dict):
            raise ValueError("--manifest-json must evaluate to a JSON object")
        return parsed
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import resolve_manifest as rm  # type: ignore

    return rm.resolve_manifest(toolkit_root, target_dir, teams_arg)


def _effective_auto_detect(target_dir: str, no_auto_detect: bool, force_auto: bool) -> bool:
    """Resolve effective auto_detect_hosts setting from CLI flags and saved config."""
    if no_auto_detect:
        return False
    if force_auto:
        return True
    cfg = load_install_config(target_dir)
    return bool(cfg.get("auto_detect_hosts", True)) if cfg else True


def _has_explicit_or_detected_hosts(
    target_dir: str,
    profiles: Dict[str, Dict[str, Any]],
    hosts_arg: Optional[str],
    auto_detect: bool,
    force_auto: bool = False,
) -> bool:
    """Return True if hosts came from CLI flag, saved config.json, or workspace markers."""
    arg_clean = (hosts_arg or "").strip()
    if arg_clean and arg_clean.lower() != "auto":
        return True
    cfg = load_install_config(target_dir)
    if cfg and cfg.get("hosts"):
        return True
    should_detect = auto_detect and (True if force_auto else (bool(cfg.get("auto_detect_hosts", True)) if cfg else True))
    return bool(should_detect and detect_workspace_hosts(target_dir, profiles))


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for compile_assets.py."""
    parser = argparse.ArgumentParser(description="Workforces Multi-AI Asset & Frontmatter Compiler")
    parser.add_argument("--toolkit-root", default=".", help="Path to Workforces toolkit root")
    parser.add_argument("--target", default=".", help="Target project workspace directory")
    parser.add_argument("--hosts", "--editor", dest="hosts", default=None, help="Comma-separated hosts, 'auto', or 'all'")
    parser.add_argument("--no-auto-detect", action="store_true", help="Disable auto-detecting workspace AI folders")
    parser.add_argument("--auto-detect", action="store_true", help="Re-enable workspace AI folder auto-detection")
    parser.add_argument("--teams", default=None, help="Comma-separated team packs ('all', 'none', or list)")
    parser.add_argument("--manifest-json", default=None, help="Path or inline JSON of resolved manifest")
    parser.add_argument("--save-config", action="store_true", help="Persist settings to workforces/config.json")
    parser.add_argument("--repo-type", default=None, help="Repository type ('project', 'workforce', or 'personal')")
    parser.add_argument("--sync-source", action="store_true", help="Sync source .md frontmatter & plugin hooks.json")
    parser.add_argument("--detect-only", action="store_true", help="Print resolved active hosts and exit")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--dry", "--dry-run", dest="dry", action="store_true", help="Dry run without writing files")
    return parser


def _run_sync_source_cli(args: argparse.Namespace) -> int:
    """Execute --sync-source CLI mode and print summary."""
    changed = sync_source_frontmatter(args.toolkit_root, dry_run=args.dry)
    if args.json:
        print(json.dumps({"synced_files": changed, "dry_run": args.dry}))
    else:
        mode_label = "Would update" if args.dry else "Synchronized"
        print(f"{mode_label} {changed} source file(s) from canonical sidecar JSON.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint for compiling multi-host toolkit assets."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.sync_source:
        return _run_sync_source_cli(args)
    profiles = load_host_profiles(args.toolkit_root)
    force_auto = bool(args.auto_detect or (args.hosts and args.hosts.strip().lower() == "auto")) and not args.no_auto_detect
    eff_auto = _effective_auto_detect(args.target, args.no_auto_detect, force_auto)
    try:
        active_hosts = resolve_active_hosts(
            args.target, profiles, hosts_arg=args.hosts, auto_detect=eff_auto, force_auto_detect=force_auto
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.detect_only:
        explicit_det = _has_explicit_or_detected_hosts(args.target, profiles, args.hosts, eff_auto, force_auto)
        payload = {"hosts": active_hosts, "explicit_or_detected": explicit_det, "auto_detect_hosts": eff_auto}
        print(json.dumps(payload) if args.json else ",".join(active_hosts))
        return 0
    manifest = _resolve_cli_manifest(args.toolkit_root, args.target, args.teams, args.manifest_json)
    summary = install_compiled_hosts(args.toolkit_root, args.target, active_hosts, manifest, dry_run=args.dry)
    if args.save_config and not args.dry:
        repo_type = args.repo_type or infer_repo_type(args.target) or "project"
        teams = manifest.get("installed_teams") or manifest.get("teams") or []
        summary["config_path"] = save_install_config(
            args.target, active_hosts, repo_type, teams, profiles, auto_detect_hosts=eff_auto
        )
    msg = f"{'Would write' if args.dry else 'Compiled'} {summary['written']} file(s) across hosts: {', '.join(summary['hosts'])}"
    print(json.dumps(summary, indent=2) if args.json else msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
