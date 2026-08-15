"""五个音频工作流页签。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from mp3_processor.context import AppContext
from mp3_processor.execution import CancellationToken, ProgressCallback
from mp3_processor.flows import (
    apply_cover_flow,
    convert_audio_flow,
    prepare_cover_flow,
    split_audio_flow,
    update_metadata_flow,
)
from mp3_processor.gui.task_runner import Task
from mp3_processor.gui.widgets import PathField
from mp3_processor.results import FlowResult


StartCallback = Callable[[str, Task], bool]
PreviewCallback = Callable[[str, dict[str, object]], None]
ContextProvider = Callable[[], AppContext]


class WorkflowTab(ttk.Frame):
    """工作流表单的公共布局与动作。"""

    title = "工作流"

    def __init__(
        self,
        parent: tk.Misc,
        *,
        project_root: Path,
        context_provider: ContextProvider,
        start_callback: StartCallback,
        cancel_callback: Callable[[], None],
        preview_callback: PreviewCallback,
    ) -> None:
        super().__init__(parent, padding=18)
        self.project_root = project_root
        self.context_provider = context_provider
        self.start_callback = start_callback
        self.cancel_callback = cancel_callback
        self.preview_callback = preview_callback
        self.form = ttk.Frame(self)
        self.form.grid(row=0, column=0, sticky="nsew")
        self.form.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def add_path(
        self,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        mode: str = "directory",
        filetypes: tuple[tuple[str, str], ...] = (("所有文件", "*"),),
    ) -> None:
        ttk.Label(self.form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=7)
        PathField(
            self.form,
            variable=variable,
            project_root=self.project_root,
            mode=mode,  # type: ignore[arg-type]
            filetypes=filetypes,
        ).grid(row=row, column=1, columnspan=5, sticky="ew", pady=7)

    def add_entry(
        self,
        row: int,
        label: str,
        variable: tk.Variable,
        *,
        width: int = 18,
        values: tuple[str, ...] | None = None,
    ) -> None:
        ttk.Label(self.form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=7)
        if values:
            widget = ttk.Combobox(self.form, textvariable=variable, values=values, width=width, state="readonly")
        else:
            widget = ttk.Entry(self.form, textvariable=variable, width=width)
        widget.grid(row=row, column=1, sticky="w", pady=7)

    def add_actions(self, row: int) -> None:
        actions = ttk.Frame(self.form)
        actions.grid(row=row, column=0, columnspan=6, sticky="e", pady=(22, 0))
        ttk.Button(actions, text="参数预览", command=self._preview, width=16).pack(side="left", padx=6)
        self.run_button = ttk.Button(actions, text="▶ 开始执行", command=self._start, style="Accent.TButton", width=18)
        self.run_button.pack(side="left", padx=6)
        self.cancel_button = ttk.Button(actions, text="取消任务", command=self.cancel_callback, width=14, state="disabled")
        self.cancel_button.pack(side="left", padx=6)

    def set_running(self, running: bool) -> None:
        self.run_button.configure(state="disabled" if running else "normal")
        self.cancel_button.configure(state="normal" if running else "disabled")

    def collect_parameters(self) -> dict[str, object]:
        raise NotImplementedError

    def execute(
        self,
        context: AppContext,
        parameters: dict[str, object],
        token: CancellationToken,
        progress: ProgressCallback,
    ) -> FlowResult:
        raise NotImplementedError

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        raise NotImplementedError

    def _start(self) -> None:
        try:
            parameters = self.collect_parameters()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc), parent=self)
            return
        if parameters.get("write") and not messagebox.askyesno(
            "确认写入",
            "此操作会直接修改音频文件。已备份原文件并确认继续吗？",
            parent=self,
        ):
            return
        context = self.context_provider()
        self.start_callback(
            self.title,
            lambda token, progress: self.execute(context, parameters, token, progress),
        )

    def _preview(self) -> None:
        try:
            self.preview_callback(self.title, self.collect_parameters())
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc), parent=self)

    @staticmethod
    def required(value: str, label: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{label}不能为空")
        return value

    @staticmethod
    def nonnegative_int(value: str, label: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{label}必须是整数") from exc
        if parsed < 0:
            raise ValueError(f"{label}不能小于 0")
        return parsed


class ConvertTab(WorkflowTab):
    title = "音频转换"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.input_path = tk.StringVar(self)
        self.output_dir = tk.StringVar(self)
        self.bitrate = tk.StringVar(self, "192k")
        self.max_files = tk.StringVar(self, "0")
        self.max_depth = tk.StringVar(self, "0")
        self.recursive = tk.BooleanVar(self, True)
        self.overwrite = tk.BooleanVar(self, False)
        self.validate_output = tk.BooleanVar(self, True)
        self.extensions = {name: tk.BooleanVar(self, name in {"m4a", "mp4", "wma"}) for name in ("m4a", "mp4", "wma", "wav", "flac")}

        paths = ttk.LabelFrame(self.form, text="路径配置", padding=14)
        paths.grid(row=0, column=0, columnspan=6, sticky="ew", pady=(0, 14))
        paths.columnconfigure(1, weight=1)
        self.form = paths
        self.add_path(0, "输入目录 (Input Dir)", self.input_path)
        self.add_path(1, "输出目录 (Output Dir)", self.output_dir)

        options = ttk.LabelFrame(self, text="转换参数", padding=14)
        options.grid(row=1, column=0, sticky="ew")
        options.columnconfigure(1, weight=1)
        self.form = options
        ttk.Label(options, text="支持的源格式").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=7)
        extension_box = ttk.Frame(options)
        extension_box.grid(row=0, column=1, columnspan=5, sticky="w")
        for name, variable in self.extensions.items():
            ttk.Checkbutton(extension_box, text=name, variable=variable).pack(side="left", padx=(0, 18))
        self.add_entry(1, "目标比特率", self.bitrate, values=("128k", "192k", "256k", "320k"))
        ttk.Label(options, text="最大文件数 (0=无限制)").grid(row=1, column=2, sticky="e", padx=(24, 12))
        ttk.Entry(options, textvariable=self.max_files, width=10).grid(row=1, column=3, sticky="w")
        ttk.Label(options, text="最大递归深度 (0=无限制)").grid(row=1, column=4, sticky="e", padx=(24, 12))
        ttk.Entry(options, textvariable=self.max_depth, width=10).grid(row=1, column=5, sticky="w")
        controls = ttk.Frame(options)
        controls.grid(row=2, column=0, columnspan=6, sticky="w", pady=10)
        ttk.Checkbutton(controls, text="递归扫描子目录", variable=self.recursive).pack(side="left", padx=(0, 24))
        ttk.Checkbutton(controls, text="覆盖已有文件", variable=self.overwrite).pack(side="left", padx=(0, 24))
        ttk.Checkbutton(controls, text="校验输出有效性", variable=self.validate_output).pack(side="left")
        self.add_actions(3)

    def collect_parameters(self) -> dict[str, object]:
        extensions = [name for name, variable in self.extensions.items() if variable.get()]
        if not extensions:
            raise ValueError("至少选择一种源格式")
        return {
            "input_path": self.required(self.input_path.get(), "输入目录"),
            "output_dir": self.required(self.output_dir.get(), "输出目录"),
            "input_extensions": extensions,
            "recursive": self.recursive.get(),
            "max_depth": self.nonnegative_int(self.max_depth.get(), "最大递归深度"),
            "bitrate": self.required(self.bitrate.get(), "目标比特率"),
            "overwrite": self.overwrite.get(),
            "validate_output": self.validate_output.get(),
            "max_files": self.nonnegative_int(self.max_files.get(), "最大文件数"),
        }

    def execute(self, context: AppContext, parameters: dict[str, object], token: CancellationToken, progress: ProgressCallback) -> FlowResult:
        return convert_audio_flow.run(context, **parameters, progress=progress, cancel_token=token)  # type: ignore[arg-type]

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        self.input_path.set(config.get("input_path", ""))
        self.output_dir.set(config.get("output_dir", ""))
        self.bitrate.set(config.get("bitrate", "192k"))
        self.max_files.set(str(config.get("max_files", 0)))
        self.max_depth.set(str(config.get("max_depth", 0)))
        self.recursive.set(bool(config.get("recursive", True)))
        self.overwrite.set(bool(config.get("overwrite", False)))
        self.validate_output.set(bool(config.get("validate_output", True)))
        selected = set(config.get("input_extensions", []))
        for name, variable in self.extensions.items():
            variable.set(name in selected)


class MetadataTab(WorkflowTab):
    title = "元数据更新"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.input_path = tk.StringVar(self)
        self.artist = tk.StringVar(self)
        self.album = tk.StringVar(self)
        self.max_files = tk.StringVar(self, "0")
        self.recursive = tk.BooleanVar(self, True)
        self.include_folder = tk.BooleanVar(self, True)
        self.write = tk.BooleanVar(self, False)
        self.add_path(0, "输入目录", self.input_path)
        self.add_entry(1, "艺术家 (Artist)", self.artist)
        self.add_entry(2, "专辑 (Album)", self.album)
        self.add_entry(3, "最大文件数 (0=无限制)", self.max_files)
        ttk.Checkbutton(self.form, text="递归扫描子目录", variable=self.recursive).grid(row=4, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="将文件夹名加入专辑", variable=self.include_folder).grid(row=5, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="实际写入（未选中时仅预览）", variable=self.write).grid(row=6, column=0, columnspan=2, sticky="w", pady=7)
        self.add_actions(7)

    def collect_parameters(self) -> dict[str, object]:
        return {
            "input_path": self.required(self.input_path.get(), "输入目录"),
            "artist": self.artist.get().strip(),
            "album": self.album.get().strip(),
            "recursive": self.recursive.get(),
            "include_folder_in_album": self.include_folder.get(),
            "write": self.write.get(),
            "max_files": self.nonnegative_int(self.max_files.get(), "最大文件数"),
        }

    def execute(self, context: AppContext, parameters: dict[str, object], token: CancellationToken, progress: ProgressCallback) -> FlowResult:
        return update_metadata_flow.run(context, **parameters, progress=progress, cancel_token=token)  # type: ignore[arg-type]

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        self.input_path.set(config.get("input_path", ""))
        self.artist.set(config.get("artist", ""))
        self.album.set(config.get("album", ""))
        self.max_files.set(str(config.get("max_files", 0)))
        self.recursive.set(bool(config.get("recursive", True)))
        self.include_folder.set(bool(config.get("include_folder_in_album", True)))
        self.write.set(bool(config.get("write", False)))


class PrepareCoverTab(WorkflowTab):
    title = "封面裁剪"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.input_path = tk.StringVar(self)
        self.output_dir = tk.StringVar(self)
        self.crop_values = [tk.StringVar(self, "0") for _ in range(4)]
        self.max_files = tk.StringVar(self, "0")
        self.recursive = tk.BooleanVar(self, True)
        self.overwrite = tk.BooleanVar(self, False)
        self.add_path(0, "图片输入目录", self.input_path)
        self.add_path(1, "图片输出目录", self.output_dir)
        ttk.Label(self.form, text="裁剪区域 (左/上/右/下)").grid(row=2, column=0, sticky="w", pady=7)
        crop_box = ttk.Frame(self.form)
        crop_box.grid(row=2, column=1, sticky="w")
        for label, variable in zip(("左", "上", "右", "下"), self.crop_values, strict=True):
            ttk.Label(crop_box, text=label).pack(side="left", padx=(0, 4))
            ttk.Entry(crop_box, textvariable=variable, width=8).pack(side="left", padx=(0, 12))
        self.add_entry(3, "最大文件数 (0=无限制)", self.max_files)
        ttk.Checkbutton(self.form, text="递归扫描子目录", variable=self.recursive).grid(row=4, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="覆盖已有图片", variable=self.overwrite).grid(row=5, column=0, columnspan=2, sticky="w", pady=7)
        self.add_actions(6)

    def collect_parameters(self) -> dict[str, object]:
        values = tuple(self.nonnegative_int(value.get(), "裁剪坐标") for value in self.crop_values)
        if values[2] <= values[0] or values[3] <= values[1]:
            raise ValueError("裁剪区域的右、下坐标必须分别大于左、上坐标")
        return {
            "input_path": self.required(self.input_path.get(), "图片输入目录"),
            "output_dir": self.required(self.output_dir.get(), "图片输出目录"),
            "crop_box": values,
            "recursive": self.recursive.get(),
            "overwrite": self.overwrite.get(),
            "max_files": self.nonnegative_int(self.max_files.get(), "最大文件数"),
        }

    def execute(self, context: AppContext, parameters: dict[str, object], token: CancellationToken, progress: ProgressCallback) -> FlowResult:
        return prepare_cover_flow.run(context, **parameters, progress=progress, cancel_token=token)  # type: ignore[arg-type]

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        self.input_path.set(config.get("input_path", ""))
        self.output_dir.set(config.get("output_dir", ""))
        values = config.get("crop_box", [0, 0, 1000, 1000])
        for variable, value in zip(self.crop_values, values, strict=False):
            variable.set(str(value))
        self.max_files.set(str(config.get("max_files", 0)))
        self.recursive.set(bool(config.get("recursive", True)))
        self.overwrite.set(bool(config.get("overwrite", False)))


class ApplyCoverTab(WorkflowTab):
    title = "封面嵌入"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.input_path = tk.StringVar(self)
        self.cover_image = tk.StringVar(self)
        self.max_files = tk.StringVar(self, "0")
        self.recursive = tk.BooleanVar(self, True)
        self.replace_existing = tk.BooleanVar(self, True)
        self.write = tk.BooleanVar(self, False)
        self.add_path(0, "音频输入目录", self.input_path)
        self.add_path(
            1,
            "封面图片",
            self.cover_image,
            mode="file",
            filetypes=(("封面图片", "*.png *.jpg *.jpeg"), ("所有文件", "*")),
        )
        self.add_entry(2, "最大文件数 (0=无限制)", self.max_files)
        ttk.Checkbutton(self.form, text="递归扫描子目录", variable=self.recursive).grid(row=3, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="替换已有封面", variable=self.replace_existing).grid(row=4, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="实际写入（未选中时仅预览）", variable=self.write).grid(row=5, column=0, columnspan=2, sticky="w", pady=7)
        self.add_actions(6)

    def collect_parameters(self) -> dict[str, object]:
        return {
            "input_path": self.required(self.input_path.get(), "音频输入目录"),
            "cover_image": self.required(self.cover_image.get(), "封面图片"),
            "recursive": self.recursive.get(),
            "replace_existing": self.replace_existing.get(),
            "write": self.write.get(),
            "max_files": self.nonnegative_int(self.max_files.get(), "最大文件数"),
        }

    def execute(self, context: AppContext, parameters: dict[str, object], token: CancellationToken, progress: ProgressCallback) -> FlowResult:
        return apply_cover_flow.run(context, **parameters, progress=progress, cancel_token=token)  # type: ignore[arg-type]

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        self.input_path.set(config.get("input_path", ""))
        self.cover_image.set(config.get("cover_image", ""))
        self.max_files.set(str(config.get("max_files", 0)))
        self.recursive.set(bool(config.get("recursive", True)))
        self.replace_existing.set(bool(config.get("replace_existing", True)))
        self.write.set(bool(config.get("write", False)))


class SplitAudioTab(WorkflowTab):
    title = "音频分割"

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.input_path = tk.StringVar(self)
        self.output_dir = tk.StringVar(self)
        self.duration_minutes = tk.StringVar(self, "30")
        self.bitrate = tk.StringVar(self, "192k")
        self.max_files = tk.StringVar(self, "0")
        self.recursive = tk.BooleanVar(self, True)
        self.overwrite = tk.BooleanVar(self, False)
        self.extensions = {name: tk.BooleanVar(self, name in {"mp3", "m4a"}) for name in ("mp3", "m4a", "wma", "wav", "flac")}
        self.add_path(0, "音频输入目录", self.input_path)
        self.add_path(1, "分段输出目录", self.output_dir)
        ttk.Label(self.form, text="输入格式").grid(row=2, column=0, sticky="w", pady=7)
        extension_box = ttk.Frame(self.form)
        extension_box.grid(row=2, column=1, columnspan=5, sticky="w")
        for name, variable in self.extensions.items():
            ttk.Checkbutton(extension_box, text=name, variable=variable).pack(side="left", padx=(0, 18))
        self.add_entry(3, "每段时长（分钟）", self.duration_minutes)
        self.add_entry(4, "输出比特率", self.bitrate, values=("128k", "192k", "256k", "320k"))
        self.add_entry(5, "最大文件数 (0=无限制)", self.max_files)
        ttk.Checkbutton(self.form, text="递归扫描子目录", variable=self.recursive).grid(row=6, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(self.form, text="覆盖已有分段", variable=self.overwrite).grid(row=7, column=0, columnspan=2, sticky="w", pady=7)
        self.add_actions(8)

    def collect_parameters(self) -> dict[str, object]:
        extensions = [name for name, variable in self.extensions.items() if variable.get()]
        if not extensions:
            raise ValueError("至少选择一种输入格式")
        try:
            duration = float(self.duration_minutes.get())
        except ValueError as exc:
            raise ValueError("每段时长必须是数字") from exc
        if duration <= 0:
            raise ValueError("每段时长必须大于 0")
        return {
            "input_path": self.required(self.input_path.get(), "音频输入目录"),
            "output_dir": self.required(self.output_dir.get(), "分段输出目录"),
            "input_extensions": extensions,
            "recursive": self.recursive.get(),
            "duration_minutes": duration,
            "bitrate": self.required(self.bitrate.get(), "输出比特率"),
            "overwrite": self.overwrite.get(),
            "max_files": self.nonnegative_int(self.max_files.get(), "最大文件数"),
        }

    def execute(self, context: AppContext, parameters: dict[str, object], token: CancellationToken, progress: ProgressCallback) -> FlowResult:
        return split_audio_flow.run(context, **parameters, progress=progress, cancel_token=token)  # type: ignore[arg-type]

    def load_config(self, config: dict[str, Any], app_config: dict[str, Any]) -> None:
        self.input_path.set(config.get("input_path", ""))
        self.output_dir.set(config.get("output_dir", ""))
        self.duration_minutes.set(str(config.get("duration_minutes", 30)))
        self.bitrate.set(config.get("bitrate", "192k"))
        self.max_files.set(str(config.get("max_files", 0)))
        self.recursive.set(bool(config.get("recursive", True)))
        self.overwrite.set(bool(config.get("overwrite", False)))
        selected = set(config.get("input_extensions", []))
        for name, variable in self.extensions.items():
            variable.set(name in selected)


TAB_TYPES = (ConvertTab, MetadataTab, PrepareCoverTab, ApplyCoverTab, SplitAudioTab)
TAB_CONFIG_NAMES = ("convert_audio", "update_metadata", "prepare_cover", "apply_cover", "split_audio")
