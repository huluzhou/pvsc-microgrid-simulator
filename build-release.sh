#!/bin/bash
# 构建Release版本脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "  光储充微电网模拟器 - Release构建"
echo "=========================================="
echo ""

echo "[1/2] 构建前端..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ 前端构建失败"
    exit 1
fi

echo ""
echo "[2/2] 构建Rust后端 (Release)..."
cd src-tauri
cargo build --release

if [ $? -ne 0 ]; then
    echo "❌ Rust构建失败"
    exit 1
fi

cd ..

echo ""
echo "=========================================="
echo "✅ Release版本构建成功！"
echo "=========================================="
echo ""
echo "可执行文件位置: src-tauri/target/release/pvsc-microgrid-simulator"
echo "文件大小: $(du -h src-tauri/target/release/pvsc-microgrid-simulator | cut -f1)"
echo ""
echo "运行方式："
echo "  1. ./run-release.sh"
echo "  2. ./src-tauri/target/release/pvsc-microgrid-simulator"
echo ""
