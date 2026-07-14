#!/usr/bin/env bash
# Deploy M2TW Complete Edition from this repo into the Steam Medieval II game folder.
# Validators run first and gate the deploy.
# Usage: ./deploy.sh [--dry-run]
set -euo pipefail

GAME="/mnt/c/Program Files (x86)/Steam/steamapps/common/Medieval II Total War"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

if [ ! -d "$GAME" ]; then
  echo "ERROR: game folder not found: $GAME" >&2
  exit 1
fi

echo "== validators =="
python3 "$REPO/tools/validate_faction_order.py"
python3 "$REPO/tools/validate_strat.py"

run() {
  echo "  $*"
  if [ "$DRY" -eq 0 ]; then
    "$@"
  fi
}

echo "Repo : $REPO"
echo "Game : $GAME"
[ "$DRY" -eq 1 ] && echo "(dry-run — nothing will be written)"

echo "[1/3] mod folder  -> mods/complete_edition"
run mkdir -p "$GAME/mods/complete_edition"
run cp -r "$REPO/mod/complete_edition/data" "$GAME/mods/complete_edition/"
# the engine caches the campaign map in map.rwm; a stale cache after
# descr_regions/descr_strat changes causes wrong region binding
run rm -f "$GAME/mods/complete_edition/data/world/maps/base/map.rwm"
# retired asset locations from earlier rounds (cp -r does not delete)
run rm -rf "$GAME/mods/complete_edition/data/ui/symbols" \
           "$GAME/mods/complete_edition/data/ui/rebel_symbols" \
           "$GAME/mods/complete_edition/data/ui/loading_screen"

echo "[2/3] mod cfg     -> mods/complete_edition/complete_edition.cfg"
run cp "$REPO/launcher/complete_edition.cfg" "$GAME/mods/complete_edition/"

echo "[3/3] launcher    -> game root"
run cp "$REPO/launcher/complete_edition.bat" "$GAME/"

echo "Done. Run complete_edition.bat in the game folder (requires M2EX installed)."
