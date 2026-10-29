#!/usr/bin/env bash
# Workforces Multi-AI Toolkit Updater
# Prunes obsolete toolkit files, compiles canonical sidecar metadata + Markdown into
# all active AI host layouts, and migrates legacy workspace references.
#
# Usage:
#   bash skills/wf-management/scripts/update.sh /path/to/project [options]

set -euo pipefail

# python3 is the usual name; Windows (including Grok Build) often only has `python`.
PYTHON=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
    PYTHON="$cand"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "Error: Python 3 is required to run Workforces multi-host updater." >&2
  exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TARGET=""
DRY=false
FORCE=false
NON_INTERACTIVE=false
HOSTS_ARG=""
NO_AUTO_DETECT=false
FORCE_AUTO_DETECT=false
VSCODE_ALIAS_USED=false

usage() {
  echo -e "${BOLD}Workforces Toolkit Updater${NC}"
  echo ""
  echo "Usage: bash skills/wf-management/scripts/update.sh <target-project-path> [options]"
  echo ""
  echo "Options:"
  echo "  --hosts <list>         AI hosts: auto, all, or CSV (antigravity,claude,grok,copilot,cursor)"
  echo "  --editor <list>        Alias for --hosts (supports gemini, vscode, github, claude-code, grok-build)"
  echo "  --no-auto-detect       Disable workspace folder auto-detection (use saved config / explicit --hosts)"
  echo "  --dry, --dry-run       Show what would change without modifying files"
  echo "  --force                Force re-sync of all toolkit files regardless of version hash"
  echo "  --non-interactive      Run without prompting"
  echo "  --help, -h             Show this help menu"
  echo ""
  exit "${1:-0}"
}

record_hosts_arg() {
  HOSTS_ARG="$1"
  local norm_hosts
  norm_hosts="$(printf '%s' "$HOSTS_ARG" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  if [[ ",$norm_hosts," == *",vscode,"* || ",$norm_hosts," == *",vs-code,"* ]]; then
    VSCODE_ALIAS_USED=true
  fi
  if [[ "$norm_hosts" == "auto" && "$NO_AUTO_DETECT" == false ]]; then
    FORCE_AUTO_DETECT=true
  fi
}

if [[ $# -lt 1 ]]; then
  usage 0
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage 0
fi

TARGET="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry|--dry-run)
      DRY=true
      ;;
    --force)
      FORCE=true
      ;;
    --non-interactive)
      NON_INTERACTIVE=true
      ;;
    --hosts|--editor)
      [[ $# -ge 2 ]] || { echo -e "${RED}Error: Missing value for $1${NC}" >&2; usage 1; }
      shift
      record_hosts_arg "${1:-}"
      ;;
    --hosts=*|--editor=*)
      record_hosts_arg "${1#*=}"
      ;;
    --no-auto-detect)
      NO_AUTO_DETECT=true
      FORCE_AUTO_DETECT=false
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}" >&2
      usage 1
      ;;
  esac
  shift
done

if [[ ! -d "$TARGET" ]]; then
  echo -e "${RED}Error: Target directory does not exist: $TARGET${NC}"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"
VERSION_FILE="$TARGET/workforces/.version"
WORKFORCES_REPO_EXPLICIT="${WORKFORCES_REPO:-}"
WORKFORCES_REPO="${WORKFORCES_REPO:-https://github.com/wedigcode/workforces.git}"
TMP_BASE="${TMPDIR:-/tmp}"
TMP_ROOT="$(mktemp -d "${TMP_BASE%/}/workforces-update.XXXXXX")"
TMP_DIR="$TMP_ROOT/repo"
trap 'rm -rf "$TMP_ROOT"' EXIT

INSTALLED_HASH="unknown"
if [[ -f "$VERSION_FILE" ]]; then
  INSTALLED_HASH=$(grep "^commit:" "$VERSION_FILE" | awk '{print $2}' || echo "unknown")
fi

echo -e ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${BOLD}Workforces Updater${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Target:    $TARGET"
echo -e "  Installed: ${INSTALLED_HASH}"
[[ "$DRY" == true ]] && echo -e "  ${YELLOW}Mode: DRY RUN — no files will be written${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." 2>/dev/null && pwd || true)"

if [[ -n "${WORKFORCES_UPDATE_SOURCE_DIR:-}" && -d "${WORKFORCES_UPDATE_SOURCE_DIR}/skills" ]]; then
  echo -e "${BOLD}▸ Using configured source directory...${NC}"
  SOURCE_DIR="$(cd "$WORKFORCES_UPDATE_SOURCE_DIR" && pwd)"
  LATEST_HASH=$(git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
elif [[ -z "$WORKFORCES_REPO_EXPLICIT" && -d "$TOOLKIT_ROOT/.git" && -d "$TOOLKIT_ROOT/skills" ]]; then
  echo -e "${BOLD}▸ Using local repo as source...${NC}"
  SOURCE_DIR="$TOOLKIT_ROOT"
  LATEST_HASH=$(git -C "$TOOLKIT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
elif [[ -z "$WORKFORCES_REPO_EXPLICIT" && -n "$MONOREPO_ROOT" && -d "$MONOREPO_ROOT/.git" && -f "$MONOREPO_ROOT/skills/wf-management/scripts/resolve_manifest.py" && -d "$MONOREPO_ROOT/teams" ]]; then
  echo -e "${BOLD}▸ Using local repo as source...${NC}"
  SOURCE_DIR="$MONOREPO_ROOT"
  LATEST_HASH=$(git -C "$MONOREPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
else
  echo -e "${BOLD}▸ Fetching latest workforces from remote...${NC}"
  if ! git clone --depth=1 "$WORKFORCES_REPO" "$TMP_DIR" 2>/dev/null || [[ ! -d "$TMP_DIR/skills" ]]; then
    echo -e "${RED}Error: Failed to clone workforces repository from $WORKFORCES_REPO${NC}" >&2
    exit 1
  fi
  SOURCE_DIR="$TMP_DIR"
  LATEST_HASH=$(git -C "$TMP_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

echo -e "  Latest:    ${LATEST_HASH}"

COMPILER_SCRIPT="$SOURCE_DIR/skills/wf-management/scripts/compile_assets.py"
RESOLVER_SCRIPT="$SOURCE_DIR/skills/wf-management/scripts/resolve_manifest.py"
if [[ ! -f "$RESOLVER_SCRIPT" && -f "$SOURCE_DIR/skills/workforce-management/scripts/resolve_manifest.py" ]]; then
  RESOLVER_SCRIPT="$SOURCE_DIR/skills/workforce-management/scripts/resolve_manifest.py"
fi

# ─── Resolve Active Hosts ───
DETECT_ARGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --detect-only --json)
[[ -n "$HOSTS_ARG" ]] && DETECT_ARGS+=(--hosts "$HOSTS_ARG")
[[ "$NO_AUTO_DETECT" == true ]] && DETECT_ARGS+=(--no-auto-detect)
[[ "$FORCE_AUTO_DETECT" == true ]] && DETECT_ARGS+=(--auto-detect)

if ! DETECT_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${DETECT_ARGS[@]}"); then
  echo -e "${RED}Error: Failed to resolve AI hosts.${NC}" >&2
  exit 1
fi
ACTIVE_HOSTS_CSV=$("$PYTHON" -c "import json,sys; print(','.join(json.loads(sys.argv[1])['hosts']))" "$DETECT_JSON")
EFFECTIVE_AUTO_DETECT=$("$PYTHON" -c "import json,sys; print('true' if json.loads(sys.argv[1]).get('auto_detect_hosts', True) else 'false')" "$DETECT_JSON")
echo -e "  Hosts:     ${CYAN}${ACTIVE_HOSTS_CSV}${NC}"

has_active_host() {
  [[ ",$ACTIVE_HOSTS_CSV," == *",$1,"* ]]
}

# ─── Ensure workforces/tmp and workforces/session-context in .gitignore ───
GITIGNORE_FILE="$TARGET/.gitignore"
add_update_gitignore_entry() {
  local entry="$1"
  local label="$2"
  if [[ ! -f "$GITIGNORE_FILE" ]]; then
    if [[ "$DRY" == true ]]; then
      echo -e "  ${GREEN}WOULD CREATE:${NC} .gitignore with '$label'"
    else
      echo "$entry" > "$GITIGNORE_FILE"
      echo -e "  ${GREEN}CREATED:${NC} .gitignore with '$label'"
    fi
  elif ! grep -qs "^/\?${entry//\*/\\*}" "$GITIGNORE_FILE" && ! grep -qs "^/\?workforces/\?$" "$GITIGNORE_FILE"; then
    if [[ "$DRY" == true ]]; then
      echo -e "  ${YELLOW}WOULD ADD:${NC} '$label' to .gitignore"
    else
      if [[ -s "$GITIGNORE_FILE" ]] && [[ "$(tail -c 1 "$GITIGNORE_FILE")" != $'\n' ]]; then
        echo "" >> "$GITIGNORE_FILE"
      fi
      echo "$entry" >> "$GITIGNORE_FILE"
      echo -e "  ${GREEN}ADDED:${NC} '$label' to .gitignore"
    fi
  fi
}

add_update_gitignore_entry "workforces/tmp" "workforces/tmp"
add_update_gitignore_entry "workforces/session-context/*" "workforces/session-context/*"
add_update_gitignore_entry "!workforces/session-context/.gitkeep" "!workforces/session-context/.gitkeep"
add_update_gitignore_entry "workforces/memory" "workforces/memory"
add_update_gitignore_entry ".worktrees" ".worktrees (agent parallelization)"

if [[ "$DRY" != true ]]; then
  mkdir -p "$TARGET/workforces/tmp" "$TARGET/workforces/session-context"
  touch "$TARGET/workforces/session-context/.gitkeep"
fi

# ─── Resolve Assets via Team Manifest Resolver ───
RESOLVER_OK=false
RESOLVE_ARGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --format bash-export)
[[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && RESOLVE_ARGS+=(--no-auto-detect)

if [[ -f "$RESOLVER_SCRIPT" ]]; then
  if RESOLVER_OUTPUT=$("$PYTHON" "$RESOLVER_SCRIPT" "${RESOLVE_ARGS[@]}"); then
    eval "$RESOLVER_OUTPUT"
    RESOLVER_OK=true
  fi
fi
if [[ "$RESOLVER_OK" != true ]]; then
  ALLOWED_AGENTS="wf-project-manager.md wf-scribe.md wf-programmer.md wf-designer.md"
  ALLOWED_RULES="wf-base.md wf-clean-coder.md wf-design-standards.md wf-lean-execution.md wf-mcp-protection.md wf-session-context.md wf-file-integrity.md wf-git-workflow.md"
  ALLOWED_SKILLS="wf-agent-parallelization wf-brand-guidelines wf-clean-coder wf-code-graph wf-codebase-improvement wf-design-anti-patterns wf-doc-generator wf-image-workflow wf-integrity-validator wf-issue-tracker wf-jules-integration wf-launch-playbook wf-market-validation wf-memory-management wf-persona-management wf-post-code-review wf-pr-review wf-session-context wf-site-setup wf-social-engagement wf-task-tracker wf-ui-ux-design wf-usage-tracker wf-visual-design-fundamentals wf-management wf-canvas wf-github-project-planning wf-hypothesis-tracker wf-plan wf-sync wf-advisor wf-ideate wf-investigate wf-question-formulation wf-update wf-dashboard"
  ALLOWED_WORKFLOWS=""
  ALLOWED_PLUGINS="wf-programming-plugin wf-integrity-plugin"
  ALLOWED_TEAMS="dev design"
  INSTALLED_TEAMS_LIST="dev design"
fi

discover_new_upstream_teams() {
  NEW_TEAMS_AVAILABLE=()
  if [[ -d "$SOURCE_DIR/teams" ]]; then
    for stdir in "$SOURCE_DIR/teams"/*; do
      [[ -d "$stdir" && ( -f "$stdir/pack.md" || -f "$stdir/team.json" || -f "$stdir/pack.json" ) ]] || continue
      local team_id
      team_id=$(basename "$stdir")
      if [[ ! " $ALLOWED_TEAMS " =~ " $team_id " ]]; then
        NEW_TEAMS_AVAILABLE+=("$team_id")
      fi
    done
  fi
}

# ─── Multi-Host Drift, Obsolete Asset & Migration Detection ───
NEEDS_UPDATE=false
if [[ "$FORCE" == true || "$INSTALLED_HASH" != "$LATEST_HASH" || "$INSTALLED_HASH" == "unknown" ]]; then
  NEEDS_UPDATE=true
fi

if [[ "$NEEDS_UPDATE" == false ]]; then
  DRY_CHECK_ARGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --dry --json)
  [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && DRY_CHECK_ARGS+=(--no-auto-detect)
  [[ "$FORCE_AUTO_DETECT" == true ]] && DRY_CHECK_ARGS+=(--auto-detect)
  DRY_COMPILE_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${DRY_CHECK_ARGS[@]}")
  PENDING_WRITES=$("$PYTHON" -c "import json,sys; print(json.loads(sys.argv[1]).get('written', 0))" "$DRY_COMPILE_JSON")
  if [[ "$PENDING_WRITES" -gt 0 ]]; then
    NEEDS_UPDATE=true
  fi
fi

if [[ "$NEEDS_UPDATE" == false ]]; then
  STATE_OK=$("$PYTHON" - "$TARGET" "$ACTIVE_HOSTS_CSV" "$EFFECTIVE_AUTO_DETECT" "$VSCODE_ALIAS_USED" << 'PYEOF'
import json, os, sys
target, hosts_csv, eff_auto, vscode_alias = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
expected = [h for h in hosts_csv.split(",") if h]
doc_map = {
    "antigravity": "GEMINI.md",
    "claude": "CLAUDE.md",
    "grok": "AGENTS.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor": "AGENTS.md",
}
for h in expected:
    if not os.path.isfile(os.path.join(target, doc_map[h])):
        print("false"); sys.exit(0)
for rel in ("workforces/config.json", "workforces/.manifest.json"):
    p = os.path.join(target, rel)
    if not os.path.isfile(p):
        print("false"); sys.exit(0)
    try:
        data = json.loads(open(p, encoding="utf-8").read())
    except Exception:
        print("false"); sys.exit(0)
    if data.get("hosts") != expected:
        print("false"); sys.exit(0)
    if rel == "workforces/config.json" and bool(data.get("auto_detect_hosts", True)) != (eff_auto == "true"):
        print("false"); sys.exit(0)
if os.path.isfile(os.path.join(target, ".github", "copilot", "instructions.md")):
    print("false"); sys.exit(0)
vsc = os.path.join(target, ".vscode", "settings.json")
if "copilot" in expected and (os.path.isdir(os.path.join(target, ".vscode")) or vscode_alias == "true") and not os.path.isfile(vsc):
    print("false"); sys.exit(0)
if os.path.isfile(vsc) and ".github/copilot/instructions.md" in open(vsc, encoding="utf-8").read():
    print("false"); sys.exit(0)
for doc in ("GEMINI.md", "CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md"):
    dp = os.path.join(target, doc)
    if os.path.isfile(dp) and "rules/base.md" in open(dp, encoding="utf-8").read():
        print("false"); sys.exit(0)
print("true")
PYEOF
)
  if [[ "$STATE_OK" != "true" ]]; then
    NEEDS_UPDATE=true
  fi
fi

if [[ "$NEEDS_UPDATE" == false && -f "$RESOLVER_SCRIPT" ]]; then
  PRUNE_CHECK_ARGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --prune-obsolete --dry --format json)
  [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && PRUNE_CHECK_ARGS+=(--no-auto-detect)
  if ! "$PYTHON" "$RESOLVER_SCRIPT" "${PRUNE_CHECK_ARGS[@]}" 2>/dev/null | grep -q '"pruned_count": 0'; then
    NEEDS_UPDATE=true
  fi
fi

if [[ "$NEEDS_UPDATE" == false ]]; then
  discover_new_upstream_teams
  echo ""
  echo -e "  ${GREEN}✓ Core toolkit already up to date (${INSTALLED_HASH})${NC}"
  if [[ ${#NEW_TEAMS_AVAILABLE[@]} -gt 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}💡 New Team Packs available in upstream workforces:${NC}"
    for nt in "${NEW_TEAMS_AVAILABLE[@]}"; do
      echo -e "     - ${CYAN}$nt${NC}"
    done
  fi
  echo ""
  exit 0
fi

echo -e "${BOLD}▸ Updating toolkit across active hosts (${ACTIVE_HOSTS_CSV})${NC}"
echo -e "  Active Installed Teams: ${GREEN}${INSTALLED_TEAMS_LIST:-core}${NC}"
echo ""

# ─── Prune Obsolete Toolkit Assets Across Active Hosts ───
if [[ -f "$RESOLVER_SCRIPT" ]]; then
  echo -e "${BOLD}▸ Scanning for obsolete toolkit assets...${NC}"
  PRUNE_FLAGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --prune-obsolete)
  [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && PRUNE_FLAGS+=(--no-auto-detect)
  [[ "$DRY" == true ]] && PRUNE_FLAGS+=(--dry)
  "$PYTHON" "$RESOLVER_SCRIPT" "${PRUNE_FLAGS[@]}"
  echo ""
fi

# ─── Compile Assets & Lifecycle Hooks Across Active Hosts ───
COMPILE_FLAGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --save-config --json)
[[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && COMPILE_FLAGS+=(--no-auto-detect)
[[ "$FORCE_AUTO_DETECT" == true ]] && COMPILE_FLAGS+=(--auto-detect)
[[ "$DRY" == true ]] && COMPILE_FLAGS+=(--dry)

COMPILE_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${COMPILE_FLAGS[@]}")
COPIED=$("$PYTHON" -c "import json,sys; print(json.loads(sys.argv[1]).get('written', 0))" "$COMPILE_JSON")
TOTAL_MANAGED=$("$PYTHON" -c "import json,sys; print(len(json.loads(sys.argv[1]).get('installed_files', [])))" "$COMPILE_JSON")
SKIPPED=$(( TOTAL_MANAGED >= COPIED ? TOTAL_MANAGED - COPIED : 0 ))

discover_new_upstream_teams

# ─── Migrate Legacy Copilot & Host Root Instructions ───
LEGACY_CP_INST="$TARGET/.github/copilot/instructions.md"
NEW_CP_INST="$TARGET/.github/copilot-instructions.md"
if [[ -f "$LEGACY_CP_INST" ]]; then
  if [[ "$DRY" == true ]]; then
    echo -e "  ${YELLOW}WOULD MIGRATE:${NC} .github/copilot/instructions.md -> .github/copilot-instructions.md"
  else
    mkdir -p "$TARGET/.github"
    "$PYTHON" - "$LEGACY_CP_INST" "$NEW_CP_INST" << 'PYEOF'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
for old, new in (
    (".github/copilot/rules/base.md", ".github/instructions/wf-base.instructions.md"),
    (".github/copilot/rules/wf-base.md", ".github/instructions/wf-base.instructions.md"),
    ("rules/base.md", "instructions/wf-base.instructions.md"),
    (".github/copilot/rules/", ".github/instructions/"),
    (".github/copilot/agents/", ".github/agents/"),
    (".github/copilot/skills/", ".github/skills/"),
    (".github/copilot/workflows/", ".github/prompts/"),
):
    text = text.replace(old, new)
if not os.path.isfile(dst):
    open(dst, "w", encoding="utf-8").write(text)
os.remove(src)
cp_dir = os.path.dirname(src)
try:
    if os.path.isdir(cp_dir) and not os.listdir(cp_dir):
        os.rmdir(cp_dir)
except OSError:
    pass
PYEOF
    echo -e "  ${GREEN}MIGRATED:${NC} .github/copilot/instructions.md -> .github/copilot-instructions.md"
  fi
fi

VSCODE_SETTINGS="$TARGET/.vscode/settings.json"
if [[ -f "$VSCODE_SETTINGS" ]] && grep -qs "\.github/copilot/instructions\.md" "$VSCODE_SETTINGS"; then
  if [[ "$DRY" == true ]]; then
    echo -e "  ${YELLOW}WOULD UPDATE:${NC} .vscode/settings.json (.github/copilot/instructions.md -> .github/copilot-instructions.md)"
  else
    "$PYTHON" -c "import sys; p=sys.argv[1]; s=open(p,encoding='utf-8').read().replace('.github/copilot/instructions.md','.github/copilot-instructions.md'); open(p,'w',encoding='utf-8').write(s)" "$VSCODE_SETTINGS"
    echo -e "  ${GREEN}UPDATED:${NC} .vscode/settings.json"
  fi
fi

for host_doc in "$TARGET/GEMINI.md" "$TARGET/CLAUDE.md" "$TARGET/AGENTS.md" "$TARGET/.github/copilot-instructions.md"; do
  if [[ -f "$host_doc" ]] && grep -qs "rules/base.md" "$host_doc"; then
    rel_doc="${host_doc#$TARGET/}"
    if [[ "$DRY" == true ]]; then
      echo -e "  ${YELLOW}WOULD UPDATE:${NC} $rel_doc (rules/base.md -> rules/wf-base.md)"
    else
      "$PYTHON" - "$host_doc" "$rel_doc" << 'PYEOF'
import sys
p, rel = sys.argv[1], sys.argv[2]
s = open(p, encoding="utf-8").read()
if rel == ".github/copilot-instructions.md":
    s = s.replace(".github/copilot/rules/base.md", ".github/instructions/wf-base.instructions.md")
    s = s.replace("rules/base.md", "instructions/wf-base.instructions.md")
else:
    s = s.replace("rules/base.md", "rules/wf-base.md")
open(p, "w", encoding="utf-8").write(s)
PYEOF
      echo -e "  ${GREEN}UPDATED:${NC} $rel_doc (migrated legacy base rule reference)"
    fi
  fi
done

# ─── Generate Missing Root Context Docs for Newly Activated Hosts ───
if [[ "$DRY" != true ]]; then
  if has_active_host "antigravity" && [[ ! -f "$TARGET/GEMINI.md" ]]; then
    cat > "$TARGET/GEMINI.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit.

## Toolkit Structures
- Config, Personas & Skills: \`.agents/\`
- User Workspace & State: \`workforces/\`

## Instructions
Refer to \`.agents/rules/wf-base.md\` and run modular skills from \`.agents/skills/\` (e.g. \`/wf-plan\`, \`/wf-sync\`, \`/wf-advisor\`) or invoke specialized subagents from \`.agents/agents/\` (e.g. \`@wf-programmer\`, \`@wf-designer\`) to perform tasks.
EOF
    echo -e "  ${GREEN}CREATED:${NC} GEMINI.md"
  fi

  if has_active_host "claude" && [[ ! -f "$TARGET/CLAUDE.md" ]]; then
    cat > "$TARGET/CLAUDE.md" << EOF
# Claude Code Instructions

This project utilizes the Workforces AI toolkit. Please refer to rules in \`.claude/rules/wf-base.md\` and run modular skills from \`.claude/skills/\` (e.g. \`/wf-plan\`, \`/wf-sync\`, \`/wf-advisor\`) or invoke specialist agents from \`.claude/agents/\` (e.g. \`@wf-programmer\`, \`@wf-designer\`).
EOF
    echo -e "  ${GREEN}CREATED:${NC} CLAUDE.md"
  fi

  if has_active_host "copilot"; then
    if [[ ! -f "$TARGET/.github/copilot-instructions.md" ]]; then
      mkdir -p "$TARGET/.github"
      cat > "$TARGET/.github/copilot-instructions.md" << EOF
# GitHub Copilot Instructions

This project utilizes the [workforces](https://github.com/wedigcode/workforces) AI toolkit. Please refer to instructions in \`.github/instructions/wf-base.instructions.md\`, run modular skills from \`.github/skills/\` (e.g. \`/wf-plan\`, \`/wf-sync\`, \`/wf-advisor\`), or invoke specialist custom agents from \`.github/agents/\` (e.g. \`@wf-programmer\`, \`@wf-designer\`).
EOF
      echo -e "  ${GREEN}CREATED:${NC} .github/copilot-instructions.md"
    fi

    if [[ -d "$TARGET/.vscode" || "$VSCODE_ALIAS_USED" == true ]]; then
      mkdir -p "$TARGET/.vscode"
      if [[ ! -f "$TARGET/.vscode/settings.json" ]]; then
        cat > "$TARGET/.vscode/settings.json" << EOF
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".github/copilot-instructions.md" }
  ]
}
EOF
        echo -e "  ${GREEN}CREATED:${NC} .vscode/settings.json"
      fi
    fi
  fi

  if (has_active_host "grok" || has_active_host "cursor") && [[ ! -f "$TARGET/AGENTS.md" ]]; then
    if has_active_host "grok" && has_active_host "cursor"; then
      cat > "$TARGET/AGENTS.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit.

## Toolkit Structures
- Grok Build assets: \`.grok/\` (rules in \`.grok/rules/wf-base.md\`, skills in \`.grok/skills/\`, agents in \`.grok/agents/\`)
- Cursor assets: \`.cursor/\` (rules in \`.cursor/rules/wf-base.mdc\`, skills in \`.cursor/skills/\`, agents in \`.cursor/agents/\`)
- User workspace and state: \`workforces/\`
EOF
    elif has_active_host "cursor"; then
      cat > "$TARGET/AGENTS.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit, configured for Cursor.

## Toolkit Structures
- Rules, personas & skills: \`.cursor/\`
- User workspace and state: \`workforces/\`

## Instructions
Refer to \`.cursor/rules/wf-base.mdc\` and run modular skills from \`.cursor/skills/\` (e.g. \`/wf-plan\`, \`/wf-sync\`, \`/wf-advisor\`) or invoke specialist agents from \`.cursor/agents/\` (e.g. \`@wf-programmer\`, \`@wf-designer\`).
EOF
    else
      cat > "$TARGET/AGENTS.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit, installed for Grok Build.

## Toolkit Structures
- Config, personas, skills: \`.grok/\`
- User workspace and state: \`workforces/\`

## Instructions
Refer to \`.grok/rules/wf-base.md\` and run modular skills from \`.grok/skills/\` (e.g. \`/wf-plan\`, \`/wf-sync\`, \`/wf-advisor\`) or invoke specialist agents from \`.grok/agents/\` (e.g. \`@wf-programmer\`, \`@wf-designer\`).
EOF
    fi
    echo -e "  ${GREEN}CREATED:${NC} AGENTS.md"
  fi
fi

# ─── Write version hash & multi-host manifest ───
if [[ "$DRY" != true ]]; then
  mkdir -p "$(dirname "$VERSION_FILE")"
  cat > "$VERSION_FILE" << EOF
# Workforces Version Info
repo: $WORKFORCES_REPO
commit: $LATEST_HASH
date: $(date -u +%Y-%m-%d)
EOF
  echo -e "  ${GREEN}WRITTEN:${NC} workforces/.version ($LATEST_HASH)"

  if [[ -f "$RESOLVER_SCRIPT" ]]; then
    SAVE_MF_ARGS=(--toolkit-root "$SOURCE_DIR" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --save-manifest --version-hash "$LATEST_HASH")
    [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && SAVE_MF_ARGS+=(--no-auto-detect)
    "$PYTHON" "$RESOLVER_SCRIPT" "${SAVE_MF_ARGS[@]}" >/dev/null
    echo -e "  ${GREEN}WRITTEN:${NC} workforces/.manifest.json"
  fi
fi

echo ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$DRY" == true ]]; then
  echo -e "  ${YELLOW}Dry run complete — no files were modified.${NC}"
else
  echo -e "  ${BOLD}Update Summary:${NC}"
  echo -e "  Updated:  ${GREEN}$COPIED${NC} files"
  echo -e "  Skipped:  $SKIPPED files (already identical)"
  echo -e "  Hosts:    ${CYAN}$ACTIVE_HOSTS_CSV${NC}"
  if [[ ${#NEW_TEAMS_AVAILABLE[@]} -gt 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}💡 New Team Packs available in upstream workforces:${NC}"
    for nt in "${NEW_TEAMS_AVAILABLE[@]}"; do
      echo -e "     - ${CYAN}$nt${NC}"
    done
  fi
  echo ""
  echo -e "  ${GREEN}✓ Toolkit updated to $LATEST_HASH${NC}"
fi
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
