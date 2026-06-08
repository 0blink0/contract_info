#!/usr/bin/env bash
set -euo pipefail

PLATFORM=""
VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PLATFORM" || -z "$VERSION" ]]; then
  echo "Usage: bash scripts/package_backend.sh --platform <platform> --version <version>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT/dist/ctrx-backend"
RES_DIR="$ROOT/electron/resources"
MANIFEST="$RES_DIR/.backend-manifest.json"
TARGET_NAME="ctrx-backend-${PLATFORM}-v${VERSION}"
TARGET_DIR="$RES_DIR/$TARGET_NAME"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found in PATH" >&2
  exit 1
fi

pyinstaller "$ROOT/ctrx_backend.spec" --noconfirm --clean --log-level WARN

if [[ ! -d "$DIST_DIR" ]]; then
  echo "Expected pyinstaller output not found: $DIST_DIR" >&2
  exit 1
fi

mkdir -p "$RES_DIR"
rm -rf "$TARGET_DIR"
cp -R "$DIST_DIR" "$TARGET_DIR"

python - <<'PY' "$MANIFEST" "$PLATFORM" "$VERSION" "$TARGET_NAME" "$RES_DIR"
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

manifest_path = Path(sys.argv[1])
platform = sys.argv[2]
version = sys.argv[3]
target_name = sys.argv[4]
resources_dir = Path(sys.argv[5])

existing = {}
if manifest_path.exists():
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))

current = {
    "platform": platform,
    "version": version,
    "builtAt": datetime.now(timezone.utc).isoformat(),
    "path": target_name,
}

previous = None
old_current = existing.get("current")
old_previous = existing.get("previous")
if old_current and old_current.get("platform") == platform and old_current.get("path") != target_name:
    previous = old_current
elif old_previous and old_previous.get("platform") == platform:
    previous = old_previous

manifest = {"current": current, "previous": previous}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

keep = {current["path"]}
if previous:
    keep.add(previous["path"])

for entry in resources_dir.glob(f"ctrx-backend-{platform}-v*"):
    if entry.is_dir() and entry.name not in keep:
        for child in entry.iterdir():
            if child.is_dir():
                import shutil
                shutil.rmtree(child)
            else:
                child.unlink()
        entry.rmdir()
PY

echo "Packaged backend to $TARGET_DIR"
