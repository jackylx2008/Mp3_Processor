# Mp3 Processor

Mp3 Processor 是一个面向批量音频业务的 Python 工具集，支持格式转换、元数据更新、封面准备与写入、长音频切分。项目按“基础能力模块 + 场景编排层 + 独立入口脚本”组织，业务文件与代码解耦。

## 安全约定

- `mp3_files/`、`input/`、`output/`、`logs/`、`common.env` 均不提交 Git。
- 格式转换和切分只写入 `output/`，不会删除源文件。
- 元数据与封面流程默认仅预览；必须传入 `--write` 才会修改业务音频。
- 首次正式处理前仍建议备份原始音频。

## 环境准备

要求安装 Anaconda 或 Miniconda。项目使用根目录前缀环境 `.venv`，`environment.yml` 会安装 Python 3.12、开发依赖和 FFmpeg。

`.venv` 只供当前操作系统使用，不提交 Git，也不能在 Windows 和 macOS 之间复用。如果项目由 Synology Drive 同步，应在同步工具中排除 `.venv/`，并在每台机器上从 `environment.yml` 重建。

Windows PowerShell：

```powershell
conda env create --prefix .\.venv -f environment.yml
conda activate .\.venv
.\.venv\python.exe -m pytest -q
```

macOS/Linux：

```bash
conda env create --prefix ./.venv -f environment.yml
conda activate ./.venv
./.venv/bin/python -m pytest -q
```

依赖声明变化后执行：

```bash
conda env update --prefix ./.venv -f environment.yml --prune
```

激活环境后可直接运行入口。`FFMPEG_PATH` 默认为 `ffmpeg`（Conda 环境已提供），也可在 `common.env` 中设为本机 FFmpeg 的绝对路径。

## 配置

所有工作流统一读取根目录 `config.yaml`。本机差异写入不入库的 `common.env`：

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

默认业务输入目录为 `mp3_files/input/`，也可以通过 `config.yaml`、`common.env` 或入口参数 `--input` 覆盖。

## 工作流入口

### 转换音频

递归查找 M4A、MP4、WMA，转换为 MP3，并保留输入目录层级：

```powershell
python convert_audio.py --max-files 1
python convert_audio.py --input input --output output/converted
```

默认输出到 `output/converted/`。已有文件默认跳过，可在配置中启用覆盖。

### 更新元数据

预览前 5 个文件的标题、艺术家和专辑：

```powershell
python update_metadata.py --max-files 5
```

确认配置后实际写入：

```powershell
python update_metadata.py --write
```

标题默认取文件名，并把“第001集”规范为“第1集”。艺术家和专辑配置位于 `flows.update_metadata`。

### 裁剪封面图片

```powershell
python prepare_cover.py --input assets/cover_images/input --output output/covers
```

裁剪区域由 `flows.prepare_cover.crop_box` 控制，格式为 `[左, 上, 右, 下]`。

### 写入音频封面

先预览：

```powershell
python apply_cover.py --cover output/covers/sample.png --max-files 5
```

确认后写入：

```powershell
python apply_cover.py --cover output/covers/sample.png --write
```

支持 MP3、M4A 和 WMA；封面图片使用 PNG 或 JPEG。

### 切分音频

```powershell
python split_audio.py --max-files 1
```

默认按 30 分钟切分到 `output/split/`，最后不足 30 分钟的片段也会保留。

每个入口都支持 `--help` 和 `--config-file`。

## 代码结构

```text
Mp3_Processor/
├── logging_config.py              # 全项目唯一日志初始化
├── config.yaml                    # 统一配置入口
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
│   ├── modules/                   # 单一职责基础能力
│   └── flows/                     # 业务步骤编排
├── docs/                          # README 之外的项目文档
├── tests/                         # 自动化测试
└── logs/                          # 运行日志（不提交 Git）
```

模块层不读取业务配置，也不决定完整执行路径；flows 通过 `AppContext` 获取配置并组合模块；根目录入口只负责参数、启动、调用和结果输出。

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

使用业务样本做低风险验证时，先限制文件数量：

```powershell
python update_metadata.py --max-files 3
python convert_audio.py --max-files 1
```

## 旧版本迁移

旧版的 `audio_convert.yaml`、`mp3_metadata.yaml`、`path.yaml` 已合并到 `config.yaml`；旧 `src/*.py` 直接执行方式已替换为根目录独立入口。真实路径和专辑信息不要写回仓库配置，应放入 `common.env`。
