import tkinter as tk
from tkinter import ttk,messagebox,font as tkfont
from PIL import Image, ImageDraw, ImageFont
import os
import platform

class WatermarkApp:
    def __init__(self, parent_frame, main_app):
        self.parent = parent_frame
        self.main_app = main_app
        self.watermark_text = tk.StringVar(value="水印内容")
        self.font_size = tk.IntVar(value=20)
        self.font_color_var = tk.StringVar(value="黑色")
        self.color_map = {
            "黑色": "#000000", "白色": "#FFFFFF", "红色": "#ED4719",
            "蓝色": "#498AEB", "绿色": "#009300"
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
        size_spin.bind("<MouseWheel>", lambda e: "break", add="+")
        size_spin.bind("<Button-4>", lambda e: "break", add="+")
        size_spin.bind("<Button-5>", lambda e: "break", add="+")

        ttk.Label(settings_frame, text="字体颜色:").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        color_options = list(self.color_map.keys())
        color_combo = ttk.Combobox(settings_frame, textvariable=self.font_color_var, values=color_options, state="readonly")
        color_combo.grid(row=2, column=1, padx=(5,0), pady=(5,0), sticky=tk.W)
        color_combo.bind("<<ComboboxSelected>>", lambda e: self.main_app.show_preview())
        color_combo.bind("<MouseWheel>", lambda e: "break", add="+")
        color_combo.bind("<Button-4>", lambda e: "break", add="+")
        color_combo.bind("<Button-5>", lambda e: "break", add="+")

        bold_check = ttk.Checkbutton(settings_frame, text="加粗", variable=self.is_bold, command=self.main_app.show_preview)
        bold_check.grid(row=3, column=0, pady=(5,0), sticky=tk.W)

        ttk.Label(settings_frame, text="字体:").grid(row=4, column=0, sticky=tk.W, pady=(5,0))
        font_combo = ttk.Combobox(settings_frame, textvariable=self.font_family, values=self.fonts, state="readonly")
        font_combo.grid(row=4, column=1, padx=(5,0), pady=(5,0), sticky=(tk.W, tk.E))
        font_combo.bind("<<ComboboxSelected>>", lambda e: self.main_app.show_preview())
        font_combo.bind("<MouseWheel>", lambda e: "break", add="+")
        font_combo.bind("<Button-4>", lambda e: "break", add="+")
        font_combo.bind("<Button-5>", lambda e: "break", add="+")

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