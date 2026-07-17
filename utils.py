import os
import platform
from pathlib import Path
import exifread
import piexif
from PIL import Image, ImageDraw, ImageFont, ImageTk
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
        fonts = []
        try:
            if platform.system() == "Windows":
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                i = 0
                while True:
                    try:
                        name, path, _ = winreg.EnumValue(key, i)
                        if ".ttf" in path or ".ttc" in path:
                            fonts.append(name.split(" (TrueType)")[0])
                        i += 1
                    except:
                        break
            else:
                fonts = ["Arial", "Sans", "PingFang", "Microsoft YaHei"]
        except:
            fonts = ["Microsoft YaHei", "Arial", "Sans"]
        return sorted(list(set(fonts)))


class WatermarkGenerator:
    @staticmethod
    def get_font(name, size):
        # 实现同原代码，放在 utils 中
        try:
            if platform.system() == "Windows":
                font_paths = [
                    f"C:/Windows/Fonts/{name}.ttc",
                    f"C:/Windows/Fonts/{name}.ttf",
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/msyhbd.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/arial.ttf"
                ]
                for p in font_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                i = 0
                while True:
                    try:
                        fname, fpath, _ = winreg.EnumValue(key, i)
                        if name.lower() in fname.lower():
                            full_path = os.path.join("C:/Windows/Fonts", fpath)
                            if os.path.exists(full_path):
                                return ImageFont.truetype(full_path, size)
                        i += 1
                    except:
                        break
            else:
                for p in [
                    f"/System/Library/Fonts/{name}.ttc",
                    "/System/Library/Fonts/PingFang.ttc",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                ]:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
        except:
            pass
        return ImageFont.load_default()

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
                icon = Image.open(icon_path).convert("RGBA")
                max_h = WM_CFG.get("icon_max_height", 140)
                return WatermarkGenerator.resize_by_height(icon, max_h)
        return Image.new("RGBA", (1, WM_CFG.get("icon_max_height", 140)), (0, 0, 0, 0))

    @staticmethod
    def add_watermark(img_path, out_path, data, font_name):
        # 完整实现，与原始代码完全一致
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        bar_h = WM_CFG["bar_height"]
        bg = tuple(WM_CFG["background_color"])
        bg = tuple(WM_CFG["background_color"])
        icon_left = WM_CFG["icon_margin_left"]
        icon_right = WM_CFG["icon_margin_right"]
        v_off = WM_CFG["vertical_center_offset"]
        new_img = Image.new("RGB", (w, h + bar_h), bg)
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        fc = WM_CFG["fonts"]
        colors = WM_CFG["colors"]
        stroke_en = WM_CFG["stroke"]["enabled"]
        stroke_w = WM_CFG["stroke"]["width"] if stroke_en else 0
        stroke_c = tuple(WM_CFG["stroke"]["fill"]) if stroke_en else None
        font_cam = WatermarkGenerator.get_font(font_name, fc["camera"])
        font_len = WatermarkGenerator.get_font(font_name, fc["lens"])
        font_name_f = WatermarkGenerator.get_font(font_name, fc["name"])
        font_param = WatermarkGenerator.get_font(font_name, fc["params"])
        font_time = WatermarkGenerator.get_font(font_name, fc["time"])
        icon = WatermarkGenerator.load_brand_icon(data["brand"])
        icon_y = h + (bar_h - icon.height)//2
        new_img.paste(icon, (icon_left, icon_y), icon)
        left_x = icon_left + icon.width + icon_right
        base_y = h + (bar_h//2) - v_off
        left_cfg = WM_CFG["left_text"]
        cam_pos = (left_x + left_cfg["camera"]["x_offset"], base_y + left_cfg["camera"]["y"])
        draw.text(cam_pos, data["camera"], fill=tuple(colors["camera"]), font=font_cam,
                  stroke_width=stroke_w, stroke_fill=stroke_c)
        lens_pos = (left_x + left_cfg["lens"]["x_offset"], base_y + left_cfg["lens"]["y"])
        draw.text(lens_pos, data["lens"], fill=tuple(colors["lens"]), font=font_len,
                  stroke_width=stroke_w, stroke_fill=stroke_c)
        if data["photo_name"]:
            name_pos = (left_x + left_cfg["name"]["x_offset"], base_y + left_cfg["name"]["y"])
            draw.text(name_pos, data["photo_name"], fill=tuple(colors["name"]), font=font_name_f,
                      stroke_width=stroke_w, stroke_fill=stroke_c)
        right_cfg = WM_CFG["right_text"]
        param_text = f"{data['focal']}  {data['f']}  {data['exp']}  {data['iso']}"
        time_text = f"{data['datetime']}"
        if data['location']:
            time_text += f" | {data['location']}"
        param_w = draw.textlength(param_text, font=font_param)
        time_w = draw.textlength(time_text, font=font_time)
        param_x = w + right_cfg["params"]["x_offset"] - param_w
        time_x = w + right_cfg["time"]["x_offset"] - time_w
        draw.text((param_x, base_y + right_cfg["params"]["y"]), param_text,
                  fill=tuple(colors["params"]), font=font_param,
                                    stroke_width=stroke_w, stroke_fill=stroke_c)
        draw.text((time_x, base_y + right_cfg["time"]["y"]), time_text,
                  fill=tuple(colors["time"]), font=font_time,
                  stroke_width=stroke_w, stroke_fill=stroke_c)
        new_img.save(out_path, quality=95)
        try:
            exif_dict = piexif.load(img_path)
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, out_path)
        except Exception as e:
            print(f"EXIF保存失败 ({os.path.basename(img_path)}): {e}")


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