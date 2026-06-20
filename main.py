"""
相机水印工具 v2.3 - 完整修复版
- 所有参数输入框可编辑
- 自动预览正常工作
- EXIF智能识别
- 文字不重叠
- 支持手动修改任何参数
- 保存原始EXIF到输出图片
- 更多品牌图标关联
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import exifread
import threading
from pathlib import Path
import platform
import json
import piexif
import shutil

# ==================== 全局配置加载 ====================
SETTINGS_PATH = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "gui": {
        "font_family": "Microsoft YaHei",
        "font_size": 10,
        "title_font_size": 11,
        "window_size": "1200x900",
        "preview_auto_refresh": True,
    },
    "watermark": {
        "bar_height": 280,
        "background_color": [255, 255, 255],
        "icon_max_height": 140,
        "icon_margin_left": 40,
        "icon_margin_right": 40,
        "vertical_center_offset": 30,
        "left_text": {
            "camera": {"x_offset": 0, "y": -40},
            "lens": {"x_offset": 0, "y": 10},
            "name": {"x_offset": 0, "y": 60}
        },
        "right_text": {
            "params": {"x_offset": -40, "y": -40},
            "time": {"x_offset": -40, "y": 10}
        },
        "fonts": {
            "camera": 56,
            "lens": 44,
            "name": 48,
            "params": 56,
            "time": 44
        },
        "colors": {
            "camera": [0, 0, 0],
            "lens": [80, 80, 80],
            "name": [30, 30, 30],
            "params": [0, 0, 0],
            "time": [80, 80, 80]
        },
        "stroke": {
            "enabled": True,
            "width": 3,
            "fill": [255, 255, 255]
        }
    },
    "brand_icons": {
        "FUJIFILM": "fujifilm.png",
        "Canon": "canon.png",
        "NIKON": "nikon.png",
        "SONY": "sony.png",
        "Panasonic": "panasonic.png",
        "Olympus": "olympus.png",
        "Leica": "leica.png",
        "Hasselblad": "hasselblad.png",
        "DJI": "dji.png",
        "GoPro": "gopro.png"
    },
    "model_short_names": {
        "NIKON Z30": "Z30",
        "NIKON Z50": "Z50",
        "NIKON Z6": "Z6",
        "NIKON Z7": "Z7",
        "CANON EOS R5": "EOS R5",
        "SONY ILCE-7M3": "A7 III"
    },
    "brand_fix_map": {
        "NIKON CORPORATION": "NIKON",
        "NIKON CORP": "NIKON",
        "FUJIFILM": "FUJIFILM",
        "CANON": "Canon",
        "SONY": "SONY"
    },
    "camera_database": {
        "NIKON": {
            "cameras": ["Z30", "Z50", "Z6", "Z7", "Z8", "Z9", "D850", "D750"],
            "lenses": [
                "NIKKOR Z DX 16-50mm f/3.5-6.3 VR",
                "NIKKOR Z DX 18-140mm f/3.5-6.3 VR",
                "NIKKOR Z 24-70mm f/4 S",
                "NIKKOR Z 50mm f/1.8 S"
            ]
        },
        "Canon": {
            "cameras": ["EOS R5", "EOS R6", "EOS 5D Mark IV"],
            "lenses": ["RF 24-105mm f/4L IS USM", "EF 50mm f/1.8 STM"]
        },
        "SONY": {
            "cameras": ["A7 III", "A7 IV", "A7R V", "A6400"],
            "lenses": ["FE 24-70mm f/2.8 GM", "E 18-135mm f/3.5-5.6 OSS"]
        }
    }
}

# 加载配置
if SETTINGS_PATH.exists():
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        SETTINGS = json.load(f)
    for section, values in DEFAULT_SETTINGS.items():
        if section not in SETTINGS:
            SETTINGS[section] = values
        elif isinstance(values, dict):
            for k, v in values.items():
                if k not in SETTINGS[section]:
                    SETTINGS[section][k] = v
else:
    SETTINGS = DEFAULT_SETTINGS
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(SETTINGS, f, indent=2, ensure_ascii=False)

GUI_CFG = SETTINGS["gui"]
WM_CFG = SETTINGS["watermark"]
BRAND_ICONS = SETTINGS["brand_icons"]
MODEL_SHORT = SETTINGS["model_short_names"]
BRAND_FIX = SETTINGS["brand_fix_map"]
CAMERA_DB = SETTINGS["camera_database"]

try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS

# ==================== 工具类 ====================
class FontManager:
    @staticmethod
    def get_system_fonts():
        fonts = []
        try:
            if platform.system() == "Windows":
                import winreg
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
                if model in MODEL_SHORT:
                    info["camera_model"] = MODEL_SHORT[model]
                else:
                    info["camera_model"] = model

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

class WatermarkGenerator:
    @staticmethod
    def get_font(name, size):
        try:
            if platform.system() == "Windows":
                font_paths = [
                    f"C:/Windows/Fonts/{name}.ttc",
                    f"C:/Windows/Fonts/{name}.ttf",
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/arial.ttf"
                ]
                for p in font_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
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
        return img.resize((int(w*ratio), target_h), RESAMPLE)

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
        return Image.new("RGBA", (1, WM_CFG.get("icon_max_height", 140)), (0,0,0,0))

    @staticmethod
    def add_watermark(img_path, out_path, data, font_name):
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        bar_h = WM_CFG["bar_height"]
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

                # 保存原始EXIF到输出图片
        try:
            exif_dict = piexif.load(img_path)
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, out_path)
        except Exception as e:
            print(f"EXIF保存失败 ({os.path.basename(img_path)}): {e}")

# ==================== 主程序界面 ====================
class PhotoWatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("相机水印工具 v2.3")
        self.root.geometry(GUI_CFG.get("window_size", "1200x900"))
        
        # 设置窗口最小尺寸
        self.root.minsize(1000, 700)
        
        self.input_files = []
        self.current_index = -1
        self.output_path = tk.StringVar(value=str(Path.home() / "Desktop" / "水印输出"))
        self.selected_font = tk.StringVar(value="Microsoft YaHei")
        self.font_list = FontManager.get_system_fonts()
        if self.font_list:
            if "Microsoft YaHei" in self.font_list:
                self.selected_font.set("Microsoft YaHei")
            else:
                self.selected_font.set(self.font_list[0])

        # 参数变量 - 使用 tk.StringVar 确保可编辑
        self.brand_var = tk.StringVar()
        self.camera_var = tk.StringVar()
        self.lens_var = tk.StringVar()
        self.photo_name_var = tk.StringVar()
        self.focal_var = tk.StringVar()
        self.f_var = tk.StringVar()
        self.exp_var = tk.StringVar()
        self.iso_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.loc_var = tk.StringVar()

        self._init_ui()
        Path(self.output_path.get()).mkdir(parents=True, exist_ok=True)

    def _init_ui(self):
        # 设置整体风格
        style = ttk.Style()
        style.configure(".", font=(GUI_CFG["font_family"], GUI_CFG["font_size"]))
        
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=1)
        
        # 使用 PanedWindow 实现左右分栏
        main_pw = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_pw.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)

        # ========== 左侧：文件列表 ==========
        left_frame = ttk.Frame(main_pw, width=280)
        main_pw.add(left_frame, weight=0)
        
        # 标题
        ttk.Label(left_frame, text="📁 已添加照片", 
                 font=(GUI_CFG["font_family"], GUI_CFG["title_font_size"], "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # 列表框
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, 
                                  yscrollcommand=scrollbar.set, 
                                  selectmode=tk.SINGLE,
                                  font=(GUI_CFG["font_family"], GUI_CFG["font_size"]),
                                  bg="white",
                                  selectbackground="#0078D4",
                                  activestyle="none")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        
        # 按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=8)
        ttk.Button(btn_frame, text="➕ 添加图片", command=self.select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📂 清空列表", command=self.clear_all).pack(side=tk.LEFT, padx=2)

        # ========== 右侧：预览和参数 ==========
        right_frame = ttk.Frame(main_pw)
        main_pw.add(right_frame, weight=1)

        # 输出路径
        path_frame = ttk.LabelFrame(right_frame, text="💾 输出设置")
        path_frame.pack(fill=tk.X, pady=(0, 5))
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(path_inner, text="保存路径：").pack(side=tk.LEFT)
        ttk.Entry(path_inner, textvariable=self.output_path, width=50).pack(side=tk.LEFT, padx=6)
        ttk.Button(path_inner, text="浏览...", command=self.select_out_dir).pack(side=tk.LEFT, padx=2)

        # 预览画布
        preview_frame = ttk.LabelFrame(right_frame, text="🖼 效果预览")
        preview_frame.pack(fill=tk.BOTH, expand=1, pady=(0, 5))
        
        # 预览控制按钮
        preview_ctrl = ttk.Frame(preview_frame)
        preview_ctrl.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(preview_ctrl, text="◀ 上一张", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="下一张 ▶", command=self.next_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="🔄 刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=10)
        self.preview_label = ttk.Label(preview_ctrl, text="")
        self.preview_label.pack(side=tk.LEFT, padx=10)
        
        self.canvas = tk.Canvas(preview_frame, bg="#f5f5f5", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=1, padx=4, pady=4)

        # 参数编辑区域 - 使用 LabelFrame 分组
        param_frame = ttk.LabelFrame(right_frame, text="✏️ 水印参数（可手动修改任何字段）")
        param_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 创建三个子框架，让参数布局更清晰
        # 第一行：品牌、相机、镜头
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row1, text="品牌：", width=6).pack(side=tk.LEFT)
        self.cbo_brand = ttk.Combobox(row1, textvariable=self.brand_var, 
                                      values=list(CAMERA_DB.keys()), width=12, state="normal")
        self.cbo_brand.pack(side=tk.LEFT, padx=(0, 10))
        self.cbo_brand.bind("<<ComboboxSelected>>", self.on_brand_change)
        # 允许手动输入
        self.cbo_brand.bind("<KeyRelease>", lambda e: self.on_brand_change())
        
        ttk.Label(row1, text="相机：", width=6).pack(side=tk.LEFT)
        self.cbo_cam = ttk.Combobox(row1, textvariable=self.camera_var, width=15)
        self.cbo_cam.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row1, text="镜头：", width=6).pack(side=tk.LEFT)
        self.cbo_len = ttk.Combobox(row1, textvariable=self.lens_var, width=25)
        self.cbo_len.pack(side=tk.LEFT)
        
        # 第二行：照片名、焦距、光圈、快门、ISO
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row2, text="标题：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.photo_name_var, width=12).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="焦距：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.focal_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="光圈：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.f_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="快门：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.exp_var, width=10).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="ISO：", width=4).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.iso_var, width=10).pack(side=tk.LEFT)
        
        # 第三行：时间、地点、字体
        row3 = ttk.Frame(param_frame)
        row3.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(row3, text="时间：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.time_var, width=22).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text="地点：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.loc_var, width=22).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row3, textvariable=self.selected_font, 
                                    values=self.font_list, width=20, state="readonly")
        self.font_cb.pack(side=tk.LEFT)
        self.font_cb.bind("<<ComboboxSelected>>", lambda e: self.show_preview())

                # 操作按钮
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=6)
        
        ttk.Button(action_frame, text="🔄 刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🎨 添加水印(当前)", command=self.add_watermark_current).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="⚙ 设置编辑器", command=self.open_settings_editor).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📷 水印工具", command=self.open_picmarker).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📦 批量处理(全部)", command=self.start_batch).pack(side=tk.RIGHT, padx=2)
        
        self.progress = ttk.Progressbar(right_frame, orient=tk.HORIZONTAL)
        self.progress.pack(fill=tk.X, pady=(0, 3))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)

        # 绑定窗口大小改变事件，自动调整预览
        self.canvas.bind("<Configure>", lambda e: self.root.after(200, self.show_preview))

    # ---------- 图片导航 ----------
    def prev_image(self):
        if not self.input_files:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()

    def next_image(self):
        if not self.input_files:
            return
        if self.current_index < len(self.input_files) - 1:
            self.current_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()

    # ---------- 文件操作 ----------
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择照片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.tif *.tiff"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("所有文件", "*.*")
            ]
        )
        if not files:
            return
        
        added = 0
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                added += 1
        
        if added > 0:
            self.status_var.set(f"已添加 {added} 张照片，共 {len(self.input_files)} 张")
            if self.current_index == -1:
                self.listbox.selection_set(0)
                self.current_index = 0
                self._update_preview_for_current()
            self.show_preview()

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的照片")
            return
        
        idx = sel[0]
        filename = os.path.basename(self.input_files[idx])
        
        if messagebox.askyesno("确认删除", f"确定要删除 {filename} 吗？"):
            self.listbox.delete(idx)
            del self.input_files[idx]
            
            if not self.input_files:
                self.current_index = -1
                self.canvas.delete("all")
                self.status_var.set("列表已清空")
            else:
                if self.current_index >= len(self.input_files):
                    self.current_index = len(self.input_files) - 1
                self.listbox.selection_set(self.current_index)
                self._update_preview_for_current()

    def clear_all(self):
        if self.input_files and messagebox.askyesno("确认清空", "确定要清空所有照片吗？"):
            self.input_files = []
            self.current_index = -1
            self.listbox.delete(0, tk.END)
            self.canvas.delete("all")
            self.status_var.set("列表已清空")

    def on_list_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx != self.current_index:
            self.current_index = idx
            self._update_preview_for_current()

    def _update_preview_for_current(self):
        """更新当前照片的EXIF信息并刷新预览"""
        if self.current_index < 0 or self.current_index >= len(self.input_files):
            return
        
        path = self.input_files[self.current_index]
        filename = os.path.basename(path)
        self.status_var.set(f"当前: {filename} ({self.current_index+1}/{len(self.input_files)})")
        
        # 读取EXIF并填充参数
        info = ExifReader.get_exif_full(path)
        
        self.brand_var.set(info.get("make", ""))
        self.on_brand_change()
        self.camera_var.set(info.get("camera_model", ""))
        self.lens_var.set(info.get("lens_model", ""))
        self.focal_var.set(info.get("focal", ""))
        self.f_var.set(info.get("f", ""))
        self.exp_var.set(info.get("exposure", ""))
        self.iso_var.set(info.get("iso", ""))
        self.time_var.set(info.get("datetime", ""))
        
        # 自动预览
        self.root.after(100, self.show_preview)

    def on_brand_change(self, event=None):
        """品牌改变时更新相机和镜头下拉列表"""
        brand = self.brand_var.get().strip()
        if brand in CAMERA_DB:
            cams = CAMERA_DB[brand].get("cameras", [])
            lens = CAMERA_DB[brand].get("lenses", [])
            self.cbo_cam.config(values=cams)
            self.cbo_len.config(values=lens)
        else:
            # 即使是未知品牌，也保留手动输入的可能性
            pass

    def select_out_dir(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.output_path.set(d)

    def get_data(self):
        """收集所有参数"""
        return {
            "brand": self.brand_var.get().strip(),
            "camera": self.camera_var.get().strip(),
            "lens": self.lens_var.get().strip(),
            "photo_name": self.photo_name_var.get().strip(),
            "focal": self.focal_var.get().strip(),
            "f": self.f_var.get().strip(),
            "exp": self.exp_var.get().strip(),
            "iso": self.iso_var.get().strip(),
            "datetime": self.time_var.get().strip(),
            "location": self.loc_var.get().strip()
        }

    def show_preview(self):
        """生成并显示预览"""
        if not self.input_files or self.current_index == -1:
            return
        
        try:
            os.makedirs(self.output_path.get(), exist_ok=True)
            tmp = Path(self.output_path.get()) / "_tmp_preview.jpg"
            
            WatermarkGenerator.add_watermark(
                self.input_files[self.current_index],
                str(tmp),
                self.get_data(),
                self.selected_font.get()
            )
            
            im = Image.open(tmp)
            cw = max(self.canvas.winfo_width(), 100)
            ch = max(self.canvas.winfo_height(), 100)
            
            # 计算缩放比例
            scale = min((cw-20)/im.width, (ch-20)/im.height, 1.0)
            new_size = (int(im.width*scale), int(im.height*scale))
            im = im.resize(new_size, RESAMPLE)
            
            self.preview_img = ImageTk.PhotoImage(im)
            self.canvas.delete("all")
            self.canvas.create_image(cw//2, ch//2, image=self.preview_img, anchor=tk.CENTER)
            
            # 清理临时文件
            tmp.unlink(missing_ok=True)
            
            self.preview_label.config(text=f"预览: {os.path.basename(self.input_files[self.current_index])}")
            
        except Exception as e:
            self.status_var.set(f"预览失败: {str(e)}")

    def add_watermark_current(self):
        """为当前图片单独添加水印"""
        if not self.input_files or self.current_index == -1:
            messagebox.showwarning("提示", "请先选择照片")
            return
        
        os.makedirs(self.output_path.get(), exist_ok=True)
        path = self.input_files[self.current_index]
        name = os.path.basename(path)
        out = os.path.join(self.output_path.get(), f"Watermark_{name}")
        
        try:
            WatermarkGenerator.add_watermark(path, out, self.get_data(), self.selected_font.get())
            self.status_var.set(f"✅ 已完成: {name}")
            messagebox.showinfo("完成", f"水印已保存到:\n{out}")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")

    def start_batch(self):
        """批量处理所有图片"""
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加照片")
            return
        
        if not messagebox.askyesno("确认批量处理", f"将处理 {len(self.input_files)} 张照片，是否继续？"):
            return
        
        os.makedirs(self.output_path.get(), exist_ok=True)
        data = self.get_data()
        font = self.selected_font.get()
        total = len(self.input_files)
        self.progress["maximum"] = total
        
        def worker():
            success = 0
            for i, f in enumerate(self.input_files):
                name = os.path.basename(f)
                out = os.path.join(self.output_path.get(), f"Watermark_{name}")
                try:
                    WatermarkGenerator.add_watermark(f, out, data, font)
                    success += 1
                except Exception as e:
                    pass
                
                self.progress["value"] = i + 1
                self.status_var.set(f"处理中... {i+1}/{total}")
                self.root.update()
            
            self.progress["value"] = 0
            self.status_var.set(f"✅ 完成！成功 {success}/{total}")
            messagebox.showinfo("批量处理完成", f"成功处理 {success}/{total} 张照片\n保存位置: {self.output_path.get()}")
        
        threading.Thread(target=worker, daemon=True).start()

    def open_settings_editor(self):
        """打开设置编辑器"""
        import subprocess
        editor_path = Path(__file__).parent / "edit.py"
        if editor_path.exists():
            subprocess.Popen(["python", str(editor_path)])
        else:
            messagebox.showerror("错误", f"未找到 {editor_path}")

    def open_picmarker(self):
        """打开Picmarker工具"""
        import subprocess
        marker_path = Path(__file__).parent / "Picmarker.py"
        if marker_path.exists():
            subprocess.Popen(["python", str(marker_path)])
        else:
            messagebox.showerror("错误", f"未找到 {marker_path}")

if __name__ == "__main__":
    # 检查并安装依赖
    try:
        import exifread
    except ImportError:
        print("正在安装依赖库...")
        os.system("python -m pip install Pillow exifread")
        import exifread
    
    root = tk.Tk()
    app = PhotoWatermarkApp(root)
    root.mainloop()
