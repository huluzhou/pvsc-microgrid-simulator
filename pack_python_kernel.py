#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 PyInstaller 打包 Python 内核为独立可执行文件
用于 Tauri 应用集成
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path


def find_python_executable():
    """查找可用的 Python 解释器"""
    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv and sys.executable:
        print(f"检测到虚拟环境: {sys.prefix}")
        return sys.executable
    
    # 尝试查找 python3 或 python
    candidates = ["python3", "python"]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_info = result.stdout.strip()
                print(f"使用 Python 解释器: {cmd} ({version_info})")
                if not in_venv:
                    print("⚠ 警告: 未在虚拟环境中，建议使用虚拟环境")
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    if sys.executable:
        print(f"使用当前 Python 解释器: {sys.executable}")
        return sys.executable
    
    raise RuntimeError("未找到可用的 Python 解释器")


def check_pyinstaller(python_exe):
    """检查并安装 PyInstaller"""
    try:
        result = subprocess.run(
            [python_exe, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"PyInstaller 版本: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    print("PyInstaller 未安装，正在安装...")
    try:
        subprocess.check_call([
            python_exe, "-m", "pip", "install", "pyinstaller>=6.0"
        ])
        print("PyInstaller 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ PyInstaller 安装失败 (退出码: {e.returncode})")
        return False


def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = [
        'build',
        'dist/python-kernel',
        '__pycache__',
    ]
    
    files_to_clean = [
        'python-kernel.spec',
    ]
    
    print("清理构建文件...")
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  清理目录: {dir_name}")
            shutil.rmtree(dir_name, ignore_errors=True)
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            print(f"  清理文件: {file_name}")
            os.remove(file_name)


def build_executable(python_exe):
    """使用 PyInstaller 构建可执行文件"""
    print("\n开始使用 PyInstaller 构建 Python 内核...")
    
    # 确定入口文件
    entry_file = Path("python-kernel/main.py")
    if not entry_file.exists():
        print(f"错误: 找不到入口文件 {entry_file}")
        return False
    
    # 确定输出目录
    output_dir = Path("dist/python-kernel")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # PyInstaller 命令
    exe_name = "python-kernel"
    
    cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",           # 不询问确认
        "--clean",               # 清理临时文件
        "--name", exe_name,      # 输出文件名
        "--distpath", str(output_dir.parent),  # 输出目录
        "--workpath", "build",   # 工作目录
        "--specpath", ".",       # spec 文件位置
    ]
    
    # 使用目录模式（非单文件），启动更快
    # 单文件模式启动慢是因为需要解压
    cmd.append("--onedir")
    
    # 不显示控制台窗口（Windows）
    if sys.platform == "win32":
        cmd.append("--noconsole")
    
    # 隐藏导入（PyInstaller 可能检测不到的模块）
    hidden_imports = [
        # 本地模块
        "simulation",
        "simulation.engine",
        "simulation.adapters",
        "simulation.adapters.pandapower_adapter",
        "simulation.adapters.topology_adapter",
        "simulation.power_calculation",
        "simulation.power_calculation.factory",
        "simulation.power_calculation.interface",
        "simulation.power_calculation.implementations",
        "simulation.power_calculation.implementations.pandapower_impl",
        "simulation.power_calculation.implementations.pypsa_impl",
        "simulation.power_calculation.implementations.gridcal_impl",
        "simulation.historical_data",
        "ai",
        "ai.factory",
        "ai.interface",
        "ai.implementations",
        "ai.implementations.pytorch_impl",
        "ai.implementations.tensorflow_impl",
        "ai.implementations.gym_impl",
        # 第三方库
        "pandapower",
        "pandapower.auxiliary",
        "pandapower.build_branch",
        "pandapower.build_bus",
        "pandapower.build_gen",
        "pandapower.create",
        "pandapower.diagnostic",
        "pandapower.file_io",
        "pandapower.networks",
        "pandapower.pf",
        "pandapower.pf.runpp",
        "pandapower.powerflow",
        "pandapower.results",
        "pandapower.run",
        "pandapower.runpp",
        "pandapower.toolbox",
        "pandapower.topology",
        "numpy",
        "numpy.core",
        "numpy.linalg",
        "pandas",
        "pandas.core",
        "scipy",
        "scipy.sparse",
        "scipy.sparse.linalg",
        "scipy.sparse.csgraph",
        "scipy.optimize",
        "scipy.linalg",
        "networkx",
    ]
    
    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])
    
    # 收集子模块
    collect_submodules = [
        "simulation",
        "ai", 
        "pandapower",
    ]
    
    for module in collect_submodules:
        cmd.extend(["--collect-submodules", module])
    
    # 添加数据文件（Python 内核的模块作为包）
    cmd.extend(["--add-data", f"python-kernel/simulation{os.pathsep}simulation"])
    cmd.extend(["--add-data", f"python-kernel/ai{os.pathsep}ai"])
    
    # 排除不需要的模块
    excludes = [
        "tkinter",
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "sphinx",
    ]
    
    for module in excludes:
        cmd.extend(["--exclude-module", module])
    
    # 入口文件
    cmd.append(str(entry_file))
    
    print(f"执行命令: {' '.join(cmd)}")
    print(f"输出目录: {output_dir}")
    
    start_time = time.time()
    try:
        # 执行 PyInstaller
        result = subprocess.run(cmd, check=True)
        
        # PyInstaller 输出到 dist/python-kernel/python-kernel/
        pyinstaller_output = output_dir.parent / exe_name / exe_name
        if sys.platform == "win32":
            exe_path = pyinstaller_output.parent / f"{exe_name}.exe"
        else:
            exe_path = pyinstaller_output.parent / exe_name
        
        # 将输出移动到正确位置
        pyinstaller_dist = output_dir.parent / exe_name
        if pyinstaller_dist.exists() and pyinstaller_dist != output_dir:
            # 移动内容到 output_dir
            if output_dir.exists():
                shutil.rmtree(output_dir)
            shutil.move(str(pyinstaller_dist), str(output_dir))
        
        # 检查可执行文件
        if sys.platform == "win32":
            final_exe = output_dir / f"{exe_name}.exe"
        else:
            final_exe = output_dir / exe_name
        
        if final_exe.exists():
            # 计算目录大小
            total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
            
            print(f"\n[成功] 构建成功!")
            print(f"  输出目录: {output_dir}")
            print(f"  可执行文件: {final_exe}")
            print(f"  目录总大小: {total_size / (1024*1024):.2f} MB")
            
            end_time = time.time()
            print(f"\n构建耗时: {end_time - start_time:.2f} 秒")
            return True
        else:
            print(f"\n[错误] 未找到生成的可执行文件")
            print(f"  期望位置: {final_exe}")
            if output_dir.exists():
                print(f"  输出目录内容:")
                for item in output_dir.iterdir():
                    print(f"    - {item.name}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n[错误] 构建失败: {e}")
        return False
    except Exception as e:
        print(f"\n[错误] 构建过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Python 内核 PyInstaller 打包工具")
    print("=" * 60)
    print("此工具将 Python 内核打包为独立可执行文件，供 Tauri 应用调用")
    print()
    
    # 0. 查找 Python 解释器
    try:
        python_exe = find_python_executable()
    except RuntimeError as e:
        print(f"错误: {e}")
        return False
    
    # 1. 检查 PyInstaller
    print("\n[1/3] 检查 PyInstaller...")
    if not check_pyinstaller(python_exe):
        return False
    
    # 2. 清理构建文件
    print("\n[2/3] 清理构建文件...")
    clean_build()
    
    # 3. 构建可执行文件
    print("\n[3/3] 构建可执行文件...")
    if not build_executable(python_exe):
        return False
    
    exe_ext = ".exe" if sys.platform == "win32" else ""
    
    print("\n" + "=" * 60)
    print("打包完成!")
    print("=" * 60)
    print("输出目录位置:")
    print(f"  - dist/python-kernel/")
    print(f"  - 可执行文件: dist/python-kernel/python-kernel{exe_ext}")
    print("=" * 60)
    print("\n提示: 在 Tauri 构建时，此输出将被包含在应用包中")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
