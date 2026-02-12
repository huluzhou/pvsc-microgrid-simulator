# 构建与发布指南

## 构建流程

1. **打包 Python 内核**：使用 Nuitka 将 `python-kernel/` 编译为独立可执行文件
2. **构建前端**：`npm run build`
3. **构建 Tauri 应用**：`npm run tauri build`

## 本地构建

### Windows

```batch
build-release.bat
```

或分步执行：

```batch
python pack_python_kernel.py
npm run build
npm run tauri build
```

### Linux / macOS

```bash
./build-release.sh
```

## CI 构建 (GitHub Actions)

在 GitHub Actions 页手动运行 `Build Release` 工作流：

- 在 `windows-latest` 上构建
- 使用 Nuitka 打包 Python 内核（单文件模式）
- 仅生成 NSIS 安装包（.exe）
- 产物上传至 Actions Artifacts

## Python 内核打包说明

### 方式：Nuitka

- **优点**：生成原生可执行文件，无需用户安装 Python；性能较好
- **输出**：`dist/python-kernel/python-kernel.exe`（Windows）或 `python-kernel`（Linux）
- **依赖**：pandapower, numpy, pandas 等（见 `python-kernel/requirements.txt`）

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `PYTHON_KERNEL_ONEFILE` | 1=单文件，0=目录模式 | 1 |
| `NUITKA_JOBS` | 并行编译任务数 | 1 |

### 若 CI 内存不足

将 `PYTHON_KERNEL_ONEFILE=0` 可降低 Nuitka 内存占用，输出为目录形式（含 exe 与 dll）。

## 输出路径

- **安装包**：`src-tauri/target/release/bundle/nsis/*.exe`
- **内核**：`dist/python-kernel/`（打包后复制到应用 bundle 的 resources）
