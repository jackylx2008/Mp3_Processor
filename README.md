# Mp3 Processor

Mp3 Processor 是一个带统一桌面界面的批量音频处理工具，支持格式转换、元数据更新、封面准备与写入、长音频切分。项目按“Tkinter 界面层 + 场景编排层 + 基础能力模块”组织，界面与音频处理逻辑相互解耦。

## 安全约定

- `mp3_files/`、`input/`、`output/`、`logs/`、`common.env` 均不提交 Git。
- 格式转换和切分只写入 `output/`，不会删除源文件。
- 元数据与封面流程默认仅预览；必须传入 `--write` 才会修改业务音频。
- 首次正式处理前仍建议备份原始音频。

## 环境准备

要求安装 Anaconda 或 Miniconda。项目使用根目录前缀环境 `.conda`，`environment.yml` 会安装 Python 3.12、开发依赖和 FFmpeg。

`.conda` 只供当前操作系统使用，不提交 Git，也不能在 Windows 和 macOS 之间复用。如果项目由 Synology Drive 同步，应在同步工具中排除 `.conda/`，并在每台机器上从 `environment.yml` 重建。

Windows PowerShell：

```powershell
conda env create --prefix .\.conda -f environment.yml
conda activate .\.conda
.\.conda\python.exe -m pytest -q
```

macOS/Linux：

```bash
conda env create --prefix ./.conda -f environment.yml
conda activate ./.conda
./.conda/bin/python -m pytest -q
```

依赖声明变化后执行：

```bash
conda env update --prefix ./.conda -f environment.yml --prune
```

激活环境后可直接运行入口。`FFMPEG_PATH` 默认为 `ffmpeg`（Conda 环境已提供），也可在 `common.env` 中设为本机 FFmpeg 的绝对路径。

## 启动桌面界面

激活项目环境后运行：

```powershell
python gui.py
```

也可以指定另一份 UI 配置：

```powershell
python gui.py --config-file path/to/ui_config.yaml
```

窗口包含五个工作流页签和一个“全局配置”页签：

- 音频转换：可选 MP3/M4A/MP4/WMA/WAV/FLAC/OGG 输入，并输出为 MP3/M4A/WMA/WAV/FLAC/OGG；默认使用 8 个并发 FFmpeg 任务。
- 元数据更新：艺术家、专辑、文件夹专辑名和预览/实际写入。
- 封面裁剪：图片目录、裁剪区域和覆盖选项。
- 封面嵌入：封面选择、替换策略和预览/实际写入。
- 音频分割：源格式、分段时长、码率和覆盖选项。
- 全局配置：选择或重新加载 UI YAML 配置文件。

同一时间只运行一个工作流任务。耗时处理在后台线程执行，音频转换工作流内部采用有界文件并发。点击“取消任务”后，程序会停止提交新文件，等待已经启动的 FFmpeg 任务安全结束；状态栏会显示真实的 HH:MM:SS 任务耗时。

## UI 配置

桌面界面默认读取根目录 `ui_config.yaml`。该文件分为三部分：

- `app`：窗口标题、日志级别和 FFmpeg。
- `ui`：窗口尺寸和日志保留行数。
- `workflows`：五个页签的初始值。

顶部“全局配置文件”区域可以选择并重新加载其他 YAML 文件。界面上修改的参数仅作用于本次运行，不自动写回配置文件。

本机路径差异仍写入不入库的 `common.env`：

```powershell
Copy-Item common.env.example common.env
```

macOS/Linux：

```bash
cp common.env.example common.env
```

路径优先使用相对项目根目录的写法。跨平台绝对路径可通过以下环境变量管理：

- `CLOUDSTATION_ROOT_WINDOWS`
- `CLOUDSTATION_ROOT_MACOS`
- `CLOUDSTATION_ROOT_LINUX`
- `CLOUDSTATION_ROOT`（显式设置时优先）

默认映射为 Windows `D:\CloudStaion`、macOS `~/SynologyDrive`、Linux `~/CloudStation`。配置加载器会按当前系统自动选择，业务模块不需要判断操作系统。

默认业务输入目录为 `mp3_files/input/`，也可以通过 `ui_config.yaml`、`common.env` 或界面路径选择器覆盖。

## 安全操作

- 元数据和封面嵌入默认仅预览；勾选“实际写入”后还会显示确认框。
- 任务运行时禁止重复启动和重新加载配置。
- 关闭运行中的窗口时，会先请求取消并等待安全处理边界。
- 转换和分割默认不覆盖已有文件。
- 日志同时显示在窗口并写入 `logs/gui.log`。

## 命令行入口

根目录下原有的独立 CLI 脚本仍保留用于开发和排障，但不作为新 UI 配置接口的一部分。桌面界面只读取 `ui_config.yaml` 的 `workflows` 配置。

转换入口可通过参数覆盖输入和输出类型，例如：

    python convert_audio.py --input-type mp3 m4a --output-type flac --workers 8 --max-files 5

不传参数时读取 `config.yaml`：`input_extensions` 控制输入类型，`output_type` 控制输出类型，`workers` 控制并发任务数（默认 8，范围 1–32）；默认包含 MP3 输入并输出 MP3。命令行参数优先级更高。

## 转换性能

- 建议把输入和输出目录放在本地 SSD/NVMe 硬盘，避免 OneDrive 等同步目录在批量创建文件时成为瓶颈。
- Ryzen 9 9950X 建议从 8 个并发任务开始；如果 CPU、磁盘仍有余量，可测试 12 或 16。更高并发不一定更快。
- RTX 5090 的 NVENC 主要用于视频编码，FFmpeg 的 MP3、AAC、FLAC、OGG 等常规音频编码仍以 CPU 为主，因此本项目采用文件级 CPU 并发。
- 默认保留转换后音频验证以保证输出完整性；关闭验证可以减少少量耗时，但会降低批量任务的安全性。

## 代码结构

```text
Mp3_Processor/
├── logging_config.py              # 全项目唯一日志初始化
├── gui.py                         # 统一桌面界面入口
├── ui_config.yaml                 # UI 与五个工作流的初始配置
├── config.yaml                    # 原 CLI 配置
├── environment.yml               # 跨平台 Conda 环境声明
├── common.env.example             # 本机环境示例
├── convert_audio.py               # 转换工作流入口
├── update_metadata.py             # 元数据工作流入口
├── prepare_cover.py               # 封面图片准备入口
├── apply_cover.py                 # 音频封面写入入口
├── split_audio.py                 # 音频切分入口
├── src/mp3_processor/
│   ├── bootstrap.py               # 入口共用的配置与日志初始化
│   ├── cli.py                     # 统一结果输出与退出状态
│   ├── config_loader.py           # YAML、dotenv、环境变量解析
│   ├── context.py                 # 统一应用上下文
│   ├── platform_tools.py          # 跨平台外部工具定位
│   ├── results.py                 # 工作流结构化结果
│   ├── execution.py               # 进度事件与协作式取消
│   ├── gui/                       # Tkinter 界面与后台任务桥接
│   ├── modules/                   # 单一职责基础能力
│   └── flows/                     # 业务步骤编排
├── docs/                          # README 之外的项目文档
├── tests/                         # 自动化测试
└── logs/                          # 运行日志（不提交 Git）
```

桌面图标资源位于 `assets/app_icon/`：运行时使用 PNG，Windows 使用多尺寸 ICO，macOS ICNS 可用于应用打包。GUI 启动时会按平台设置标题栏、任务栏或 Dock 图标。

模块层不读取业务配置，也不决定完整执行路径；flows 通过 `AppContext` 获取配置并组合模块；GUI 只负责收集参数、启动后台任务和显示结构化反馈。

更详细的依赖方向、配置生命周期和扩展步骤见 [架构说明](docs/ARCHITECTURE.md)；路径、环境、换行和云盘同步约定见 [跨平台编程与协作规范](docs/CROSS_PLATFORM_PROGRAMMING.md)。

## 测试与检查

运行自动化测试：

```powershell
python -m pytest -q
```

运行静态检查：

```powershell
flake8 .
```

使用业务样本做低风险验证时，在对应页签将“最大文件数”设为较小值，并先使用预览模式。

## 旧版本迁移

旧版的 `audio_convert.yaml`、`mp3_metadata.yaml`、`path.yaml` 已合并到 `config.yaml`；旧 `src/*.py` 直接执行方式已替换为根目录独立入口。真实路径和专辑信息不要写回仓库配置，应放入 `common.env`。
