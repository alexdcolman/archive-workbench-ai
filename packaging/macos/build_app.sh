#!/bin/bash
set -euo pipefail
BINARY="$1"
VERSION="$2"
OUTPUT_DIR="$3"

case "$VERSION" in
  *.dev*)
    BASE_VERSION=${VERSION%%.dev*}
    DEV_NUMBER=${VERSION##*.dev}
    MAJOR=${BASE_VERSION%%.*}
    REST=${BASE_VERSION#*.}
    MINOR=${REST%%.*}
    BUNDLE_SHORT_VERSION="$MAJOR.$MINOR.$DEV_NUMBER"
    ;;
  *)
    BUNDLE_SHORT_VERSION="$VERSION"
    ;;
esac

case "$BUNDLE_SHORT_VERSION" in
  *[!0-9.]*|.*|*..*|*.)
    echo "Versión de bundle macOS inválida: $BUNDLE_SHORT_VERSION" >&2
    exit 2
    ;;
esac

BUNDLE_BUILD_VERSION="$BUNDLE_SHORT_VERSION"
APP="$OUTPUT_DIR/Archive Workbench AI.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp "$BINARY" "$APP/Contents/MacOS/aw-ai"
chmod +x "$APP/Contents/MacOS/aw-ai"
cat > "$APP/Contents/MacOS/setup-launcher" <<'EOF'
#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$HERE/aw-ai" setup
EOF
chmod +x "$APP/Contents/MacOS/setup-launcher"
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Archive Workbench AI Setup</string>
<key>CFBundleDisplayName</key><string>Archive Workbench AI Setup</string>
<key>CFBundleIdentifier</key><string>org.giar.archive-workbench-ai</string>
<key>CFBundleVersion</key><string>${BUNDLE_BUILD_VERSION}</string>
<key>CFBundleShortVersionString</key><string>${BUNDLE_SHORT_VERSION}</string>
<key>CFBundleExecutable</key><string>setup-launcher</string>
<key>LSUIElement</key><false/>
</dict></plist>
EOF
DMG="$OUTPUT_DIR/Archive-Workbench-AI-${VERSION}-macOS.dmg"
rm -f "$DMG"
hdiutil create -volname "Archive Workbench AI" -srcfolder "$APP" -ov -format UDZO "$DMG"
echo "$DMG"
