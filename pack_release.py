#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包发布脚本
用于自动更新版本号、调用build.py构建项目并创建ZIP压缩包
"""

import os
import sys
import re
import subprocess
import shutil
from pathlib import Path
import argparse
from datetime import datetime
import time

# 尝试导入tqdm进度条库
try:
    from tqdm import tqdm
except ImportError:
    # 如果tqdm库不可用，定义一个简单的模拟进度条类
    class tqdm:
        def __init__(self, iterable=None, total=None, desc='', unit='it'):
            self.iterable = iterable
            self.total = total or len(iterable) if iterable else 0
            self.desc = desc
            self.unit = unit
            self.n = 0
            self.start_time = time.time()
            print(f"{self.desc} {self.n}/{self.total} {self.unit}", end='', flush=True)
        
        def update(self, n=1):
            self.n += n
            elapsed = time.time() - self.start_time
            rate = self.n / elapsed if elapsed > 0 else 0
            print(f"\r{self.desc} {self.n}/{self.total} {self.unit} [{elapsed:.1f}s, {rate:.1f}{self.unit}/s]", end='', flush=True)
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.time() - self.start_time
            print(f"\r{self.desc} {self.total}/{self.total} {self.unit} [{elapsed:.1f}s, {self.total/elapsed:.1f}{self.unit}/s]\n", flush=True)
        
        def __iter__(self):
            if self.iterable:
                for item in self.iterable:
                    yield item
                    self.update()


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
        # 功能更新：累加第二位，重置第三位，确保生成三位版本号
        # 确保至少有三位版本号
        while len(version_parts) < 3:
            version_parts.append(0)
        # 累加第二位
        version_parts[1] += 1
        # 重置第三位为0
        version_parts[2] = 0
        # 只保留前三位
        version_parts = version_parts[:3]
    elif update_type == "fix":
        # 修复：累加第三位，确保生成三位版本号
        # 确保至少有三位版本号
        while len(version_parts) < 3:
            version_parts.append(0)
        # 累加第三位
        version_parts[2] += 1
        # 只保留前三位
        version_parts = version_parts[:3]
    
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
                                   check=True, cwd=os.getcwd())
        print("build.py脚本执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"build.py脚本执行失败")
        return False
    except Exception as e:
        print(f"运行build.py时发生异常: {e}")
        return False

def compress(dist_dir, output_file, format="7z"):
    """将dist目录压缩成指定格式
    
    Args:
        dist_dir: 要压缩的目录路径
        output_file: 输出的压缩包路径
        format: 压缩格式，支持"zip"和"7z"
    
    Returns:
        tuple: (成功标志, 实际创建的压缩包路径)
    """
    dist_path = Path(dist_dir)
    if not dist_path.exists() or not dist_path.is_dir():
        print(f"错误: 找不到dist目录 {dist_dir}")
        return False, None
    
    # 计算文件总数用于进度条
    total_files = 0
    for root, dirs, files in os.walk(dist_dir):
        total_files += len(files)
    
    # 根据格式确保输出文件使用正确的扩展名
    if format == "7z" and not output_file.endswith(".7z"):
        output_file += ".7z"
    elif format == "zip" and not output_file.endswith(".zip"):
        output_file += ".zip"
    
    if format == "7z":
        try:
            import py7zr
            
            print(f"使用py7zr库创建7z压缩包: {output_file}")
            
            with py7zr.SevenZipFile(output_file, 'w') as z:
                # 使用进度条显示压缩进度
                with tqdm(total=total_files, desc="压缩进度", unit="文件") as pbar:
                    for root, dirs, files in os.walk(dist_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # 生成相对于dist_dir的路径
                            arcname = os.path.relpath(file_path, dist_dir)
                            z.write(file_path, arcname)
                            pbar.update(1)
            
            print(f"7z压缩包创建成功: {output_file}")
            return True, output_file
        except ImportError:
            print("错误: 找不到py7zr库，请先安装")
            return False, None
        except Exception as e:
            print(f"创建7z压缩包时出错: {e}")
            return False, None
    else:  # zip格式
        import zipfile
        
        print(f"使用Python内置zipfile模块创建ZIP压缩包: {output_file}")
        
        try:
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                # 使用进度条显示压缩进度
                with tqdm(total=total_files, desc="压缩进度", unit="文件") as pbar:
                    for root, dirs, files in os.walk(dist_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # 生成相对于dist_dir的路径
                            arcname = os.path.relpath(file_path, dist_dir)
                            zipf.write(file_path, arcname)
                            pbar.update(1)
            
            print(f"ZIP压缩包创建成功: {output_file}")
            return True, output_file
        except zipfile.BadZipFile as e:
            print(f"ZIP文件格式错误: {e}")
            return False, None
        except zipfile.LargeZipFile as e:
            print(f"ZIP文件过大错误: {e}")
            return False, None
        except IOError as e:
            print(f"I/O错误: {e}")
            return False, None
        except Exception as e:
            print(f"创建ZIP压缩包时出错: {e}")
            return False, None

def main():
    """主函数"""
    print("=== PandaPower仿真器发布打包工具 ===")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PandaPower仿真器发布打包工具')
    parser.add_argument('--type', '-t', choices=['feature', 'fix', 'none'], default='none',
                      help='更新类型: feature(功能更新)、fix(修复) 或 none(不修改版本号)')
    parser.add_argument('--format', '-f', choices=['zip', '7z'], default='7z',
                      help='压缩格式: zip 或 7z (默认: 7z)')
    args = parser.parse_args()
    
    update_type = args.type
    if update_type == 'none':
        update_type_text = "不修改版本号"
    else:
        update_type_text = "功能更新" if update_type == "feature" else "修复"
    print(f"更新类型: {update_type_text}")
    print(f"压缩格式: {args.format}")
    
    # 1. 获取当前版本号
    print("\n[1/5] 获取当前版本号...")
    current_version = get_current_version()
    if not current_version:
        print("无法继续，退出")
        return False
    print(f"当前版本号: {current_version}")
    
    # 2. 根据更新类型决定是否修改版本号
    if update_type == 'none':
        print("\n[2/5] 跳过版本号修改")
        new_version = current_version
    else:
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
        # 构建失败，如果修改了版本号则恢复
        if update_type != 'none':
            print("构建失败，恢复版本号...")
            update_main_window_version(current_version)
        print("无法继续，退出")
        return False
    
    # 5. 压缩成指定格式
    print("\n[5/5] 创建压缩包...")
    dist_dir = "dist"
    # 创建带版本号和精确到分钟的时间戳的压缩包名称
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = f"pandapower_sim_v{new_version}_{timestamp}"
    
    success, actual_output_file = compress(dist_dir, output_file, args.format)
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