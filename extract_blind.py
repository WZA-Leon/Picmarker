"""
Picmarker V1.3 - 盲水印提取命令行工具
用法: python extract_blind.py <图片路径> [--pwd 密码]
默认密码: 123456
"""
import argparse
import sys
from pathlib import Path


def extract_blind(image_path: str, password: str = "123456") -> str:
    """从图片中提取盲水印"""
    from hidden_watermark import DWTWatermark

    path = Path(image_path)
    if not path.exists():
        print(f"文件不存在: {image_path}")
        sys.exit(1)

    bw = DWTWatermark(password=int(password))
    return bw.extract(str(path))


def main():
    parser = argparse.ArgumentParser(description="Picmarker 盲水印提取工具")
    parser.add_argument("image", help="要提取盲水印的图片路径")
    parser.add_argument("--pwd", default="123456", help="密码 (默认: 123456)")
    args = parser.parse_args()

    result = extract_blind(args.image, args.pwd)
    print("提取成功")
    print(f"图片: {args.image}")
    print(f"内容: {result}")


if __name__ == "__main__":
    main()
