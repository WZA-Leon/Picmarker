# ui_main.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
from PIL import Image, ImageTk
try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS
import os
import threading
from pathlib import Path
import shutil
import subprocess

from config import GUI_CFG, CAMERA_DB
from utils import ExifReader, FontManager, WatermarkGenerator, CollapsiblePanel
from ui_watermark import WatermarkApp


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
        self.enable_border = tk.BooleanVar(value=False)
        self.enable_watermark = tk.BooleanVar(value=False)
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
        
        #循环创建行
        rows = []
        for i in range(8):
            row = ttk.Frame(param_frame)
            row.pack(fill=tk.X, padx=8, pady=4)
            rows.append(row)
        row1, row2, row3, row4, row5, row6, row7, row8 = rows

        #粘贴左侧明文水印的功能到行里
        ttk.Label(row1, text="品牌：", width=6).pack(side=tk.LEFT)
        self.cbo_brand = ttk.Combobox(row1, textvariable=self.brand_var,values=list(CAMERA_DB.keys()), width=20, state="readonly")
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
        ttk.Label(row4, text="焦距：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row4, textvariable=self.focal_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row5, text="光圈：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row5, textvariable=self.f_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row6, text="快门：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row6, textvariable=self.exp_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row7, text="ISO：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row7, textvariable=self.iso_var, width=20, state="readonly").pack(side=tk.LEFT)
        ttk.Label(row8, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row8, textvariable=self.selected_font,values=self.font_list, width=20, state="readonly")
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
            # 后台生成所有图片的缩略图缓存
            threading.Thread(target=self._precache_all_thumbnails, daemon=True).start()
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
    def _precache_all_thumbnails(self):
        """后台预生成所有图片的缩略图缓存"""
        temp_dir = Path(__file__).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        for path in self.input_files:
            img_hash = hash(path) & 0xFFFFFFFF
            cache_path = temp_dir / f"_thumb_{img_hash:x}.jpg"
            if cache_path.exists():
                continue
            try:
                with Image.open(path) as img:
                    scale = min(800/img.width, 600/img.height, 1.0)
                    thumb = img.resize((int(img.width*scale), int(img.height*scale)), RESAMPLE)
                    thumb.convert("RGB").save(cache_path, quality=85)
            except:
                pass

    def _get_preview_hash(self):
        """生成当前预览参数的确定性哈希值"""
        import hashlib
        data = self.get_data()
        wm = self.simple_watermark_panel
        wm_text = wm.watermark_text.get() if wm else ""
        wm_font = wm.font_family.get() if wm else ""
        wm_size = wm.font_size.get() if wm else 0
        wm_color = wm.font_color_var.get() if wm else ""
        raw = f"{self.current_index}|{self.enable_border.get()}|{self.enable_watermark.get()}|{self.selected_font.get()}|{data['brand']}|{data['camera']}|{data['lens']}|{data['photo_name']}|{data['focal']}|{data['f']}|{data['exp']}|{data['iso']}|{data['datetime']}|{data['location']}|{wm_text}|{wm_font}|{wm_size}|{wm_color}"
        return hashlib.md5(raw.encode()).hexdigest()

    def show_preview(self):
        if not self.input_files or self.current_index == -1:
            return
        try:
            temp_dir = Path(__file__).parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            img_path = self.input_files[self.current_index]
            cw = max(self.canvas.winfo_width(), 100)
            ch = max(self.canvas.winfo_height(), 100)
            cur_hash = self._get_preview_hash()
            if self._cached_params.get("hash") == cur_hash and self._cached_preview_path and self._cached_preview_path.exists():
                im = Image.open(self._cached_preview_path)
            else:
                # 1. 打开原图缩略到预览尺寸
                with Image.open(img_path) as full_img:
                    scale = min((cw-20)/full_img.width, (ch-20)/full_img.height, 1.0)
                    thumb_size = (int(full_img.width*scale), int(full_img.height*scale))
                    thumb = full_img.resize(thumb_size, RESAMPLE).convert("RGBA")

                # 2. 在缩略图上直接绘制边框水印（按比例缩放参数）
                if self.enable_border.get():
                    from PIL import ImageDraw
                    data = self.get_data()
                    font_name = self.selected_font.get()
                    tw, th = thumb.size
                                        # 计算原图→缩略图的比例（用宽度比，确保宽高比一致）
                    with Image.open(img_path) as full_img:
                        scale_ratio = tw / full_img.width
                    from config import WM_CFG
                    bar_h = int(WM_CFG["bar_height"] * scale_ratio)
                    bg = tuple(WM_CFG["background_color"])
                    bordered = Image.new("RGBA", (tw, th + bar_h), bg + (255,))
                    bordered.paste(thumb, (0, 0))
                    draw = ImageDraw.Draw(bordered)
                    fc = WM_CFG["fonts"]
                    colors = WM_CFG["colors"]
                    font_cam = WatermarkGenerator.get_font(font_name, max(1, int(fc["camera"] * scale_ratio)))
                    font_len = WatermarkGenerator.get_font(font_name, max(1, int(fc["lens"] * scale_ratio)))
                    font_param = WatermarkGenerator.get_font(font_name, max(1, int(fc["params"] * scale_ratio)))
                    font_time = WatermarkGenerator.get_font(font_name, max(1, int(fc["time"] * scale_ratio)))
                     # 加载图标，与 add_watermark 一致：固定高度 icon_max_height，再按 scale_ratio 缩放
                    icon = WatermarkGenerator.load_brand_icon(data["brand"])
                    icon_h = max(1, int(icon.height * scale_ratio))
                    icon = icon.resize((max(1, int(icon.width * scale_ratio)), icon_h), RESAMPLE)
                    icon_left = int(WM_CFG["icon_margin_left"] * scale_ratio)
                    icon_y = th + (bar_h - icon.height) // 2
                    bordered.paste(icon, (icon_left, icon_y), icon)
                    left_x = icon_left + icon.width + int(WM_CFG["icon_margin_right"] * scale_ratio)
                    base_y = th + (bar_h // 2) - int(WM_CFG["vertical_center_offset"] * scale_ratio)
                    stroke_en = WM_CFG["stroke"]["enabled"]
                    stroke_w = int(WM_CFG["stroke"]["width"] * scale_ratio) if stroke_en else 0
                    stroke_c = tuple(WM_CFG["stroke"]["fill"]) if stroke_en else None
                    left_cfg = WM_CFG["left_text"]
                    draw.text((left_x + int(left_cfg["camera"]["x_offset"] * scale_ratio),
                               base_y + int(left_cfg["camera"]["y"] * scale_ratio)),
                              data["camera"], fill=tuple(colors["camera"]), font=font_cam,
                              stroke_width=stroke_w, stroke_fill=stroke_c)
                    draw.text((left_x + int(left_cfg["lens"]["x_offset"] * scale_ratio),
                               base_y + int(left_cfg["lens"]["y"] * scale_ratio)),
                              data["lens"], fill=tuple(colors["lens"]), font=font_len,
                              stroke_width=stroke_w, stroke_fill=stroke_c)
                    right_cfg = WM_CFG["right_text"]
                    param_text = f"{data['focal']}  {data['f']}  {data['exp']}  {data['iso']}"
                    time_text = f"{data['datetime']}"
                    param_w = draw.textlength(param_text, font=font_param)
                    time_w = draw.textlength(time_text, font=font_time)
                    draw.text((tw + int(right_cfg["params"]["x_offset"] * scale_ratio) - param_w,
                               base_y + int(right_cfg["params"]["y"] * scale_ratio)),
                              param_text, fill=tuple(colors["params"]), font=font_param,
                              stroke_width=stroke_w, stroke_fill=stroke_c)
                    draw.text((tw + int(right_cfg["time"]["x_offset"] * scale_ratio) - time_w,
                               base_y + int(right_cfg["time"]["y"] * scale_ratio)),
                              time_text, fill=tuple(colors["time"]), font=font_time,
                              stroke_width=stroke_w, stroke_fill=stroke_c)
                    thumb = bordered

                # 3. 在缩略图上叠加明文水印
                if self.enable_watermark.get() and self.simple_watermark_panel:
                    wm = self.simple_watermark_panel
                    if wm.watermark_text.get().strip():
                        font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                        color = wm.color_map[wm.font_color_var.get()]
                        overlay = Image.new("RGBA", thumb.size, (0, 0, 0, 0))
                        wm.add_scattered_watermarks(overlay, wm.watermark_text.get(), font, color)
                        thumb = Image.alpha_composite(thumb, overlay)

                                # 4. 保存预览缩略图到缓存（使用参数哈希，避免覆盖后台缓存）
                tmp_thumb = temp_dir / f"_preview_{cur_hash}.jpg"
                thumb.convert("RGB").save(tmp_thumb, quality=85)
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
            if self.enable_border.get():
                WatermarkGenerator.add_watermark(path, out, self.get_data(), self.selected_font.get())
            else:
                shutil.copy2(path, out)
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
                    if self.enable_border.get():
                        WatermarkGenerator.add_watermark(f, out, data, font)
                    else:
                        shutil.copy2(f, out)
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
            messagebox.showwarning("提示", "请先添加照片")
            return
        pwd = self.hidden_pwd.get().strip()
        text = self.hidden_text.get().strip()
        if not pwd or not text:
            messagebox.showerror("错误", "密码和加密内容不能为空")
            return
        total = len(self.input_files)
        output_dir = self.output_path.get()
        os.makedirs(output_dir, exist_ok=True)
        messagebox.showinfo("提示", "盲水印功能尚未实现")

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
                self.root.after(0, lambda: self.status_var.set("❌ 未安装 blind-watermark 库"))
                self.root.after(0, lambda: messagebox.showerror("错误", "请先安装 blind-watermark"))
                return

            try:
                bw = WaterMark(password_img=int(pwd), password_wm=int(pwd))
                # 其余代码保持不变（读取图片、提取等）
                from PIL import Image
                import numpy as np
                pil_img = Image.open(path).convert('RGB')
                img_cv = np.array(pil_img)[:, :, ::-1]
                len_path = path + '.len'
                if os.path.exists(len_path):
                    with open(len_path) as lf:
                        wm_shape = int(lf.read())
                else:
                    self.root.after(0, lambda: self.status_var.set("❌ 缺少水印长度信息"))
                    self.root.after(0, lambda: messagebox.showerror("错误", "找不到 .len 文件"))
                    return
                wm_extract = bw.extract(embed_img=img_cv, wm_shape=wm_shape, mode='str')
                self.root.after(0, lambda: self.status_var.set("✅ 提取成功"))
                self.root.after(0, lambda: messagebox.showinfo("提取结果",
                    f"图片: {os.path.basename(path)}\n密码: {pwd}\n\n提取内容:\n{wm_extract}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set("❌ 提取失败"))
                self.root.after(0, lambda: messagebox.showerror("提取失败", f"密码错误或图片不含盲水印\n\n{str(e)}"))

        threading.Thread(target=worker, daemon=True).start()
    

    