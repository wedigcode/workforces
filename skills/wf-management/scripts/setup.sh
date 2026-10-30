#!/usr/bin/env bash
# Workforces Multi-AI Setup Script
# Compiles and installs agents, rules, skills, workflows, teams, and lifecycle hooks
# from canonical sidecar metadata into one or more AI host layouts.
#
# Usage:
#   bash skills/wf-management/scripts/setup.sh /path/to/project [options]

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
  echo "Error: Python 3 is required to compile multi-host Workforces assets." >&2
  exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TARGET=""
REPO_TYPE=""
HOSTS_ARG=""
NO_AUTO_DETECT=false
FORCE_AUTO_DETECT=false
VSCODE_ALIAS_USED=false
TEAMS_ARG=""
SITE_SETUP=""
NON_INTERACTIVE=false
DRY=false

usage() {
  echo -e "${BOLD}Workforces Setup${NC}"
  echo ""
  echo "Usage: bash skills/wf-management/scripts/setup.sh <target-project-path> [options]"
  echo ""
  echo "Options:"
  echo "  --type <type>          Repo type: workforce or project"
  echo "  --hosts <list>         AI hosts: auto, all, or CSV (antigravity,claude,grok,copilot,cursor)"
  echo "  --editor <list>        Alias for --hosts (supports gemini, vscode, github, claude-code, grok-build)"
  echo "  --no-auto-detect       Do not auto-detect workspace AI host folders (pin explicit --hosts)"
  echo "  --teams <team-list>    Teams to install (e.g. 'dev,design,launch', 'all', 'none')"
  echo "  --site-setup           Initialize Site Setup & Product Brief starter (for greenfield sites)"
  echo "  --skip-site-setup      Skip Site Setup initialization"
  echo "  --non-interactive      Do not prompt for any options (fails on invalid configuration)"
  echo "  --dry, --dry-run       Dry run: simulate setup without copying files or modifying target"
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
    --type)
      [[ $# -ge 2 ]] || { echo -e "${RED}Error: Missing value for $1${NC}" >&2; usage 1; }
      shift
      REPO_TYPE="${1:-}"
      ;;
    --type=*)
      REPO_TYPE="${1#*=}"
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
    --teams)
      [[ $# -ge 2 ]] || { echo -e "${RED}Error: Missing value for $1${NC}" >&2; usage 1; }
      shift
      TEAMS_ARG="${1:-}"
      ;;
    --teams=*)
      TEAMS_ARG="${1#*=}"
      ;;
    --site-setup)
      SITE_SETUP=true
      ;;
    --skip-site-setup)
      SITE_SETUP=false
      ;;
    --non-interactive)
      NON_INTERACTIVE=true
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

COMPILER_SCRIPT="$TOOLKIT_ROOT/skills/wf-management/scripts/compile_assets.py"
if [[ ! -f "$COMPILER_SCRIPT" && -f "$TOOLKIT_ROOT/.agents/skills/wf-management/scripts/compile_assets.py" ]]; then
  COMPILER_SCRIPT="$TOOLKIT_ROOT/.agents/skills/wf-management/scripts/compile_assets.py"
fi
RESOLVER_SCRIPT="$TOOLKIT_ROOT/skills/wf-management/scripts/resolve_manifest.py"
if [[ ! -f "$RESOLVER_SCRIPT" && -f "$TOOLKIT_ROOT/.agents/skills/wf-management/scripts/resolve_manifest.py" ]]; then
  RESOLVER_SCRIPT="$TOOLKIT_ROOT/.agents/skills/wf-management/scripts/resolve_manifest.py"
fi

# Detect if target workspace is empty / greenfield (regex-safe for paths containing brackets)
IS_EMPTY_WORKSPACE=false
NON_DOT_COUNT=$(find "$TARGET" -mindepth 1 -maxdepth 1 -not -name ".*" 2>/dev/null | wc -l | tr -d '[:space:]' || true)
if [[ "${NON_DOT_COUNT:-0}" -eq 0 ]]; then
  IS_EMPTY_WORKSPACE=true
fi

# ─── Site Setup Prompt for Empty Repos ───
if [[ -z "$SITE_SETUP" ]]; then
  if [[ "$IS_EMPTY_WORKSPACE" == true ]]; then
    if [[ "$NON_INTERACTIVE" == true || "$DRY" == true ]]; then
      SITE_SETUP=false
    else
      echo ""
      echo -e "${BOLD}${CYAN}🚀 Empty project workspace detected!${NC}"
      echo "Would you like to initialize a Site Setup & Product Brief (Design Pilot)?"
      read -r -p "Enable site setup? (y/n) [default: y]: " site_choice
      case "$site_choice" in
        n|N|no|No) SITE_SETUP=false ;;
        *) SITE_SETUP=true ;;
      esac
    fi
  else
    SITE_SETUP=false
  fi
fi

# ─── Repo Type Detection / Prompt ───
if [[ -z "$REPO_TYPE" ]]; then
  if [[ "$NON_INTERACTIVE" == true || "$DRY" == true ]]; then
    EXISTING_REPO_TYPE=$("$PYTHON" -c "import os,sys; sys.path.insert(0, sys.argv[1]); import compile_assets as ca; print(ca.infer_repo_type(sys.argv[2]) or '')" "$(dirname "$COMPILER_SCRIPT")" "$TARGET" 2>/dev/null || true)
    if [[ "$EXISTING_REPO_TYPE" == "workforce" || "$EXISTING_REPO_TYPE" == "project" || "$EXISTING_REPO_TYPE" == "personal" ]]; then
      REPO_TYPE="$EXISTING_REPO_TYPE"
    else
      echo -e "${YELLOW}Defaulting repo type to 'project'${NC}"
      REPO_TYPE="project"
    fi
  else
    echo ""
    echo -e "${BOLD}Select repository type:${NC}"
    echo "  1) Workforce (Central command, plans and delegates to other projects)"
    echo "  2) Project (Specific codebase/initiative with its own issue tracking)"
    read -r -p "Select type (1/2): " repo_choice
    case "$repo_choice" in
      1|w|workforce|W|Workforce) REPO_TYPE="workforce" ;;
      2|p|project|P|Project)     REPO_TYPE="project" ;;
      personal|Personal)         REPO_TYPE="personal" ;;
      *) echo -e "${RED}Invalid choice. Defaulting to project.${NC}"; REPO_TYPE="project" ;;
    esac
  fi
fi

if [[ "$REPO_TYPE" != "workforce" && "$REPO_TYPE" != "project" && "$REPO_TYPE" != "personal" ]]; then
  echo -e "${RED}Error: Invalid repo type '$REPO_TYPE'. Must be 'workforce', 'project', or 'personal'.${NC}"
  exit 1
fi

# ─── AI Host Detection & Optional Interactive Multi-Host Prompt ───
DETECT_FLAGS=(--toolkit-root "$TOOLKIT_ROOT" --target "$TARGET" --detect-only --json)
[[ -n "$HOSTS_ARG" ]] && DETECT_FLAGS+=(--hosts "$HOSTS_ARG")
[[ "$NO_AUTO_DETECT" == true ]] && DETECT_FLAGS+=(--no-auto-detect)
[[ "$FORCE_AUTO_DETECT" == true ]] && DETECT_FLAGS+=(--auto-detect)

if ! DETECT_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${DETECT_FLAGS[@]}"); then
  echo -e "${RED}Error: Failed to resolve AI hosts for '$HOSTS_ARG'.${NC}" >&2
  exit 1
fi

EXPLICIT_OR_DETECTED=$("$PYTHON" -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('explicit_or_detected') else 'false')" "$DETECT_JSON")

map_interactive_hosts() {
  local raw="${1// /,}"
  if [[ -z "$raw" ]]; then
    echo "antigravity"
    return
  fi
  local mapped=()
  IFS=',' read -ra tokens <<< "$raw"
  for tok in "${tokens[@]}"; do
    tok="$(echo "$tok" | tr -d '[:space:]')"
    case "$tok" in
      1) mapped+=("antigravity") ;;
      2) mapped+=("claude") ;;
      3) mapped+=("grok") ;;
      4) mapped+=("copilot") ;;
      5) mapped+=("cursor") ;;
      a|A|all|ALL|"*") echo "all"; return ;;
      "") ;;
      *) mapped+=("$tok") ;;
    esac
  done
  if [[ ${#mapped[@]} -eq 0 ]]; then
    echo "antigravity"
  else
    local IFS=','
    echo "${mapped[*]}"
  fi
}

if [[ -z "$HOSTS_ARG" && "$EXPLICIT_OR_DETECTED" == "false" && "$NON_INTERACTIVE" == false && "$DRY" == false ]]; then
  echo ""
  echo -e "${BOLD}Select AI host(s) to configure (comma-separated for multi-AI):${NC}"
  echo "  1) Antigravity / Gemini (.agents/)"
  echo "  2) Claude Code (.claude/)"
  echo "  3) Grok Build (.grok/)"
  echo "  4) GitHub Copilot / VS Code (.github/)"
  echo "  5) Cursor (.cursor/)"
  echo "  a) All supported AI hosts"
  read -r -p "Select AI host(s) [default: 1]: " host_choice
  record_hosts_arg "$(map_interactive_hosts "$host_choice")"
  if [[ ",$(printf '%s' "$host_choice" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')," == *",vscode,"* ]]; then
    VSCODE_ALIAS_USED=true
  fi
  DETECT_FLAGS=(--toolkit-root "$TOOLKIT_ROOT" --target "$TARGET" --hosts "$HOSTS_ARG" --detect-only --json)
  [[ "$NO_AUTO_DETECT" == true ]] && DETECT_FLAGS+=(--no-auto-detect)
  [[ "$FORCE_AUTO_DETECT" == true ]] && DETECT_FLAGS+=(--auto-detect)
  if ! DETECT_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${DETECT_FLAGS[@]}"); then
    echo -e "${RED}Error: Invalid AI host selection '$host_choice'.${NC}" >&2
    exit 1
  fi
fi

ACTIVE_HOSTS_CSV=$("$PYTHON" -c "import json,sys; print(','.join(json.loads(sys.argv[1])['hosts']))" "$DETECT_JSON")
EFFECTIVE_AUTO_DETECT=$("$PYTHON" -c "import json,sys; print('true' if json.loads(sys.argv[1]).get('auto_detect_hosts', True) else 'false')" "$DETECT_JSON")

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  Workforces Toolkit Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Source:  ${CYAN}$TOOLKIT_ROOT${NC}"
echo -e "  Target:  ${CYAN}$TARGET${NC}"
echo -e "  Hosts:   ${CYAN}$ACTIVE_HOSTS_CSV${NC}"
echo -e "  Type:    ${CYAN}$REPO_TYPE${NC}"
[[ "$DRY" == true ]] && echo -e "  ${YELLOW}Mode:    DRY RUN — no files will be written${NC}"
echo ""

# ─── Resolve Assets via Team Manifest Resolver ───
RESOLVER_OK=false
RESOLVE_ARGS=(--toolkit-root "$TOOLKIT_ROOT" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --format bash-export)
[[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && RESOLVE_ARGS+=(--no-auto-detect)
[[ -n "$TEAMS_ARG" ]] && RESOLVE_ARGS+=(--teams "$TEAMS_ARG")

if [[ -f "$RESOLVER_SCRIPT" ]]; then
  if RESOLVER_OUTPUT=$("$PYTHON" "$RESOLVER_SCRIPT" "${RESOLVE_ARGS[@]}"); then
    eval "$RESOLVER_OUTPUT"
    RESOLVER_OK=true
  fi
fi
if [[ "$RESOLVER_OK" != true ]]; then
  ALLOWED_AGENTS="wf-project-manager.md wf-scribe.md wf-programmer.md wf-designer.md"
  ALLOWED_RULES="wf-base.md wf-clean-coder.md wf-design-standards.md wf-lean-execution.md wf-mcp-protection.md wf-session-context.md wf-file-integrity.md wf-git-workflow.md"
  ALLOWED_SKILLS="wf-agent-parallelization wf-brand-guidelines wf-clean-coder wf-code-graph wf-codebase-improvement wf-design-anti-patterns wf-doc-generator wf-image-workflow wf-integrity-validator wf-issue-tracker wf-launch-playbook wf-market-validation wf-memory-management wf-persona-management wf-post-code-review wf-pr-review wf-session-context wf-site-setup wf-social-engagement wf-task-tracker wf-ui-ux-design wf-usage-tracker wf-visual-design-fundamentals wf-management wf-canvas wf-github-project-planning wf-hypothesis-tracker wf-plan wf-sync wf-advisor wf-ideate wf-investigate wf-question-formulation wf-update wf-dashboard"
  ALLOWED_WORKFLOWS=""
  ALLOWED_PLUGINS="wf-programming-plugin wf-integrity-plugin"
  ALLOWED_TEAMS="dev design"
  INSTALLED_TEAMS_LIST="dev design"
fi

echo -e "  Installed Teams: ${GREEN}${INSTALLED_TEAMS_LIST:-core}${NC}"
echo ""

# ─── Prune Deactivated Team / Host Assets When Re-Running Setup ───
if [[ -f "$TARGET/workforces/.manifest.json" && -f "$RESOLVER_SCRIPT" ]]; then
  PRUNE_ARGS=(--toolkit-root "$TOOLKIT_ROOT" --target "$TARGET" --hosts "$ACTIVE_HOSTS_CSV" --prune-obsolete)
  [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && PRUNE_ARGS+=(--no-auto-detect)
  [[ -n "$TEAMS_ARG" ]] && PRUNE_ARGS+=(--teams "$TEAMS_ARG")
  [[ "$DRY" == true ]] && PRUNE_ARGS+=(--dry)
  "$PYTHON" "$RESOLVER_SCRIPT" "${PRUNE_ARGS[@]}"
fi

# ─── Compile Assets & Lifecycle Hooks Across Active Hosts ───
echo -e "${BOLD}▸ Compiling host-native assets & lifecycle hooks...${NC}"
COMPILE_ARGS=(
  --toolkit-root "$TOOLKIT_ROOT"
  --target "$TARGET"
  --hosts "$ACTIVE_HOSTS_CSV"
  --repo-type "$REPO_TYPE"
  --save-config
  --json
)
[[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && COMPILE_ARGS+=(--no-auto-detect)
[[ "$FORCE_AUTO_DETECT" == true ]] && COMPILE_ARGS+=(--auto-detect)
[[ -n "$TEAMS_ARG" ]] && COMPILE_ARGS+=(--teams "$TEAMS_ARG")
[[ "$DRY" == true ]] && COMPILE_ARGS+=(--dry)

COMPILE_JSON=$("$PYTHON" "$COMPILER_SCRIPT" "${COMPILE_ARGS[@]}")
COPIED=$("$PYTHON" -c "import json,sys; print(json.loads(sys.argv[1]).get('written', 0))" "$COMPILE_JSON")
TOTAL_MANAGED=$("$PYTHON" -c "import json,sys; print(len(json.loads(sys.argv[1]).get('installed_files', [])))" "$COMPILE_JSON")
SKIPPED=$(( TOTAL_MANAGED >= COPIED ? TOTAL_MANAGED - COPIED : 0 ))

# ─── Setup Workspace folder (workforces/) ───
WORKFORCES_DIR="$TARGET/workforces"
if [[ "$DRY" != true ]]; then
  mkdir -p "$WORKFORCES_DIR" "$WORKFORCES_DIR/goals" "$WORKFORCES_DIR/tmp" "$WORKFORCES_DIR/session-context" \
    "$WORKFORCES_DIR/hypotheses/draft" "$WORKFORCES_DIR/hypotheses/running" \
    "$WORKFORCES_DIR/hypotheses/validated" "$WORKFORCES_DIR/hypotheses/invalidated" "$WORKFORCES_DIR/hypotheses/pivoted"
  touch "$WORKFORCES_DIR/session-context/.gitkeep"
fi

# ─── Ensure workforces/tmp and workforces/session-context in .gitignore ───
GITIGNORE_FILE="$TARGET/.gitignore"
add_gitignore_entry() {
  local entry="$1"
  local label="$2"
  if [[ "$DRY" == true ]]; then
    return
  fi
  if [[ ! -f "$GITIGNORE_FILE" ]]; then
    echo "$entry" > "$GITIGNORE_FILE"
    echo -e "  ${GREEN}CREATED:${NC} .gitignore with '$label'"
  elif ! grep -qs "^/\?${entry//\*/\\*}" "$GITIGNORE_FILE" && ! grep -qs "^/\?workforces/\?$" "$GITIGNORE_FILE"; then
    if [[ -s "$GITIGNORE_FILE" ]] && [[ "$(tail -c 1 "$GITIGNORE_FILE")" != $'\n' ]]; then
      echo "" >> "$GITIGNORE_FILE"
    fi
    echo "$entry" >> "$GITIGNORE_FILE"
    echo -e "  ${GREEN}ADDED:${NC} '$label' to .gitignore"
  fi
}

add_gitignore_entry "workforces/tmp" "workforces/tmp"
add_gitignore_entry "workforces/session-context/*" "workforces/session-context/*"
add_gitignore_entry "!workforces/session-context/.gitkeep" "!workforces/session-context/.gitkeep"
add_gitignore_entry "workforces/memory" "workforces/memory"
add_gitignore_entry ".worktrees" ".worktrees (agent parallelization)"

if [[ "$DRY" != true ]]; then
  if [[ ! -f "$WORKFORCES_DIR/README.md" ]]; then
    capitalized_type="$(tr '[:lower:]' '[:upper:]' <<< ${REPO_TYPE:0:1})${REPO_TYPE:1}"
    cat > "$WORKFORCES_DIR/README.md" << EOF
# ${capitalized_type} Goals & Objectives
Snapshot of workspace goals, objectives, and tracking files.
EOF
    echo -e "  ${GREEN}CREATED:${NC} workforces/README.md"
  fi

  INSTALLED_TEAMS_YAML=""
  for t in $INSTALLED_TEAMS_LIST; do
    INSTALLED_TEAMS_YAML+=$'  - '"$t"$'\n'
  done

  if [[ ! -f "$WORKFORCES_DIR/workrules.md" ]]; then
    cat > "$WORKFORCES_DIR/workrules.md" << EOF
# Work Rules

## Type
- type: ${REPO_TYPE}

## Installed Teams
- installed_teams:
${INSTALLED_TEAMS_YAML:-  []}

## GitHub Settings
# GitHub usernames this workforce tracks for issues/PRs (comma-separated, @me = active user)
- github_usernames: @me

# Repositories to ignore when scanning for issues and PRs
- ignored_repos: []

## AI Preferences
# Provide custom preferences or guidelines for response style (e.g. "keep replies short", "prefer code blocks")
- response_style: standard

## How to Find Work
1. Check GitHub issues assigned to configured usernames
2. Check unassigned issues in project repositories
3. Check workforces/goals/ for active task boards
EOF
    echo -e "  ${GREEN}CREATED:${NC} workforces/workrules.md"
  else
    "$PYTHON" - "$(dirname "$RESOLVER_SCRIPT")" "$TARGET" "$REPO_TYPE" "$INSTALLED_TEAMS_LIST" << 'PYEOF'
import os, re, sys
sys.path.insert(0, sys.argv[1])
import prune_team as pt
target, repo_type, teams_raw = sys.argv[2], sys.argv[3], sys.argv[4]
teams = [t for t in teams_raw.split() if t]
changed = pt.update_workrules(target, teams, dry_run=False)
wr = os.path.join(target, "workforces", "workrules.md")
txt = open(wr, encoding="utf-8").read()
new_txt = re.sub(r"(?m)^-\s*type:\s*\S+", f"- type: {repo_type}", txt)
if new_txt != txt:
    open(wr, "w", encoding="utf-8").write(new_txt)
    changed = True
if changed:
    print("UPDATED")
PYEOF
  fi

  if [[ ! -f "$WORKFORCES_DIR/workstate.md" ]]; then
    if [[ "$SITE_SETUP" == true ]]; then
      cat > "$WORKFORCES_DIR/workstate.md" << EOF
# Work State

## Configuration
| Setting | Value |
|---------|-------|
| GitHub Usernames | @me |
| Ignored Repos | |
| Goals Directory | workforces/goals/ |

## Active Tasks
| # | Task | Priority | Score | Status | Issue | Started | Notes |
|---|------|----------|-------|--------|-------|---------|-------|
| 1 | Complete /wf-site-setup — Design Pilot Product Brief & Multi-Team Handoffs | P0 | RICE: 950 | pending | — | $(date +%Y-%m-%d) | Define site type, tech stack, design concepts, and AI protocols |
EOF
    else
      cat > "$WORKFORCES_DIR/workstate.md" << EOF
# Work State

## Configuration
| Setting | Value |
|---------|-------|
| GitHub Usernames | @me |
| Ignored Repos | |
| Goals Directory | workforces/goals/ |
EOF
    fi
    echo -e "  ${GREEN}CREATED:${NC} workforces/workstate.md"
  fi
fi

# ─── Initialize Site Setup Artifacts if requested ───
if [[ "$SITE_SETUP" == true && "$DRY" != true ]]; then
  DOCS_DIR="$TARGET/docs"
  mkdir -p "$DOCS_DIR"
  if [[ ! -f "$DOCS_DIR/product-brief.md" ]]; then
    cat > "$DOCS_DIR/product-brief.md" << EOF
# Product Brief: [Site / Product Name]

_Status: Draft — Run /wf-site-setup (or invoke @wf-designer / /wf-advisor) to complete this brief._

---

## 1. Project Summary, Core Problem & Pain Points
- **Site Type:** [SaaS / Local Lead Gen / E-commerce / Blog / Portfolio / Web App]
- **Business Model:** [Direct Service / Lead Gen Affiliate / Subscription SaaS / Direct Sales]
- **Core Problem Statement:** [Fundamental breakdown or market gap being solved]
- **Acute Pain Points Breakdown:**
  - **Tier 1 (Critical Blockers):** [Direct revenue loss, compliance risk, or active churn]
  - **Tier 2 (Operational Drag):** [Manual toil, wasted hours, or error risk]
  - **Tier 3 (UX Friction):** [Confusion, drop-off, or support volume]
- **Current Workarounds:** [How users cope today and why existing tools fail]
- **Cost of Inaction:** [Quantified cost if unsolved for 6 months]
- **Target Audience:** [Key customer personas and raw voice verbatims]

## 2. Problem-to-Solution Lineage Matrix
| # | Identified Pain Point | Severity | Current Workaround | Proposed Solution / Feature | Success Metric |
|---|----------------------|----------|-------------------|-----------------------------|----------------|
| P-1 | [e.g. 48hr manual review delay] | P0 | [Manual staff emails] | [Real-time automated Step Function evaluator] | [Review time < 3s, drop-off < 5%] |
| P-2 | [e.g. Complex pricing table hesitation] | P1 | [Support quote requests] | [Interactive ROI calculator] | [Checkout conversion +25%] |

## 3. Creative Concept & Narrative
- **Visual Metaphor & Story:** [Defined via @wf-designer]

- **Inspiration References:** [Awwwards / SiteInspire / Dribbble / Land-book / Landing.love]
- **Design Archetype:** [e.g., Editorial Minimalist, Neo-Brutalist, Dark Luxury, High-Tech Clean]

## 4. Layout Specification
- **Key Regions:** [Header, Hero, Problem/Solution, Feature Grid, Social Proof, Pricing/CTA, Footer]
- **Responsive Architecture:** [Mobile-first breakpoints]

## 5. Visual Style Guide & Tokens
- **Brand Colors:** [Primary, Secondary, Accent, Neutrals]
- **Typography:** [Display / Heading / Body font pairings]
- **Vector Icons:** [Lucide / Heroicons / Phosphor — zero unicode emojis in UI]
- **Tokens File:** \`src/styles/tokens.css\` (or framework styling tokens)

## 6. Content Direction
- **Brand Voice:** [Tone, do's and don'ts]
- **Headlines & Hook:** [Conversion copy script]

## 7. Technical Stack & AI Protocols
- **Framework:** [Next.js / Python FastAPI or Django / Vite / Astro / Plain HTML]
- **Styling:** [Vanilla CSS / CSS Modules / Tailwind]
- **Hosting:** [Cloudflare Pages / AWS Amplify / Google Firebase or Cloud Run / Docker]
- **Database / Backend:** [Supabase / Firebase / SQLite / PostgreSQL / None / Static]
- **Compliance Variant:** [Standard / Lead-Gen FTC Disclosure]
- **AI Protocol Files:** [robots.txt, llms.txt, ai.txt, sitemap, ai-plugin.json]
EOF
    echo -e "  ${GREEN}CREATED:${NC} docs/product-brief.md"
  fi

  if [[ ! -f "$WORKFORCES_DIR/images.json" ]]; then
    cat > "$WORKFORCES_DIR/images.json" << EOF
{
  "brandVariables": {
    "primaryColor": "",
    "primaryHex": "",
    "secondaryColor": "",
    "secondaryHex": "",
    "brandMood": "",
    "visualStyle": "",
    "tone": ""
  },
  "images": []
}
EOF
    echo -e "  ${GREEN}CREATED:${NC} workforces/images.json"
  fi
fi

if [[ "$REPO_TYPE" == "workforce" && "$DRY" != true ]]; then
  mkdir -p "$WORKFORCES_DIR/projects"
  if [[ ! -f "$WORKFORCES_DIR/projects/README.md" ]]; then
    cat > "$WORKFORCES_DIR/projects/README.md" << EOF
## Project States

- 🟢 **Active**: Currently working on
- 🟡 **On Hold**: Paused temporarily
- 🔵 **Planned**: Scheduled but not started
- ✅ **Complete**: Done
- 🔴 **Cancelled**: Stopped
EOF
    echo -e "  ${GREEN}CREATED:${NC} workforces/projects/README.md"
  fi
fi

# ─── Write installed version metadata & multi-host manifest ───
if [[ "$DRY" != true ]]; then
  VERSION_FILE="$WORKFORCES_DIR/.version"
  INSTALLED_HASH="unknown"
  if command -v git &>/dev/null && [[ -d "$TOOLKIT_ROOT/.git" ]]; then
    INSTALLED_HASH=$(git -C "$TOOLKIT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
  fi

  cat > "$VERSION_FILE" << EOF
# Workforces Version Info
repo: https://github.com/wedigcode/workforces
commit: ${INSTALLED_HASH}
date: $(date -u +%Y-%m-%d)
EOF
  echo -e "  ${GREEN}WRITTEN:${NC} workforces/.version (${INSTALLED_HASH})"

  if [[ -f "$RESOLVER_SCRIPT" ]]; then
    SAVE_MF_ARGS=(
      --toolkit-root "$TOOLKIT_ROOT"
      --target "$TARGET"
      --hosts "$ACTIVE_HOSTS_CSV"
      --save-manifest
      --version-hash "${INSTALLED_HASH}"
    )
    [[ "$EFFECTIVE_AUTO_DETECT" == "false" ]] && SAVE_MF_ARGS+=(--no-auto-detect)
    [[ -n "$TEAMS_ARG" ]] && SAVE_MF_ARGS+=(--teams "$TEAMS_ARG")
    "$PYTHON" "$RESOLVER_SCRIPT" "${SAVE_MF_ARGS[@]}" >/dev/null
    echo -e "  ${GREEN}WRITTEN:${NC} workforces/.manifest.json"
  fi
fi

# ─── Root Host Context Doc Generator (per active host) ───
has_active_host() {
  [[ ",$ACTIVE_HOSTS_CSV," == *",$1,"* ]]
}

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

# ─── Summary ───
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}Install Summary${NC}"
if [[ "$DRY" == true ]]; then
  echo -e "  Simulated: ${YELLOW}$COPIED${NC} files to compile"
  echo -e "  Skipped:   $SKIPPED files (already identical)"
  echo -e "  Hosts:     ${CYAN}$ACTIVE_HOSTS_CSV${NC}"
  echo ""
  echo -e "  ${YELLOW}Mode: DRY RUN — no files were created or modified${NC}"
  echo -e "  ${YELLOW}✓ Dry-run completed successfully! Run without --dry to install.${NC}"
else
  echo -e "  Compiled: ${GREEN}$COPIED${NC} files"
  echo -e "  Skipped:  $SKIPPED files (already identical)"
  echo -e "  Hosts:    ${CYAN}$ACTIVE_HOSTS_CSV${NC}"
  echo ""
  echo -e "  ${GREEN}✓ Workforces toolkit installed successfully!${NC}"
fi
if [[ "$SITE_SETUP" == true ]]; then
  echo ""
  echo -e "  ${BOLD}${CYAN}🚀 Site Setup Initialized:${NC}"
  echo -e "     Run ${BOLD}/wf-site-setup${NC} (or invoke ${BOLD}/wf-advisor${NC} / ${BOLD}@wf-designer${NC}) in your AI assistant to:"
  echo -e "     1. Consult with wf-advisor to unpack root problems, pain points & stakes"
  echo -e "     2. Brainstorm creative design concepts & define design tokens"
  echo -e "     3. Select tech stack & cloud hosting"
  echo -e "     4. Complete your Product Brief (${CYAN}docs/product-brief.md${NC})"
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
