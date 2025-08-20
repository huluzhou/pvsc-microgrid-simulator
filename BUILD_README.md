# PandaPower仿真器打包说明

本文档说明如何将PandaPower仿真器打包成可执行文件。

## 环境准备

### 1. 安装Anaconda或Miniconda

确保系统已安装Anaconda或Miniconda，并且conda命令可在命令行中使用。

### 2. 创建conda环境

```bash
# 使用environment.yml创建环境
conda env create -f environment.yml

# 或者手动创建环境
conda create -n pandapower_sim python=3.10
conda activate pandapower_sim
conda install -c conda-forge pyside6 pandapower numpy pandas matplotlib pyinstaller
```

### 3. 激活环境

```bash
conda activate pandapower_sim
```

## 打包方法

### 方法一：使用PowerShell脚本（推荐）

**在PowerShell中运行**：
```powershell
# 方式1：右键点击build.ps1文件，选择"使用PowerShell运行"
# 方式2：在PowerShell中执行
powershell -ExecutionPolicy Bypass -File build.ps1
```

**注意**: 如果遇到执行策略限制，请使用管理员权限运行PowerShell并执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

PowerShell脚本会自动：
- 检查conda环境
- 激活pandapower_sim环境  
- 检查Python和PyInstaller
- 执行打包过程
- 提供详细的错误提示和解决方案

### 方法二：手动执行

```bash
# 激活conda环境
conda activate pandapower_sim

# 注意：如果使用environment.yml创建环境，PyInstaller已自动安装
# 如果需要手动安装PyInstaller：
# conda install -y pyinstaller
# 或者使用pip
# pip install pyinstaller

# 执行打包脚本
python build.py

# 或者直接使用PyInstaller
pyinstaller pandapower_sim.spec
```

## 打包文件说明

- `pandapower_sim.spec`: PyInstaller配置文件，定义了打包参数
- `build.py`: Python打包脚本，自动化整个打包过程
- `build.ps1`: PowerShell脚本，一键打包（推荐使用）

## 输出文件

打包完成后，可执行文件将位于：
- `dist/PandaPowerSim.exe`: 主可执行文件
- `dist/`: 包含所有依赖文件的目录

## 注意事项

1. **必须使用conda环境**：确保在正确的conda环境中进行打包
2. **资源文件**：SVG图标和其他资源文件会自动包含在打包中
3. **依赖检查**：脚本会自动检查并安装必要的依赖
4. **分发**：将整个`dist`文件夹分发给最终用户

## 故障排除

### 常见问题

1. **PyInstaller 未找到**
   - 确保使用 conda 环境：`conda activate pandapower_sim`
   - 检查依赖安装：`conda list pyinstaller`

2. **构建失败**
   - 检查所有依赖是否正确安装
   - 确保在项目根目录执行构建命令
   - 查看详细错误信息进行调试
   - 如果遇到 lxml 相关错误，这是已知问题，构建脚本已优化避免此问题

3. **可执行文件无法运行**
   - 确保目标系统有必要的运行时库
   - 检查防病毒软件是否误报
   - 尝试在命令行运行查看错误信息

### 已解决的问题

- **lxml 模块导入错误**: 通过简化 PyInstaller 配置解决
- **复杂依赖冲突**: 使用更简洁的打包命令避免 spec 文件复杂性
- **资源文件路径问题**: 自动检测并包含实际存在的资源文件