#!/usr/bin/env python3
"""
生成 PWA 图标
基于医疗问答 Logo 样式：深蓝背景 + 青绿十字 + 金色圆环
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 创建 icons 目录
os.makedirs(os.path.dirname(__file__), exist_ok=True)

# 图标尺寸
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size):
    """创建医疗主题图标"""
    # 创建图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色定义
    bg_color = (30, 35, 60)  # 深蓝背景
    cross_color = (0, 200, 180)  # 青绿色十字
    ring_color = (200, 170, 100)  # 金色圆环
    
    # 绘制背景（圆角矩形）
    padding = size // 20
    corner_radius = size // 8
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=bg_color
    )
    
    # 绘制外圆环
    center = size // 2
    ring_radius = int(size * 0.35)
    ring_width = max(2, size // 40)
    draw.ellipse(
        [center - ring_radius, center - ring_radius,
         center + ring_radius, center + ring_radius],
        outline=ring_color,
        width=ring_width
    )
    
    # 绘制内圆环
    inner_ring_radius = int(size * 0.28)
    draw.ellipse(
        [center - inner_ring_radius, center - inner_ring_radius,
         center + inner_ring_radius, center + inner_ring_radius],
        outline=ring_color,
        width=ring_width
    )
    
    # 绘制十字（医疗符号）
    cross_size = int(size * 0.18)
    cross_thickness = max(4, size // 15)
    
    # 垂直线
    draw.rounded_rectangle(
        [center - cross_thickness // 2, center - cross_size,
         center + cross_thickness // 2, center + cross_size],
        radius=cross_thickness // 4,
        fill=cross_color
    )
    # 水平线
    draw.rounded_rectangle(
        [center - cross_size, center - cross_thickness // 2,
         center + cross_size, center + cross_thickness // 2],
        radius=cross_thickness // 4,
        fill=cross_color
    )
    
    # 绘制对话气泡（简化版）
    bubble_color = (60, 70, 100, 180)  # 半透明深蓝灰
    
    # 左侧气泡
    bubble_size = size // 8
    left_bubble_x = center - int(size * 0.22)
    left_bubble_y = center - int(size * 0.08)
    draw.rounded_rectangle(
        [left_bubble_x - bubble_size, left_bubble_y - bubble_size // 2,
         left_bubble_x + bubble_size, left_bubble_y + bubble_size // 2],
        radius=bubble_size // 4,
        fill=bubble_color
    )
    # 气泡小尾巴
    draw.polygon([
        (left_bubble_x - bubble_size + bubble_size // 4, left_bubble_y + bubble_size // 2),
        (left_bubble_x - bubble_size, left_bubble_y + bubble_size // 2 + bubble_size // 3),
        (left_bubble_x - bubble_size + bubble_size // 2, left_bubble_y + bubble_size // 2),
    ], fill=bubble_color)
    
    # 右侧气泡
    right_bubble_x = center + int(size * 0.22)
    right_bubble_y = center + int(size * 0.08)
    draw.rounded_rectangle(
        [right_bubble_x - bubble_size, right_bubble_y - bubble_size // 2,
         right_bubble_x + bubble_size, right_bubble_y + bubble_size // 2],
        radius=bubble_size // 4,
        fill=bubble_color
    )
    # 气泡小尾巴
    draw.polygon([
        (right_bubble_x + bubble_size - bubble_size // 4, right_bubble_y - bubble_size // 2),
        (right_bubble_x + bubble_size, right_bubble_y - bubble_size // 2 - bubble_size // 3),
        (right_bubble_x + bubble_size - bubble_size // 2, right_bubble_y - bubble_size // 2),
    ], fill=bubble_color)
    
    # 添加装饰点（模拟原图的星星点）
    dot_color = ring_color
    dot_positions = [
        (center, int(size * 0.08)),  # 顶部
        (int(size * 0.92), center),  # 右侧
        (center, int(size * 0.92)),  # 底部
        (int(size * 0.08), center),  # 左侧
    ]
    dot_radius = max(2, size // 50)
    for dx, dy in dot_positions:
        draw.ellipse(
            [dx - dot_radius, dy - dot_radius,
             dx + dot_radius, dy + dot_radius],
            fill=dot_color
        )
    
    return img

def main():
    print("开始生成 PWA 图标...")
    
    for size in SIZES:
        img = create_icon(size)
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        img.save(filepath, "PNG")
        print(f"✓ 生成: {filename}")
    
    # 生成 favicon.ico (多尺寸)
    favicon_sizes = [16, 32, 48]
    favicon_images = [create_icon(s) for s in favicon_sizes]
    favicon_path = os.path.join(os.path.dirname(__file__), "..", "favicon.ico")
    favicon_images[0].save(
        favicon_path,
        "ICO",
        sizes=[(s, s) for s in favicon_sizes],
        append_images=favicon_images[1:]
    )
    print(f"✓ 生成: favicon.ico")
    
    # 生成 apple-touch-icon.png (180x180)
    apple_icon = create_icon(180)
    apple_path = os.path.join(os.path.dirname(__file__), "..", "apple-touch-icon.png")
    apple_icon.save(apple_path, "PNG")
    print(f"✓ 生成: apple-touch-icon.png")
    
    print("\n图标生成完成！")
    print(f"位置: {os.path.dirname(__file__)}")

if __name__ == "__main__":
    main()
