# ui_settings.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path

try:
    RESAMPLE = Image.Resampling.LANCZOS
except:
    RESAMPLE = Image.LANCZOS


class SettingsWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("关于 Picmarker")
        self.win.state("zoomed")
        self.win.transient(parent)
        self.win.grab_set()
        main_frame = ttk.Frame(self.win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 功能按钮区域（只保留清理缓存和设置水印参数）
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(0, 15))

        ttk.Button(btn_frame, text="清理缓存", command=None, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="设置水印参数", command=None, width=15).pack(side=tk.LEFT, padx=10)
        # 分隔线
        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=(0, 10))

        # 介绍内容（可滚动）
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 滚轮事件绑定到 canvas 和 scroll_frame
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "pages")
            return "break"
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)

        # 将 Logo 图片放入 scroll_frame（按滚动区域宽度缩放）
        logo_path = Path(__file__).parent / "icons" / "test.jpg"
        if logo_path.exists():
            img = Image.open(logo_path)
            self.win.update_idletasks()
            # 用 canvas 宽度作为缩放基准
            cw = canvas.winfo_width() or 600
            if cw <= 0:
                cw = 600
            scale = cw / img.width
            new_w = max(int(img.width * scale), 1)
            new_h = max(int(img.height * scale), 1)
            img = img.resize((new_w, new_h), RESAMPLE)
            self.logo_img = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(scroll_frame, image=self.logo_img)
            logo_label.pack(fill=tk.X, pady=(0, 15))
        else:
            ttk.Label(scroll_frame, text="[Logo]", font=("Arial", 24)).pack(pady=(0, 15))

        # 读取 README.md 内容
        readme_path = Path(__file__).parent / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
        else:
            content = "# Picmarker V1.3\n\nREADME.md 文件未找到。"

        # 将 Markdown 文本按行显示为 Label（带层级样式）
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                lbl = ttk.Label(scroll_frame, text=line, font=("Arial", 16, "bold"))
                lbl.pack(anchor="w", pady=(12, 4))
            elif stripped.startswith("## ") and not stripped.startswith("### "):
                lbl = ttk.Label(scroll_frame, text=line, font=("Arial", 14, "bold"))
                lbl.pack(anchor="w", pady=(8, 3))
            elif stripped.startswith("### "):
                lbl = ttk.Label(scroll_frame, text=line, font=("Arial", 12, "bold"))
                lbl.pack(anchor="w", pady=(5, 2))
            elif stripped.startswith("- "):
                lbl = ttk.Label(scroll_frame, text="  • " + line.strip()[2:], wraplength=600, justify="left")
                lbl.pack(anchor="w", padx=(20, 0))
            elif stripped.startswith("|"):
                lbl = ttk.Label(scroll_frame, text=line, font=("Consolas", 9), wraplength=600)
                lbl.pack(anchor="w", padx=(10, 0))
            elif stripped == "":
                ttk.Label(scroll_frame, text="").pack()
            else:
                lbl = ttk.Label(scroll_frame, text=line, wraplength=600, justify="left")
                lbl.pack(anchor="w")

        # 链接放入 scroll_frame（图片下方）
        link_label = ttk.Label(
            scroll_frame,
            text="GitHub: https://www.github.com/WZA-Leon/Picmarker",
            foreground="blue",
            cursor="hand2",
            font=("Arial", 10)
        )
        link_label.pack(anchor="w", pady=(5, 10))
        link_label.bind("<Button-1>", lambda e: self._open_link())

    def _open_link(self):
        import webbrowser
        webbrowser.open("https://www.github.com/WZA-Leon/Picmarker")

