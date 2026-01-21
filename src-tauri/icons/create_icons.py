#!/usr/bin/env python3
"""创建有效的 PNG 图标文件"""
try:
    from PIL import Image, ImageDraw
    
    def create_icon(size, filename):
        """创建指定大小的图标"""
        img = Image.new('RGBA', (size, size), (59, 130, 246, 255))  # 蓝色背景
        draw = ImageDraw.Draw(img)
        # 绘制一个简单的圆形图标
        margin = size // 8
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=(255, 255, 255, 255))
        # 绘制一个简单的符号（闪电）
        if size >= 32:
            center = size // 2
            points = [
                (center - size//6, center - size//4),
                (center, center - size//8),
                (center - size//8, center),
                (center + size//6, center + size//4),
                (center, center + size//8),
                (center + size//8, center),
            ]
            draw.polygon(points, fill=(59, 130, 246, 255))
        img.save(filename, 'PNG')
        print(f'Created {filename} ({size}x{size})')
    
    # 创建所有需要的图标
    create_icon(32, '32x32.png')
    create_icon(128, '128x128.png')
    create_icon(256, '128x128@2x.png')
    print('All icons created successfully')
    
except ImportError:
    print('PIL (Pillow) not installed. Installing...')
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'Pillow'])
    print('Please run this script again')
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
