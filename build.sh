#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="${APP_OUTPUT:-${SCRIPT_DIR}/dist/AI Control Studio.app}"
PYTHON_RUNTIME="$(command -v python3)"
"${PYTHON_RUNTIME}" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"'
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"
swiftc -O "${SCRIPT_DIR}/SecretVault.swift" "${SCRIPT_DIR}/main.swift" "${SCRIPT_DIR}/CatalogView.swift" "${SCRIPT_DIR}/VisualStyle.swift" "${SCRIPT_DIR}/SetupSupport.swift" "${SCRIPT_DIR}/StudioView.swift" -o "${APP}/Contents/MacOS/AI-Control-Studio"
cp "${SCRIPT_DIR}/packages.py" "${SCRIPT_DIR}/research_locals.py" "${SCRIPT_DIR}/local-sources.json" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/catalog.py" "${SCRIPT_DIR}/catalog-seed.json" "${SCRIPT_DIR}/provider-guides.json" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/secret_store.py" "${SCRIPT_DIR}/jev_assist.py" "${SCRIPT_DIR}/tavily_skills.py" "${SCRIPT_DIR}/jev.py" "${SCRIPT_DIR}/studio.py" "${SCRIPT_DIR}/skill_import.py" "${SCRIPT_DIR}/studio.html" "${SCRIPT_DIR}/gateway_profiles.py" "${SCRIPT_DIR}/apply_bundle.py" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/codex_switch.py" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/switch.py" "${APP}/Contents/Resources/switch.py"
mkdir -p "${APP}/Contents/Resources/logos"
cp "${SCRIPT_DIR}/assets/logos/"*.png "${SCRIPT_DIR}/assets/logos/sources.json" "${APP}/Contents/Resources/logos/"
rm -f "${APP}/Contents/Resources/gateway-switch-art.png"
cp "${SCRIPT_DIR}/assets/logo-index.json" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/assets/pixel-switch-sidebar.png" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/assets/pixel-switch-icon.png" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/assets/workshop-"*.png "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/assets/switch-mark.png" "${APP}/Contents/Resources/"
cp "${SCRIPT_DIR}/assets/PixelSwitch.icns" "${APP}/Contents/Resources/PixelSwitch.icns"
cat > "${APP}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>io.github.ai-control-studio</string>
  <key>CFBundleName</key><string>AI Control Studio</string>
  <key>CFBundleDisplayName</key><string>AI Control Studio</string>
  <key>CFBundleExecutable</key><string>AI-Control-Studio</string>
  <key>CFBundleIconFile</key><string>PixelSwitch.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>AIControlPythonRuntime</key><string>__PYTHON_RUNTIME__</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
"${PYTHON_RUNTIME}" - "${APP}/Contents/Info.plist" "${PYTHON_RUNTIME}" <<'PY'
import plistlib,sys
p=sys.argv[1]
with open(p,"rb") as f:d=plistlib.load(f)
d["AIControlPythonRuntime"]=sys.argv[2]
with open(p,"wb") as f:plistlib.dump(d,f)
PY
echo "Created ${APP}"
