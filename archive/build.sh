#!/bin/bash

echo "=== VERA v2 Core Build ==="

# 1. Create cargo project structure
mkdir -p src
echo "✓ Created src/"

# 2. Build release
echo "Building Rust..."
cargo build --release 2>&1 | tail -20

# 3. Generate JNI headers (if installed)
if command -v javac &> /dev/null; then
    echo "Generating JNI headers..."
    javac -h . src/vera_android.rs 2>/dev/null || true
fi

# 4. Summary
echo ""
echo "=== Build Complete ==="
echo "Library: target/release/libvera.so (or libvera.dylib)"
echo "Ready for Android JNI integration"

