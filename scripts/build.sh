#!/usr/bin/env bash
# scripts/build.sh
# Run on native Ubuntu 22.04 (glibc 2.35) to produce AppImage and .deb.
# Usage: bash scripts/build.sh --version <semver>
set -euo pipefail

VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Usage: bash scripts/build.sh --version <semver>" >&2
  exit 2
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be semver (e.g. 1.2.0). Got: '$VERSION'" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Step 1: PyInstaller backend ==="
bash "$ROOT/scripts/package_backend.sh" --platform linux-x64 --version "$VERSION"

echo "=== Step 2: Vite frontend (Electron: relative base + hash router) ==="
(cd "$ROOT/frontend" && VITE_ELECTRON=1 npm run build)

echo "=== Step 3: tsc electron main process + stage preload.cjs ==="
(cd "$ROOT" && npm run build:electron)

echo "=== Step 4: electron-builder (Linux AppImage + deb) ==="
(cd "$ROOT" && npx electron-builder --linux "-c.extraMetadata.version=$VERSION")

echo "Build complete. Artifacts in dist/"
