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
from pathlib import Path


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
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))


def build_executable():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 使用简化的PyInstaller命令，避免复杂的spec文件配置问题
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed", 
        "--name=pandapower_sim",
        "--add-data=src/assets;assets",
        "src/main.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功!")
        print("可执行文件已生成: dist/pandapower_sim.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def copy_assets():
    """复制资源文件到dist目录"""
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("dist目录不存在，构建可能失败")
        return False
    
    # 确保资源文件被正确复制
    assets_src = Path('src/assets')
    if assets_src.exists():
        assets_dst = dist_dir / 'assets'
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
        print("资源文件复制完成")
    
    return True


def main():
    """主函数"""
    print("=== PandaPower仿真器打包工具 ===")
    
    # 检查conda环境
    check_conda_env()
    
    # 检查PyInstaller
    if not check_pyinstaller():
        return False
    
    # 清理构建文件
    clean_build()
    
    # 构建可执行文件
    if not build_executable():
        return False
    
    # 复制资源文件
    if not copy_assets():
        return False
    
    print("\n=== 打包完成 ===")
    print("可执行文件位置: dist/PandaPowerSim.exe")
    print("您可以将整个dist文件夹分发给用户")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)