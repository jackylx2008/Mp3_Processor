"""Mp3 Processor 的 Tkinter 主窗口。"""

from __future__ import annotations

import json
import logging
import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from logging_config import LOG_FORMAT, get_logger, setup_logger
from mp3_processor.config_loader import load_config
from mp3_processor.context import AppContext
from mp3_processor.execution import ProgressEvent
from mp3_processor.gui.tabs import TAB_CONFIG_NAMES, TAB_TYPES, WorkflowTab
from mp3_processor.gui.task_runner import QueueLogHandler, Task, TaskMessage, TaskRunner
from mp3_processor.platform_tools import resolve_executable
from mp3_processor.results import FlowResult


class Mp3ProcessorApp:
    """统一承载配置、五个工作流和运行反馈的桌面窗口。"""

    POLL_INTERVAL_MS = 100
    LOG_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?$")

    def __init__(self, root: tk.Tk, project_root: Path, config_path: Path, config: dict[str, Any]) -> None:
        self.root = root
        self.project_root = project_root
        self.config_path = config_path
        self.config = config
        self.context = AppContext(project_root, config, get_logger("mp3_processor.gui"))
        self.runner = TaskRunner()
        self.tabs: list[WorkflowTab] = []
        self.close_when_done = False
        self.max_log_lines = 2000

        self._configure_window()
        self._build_layout()
        self._attach_log_handler()
        self._apply_config(config_path, config, initial=True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_messages)

    def _configure_window(self) -> None:
        self.root.minsize(880, 650)
        self._set_window_icon()
        style = ttk.Style(self.root)
        style.configure("Accent.TButton", font=("TkDefaultFont", 11, "bold"), padding=(14, 8))
        style.configure("Status.TLabel", padding=(8, 5))

    def _set_window_icon(self) -> None:
        """按当前平台设置标题栏、任务栏或 Dock 图标。"""
        icon_root = self.project_root / "assets" / "app_icon"
        png_path = icon_root / "mp3_processor.png"
        ico_path = icon_root / "mp3_processor.ico"
        self.window_icon: tk.PhotoImage | None = None
        try:
            self.window_icon = tk.PhotoImage(master=self.root, file=png_path)
            self.root.iconphoto(True, self.window_icon)
        except (OSError, tk.TclError) as exc:
            logging.getLogger(__name__).warning("PNG 应用图标加载失败: %s", exc)
        try:
            if sys.platform == "win32" and ico_path.is_file():
                self.root.iconbitmap(default=str(ico_path))
            elif sys.platform == "darwin":
                _set_macos_app_icon(png_path)
        except (OSError, tk.TclError) as exc:
            logging.getLogger(__name__).warning("平台原生应用图标加载失败: %s", exc)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=3)
        self.root.rowconfigure(1, weight=2)
        self.config_variable = tk.StringVar(self.root, str(self.config_path))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=(8, 3))
        common = {
            "project_root": self.project_root,
            "context_provider": lambda: self.context,
            "start_callback": self.start_task,
            "cancel_callback": self.cancel_task,
            "preview_callback": self.preview_parameters,
        }
        for tab_type in TAB_TYPES:
            tab = tab_type(self.notebook, **common)
            self.tabs.append(tab)
            self.notebook.add(tab, text=tab.title)
        self._add_config_tab()

        log_frame = ttk.LabelFrame(self.root, text="运行日志与实时输出 (Execution Log & Console Output)", padding=6)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(3, 4))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        ttk.Button(log_frame, text="清空日志", command=self._clear_log, width=10).grid(row=0, column=0, sticky="e", pady=(0, 5))
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            state="disabled",
            background="#171923",
            foreground="#e2e8f0",
            insertbackground="#e2e8f0",
            font=("TkFixedFont", 11),
            wrap="word",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self._configure_log_colors()

        status = ttk.Frame(self.root)
        status.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        status.columnconfigure(0, weight=1)
        self.status_variable = tk.StringVar(self.root, "状态：就绪")
        self.ffmpeg_variable = tk.StringVar(self.root, "FFmpeg：检查中")
        self.progress = ttk.Progressbar(status, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        ttk.Label(status, textvariable=self.status_variable, style="Status.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(status, textvariable=self.ffmpeg_variable, style="Status.TLabel").grid(row=1, column=1)
        ttk.Label(status, text=f"Python Tkinter / Tk {tk.TkVersion}", style="Status.TLabel").grid(row=1, column=2, sticky="e")

    def _add_config_tab(self) -> None:
        config_tab = ttk.Frame(self.notebook, padding=12)
        config_tab.columnconfigure(0, weight=1)
        config_group = ttk.LabelFrame(config_tab, text="全局配置文件 (Config)", padding=10)
        config_group.grid(row=0, column=0, sticky="ew")
        config_group.columnconfigure(1, weight=1)
        ttk.Label(config_group, text="配置文件路径").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(config_group, textvariable=self.config_variable).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(config_group, text="浏览…", command=self._browse_config, width=10).grid(row=0, column=2, padx=(6, 3), pady=4)
        ttk.Button(config_group, text="重新加载", command=self._reload_config, width=12).grid(row=0, column=3, padx=(3, 0), pady=4)
        ttk.Label(
            config_group,
            text="重新加载会用 YAML 中的初始值刷新五个工作流页签；界面修改不会自动写回配置文件。",
            foreground="#666666",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))
        self.notebook.add(config_tab, text="全局配置")

    def _configure_log_colors(self) -> None:
        """使用接近标准终端 ANSI 色的深色日志主题。"""
        self.log_text.tag_configure("timestamp", foreground="#808080")
        self.log_text.tag_configure("separator", foreground="#808080")
        self.log_text.tag_configure("logger", foreground="#57c7ff")
        self.log_text.tag_configure("DEBUG", foreground="#9aedfe")
        self.log_text.tag_configure("INFO", foreground="#5af78e")
        self.log_text.tag_configure("WARNING", foreground="#f3f99d")
        self.log_text.tag_configure("ERROR", foreground="#ff5f56")
        self.log_text.tag_configure("CRITICAL", foreground="#ff6ac1", font=("TkFixedFont", 11, "bold"))
        self.log_text.tag_configure("message", foreground="#f1f1f0")

    def _attach_log_handler(self) -> None:
        self.queue_log_handler = QueueLogHandler(self.runner.post_log)
        self.queue_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(self.queue_log_handler)

    def _apply_config(self, path: Path, config: dict[str, Any], *, initial: bool = False) -> None:
        app_config = self._mapping(config, "app")
        ui_config = self._mapping(config, "ui")
        workflows = self._mapping(config, "workflows")
        self.config_path = path
        self.config = config
        self.context = AppContext(self.project_root, config, get_logger("mp3_processor.gui"))
        self.config_variable.set(str(path))
        self.root.title(str(app_config.get("title", "MP3 Processor GUI")))
        geometry = str(ui_config.get("geometry", "1104x760"))
        if "x" in geometry:
            self.root.geometry(geometry)
        self.max_log_lines = max(100, int(ui_config.get("max_log_lines", 2000)))
        self._set_log_level(str(app_config.get("log_level", "INFO")))
        for tab, name in zip(self.tabs, TAB_CONFIG_NAMES, strict=True):
            tab.load_config(self._mapping(workflows, name), app_config)
        self._check_ffmpeg(str(app_config.get("ffmpeg", "ffmpeg")))
        if not initial:
            self.status_variable.set("状态：配置已重新加载")
            self._append_log(f"已加载 UI 配置：{path}")

    def _browse_config(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            initialdir=self.config_path.parent,
            filetypes=(("YAML 配置", "*.yaml *.yml"), ("所有文件", "*")),
        )
        if selected:
            self.config_variable.set(selected)
            self._reload_config()

    def _reload_config(self) -> None:
        if self.runner.active:
            messagebox.showwarning("任务运行中", "任务结束或取消后才能重新加载配置。", parent=self.root)
            return
        path = Path(self.config_variable.get()).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        try:
            config = load_config(path)
            self._apply_config(path.resolve(), config)
        except Exception as exc:
            messagebox.showerror("配置加载失败", str(exc), parent=self.root)

    def start_task(self, name: str, task: Task) -> bool:
        if not self.runner.start(name, task):
            messagebox.showwarning("任务运行中", "当前已有任务正在执行。", parent=self.root)
            return False
        self.progress.configure(value=0)
        self.status_variable.set(f"状态：正在启动{name}")
        self._set_tabs_running(True)
        return True

    def cancel_task(self) -> None:
        if self.runner.cancel():
            self.status_variable.set("状态：正在取消，将在安全处理边界停止…")
            self._append_log("已请求取消任务；当前文件安全结束后停止。")

    def preview_parameters(self, name: str, parameters: dict[str, object]) -> None:
        rendered = json.dumps(parameters, ensure_ascii=False, indent=2, default=str)
        self._append_log(f"[{name}] 本次运行参数：\n{rendered}")
        self.status_variable.set(f"状态：已预览{name}参数")

    def _poll_messages(self) -> None:
        for message in self.runner.drain():
            self._handle_message(message)
        if self.close_when_done and not self.runner.active:
            self._destroy()
            return
        self.root.after(self.POLL_INTERVAL_MS, self._poll_messages)

    def _handle_message(self, message: TaskMessage) -> None:
        if message.kind == "log":
            self._append_log(str(message.payload))
        elif message.kind == "started":
            self.status_variable.set(f"状态：正在执行{message.payload}")
            self._append_log(f"开始执行：{message.payload}")
        elif message.kind == "progress" and isinstance(message.payload, ProgressEvent):
            event = message.payload
            percent = event.current * 100 / event.total if event.total else 0
            self.progress.configure(value=percent)
            suffix = f"（{event.current}/{event.total}）" if event.total else ""
            self.status_variable.set(f"状态：{event.message}{suffix}")
        elif message.kind == "completed" and isinstance(message.payload, FlowResult):
            result = message.payload
            self.progress.configure(value=100)
            summary = (
                f"完成：发现 {result.discovered}，成功 {result.succeeded}，"
                f"跳过 {result.skipped}，失败 {result.failed}"
            )
            self.status_variable.set(f"状态：{summary}")
            self._append_log(summary)
            self._set_tabs_running(False)
            if result.failed:
                messagebox.showwarning("任务完成但存在错误", summary, parent=self.root)
        elif message.kind == "cancelled":
            self.status_variable.set("状态：任务已取消")
            self._append_log("任务已取消。")
            self._set_tabs_running(False)
        elif message.kind == "failed":
            self.status_variable.set("状态：任务执行失败")
            self._append_log(f"任务执行失败：{message.payload}")
            self._set_tabs_running(False)
            messagebox.showerror("任务执行失败", str(message.payload), parent=self.root)

    def _set_tabs_running(self, running: bool) -> None:
        for tab in self.tabs:
            tab.set_running(running)

    def _append_log(self, message: str) -> None:
        if not message:
            return
        if not message[:1].isdigit() or " - " not in message[:30]:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"{timestamp} - INFO - GUI - {message}"
        self.log_text.configure(state="normal")
        parts = message.rstrip().split(" - ", 3)
        if len(parts) == 4 and self.LOG_TIMESTAMP.match(parts[0]):
            timestamp, level, logger_name, text = parts
            level_tag = level if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "message"
            message_tag = level_tag if level in {"WARNING", "ERROR", "CRITICAL"} else "message"
            self.log_text.insert("end", timestamp, "timestamp")
            self.log_text.insert("end", " - ", "separator")
            self.log_text.insert("end", level, level_tag)
            self.log_text.insert("end", " - ", "separator")
            self.log_text.insert("end", logger_name, "logger")
            self.log_text.insert("end", " - ", "separator")
            self.log_text.insert("end", text + "\n", message_tag)
        else:
            self.log_text.insert("end", message.rstrip() + "\n", "message")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > self.max_log_lines:
            self.log_text.delete("1.0", f"{line_count - self.max_log_lines + 1}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _check_ffmpeg(self, executable: str) -> None:
        try:
            resolved = resolve_executable(executable, name="FFmpeg")
            self.ffmpeg_variable.set(f"FFmpeg：已配置 ({Path(resolved).name})")
        except FileNotFoundError:
            self.ffmpeg_variable.set("FFmpeg：不可用")

    def _set_log_level(self, value: str) -> None:
        level = logging.getLevelName(value.upper())
        if not isinstance(level, int):
            raise ValueError(f"未知日志级别: {value}")
        logging.getLogger().setLevel(level)

    def _on_close(self) -> None:
        if not self.runner.active:
            self._destroy()
            return
        if messagebox.askyesno(
            "任务运行中",
            "要取消当前任务并在安全停止后关闭窗口吗？",
            parent=self.root,
        ):
            self.close_when_done = True
            self.cancel_task()

    def _destroy(self) -> None:
        logging.getLogger().removeHandler(self.queue_log_handler)
        self.root.destroy()

    @staticmethod
    def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
        value = mapping.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"配置项 {key} 必须是映射")
        return value


def run_gui(project_root: Path, config_path: Path) -> int:
    """加载 UI 配置并启动 Tk 主循环。"""
    config = load_config(config_path)
    app_config = config.get("app", {})
    if not isinstance(app_config, dict):
        raise ValueError("配置项 app 必须是映射")
    setup_logger(
        log_level=app_config.get("log_level", "INFO"),
        log_file=project_root / "logs" / "gui.log",
    )
    _set_windows_app_id()
    root = tk.Tk()
    Mp3ProcessorApp(root, project_root, config_path.resolve(), config)
    root.mainloop()
    return 0


def _set_windows_app_id() -> None:
    """让 Windows 任务栏把程序识别为独立应用，而不是 Python。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "jackylx2008.Mp3Processor"
        )
    except (AttributeError, OSError):
        logging.getLogger(__name__).warning("无法设置 Windows AppUserModelID")


def _set_macos_app_icon(icon_path: Path) -> bool:
    """通过 AppKit 设置 Dock 和应用切换器图标，不修改窗口标题栏。"""
    if sys.platform != "darwin":
        return False
    try:
        import ctypes
        import ctypes.util

        appkit_path = ctypes.util.find_library("AppKit")
        objc_path = ctypes.util.find_library("objc")
        if not appkit_path or not objc_path:
            raise OSError("找不到 macOS AppKit 或 Objective-C Runtime")
        ctypes.cdll.LoadLibrary(appkit_path)
        objc = ctypes.cdll.LoadLibrary(objc_path)
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p

        message_address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        if message_address is None:
            raise OSError("找不到 objc_msgSend")
        send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(message_address)
        send_cstring = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_char_p,
        )(message_address)
        send_object = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(message_address)

        def get_class(name: str) -> int:
            return objc.objc_getClass(name.encode("ascii"))

        def get_selector(name: str) -> int:
            return objc.sel_registerName(name.encode("ascii"))

        application = send(get_class("NSApplication"), get_selector("sharedApplication"))
        ns_path = send_cstring(
            get_class("NSString"),
            get_selector("stringWithUTF8String:"),
            str(icon_path.resolve()).encode("utf-8"),
        )
        image = send_object(
            send(get_class("NSImage"), get_selector("alloc")),
            get_selector("initWithContentsOfFile:"),
            ns_path,
        )
        if not application or not image:
            raise OSError(f"AppKit 无法读取应用图标: {icon_path}")
        try:
            send_object(application, get_selector("setApplicationIconImage:"), image)
            return bool(send(application, get_selector("applicationIconImage")))
        finally:
            send(image, get_selector("release"))
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        logging.getLogger(__name__).warning("macOS 应用图标加载失败: %s", exc)
        return False
