#!/usr/bin/env bash
# Workforces Toolkit Updater
# Updates the installed Workforces files in the target project using the latest version.
#
# Usage:
#   bash skills/workforce-management/scripts/update.sh /path/to/project [options]
#
# Options:
#   --dry                  Dry run mode (shows what would change, does not write files)
#   --non-interactive      Run without prompting (ideal for AI assistants)
#   --help, -h             Show this help menu

set -euo pipefail

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

usage() {
  echo -e "${BOLD}Workforces Toolkit Updater${NC}"
  echo ""
  echo "Usage: bash skills/workforce-management/scripts/update.sh <target-project-path> [options]"
  echo ""
  echo "Options:"
  echo "  --dry                  Show what would change without modifying files"
  echo "  --force                Force re-sync of all toolkit files regardless of version hash"
  echo "  --non-interactive      Run without prompting"
  echo ""
  exit 1
}

# Parse args
if [[ $# -lt 1 ]]; then
  usage
fi

TARGET="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry)
      DRY=true
      ;;
    --force)
      FORCE=true
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
VERSION_FILE="$TARGET/workforces/.version"
WORKFORCES_REPO="https://github.com/wedigcode/workforces.git"
TMP_DIR="$TARGET/.agents/.tmp-update-$$"
trap 'rm -rf "$TMP_DIR"' EXIT

# Detect installed version
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

# Find source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# If running from a git checkout of the workforces repo, we can use that local checkout as the source.
# Otherwise, we clone the remote repo.
if [[ -d "$TOOLKIT_ROOT/.git" && -d "$TOOLKIT_ROOT/skills" ]]; then
  echo -e "${BOLD}▸ Using local repo as source...${NC}"
  SOURCE_DIR="$TOOLKIT_ROOT"
  LATEST_HASH=$(git -C "$TOOLKIT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
else
  echo -e "${BOLD}▸ Fetching latest workforces from remote...${NC}"
  git clone --depth=1 "$WORKFORCES_REPO" "$TMP_DIR" 2>/dev/null || true
  SOURCE_DIR="$TMP_DIR"
  LATEST_HASH=$(git -C "$TMP_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
fi

echo -e "  Latest:    ${LATEST_HASH}"

# Detect base config directory
if [[ -d "$TARGET/.agents" ]]; then
  BASE_DIR=".agents"
elif [[ -d "$TARGET/.github/copilot" ]]; then
  BASE_DIR=".github/copilot"
elif [[ -d "$TARGET/.claude" ]]; then
  BASE_DIR=".claude"
else
  BASE_DIR=".agents"
fi

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

remove_gitignore_entry() {
  local entry="$1"
  local label="$2"
  if [[ -f "$GITIGNORE_FILE" ]] && grep -qs "${entry}" "$GITIGNORE_FILE"; then
    if [[ "$DRY" == true ]]; then
      echo -e "  ${YELLOW}WOULD REMOVE:${NC} '$label' from .gitignore"
    else
      python3 -c "import sys; path, target = sys.argv[1], sys.argv[2]; lines = [l for l in open(path).read().splitlines() if target not in l]; open(path, 'w').write('\n'.join(lines) + ('\n' if lines else ''))" "$GITIGNORE_FILE" "$entry"
      echo -e "  ${GREEN}REMOVED:${NC} '$label' from .gitignore"
    fi
  fi
}

add_update_gitignore_entry "workforces/tmp" "workforces/tmp"
add_update_gitignore_entry "workforces/session-context/*" "workforces/session-context/*"
add_update_gitignore_entry "!workforces/session-context/.gitkeep" "!workforces/session-context/.gitkeep"

if [[ "$DRY" != true ]]; then
  mkdir -p "$TARGET/workforces/tmp" "$TARGET/workforces/session-context"
  touch "$TARGET/workforces/session-context/.gitkeep"
fi

MISSING_CORE_DIRS=false
for d in plugins agents workflows rules skills teams; do
  if [[ -d "$SOURCE_DIR/$d" && ! -d "$TARGET/$BASE_DIR/$d" ]]; then
    MISSING_CORE_DIRS=true
    break
  fi
done

if [[ "$FORCE" == false && "$INSTALLED_HASH" == "$LATEST_HASH" && "$INSTALLED_HASH" != "unknown" && "$MISSING_CORE_DIRS" == false ]]; then
  NEW_TEAMS_AVAILABLE=()
  if [[ -d "$SOURCE_DIR/teams" ]]; then
    for stdir in "$SOURCE_DIR/teams"/*; do
      [[ -d "$stdir" && ( -f "$stdir/pack.md" || -f "$stdir/team.json" ) ]] || continue
      team_id=$(basename "$stdir")
      if [[ ! -d "$TARGET/workforces/teams/$team_id" ]]; then
        NEW_TEAMS_AVAILABLE+=("$team_id")
      fi
    done
  fi

  echo ""
  echo -e "  ${GREEN}✓ Core toolkit already up to date (${INSTALLED_HASH})${NC}"
  if [[ ${#NEW_TEAMS_AVAILABLE[@]} -gt 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}💡 New Team Packs available in upstream workforces:${NC}"
    for nt in "${NEW_TEAMS_AVAILABLE[@]}"; do
      echo -e "     - ${CYAN}$nt${NC}"
    done
    echo -e "     Run: bash .agents/skills/workforce-management/scripts/setup.sh ./ --teams ${NEW_TEAMS_AVAILABLE[0]} to install."
  fi
  echo ""
  exit 0
fi

echo -e "${BOLD}▸ Updating toolkit layer ($BASE_DIR/)${NC}"

COPIED=0
SKIPPED=0

copy_file() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ ! -f "$src" ]]; then
    return
  fi

  if [[ "$DRY" == true ]]; then
    if [[ -f "$dest" ]]; then
      if ! cmp -s "$src" "$dest"; then
        echo -e "  ${YELLOW}WOULD UPDATE:${NC} $label"
        (( COPIED++ )) || true
      fi
    else
      echo -e "  ${GREEN}WOULD CREATE:${NC} $label"
      (( COPIED++ )) || true
    fi
    return
  fi

  mkdir -p "$(dirname "$dest")"
  if [[ -f "$dest" ]] && cmp -s "$src" "$dest"; then
    (( SKIPPED++ )) || true
  else
    cp "$src" "$dest"
    echo -e "  ${GREEN}UPDATED:${NC} $label"
    (( COPIED++ )) || true
  fi
}

# ─── Copy Agents ───
AGENTS_SRC=""
if [[ -d "$SOURCE_DIR/agents" ]]; then
  AGENTS_SRC="$SOURCE_DIR/agents"
elif [[ -d "$SOURCE_DIR/.agents/agents" ]]; then
  AGENTS_SRC="$SOURCE_DIR/.agents/agents"
fi

if [[ -n "$AGENTS_SRC" ]]; then
  for f in "$AGENTS_SRC"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    copy_file "$f" "$TARGET/$BASE_DIR/agents/$basename" "$BASE_DIR/agents/$basename"
  done
fi

# ─── Copy Workflows ───
if [[ -d "$SOURCE_DIR/workflows" ]]; then
  for f in "$SOURCE_DIR/workflows"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    copy_file "$f" "$TARGET/$BASE_DIR/workflows/$basename" "$BASE_DIR/workflows/$basename"
  done
fi

# ─── Copy Rules ───
if [[ -d "$SOURCE_DIR/rules" ]]; then
  for f in "$SOURCE_DIR/rules"/*.md; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    copy_file "$f" "$TARGET/$BASE_DIR/rules/$basename" "$BASE_DIR/rules/$basename"
  done
fi

# ─── Copy Skills ───
if [[ -d "$SOURCE_DIR/skills" ]]; then
  for skill_dir in "$SOURCE_DIR/skills"/*; do
    [[ -d "$skill_dir" ]] || continue
    skill_name=$(basename "$skill_dir")
    
    mkdir -p "$TARGET/$BASE_DIR/skills/$skill_name"
    while read -r f; do
      [[ -n "$f" ]] || continue
      rel_path="${f#$skill_dir/}"
      copy_file "$f" "$TARGET/$BASE_DIR/skills/$skill_name/$rel_path" "$BASE_DIR/skills/$skill_name/$rel_path"
    done < <(find "$skill_dir" -type f)
  done
fi

# ─── Copy Plugins ───
if [[ -d "$SOURCE_DIR/plugins" ]]; then
  echo -e "${BOLD}▸ Copying Plugins...${NC}"
  for plugin_dir in "$SOURCE_DIR/plugins"/*; do
    [[ -d "$plugin_dir" ]] || continue
    plugin_name=$(basename "$plugin_dir")
    
    mkdir -p "$TARGET/$BASE_DIR/plugins/$plugin_name"
    while read -r f; do
      [[ -n "$f" ]] || continue
      rel_path="${f#$plugin_dir/}"
      copy_file "$f" "$TARGET/$BASE_DIR/plugins/$plugin_name/$rel_path" "$BASE_DIR/plugins/$plugin_name/$rel_path"
    done < <(find "$plugin_dir" -type f)
  done
fi

# ─── Sync Upstream Team Pack Building Blocks & Discover New Building Blocks ───
NEW_TEAMS_AVAILABLE=()

if [[ -d "$SOURCE_DIR/teams" ]]; then
  echo -e "${BOLD}▸ Syncing Upstream Team Pack Building Blocks...${NC}"
  for stdir in "$SOURCE_DIR/teams"/*; do
    [[ -d "$stdir" ]] || continue
    team_name=$(basename "$stdir")
    
    if [[ ! -d "$TARGET/workforces/teams/$team_name" ]]; then
      NEW_TEAMS_AVAILABLE+=("$team_name")
    fi

    mkdir -p "$TARGET/$BASE_DIR/teams/$team_name"
    while read -r f; do
      [[ -n "$f" ]] || continue
      rel="${f#$stdir/}"
      copy_file "$f" "$TARGET/$BASE_DIR/teams/$team_name/$rel" "$BASE_DIR/teams/$team_name/$rel"
    done < <(find "$stdir" -type f)
  done
fi

# ─── Write version hash ───
if [[ "$DRY" != true ]]; then
  cat > "$VERSION_FILE" << EOF
# Workforces Version Info
repo: $WORKFORCES_REPO
commit: $LATEST_HASH
date: $(date -u +%Y-%m-%d)
EOF
  echo -e "  ${GREEN}WRITTEN:${NC} workforces/.version ($LATEST_HASH)"
fi

echo ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$DRY" == true ]]; then
  echo -e "  ${YELLOW}Dry run complete — no files were modified.${NC}"
else
  echo -e "  ${BOLD}Update Summary:${NC}"
  echo -e "  Updated:  ${GREEN}$COPIED${NC} files"
  echo -e "  Skipped:  $SKIPPED files (already identical)"
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
