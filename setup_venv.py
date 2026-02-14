#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
venv环境管理脚本
用于创建和管理开发环境和打包环境
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def get_python_executable():
    """获取Python可执行文件路径"""
    return sys.executable


def check_python_version():
    """检查Python版本是否符合要求（3.10）"""
    version = sys.version_info
    if version.major != 3 or version.minor != 10:
        print(f"警告: 当前Python版本为 {version.major}.{version.minor}.{version.micro}")
        print("建议使用 Python 3.10.x 版本")
        # 非交互模式下自动继续
        if sys.stdin.isatty():
            response = input("是否继续? (y/n): ")
            if response.lower() != 'y':
                return False
        else:
            print("非交互模式，自动继续...")
    else:
        print(f"Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True


def create_venv(venv_name, requirements_file):
    """创建venv环境并安装依赖"""
    venv_path = Path(venv_name)
    
    # 检查venv是否已存在
    if venv_path.exists():
        print(f"\n{venv_name} 已存在")
        # 非交互模式下自动删除并重新创建
        if sys.stdin.isatty():
            response = input("是否删除并重新创建? (y/n): ")
            if response.lower() == 'y':
                print(f"删除现有的 {venv_name}...")
                shutil.rmtree(venv_path)
            else:
                print(f"跳过创建 {venv_name}")
                return True
        else:
            print(f"非交互模式，自动删除并重新创建 {venv_name}...")
            shutil.rmtree(venv_path)
    
    print(f"\n创建 {venv_name} 环境...")
    try:
        # 创建venv
        subprocess.check_call([
            sys.executable, "-m", "venv", str(venv_path)
        ])
        print(f"{venv_name} 创建成功")
        
        # 确定pip路径（Windows和Unix不同）
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip.exe"
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"
        
        # 升级pip
        print(f"升级 {venv_name} 中的pip...")
        subprocess.check_call([
            str(python_path), "-m", "pip", "install", "--upgrade", "pip"
        ])
        
        # 安装依赖
        if Path(requirements_file).exists():
            print(f"从 {requirements_file} 安装依赖...")
            subprocess.check_call([
                str(pip_path), "install", "-r", requirements_file
            ])
            print(f"{venv_name} 依赖安装完成")
        else:
            print(f"警告: 找不到 {requirements_file}，跳过依赖安装")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"创建 {venv_name} 失败: {e}")
        return False
    except Exception as e:
        print(f"创建 {venv_name} 时发生异常: {e}")
        return False


def get_venv_python(venv_name):
    """获取venv中Python的路径"""
    venv_path = Path(venv_name)
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def activate_instructions(venv_name):
    """显示激活venv的说明"""
    print(f"\n{'='*60}")
    print(f"如何激活 {venv_name} 环境:")
    print(f"{'='*60}")
    if sys.platform == "win32":
        print(f"Windows PowerShell:")
        print(f"  .\\{venv_name}\\Scripts\\Activate.ps1")
        print(f"\nWindows CMD:")
        print(f"  {venv_name}\\Scripts\\activate.bat")
    else:
        print(f"Linux/Mac:")
        print(f"  source {venv_name}/bin/activate")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    print("=== venv环境管理工具 ===")
    print("此工具将创建开发环境:")
    print("  venv-dev - 开发环境")
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    # 创建开发环境
    print("\n" + "="*60)
    print("创建开发环境 (venv-dev)")
    print("="*60)
    if not create_venv("venv-dev", "requirements-dev.txt"):
        return False
    activate_instructions("venv-dev")
    
    print("\n" + "="*60)
    print("venv环境创建完成!")
    print("="*60)
    print("\n使用说明:")
    print("1. 开发时激活 venv-dev 环境")
    print("2. Python内核打包使用 python-kernel/requirements.txt")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

