#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本
用于将PandaPower仿真器打包成可执行文件
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from src.config import (
    # 功能标志
    FEATURE_SIMULATION, FEATURE_MODBUS, FEATURE_REPORT, FEATURE_EXPORT,
    # 调试模式标志
    DEBUG_MODE, VERBOSE_LOGGING,
    # 辅助函数和装饰器
    is_feature_enabled, conditional_compile, import_if_enabled
)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("提示: 安装tqdm可获得更好的进度显示体验: pip install tqdm")
    
    # 简单的进度条替代
    class tqdm:
        def __init__(self, total=None, desc="", unit=""):
            self.total = total
            self.desc = desc
            self.current = 0
            print(f"{desc}...")
        
        def update(self, n=1):
            self.current += n
            if self.total:
                percent = (self.current / self.total) * 100
                print(f"\r{self.desc}: {percent:.1f}%", end="", flush=True)
            else:
                print(".", end="", flush=True)
        
        def close(self):
            print("\n完成!")
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            self.close()


def check_conda_env():
    """检查是否在conda环境中"""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env:
        print(f"当前conda环境: {conda_env}")
        return True
    else:
        print("警告: 未检测到conda环境，建议激活pandapower_sim环境")
        return False


def check_pyinstaller():
    """检查PyInstaller是否已安装
    
    注意：如果使用environment.yml创建环境，PyInstaller应该已经自动安装
    """
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        print("提示：建议使用 'conda env create -f environment.yml' 创建包含PyInstaller的完整环境")
        try:
            # 优先使用conda安装PyInstaller
            subprocess.check_call(["conda", "install", "-y", "pyinstaller"])
            print("PyInstaller通过conda安装成功")
            return True
        except subprocess.CalledProcessError:
            print("conda安装失败，尝试使用pip安装...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
                print("PyInstaller通过pip安装成功")
                return True
            except subprocess.CalledProcessError:
                print("PyInstaller安装失败，请手动安装：conda install pyinstaller 或 pip install pyinstaller")
                return False


def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    print("清理构建文件...")
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    pyc_count = 0
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
                pyc_count += 1
    
    if pyc_count > 0:
        print(f"清理了 {pyc_count} 个.pyc文件")


def build_executable():
    """构建可执行文件"""
    print("\n开始构建可执行文件...")
    
    # 使用简化的PyInstaller命令，避免复杂的spec文件配置问题
    # 排除未使用的PySide6组件以减小可执行文件大小
    if FEATURE_SIMULATION:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed", 
            "--name=pandapower_sim",
            "--upx-dir=upx",
            "--clean",
            "--optimize=2",
            "--add-data=src/assets;assets",
            # 排除未使用的PySide6模块
            "--exclude-module=PySide6.QtBluetooth",
            "--exclude-module=PySide6.QtConcurrent",
            "--exclude-module=PySide6.QtDBus",
            "--exclude-module=PySide6.QtDesigner",
            "--exclude-module=PySide6.QtHelp",
            "--exclude-module=PySide6.QtMultimedia",
            "--exclude-module=PySide6.QtMultimediaWidgets",
            "--exclude-module=PySide6.QtNetwork",
            "--exclude-module=PySide6.QtOpenGL",
            "--exclude-module=PySide6.QtOpenGLWidgets",
            "--exclude-module=PySide6.QtPositioning",
            "--exclude-module=PySide6.QtPrintSupport",
            "--exclude-module=PySide6.QtQml",
            "--exclude-module=PySide6.QtQuick",
            "--exclude-module=PySide6.QtQuickControls2",
            "--exclude-module=PySide6.QtQuickWidgets",
            "--exclude-module=PySide6.QtRemoteObjects",
            "--exclude-module=PySide6.QtScxml",
            "--exclude-module=PySide6.QtSensors",
            "--exclude-module=PySide6.QtSerialPort",
            "--exclude-module=PySide6.QtSql",
            "--exclude-module=PySide6.QtTest",
            "--exclude-module=PySide6.QtWebChannel",
            "--exclude-module=PySide6.QtWebEngine",
            "--exclude-module=PySide6.QtWebEngineCore",
            "--exclude-module=PySide6.QtWebEngineWidgets",
            "--exclude-module=PySide6.QtWebSockets",
            "--exclude-module=PySide6.QtXml",

            # 排除其他可能不需要的模块
            "--exclude-module=tkinter",
            "--exclude-module=Tkinter",
            "--exclude-module=matplotlib.backends.backend_tkagg",
            "--exclude-module=matplotlib.backends.backend_webagg",
            "--exclude-module=matplotlib.backends.backend_qt4agg",
            "--exclude-module=IPython",
            "--exclude-module=jupyter",
            "--exclude-module=notebook",
            "--exclude-module=pytest",
            "--exclude-module=test",
            "--exclude-module=doctest",
            "--exclude-module=distutils",
            "--exclude-module=setuptools",
            "--exclude-module=pkg_resources",
            "src/main.py"
        ]
    else:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed", 
            "--name=pandapower_sim",
            "--upx-dir=upx",
            "--clean",
            "--optimize=2",
            "--add-data=src/assets;assets",
            # 排除未使用的PySide6模块
            "--exclude-module=PySide6.QtBluetooth",
            "--exclude-module=PySide6.QtConcurrent",
            "--exclude-module=PySide6.QtDBus",
            "--exclude-module=PySide6.QtDesigner",
            "--exclude-module=PySide6.QtHelp",
            "--exclude-module=PySide6.QtMultimedia",
            "--exclude-module=PySide6.QtMultimediaWidgets",
            "--exclude-module=PySide6.QtNetwork",
            "--exclude-module=PySide6.QtOpenGL",
            "--exclude-module=PySide6.QtOpenGLWidgets",
            "--exclude-module=PySide6.QtPositioning",
            "--exclude-module=PySide6.QtPrintSupport",
            "--exclude-module=PySide6.QtQml",
            "--exclude-module=PySide6.QtQuick",
            "--exclude-module=PySide6.QtQuickControls2",
            "--exclude-module=PySide6.QtQuickWidgets",
            "--exclude-module=PySide6.QtRemoteObjects",
            "--exclude-module=PySide6.QtScxml",
            "--exclude-module=PySide6.QtSensors",
            "--exclude-module=PySide6.QtSerialPort",
            "--exclude-module=PySide6.QtSql",
            "--exclude-module=PySide6.QtTest",
            "--exclude-module=PySide6.QtWebChannel",
            "--exclude-module=PySide6.QtWebEngine",
            "--exclude-module=PySide6.QtWebEngineCore",
            "--exclude-module=PySide6.QtWebEngineWidgets",
            "--exclude-module=PySide6.QtWebSockets",
            "--exclude-module=PySide6.QtXml",

            # 排除pandapower及其相关组件
            "--exclude-module=pandapower",
            "--exclude-module=pandapower.converter",
            "--exclude-module=pandapower.control",
            "--exclude-module=pandapower.plotting",
            "--exclude-module=pandapower.pf",
            "--exclude-module=pandapower.opf",
            "--exclude-module=pandapower.shortcircuit",
            "--exclude-module=pandapower.results",
            "--exclude-module=pandapower.timeseries",
            "--exclude-module=numpy",
            "--exclude-module=scipy",
            "--exclude-module=pandas",
            "--exclude-module=matplotlib",
            "--exclude-module=sympy",
            
            # 排除其他可能不需要的模块
            "--exclude-module=tkinter",
            "--exclude-module=Tkinter",
            "--exclude-module=matplotlib.backends.backend_tkagg",
            "--exclude-module=matplotlib.backends.backend_webagg",
            "--exclude-module=matplotlib.backends.backend_qt4agg",
            "--exclude-module=IPython",
            "--exclude-module=jupyter",
            "--exclude-module=notebook",
            "--exclude-module=pytest",
            "--exclude-module=test",
            "--exclude-module=doctest",
            "--exclude-module=distutils",
            "--exclude-module=setuptools",
            "--exclude-module=pkg_resources",
            "src/main.py"
        ]
        
    
    try:
        print("正在执行PyInstaller...")
        # 直接运行命令，不使用进度条避免死循环
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("\n构建成功!")
        print("可执行文件已生成: dist/pandapower_sim.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n构建过程中发生异常: {e}")
        return False


def copy_assets():
    """复制资源文件到dist目录"""
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("\ndist目录不存在，构建可能失败")
        return False
    
    # 确保资源文件被正确复制
    assets_src = Path('src/assets')
    if assets_src.exists():
        asset_files = list(assets_src.glob('*'))
        
        print(f"复制资源文件... ({len(asset_files)} 个文件)")
        assets_dst = dist_dir / 'assets'
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        assets_dst.mkdir(exist_ok=True)
        
        for asset_file in asset_files:
            if asset_file.is_file():
                shutil.copy2(asset_file, assets_dst / asset_file.name)
        
        print(f"资源文件复制完成")
    else:
        print("\n未找到资源文件目录")
    
    return True


def main():
    """主函数"""
    print("=== PandaPower仿真器打包工具 ===")
    
    # 1. 检查conda环境
    print("\n[1/5] 检查conda环境...")
    check_conda_env()
    
    # 2. 检查PyInstaller
    print("\n[2/5] 检查PyInstaller...")
    if not check_pyinstaller():
        return False
    
    # 3. 清理构建文件
    print("\n[3/5] 清理构建文件...")
    clean_build()
    
    # 4. 构建可执行文件
    print("\n[4/5] 构建可执行文件...")
    if not build_executable():
        return False
    
    # 5. 复制资源文件
    print("\n[5/5] 复制资源文件...")
    if not copy_assets():
        return False
    
    print("\n" + "="*50)
    print("打包完成!")
    print("="*50)
    print("可执行文件位置: dist/pandapower_sim.exe")
    print("您可以将整个dist文件夹分发给用户")
    print("="*50)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)