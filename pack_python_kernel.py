#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Nuitka打包Python内核为独立可执行文件
用于Tauri应用集成
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def find_python_executable():
    """查找可用的Python解释器"""
    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    # 如果在虚拟环境中，优先使用当前解释器
    if in_venv and sys.executable:
        print(f"检测到虚拟环境: {sys.prefix}")
        version_result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if version_result.returncode == 0:
            version_info = version_result.stdout.strip()
            print(f"使用虚拟环境中的Python: {sys.executable} ({version_info})")
            return sys.executable
    
    # 如果不在虚拟环境中，尝试查找python3或python
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
                print(f"使用Python解释器: {cmd} ({version_info})")
                if not in_venv:
                    print("⚠ 警告: 未在虚拟环境中，建议使用虚拟环境以避免系统包冲突")
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # 最后尝试使用当前解释器
    if sys.executable:
        print(f"使用当前Python解释器: {sys.executable}")
        if not in_venv:
            print("⚠ 警告: 未在虚拟环境中，建议使用虚拟环境以避免系统包冲突")
        return sys.executable
    
    raise RuntimeError("未找到可用的Python解释器")

def check_dependencies(python_exe):
    """检查并安装必要的依赖"""
    # 检查requirements.txt
    requirements_file = Path("python-kernel/requirements.txt")
    if not requirements_file.exists():
        print("⚠ 警告: 未找到 python-kernel/requirements.txt")
        print("  请确保已安装必要的依赖: pandapower, numpy, pandas等")
        return
    
    # 检查关键依赖是否已安装
    critical_modules = ["pandapower", "numpy", "pandas"]
    missing_modules = []
    
    for module in critical_modules:
        result = subprocess.run(
            [python_exe, "-c", f"import {module}"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"检测到缺失的依赖: {', '.join(missing_modules)}")
        print("正在安装Python内核依赖...")
        try:
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "-r", str(requirements_file)],
                timeout=600,  # 10分钟超时（pandapower等可能较大）
                check=False
            )
            if result.returncode == 0:
                print("✓ Python内核依赖安装成功")
            else:
                print("⚠ 警告: 依赖安装可能不完整")
                print(f"  请手动运行: {python_exe} -m pip install -r python-kernel/requirements.txt")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            print(f"⚠ 警告: 无法自动安装依赖: {e}")
            print(f"  请手动运行: {python_exe} -m pip install -r python-kernel/requirements.txt")
    else:
        print("✓ Python内核依赖已安装")

def check_nuitka(python_exe):
    """检查Nuitka是否已安装"""
    try:
        # 使用指定的Python解释器检查Nuitka
        result = subprocess.run(
            [python_exe, "-c", "import nuitka; print(nuitka.__version__)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"Nuitka版本: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    print("Nuitka未安装，正在安装...")
    try:
        subprocess.check_call([
            python_exe, "-m", "pip", "install", 
            "nuitka>=2.7.14", "zstandard>=0.21.0"
        ])
        print("Nuitka安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Nuitka安装失败 (退出码: {e.returncode})")
        print("\n解决方案:")
        print("1. 如果系统提示 'externally-managed-environment'，请使用虚拟环境:")
        print("   python3 -m venv venv-build")
        print("   source venv-build/bin/activate  # Linux/macOS")
        print("   .\\venv-build\\Scripts\\activate  # Windows")
        print("   pip install nuitka zstandard")
        print("\n2. 或者手动安装:")
        print(f"   {python_exe} -m pip install --user nuitka zstandard")
        print("\n3. 安装完成后重新运行此脚本")
        return False

def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = [
        'python-kernel.build', 
        'python-kernel.dist', 
        'python-kernel.onefile-build',
        'main.build',
        'main.dist',
        'main.onefile-build'
    ]
    
    print("清理构建文件...")
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name, ignore_errors=True)
    
    # 清理输出目录中的旧文件
    output_dirs = [
        'src-tauri/target/release/python-kernel',
        'src-tauri/target/debug/python-kernel',
        'dist/python-kernel'
    ]
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            print(f"清理输出目录: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)

def build_executable(python_exe):
    """使用Nuitka构建Python内核可执行文件"""
    print("\n开始使用Nuitka构建Python内核可执行文件...")
    
    # 确定入口文件
    entry_file = Path("python-kernel/main.py")
    if not entry_file.exists():
        print(f"错误: 找不到入口文件 {entry_file}")
        return False
    
    # 确定输出目录
    output_dir = Path("dist/python-kernel")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建参数（可通过环境变量调整）
    # PYTHON_KERNEL_ONEFILE=0 可禁用 onefile，降低内存占用
    # NUITKA_JOBS 设置并行编译任务数（默认 1，减少内存占用）
    onefile_env = os.getenv("PYTHON_KERNEL_ONEFILE", "1").strip().lower()
    use_onefile = onefile_env not in ("0", "false", "no")
    nuitka_jobs = os.getenv("NUITKA_JOBS", "1").strip()

    # Nuitka基础命令
    cmd = [
        python_exe, "-m", "nuitka",
        "--standalone",              # 包含所有依赖
        "--show-progress",           # 显示进度
        "--show-memory",             # 显示内存使用
        "--assume-yes-for-downloads", # 自动下载依赖
        f"--jobs={nuitka_jobs}",      # 控制并行任务数
        "--lto=no",                   # 禁用 LTO，降低内存占用
        # 输出目录
        f"--output-dir={output_dir}",
    ]

    if use_onefile:
        # 生成单文件（内存占用较高）
        cmd.append("--onefile")
        cmd.append(
            f"--output-filename={'python-kernel.exe' if sys.platform == 'win32' else 'python-kernel'}"
        )
    
    # 平台特定选项
    if sys.platform == "win32":
        cmd.append("--windows-console-mode=disable")  # Windows下禁用控制台窗口
    elif sys.platform == "darwin":
        cmd.append("--macos-create-app-bundle")  # macOS创建应用包
    
    # 包含必要的包（仅包含 python-kernel 目录中实际存在的包）
    include_packages = [
        "simulation",
        "ai",
    ]
    for pkg in include_packages:
        cmd.append(f"--include-package={pkg}")
    
    # 包含pandapower相关模块
    cmd.extend([
        "--include-module=pandapower",
        "--include-module=numpy",
        "--include-module=scipy",
        "--include-module=pandas",
    ])
    
    # 排除不必要的模块以减小体积和加快编译速度
    excludes = [
        # GUI 相关
        "tkinter",
        "matplotlib",  # 整个 matplotlib，如果不需要图表
        # 交互式环境
        "IPython",
        "jupyter",
        "notebook",
        # 测试框架
        "pytest",
        "unittest",
        "doctest",
        # 包管理
        "setuptools",
        "distutils",
        "pkg_resources",
        "pip",
        # 测试目录（减少编译量）
        "scipy.tests",
        "numpy.tests", 
        "pandas.tests",
        "numpy.testing",
        "scipy.testing",
        # 不常用的 scipy 子模块
        "scipy.io.matlab",
        "scipy.io.arff",
        "scipy.io.wavfile",
        "scipy.signal",
        "scipy.ndimage",
        "scipy.interpolate",
        "scipy.integrate",
        "scipy.fft",
        # 其他
        "xml.etree.ElementTree",
        "email",
        "html.parser",
        "http.server",
        "xmlrpc",
    ]
    
    for module in excludes:
        cmd.append(f"--nofollow-import-to={module}")
    
    # 添加入口文件
    cmd.append(str(entry_file))
    
    print(f"执行命令: {' '.join(cmd)}")
    print(f"输出目录: {output_dir}")
    print(f"构建模式: {'onefile' if use_onefile else 'standalone目录'}")
    print(f"Nuitka并行任务数: {nuitka_jobs}")
    
    start_time = time.time()
    try:
        # 执行Nuitka构建
        subprocess.run(cmd, check=True)
        
        # 检查生成的文件
        exe_ext = ".exe" if sys.platform == "win32" else ""
        final_exe_name = f"python-kernel{exe_ext}"
        
        if use_onefile:
            # Onefile 模式：单个可执行文件
            exe_path = output_dir / final_exe_name
        else:
            # Standalone 目录模式：main.dist 目录下的 main 可执行文件
            nuitka_dist_dir = output_dir / "main.dist"
            nuitka_exe_path = nuitka_dist_dir / f"main{exe_ext}"
            
            if not nuitka_exe_path.exists():
                print(f"\n✗ 错误: 未找到 Nuitka 生成的可执行文件 {nuitka_exe_path}")
                if output_dir.exists():
                    print(f"  输出目录 {output_dir} 内容:")
                    for item in output_dir.iterdir():
                        print(f"    - {item.name}")
                return False
            
            # 重新组织目录结构，使其符合 Tauri 的期望
            # 将 main.dist/ 下的所有内容移动到 output_dir，并重命名可执行文件
            print("\n重新组织目录结构以适配 Tauri...")
            
            # 将 main.dist 内的所有文件移动到 output_dir
            for item in nuitka_dist_dir.iterdir():
                dest = output_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            
            # 删除空的 main.dist 目录
            if nuitka_dist_dir.exists():
                nuitka_dist_dir.rmdir()
            
            # 重命名可执行文件：main.exe -> python-kernel.exe
            old_exe = output_dir / f"main{exe_ext}"
            exe_path = output_dir / final_exe_name
            if old_exe.exists():
                old_exe.rename(exe_path)
                print(f"  重命名: main{exe_ext} -> {final_exe_name}")
        
        if exe_path.exists():
            if use_onefile:
                print(f"\n✓ 构建成功! 可执行文件: {exe_path}")
                print(f"  文件大小: {exe_path.stat().st_size / (1024*1024):.2f} MB")
            else:
                # 计算目录总大小
                total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
                print(f"\n✓ 构建成功! 输出目录: {output_dir}")
                print(f"  目录总大小: {total_size / (1024*1024):.2f} MB")
                print(f"  可执行文件: {exe_path}")
            
            # 同时复制到Tauri的target目录（如果存在）
            tauri_release_dir = Path("src-tauri/target/release/python-kernel")
            tauri_debug_dir = Path("src-tauri/target/debug/python-kernel")
            
            for tauri_dir in [tauri_release_dir, tauri_debug_dir]:
                if tauri_dir.parent.exists():
                    if use_onefile:
                        # Onefile 模式：复制单个文件
                        tauri_dir.mkdir(parents=True, exist_ok=True)
                        tauri_exe = tauri_dir / final_exe_name
                        if tauri_exe.exists():
                            tauri_exe.unlink()
                        shutil.copy2(exe_path, tauri_exe)
                        print(f"  已复制到: {tauri_exe}")
                    else:
                        # Standalone 目录模式：复制整个目录
                        if tauri_dir.exists():
                            shutil.rmtree(tauri_dir)
                        shutil.copytree(output_dir, tauri_dir)
                        print(f"  已复制目录到: {tauri_dir}")
            
            end_time = time.time()
            duration = end_time - start_time
            print(f"\n构建耗时: {duration:.2f}秒")
            return True
        else:
            print(f"\n✗ 错误: 未找到生成的可执行文件 {exe_path}")
            # 列出输出目录内容以便调试
            if output_dir.exists():
                print(f"  输出目录 {output_dir} 内容:")
                for item in output_dir.iterdir():
                    print(f"    - {item.name}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 构建失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 构建过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Python内核 Nuitka打包工具")
    print("=" * 60)
    print("此工具将Python内核打包为独立可执行文件，供Tauri应用调用")
    print()
    
    # 0. 查找Python解释器
    try:
        python_exe = find_python_executable()
    except RuntimeError as e:
        print(f"错误: {e}")
        return False
    
    # 0.5. 检查并安装Python内核依赖
    print("\n[0/4] 检查Python内核依赖...")
    check_dependencies(python_exe)
    
    # 1. 检查Nuitka
    print("\n[1/4] 检查Nuitka...")
    if not check_nuitka(python_exe):
        return False
    
    # 2. 清理构建文件
    print("\n[2/4] 清理构建文件...")
    clean_build()
    
    # 3. 构建可执行文件
    print("\n[3/4] 构建可执行文件...")
    if not build_executable(python_exe):
        return False
    
    print("\n" + "=" * 60)
    print("打包完成!")
    print("=" * 60)
    
    # 根据模式显示输出位置
    onefile_env = os.getenv("PYTHON_KERNEL_ONEFILE", "1").strip().lower()
    use_onefile = onefile_env not in ("0", "false", "no")
    exe_ext = ".exe" if sys.platform == "win32" else ""
    
    if use_onefile:
        print("可执行文件位置:")
        print(f"  - dist/python-kernel/python-kernel{exe_ext}")
    else:
        print("输出目录位置:")
        print(f"  - dist/python-kernel/")
        print(f"  - 可执行文件: dist/python-kernel/python-kernel{exe_ext}")
    print("=" * 60)
    print("\n提示: 在Tauri构建时，此输出将被包含在应用包中")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
