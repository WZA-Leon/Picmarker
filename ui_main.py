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
from progress_util import ProgressDialog
from hidden_watermark import DWTWatermark
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
        main_pw = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_pw.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)
        left_frame = ttk.Frame(main_pw, width=400)
        self.left_frame = left_frame
        main_pw.add(left_frame, weight=0)
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
                self.left_canvas.yview_scroll(int(-1 * event.delta / 120), "units")
                return "break"

        left_frame.bind("<Enter>", on_enter_left, add="+")
        left_frame.bind("<Leave>", on_leave_left, add="+")
        self.left_canvas.bind("<Enter>", on_enter_left, add="+")
        self.left_canvas.bind("<Leave>", on_leave_left, add="+")
        self.left_canvas.bind("<MouseWheel>", on_mousewheel_left, add="+")
        self.root.bind_all("<MouseWheel>", on_mousewheel_left, add="+")
        btn_frame = ttk.Frame(self.left_scroll_content)
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
        # 单击列表项切换预览（绑定到 inner 上，使用 bind_class 捕获所有子控件）
        # 改为在 _add_checklist_row 中为每个 Checkbutton 单独绑定
        # 存储复选框变量列表: list of (frame, tk.BooleanVar, filepath)
        self.check_vars = []
        panel_border = CollapsiblePanel(self.left_scroll_content, "添加边框", expanded=False)
        panel_border.pack(fill="x", pady=3)
        param_frame = ttk.LabelFrame(panel_border.content, text="水印参数")
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
        ttk.Entry(row4, textvariable=self.focal_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row5, text="光圈：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row5, textvariable=self.f_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row6, text="快门：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row6, textvariable=self.exp_var, width=20, state="readonly").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row7, text="ISO：", width=6).pack(side=tk.LEFT)
        ttk.Entry(row7, textvariable=self.iso_var, width=20, state="readonly").pack(side=tk.LEFT)
        ttk.Label(row8, text="字体：", width=6).pack(side=tk.LEFT)
        self.font_cb = ttk.Combobox(row8, textvariable=self.selected_font,values=self.font_list, width=20, state="readonly")
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
        ttk.Label(hidden_frame, text="⚠ 处理速度较慢，请耐心等待", foreground="red", font=("Arial", 16, "bold")).grid(row=2, column=0, columnspan=2, pady=5)
        # 嵌入/提取模式选择
        self.hidden_mode = tk.StringVar(value="embed")
        mode_frame = ttk.Frame(hidden_frame)
        mode_frame.grid(row=3, column=0, columnspan=2, pady=3)
        ttk.Radiobutton(mode_frame, text="嵌入", variable=self.hidden_mode, value="embed", command=self._toggle_hidden_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="提取", variable=self.hidden_mode, value="extract", command=self._toggle_hidden_mode).pack(side=tk.LEFT, padx=5)
        self.hidden_hint = ttk.Label(hidden_frame, text="💡 启用隐形水印开关后，处理将自动嵌入", foreground="gray")
        self.hidden_hint.grid(row=5, column=0, columnspan=2, pady=(10,0))
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
        ttk.Button(action_frame, text="📦 处理照片", command=self.start_batch).pack(side=tk.RIGHT, padx=2)
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)
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
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                self._add_checklist_row(f)
                added += 1
        if added > 0:
            self.status_var.set(f"已添加 {added} 张照片，共 {len(self.input_files)} 张")
            if self.current_index == -1:
                self.current_index = 0
                self._update_preview_for_current()
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
            for frame, _, _ in self.check_vars:
                frame.destroy()
            self.check_vars.clear()
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
        """Checkbutton 点击：切换勾选状态并切换预览"""
        widget = event.widget
        for i, (frame, var, path) in enumerate(self.check_vars):
            w = widget
            while w and w != self.checklist_inner:
                if w == frame or w.master == frame:
                    var.set(not var.get())
                    if self.current_index >= 0:
                        self._save_current_edits()
                    self.current_index = i
                    self._update_preview_for_current()
                    self._highlight_checklist_row(i)
                    return "break"
                w = w.master

    def _on_checklist_click(self, event):
        """单击行切换预览并高亮，不干涉复选框选中状态"""
        widget = event.widget
        self.root.title(f"clicked: {type(widget).__name__}")
        for i, (frame, var, path) in enumerate(self.check_vars):
            w = widget
            while w and w != self.checklist_inner:
                if w == frame or w.master == frame:
                    self.root.title(f"MATCH i={i}")
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
                self.status_var.set(f"预览失败: {str(e)}")
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
                # 1. 打开原图缩略到预览尺寸
                with Image.open(img_path) as full_img:
                    scale = min((cw-20)/full_img.width, (ch-20)/full_img.height, 1.0)
                    thumb_size = (int(full_img.width*scale), int(full_img.height*scale))
                    thumb = full_img.resize(thumb_size, RESAMPLE).convert("RGBA")
                dlg.set_progress(1)

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
                dlg.set_progress(2)

                # 3. 在缩略图上叠加明文水印
                if self.enable_watermark.get() and self.simple_watermark_panel:
                    wm = self.simple_watermark_panel
                    if wm.watermark_text.get().strip():
                        font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                        color = wm.color_map[wm.font_color_var.get()]
                        overlay = Image.new("RGBA", thumb.size, (0, 0, 0, 0))
                        wm.add_scattered_watermarks(overlay, wm.watermark_text.get(), font, color)
                        thumb = Image.alpha_composite(thumb, overlay)
                dlg.set_progress(3)

                # 4. 保存预览缩略图到缓存（使用参数哈希，避免覆盖后台缓存）
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
            if 'dlg' in dir():
                dlg.close()
            self.status_var.set(f"预览失败: {str(e)}")
    def start_batch(self):
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加照片")
            return
        # 获取所有勾选的图片
        checked_indices = [i for i, (_, var, _) in enumerate(self.check_vars) if var.get()]
        if not checked_indices:
            messagebox.showwarning("提示", "请先勾选要处理的图片")
            return
        checked_files = [self.input_files[i] for i in checked_indices]
        if not messagebox.askyesno("确认处理", f"将处理 {len(checked_files)} 张照片，是否继续？"):
            return
        # 检查是否有任何功能启用
        has_any_func = self.enable_border.get() or self.enable_watermark.get() or self.enable_hidden.get()
        if not has_any_func:
            messagebox.showwarning("提示", "请至少勾选一项功能（添加边框、明文水印、隐形水印）")
            return
        os.makedirs(self.output_path.get(), exist_ok=True)
        font = self.selected_font.get()
        total = len(checked_files)
        dlg = ProgressDialog(self.root, "处理...", maximum=total)
        dlg.set_text(f"正在处理 0/{total}")
        self.root.update()    
        def worker():
            success = 0
            is_extract = self.hidden_mode.get() == "extract" and self.enable_hidden.get()
            for i, f in enumerate(checked_files):
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
                        if self.enable_watermark.get() and self.simple_watermark_panel:
                            wm = self.simple_watermark_panel
                            if wm.watermark_text.get().strip():
                                img = Image.open(out).convert("RGBA")
                                wm_font = wm.get_font(wm.font_family.get(), wm.font_size.get())
                                color = wm.color_map[wm.font_color_var.get()]
                                wm.add_scattered_watermarks(img, wm.watermark_text.get(), wm_font, color)
                                img.convert("RGB").save(out, quality=95)
                                # 恢复 EXIF
                                try:
                                    exif_dict = piexif.load(f)
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
                self.root.after(0, lambda v=i+1: dlg.set_progress(v))
                self.root.after(0, lambda v=f"{i+1}/{total}": dlg.set_text(f"正在处理 {v}"))
                self.status_var.set(f"处理中... {i+1}/{total}")
            self.root.after(0, dlg.close)
            self.status_var.set(f"完成！成功 {success}/{total}")
            if not is_extract:
                self.root.after(0, lambda: messagebox.showinfo("处理完成", f"成功处理 {success}/{total} 张照片\n保存位置: {self.output_path.get()}"))
        threading.Thread(target=worker, daemon=True).start()
    
    def _toggle_hidden_mode(self):
        if self.hidden_mode.get() == "embed":
            self.hidden_text_label.grid()
            self.hidden_text_entry.grid()
            self.hidden_pwd_label.grid()
            self.hidden_pwd_entry.grid()
            self.hidden_hint.config(text="💡 启用隐形水印开关后，处理将自动嵌入")
        else:
            self.hidden_text_label.grid_remove()
            self.hidden_text_entry.grid_remove()
            self.hidden_pwd_label.grid_remove()
            self.hidden_pwd_entry.grid_remove()
            self.hidden_hint.config(text="💡 启用隐形水印开关后，处理将自动提取")
            # 提取模式下自动取消边框和明文水印的勾选
            self.enable_border.set(False)
            self.enable_watermark.set(False)

        

    
    

    