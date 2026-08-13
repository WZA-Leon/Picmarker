import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片水印添加工具")
        self.root.geometry("900x600")
        self.root.resizable(True, True)

        # 统一字体和颜色定义
        self.default_font = ("微软雅黑", 10, "bold")
        self.default_fg = "black"
        self.button_bg = "#f0f0f0"

        # 初始化变量
        self.image_paths = []
        self.thumbnails = []  # 保存缩略图PhotoImage
        self.output_path = ""
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
        self.fonts = sorted(tkfont.families())  # 获取所有系统字体
        self.font_family = tk.StringVar(value="Arial" if "Arial" in self.fonts else self.fonts[0])

        # 预览图片
        self.preview_image = None
        self.preview_photo = None
        self._preview_after_id = None

        # 设置样式
        style = ttk.Style()
        style.configure("TButton", font=self.default_font, relief="flat", background=self.button_bg)
        style.configure("TLabel", font=self.default_font, foreground=self.default_fg)
        style.configure("TEntry", font=self.default_font)
        style.configure("TCombobox", font=self.default_font)
        style.configure("Card.TLabelframe", borderwidth=2, relief="solid")
        style.configure("Card.TLabelframe.Label", font=self.default_font, foreground=self.default_fg)

        # 绑定变量变化更新预览
        self.watermark_text.trace_add("write", self.update_watermark_preview)
        self.font_size.trace_add("write", self.update_watermark_preview)
        self.font_color_var.trace_add("write", self.update_watermark_preview)
        self.is_bold.trace_add("write", self.update_watermark_preview)
        self.font_family.trace_add("write", self.update_watermark_preview)

        # 创建界面元素
        self.create_widgets()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 左侧框架
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        left_frame.columnconfigure(0, weight=1)

        # 水印设置框架
        settings_frame = ttk.LabelFrame(left_frame, text="水印设置", padding="5", style="Card.TLabelframe")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)

        # 水印内容
        ttk.Label(settings_frame, text="水印内容:").grid(row=0, column=0, sticky=tk.W)
        text_entry = ttk.Entry(settings_frame, textvariable=self.watermark_text, width=25)
        text_entry.grid(row=0, column=1, padx=(5,0))
        text_entry.bind('<KeyRelease>', self.schedule_preview_update)
        text_entry.bind('<FocusOut>', self.schedule_preview_update)

        # 字体大小
        ttk.Label(settings_frame, text="字体大小:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        size_spin = ttk.Spinbox(settings_frame, from_=10, to=100, textvariable=self.font_size, width=8)
        size_spin.grid(row=1, column=1, padx=(5,0), pady=(5,0), sticky=tk.W)
        size_spin.bind('<ButtonRelease-1>', self.schedule_preview_update)
        size_spin.bind('<KeyRelease>', self.schedule_preview_update)

        # 字体颜色
        ttk.Label(settings_frame, text="字体颜色:").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        color_options = list(self.color_map.keys())
        color_combo = ttk.Combobox(settings_frame, textvariable=self.font_color_var, values=color_options, state="readonly")
        color_combo.grid(row=2, column=1, padx=(5,0), pady=(5,0), sticky=tk.W)
        color_combo.bind("<<ComboboxSelected>>", self.schedule_preview_update)

        # 加粗选项
        bold_check = ttk.Checkbutton(settings_frame, text="加粗", variable=self.is_bold, command=self.update_watermark_preview)
        bold_check.grid(row=3, column=0, pady=(5,0), sticky=tk.W)

        # 字体选择
        ttk.Label(settings_frame, text="字体:").grid(row=4, column=0, sticky=tk.W, pady=(5,0))
        font_combo = ttk.Combobox(settings_frame, textvariable=self.font_family, values=self.fonts, state="readonly")
        font_combo.grid(row=4, column=1, padx=(5,0), pady=(5,0), sticky=(tk.W, tk.E))
        font_combo.bind("<<ComboboxSelected>>", self.schedule_preview_update)

        # 图片选择框架
        image_frame = ttk.LabelFrame(left_frame, text="图片选择", padding="5", style="Card.TLabelframe")
        image_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        left_frame.rowconfigure(1, weight=1)

        # 按钮框架
        button_frame = ttk.Frame(image_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0,5))

        # 选择图片按钮
        ttk.Button(button_frame, text="选择图片", command=self.select_images).grid(row=0, column=0, padx=(0,10))

        # 清除所有按钮
        ttk.Button(button_frame, text="清除所有", command=self.clear_all_images).grid(row=0, column=1)

        # 图片预览框架
        self.preview_frame = ttk.Frame(image_frame)
        self.preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        image_frame.rowconfigure(1, weight=1)

        # 滚动条
        self.canvas = tk.Canvas(self.preview_frame, height=200)  # 减小高度
        scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 输出设置框架
        output_frame = ttk.LabelFrame(left_frame, text="输出设置", padding="5", style="Card.TLabelframe")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)

        # 选择输出路径
        ttk.Button(output_frame, text="选择输出路径", command=self.select_output_path).grid(row=0, column=0)
        self.output_label = ttk.Label(output_frame, text="未选择输出路径")
        self.output_label.grid(row=1, column=0, pady=(5,0))

        # 添加水印按钮
        ttk.Button(left_frame, text="添加水印", command=self.add_watermark).grid(row=3, column=0, pady=10)

        # 版权信息
        copyright_label = ttk.Label(left_frame, text="© WZA 保留所有权利", font=self.default_font, foreground=self.default_fg)
        copyright_label.grid(row=4, column=0, pady=(0,5))

        # 右侧水印预览框架
        preview_frame = ttk.LabelFrame(main_frame, text="水印预览（单个水印）", padding="5", style="Card.TLabelframe")
        preview_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=(10,0))
        main_frame.columnconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0)

        # 刷新预览按钮
        ttk.Button(preview_frame, text="刷新预览", command=self.update_watermark_preview).grid(row=1, column=0, pady=(5,0))

        # 提示标签
        ttk.Label(preview_frame, text="如预览未自动更新，请点击上方刷新", font=("Arial", 8), foreground="gray").grid(row=2, column=0, pady=(5,0))

        # 初始预览
        self.update_watermark_preview()

    def update_watermark_preview(self, *args):
        """更新水印预览"""
        try:
            # 创建预览图片 (200x200)
            preview_img = Image.new('RGB', (200, 200), color=(240, 240, 240))

            # 获取适合预览的字体大小
            text = self.watermark_text.get() or "预览"
            max_size = min(self.font_size.get(), 30)
            temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
            while max_size > 8:
                font = self.get_font(self.font_family.get(), max_size)
                bbox = temp_draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                # 旋转后的大致大小
                rotated_w = int((text_width + text_height) * 0.707)
                rotated_h = rotated_w
                if rotated_w <= 180 and rotated_h <= 180:
                    break
                max_size -= 2
            preview_font_size = max_size

            # 水印颜色
            color = self.color_map[self.font_color_var.get()]

            # 生成旋转文字图片并粘贴到中心
            font = self.get_font(self.font_family.get(), preview_font_size)
            rotated_text = self.create_rotated_text_image(text, font, color)
            x = max(0, (200 - rotated_text.width) // 2)
            y = max(0, (200 - rotated_text.height) // 2)
            preview_img.paste(rotated_text, (x, y), rotated_text)

            # 转换为PhotoImage
            self.preview_photo = ImageTk.PhotoImage(preview_img)
            self.preview_label.config(image=self.preview_photo)

        except Exception as e:
            print(f"预览更新错误: {e}")
            # 显示错误图片
            error_img = Image.new('RGB', (200, 200), color=(255, 200, 200))
            draw = ImageDraw.Draw(error_img)
            draw.text((10, 90), "预览错误", fill="red", font=self.get_font("Arial", 16))
            self.preview_photo = ImageTk.PhotoImage(error_img)
            self.preview_label.config(image=self.preview_photo)

    def schedule_preview_update(self, event=None):
        """防抖刷新预览"""
        if self._preview_after_id:
            self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(200, self.update_watermark_preview)

    def add_scattered_watermarks(self, image, text, font, color):
        """添加分散的45度水印"""
        width, height = image.size
        # 生成旋转文字图像
        rotated_text = self.create_rotated_text_image(text, font, color)
        text_width, text_height = rotated_text.size

        # 间距
        spacing = max(text_width, text_height) * 1.5

        # 计算位置并粘贴
        y = -text_height
        while y < height + text_height:
            x = -text_width
            while x < width + text_width:
                image.paste(rotated_text, (int(x), int(y)), rotated_text)
                x += spacing
            y += spacing

    def select_images(self):
        # 选择图片文件，支持批量选择
        filetypes = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        new_paths = list(filedialog.askopenfilenames(title="选择图片", filetypes=filetypes))
        if new_paths:
            self.image_paths.extend(new_paths)
            self.update_preview()

    def update_preview(self):
        # 清除旧的缩略图
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnails = []

        if not self.image_paths:
            # 显示没有图片的提示
            no_image_label = ttk.Label(self.scrollable_frame, text="没有图片", font=(self.default_font[0], 14), foreground="gray")
            no_image_label.grid(row=0, column=0, padx=20, pady=20)
            return

        # 生成新缩略图
        for i, path in enumerate(self.image_paths):
            try:
                img = Image.open(path)
                img.thumbnail((100, 100))  # 缩放
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)

                # 创建框架包含缩略图和移除按钮
                item_frame = ttk.Frame(self.scrollable_frame)
                item_frame.grid(row=i//4, column=i%4, padx=5, pady=5)

                label = ttk.Label(item_frame, image=photo)
                label.grid(row=0, column=0)

                name_label = ttk.Label(item_frame, text=os.path.basename(path), wraplength=100)
                name_label.grid(row=1, column=0)

                remove_btn = ttk.Button(item_frame, text="移除", command=lambda idx=i: self.remove_image(idx))
                remove_btn.grid(row=2, column=0)

            except Exception as e:
                messagebox.showerror("错误", f"加载图片 {os.path.basename(path)} 缩略图失败: {str(e)}")

    def remove_image(self, index):
        """移除指定索引的图片并刷新缩略图"""
        if 0 <= index < len(self.image_paths):
            del self.image_paths[index]
            self.update_preview()

    def get_font(self, family, size):
        """获取字体，支持中文"""
        # 优先尝试中文字体
        chinese_fonts = [
            "C:\\Windows\\Fonts\\msyh.ttc",    # 微软雅黑
            "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
            "C:\\Windows\\Fonts\\simhei.ttf",  # 黑体
        ]
        for font_path in chinese_fonts:
            try:
                font = ImageFont.truetype(font_path, size)
                return font
            except:
                continue

        # 然后尝试用户选择的字体
        try:
            font = ImageFont.truetype(family, size)
            return font
        except:
            pass

        # 尝试常见字体文件路径
        font_paths = [
            f"C:\\Windows\\Fonts\\{family}.ttf",
            f"C:\\Windows\\Fonts\\{family}.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",   # Arial
        ]
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                return font
            except:
                continue
        # 最后使用默认字体
        return ImageFont.load_default()
    def create_rotated_text_image(self, text, font, color):
        """创建带边距的旋转文字图像"""
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
    def clear_all_images(self):
        # 清除所有选中的图片
        self.image_paths = []
        self.update_preview()

    def select_output_path(self):
        # 选择输出目录
        self.output_path = filedialog.askdirectory(title="选择输出路径")
        if self.output_path:
            self.output_label.config(text=f"输出路径: {self.output_path}")
        else:
            self.output_label.config(text="未选择输出路径")

    def add_watermark(self):
        # 检查输入
        if not self.image_paths:
            messagebox.showerror("错误", "请先选择图片")
            return
        if not self.output_path:
            messagebox.showerror("错误", "请先选择输出路径")
            return
        if not self.watermark_text.get().strip():
            messagebox.showerror("错误", "请输入水印内容")
            return

        font_color = self.color_map[self.font_color_var.get()]

        # 处理每张图片
        success_count = 0
        for image_path in self.image_paths:
            try:
                # 打开图片
                image = Image.open(image_path)
                draw = ImageDraw.Draw(image)

                # 设置字体
                font = self.get_font(self.font_family.get(), self.font_size.get())

                # 计算水印位置（右下角）
                bbox = draw.textbbox((0, 0), self.watermark_text.get(), font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = image.width - text_width - 10
                y = image.height - text_height - 10

                # 添加分散水印
                self.add_scattered_watermarks(image, self.watermark_text.get(), font, font_color)

                # 保存图片
                base_name = os.path.basename(image_path)
                output_file = os.path.join(self.output_path, f"watermarked_{base_name}")
                image.save(output_file)
                success_count += 1

            except Exception as e:
                messagebox.showerror("错误", f"处理图片 {os.path.basename(image_path)} 时出错: {str(e)}")

        if success_count > 0:
            messagebox.showinfo("成功", f"成功为 {success_count} 张图片添加水印")
            # 自动清除图片列表
            self.clear_all_images()

if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap("icon.ico")  
    root.resizable(False, False)
    app = WatermarkApp(root)
    root.mainloop()