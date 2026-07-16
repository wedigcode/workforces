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
BOLD='\033[1m'
NC='\033[0m'

TARGET=""
DRY=false
NON_INTERACTIVE=false

usage() {
  echo -e "${BOLD}Workforces Toolkit Updater${NC}"
  echo ""
  echo "Usage: bash skills/workforce-management/scripts/update.sh <target-project-path> [options]"
  echo ""
  echo "Options:"
  echo "  --dry                  Show what would change without modifying files"
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
TMP_DIR="/tmp/workforces-update-$$"
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
if [[ -d "$TOOLKIT_ROOT/.git" ]]; then
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

if [[ "$INSTALLED_HASH" == "$LATEST_HASH" && "$INSTALLED_HASH" != "unknown" ]]; then
  echo ""
  echo -e "  ${GREEN}✓ Already up to date${NC}"
  echo ""
  exit 0
fi

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
if [[ -d "$SOURCE_DIR/agents" ]]; then
  for f in "$SOURCE_DIR/agents"/*.md; do
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
  echo ""
  echo -e "  ${GREEN}✓ Toolkit updated to $LATEST_HASH${NC}"
fi
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
