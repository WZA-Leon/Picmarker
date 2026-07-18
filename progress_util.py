import tkinter as tk
from tkinter import ttk


class ProgressDialog:
    """模态环形进度条弹窗，不可关闭，始终置顶，完成后自动关闭"""

    def __init__(self, root, title="处理中..."):
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

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=250)
        self.progress.pack()
        self.progress.start(10)

        self._closed = False

    def set_text(self, text):
        self.label.config(text=text)
        self.root.update()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.progress.stop()
        self.dialog.grab_release()
        self.dialog.destroy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
