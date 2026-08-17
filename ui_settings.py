# ui_settings.py
import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox
from PIL import Image, ImageTk
from pathlib import Path
import shutil
from progress_util import ProgressDialog

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

        # 清理缓存区域（独立带边框的 frame）
        cache_frame = ttk.LabelFrame(main_frame, text="缓存管理", padding=10)
        cache_frame.pack(fill=tk.X, pady=(0, 15))
        cache_inner = ttk.Frame(cache_frame)
        cache_inner.pack(fill=tk.X)
        ttk.Button(cache_inner, text="清理缓存", command=self._clear_cache, width=15).pack(side=tk.LEFT, padx=(0, 10))
        self.cache_size_label = ttk.Label(cache_inner, text="")
        self.cache_size_label.pack(side=tk.LEFT)
        self._update_cache_size()

        # 水印管理区域
        edit_watermark_btn_frame = ttk.LabelFrame(main_frame, text="水印管理", padding=10)
        edit_watermark_btn_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Button(edit_watermark_btn_frame, text="设置水印参数", command=None, width=15).pack(side=tk.LEFT, padx=10)

        # 介绍内容（恢复滚动区域）
        intro_frame = ttk.LabelFrame(main_frame, text="软件介绍", padding=10)
        intro_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        canvas = tk.Canvas(intro_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(intro_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 滚轮事件绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "pages")
            return "break"
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)

        # 加载Logo（放在所有介绍文字最上面）
        logo_path = Path(__file__).parent / "icons" / "icon.png"
        # ==========修复缩进：if 顶格和logo_path同一层级==========
        if logo_path.exists():
            img = Image.open(logo_path)
            cw = canvas.winfo_width()
            if cw <= 10:
                cw = 700
            scale = cw / img.width
            new_w = max(int(img.width * scale), 1)
            new_h = max(int(img.height * scale), 1)
            img = img.resize((new_w, new_h), RESAMPLE)
            self.logo_img = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(scroll_frame, image=self.logo_img)
            logo_label.pack(fill=tk.X, pady=(0, 15))
        else:
            ttk.Label(scroll_frame, text="[Logo 图片缺失：icons/icon.png]", font=("Microsoft YaHei", 24)).pack(pady=(0, 15))

        intro_lines = [
            ("title", "Picmarker V1.3 - 专业图片水印工具"),
            ("subtitle", "作者：WZA-Leon"),
            ("subtitle", "面向摄影爱好者、自媒体创作者的版权保护工具"),
            ("text", "Picmarker基于Python+Tkinter开发，跨平台轻量图片水印软件，集成边框水印、明文水印、DWT隐形水印三大核心能力，支持批量图片处理，一站式完成图片版权标识添加。"),
            ("subtitle", "一、核心三大水印功能："),
            ("bullet", "边框水印(EXIF水印)：自动读取相机品牌、型号、镜头、光圈快门ISO、拍摄时间等EXIF参数，底部生成信息条；支持品牌图标展示、自定义字体、手动修改EXIF、器材三级联动选择"),
            ("bullet", "明文可见水印：自定义水印文字，可调字体、10-100px字号、黑白红蓝绿五色、加粗；支持45°倾斜全图平铺散布水印"),
            ("bullet", "DWT小波隐形盲水印：频域嵌入肉眼不可见版权信息，支持自定义加密文本+密码保护；具备强抗裁剪、抗压缩特性，支持任意尺寸大图，可执行水印嵌入/提取双操作"),
            ("subtitle", "二、批量处理配套能力："),
            ("bullet", "多选图片导入，复选框筛选待处理素材，内置实时预览窗口"),
            ("bullet", "处理进度条可视化展示，输出自动保留原图原始EXIF信息，支持数百张图片批量加工"),
            ("subtitle", "三、适用使用场景："),
            ("bullet", "摄影作品发布：EXIF边框展示拍摄参数，提升作品专业质感"),
            ("bullet", "自媒体图文防盗图：平铺明文水印覆盖全图，遏制恶意盗图"),
            ("bullet", "商用图片版权溯源：嵌入隐形水印，侵权后提取信息用于维权取证"),
            ("bullet", "摄影器材测评：批量生成带完整镜头相机参数的展示图"),
            ("subtitle", "四、运行环境与兼容性："),
            ("bullet", "系统：Windows / macOS / Linux 全平台兼容，统一操作界面无功能阉割"),
            ("bullet", "运行依赖：Python3.8+，Pillow、piexif、exifread、pywt、numpy"),
            ("bullet", "硬件门槛低，推荐4GB及以上内存即可流畅批量处理"),
            ("subtitle", "五、底层技术架构："),
            ("bullet", "图形界面：Tkinter + ttk主题组件"),
            ("bullet", "图像处理：Pillow(PIL)库完成图片渲染与绘制"),
            ("bullet", "EXIF读写：exifread读取元数据，piexif写入保存参数"),
            ("bullet", "隐形水印算法：PyWavelets离散小波变换 + NumPy矩阵运算"),
            ("bullet", "本地配置：JSON格式settings.json持久化保存用户参数"),
            ("subtitle", "六、版本迭代规划："),
            ("text", "短期(V1.4-V1.5)更新方向："),
            ("bullet", "新增图片标注、箭头/矩形框批注、基础调色(亮度/对比度/饱和度/色温)"),
            ("bullet", "扩充EXIF边框样式模板，优化DWT隐形水印鲁棒性，适配blind_watermark增强抗旋转/缩放/遮挡"),
            ("bullet", "新增右键快捷启动、多语言切换、窗口自定义外观"),
            ("text", "中期(V1.6-V2.0)更新方向："),
            ("bullet", "自由自定义水印位置、透明度、平铺角度，支持保存水印预设一键复用"),
            ("bullet", "深度GUI自定义，批量图片格式互转(JPG/PNG/TIFF/WebP)"),
            ("text", "长期(V2.0+)远景规划："),
            ("bullet", "开放插件系统，支持第三方拓展水印算法"),
            ("bullet", "无GUI命令行模式，适配自动化脚本批量处理"),
            ("bullet", "支持CR3、NEF等相机RAW原始照片解析处理"),
            ("subtitle", "七、基础操作流程："),
            ("bullet", "点击「添加」按钮批量导入本地图片素材"),
            ("bullet", "勾选边框/明文/隐形水印功能，自定义各项水印参数"),
            ("bullet", "实时预览水印效果，筛选需要处理的图片"),
            ("bullet", "点击「处理照片」，批量导出带版权水印的成品图片")
        ]

        for kind, text in intro_lines:
            if kind == "title":
                lbl = ttk.Label(scroll_frame, text=text, font=tkfont.Font(family="Microsoft YaHei", size=35, weight="bold"))
                lbl.pack(anchor="w", pady=(12, 4))
            elif kind == "subtitle":
                lbl = ttk.Label(scroll_frame, text=text, font=tkfont.Font(family="Microsoft YaHei", size=20, weight="bold"))
                lbl.pack(anchor="w", pady=(8, 3))
            elif kind == "bullet":
                lbl = ttk.Label(scroll_frame, text="  • " + text, justify="left")
                lbl.pack(anchor="w", padx=(20, 0))
            else:
                lbl = ttk.Label(scroll_frame, text=text, justify="left")
                lbl.pack(anchor="w")

        # 链接1（顺带修复多余www，原www.github.com不标准）
        link_label1 = ttk.Label(
            scroll_frame,
            text="点击访问软件开源github仓库: https://github.com/WZA-Leon/Picmarker",
            foreground="cornflowerblue",
            cursor="hand2",
            font=("Microsoft YaHei", 17, "bold italic underline"),
        )
        link_label1.pack(anchor="w", pady=(5, 10))
        link_label1.bind("<Button-1>", lambda e: self._open_link1())

        # 链接2
        link_label2 = ttk.Label(
            scroll_frame,
            text="点击访问作者github主页: https://github.com/WZA-Leon",
            foreground="cornflowerblue",
            cursor="hand2",
            font=("Microsoft YaHei", 17, "bold italic underline"),
        )
        link_label2.pack(anchor="w", pady=(5, 10))
        link_label2.bind("<Button-1>", lambda e: self._open_link2())

    def _open_link1(self):
        import webbrowser
        webbrowser.open("https://github.com/WZA-Leon/Picmarker")

    def _open_link2(self):
        import webbrowser
        webbrowser.open("https://github.com/WZA-Leon")

    def _get_cache_size(self):
        """返回 temp 文件夹中所有内容的总大小（字节）"""
        temp_dir = Path(__file__).parent / "temp"
        total = 0
        if temp_dir.exists():
            for f in temp_dir.rglob("*"):
                try:
                    if f.is_file():
                        total += f.stat().st_size
                except:
                    pass
        return total

    def _format_size(self, size):
        """将字节数格式化为可读字符串"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _update_cache_size(self):
        """更新缓存大小显示"""
        size = self._get_cache_size()
        self.cache_size_label.config(text=f"当前缓存大小：{self._format_size(size)}")

    def _clear_cache(self):
        """清除 temp 文件夹中的缓存文件"""
        temp_dir = Path(__file__).parent / "temp"
        if not temp_dir.exists():
            messagebox.showinfo("清理缓存", "缓存文件夹不存在")
            return
        freed = self._get_cache_size()
        files = [f for f in temp_dir.rglob("*") if f.is_file()]
        total = len(files)
        if total == 0:
            self._update_cache_size()
            messagebox.showinfo("清理缓存", "缓存文件夹为空")
            return
        dlg = ProgressDialog(self.win, "清理缓存...", maximum=total)
        dlg.set_text(f"正在清理 0/{total}")
        count = 0
        for i, f in enumerate(files, 1):
            try:
                f.unlink()
                count += 1
            except Exception as e:
                print(f"删除失败 {f.name}: {e}")
            dlg.set_progress(i)
            dlg.set_text(f"正在清理 {i}/{total}")
        dlg.close()
        self._update_cache_size()
        messagebox.showinfo("清理缓存", f"已清除 {count} 个缓存文件\n释放空间：{self._format_size(freed)}")