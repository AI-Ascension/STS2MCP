#!/usr/bin/env bash
# Build all three stub DLLs and output them ready for CI use.
# Usage: ./build-stubs.sh [output-dir]
# Default output: ../stubs/libs-game/data_sts2_windows_x86_64/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-"$SCRIPT_DIR/libs-game/data_sts2_windows_x86_64"}"

echo "Building stub DLLs -> $OUT_DIR"
mkdir -p "$OUT_DIR"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

dotnet build "$SCRIPT_DIR/GodotSharp/GodotSharp.csproj" -c Release -o "$TMPDIR/godot" --nologo --verbosity minimal
dotnet build "$SCRIPT_DIR/Harmony/Harmony.csproj"       -c Release -o "$TMPDIR/harmony" --nologo --verbosity minimal
dotnet build "$SCRIPT_DIR/sts2/sts2.csproj"             -c Release -o "$TMPDIR/sts2" --nologo --verbosity minimal

cp "$TMPDIR/godot/GodotSharp.dll"   "$OUT_DIR/GodotSharp.dll"
cp "$TMPDIR/harmony/0Harmony.dll"   "$OUT_DIR/0Harmony.dll"
cp "$TMPDIR/sts2/sts2.dll"          "$OUT_DIR/sts2.dll"

# Also copy to the flat libs/ directory (used by tasks that just need the DLLs)
LIBS_DIR="$SCRIPT_DIR/libs"
mkdir -p "$LIBS_DIR"
cp "$OUT_DIR/GodotSharp.dll" "$LIBS_DIR/GodotSharp.dll"
cp "$OUT_DIR/0Harmony.dll"   "$LIBS_DIR/0Harmony.dll"
cp "$OUT_DIR/sts2.dll"       "$LIBS_DIR/sts2.dll"

echo "Done. Stub DLLs written to $OUT_DIR"
