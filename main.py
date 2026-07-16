import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
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
# ==================== Picmarker 内嵌水印工具类（原Picmarker.py完整代码） ====================
# ==================== Picmarker 内嵌水印工具类（精简版） ====================
class WatermarkApp:
    def __init__(self, parent_frame, main_app):
        self.parent = parent_frame
        self.main_app = main_app  # 主程序引用，直接复用主程序的图片列表
        # 初始化变量
        self.watermark_text = tk.StringVar(value="水印内容")
        self.font_size = tk.IntVar(value=20)
        self.font_color_var = tk.StringVar(value="黑色")
        self.color_map = {
            "黑色": "#000000",
            "白色": "#FFFFFF",
            "红色": "#FF0000",
            "蓝色": "#0000FF",
            "绿色": "#00FF00"
        }
        self.is_bold = tk.BooleanVar(value=False)
        self.fonts = sorted(tkfont.families())
        self.font_family = tk.StringVar(value="Arial" if "Arial" in self.fonts else self.fonts[0])
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)

        # 水印设置
        settings_frame = ttk.LabelFrame(main_frame, text="简易水印设置", padding="5")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)

        ttk.Label(settings_frame, text="水印内容:").grid(row=0, column=0, sticky=tk.W)
        text_entry = ttk.Entry(settings_frame, textvariable=self.watermark_text, width=25)
        text_entry.grid(row=0, column=1, padx=(5,0))
        text_entry.bind("<KeyRelease>", lambda e: self.main_app.show_preview())

        ttk.Label(settings_frame, text="字体大小:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        size_spin = ttk.Spinbox(settings_frame, from_=10, to=100, textvariable=self.font_size, width=8)
        size_spin.grid(row=1, column=1, padx=(5,0), pady=(5,0), sticky=tk.W)
        size_spin.bind("<<Increment>>", lambda e: self.main_app.show_preview())
        size_spin.bind("<<Decrement>>", lambda e: self.main_app.show_preview())

        ttk.Label(settings_frame, text="字体颜色:").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        color_options = list(self.color_map.keys())
        color_combo = ttk.Combobox(settings_frame, textvariable=self.font_color_var, values=color_options, state="readonly")
        color_combo.grid(row=2, column=1, padx=(5,0), pady=(5,0), sticky=tk.W)
        color_combo.bind("<<ComboboxSelected>>", lambda e: self.main_app.show_preview())

        bold_check = ttk.Checkbutton(settings_frame, text="加粗", variable=self.is_bold, command=self.main_app.show_preview)
        bold_check.grid(row=3, column=0, pady=(5,0), sticky=tk.W)

        ttk.Label(settings_frame, text="字体:").grid(row=4, column=0, sticky=tk.W, pady=(5,0))
        font_combo = ttk.Combobox(settings_frame, textvariable=self.font_family, values=self.fonts, state="readonly")
        font_combo.grid(row=4, column=1, padx=(5,0), pady=(5,0), sticky=(tk.W, tk.E))
        font_combo.bind("<<ComboboxSelected>>", lambda e: self.main_app.show_preview())

        # 执行按钮
        ttk.Button(settings_frame, text="批量添加水印", command=self.add_watermark).grid(row=5, column=1, padx=(5,0), pady=(5,0), sticky=(tk.W, tk.E))

    def add_scattered_watermarks(self, image, text, font, color):
        width, height = image.size
        rotated_text = self.create_rotated_text_image(text, font, color)
        text_width, text_height = rotated_text.size
        spacing = max(text_width, text_height) * 1.5
        y = -text_height
        while y < height + text_height:
            x = -text_width
            while x < width + text_width:
                image.paste(rotated_text, (int(x), int(y)), rotated_text)
                x += spacing
            y += spacing

    def get_font(self, family, size):
        chinese_fonts = [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simsun.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
        ]
        for font_path in chinese_fonts:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        try:
            return ImageFont.truetype(family, size)
        except:
            pass
        font_paths = [
            f"C:\\Windows\\Fonts\\{family}.ttf",
            f"C:\\Windows\\Fonts\\{family}.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()

    def create_rotated_text_image(self, text, font, color):
        temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        padding = max(20, int(max(text_width, text_height) * 0.5))
        text_img = Image.new('RGBA', (text_width + padding * 2, text_height + padding * 2), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_img)
        text_draw.text((padding, padding), text, fill=color, font=font)
        rotated = text_img.rotate(45, expand=True, resample=Image.BICUBIC)
        final_img = Image.new('RGBA', (rotated.width + 10, rotated.height + 10), (0, 0, 0, 0))
        final_img.paste(rotated, (5, 5), rotated)
        return final_img

    def add_watermark(self):
        # 直接使用主程序的图片列表和输出路径
        image_paths = self.main_app.input_files
        if not image_paths:
            messagebox.showerror("错误", "请先在主程序添加图片")
            return
        output_path = self.main_app.output_path.get()
        if not output_path:
            messagebox.showerror("错误", "请先在主程序设置输出路径")
            return
        if not self.watermark_text.get().strip():
            messagebox.showerror("错误", "请输入水印内容")
            return
        font_color = self.color_map[self.font_color_var.get()]
        success_count = 0
        for image_path in image_paths:
            try:
                image = Image.open(image_path)
                font = self.get_font(self.font_family.get(), self.font_size.get())
                self.add_scattered_watermarks(image, self.watermark_text.get(), font, font_color)
                base_name = os.path.basename(image_path)
                output_file = os.path.join(output_path, f"watermarked_{base_name}")
                image.save(output_file)
                success_count += 1
            except Exception as e:
                messagebox.showerror("错误", f"处理失败 {os.path.basename(image_path)}:{str(e)}")
        if success_count > 0:
            messagebox.showinfo("完成", f"成功处理 {success_count} 张图片")

# ==================== 工具类 ====================
class CollapsiblePanel(ttk.Frame):
    """可折叠面板：点击标题按钮切换内容显示/隐藏"""
    def __init__(self, parent, title, expanded=False):
        super().__init__(parent)
        self.is_expanded = expanded
        self.title_text = title
        arrow = "▲" if expanded else "▼"
        self.title_btn = ttk.Button(
            self,
            text=f"{arrow} {title}",
            command=self.toggle
        )
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
                    "C:/Windows/Fonts/msyhbd.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/arial.ttf"
                ]
                for p in font_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
                import winreg
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
        self.root.title("Picmarker V1.3 - 批量图片水印工具")
        self.root.geometry(GUI_CFG.get("window_size", "1200x900"))
        self.root.minsize(1000, 700)
        self.root.iconbitmap('icons/icon.ico')
        self.root.state("zoomed")
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
        self.simple_watermark_panel = None
        self._cached_preview_path = None  # 缓存上次生成的预览图路径
        self._cached_params = {}  # 缓存参数哈希
        self._init_ui()
        self.auto_refresh_preview()
        Path(self.output_path.get()).mkdir(parents=True, exist_ok=True)
    def _init_ui(self):
        style = ttk.Style()
        style.configure(".", font=(GUI_CFG["font_family"], GUI_CFG["font_size"]))
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=1)
        main_pw = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_pw.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)
        left_frame = ttk.Frame(main_pw, width=400)
        main_pw.add(left_frame, weight=0)
        # 禁止左侧面板被拖拽调整大小
        self.left_canvas = tk.Canvas(left_frame, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.left_canvas.yview)
        self.left_scroll_content = ttk.Frame(self.left_canvas)
        self.left_scroll_content.bind("<Configure>", self.update_left_scroll_region)
        self.left_canvas.create_window((0, 0), window=self.left_scroll_content, anchor="nw", width=350)
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        self.left_canvas.pack(side="left", fill="both", expand=True)
        self.left_scrollbar.pack(side="right", fill="y")
        # 绑定鼠标滚轮滚动
        def on_mousewheel(event):
            # Windows 滚轮每格是 120，向上为正，向下为负
            delta = -1 if event.delta > 0 else 1
            self.left_canvas.yview_scroll(delta, "units")
        
        # 绑定到 Canvas 和内容区域，确保鼠标在左侧任意位置都能滚动
        self.left_canvas.bind("<MouseWheel>", on_mousewheel)
        self.left_scroll_content.bind("<MouseWheel>", on_mousewheel)
        btn_frame = ttk.Frame(self.left_scroll_content)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="➕ 添加图片", command=self.select_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="🗑 删除选中", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="📂 清空列表", command=self.clear_all).pack(side="left", padx=2)
        # 功能启用/禁用开关
        enable_frame = ttk.LabelFrame(self.left_scroll_content, text="功能开关", padding="3")
        enable_frame.pack(fill="x", pady=3)
        self.enable_border = tk.BooleanVar(value=True)
        self.enable_watermark = tk.BooleanVar(value=True)
        self.enable_hidden = tk.BooleanVar(value=False)
        ttk.Checkbutton(enable_frame, text="添加边框", variable=self.enable_border, command=self.show_preview).pack(side="left", padx=3)
        ttk.Checkbutton(enable_frame, text="明文水印", variable=self.enable_watermark, command=self.show_preview).pack(side="left", padx=3)
        ttk.Checkbutton(enable_frame, text="隐形水印", variable=self.enable_hidden, command=self.show_preview).pack(side="left", padx=3)
        list_frame = ttk.Frame(self.left_scroll_content)
        list_frame.pack(fill="both", expand=True, pady=5)
        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(list_frame,
                                  yscrollcommand=list_scrollbar.set,
                                  selectmode=tk.SINGLE,
                                  font=(GUI_CFG["font_family"], GUI_CFG["font_size"]),
                                  bg="white",
                                  selectbackground="#0078D4",
                                  activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        list_scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        panel_border = CollapsiblePanel(self.left_scroll_content, "添加边框", expanded=False)
        panel_border.pack(fill="x", pady=3)
        param_frame = ttk.LabelFrame(panel_border.content, text="✏️ 水印参数")
        param_frame.pack(fill=tk.X, pady=(0, 5))
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, padx=8, pady=4)
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, padx=8, pady=4)
        row3 = ttk.Frame(param_frame)
        row3.pack(fill=tk.X, padx=8, pady=4)
        row4 = ttk.Frame(param_frame)
        row4.pack(fill=tk.X, padx=8, pady=4)
        row5 = ttk.Frame(param_frame)
        row5.pack(fill=tk.X, padx=8, pady=4)
        row6 = ttk.Frame(param_frame)
        row6.pack(fill=tk.X, padx=8, pady=4)
        row7 = ttk.Frame(param_frame)
        row7.pack(fill=tk.X, padx=8, pady=4)
        row8 = ttk.Frame(param_frame)
        row8.pack(fill=tk.X, padx=8, pady=4)
        row9 = ttk.Frame(param_frame)
        row9.pack(fill=tk.X, padx=8, pady=4)
        row10 = ttk.Frame(param_frame)
        row10.pack(fill=tk.X, padx=8, pady=4)
        row11 = ttk.Frame(param_frame)
        row11.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(row1, text="品牌：", width=6).pack(side=tk.LEFT)
        self.cbo_brand = ttk.Combobox(row1, textvariable=self.brand_var,
                                      values=list(CAMERA_DB.keys()), width=20, state="readonly")
        self.cbo_brand.pack(side=tk.LEFT, padx=(0, 10))
        self.cbo_brand.bind("<<ComboboxSelected>>", self.on_brand_change)
        self.cbo_brand.bind("<KeyRelease>", lambda e: self.on_brand_change())
        self.cbo_brand.bind("<<ComboboxSelected>>", lambda e: self.show_preview(), add="+")
        ttk.Label(row2, text="相机：", width=6).pack(side=tk.LEFT)
        self.cbo_cam = ttk.Combobox(row2, textvariable=self.camera_var, width=20, state="readonly")
        self.cbo_cam.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_cam.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row3, text="镜头：", width=6).pack(side=tk.LEFT)
        self.cbo_len = ttk.Combobox(row3, textvariable=self.lens_var, width=20, state="readonly")
        self.cbo_len.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_len.pack(side=tk.LEFT)
        ttk.Label(row4, text="标题：", width=6).pack(side=tk.LEFT)
        entry_name = ttk.Entry(row4, textvariable=self.photo_name_var, width=20, state="normal")
        entry_name.pack(side=tk.LEFT, padx=(0, 10))
        entry_name.bind("<KeyRelease>", lambda e: self.show_preview())
        ttk.Label(row5, text="焦距：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row5, textvariable=self.focal_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row6, text="光圈：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row6, textvariable=self.f_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row7, text="快门：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row7, textvariable=self.exp_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row8, text="ISO：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row8, textvariable=self.iso_var, width=20, state="readonly").pack(side=tk.LEFT)
        ttk.Label(row9, text="时间：", width=6).pack(side=tk.LEFT)
        entry_time = ttk.Entry(row9, textvariable=self.time_var, width=20, state="normal")
        entry_time.pack(side=tk.LEFT, padx=(0, 10))
        entry_time.bind("<KeyRelease>", lambda e: self.show_preview())
        ttk.Label(row10, text="地点：", width=6).pack(side=tk.LEFT)
        entry_loc = ttk.Entry(row10, textvariable=self.loc_var, width=20, state="normal")
        entry_loc.pack(side=tk.LEFT, padx=(0, 10))
        entry_loc.bind("<KeyRelease>", lambda e: self.show_preview())
        ttk.Label(row11, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row11, textvariable=self.selected_font,values=self.font_list, width=20, state="readonly")
        self.font_cb.pack(side=tk.LEFT)
        self.font_cb.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        # ========== 第二个折叠面板：明文水印，内部嵌入Picmarker完整界面 ==========
        panel_text = CollapsiblePanel(self.left_scroll_content, "明文水印", expanded=False)
        panel_text.pack(fill="x", pady=3)
        # 将Picmarker界面嵌入明文水印面板的content里
        self.simple_watermark_panel = WatermarkApp(panel_text.content, self)
        
        
                # 隐形水印面板
        panel_hidden = CollapsiblePanel(self.left_scroll_content, "隐形水印", expanded=False)
        panel_hidden.pack(fill="x", pady=3)
        hidden_frame = ttk.LabelFrame(panel_hidden.content, text="盲水印设置", padding="5")
        hidden_frame.pack(fill="x", pady=2)
        ttk.Label(hidden_frame, text="密码:").grid(row=0, column=0, sticky=tk.W)
        self.hidden_pwd = tk.StringVar(value="123456")
        ttk.Entry(hidden_frame, textvariable=self.hidden_pwd, width=20, show="*").grid(row=0, column=1, padx=5)
        ttk.Label(hidden_frame, text="加密内容:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.hidden_text = tk.StringVar(value="版权信息")
        ttk.Entry(hidden_frame, textvariable=self.hidden_text, width=20).grid(row=1, column=1, padx=5, pady=(5,0))
        ttk.Label(hidden_frame, text="⚠ 处理速度较慢，请耐心等待", foreground="orange").grid(row=2, column=0, columnspan=2, pady=5)
        btn_hidden = ttk.Button(hidden_frame, text="批量嵌入盲水印", command=self.batch_embed_hidden)
        btn_hidden.grid(row=3, column=0, columnspan=2, pady=3)
        ttk.Label(hidden_frame, text="提取盲水印:", foreground="gray").grid(row=4, column=0, columnspan=2, pady=(10,0))
        btn_extract = ttk.Button(hidden_frame, text="提取当前图片盲水印", command=self.extract_hidden)
        btn_extract.grid(row=5, column=0, columnspan=2, pady=3)
        right_frame = ttk.Frame(main_pw)
        main_pw.add(right_frame, weight=1)
        path_frame = ttk.LabelFrame(right_frame, text="💾 输出设置")
        path_frame.pack(fill=tk.X, pady=(0, 5))
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(path_inner, text="保存路径：").pack(side=tk.LEFT)
        ttk.Entry(path_inner, textvariable=self.output_path, width=50).pack(side=tk.LEFT, padx=6)
        ttk.Button(path_inner, text="浏览...", command=self.select_out_dir).pack(side=tk.LEFT, padx=2)
        preview_frame = ttk.LabelFrame(right_frame, text="🖼 效果预览")
        preview_frame.pack(fill=tk.BOTH, expand=1, pady=(0, 5))
        preview_ctrl = ttk.Frame(preview_frame)
        preview_ctrl.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(preview_ctrl, text="◀ 上一张", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="下一张 ▶", command=self.next_image).pack(side=tk.LEFT, padx=2)
        self.preview_label = ttk.Label(preview_ctrl, text="")
        self.preview_label.pack(side=tk.LEFT, padx=10)
        self.canvas = tk.Canvas(preview_frame, bg="#f5f5f5", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=1, padx=4, pady=4)
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=6)
        ttk.Button(action_frame, text="🔄 刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🎨 添加水印(当前)", command=self.add_watermark_current).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="⚙ 设置编辑器", command=self.open_settings_editor).pack(side=tk.LEFT, padx=2)
        # 原有独立启动Picmarker按钮保留，作为备用入口
        ttk.Button(action_frame, text="📷 水印工具(独立窗口)", command=self.open_picmarker).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📦 批量处理(全部)", command=self.start_batch).pack(side=tk.RIGHT, padx=2)
        self.progress = ttk.Progressbar(right_frame, orient=tk.HORIZONTAL)
        self.progress.pack(fill=tk.X, pady=(0, 3))
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)
        self.canvas.bind("<Configure>", lambda e: self.root.after(200, self.show_preview))

    def update_left_scroll_region(self, event):
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def auto_refresh_preview(self):
        # 仅首次加载时显示预览，后续由各控件按需触发
        if not self._cached_preview_path:
            self.show_preview()

        def _save_current_edits(self):
        #保存当前图片的用户修改
            if self.current_index >= 0 and hasattr(self, '_user_edits'):
                self._user_edits[self.current_index] = {
                "brand": self.brand_var.get().strip(),
                "camera": self.camera_var.get().strip(),
                "lens": self.lens_var.get().strip(),
                "focal": self.focal_var.get().strip(),
                "f": self.f_var.get().strip(),
                "exp": self.exp_var.get().strip(),
                "iso": self.iso_var.get().strip(),
                "datetime": self.time_var.get().strip(),
                "location": self.loc_var.get().strip(),
                "photo_name": self.photo_name_var.get().strip()
            }
    def prev_image(self):
        if not self.input_files:
            return
        if self.current_index > 0:
            self._save_current_edits()
            self.current_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()
    def next_image(self):
        if not self.input_files:
            return
        if self.current_index < len(self.input_files) - 1:
            self._save_current_edits()
            self.current_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._update_preview_for_current()
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
                self.brand_var.set("")
                self.camera_var.set("")
                self.lens_var.set("")
                self.photo_name_var.set("")
                self.focal_var.set("")
                self.f_var.set("")
                self.exp_var.set("")
                self.iso_var.set("")
                self.time_var.set("")
                self.loc_var.set("")
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
            self.brand_var.set("")
            self.camera_var.set("")
            self.lens_var.set("")
            self.photo_name_var.set("")
            self.focal_var.set("")
            self.f_var.set("")
            self.exp_var.set("")
            self.iso_var.set("")
            self.time_var.set("")
            self.loc_var.set("")
    def on_list_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx != self.current_index:
            self._save_current_edits()
            self.current_index = idx
            self._update_preview_for_current()
    def _update_preview_for_current(self):
        if self.current_index < 0 or self.current_index >= len(self.input_files):
            return
        path = self.input_files[self.current_index]
        filename = os.path.basename(path)
        self.status_var.set(f"当前: {filename} ({self.current_index+1}/{len(self.input_files)})")
        # 保存当前用户修改，切换图片时恢复
        if not hasattr(self, '_user_edits'):
            self._user_edits = {}
        # 先保存当前图片的用户修改
        if self.current_index in self._user_edits:
            edits = self._user_edits[self.current_index]
        else:
            info = ExifReader.get_exif_full(path)
            edits = {
                "brand": info.get("make", ""),
                "camera": info.get("camera_model", ""),
                "lens": info.get("lens_model", ""),
                "focal": info.get("focal", ""),
                "f": info.get("f", ""),
                "exp": info.get("exposure", ""),
                "iso": info.get("iso", ""),
                "datetime": info.get("datetime", ""),
                "location": "",
                "photo_name": ""
            }
            self._user_edits[self.current_index] = edits
        self.brand_var.set(edits["brand"])
        self.on_brand_change()
        self.camera_var.set(edits["camera"])
        self.lens_var.set(edits["lens"])
        self.focal_var.set(edits["focal"])
        self.f_var.set(edits["f"])
        self.exp_var.set(edits["exp"])
        self.iso_var.set(edits["iso"])
        self.time_var.set(edits["datetime"])
        self.loc_var.set(edits["location"])
        self.photo_name_var.set(edits["photo_name"])
        self.root.after(100, self.show_preview)
    def on_brand_change(self, event=None):
        brand = self.brand_var.get().strip()
        if brand in CAMERA_DB:
            cams = CAMERA_DB[brand].get("cameras", [])
            lens = CAMERA_DB[brand].get("lenses", [])
            self.cbo_cam.config(values=cams)
            self.cbo_len.config(values=lens)
    def select_out_dir(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.output_path.set(d)
    def get_data(self):
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
    def _get_preview_hash(self):
        """生成当前预览参数的哈希值，用于判断是否需要重新生成"""
        data = self.get_data()
        wm = self.simple_watermark_panel
        wm_text = wm.watermark_text.get() if wm else ""
        wm_font = wm.font_family.get() if wm else ""
        wm_size = wm.font_size.get() if wm else 0
        wm_color = wm.font_color_var.get() if wm else ""
        return hash((
            self.current_index,
            self.enable_border.get(),
            self.enable_watermark.get(),
            self.selected_font.get(),
            data["brand"], data["camera"], data["lens"], data["photo_name"],
            data["focal"], data["f"], data["exp"], data["iso"],
            data["datetime"], data["location"],
            wm_text, wm_font, wm_size, wm_color
        ))

    def show_preview(self):
        if not self.input_files or self.current_index == -1:
            return
        try:
            os.makedirs(self.output_path.get(), exist_ok=True)
            img_path = self.input_files[self.current_index]
            cur_hash = self._get_preview_hash()
            cw = max(self.canvas.winfo_width(), 100)
            ch = max(self.canvas.winfo_height(), 100)
            if self._cached_preview_path and self._cached_preview_path.exists() and self._cached_params.get("hash") == cur_hash:
                im = Image.open(self._cached_preview_path)
            else:
                tmp_full = Path(self.output_path.get()) / "_tmp_preview_full.jpg"
                # 在原图上处理水印
                if self.enable_border.get():
                    WatermarkGenerator.add_watermark(img_path, str(tmp_full), self.get_data(), self.selected_font.get())
                else:
                    shutil.copy2(img_path, str(tmp_full))
                if self.enable_watermark.get() and self.simple_watermark_panel:
                    wm = self.simple_watermark_panel
                    if wm.watermark_text.get().strip():
                        img = Image.open(tmp_full).convert("RGBA")
                        font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                        color = wm.color_map[wm.font_color_var.get()]
                        wm.add_scattered_watermarks(img, wm.watermark_text.get(), font, color)
                        img.convert("RGB").save(tmp_full, quality=95)
                # 缩略到预览尺寸
                tmp_thumb = Path(self.output_path.get()) / "_tmp_thumb.jpg"
                with Image.open(tmp_full) as full_img:
                    scale = min((cw-20)/full_img.width, (ch-20)/full_img.height, 1.0)
                    thumb = full_img.resize((int(full_img.width*scale), int(full_img.height*scale)), RESAMPLE)
                    thumb.save(tmp_thumb, quality=85)
                tmp_full.unlink(missing_ok=True)
                self._cached_preview_path = tmp_thumb
                self._cached_params["hash"] = cur_hash
                im = Image.open(tmp_thumb)
            self.preview_img = ImageTk.PhotoImage(im)
            self.canvas.delete("all")
            self.canvas.create_image(cw//2, ch//2, image=self.preview_img, anchor=tk.CENTER)
            self.preview_label.config(text=f"预览: {os.path.basename(self.input_files[self.current_index])}")
        except Exception as e:
            self.status_var.set(f"预览失败: {str(e)}")
    def add_watermark_current(self):
        if not self.input_files or self.current_index == -1:
            messagebox.showwarning("提示", "请先选择照片")
            return
        os.makedirs(self.output_path.get(), exist_ok=True)
        path = self.input_files[self.current_index]
        name = os.path.basename(path)
        out = os.path.join(self.output_path.get(), f"Watermark_{name}")
        try:
            WatermarkGenerator.add_watermark(path, out, self.get_data(), self.selected_font.get())
            # 应用明文水印
            if self.enable_watermark.get() and self.simple_watermark_panel:
                wm = self.simple_watermark_panel
                if wm.watermark_text.get().strip():
                    img = Image.open(out).convert("RGBA")
                    wm_font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                    color = wm.color_map[wm.font_color_var.get()]
                    wm.add_scattered_watermarks(img, wm.watermark_text.get(), wm_font, color)
                    img.convert("RGB").save(out, quality=95)
            self.status_var.set(f"已完成: {name}")
            messagebox.showinfo("完成", f"水印已保存到:\n{out}")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
    def start_batch(self):
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加照片")
            return
        if not messagebox.askyesno("确认批量处理", f"将处理 {len(self.input_files)} 张照片，是否继续？"):
            return
        os.makedirs(self.output_path.get(), exist_ok=True)
        font = self.selected_font.get()
        total = len(self.input_files)
        self.progress["maximum"] = total
        def worker():
            success = 0
            for i, f in enumerate(self.input_files):
                name = os.path.basename(f)
                out = os.path.join(self.output_path.get(), f"Watermark_{name}")
                try:
                    # 每张图片单独读取 EXIF 生成数据
                    info = ExifReader.get_exif_full(f)
                    data = {
                        "brand": info.get("make", ""),
                        "camera": info.get("camera_model", ""),
                        "lens": info.get("lens_model", ""),
                        "photo_name": "",
                        "focal": info.get("focal", ""),
                        "f": info.get("f", ""),
                        "exp": info.get("exposure", ""),
                        "iso": info.get("iso", ""),
                        "datetime": info.get("datetime", ""),
                        "location": ""
                    }
                    WatermarkGenerator.add_watermark(f, out, data, font)
                    # 应用明文水印
                    if self.enable_watermark.get() and self.simple_watermark_panel:
                        wm = self.simple_watermark_panel
                        if wm.watermark_text.get().strip():
                            img = Image.open(out).convert("RGBA")
                            wm_font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                            color = wm.color_map[wm.font_color_var.get()]
                            wm.add_scattered_watermarks(img, wm.watermark_text.get(), wm_font, color)
                            img.convert("RGB").save(out, quality=95)
                    success += 1
                except Exception as e:
                    print(f"处理失败 {name}: {e}")
                self.progress["value"] = i + 1
                self.status_var.set(f"处理中... {i+1}/{total}")
                self.root.update()
            self.progress["value"] = 0
            self.status_var.set(f"完成！成功 {success}/{total}")
            messagebox.showinfo("批量处理完成", f"成功处理 {success}/{total} 张照片\n保存位置: {self.output_path.get()}")
        threading.Thread(target=worker, daemon=True).start()
    def open_settings_editor(self):
        
        import subprocess
        editor_path = Path(__file__).parent / "edit.py"
        if editor_path.exists():
            subprocess.Popen(["python", str(editor_path)])
        else:
            messagebox.showerror("错误", f"未找到 {editor_path}")
        return
    def batch_embed_hidden(self):
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加图片")
            return
        pwd = self.hidden_pwd.get().strip()
        text = self.hidden_text.get().strip()
        if not pwd or not text:
            messagebox.showerror("错误", "请输入密码和加密内容")
            return
        if not messagebox.askyesno("确认", f"将对 {len(self.input_files)} 张图片嵌入盲水印\n密码: {pwd}\n内容: {text}\n\n⚠ 处理速度较慢，是否继续？"):
            return
        os.makedirs(self.output_path.get(), exist_ok=True)
        total = len(self.input_files)
        self.progress["maximum"] = total
        def worker():
            try:
                from blind_watermark import WaterMark
            except ImportError:
                self.status_var.set("❌ 未安装 blind-watermark 库")
                return
            success = 0
            for i, f in enumerate(self.input_files):
                name = os.path.basename(f)
                out = os.path.join(self.output_path.get(), f"hidden_{name}")
                try:
                    bw = WaterMark(password_img=int(pwd), password_wm=int(pwd))
                    from PIL import Image
                    import numpy as np
                    pil_img = Image.open(f).convert('RGB')
                    img_cv = np.array(pil_img)[:, :, ::-1]
                    bw.read_img(img=img_cv)
                    bw.read_wm(text, mode='str')
                    bw.embed(out)
                    # 保存水印长度到同名 .len 文件
                    with open(out + '.len', 'w') as lf:
                        lf.write(str(len(bw.wm_bit)))
                    success += 1
                except Exception as e:
                    print(f"嵌入失败 {name}: {e}")
                self.progress["value"] = i + 1
                self.status_var.set(f"嵌入盲水印... {i+1}/{total}")
                self.root.update()
            self.progress["value"] = 0
            msg = f"完成！成功 {success}/{total}\n密码: {pwd}\n保存位置: {self.output_path.get()}"
            self.status_var.set(f"✅ 盲水印嵌入完成 {success}/{total}")
            messagebox.showinfo("盲水印嵌入完成", msg)
        threading.Thread(target=worker, daemon=True).start()

    def extract_hidden(self):
        if not self.input_files or self.current_index == -1:
            messagebox.showwarning("提示", "请先选择图片")
            return
        pwd = self.hidden_pwd.get().strip()
        if not pwd:
            messagebox.showerror("错误", "请输入密码")
            return
        path = self.input_files[self.current_index]
        self.status_var.set("正在提取盲水印...")
        def worker():
            try:
                from blind_watermark import WaterMark
            except ImportError:
                self.status_var.set("❌ 未安装 blind-watermark 库")
                return
            try:
                bw = WaterMark(password_img=int(pwd), password_wm=int(pwd))
                from PIL import Image
                import numpy as np
                pil_img = Image.open(path).convert('RGB')
                img_cv = np.array(pil_img)[:, :, ::-1]
                len_path = path + '.len'
                if os.path.exists(len_path):
                    with open(len_path) as lf:
                        wm_shape = int(lf.read())
                else:
                    self.status_var.set("❌ 缺少水印长度信息")
                    messagebox.showerror("错误", "找不到水印长度文件 (.len)，请重新嵌入")
                    return
                wm_extract = bw.extract(embed_img=img_cv, wm_shape=wm_shape, mode='str')
                self.status_var.set(f"✅ 提取成功")
                messagebox.showinfo("盲水印提取结果", f"图片: {os.path.basename(path)}\n密码: {pwd}\n\n提取内容:\n{wm_extract}")
            except Exception as e:
                self.status_var.set(f"❌ 提取失败")
                messagebox.showerror("提取失败", f"密码错误或图片不含盲水印\n\n{str(e)}")
        threading.Thread(target=worker, daemon=True).start()

    def open_picmarker(self):
        import subprocess
        marker_path = Path(__file__).parent / "Picmarker.py"
        if marker_path.exists():
            subprocess.Popen(["python", str(marker_path)])
        else:
            messagebox.showerror("错误", f"未找到 {marker_path}")
if __name__ == "__main__":
    try:
        import exifread
    except ImportError:
        print("正在安装依赖库...")
        os.system("python -m pip install Pillow exifread piexif")
        import exifread
    root = tk.Tk()
    app = PhotoWatermarkApp(root)
    root.mainloop()