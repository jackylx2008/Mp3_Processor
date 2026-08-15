"""GUI 中复用的表单控件。"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Literal


class PathField(ttk.Frame):
    """带浏览按钮的路径输入框。"""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        variable: tk.StringVar,
        project_root: Path,
        mode: Literal["directory", "file"] = "directory",
        filetypes: tuple[tuple[str, str], ...] = (("所有文件", "*"),),
    ) -> None:
        super().__init__(parent)
        self.variable = variable
        self.project_root = project_root
        self.mode = mode
        self.filetypes = filetypes
        self.columnconfigure(0, weight=1)
        ttk.Entry(self, textvariable=variable).grid(row=0, column=0, sticky="ew")
        ttk.Button(self, text="选择…", command=self._browse, width=10).grid(row=0, column=1, padx=(8, 0))

    def _browse(self) -> None:
        current = Path(self.variable.get()).expanduser() if self.variable.get().strip() else self.project_root
        if not current.is_absolute():
            current = self.project_root / current
        initial = current if current.is_dir() else current.parent
        if self.mode == "directory":
            selected = filedialog.askdirectory(parent=self, initialdir=initial)
        else:
            selected = filedialog.askopenfilename(parent=self, initialdir=initial, filetypes=self.filetypes)
        if selected:
            self.variable.set(selected)
