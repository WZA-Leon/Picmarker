import tkinter as tk
from tkinter import ttk


class ProgressDialog:
    """模态进度条弹窗，不可关闭，始终置顶，完成后自动关闭"""

    def __init__(self, root, title="处理中...", maximum=100):
        self.root = root
        self.dialog = tk.Toplevel(root)
        self.dialog.title(title)
        self.dialog.geometry("300x120")
        self.dialog.resizable(False, False)
        self.dialog.transient(root)
        self.dialog.grab_set()
        self.dialog.attributes("-topmost", True)
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        self.dialog.update_idletasks()
        x = root.winfo_x() + (root.winfo_width() - 300) // 2
        y = root.winfo_y() + (root.winfo_height() - 120) // 2
        self.dialog.geometry(f"+{x}+{y}")

        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(frame, text="请稍候...", anchor=tk.CENTER)
        self.label.pack(pady=(0, 10))

        self.progress = ttk.Progressbar(frame, mode="determinate", length=250, maximum=maximum)
        self.progress.pack()

        self._closed = False
        self.dialog.update()

    def set_text(self, text):
        if self._closed:
            return
        self.label.config(text=text)
        self.dialog.update_idletasks()

    def set_progress(self, value):
        if self._closed:
            return
        self.progress["value"] = value
        self.dialog.update_idletasks()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.dialog.grab_release()
        self.dialog.destroy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
