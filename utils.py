import os
import platform
from pathlib import Path
import exifread
import piexif
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageOps
import tkinter as tk
from tkinter import ttk, font as tkfont
import winreg  # 仅在 Windows 下使用

from config import (
    BRAND_FIX, MODEL_SHORT, BRAND_ICONS,
    WM_CFG, CAMERA_DB
)

# 兼容旧版 PIL
try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS


def apply_exif_orientation(img):
    """根据 EXIF Orientation 信息旋转图片，使竖拍照片正确显示"""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


class ExifReader:
    @staticmethod
    def _safe_str(val):
        return str(val).strip()
    
    @staticmethod
    def get_exif_full(image_path):
        info = {
            "make": "", "camera_model": "", "lens_model": "",
            "focal": "", "f": "", "exposure": "", "iso": "", "datetime": ""
        }
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            if 'Image Make' in tags:
                make_raw = ExifReader._safe_str(tags['Image Make']).upper()
                for orig, fixed in BRAND_FIX.items():
                    if orig in make_raw:
                        info["make"] = fixed
                        break
                else:
                    info["make"] = make_raw
            if 'Image Model' in tags:
                model = ExifReader._safe_str(tags['Image Model'])
                info["camera_model"] = MODEL_SHORT.get(model, model)
            if 'EXIF LensModel' in tags:
                info["lens_model"] = ExifReader._safe_str(tags['EXIF LensModel'])
            if 'EXIF FocalLength' in tags:
                fl = tags['EXIF FocalLength']
                try:
                    fl_val = float(fl.values[0]) if hasattr(fl, 'values') else float(fl)
                except:
                    fl_val = str(fl)
                info["focal"] = f"{fl_val}mm"
            if 'EXIF FNumber' in tags:
                fn = tags['EXIF FNumber']
                try:
                    fn_val = float(fn.values[0]) if hasattr(fn, 'values') else float(fn)
                except:
                    fn_val = str(fn)
                info["f"] = f"f/{fn_val}"
            if 'EXIF ExposureTime' in tags:
                et = tags['EXIF ExposureTime']
                try:
                    et_val = float(et.values[0]) if hasattr(et, 'values') else float(et)
                    if et_val >= 1:
                        info["exposure"] = f"{et_val}s"
                    else:
                        info["exposure"] = f"1/{int(1/et_val)}s"
                except:
                    info["exposure"] = str(et)
            if 'EXIF ISOSpeedRatings' in tags:
                iso = str(tags['EXIF ISOSpeedRatings'])
                info["iso"] = f"ISO{iso}" if not iso.startswith("ISO") else iso
            if 'EXIF DateTimeOriginal' in tags:
                dt = str(tags['EXIF DateTimeOriginal']).replace(":", "-", 2)
                info["datetime"] = dt
        except:
            pass
        return info


class FontManager:
    @staticmethod
    def get_system_fonts():
        try:
            import tkinter as tk
            from tkinter import font as tkfont
            root = tk.Tk()
            root.withdraw()
            families = sorted(tkfont.families())
            root.destroy()
        except:
            families = ["Arial", "Microsoft YaHei", "SimHei", "SimSun"]
        # 过滤 @ 开头的竖排变体、粗体/斜体/细体等变体
        skip = ["bold", "black", "italic", "light", "medium",
                "semibold", "thin", "regular", "oblique"]
        result = []
        for f in families:
            if f.startswith("@"):
                continue
            if any(k in f.lower() for k in skip):
                continue
            result.append(f)
        return sorted(list(set(result)))


class WatermarkGenerator:
    # 字体缓存：相同字体名+字号只加载一次，提升预览性能
    _font_cache = {}

    # 中文字体显示名 -> 注册表英文名映射（仅注册表里是英文名的字体）
    _CN_FONT_MAP = {
        "宋体": "SimSun", "新宋体": "SimSun", "黑体": "SimHei",
        "楷体": "KaiTi", "仿宋": "FangSong", "等线": "DengXian",
        "微软雅黑": "Microsoft YaHei",
    }

    @staticmethod
    def get_font(name, size, bold=False):
        cache_key = (name.lower(), size, bold)
        if cache_key in WatermarkGenerator._font_cache:
            return WatermarkGenerator._font_cache[cache_key]

        # 中文字体显示名映射到注册表英文名，便于匹配
        name = WatermarkGenerator._CN_FONT_MAP.get(name.strip(), name)

        # 通过注册表枚举系统字体，优先选择中文字体
        cn_keywords = ["yahei", "msyh", "simsun", "simhei", "dengxian",
                       "kaiti", "fangsong", "song", "hei", "kai", "fang"]
        bold_keywords = ["bold", "bd", "粗体", "黑体"]
        try:
            if platform.system() == "Windows":
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                i = 0
                cn_candidates = []
                bold_candidates = []
                while True:
                    try:
                        fname, fpath, _ = winreg.EnumValue(key, i)
                        if ".ttf" in fpath.lower() or ".ttc" in fpath.lower():
                            full_path = os.path.join("C:/Windows/Fonts", fpath)
                            if os.path.exists(full_path):
                                # 优先匹配用户选择的字体名
                                clean = fname.split(" (TrueType)")[0].split(" (OpenType)")[0]
                                # 去掉粗体/斜体等变体后缀，便于与用户选择的字体名匹配
                                clean_base = clean
                                for kw in bold_keywords + ["italic", "oblique", "regular", "light", "medium", "semibold", "thin"]:
                                    clean_base = clean_base.replace(kw, "").replace(kw.capitalize(), "")
                                clean_base = clean_base.strip()
                                nl = name.lower()
                                cl = clean_base.lower()
                                # 精确匹配，或前缀匹配（如 "Microsoft YaHei" 匹配 "Microsoft YaHei & Microsoft YaHei UI"）
                                if nl == cl or cl.startswith(nl) or nl.startswith(cl):
                                    # 加粗时优先用粗体变体
                                    if bold and any(k in fname.lower() for k in bold_keywords):
                                        font = ImageFont.truetype(full_path, size)
                                        WatermarkGenerator._font_cache[cache_key] = font
                                        return font
                                    if not bold:
                                        font = ImageFont.truetype(full_path, size)
                                        WatermarkGenerator._font_cache[cache_key] = font
                                        return font
                                # 收集中文字体作为候选
                                if any(k in fname.lower() for k in cn_keywords):
                                    if bold and any(k in fname.lower() for k in bold_keywords):
                                        bold_candidates.append(full_path)
                                    cn_candidates.append(full_path)
                        i += 1
                    except:
                        break
                # 加粗时优先用粗体中文字体
                if bold:
                    for full_path in bold_candidates:
                        try:
                            font = ImageFont.truetype(full_path, size)
                            WatermarkGenerator._font_cache[cache_key] = font
                            return font
                        except:
                            continue
                # 用户字体未找到时，优先用中文字体
                for full_path in cn_candidates:
                    try:
                        font = ImageFont.truetype(full_path, size)
                        WatermarkGenerator._font_cache[cache_key] = font
                        return font
                    except:
                        continue
        except:
            pass

        # 回退：直接按名字加载
        try:
            font = ImageFont.truetype(name, size)
            WatermarkGenerator._font_cache[cache_key] = font
            return font
        except:
            pass
        font_paths = [
            f"C:\\Windows\\Fonts\\{name}.ttf",
            f"C:\\Windows\\Fonts\\{name}.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        if bold:
            font_paths = [
                "C:\\Windows\\Fonts\\msyhbd.ttc",
                "C:\\Windows\\Fonts\\simhei.ttf",
                f"C:\\Windows\\Fonts\\{name}.ttf",
                f"C:\\Windows\\Fonts\\{name}.ttc",
                "C:\\Windows\\Fonts\\arial.ttf",
            ]
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                WatermarkGenerator._font_cache[cache_key] = font
                return font
            except:
                continue
        font = ImageFont.load_default()
        WatermarkGenerator._font_cache[cache_key] = font
        return font

    @staticmethod
    def resize_by_height(img, target_h):
        w, h = img.size
        ratio = target_h / h
        return img.resize((int(w * ratio), target_h), RESAMPLE)

    @staticmethod
    def load_brand_icon(brand):
        icon_dir = Path(__file__).parent / "icons"
        icon_dir.mkdir(exist_ok=True)
        icon_file = BRAND_ICONS.get(brand, None)
        if icon_file:
            icon_path = icon_dir / icon_file
            if icon_path.exists():
                return Image.open(icon_path).convert("RGBA")
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    # ========== 核心：纯渲染方法（预览+正式生成 100% 共用） ==========
    @staticmethod
    def render_border(img: Image.Image, data: dict, font_name: str, bold: bool = False) -> Image.Image:
        img = img.convert("RGB")
        w, h = img.size

        # 全局唯一缩放系数：所有元素全部基于图片宽度等比缩放
        scale = w / WM_CFG["base_width"]

        # 边框高度：等比缩放 + 上下限安全保护
        bar_h = int(WM_CFG["base_bar_height"] * scale)
        bar_h = max(20, min(bar_h, int(w / 5)))

        bg = tuple(WM_CFG["background_color"])
        icon_left = int(WM_CFG["icon_margin_left"] * scale)
        icon_right = int(WM_CFG["icon_margin_right"] * scale)

        # 创建带边框的新画布
        new_img = Image.new("RGB", (w, h + bar_h), bg)
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)

        # 字体、描边：统一乘缩放系数
        fc = WM_CFG["fonts"]
        colors = WM_CFG["colors"]
        stroke_en = WM_CFG["stroke"]["enabled"]
        stroke_w = max(0, int(WM_CFG["stroke"]["width"] * scale)) if stroke_en else 0
        stroke_c = tuple(WM_CFG["stroke"]["fill"]) if stroke_en else None

        font_cam = WatermarkGenerator.get_font(font_name, max(1, int(fc["camera"] * scale)), bold)
        font_len = WatermarkGenerator.get_font(font_name, max(1, int(fc["lens"] * scale)), bold)
        font_name_f = WatermarkGenerator.get_font(font_name, max(1, int(fc["name"] * scale)), bold)
        font_param = WatermarkGenerator.get_font(font_name, max(1, int(fc["params"] * scale)), bold)
        font_time = WatermarkGenerator.get_font(font_name, max(1, int(fc["time"] * scale)), bold)

        # 图标：统一乘 scale + 宽高双重限制，防止超出边框
        icon = WatermarkGenerator.load_brand_icon(data["brand"])
        # 先按缩放系数等比缩放
        icon_h = max(1, int(icon.height * scale))
        icon_w = max(1, int(icon.width * scale))
        icon = icon.resize((icon_w, icon_h), RESAMPLE)

        # 限制最大宽度
        max_icon_w = int(w / 5)
        if icon.width > max_icon_w:
            new_h = max(1, int(icon.height * max_icon_w / icon.width))
            icon = icon.resize((max_icon_w, new_h), RESAMPLE)

        # 新增：限制最大高度，不超过边框高度的85%，避免上下溢出
        max_icon_h = int(bar_h * 0.85)
        if icon.height > max_icon_h:
            new_w = max(1, int(icon.width * max_icon_h / icon.height))
            icon = icon.resize((new_w, max_icon_h), RESAMPLE)

        # 图标垂直居中
        icon_y = h + (bar_h - icon.height) // 2
        new_img.paste(icon, (icon_left, icon_y), icon)
        left_x = icon_left + icon.width + icon_right

        # 文字排版：偏移量统一乘缩放系数
        left_cfg = WM_CFG["left_text"]
        right_cfg = WM_CFG["right_text"]

        cam_text = data["camera"]
        lens_text = data["lens"]
        param_text = f"{data['focal']}  {data['f']}  {data['exp']}  {data['iso']}"
        time_text = f"{data['datetime']}"

        def _bbox(text, font):
            b = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
            return b[1], b[3]

        cam_t, cam_b = _bbox(cam_text, font_cam)
        lens_t, lens_b = _bbox(lens_text, font_len)
        param_t, param_b = _bbox(param_text, font_param)
        time_t, time_b = _bbox(time_text, font_time)

        # 左侧整体垂直居中
        left_gap = int(left_cfg["lens"]["y"] * scale) - int(left_cfg["camera"]["y"] * scale)
        # 仅保留最小间距保护，不再强制压缩上限，保证配置的间距完整生效
        left_gap = max(left_gap, int(8 * scale))
        left_h = (lens_b + left_gap) - cam_t
        bar_center = h + bar_h // 2
        left_base = bar_center - left_h // 2 - cam_t

        draw.text(
            (left_x + int(left_cfg["camera"]["x_offset"] * scale), left_base),
            cam_text, fill=tuple(colors["camera"]), font=font_cam,
            stroke_width=stroke_w, stroke_fill=stroke_c
        )
        draw.text(
            (left_x + int(left_cfg["lens"]["x_offset"] * scale), left_base + left_gap),
            lens_text, fill=tuple(colors["lens"]), font=font_len,
            stroke_width=stroke_w, stroke_fill=stroke_c
        )

        # 右侧右对齐 + 垂直居中
        param_w = draw.textlength(param_text, font=font_param)
        time_w = draw.textlength(time_text, font=font_time)
        param_x = w + int(right_cfg["params"]["x_offset"] * scale) - param_w
        time_x = w + int(right_cfg["time"]["x_offset"] * scale) - time_w

        right_gap = int(right_cfg["time"]["y"] * scale) - int(right_cfg["params"]["y"] * scale)
        right_gap = max(right_gap, int(8 * scale))
        right_h = (time_b + right_gap) - param_t
        right_base = bar_center - right_h // 2 - param_t

        draw.text(
            (param_x, right_base), param_text,
            fill=tuple(colors["params"]), font=font_param,
            stroke_width=stroke_w, stroke_fill=stroke_c
        )
        draw.text(
            (time_x, right_base + right_gap), time_text,
            fill=tuple(colors["time"]), font=font_time,
            stroke_width=stroke_w, stroke_fill=stroke_c
        )

        return new_img

    # ========== 正式生成方法：仅负责IO与EXIF，渲染复用 render_border ==========
    @staticmethod
    def add_watermark(img_path, out_path, data, font_name, bold=False):
        # 读取图片并校正方向
        img = apply_exif_orientation(Image.open(img_path))

        # 调用统一渲染核心（与预览使用完全相同的算法）
        result_img = WatermarkGenerator.render_border(img, data, font_name, bold)

        # 只要图片有EXIF，就强制原样保留，不做任何修改
        exif_bytes = None
        try:
            exif_dict = piexif.load(img_path)
            # 强制：只要load成功且非空，就原样dump传回，不管内容是什么
            if exif_dict:
                exif_bytes = piexif.dump(exif_dict)
        except Exception as e:
            print(f"EXIF读取失败 ({os.path.basename(img_path)}): {e}")

        # 保存图片（有EXIF时直接携带原EXIF，避免二次插入冲突）
        if exif_bytes:
            result_img.save(out_path, quality=95, exif=exif_bytes)
        else:
            result_img.save(out_path, quality=95)
            
class CollapsiblePanel(ttk.Frame):
    def __init__(self, parent, title, expanded=False):
        super().__init__(parent)
        self.is_expanded = expanded
        self.title_text = title
        arrow = "▲" if expanded else "▼"
        self.title_btn = ttk.Button(self, text=f"{arrow} {title}", command=self.toggle)
        self.title_btn.pack(fill="x", pady=2)
        self.content = ttk.Frame(self)
        if expanded:
            self.content.pack(fill="x", padx=2, pady=3)

    def toggle(self):
        if self.is_expanded:
            self.content.pack_forget()
            self.title_btn.config(text=f"▼ {self.title_text}")
        else:
            self.content.pack(fill="x", padx=2, pady=3)
            self.title_btn.config(text=f"▲ {self.title_text}")
        self.is_expanded = not self.is_expanded
        self.update_idletasks()