"""
settings.json 图形化编辑器 v1.1
独立于相机水印主程序，用于可视化修改配置文件。
每个输入框都带有独立标签，清晰对应配置项。
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
from pathlib import Path
import copy

# 配置文件路径（与脚本同目录）
SETTINGS_PATH = Path(__file__).parent / "settings.json"

# 默认配置（用于初始化或重置）
DEFAULT_SETTINGS = {
    "gui": {
        "font_family": "Microsoft YaHei",
        "font_size": 10,
        "title_font_size": 11,
        "window_size": "1200x900",
        "preview_auto_refresh": True
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

class SettingsEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("settings.json 编辑器")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        self.settings = self.load_settings()
        self.create_widgets()
        self.populate_all_tabs()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return copy.deepcopy(DEFAULT_SETTINGS)

    def save_settings(self):
        try:
            self.collect_all_data()
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", "配置已保存。")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def on_closing(self):
        if messagebox.askyesno("退出", "是否保存修改后退出？"):
            self.save_settings()
        self.root.destroy()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_gui = ttk.Frame(self.notebook)
        self.tab_watermark_basic = ttk.Frame(self.notebook)
        self.tab_watermark_text = ttk.Frame(self.notebook)
        self.tab_mappings = ttk.Frame(self.notebook)
        self.tab_database = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_gui, text="界面设置")
        self.notebook.add(self.tab_watermark_basic, text="水印基本")
        self.notebook.add(self.tab_watermark_text, text="水印文本")
        self.notebook.add(self.tab_mappings, text="品牌与型号映射")
        self.notebook.add(self.tab_database, text="相机数据库")

        self.build_gui_tab()
        self.build_watermark_basic_tab()
        self.build_watermark_text_tab()
        self.build_mappings_tab()
        self.build_database_tab()

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(bottom_frame, text="保存配置", command=self.save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="重置为默认", command=self.reset_defaults).pack(side=tk.RIGHT, padx=5)

    # ---------- 选项卡 1: GUI ----------
    def build_gui_tab(self):
        frame = self.tab_gui
        pad = {'padx': 5, 'pady': 5}
        row = 0

        ttk.Label(frame, text="默认字体：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.gui_font_family = tk.StringVar()
        ttk.Entry(frame, textvariable=self.gui_font_family, width=30).grid(row=row, column=1, **pad)
        row += 1

        ttk.Label(frame, text="基础字号：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.gui_font_size = tk.IntVar()
        ttk.Spinbox(frame, from_=6, to=20, textvariable=self.gui_font_size, width=5).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="标题字号：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.gui_title_font_size = tk.IntVar()
        ttk.Spinbox(frame, from_=8, to=24, textvariable=self.gui_title_font_size, width=5).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="窗口尺寸 (宽x高)：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.gui_window_size = tk.StringVar()
        ttk.Entry(frame, textvariable=self.gui_window_size, width=30).grid(row=row, column=1, **pad)
        row += 1

        ttk.Label(frame, text="自动刷新预览：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.gui_preview_auto_refresh = tk.BooleanVar()
        ttk.Checkbutton(frame, variable=self.gui_preview_auto_refresh).grid(row=row, column=1, sticky=tk.W, **pad)

    def populate_gui_tab(self):
        gui = self.settings.get("gui", {})
        self.gui_font_family.set(gui.get("font_family", ""))
        self.gui_font_size.set(gui.get("font_size", 10))
        self.gui_title_font_size.set(gui.get("title_font_size", 11))
        self.gui_window_size.set(gui.get("window_size", "1150x880"))
        self.gui_preview_auto_refresh.set(gui.get("preview_auto_refresh", True))

    # ---------- 选项卡 2: 水印基本 ----------
    def build_watermark_basic_tab(self):
        frame = self.tab_watermark_basic
        pad = {'padx': 5, 'pady': 5}
        row = 0

        ttk.Label(frame, text="白条高度 (px)：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_bar_height = tk.IntVar()
        ttk.Spinbox(frame, from_=50, to=500, increment=10, textvariable=self.wm_bar_height, width=6).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="白条颜色 (R,G,B)：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_bg_color = tk.StringVar()
        ttk.Entry(frame, textvariable=self.wm_bg_color, width=25).grid(row=row, column=1, **pad)
        row += 1

        ttk.Label(frame, text="品牌图标最大高度：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_icon_max_height = tk.IntVar()
        ttk.Spinbox(frame, from_=20, to=200, increment=10, textvariable=self.wm_icon_max_height, width=6).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="图标左边距：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_icon_margin_left = tk.IntVar()
        ttk.Spinbox(frame, from_=0, to=100, textvariable=self.wm_icon_margin_left, width=6).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="图标右边距：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_icon_margin_right = tk.IntVar()
        ttk.Spinbox(frame, from_=0, to=100, textvariable=self.wm_icon_margin_right, width=6).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        ttk.Label(frame, text="文本垂直偏移：").grid(row=row, column=0, sticky=tk.W, **pad)
        self.wm_vertical_center_offset = tk.IntVar()
        ttk.Spinbox(frame, from_=-100, to=100, textvariable=self.wm_vertical_center_offset, width=6).grid(row=row, column=1, sticky=tk.W, **pad)
        row += 1

        # 描边设置
        stroke_frame = ttk.LabelFrame(frame, text="文字描边")
        stroke_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
        self.stroke_enabled = tk.BooleanVar()
        ttk.Checkbutton(stroke_frame, text="启用描边", variable=self.stroke_enabled).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(stroke_frame, text="描边宽度：").grid(row=0, column=1, padx=5, pady=5)
        self.stroke_width = tk.IntVar()
        ttk.Spinbox(stroke_frame, from_=1, to=10, textvariable=self.stroke_width, width=5).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(stroke_frame, text="描边颜色 (R,G,B)：").grid(row=0, column=3, padx=5, pady=5)
        self.stroke_fill = tk.StringVar()
        ttk.Entry(stroke_frame, textvariable=self.stroke_fill, width=20).grid(row=0, column=4, padx=5, pady=5)

    def populate_watermark_basic_tab(self):
        wm = self.settings.get("watermark", {})
        self.wm_bar_height.set(wm.get("bar_height", 250))
        self.wm_bg_color.set(",".join(str(v) for v in wm.get("background_color", [255,255,255])))
        self.wm_icon_max_height.set(wm.get("icon_max_height", 140))
        self.wm_icon_margin_left.set(wm.get("icon_margin_left", 30))
        self.wm_icon_margin_right.set(wm.get("icon_margin_right", 30))
        self.wm_vertical_center_offset.set(wm.get("vertical_center_offset", 40))

        stroke = wm.get("stroke", {})
        self.stroke_enabled.set(stroke.get("enabled", True))
        self.stroke_width.set(stroke.get("width", 2))
        self.stroke_fill.set(",".join(str(v) for v in stroke.get("fill", [255,255,255])))

    # ---------- 选项卡 3: 水印文本 ----------
    def build_watermark_text_tab(self):
        frame = self.tab_watermark_text
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        pad = {'padx': 5, 'pady': 5}

        # --- 左侧文本位置 ---
        left_frame = ttk.LabelFrame(scrollable_frame, text="左侧文本位置偏移")
        left_frame.pack(fill="x", padx=5, pady=5)
        self.left_pos_vars = {}
        keys = [("相机 (camera)", "camera"), ("镜头 (lens)", "lens"), ("照片名 (name)", "name")]
        for i, (label, key) in enumerate(keys):
            row_frame = ttk.Frame(left_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(row_frame, text=f"{label}  X 偏移：").pack(side="left", padx=2)
            x_var = tk.IntVar()
            ttk.Spinbox(row_frame, from_=-200, to=200, textvariable=x_var, width=6).pack(side="left", padx=2)
            ttk.Label(row_frame, text="  Y 偏移：").pack(side="left", padx=2)
            y_var = tk.IntVar()
            ttk.Spinbox(row_frame, from_=-200, to=200, textvariable=y_var, width=6).pack(side="left", padx=2)
            self.left_pos_vars[key] = (x_var, y_var)

        # --- 右侧文本位置 ---
        right_frame = ttk.LabelFrame(scrollable_frame, text="右侧文本位置偏移")
        right_frame.pack(fill="x", padx=5, pady=5)
        self.right_pos_vars = {}
        keys = [("参数 (params)", "params"), ("时间/地点 (time)", "time")]
        for label, key in keys:
            row_frame = ttk.Frame(right_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(row_frame, text=f"{label}  X 偏移：").pack(side="left", padx=2)
            x_var = tk.IntVar()
            ttk.Spinbox(row_frame, from_=-500, to=200, textvariable=x_var, width=6).pack(side="left", padx=2)
            ttk.Label(row_frame, text="  Y 偏移：").pack(side="left", padx=2)
            y_var = tk.IntVar()
            ttk.Spinbox(row_frame, from_=-200, to=200, textvariable=y_var, width=6).pack(side="left", padx=2)
            self.right_pos_vars[key] = (x_var, y_var)

        # --- 字体大小 ---
        font_frame = ttk.LabelFrame(scrollable_frame, text="字体大小")
        font_frame.pack(fill="x", padx=5, pady=5)
        self.font_vars = {}
        font_keys = [("相机 (camera)", "camera"), ("镜头 (lens)", "lens"),
                     ("照片名 (name)", "name"), ("参数 (params)", "params"),
                     ("时间 (time)", "time")]
        for label, key in font_keys:
            row_frame = ttk.Frame(font_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(row_frame, text=f"{label}：").pack(side="left", padx=2)
            var = tk.IntVar()
            ttk.Spinbox(row_frame, from_=8, to=120, textvariable=var, width=6).pack(side="left", padx=2)
            self.font_vars[key] = var

        # --- 颜色 ---
        color_frame = ttk.LabelFrame(scrollable_frame, text="文字颜色 (R,G,B)")
        color_frame.pack(fill="x", padx=5, pady=5)
        self.color_vars = {}
        for label, key in font_keys:
            row_frame = ttk.Frame(color_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(row_frame, text=f"{label}：").pack(side="left", padx=2)
            var = tk.StringVar()
            ttk.Entry(row_frame, textvariable=var, width=18).pack(side="left", padx=2)
            self.color_vars[key] = var

    def populate_watermark_text_tab(self):
        wm = self.settings.get("watermark", {})
        left_text = wm.get("left_text", {})
        for key in ["camera", "lens", "name"]:
            cfg = left_text.get(key, {"x_offset": 0, "y": 0})
            x_var, y_var = self.left_pos_vars[key]
            x_var.set(cfg.get("x_offset", 0))
            y_var.set(cfg.get("y", 0))

        right_text = wm.get("right_text", {})
        for key in ["params", "time"]:
            cfg = right_text.get(key, {"x_offset": 0, "y": 0})
            x_var, y_var = self.right_pos_vars[key]
            x_var.set(cfg.get("x_offset", 0))
            y_var.set(cfg.get("y", 0))

        fonts = wm.get("fonts", {})
        for key, var in self.font_vars.items():
            var.set(fonts.get(key, 30))

        colors = wm.get("colors", {})
        for key, var in self.color_vars.items():
            c = colors.get(key, [0,0,0])
            var.set(",".join(str(v) for v in c))

    # ---------- 选项卡 4: 品牌与型号映射 ----------
    def build_mappings_tab(self):
        frame = self.tab_mappings
        nb = ttk.Notebook(frame)
        nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tab_icons = ttk.Frame(nb)
        nb.add(tab_icons, text="品牌图标文件名")
        self.build_table(tab_icons, "brand_icons", ["品牌", "图标文件名"])

        tab_short = ttk.Frame(nb)
        nb.add(tab_short, text="型号简称")
        self.build_table(tab_short, "model_short_names", ["原始型号", "简称"])

        tab_fix = ttk.Frame(nb)
        nb.add(tab_fix, text="品牌名修正")
        self.build_table(tab_fix, "brand_fix_map", ["原始品牌名", "统一品牌名"])

    def build_table(self, parent, section_key, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=vsb.set)
        vsb.config(command=tree.yview)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="添加", command=lambda: self.add_mapping_row(tree, section_key)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="编辑", command=lambda: self.edit_mapping_row(tree, section_key)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除", command=lambda: self.delete_mapping_row(tree, section_key)).pack(side=tk.LEFT, padx=5)

        if not hasattr(self, 'mapping_trees'):
            self.mapping_trees = {}
        self.mapping_trees[section_key] = tree

    def populate_mapping_table(self, section_key):
        tree = self.mapping_trees.get(section_key)
        if not tree:
            return
        for item in tree.get_children():
            tree.delete(item)
        mapping = self.settings.get(section_key, {})
        for key, value in mapping.items():
            tree.insert("", tk.END, values=(key, value))

    def add_mapping_row(self, tree, section_key):
        mapping = self.settings.setdefault(section_key, {})
        new_key = simpledialog.askstring("新增", "输入键名：")
        if new_key:
            new_value = simpledialog.askstring("新增", f"{new_key} 对应的值：")
            if new_value is not None:
                mapping[new_key] = new_value
                self.populate_mapping_table(section_key)

    def edit_mapping_row(self, tree, section_key):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一行")
            return
        item = selected[0]
        values = tree.item(item, 'values')
        key, value = values[0], values[1]
        mapping = self.settings.setdefault(section_key, {})
        new_value = simpledialog.askstring("编辑", f"修改 {key} 的值：", initialvalue=value)
        if new_value is not None:
            mapping[key] = new_value
            self.populate_mapping_table(section_key)

    def delete_mapping_row(self, tree, section_key):
        selected = tree.selection()
        if not selected:
            return
        if messagebox.askyesno("确认", "确定删除选中项吗？"):
            item = selected[0]
            key = tree.item(item, 'values')[0]
            mapping = self.settings.setdefault(section_key, {})
            if key in mapping:
                del mapping[key]
                self.populate_mapping_table(section_key)

    # ---------- 选项卡 5: 相机数据库 ----------
    def build_database_tab(self):
        frame = self.tab_database
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(paned, width=150)
        right = ttk.Frame(paned)
        paned.add(left, weight=0)
        paned.add(right, weight=1)

        ttk.Label(left, text="品牌列表").pack(padx=5, pady=5)
        self.brand_list = tk.Listbox(left, exportselection=False)
        self.brand_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        brand_btn = ttk.Frame(left)
        brand_btn.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(brand_btn, text="添加品牌", command=self.add_brand).pack(side=tk.LEFT, padx=2)
        ttk.Button(brand_btn, text="删除品牌", command=self.delete_brand).pack(side=tk.LEFT, padx=2)

        ttk.Label(right, text="该品牌下的相机型号").pack(padx=5, pady=5)
        self.camera_list = tk.Listbox(right, exportselection=False)
        self.camera_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        cam_btn = ttk.Frame(right)
        cam_btn.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(cam_btn, text="添加相机", command=self.add_camera).pack(side=tk.LEFT, padx=2)
        ttk.Button(cam_btn, text="删除相机", command=self.delete_camera).pack(side=tk.LEFT, padx=2)

        ttk.Label(right, text="该品牌下的镜头型号").pack(padx=5, pady=5)
        self.lens_list = tk.Listbox(right, exportselection=False)
        self.lens_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        lens_btn = ttk.Frame(right)
        lens_btn.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(lens_btn, text="添加镜头", command=self.add_lens).pack(side=tk.LEFT, padx=2)
        ttk.Button(lens_btn, text="删除镜头", command=self.delete_lens).pack(side=tk.LEFT, padx=2)

        self.brand_list.bind('<<ListboxSelect>>', self.on_brand_select)

    def populate_database_tab(self):
        db = self.settings.get("camera_database", {})
        self.brand_list.delete(0, tk.END)
        for brand in sorted(db.keys()):
            self.brand_list.insert(tk.END, brand)
        self.camera_list.delete(0, tk.END)
        self.lens_list.delete(0, tk.END)

    def on_brand_select(self, event=None):
        sel = self.brand_list.curselection()
        if not sel:
            return
        brand = self.brand_list.get(sel[0])
        db = self.settings.get("camera_database", {})
        data = db.get(brand, {"cameras": [], "lenses": []})
        self.camera_list.delete(0, tk.END)
        for cam in data.get("cameras", []):
            self.camera_list.insert(tk.END, cam)
        self.lens_list.delete(0, tk.END)
        for lens in data.get("lenses", []):
            self.lens_list.insert(tk.END, lens)

    def add_brand(self):
        db = self.settings.setdefault("camera_database", {})
        name = simpledialog.askstring("添加品牌", "品牌名：")
        if name and name not in db:
            db[name] = {"cameras": [], "lenses": []}
            self.populate_database_tab()

    def delete_brand(self):
        sel = self.brand_list.curselection()
        if sel:
            brand = self.brand_list.get(sel[0])
            if messagebox.askyesno("确认", f"删除品牌 {brand} 及其数据？"):
                db = self.settings.get("camera_database", {})
                if brand in db:
                    del db[brand]
                self.populate_database_tab()
                self.camera_list.delete(0, tk.END)
                self.lens_list.delete(0, tk.END)

    def get_selected_brand(self):
        sel = self.brand_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个品牌")
            return None
        return self.brand_list.get(sel[0])

    def add_camera(self):
        brand = self.get_selected_brand()
        if not brand:
            return
        model = simpledialog.askstring("添加相机", f"{brand} 相机型号：")
        if model:
            db = self.settings.setdefault("camera_database", {})
            db[brand].setdefault("cameras", []).append(model)
            self.on_brand_select()

    def delete_camera(self):
        brand = self.get_selected_brand()
        if not brand:
            return
        sel = self.camera_list.curselection()
        if sel:
            item = self.camera_list.get(sel[0])
            if messagebox.askyesno("确认", f"删除相机 {item}？"):
                db = self.settings["camera_database"]
                db[brand]["cameras"].remove(item)
                self.on_brand_select()

    def add_lens(self):
        brand = self.get_selected_brand()
        if not brand:
            return
        lens = simpledialog.askstring("添加镜头", f"{brand} 镜头型号：")
        if lens:
            db = self.settings.setdefault("camera_database", {})
            db[brand].setdefault("lenses", []).append(lens)
            self.on_brand_select()

    def delete_lens(self):
        brand = self.get_selected_brand()
        if not brand:
            return
        sel = self.lens_list.curselection()
        if sel:
            item = self.lens_list.get(sel[0])
            if messagebox.askyesno("确认", f"删除镜头 {item}？"):
                db = self.settings["camera_database"]
                db[brand]["lenses"].remove(item)
                self.on_brand_select()

    # ------------------ 数据收集与填充 ------------------
    def populate_all_tabs(self):
        self.populate_gui_tab()
        self.populate_watermark_basic_tab()
        self.populate_watermark_text_tab()
        for key in ["brand_icons", "model_short_names", "brand_fix_map"]:
            self.populate_mapping_table(key)
        self.populate_database_tab()

    def collect_all_data(self):
        # GUI
        gui = self.settings.setdefault("gui", {})
        gui["font_family"] = self.gui_font_family.get()
        gui["font_size"] = self.gui_font_size.get()
        gui["title_font_size"] = self.gui_title_font_size.get()
        gui["window_size"] = self.gui_window_size.get()
        gui["preview_auto_refresh"] = self.gui_preview_auto_refresh.get()

        # Watermark basic
        wm = self.settings.setdefault("watermark", {})
        wm["bar_height"] = self.wm_bar_height.get()
        try:
            wm["background_color"] = [int(x.strip()) for x in self.wm_bg_color.get().split(",")]
        except:
            wm["background_color"] = [255, 255, 255]
        wm["icon_max_height"] = self.wm_icon_max_height.get()
        wm["icon_margin_left"] = self.wm_icon_margin_left.get()
        wm["icon_margin_right"] = self.wm_icon_margin_right.get()
        wm["vertical_center_offset"] = self.wm_vertical_center_offset.get()

        stroke = wm.setdefault("stroke", {})
        stroke["enabled"] = self.stroke_enabled.get()
        stroke["width"] = self.stroke_width.get()
        try:
            stroke["fill"] = [int(x.strip()) for x in self.stroke_fill.get().split(",")]
        except:
            stroke["fill"] = [255, 255, 255]

        # Watermark text positions
        left_text = wm.setdefault("left_text", {})
        for key, (x_var, y_var) in self.left_pos_vars.items():
            left_text[key] = {"x_offset": x_var.get(), "y": y_var.get()}
        right_text = wm.setdefault("right_text", {})
        for key, (x_var, y_var) in self.right_pos_vars.items():
            right_text[key] = {"x_offset": x_var.get(), "y": y_var.get()}

        # Fonts & colors
        fonts = wm.setdefault("fonts", {})
        for key, var in self.font_vars.items():
            fonts[key] = var.get()
        colors = wm.setdefault("colors", {})
        for key, var in self.color_vars.items():
            try:
                colors[key] = [int(x.strip()) for x in var.get().split(",")]
            except:
                colors[key] = [0, 0, 0]

    def reset_defaults(self):
        if messagebox.askyesno("重置", "确定恢复为默认配置吗？所有当前修改将丢失。"):
            self.settings = copy.deepcopy(DEFAULT_SETTINGS)
            self.populate_all_tabs()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('800x600')
    root.resizable(False, False)
    editor = SettingsEditor(root)
    root.mainloop()
