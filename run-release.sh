#!/bin/bash
# 光储充微电网模拟器 - Release版本启动脚本

cd "$(dirname "$0")"

# 检查release版本是否存在
if [ ! -f "src-tauri/target/release/pvsc-microgrid-simulator" ]; then
    echo "Release版本不存在，开始构建..."
    npm run build
    cd src-tauri
    cargo build --release
    cd ..
fi

echo "启动光储充微电网模拟器 (Release版本)..."
./src-tauri/target/release/pvsc-microgrid-simulator
