import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
from PIL import Image, ImageTk, ImageDraw
try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS
import os
import threading
from pathlib import Path
import shutil
import subprocess
import hashlib
import difflib

from config import GUI_CFG, CAMERA_DB, WM_CFG
from utils import ExifReader, FontManager, WatermarkGenerator, CollapsiblePanel, apply_exif_orientation
from ui_watermark import WatermarkApp
from progress_util import ProgressDialog
from hidden_watermark import DWTWatermark
from ui_settings import SettingsWindow
import piexif

class PhotoWatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Picmarker V1.3 - 图片水印工具")
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
        self._user_edits = {}  # 每张图片的用户修改参数
        self._init_ui()
        self.auto_refresh_preview()
        Path(self.output_path.get()).mkdir(parents=True, exist_ok=True)

    def _init_ui(self):
        style = ttk.Style()
        style.configure(".", font=(GUI_CFG["font_family"], GUI_CFG["font_size"]))
        style.configure("Treeview", rowheight=28, borderwidth=0)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Treeview.Item", padding=(5, 2))
        style.map("Treeview", background=[("selected", "#0078D7")])
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=1)

        # 顶部栏（仅占位，设置按钮已移至输出设置右侧）
        top_bar = ttk.Frame(main_container)
        top_bar.pack(fill=tk.X, pady=(2, 0))
        top_bar.columnconfigure(0, weight=1)

        main_pw = ttk.Frame(main_container)
        main_pw.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)
        left_frame = ttk.Frame(main_pw, width=400)
        self.left_frame = left_frame
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        # 禁止左侧面板被拖拽调整大小
        self.left_canvas = tk.Canvas(left_frame, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.left_canvas.yview)
        self.left_scroll_content = ttk.Frame(self.left_canvas)
        
        self.left_canvas.create_window((0, 0), window=self.left_scroll_content, anchor="nw", width=350, tags="inner")
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        self.left_canvas.pack(side="left", fill="both", expand=True)
        self.left_scrollbar.pack(side="right", fill="y")
        # 鼠标悬停跟踪：替代 event.widget 层级判断
        self._mouse_in_left = False

        def on_enter_left(event):
            self._mouse_in_left = True

        def on_leave_left(event):
            self._mouse_in_left = False

        def on_mousewheel_left(event):
            if isinstance(event.widget, ttk.Combobox):
                return "break"
            # 检查事件是否来自 checklist 区域
            w = event.widget
            while w:
                if w is self.checklist_canvas or w is self.checklist_inner:
                    return "break"
                w = w.master
            # 检查鼠标是否在 left_canvas 区域内
            if self._mouse_in_left:
                # 限制滚动范围，避免滚出内容顶部/底部出现空白
                bbox = self.left_canvas.bbox("all")
                if bbox:
                    top, bottom = self.left_canvas.yview()
                    delta = int(-1 * event.delta / 120)
                    if (delta < 0 and top <= 0) or (delta > 0 and bottom >= 1.0):
                        return "break"
                self.left_canvas.yview_scroll(int(-1 * event.delta / 120), "units")
                return "break"

        left_frame.bind("<Enter>", on_enter_left, add="+")
        left_frame.bind("<Leave>", on_leave_left, add="+")
        self.left_canvas.bind("<Enter>", on_enter_left, add="+")
        self.left_canvas.bind("<Leave>", on_leave_left, add="+")
        self.left_canvas.bind("<MouseWheel>", on_mousewheel_left, add="+")
        self.root.bind_all("<MouseWheel>", on_mousewheel_left, add="+")
        btn_frame = ttk.LabelFrame(self.left_scroll_content, text="图片操作", padding="3")
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="添加", width=4, command=self.select_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", width=4, command=self.delete_selected).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="全选", width=4, command=self.select_all).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="全不选", width=5, command=self.deselect_all).pack(side="left", padx=2)
        # 功能启用/禁用开关
        enable_frame = ttk.LabelFrame(self.left_scroll_content, text="功能开关", padding="3")
        enable_frame.pack(fill="x", pady=3)
        self.enable_border = tk.BooleanVar(value=False)
        self.enable_watermark = tk.BooleanVar(value=False)
        self.enable_hidden = tk.BooleanVar(value=False)
        ttk.Checkbutton(enable_frame, text="添加边框", variable=self.enable_border, command=self.show_preview).pack(side="left", padx=3)
        ttk.Checkbutton(enable_frame, text="明文水印", variable=self.enable_watermark, command=self.show_preview).pack(side="left", padx=3)
        ttk.Checkbutton(enable_frame, text="隐形水印", variable=self.enable_hidden, command=self.show_preview).pack(side="left", padx=3)
        list_frame = ttk.LabelFrame(self.left_scroll_content, text="图片列表", padding="5")
        list_frame.pack(fill="x", pady=5)
        list_frame.configure(height=200)
        list_frame.pack_propagate(False)
        # 使用 Canvas + Frame + Checkbutton 实现带滚动条的复选框列表
        self.checklist_canvas = tk.Canvas(list_frame, highlightthickness=0, bg="white")
        self.checklist_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.checklist_canvas.yview)
        self.checklist_inner = tk.Frame(self.checklist_canvas, bg="white")
        self.checklist_inner.bind("<Configure>", lambda e: self.checklist_canvas.configure(scrollregion=self.checklist_canvas.bbox("all")))
        self._checklist_window_id = self.checklist_canvas.create_window((0, 0), window=self.checklist_inner, anchor="nw")
        def _resize_checklist(event):
            self.checklist_canvas.itemconfig(self._checklist_window_id, width=event.width)
        self.checklist_canvas.bind("<Configure>", _resize_checklist)
        self.checklist_canvas.configure(yscrollcommand=self.checklist_scrollbar.set)
        self.checklist_scrollbar.pack(side="right", fill="y")
        self.checklist_canvas.pack(side="left", fill="both", expand=True)
        # 滚轮支持 - 滚动时自动切换焦点到列表
        def _on_list_mousewheel(event):
            self.checklist_canvas.focus_set()
            self.checklist_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        self.checklist_canvas.bind("<MouseWheel>", _on_list_mousewheel, add="+")
        self.checklist_inner.bind("<MouseWheel>", _on_list_mousewheel, add="+")
        # 存储复选框变量列表: list of (frame, tk.BooleanVar, filepath)
        self.check_vars = []
        panel_border = CollapsiblePanel(self.left_scroll_content, "添加边框", expanded=False)
        panel_border.pack(fill="x", pady=3)
        param_frame = ttk.LabelFrame(panel_border.content, text="水印参数")
        param_frame.pack(fill=tk.X, pady=(0, 5))
        
        #循环创建行
        rows = []
        for i in range(10):
            row = ttk.Frame(param_frame)
            row.pack(fill=tk.X, padx=8, pady=4)
            rows.append(row)
        row1, row2, row3, row4, row5, row6, row7, row8, row9, row10 = rows

        #粘贴左侧明文水印的功能到行里
        ttk.Label(row1, text="品牌：", width=6).pack(side=tk.LEFT)
        self.cbo_brand = ttk.Combobox(row1, textvariable=self.brand_var,values=list(CAMERA_DB.keys()), width=20, state="readonly")
        self.cbo_brand.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_brand.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_brand.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_brand.pack(side=tk.LEFT, padx=(0, 10))
        self.cbo_brand.bind("<<ComboboxSelected>>", self.on_brand_change)
        self.cbo_brand.bind("<KeyRelease>", lambda e: self.on_brand_change())
        self.cbo_brand.bind("<<ComboboxSelected>>", lambda e: self.show_preview(), add="+")
        ttk.Label(row2, text="相机：", width=6).pack(side=tk.LEFT)
        self.cbo_cam = ttk.Combobox(row2, textvariable=self.camera_var, width=20, state="readonly")
        self.cbo_cam.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_cam.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_cam.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_cam.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_cam.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row3, text="镜头：", width=6).pack(side=tk.LEFT)
        self.cbo_len = ttk.Combobox(row3, textvariable=self.lens_var, width=20, state="readonly")
        self.cbo_len.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_len.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_len.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_len.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_len.pack(side=tk.LEFT)
        ttk.Label(row4, text="焦距：", width=6).pack(side=tk.LEFT)
        self.cbo_focal = ttk.Entry(row4, textvariable=self.focal_var, width=20)
        self.cbo_focal.pack(side=tk.LEFT, padx=(0, 10))
        self.cbo_focal.bind("<FocusOut>", self._on_focal_focusout)
        self.cbo_focal.bind("<KeyRelease>", self._on_focal_key)
        ttk.Label(row5, text="光圈：", width=6).pack(side=tk.LEFT)
        self.cbo_f = ttk.Combobox(row5, textvariable=self.f_var, width=20, state="readonly",
                                  values = [
                                    "",
                                    "f/1.0", "f/1.1", "f/1.2",
                                    "f/1.4", "f/1.6", "f/1.8",
                                    "f/2", "f/2.2", "f/2.5",
                                    "f/2.8", "f/3.2", "f/3.5",
                                    "f/4", "f/4.5", "f/5",
                                    "f/5.6", "f/6.3", "f/7.1",
                                    "f/8", "f/9", "f/10",
                                    "f/11", "f/13", "f/14",
                                    "f/16", "f/18", "f/20",
                                    "f/22", "f/25", "f/29",
                                    "f/32", "f/36", "f/40",
                                    "f/45", "f/50", "f/57",
                                    "f/64"
                                ])
        self.cbo_f.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_f.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_f.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_f.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_f.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row6, text="快门：", width=6).pack(side=tk.LEFT)
        self.cbo_exp = ttk.Combobox(row6, textvariable=self.exp_var, width=20, state="readonly",
                                    values = [
                                        "",
                                        "1/8000s", "1/6400s", "1/5000s",
                                        "1/4000s", "1/3200s", "1/2500s",
                                        "1/2000s", "1/1600s", "1/1250s",
                                        "1/1000s", "1/800s", "1/640s",
                                        "1/500s", "1/400s", "1/320s",
                                        "1/250s", "1/200s", "1/160s",
                                        "1/125s", "1/100s", "1/80s",
                                        "1/60s", "1/50s", "1/40s",
                                        "1/30s", "1/25s", "1/20s",
                                        "1/15s", "1/13s", "1/10s",
                                        "1/8s", "1/6s", "1/5s",
                                        "1/4s", "1/3s", "1/2.5s",
                                        "1/2s", "1/1.6s", "1/1.3s",
                                        "1s", "1.3s", "1.6s",
                                        "2s", "2.5s", "3.2s",
                                        "4s", "5s", "6.3s",
                                        "8s", "10s", "13s",
                                        "16s", "20s", "25s",
                                        "30s"
                                    ])
        self.cbo_exp.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_exp.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_exp.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_exp.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_exp.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row7, text="ISO：", width=6).pack(side=tk.LEFT)
        self.cbo_iso = ttk.Combobox(row7, textvariable=self.iso_var, width=20, state="readonly",
                                    values = [
                                "", 
                                "ISO50", "ISO64", "ISO80", 
                                "ISO100", "ISO125", "ISO160", 
                                "ISO200", "ISO250", "ISO320", 
                                "ISO400", "ISO500", "ISO640", 
                                "ISO800", "ISO1000", "ISO1250", 
                                "ISO1600", "ISO2000", "ISO2500", 
                                "ISO3200", "ISO4000", "ISO5000", 
                                "ISO6400", "ISO8000", "ISO10000", 
                                "ISO12800", "ISO16000", "ISO20000", 
                                "ISO25600", "ISO32000", "ISO40000", 
                                "ISO51200", "ISO64000", "ISO80000", 
                                "ISO102400", "ISO128000", "ISO204800"
                            ])
        self.cbo_iso.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_iso.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_iso.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_iso.bind("<<ComboboxSelected>>", lambda e: self.show_preview())
        self.cbo_iso.pack(side=tk.LEFT)
        ttk.Label(row8, text="时间：", width=6).pack(side=tk.LEFT)
        self.time_year = tk.StringVar()
        self.time_month = tk.StringVar()
        self.time_day = tk.StringVar()
        self.cbo_time_y = ttk.Combobox(row8, textvariable=self.time_year, width=6, state="readonly",
                                       values=[""] + [str(y) for y in range(1839,2078)])
        self.cbo_time_y.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_y.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_y.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_y.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_y.pack(side=tk.LEFT)
        ttk.Label(row8, text="年", width=2).pack(side=tk.LEFT)
        self.cbo_time_m = ttk.Combobox(row8, textvariable=self.time_month, width=4, state="readonly",
                                       values=[""] + [f"{m:02d}" for m in range(1, 13)])
        self.cbo_time_m.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_m.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_m.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_m.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_m.pack(side=tk.LEFT)
        ttk.Label(row8, text="月", width=2).pack(side=tk.LEFT)
        self.cbo_time_d = ttk.Combobox(row8, textvariable=self.time_day, width=4, state="readonly",
                                       values=[""] + [f"{d:02d}" for d in range(1, 32)])
        self.cbo_time_d.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_d.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_d.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_d.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_d.pack(side=tk.LEFT)
        ttk.Label(row8, text="日", width=2).pack(side=tk.LEFT)
        self.time_hour = tk.StringVar()
        self.time_min = tk.StringVar()
        self.time_sec = tk.StringVar()
        ttk.Label(row9, text="", width=6).pack(side=tk.LEFT)
        self.cbo_time_h = ttk.Combobox(row9, textvariable=self.time_hour, width=4, state="readonly",
                                       values=[""] + [f"{h:02d}" for h in range(0, 24)])
        self.cbo_time_h.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_h.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_h.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_h.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_h.pack(side=tk.LEFT)
        ttk.Label(row9, text="时", width=2).pack(side=tk.LEFT)
        self.cbo_time_min = ttk.Combobox(row9, textvariable=self.time_min, width=4, state="readonly",
                                         values=[""] + [f"{mi:02d}" for mi in range(0, 60)])
        self.cbo_time_min.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_min.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_min.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_min.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_min.pack(side=tk.LEFT)
        ttk.Label(row9, text="分", width=2).pack(side=tk.LEFT)
        self.cbo_time_s = ttk.Combobox(row9, textvariable=self.time_sec, width=4, state="readonly",
                                       values=[""] + [f"{s:02d}" for s in range(0, 60)])
        self.cbo_time_s.bind("<MouseWheel>", lambda e: "break", add="+")
        self.cbo_time_s.bind("<Button-4>", lambda e: "break", add="+")
        self.cbo_time_s.bind("<Button-5>", lambda e: "break", add="+")
        self.cbo_time_s.bind("<<ComboboxSelected>>", self._on_time_change)
        self.cbo_time_s.pack(side=tk.LEFT)
        ttk.Label(row9, text="秒", width=2).pack(side=tk.LEFT)
        ttk.Label(row10, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row10, textvariable=self.selected_font,values=self.font_list, width=20, state="readonly")
        self.font_cb.bind("<MouseWheel>", lambda e: "break", add="+")
        self.font_cb.bind("<Button-4>", lambda e: "break", add="+")
        self.font_cb.bind("<Button-5>", lambda e: "break", add="+")
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
        hidden_frame = ttk.LabelFrame(panel_hidden.content, text="隐形水印设置", padding="5")
        hidden_frame.pack(fill="x", pady=2)
        self.hidden_pwd_label = ttk.Label(hidden_frame, text="密码:")
        self.hidden_pwd_label.grid(row=0, column=0, sticky=tk.W)
        self.hidden_pwd = tk.StringVar(value="123456")#默认密码是123456
        self.hidden_pwd_entry = ttk.Entry(hidden_frame, textvariable=self.hidden_pwd, width=20, show="•")
        self.hidden_pwd_entry.grid(row=0, column=1, padx=5)
        self.hidden_text_label = ttk.Label(hidden_frame, text="加密内容:")
        self.hidden_text_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.hidden_text = tk.StringVar(value="版权信息")
        self.hidden_text_entry = ttk.Entry(hidden_frame, textvariable=self.hidden_text, width=20)
        self.hidden_text_entry.grid(row=1, column=1, padx=5, pady=(5,0))
        tk.Label(hidden_frame, text="处理速度较慢，请耐心等待", foreground="red", bg="#f0f0f0", font=("Microsoft YaHei", 11, "bold")).grid(row=2, column=0, columnspan=2, pady=8)
        # 嵌入/提取模式选择
        self.hidden_mode = tk.StringVar(value="embed")
        mode_frame = ttk.Frame(hidden_frame)
        mode_frame.grid(row=3, column=0, columnspan=2, pady=3)
        ttk.Radiobutton(mode_frame, text="嵌入", variable=self.hidden_mode, value="embed", command=self._toggle_hidden_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="提取", variable=self.hidden_mode, value="extract", command=self._toggle_hidden_mode).pack(side=tk.LEFT, padx=5)
        self.hidden_hint = ttk.Label(hidden_frame, text="启用隐形水印开关后，处理将自动嵌入", foreground="gray")
        self.hidden_hint.grid(row=5, column=0, columnspan=2, pady=(10,0))
        right_frame = ttk.Frame(main_pw)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_frame = ttk.LabelFrame(right_frame, text="输出设置")
        path_frame.pack(fill=tk.X, pady=(0, 5))
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(path_inner, text="保存路径：").pack(side=tk.LEFT)
        ttk.Entry(path_inner, textvariable=self.output_path, width=40).pack(side=tk.LEFT, padx=6)
        ttk.Button(path_inner, text="浏览...", command=self.select_out_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(path_inner, text="软件设置", command=self.open_settings).pack(side=tk.RIGHT, padx=2)
        preview_frame = ttk.LabelFrame(right_frame, text="效果预览")
        preview_frame.pack(fill=tk.BOTH, expand=1, pady=(0, 5))
        preview_ctrl = ttk.Frame(preview_frame)
        preview_ctrl.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(preview_ctrl, text="上一张", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(preview_ctrl, text="下一张", command=self.next_image).pack(side=tk.LEFT, padx=2)
        self.preview_label = ttk.Label(preview_ctrl, text="")
        self.preview_label.pack(side=tk.LEFT, padx=10)
        self.canvas = tk.Canvas(preview_frame, bg="#f5f5f5", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=1, padx=4, pady=4)
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=6)
        ttk.Button(action_frame, text="刷新预览", command=self.show_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="处理照片", command=self.start_batch).pack(side=tk.RIGHT, padx=2)
        self.canvas.bind("<Configure>", lambda e: self.root.after(200, self.show_preview))
        def _toggle_left_scrollbar():
                    """根据内容高度决定滚动条显隐"""
                    bbox = self.left_canvas.bbox("all")
                    if bbox:
                        canvas_h = self.left_canvas.winfo_height()
                        content_h = bbox[3]
                        if content_h > canvas_h:
                            self.left_scrollbar.pack(side="right", fill="y")
                        else:
                            self.left_scrollbar.pack_forget()

        def update_left_scroll_region(event=None):
            """更新左侧 Canvas 的滚动区域"""
            self.left_scroll_content.update_idletasks()
            bbox = self.left_canvas.bbox("all")
            if bbox and bbox[3] > 0:
                self.left_canvas.configure(scrollregion=bbox)
                _toggle_left_scrollbar()
            else:
                self.left_canvas.configure(scrollregion=(0, 0, 0, 0))
                self.left_scrollbar.pack_forget()

        self.left_scroll_content.bind("<Configure>", update_left_scroll_region)

    def auto_refresh_preview(self):
        # 仅首次加载时显示预览，后续由各控件按需触发
        if not self._cached_preview_path:
            self.show_preview()

    def _save_current_edits(self):
        #保存当前图片的用户修改
        if self.current_index >= 0:
            old = self._user_edits.get(self.current_index, {})
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
                "photo_name": self.photo_name_var.get().strip(),
                "_has_exif": old.get("_has_exif", False)
            }

    def prev_image(self):
        if not self.input_files:
            return
        if self.current_index > 0:
            self._save_current_edits()
            self.current_index -= 1
            self._update_preview_for_current()
    def next_image(self):
        if not self.input_files:
            return
        if self.current_index < len(self.input_files) - 1:
            self._save_current_edits()
            self.current_index += 1
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
        rejected = []
        for f in files:
            if f not in self.input_files:
                # 检查长边比短边是否 > 3:1，超宽图剔除
                try:
                    with Image.open(f) as img:
                        w, h = img.size
                        if max(w, h) / min(w, h) > 3.0:
                            rejected.append(os.path.basename(f))
                            continue
                except Exception:
                    pass
                self.input_files.append(f)
                self._add_checklist_row(f)
                added += 1
        if rejected:
            messagebox.showwarning(
                "已剔除超宽图片",
                f"以下 {len(rejected)} 张图片长宽比超过 3:1，不符合规范，已剔除：\n\n" + "\n".join(rejected)
            )
        if added > 0:
            # 自动选择最后导入的图片
            self.current_index = len(self.input_files) - 1
            self._update_preview_for_current()
            self._highlight_checklist_row(self.current_index)
            # 后台生成所有图片的缩略图缓存
            threading.Thread(target=self._precache_all_thumbnails, daemon=True).start()
    def delete_selected(self):
        # 获取所有勾选的行
        checked_indices = [i for i, (_, var, _) in enumerate(self.check_vars) if var.get()]
        if not checked_indices:
            messagebox.showinfo("提示", "请先勾选要删除的照片")
            return
        count = len(checked_indices)
        if count == 1:
            filename = os.path.basename(self.input_files[checked_indices[0]])
            if not messagebox.askyesno("确认删除", f"确定要删除 {filename} 吗？"):
                return
        else:
            if not messagebox.askyesno("确认删除", f"确定要删除勾选的 {count} 张照片吗？"):
                return
        # 从后往前删除，避免索引变化
        for idx in reversed(checked_indices):
            frame, _, _ = self.check_vars.pop(idx)
            frame.destroy()
            del self.input_files[idx]
            # 【修复】同步删除_user_edits对应条目
            if idx in self._user_edits:
                del self._user_edits[idx]
        
        # 【修复】重新映射_user_edits索引，保证与input_files一一对应
        if self._user_edits:
            new_edits = {}
            sorted_old = sorted(self._user_edits.keys())
            for new_idx, old_idx in enumerate(sorted_old):
                new_edits[new_idx] = self._user_edits[old_idx]
            self._user_edits = new_edits

        if not self.input_files:
            self.current_index = -1
            self._user_edits.clear()
            self.canvas.delete("all")
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
            self.cbo_brand.config(state="readonly")
            self.cbo_cam.config(state="readonly")
            self.cbo_len.config(state="readonly")
            self.cbo_focal.config(state="normal")
            self.cbo_f.config(state="normal")
            self.cbo_exp.config(state="normal")
            self.cbo_iso.config(state="normal")
            self.cbo_time_y.config(state="readonly")
            self.cbo_time_m.config(state="readonly")
            self.cbo_time_d.config(state="readonly")
            self.cbo_time_h.config(state="readonly")
            self.cbo_time_min.config(state="readonly")
            self.cbo_time_s.config(state="readonly")
        else:
            if self.current_index >= len(self.input_files):
                self.current_index = len(self.input_files) - 1
            self._update_preview_for_current()
    def select_all(self):
        for _, var, _ in self.check_vars:
            var.set(True)

    def deselect_all(self):
        for _, var, _ in self.check_vars:
            var.set(False)

    def clear_all(self):
        if self.input_files and messagebox.askyesno("确认清空", "确定要清空所有照片吗？"):
            self.input_files = []
            self.current_index = -1
            self._user_edits.clear()
            for frame, _, _ in self.check_vars:
                frame.destroy()
            self.check_vars.clear()
            self.canvas.delete("all")
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
            self.cbo_brand.config(state="readonly")
            self.cbo_cam.config(state="readonly")
            self.cbo_len.config(state="readonly")
            self.cbo_focal.config(state="normal")
            self.cbo_f.config(state="normal")
            self.cbo_exp.config(state="normal")
            self.cbo_iso.config(state="normal")
            self.cbo_time.config(state="normal")
    
    def _update_checklist_scrollregion(self):
        """强制更新图片列表 Canvas 的滚动区域"""
        self.checklist_inner.update_idletasks()          # 确保子控件布局完成
        self.checklist_canvas.configure(
            scrollregion=self.checklist_canvas.bbox("all")
        )

    def _add_checklist_row(self, filepath):
        """在复选框列表中添加一行"""
        var = tk.BooleanVar(value=True)
        row = tk.Frame(self.checklist_inner, bg="white")
        row.pack(fill="x", padx=2, pady=1)
        cb = tk.Checkbutton(row, variable=var, bg="white", activebackground="white")
        cb.pack(side="left")
        lbl = tk.Label(row, text=os.path.basename(filepath), bg="white",
                       anchor="w", padx=5)
        lbl.pack(side="left", fill="x", expand=True)
                # 绑定点击事件到 row 和 Label（Checkbutton 自己处理点击）
        for widget in (row, lbl):
            widget.bind("<Button-1>", self._on_checklist_click)
            cb.bind("<Button-1>", self._on_checkbutton_click, add="+")
        # 为所有子控件绑定滚轮事件
        def _row_mousewheel(event):
            self.checklist_canvas.focus_set()
            self.checklist_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        for widget in (row, cb, lbl):
            widget.bind("<MouseWheel>", _row_mousewheel, add="+")
        self.check_vars.append((row, var, filepath))
        self._update_checklist_scrollregion()


    def _on_checkbutton_click(self, event):
        """Checkbutton 点击：切换预览并高亮，保留原生勾选切换逻辑"""
        widget = event.widget
        for i, (frame, var, path) in enumerate(self.check_vars):
            w = widget
            while w and w != self.checklist_inner:
                if w == frame or w.master == frame:
                    # 【修复】移除手动var翻转，避免与原生行为冲突导致状态不变
                    if self.current_index >= 0:
                        self._save_current_edits()
                    self.current_index = i
                    self._update_preview_for_current()
                    self._highlight_checklist_row(i)
                    return
                w = w.master

    def _on_checklist_click(self, event):
        """单击行切换预览并高亮，不干涉复选框选中状态"""
        widget = event.widget
        # 【修复】移除调试用的标题修改代码
        for i, (frame, var, path) in enumerate(self.check_vars):
            w = widget
            while w and w != self.checklist_inner:
                if w == frame or w.master == frame:
                    if self.current_index >= 0:
                        self._save_current_edits()
                    self.current_index = i
                    self._update_preview_for_current()
                    self._highlight_checklist_row(i)
                    return "break"
                w = w.master

    def _highlight_checklist_row(self, index):
        """高亮当前选中的行（用背景色）"""
        for i, (frame, var, path) in enumerate(self.check_vars):
            bg = "#E0F0FF" if i == index else "white"
            frame.configure(bg=bg)
            for child in frame.winfo_children():
                if isinstance(child, (tk.Checkbutton, tk.Label)):
                    child.configure(bg=bg, activebackground=bg)
    def _update_preview_for_current(self):
        if self.current_index < 0 or self.current_index >= len(self.input_files):
            return
        path = self.input_files[self.current_index]
        filename = os.path.basename(path)
        # 保存当前用户修改，切换图片时恢复
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
                "photo_name": "",
                "_has_exif": bool(info.get("camera_model") or info.get("lens_model"))
            }
            self._user_edits[self.current_index] = edits
        # 存在相机/镜头 EXIF 时禁用自定义选择，否则允许自定义
        has_exif = edits.get("_has_exif", False)
        state = "disabled" if has_exif else "readonly"
        self.cbo_brand.config(state=state)
        self.cbo_cam.config(state=state)
        self.cbo_len.config(state=state)
        # 焦距：EXIF 存在时禁用，否则允许输入
        self.cbo_focal.config(state="disabled" if has_exif else "normal")
        # 光圈/快门/ISO：EXIF 存在时禁用，否则允许选择
        for cbo in (self.cbo_f, self.cbo_exp, self.cbo_iso):
            cbo.config(state="disabled" if has_exif else "readonly")
        # 时间：始终允许用户修改年月日时分秒
        self.cbo_time_y.config(state="readonly")
        self.cbo_time_m.config(state="readonly")
        self.cbo_time_d.config(state="readonly")
        self.cbo_time_h.config(state="readonly")
        self.cbo_time_min.config(state="readonly")
        self.cbo_time_s.config(state="readonly")
        self.brand_var.set(edits["brand"])
        self.on_brand_change()
        self.camera_var.set(edits["camera"])
        self.lens_var.set(edits["lens"])
        # 镜头不在数据库时，匹配最相似的镜头
        self._match_lens_to_db()
        self.focal_var.set(edits["focal"])
        self.f_var.set(edits["f"])
        self.exp_var.set(edits["exp"])
        self.iso_var.set(edits["iso"])
        self._set_time_parts(edits["datetime"])
        self.loc_var.set(edits["location"])
        self.photo_name_var.set(edits["photo_name"])
        self.root.after(100, self.show_preview)
    def _match_lens_to_db(self):
        """镜头不在数据库时，匹配最相似的镜头"""
        brand = self.brand_var.get().strip()
        if brand not in CAMERA_DB:
            return
        lens = CAMERA_DB[brand].get("lenses", [])
        cur = self.lens_var.get().strip()
        if cur and cur not in lens:
            best = difflib.get_close_matches(cur, lens, n=1, cutoff=0.3)
            if best:
                self.lens_var.set(best[0])

    def on_brand_change(self, event=None):
        brand = self.brand_var.get().strip()
        if brand in CAMERA_DB:
            cams = CAMERA_DB[brand].get("cameras", [])
            lens = CAMERA_DB[brand].get("lenses", [])
            self.cbo_cam.config(values=cams)
            self.cbo_len.config(values=lens)
            self._match_lens_to_db()

    def _on_focal_key(self, event=None):
        """焦距输入：只允许数字和连字符"""
        val = self.focal_var.get()
        # 移除非法字符
        cleaned = "".join(c for c in val if c.isdigit() or c == "-")
        if cleaned != val:
            self.focal_var.set(cleaned)

    def _on_focal_focusout(self, event=None):
        """焦距失焦：自动补 mm，空则不补"""
        val = self.focal_var.get().strip()
        if val and not val.endswith("mm"):
            self.focal_var.set(f"{val}mm")
        self.show_preview()

    def _on_time_change(self, event=None):
        """年月日时分秒组合成时间字符串"""
        y = self.time_year.get().strip()
        m = self.time_month.get().strip()
        d = self.time_day.get().strip()
        h = self.time_hour.get().strip()
        mi = self.time_min.get().strip()
        s = self.time_sec.get().strip()
        if y and m and d:
            base = f"{y}-{m}-{d}"
            if h and mi and s:
                self.time_var.set(f"{base} {h}:{mi}:{s}")
            else:
                self.time_var.set(base)
        else:
            self.time_var.set("")
        # 同步保存到当前图片的用户修改
        if self.current_index in self._user_edits:
            self._user_edits[self.current_index]["datetime"] = self.time_var.get().strip()
        self.show_preview()

    def _set_time_parts(self, dt):
        """把时间字符串拆分到年月日时分秒下拉框"""
        self.time_year.set("")
        self.time_month.set("")
        self.time_day.set("")
        self.time_hour.set("")
        self.time_min.set("")
        self.time_sec.set("")
        if dt:
            parts = str(dt).replace("T", " ").split()
            date_part = parts[0].split("-") if parts else []
            time_part = parts[1].split(":") if len(parts) > 1 else []
            if len(date_part) >= 3:
                self.time_year.set(date_part[0])
                self.time_month.set(date_part[1])
                self.time_day.set(date_part[2])
            if len(time_part) >= 3:
                self.time_hour.set(time_part[0])
                self.time_min.set(time_part[1])
                self.time_sec.set(time_part[2])
            # 同步设置完整时间字符串，供水印渲染使用
            self.time_var.set(str(dt).strip())
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
                    img = apply_exif_orientation(img)
                    scale = min(800/img.width, 600/img.height, 1.0)
                    thumb = img.resize((int(img.width*scale), int(img.height*scale)), RESAMPLE)
                    thumb.convert("RGB").save(cache_path, quality=85)
            except:
                pass

    def _get_preview_hash(self):
        """生成当前预览参数的确定性哈希值"""
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
                # 三个功能都未启用时，只显示原图缩略图，不进行任何处理
        has_any_func = self.enable_border.get() or self.enable_watermark.get() or self.enable_hidden.get()
        if not has_any_func:
            dlg = ProgressDialog(self.root, "加载预览...", maximum=1)
            dlg.set_text("正在渲染预览图")
            self.root.update()
            try:
                img_path = self.input_files[self.current_index]
                cw = max(self.canvas.winfo_width(), 100)
                ch = max(self.canvas.winfo_height(), 100)
                with Image.open(img_path) as img:
                    img = apply_exif_orientation(img)
                    scale = min((cw-20)/img.width, (ch-20)/img.height, 1.0)
                    thumb = img.resize((int(img.width*scale), int(img.height*scale)), RESAMPLE)
                self.preview_img = ImageTk.PhotoImage(thumb)
                self.canvas.delete("all")
                self.canvas.create_image(cw//2, ch//2, image=self.preview_img, anchor=tk.CENTER)
                self.preview_label.config(text=f"预览: {os.path.basename(self.input_files[self.current_index])}")
                dlg.set_progress(1)
                dlg.close()
                return
            except Exception as e:
                dlg.close()
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
                dlg = ProgressDialog(self.root, "生成预览...", maximum=4)
                dlg.set_text("正在渲染预览图")
                self.root.update()
                # 1. 打开原图，缩放到适配画布的预览尺寸
                with Image.open(img_path) as full_img:
                    full_img = apply_exif_orientation(full_img)
                    original_size = full_img.size  # 保存原图尺寸，供水印比例校准使用
                    # 预留边框高度空间，避免边框文字超出画布底部
                    if self.enable_border.get():
                        est_scale = (cw-20) / full_img.width
                        est_bar_h = int(WM_CFG["base_bar_height"] * est_scale)
                        est_bar_h = max(20, min(est_bar_h, int((cw-20)/5)))
                        scale = min((cw-20)/full_img.width, (ch-20-est_bar_h)/full_img.height, 1.0)
                    else:
                        scale = min((cw-20)/full_img.width, (ch-20)/full_img.height, 1.0)
                    thumb_size = (int(full_img.width*scale), int(full_img.height*scale))
                    thumb = full_img.resize(thumb_size, RESAMPLE).convert("RGBA")


                dlg.set_progress(1)

                # 2. 调用统一核心方法渲染边框水印（与正式生成算法100%一致）
                if self.enable_border.get():
                    data = self.get_data()
                    font_name = self.selected_font.get()
                    # 核心：直接复用 render_border，无需手动计算缩放
                    bordered = WatermarkGenerator.render_border(thumb, data, font_name)
                    thumb = bordered.convert("RGBA")
                dlg.set_progress(2)

                                # 3. 叠加明文水印（全尺寸渲染后整体缩放，保证与实际输出比例100%一致）
                if self.enable_watermark.get() and self.simple_watermark_panel:
                    wm = self.simple_watermark_panel
                    wm_text = wm.watermark_text.get().strip()
                    if wm_text:
                        # 使用原始字号渲染，参数和正式批量输出完全一致
                        base_font_size = int(wm.font_size.get())
                        font = wm.get_font(wm.font_family.get(), base_font_size, wm.is_bold.get())
                        color = wm.color_map[wm.font_color_var.get()]
                        
                        # 创建与原图同尺寸的透明水印层，布局和实际生成完全相同
                        full_overlay = Image.new("RGBA", original_size, (0, 0, 0, 0))
                        wm.add_scattered_watermarks(full_overlay, wm_text, font, color)
                        
                        # 将水印层缩放到当前预览图尺寸，再叠加
                        preview_overlay = full_overlay.resize(thumb.size, RESAMPLE)
                        thumb = thumb.convert("RGBA")
                        thumb = Image.alpha_composite(thumb, preview_overlay)




                # 4. 保存预览缓存
                tmp_thumb = temp_dir / f"_preview_{cur_hash}.jpg"
                thumb.convert("RGB").save(tmp_thumb, quality=85)
                self._cached_preview_path = tmp_thumb
                self._cached_params["hash"] = cur_hash
                im = Image.open(tmp_thumb)
                dlg.set_progress(4)
                dlg.close()

            self.preview_img = ImageTk.PhotoImage(im)
            self.canvas.delete("all")
            self.canvas.create_image(cw//2, ch//2, image=self.preview_img, anchor=tk.CENTER)
            self.preview_label.config(text=f"预览: {os.path.basename(self.input_files[self.current_index])}")
        except Exception as e:
            print(f"[预览渲染异常] 图片: {os.path.basename(img_path)}, 错误: {e}")
            import traceback
            traceback.print_exc()
            if 'dlg' in dir():
                dlg.close()

    def start_batch(self):
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加照片")
            return
        # 获取所有勾选的图片索引
        checked_indices = [i for i, (_, var, _) in enumerate(self.check_vars) if var.get()]
        if not checked_indices:
            messagebox.showwarning("提示", "请先勾选要处理的图片")
            return
        if not messagebox.askyesno("确认处理", f"将处理 {len(checked_indices)} 张照片，是否继续？"):
            return
        # 检查是否有任何功能启用
        has_any_func = self.enable_border.get() or self.enable_watermark.get() or self.enable_hidden.get()
        if not has_any_func:
            messagebox.showwarning("提示", "请至少勾选一项功能（添加边框、明文水印、隐形水印）")
            return
        os.makedirs(self.output_path.get(), exist_ok=True)
        font = self.selected_font.get()
        # 【修复】处理前保存当前图片的用户修改，确保手动填写的参数生效
        self._save_current_edits()
        total = len(checked_indices)
        dlg = ProgressDialog(self.root, "处理...", maximum=total)
        dlg.set_text(f"正在处理 0/{total}")
        self.root.update()    
        def worker():
            success = 0
            is_extract = self.hidden_mode.get() == "extract" and self.enable_hidden.get()
            # 【修复】遍历索引，每张图片使用自身的参数
            for idx_in_list, file_idx in enumerate(checked_indices):
                f = self.input_files[file_idx]
                name = os.path.basename(f)
                out = os.path.join(self.output_path.get(), f"Watermark_{name}")
                try:
                    if is_extract:
                        # 提取模式：直接从原图提取，不生成输出文件
                        pwd = self.hidden_pwd.get().strip()
                        pwd_int = int(pwd)
                        bw = DWTWatermark(password=pwd_int)
                        extracted = bw.extract(f)
                        result_text = f"隐形水印提取 {name}: {extracted}"
                        print(result_text)
                        self.root.after(0, lambda r=result_text: messagebox.showinfo("提取结果", r))
                    else:
                        # 获取当前图片的专属参数
                        if file_idx in self._user_edits:
                            data = self._user_edits[file_idx]
                        else:
                            info = ExifReader.get_exif_full(f)
                            data = {
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
                        if self.enable_border.get():
                            WatermarkGenerator.add_watermark(f, out, data, font)
                        else:
                            shutil.copy2(f, out)
                        if self.enable_watermark.get() and self.simple_watermark_panel:
                            wm = self.simple_watermark_panel
                            if wm.watermark_text.get().strip():
                                img = apply_exif_orientation(Image.open(out)).convert("RGBA")
                                wm_font = wm.get_font(wm.font_family.get(), wm.font_size.get(), wm.is_bold.get())
                                color = wm.color_map[wm.font_color_var.get()]
                                wm.add_scattered_watermarks(img, wm.watermark_text.get(), wm_font, color)
                                img.convert("RGB").save(out, quality=95)
                                # 恢复 EXIF（图片已按方向旋转，重置 Orientation 为 1）
                                try:
                                    exif_dict = piexif.load(f)
                                    exif_dict['0th'][piexif.ImageIFD.Orientation] = 1
                                    exif_bytes = piexif.dump(exif_dict)
                                    piexif.insert(exif_bytes, out)
                                except:
                                    pass
                                                # 隐形水印嵌入
                        if self.enable_hidden.get():
                            try:
                                pwd = self.hidden_pwd.get().strip()
                                pwd_int = int(pwd)
                                bw = DWTWatermark(password=pwd_int)
                                text = self.hidden_text.get().strip()
                                if pwd and text:
                                    bw.embed(out, text, out)
                            except Exception as e:
                                print(f"隐形水印嵌入失败 {name}: {e}")
                        success += 1
                except Exception as e:
                    print(f"处理失败 {name}: {e}")
                self.root.after(0, lambda v=idx_in_list+1: dlg.set_progress(v))
                self.root.after(0, lambda v=f"{idx_in_list+1}/{total}": dlg.set_text(f"正在处理 {v}"))
            self.root.after(0, dlg.close)
            if not is_extract:
                self.root.after(0, lambda: messagebox.showinfo("处理完成", f"成功处理 {success}/{total} 张照片\n保存位置: {self.output_path.get()}"))
        threading.Thread(target=worker, daemon=True).start()
    
    def open_settings(self):
        SettingsWindow(self.root)

    def _toggle_hidden_mode(self):
        if self.hidden_mode.get() == "embed":
            self.hidden_text_label.grid()
            self.hidden_text_entry.grid()
            self.hidden_pwd_label.grid()
            self.hidden_pwd_entry.grid()
            self.hidden_hint.config(text="启用隐形水印开关后，处理将自动嵌入")
        else:
            self.hidden_text_label.grid_remove()
            self.hidden_text_entry.grid_remove()
            self.hidden_pwd_label.grid()
            self.hidden_pwd_entry.grid()
            self.hidden_hint.config(text="启用隐形水印开关后，处理将自动提取")
            # 提取模式下自动取消边框和明文水印的勾选
            self.enable_border.set(False)
            self.enable_watermark.set(False)

        

    
    

    