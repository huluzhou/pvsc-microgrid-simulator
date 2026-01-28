#!/bin/bash
# 构建发布版本的完整流程
# 1. 打包Python内核
# 2. 构建前端
# 3. 构建Tauri应用

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始构建发布版本"
echo "=========================================="

# 1. 打包Python内核
echo ""
echo "[1/3] 打包Python内核..."
if python pack_python_kernel.py; then
    echo "✓ Python内核打包成功"
else
    echo "✗ Python内核打包失败"
    exit 1
fi

# 2. 构建前端
echo ""
echo "[2/3] 构建前端..."
if npm run build; then
    echo "✓ 前端构建成功"
else
    echo "✗ 前端构建失败"
    exit 1
fi

# 3. 构建Tauri应用
echo ""
echo "[3/3] 构建Tauri应用..."
if npm run tauri build; then
    echo "✓ Tauri应用构建成功"
else
    echo "✗ Tauri应用构建失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "构建完成！"
echo "=========================================="
