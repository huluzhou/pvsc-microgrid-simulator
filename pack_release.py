#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包发布脚本
用于自动更新版本号、调用build.py构建项目并创建7z压缩包
"""

import os
import sys
import re
import subprocess
import shutil
from pathlib import Path
import argparse
from datetime import datetime

def get_current_version():
    """从main_window.py文件中获取当前版本号"""
    main_window_path = Path("src/components/main_window.py")
    if not main_window_path.exists():
        print(f"错误: 找不到文件 {main_window_path}")
        return None
    
    try:
        with open(main_window_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找版本号模式
            match = re.search(r'<p>版本: ([\d.]+)</p>', content)
            if match:
                return match.group(1)
            else:
                print("错误: 未在main_window.py中找到版本号")
                return None
    except Exception as e:
        print(f"读取版本号时出错: {e}")
        return None

def update_version(current_version, update_type):
    """根据更新类型更新版本号
    
    Args:
        current_version: 当前版本号，如 "1.0.6.2"
        update_type: 更新类型，"feature"表示功能更新，"fix"表示修复
    
    Returns:
        更新后的版本号
    """
    # 将版本号拆分为数字列表
    version_parts = list(map(int, current_version.split('.')))
    
    if update_type == "feature":
        # 功能更新：累加第三位，删除第四位（如果有）
        if len(version_parts) >= 3:
            version_parts[2] += 1
            # 只保留前三位
            version_parts = version_parts[:3]
        else:
            # 如果版本号少于三位，补充到三位
            while len(version_parts) < 3:
                version_parts.append(0)
            version_parts[2] += 1
    elif update_type == "fix":
        # 修复：累加第四位，如果没有第四位则添加
        if len(version_parts) >= 4:
            version_parts[3] += 1
        else:
            # 确保至少有三位，然后添加第四位
            while len(version_parts) < 3:
                version_parts.append(0)
            version_parts.append(1)
    
    # 转换回字符串
    return '.'.join(map(str, version_parts))

def update_main_window_version(new_version):
    """更新main_window.py中的版本号"""
    main_window_path = Path("src/components/main_window.py")
    if not main_window_path.exists():
        print(f"错误: 找不到文件 {main_window_path}")
        return False
    
    try:
        with open(main_window_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换版本号
        new_content = re.sub(r'<p>版本: ([\d.]+)</p>', f'<p>版本: {new_version}</p>', content)
        
        with open(main_window_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已更新main_window.py中的版本号为: {new_version}")
        return True
    except Exception as e:
        print(f"更新main_window.py版本号时出错: {e}")
        return False

def run_build_script():
    """运行build.py脚本"""
    build_script = Path("build.py")
    if not build_script.exists():
        print(f"错误: 找不到build.py脚本")
        return False
    
    print("正在运行build.py脚本...")
    try:
        result = subprocess.run([sys.executable, str(build_script)], 
                               check=True, capture_output=True, text=True)
        print("build.py脚本执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"build.py脚本执行失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"运行build.py时发生异常: {e}")
        return False

def compress_to_7z(dist_dir, output_file):
    """将dist目录压缩成7z格式，如果不可用则使用ZIP格式
    
    Returns:
        tuple: (成功标志, 实际创建的压缩包路径)
    """
    dist_path = Path(dist_dir)
    if not dist_path.exists() or not dist_path.is_dir():
        print(f"错误: 找不到dist目录 {dist_dir}")
        return False, None
    
    # 首先尝试使用py7zr库
    try:
        import py7zr
        print(f"使用py7zr库创建7z压缩包: {output_file}")
        with py7zr.SevenZipFile(output_file, 'w', filters=[{"id": py7zr.FILTER_LZMA2, "preset": 9}]) as z:
            # 添加整个目录
            z.writeall(dist_dir, os.path.basename(dist_dir))
        print(f"7z压缩包创建成功: {output_file}")
        return True, output_file
    except ImportError:
        print("警告: 未找到py7zr库，尝试其他压缩方法")
        print("提示: 可以通过 'pip install py7zr' 安装py7zr库以获得更好的7z压缩支持")
    except Exception as e:
        print(f"使用py7zr创建压缩包时出错: {e}")
    
    # 其次检查7z命令是否可用
    try:
        subprocess.run(["7z", "--help"], check=False, capture_output=True)
        has_7z = True
    except FileNotFoundError:
        has_7z = False
    
    if has_7z:
        # 使用7z命令行工具
        print(f"使用7z命令行工具创建7z压缩包: {output_file}")
        try:
            # 构建7z命令
            cmd = ["7z", "a", "-t7z", "-mx=9", output_file, str(dist_path) + "/*"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"7z压缩包创建成功: {output_file}")
            return True, output_file
        except subprocess.CalledProcessError as e:
            print(f"7z压缩失败: {e}")
            print(f"错误输出: {e.stderr}")
        except Exception as e:
            print(f"创建7z压缩包时发生异常: {e}")
    
    # 最后使用Python内置的zipfile模块作为备选
    print("尝试使用Python内置的zipfile模块")
    try:
        import zipfile
        zip_output = output_file.replace('.7z', '.zip')
        print(f"创建ZIP压缩包: {zip_output}")
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(dist_dir))
                    zipf.write(file_path, arcname)
        print(f"ZIP压缩包创建成功: {zip_output}")
        return True, zip_output
    except Exception as e:
        print(f"创建ZIP压缩包时出错: {e}")
        return False, None

def main():
    """主函数"""
    print("=== PandaPower仿真器发布打包工具 ===")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PandaPower仿真器发布打包工具')
    parser.add_argument('--type', '-t', choices=['feature', 'fix'], default='feature',
                      help='更新类型: feature(功能更新) 或 fix(修复)')
    args = parser.parse_args()
    
    update_type = args.type
    update_type_text = "功能更新" if update_type == "feature" else "修复"
    print(f"更新类型: {update_type_text}")
    
    # 1. 获取当前版本号
    print("\n[1/5] 获取当前版本号...")
    current_version = get_current_version()
    if not current_version:
        print("无法继续，退出")
        return False
    print(f"当前版本号: {current_version}")
    
    # 2. 计算新版本号
    print("\n[2/5] 计算新版本号...")
    new_version = update_version(current_version, update_type)
    print(f"新版本号: {new_version}")
    
    # 3. 更新main_window.py中的版本号
    print("\n[3/5] 更新版本号...")
    if not update_main_window_version(new_version):
        print("无法继续，退出")
        return False
    
    # 4. 运行build.py脚本
    print("\n[4/5] 构建项目...")
    if not run_build_script():
        # 构建失败，恢复版本号
        print("构建失败，恢复版本号...")
        update_main_window_version(current_version)
        print("无法继续，退出")
        return False
    
    # 5. 压缩成7z格式
    print("\n[5/5] 创建压缩包...")
    dist_dir = "dist"
    # 创建带版本号和日期的压缩包名称
    today = datetime.now().strftime("%Y%m%d")
    output_file = f"pandapower_sim_v{new_version}_{today}.7z"
    
    success, actual_output_file = compress_to_7z(dist_dir, output_file)
    if success:
        print("\n" + "="*60)
        print(f"打包发布完成!")
        print("="*60)
        print(f"版本: v{new_version}")
        print(f"压缩包: {actual_output_file}")
        print(f"构建目录: {dist_dir}")
        print("="*60)
        return True
    else:
        print("压缩包创建失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)