#!/usr/bin/env bash
# Workforces Setup Script
# Copies agents, workflows, skills, and rules from the source toolkit into a target project.
#
# Usage:
#   bash skills/workforce-management/scripts/setup.sh /path/to/project [options]
#
# Options:
#   --type <type>          Repo type: workforce or project
#   --editor <type>        Editor type: antigravity, vscode, claude, grok, auto (default: auto)
#   --teams <team-list>    Comma-separated list of teams to install (e.g., brand-marketing,sales-outreach, all, none)
#   --non-interactive      Run without prompting the user for any inputs (ideal for AI assistants)
#   --help, -h             Show this help menu

set -euo pipefail

# python3 is the usual name; Windows (including Grok Build) often only has `python`.
# Ignore the Microsoft Store stub that prints "Python was not found".
PYTHON=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
    PYTHON="$cand"
    break
  fi
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Find source toolkit directory (the parent of skills/workforce-management/scripts/setup.sh)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TARGET=""
REPO_TYPE=""
EDITOR_TYPE=""
TEAMS_ARG=""
SITE_SETUP=""
NON_INTERACTIVE=false

usage() {
  echo -e "${BOLD}Workforces Setup${NC}"
  echo ""
  echo "Usage: bash skills/workforce-management/scripts/setup.sh <target-project-path> [options]"
  echo ""
  echo "Options:"
  echo "  --type <type>          Repo type: workforce or project"
  echo "  --editor <type>        Editor type: antigravity, vscode, claude, grok, auto (default: auto)"
  echo "  --teams <team-list>    Teams to install (e.g. 'brand-marketing,sales-outreach', 'all', 'none')"
  echo "  --site-setup           Initialize Site Setup & Product Brief starter (for greenfield sites)"
  echo "  --skip-site-setup      Skip Site Setup initialization"
  echo "  --non-interactive      Do not prompt for any options (fails on invalid configuration)"
  echo ""
  exit 0
}


# Parse args
if [[ $# -lt 1 ]]; then
  usage
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
fi

TARGET="$1"
shift


while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)
      shift
      REPO_TYPE="$1"
      ;;
    --editor)
      shift
      EDITOR_TYPE="$1"
      ;;
    --teams)
      shift
      TEAMS_ARG="$1"
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
      usage
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      usage
      ;;
  esac
  shift
done

# Validate target
if [[ ! -d "$TARGET" ]]; then
  echo -e "${RED}Error: Target directory does not exist: $TARGET${NC}"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"

# Detect if target workspace is empty / greenfield
IS_EMPTY_WORKSPACE=false
NON_DOT_COUNT=$(find "$TARGET" -maxdepth 1 -not -name ".*" | grep -v "^$TARGET$" | wc -l || true)
if [[ "$NON_DOT_COUNT" -eq 0 ]]; then
  IS_EMPTY_WORKSPACE=true
fi

# ─── Site Setup Prompt for Empty Repos ───
if [[ -z "$SITE_SETUP" ]]; then
  if [[ "$IS_EMPTY_WORKSPACE" == true ]]; then
    if [[ "$NON_INTERACTIVE" == true ]]; then
      SITE_SETUP=true
    else
      echo ""
      echo -e "${BOLD}${CYAN}🚀 Empty project workspace detected!${NC}"
      echo "Would you like to initialize a Site Setup & Product Brief (Design Pilot)?"
      read -p "Enable site setup? (y/n) [default: y]: " site_choice
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
  if [[ "$NON_INTERACTIVE" == true ]]; then
    echo -e "${YELLOW}Non-interactive mode: Defaulting repo type to 'project'${NC}"
    REPO_TYPE="project"
  else
    echo ""
    echo -e "${BOLD}Select repository type:${NC}"
    echo "  1) Workforce (Central command, plans and delegates to other projects)"
    echo "  2) Project (Specific codebase/initiative with its own issue tracking)"
    read -p "Select type (1/2): " repo_choice
    case "$repo_choice" in
      1|w|workforce|W|Workforce) REPO_TYPE="workforce" ;;
      2|p|project|P|Project)     REPO_TYPE="project" ;;
      *) echo -e "${RED}Invalid choice. Defaulting to project.${NC}"; REPO_TYPE="project" ;;
    esac
  fi
fi

if [[ "$REPO_TYPE" != "workforce" && "$REPO_TYPE" != "project" ]]; then
  echo -e "${RED}Error: Invalid repo type '$REPO_TYPE'. Must be 'workforce' or 'project'.${NC}"
  exit 1
fi

# ─── Editor Detection ───
detect_editor() {
  if [[ -n "$EDITOR_TYPE" && "$EDITOR_TYPE" != "auto" ]]; then
    echo "$EDITOR_TYPE"
    return
  fi

  # Auto-detection
  if [[ -d "$TARGET/.gemini" || -f "$TARGET/GEMINI.md" || -d "$TARGET/.agents" ]]; then
    echo "antigravity"
    return
  fi

  if [[ -f "$TARGET/CLAUDE.md" || -d "$TARGET/.claude" ]]; then
    echo "claude"
    return
  fi

  if [[ -d "$TARGET/.vscode" || -d "$TARGET/.github/copilot" ]]; then
    echo "vscode"
    return
  fi

  # Only treat an existing .grok/ toolkit folder as a Grok host.
  # Do not key off AGENTS.md — many Grok projects have that file without Workforces.
  if [[ -d "$TARGET/.grok/skills" || -d "$TARGET/.grok/commands" || -d "$TARGET/.grok/agents" ]]; then
    echo "grok"
    return
  fi

  # Default to antigravity
  echo "antigravity"
}

DETECTED_EDITOR=$(detect_editor)

get_base_dir() {
  case "$DETECTED_EDITOR" in
    antigravity) echo ".agents" ;;
    vscode)      echo ".github/copilot" ;;
    claude)      echo ".claude" ;;
    grok)        echo ".grok" ;;
    *)           echo ".agents" ;;
  esac
}

BASE_DIR=$(get_base_dir)
AGENTS_DIR="$TARGET/$BASE_DIR/agents"
# Grok Build discovers slash-command markdown under commands/, not workflows/.
if [[ "$DETECTED_EDITOR" == "grok" ]]; then
  WORKFLOWS_DIR="$TARGET/$BASE_DIR/commands"
else
  WORKFLOWS_DIR="$TARGET/$BASE_DIR/workflows"
fi
SKILLS_DIR="$TARGET/$BASE_DIR/skills"
RULES_DIR="$TARGET/$BASE_DIR/rules"
PLUGINS_DIR="$TARGET/$BASE_DIR/plugins"

# Grok already owns /plan (plan mode) and /context (token meter).
workflow_dest_name() {
  local basename="$1"
  if [[ "$DETECTED_EDITOR" == "grok" ]]; then
    case "$basename" in
      plan.md)    echo "wf-plan.md" ;;
      context.md) echo "wf-context.md" ;;
      *)          echo "$basename" ;;
    esac
  else
    echo "$basename"
  fi
}

workflow_rel_dir() {
  if [[ "$DETECTED_EDITOR" == "grok" ]]; then
    echo "commands"
  else
    echo "workflows"
  fi
}

# ─── Counters ───
COPIED=0
SKIPPED=0

copy_file() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ ! -f "$src" ]]; then
    return
  fi

  mkdir -p "$(dirname "$dest")"

  if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then
    SKIPPED=$((SKIPPED + 1))
  else
    cp "$src" "$dest"
    echo -e "  ${GREEN}COPIED:${NC} $label"
    COPIED=$((COPIED + 1))
  fi
}

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  Workforces Toolkit Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Source:  ${CYAN}$TOOLKIT_ROOT${NC}"
echo -e "  Target:  ${CYAN}$TARGET${NC}"
echo -e "  Editor:  ${CYAN}$DETECTED_EDITOR ($BASE_DIR/)${NC}"
echo -e "  Type:    ${CYAN}$REPO_TYPE${NC}"
echo ""

# ─── Resolve Assets via Team Manifest Resolver ───
RESOLVER_SCRIPT="$TOOLKIT_ROOT/skills/workforce-management/scripts/resolve_manifest.py"
RESOLVER_OK=false
if [[ -f "$RESOLVER_SCRIPT" && -n "$PYTHON" ]]; then
  if RESOLVER_OUTPUT=$("$PYTHON" "$RESOLVER_SCRIPT" --toolkit-root "$TOOLKIT_ROOT" --target "$TARGET" ${TEAMS_ARG:+--teams "$TEAMS_ARG"} --format bash-export); then
    eval "$RESOLVER_OUTPUT"
    RESOLVER_OK=true
  fi
fi
if [[ "$RESOLVER_OK" != true ]]; then
  # Fallback if resolver script, python, or the resolver run is unavailable
  ALLOWED_AGENTS="advisor.md project-manager.md scribe.md programmer.md designer.md"
  ALLOWED_RULES="base.md clean-coder.md design-standards.md mcp-protection.md session-context.md"
  ALLOWED_SKILLS="brand-guidelines clean-coder code-graph codebase-improvement design-anti-patterns doc-generator image-workflow issue-tracker jules-integration memory-management post-code-review pr-review session-context ui-ux-design usage-tracker visual-design-fundamentals workforce-management"
  ALLOWED_WORKFLOWS="advisor.md brand-context.md clean.md improve.md investigate.md plan.md question-formulation.md site-setup.md sync.md task.md teams.md update-workforces.md verify-integrity.md work.md"
  ALLOWED_PLUGINS="workforce-programming-plugin workforce-usage-plugin"
  ALLOWED_TEAMS="dev design"
  INSTALLED_TEAMS_LIST="dev design"
fi

echo -e "  Installed Teams: ${GREEN}${INSTALLED_TEAMS_LIST:-core}${NC}"
echo ""

# Create directories
mkdir -p "$AGENTS_DIR" "$WORKFLOWS_DIR" "$SKILLS_DIR" "$RULES_DIR"

# ─── Copy Allowed Agents ───
AGENTS_SRC=""
if [[ -d "$TOOLKIT_ROOT/agents" ]]; then
  AGENTS_SRC="$TOOLKIT_ROOT/agents"
elif [[ -d "$TOOLKIT_ROOT/.agents/agents" ]]; then
  AGENTS_SRC="$TOOLKIT_ROOT/.agents/agents"
fi

if [[ -n "$AGENTS_SRC" ]]; then
  echo -e "${BOLD}▸ Copying Agents...${NC}"
  for f in "$AGENTS_SRC"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    if [[ " $ALLOWED_AGENTS " =~ " $basename " ]]; then
      copy_file "$f" "$AGENTS_DIR/$basename" "$BASE_DIR/agents/$basename"
    fi
  done
fi

# ─── Copy Allowed Workflows ───
if [[ -d "$TOOLKIT_ROOT/workflows" ]]; then
  echo -e "${BOLD}▸ Copying Workflows...${NC}"
  for f in "$TOOLKIT_ROOT/workflows"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    if [[ " $ALLOWED_WORKFLOWS " =~ " $basename " ]]; then
      dest_name=$(workflow_dest_name "$basename")
      rel_dir=$(workflow_rel_dir)
      copy_file "$f" "$WORKFLOWS_DIR/$dest_name" "$BASE_DIR/$rel_dir/$dest_name"
    fi
  done
fi

# ─── Copy Allowed Rules ───
if [[ -d "$TOOLKIT_ROOT/rules" ]]; then
  echo -e "${BOLD}▸ Copying Rules...${NC}"
  for f in "$TOOLKIT_ROOT/rules"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    if [[ " $ALLOWED_RULES " =~ " $basename " ]]; then
      copy_file "$f" "$RULES_DIR/$basename" "$BASE_DIR/rules/$basename"
    fi
  done
fi

# ─── Copy Allowed Skills ───
if [[ -d "$TOOLKIT_ROOT/skills" ]]; then
  echo -e "${BOLD}▸ Copying Skills...${NC}"
  for skill_dir in "$TOOLKIT_ROOT/skills"/*; do
    [[ -d "$skill_dir" ]] || continue
    skill_name=$(basename "$skill_dir")
    if [[ " $ALLOWED_SKILLS " =~ " $skill_name " ]]; then
      mkdir -p "$SKILLS_DIR/$skill_name"
      while read -r f; do
        [[ -n "$f" ]] || continue
        rel_path="${f#$skill_dir/}"
        copy_file "$f" "$SKILLS_DIR/$skill_name/$rel_path" "$BASE_DIR/skills/$skill_name/$rel_path"
      done < <(find "$skill_dir" -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -not -name ".DS_Store")
    fi
  done
fi

# ─── Copy Allowed Plugins ───
if [[ -d "$TOOLKIT_ROOT/plugins" ]]; then
  echo -e "${BOLD}▸ Copying Plugins...${NC}"
  for plugin_dir in "$TOOLKIT_ROOT/plugins"/*; do
    [[ -d "$plugin_dir" ]] || continue
    plugin_name=$(basename "$plugin_dir")
    if [[ " $ALLOWED_PLUGINS " =~ " $plugin_name " ]]; then
      mkdir -p "$PLUGINS_DIR/$plugin_name"
      while read -r f; do
        [[ -n "$f" ]] || continue
        rel_path="${f#$plugin_dir/}"
        copy_file "$f" "$PLUGINS_DIR/$plugin_name/$rel_path" "$BASE_DIR/plugins/$plugin_name/$rel_path"
      done < <(find "$plugin_dir" -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -not -name ".DS_Store")
    fi
  done
fi

# ─── Copy Installed Team Pack Building Blocks ───
if [[ -d "$TOOLKIT_ROOT/teams" ]]; then
  echo -e "${BOLD}▸ Copying Installed Team Packs...${NC}"
  for team_dir in "$TOOLKIT_ROOT/teams"/*; do
    [[ -d "$team_dir" ]] || continue
    team_name=$(basename "$team_dir")
    if [[ " $ALLOWED_TEAMS " =~ " $team_name " ]]; then
      mkdir -p "$TARGET/$BASE_DIR/teams/$team_name"
      while read -r f; do
        [[ -n "$f" ]] || continue
        rel="${f#$team_dir/}"
        copy_file "$f" "$TARGET/$BASE_DIR/teams/$team_name/$rel" "$BASE_DIR/teams/$team_name/$rel"
      done < <(find "$team_dir" -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -not -name ".DS_Store")
    fi
  done
fi


# ─── Setup Workspace folder (workforces/) ───
WORKFORCES_DIR="$TARGET/workforces"
mkdir -p "$WORKFORCES_DIR" "$WORKFORCES_DIR/goals" "$WORKFORCES_DIR/tmp" "$WORKFORCES_DIR/session-context" \
  "$WORKFORCES_DIR/hypotheses/draft" "$WORKFORCES_DIR/hypotheses/running" \
  "$WORKFORCES_DIR/hypotheses/validated" "$WORKFORCES_DIR/hypotheses/invalidated" "$WORKFORCES_DIR/hypotheses/pivoted"
touch "$WORKFORCES_DIR/session-context/.gitkeep"

# ─── Ensure workforces/tmp and workforces/session-context in .gitignore ───
GITIGNORE_FILE="$TARGET/.gitignore"
add_gitignore_entry() {
  local entry="$1"
  local label="$2"
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

# Seed workforce.md if not already present
if [[ ! -f "$WORKFORCES_DIR/README.md" ]]; then
  capitalized_type="$(tr '[:lower:]' '[:upper:]' <<< ${REPO_TYPE:0:1})${REPO_TYPE:1}"
  cat > "$WORKFORCES_DIR/README.md" << EOF
# ${capitalized_type} Goals & Objectives
Snapshot of workspace goals, objectives, and tracking files.
EOF
  echo -e "  ${GREEN}CREATED:${NC} workforces/README.md"
fi

# Format installed teams YAML
INSTALLED_TEAMS_YAML=""
for t in $INSTALLED_TEAMS_LIST; do
  INSTALLED_TEAMS_YAML+=$'  - '"$t"$'\n'
done

# Seed workrules.md if not already present
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
fi

# Seed workstate.md if not already present
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
| 1 | Complete /site-setup — Design Pilot Product Brief & Multi-Team Handoffs | P0 | RICE: 950 | pending | — | $(date +%Y-%m-%d) | Define site type, tech stack, design concepts, and AI protocols |
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

# ─── Initialize Site Setup Artifacts if requested ───
if [[ "$SITE_SETUP" == true ]]; then
  DOCS_DIR="$TARGET/docs"
  mkdir -p "$DOCS_DIR"
  if [[ ! -f "$DOCS_DIR/product-brief.md" ]]; then
    cat > "$DOCS_DIR/product-brief.md" << EOF
# Product Brief: [Site / Product Name]

_Status: Draft — Run /site-setup (or invoke @advisor / @designer) to complete this brief._

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
- **Visual Metaphor & Story:** [Defined via @designer]

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


# Setup project specific structure
if [[ "$REPO_TYPE" == "workforce" ]]; then
  # Workforce command repo tracks child projects
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

# ─── Write installed version metadata ───
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

# ─── Editor Config Generator ───
case "$DETECTED_EDITOR" in
  antigravity)
    if [[ ! -f "$TARGET/GEMINI.md" ]]; then
      cat > "$TARGET/GEMINI.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit.

## Toolkit Structures
- Config & Personas: \`.agents/\`
- User Workspace & State: \`workforces/\`

## Instructions
Refer to \`.agents/rules/base.md\` and run workflows under \`.agents/workflows/\` to perform tasks.
EOF
      echo -e "  ${GREEN}CREATED:${NC} GEMINI.md"
    fi
    ;;
  vscode)
    mkdir -p "$TARGET/.vscode"
    if [[ ! -f "$TARGET/.vscode/settings.json" ]]; then
      cat > "$TARGET/.vscode/settings.json" << EOF
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".github/copilot/instructions.md" }
  ]
}
EOF
      echo -e "  ${GREEN}CREATED:${NC} .vscode/settings.json"
    fi
    if [[ ! -f "$TARGET/.github/copilot/instructions.md" ]]; then
      mkdir -p "$TARGET/.github/copilot"
      cat > "$TARGET/.github/copilot/instructions.md" << EOF
# VS Code Copilot Instructions

This project utilizes the Workforces AI toolkit. Please refer to rules in \`.github/copilot/rules/base.md\` and use workflows inside \`.github/copilot/workflows/\`.
EOF
      echo -e "  ${GREEN}CREATED:${NC} .github/copilot/instructions.md"
    fi
    ;;
  claude)
    if [[ ! -f "$TARGET/CLAUDE.md" ]]; then
      cat > "$TARGET/CLAUDE.md" << EOF
# Claude Code Instructions

This project utilizes the Workforces AI toolkit. Please refer to rules in \`.claude/rules/base.md\` and use workflows inside \`.claude/workflows/\`.
EOF
      echo -e "  ${GREEN}CREATED:${NC} CLAUDE.md"
    fi
    ;;
  grok)
    if [[ ! -f "$TARGET/AGENTS.md" ]]; then
      cat > "$TARGET/AGENTS.md" << EOF
# Project Context

This project uses the [workforces](https://github.com/wedigcode/workforces) AI toolkit, installed for Grok Build.

## Toolkit Structures
- Config, personas, skills, slash commands: \`.grok/\`
- User workspace and state: \`workforces/\`

## Instructions
Refer to \`.grok/rules/base.md\` and run slash commands from \`.grok/commands/\`.
Workforces \`/plan\` is \`/wf-plan\`. Workforces \`/context\` is \`/wf-context\`.
See \`docs/grok.md\` in the Workforces repo for host mapping (tool names, python vs python3).
EOF
      echo -e "  ${GREEN}CREATED:${NC} AGENTS.md"
    fi
    ;;
esac

# ─── Summary ───
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}Install Summary${NC}"
echo -e "  Copied:  ${GREEN}$COPIED${NC} files"
echo -e "  Skipped: $SKIPPED files (already identical)"
echo -e "  Editor:  ${CYAN}$DETECTED_EDITOR${NC}"
echo ""
echo -e "  ${GREEN}✓ Workforces toolkit installed successfully!${NC}"
if [[ "$SITE_SETUP" == true ]]; then
  echo ""
  echo -e "  ${BOLD}${CYAN}🚀 Site Setup Initialized:${NC}"
  echo -e "     Run ${BOLD}/site-setup${NC} (or invoke ${BOLD}@advisor${NC} / ${BOLD}@designer${NC}) in your AI assistant to:"

  echo -e "     1. Consult with @advisor to unpack root problems, pain points & stakes"
  echo -e "     2. Brainstorm creative design concepts & define design tokens"
  echo -e "     3. Select tech stack & cloud hosting"
  echo -e "     4. Complete your Product Brief (${CYAN}docs/product-brief.md${NC})"
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

