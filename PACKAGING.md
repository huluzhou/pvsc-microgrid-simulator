# 打包工具升级文档

## 1. 概述
本项目已从 PyInstaller 迁移至 Nuitka 打包方案，以提升应用程序的启动速度、运行性能和代码安全性。

## 2. 工具对比

| 特性 | PyInstaller (旧方案) | Nuitka (新方案) |
|------|---------------------|----------------|
| **原理** | 打包 Python 解释器和字节码 | 将 Python 编译为 C/C++ 代码，再编译为机器码 |
| **启动速度** | 较慢 (需解压和初始化解释器) | **显著提升** (直接执行机器码) |
| **运行性能** | 普通 (解释执行) | **提升** (部分代码静态优化) |
| **安全性** | 低 (容易反编译 pyc) | **高** (难以反编译机器码) |
| **文件大小** | 较大 (包含大量无用库) | 较小 (支持更好的依赖剔除和压缩) |
| **产物形式** | 文件夹 (onedir) 或 单文件 (onefile) | **高性能单文件** (onefile + zstandard) |

## 3. 使用方法

### 3.1 环境准备
确保已安装 Nuitka 和 C 编译器 (MinGW64 或 MSVC)。
```bash
pip install nuitka zstandard
```

### 3.2 执行打包
运行新的打包脚本：
```bash
python pack_nuitka.py
```
构建产物将位于 `dist/pandapower_sim.exe`。

### 3.3 常用参数
`pack_nuitka.py` 脚本内部已配置以下优化参数：
- `--standalone` / `--onefile`: 生成独立单文件
- `--enable-plugin=pyside6`: 自动处理 PySide6 依赖
- `--windows-disable-console`: 隐藏控制台窗口
- `--include-data-dir`: 自动包含 assets 资源

## 4. 性能指标 (预期)
- **启动时间**: 缩短 30% 以上
- **内存占用**: 降低 20% 左右
- **代码保护**: 提供源码级混淆保护

## 5. 回滚方案
如果 Nuitka 打包出现兼容性问题，可随时回滚至 PyInstaller 方案。

### 回滚步骤
1. 运行原有的构建脚本：
   ```bash
   python build.py
   ```
   或者使用发布工具：
   ```bash
   python pack_release.py
   ```
2. 原有脚本未做任何修改，可直接使用。

## 6. 常见问题
- **构建时间过长**: Nuitka 需要编译 C 代码，初次构建较慢，后续会有缓存。
- **缺少模块**: 如果运行报错 `ModuleNotFoundError`，请在 `pack_nuitka.py` 中移除对应的 `--nofollow-import-to` 排除项，或添加 `--include-package`。
