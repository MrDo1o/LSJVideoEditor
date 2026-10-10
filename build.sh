#!/bin/bash
set -e # Exit immediately if a command fails

APP_NAME="LSJVideoEditor"
BUILD_DIR="build/TerminalBuild"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
MAC_OS_DIR="$APP_BUNDLE/Contents/MacOS"
RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"

echo "🧹 Cleaning old build..."
rm -rf "$BUILD_DIR"

echo "📁 Creating macOS App Bundle structure..."
mkdir -p "$MAC_OS_DIR"
mkdir -p "$RESOURCES_DIR"

echo "🔨 Compiling Swift files..."
# Find all .swift files in the current directory (.) and subdirectories
swiftc -emit-executable \
  -target $(uname -m)-apple-macosx14.0 \
  -framework SwiftUI \
  -framework AVKit \
  $(find LSJ-Video-Editor-Swift/LSJVideoEditor -name "*.swift") \
  -o "$MAC_OS_DIR/$APP_NAME"

echo "📦 Copying Resources (EliteEngine, Sovereign DSP, LumiHub, etc.)..."
# Check if EliteEngine is in the current folder, or the subfolder
if [ -d "EliteEngine" ]; then
    cp -R "EliteEngine" "$RESOURCES_DIR/"
elif [ -d "LSJVideoEditor/EliteEngine" ]; then
    cp -R "LSJVideoEditor/EliteEngine" "$RESOURCES_DIR/"
fi

# Copy Info.plist if it exists
if [ -f "Info.plist" ]; then
    cp "Info.plist" "$APP_BUNDLE/Contents/"
elif [ -f "LSJVideoEditor/Info.plist" ]; then
    cp "LSJVideoEditor/Info.plist" "$APP_BUNDLE/Contents/"
fi

echo "🔐 Code Signing the App Bundle..."
codesign --force --deep --sign - "$APP_BUNDLE"

echo "✅ Build Complete!"
echo "🚀 To run your app, type: ./$MAC_OS_DIR/$APP_NAME"

