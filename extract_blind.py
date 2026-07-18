"""
Picmarker V1.3 - 盲水印提取命令行工具
用法: python extract_blind.py <图片路径> [--pwd 密码]
默认密码: 123456
"""
import argparse
import os
import sys
from pathlib import Path


def extract_blind(image_path: str, password: str = "123456") -> str:
    """从图片中提取盲水印"""
    try:
        from blind_watermark import WaterMark
    except ImportError:
        print("❌ 请先安装 blind-watermark: pip install blind-watermark")
        sys.exit(1)

    from PIL import Image
    import numpy as np

    path = Path(image_path)
    if not path.exists():
        print(f"❌ 文件不存在: {image_path}")
        sys.exit(1)

    len_path = str(path) + '.len'
    if not os.path.exists(len_path):
        print(f"❌ 找不到水印长度文件: {len_path}")
        print("提示: 该图片可能未使用 Picmarker 嵌入盲水印")
        sys.exit(1)

    with open(len_path) as f:
        wm_shape = int(f.read())

    bw = WaterMark(password_img=int(password), password_wm=int(password))
    pil_img = Image.open(str(path)).convert('RGB')
    img_cv = np.array(pil_img)[:, :, ::-1]

    wm_extract = bw.extract(embed_img=img_cv, wm_shape=wm_shape, mode='str')
    return wm_extract


def main():
    parser = argparse.ArgumentParser(description="Picmarker 盲水印提取工具")
    parser.add_argument("image", help="要提取盲水印的图片路径")
    parser.add_argument("--pwd", default="123456", help="密码 (默认: 123456)")
    args = parser.parse_args()

    result = extract_blind(args.image, args.pwd)
    print(f"✅ 提取成功")
    print(f"图片: {args.image}")
    print(f"内容: {result}")


if __name__ == "__main__":
    main()
