# 架构说明

## 分层与依赖方向

项目只允许依赖由外向内流动：

```text
Tkinter GUI / 根目录入口
    ↓
flows 场景编排层
    ↓
modules 基础能力层
```

`config_loader.py`、`context.py`、`platform_tools.py` 和 `logging_config.py` 为三层提供公共基础设施。基础模块不能反向导入 flow 或入口脚本。

## 各层职责

### GUI 与根目录入口

`gui.py` 是主要桌面入口，默认读取 `ui_config.yaml`。`src/mp3_processor/gui/` 负责窗口、表单、后台任务、日志和状态显示，不实现文件遍历、音频读写或图片处理。

GUI 主线程只更新控件。工作流在单独的后台线程中执行，通过线程安全队列发送进度和日志；同一时间只允许一个工作流任务。音频转换流可在该后台任务内并发运行多个 FFmpeg 进程。`CancellationToken` 在文件、并发调度或分段边界协作式停止任务。

原有根目录 CLI 入口仍可用于开发和排障，但不属于 UI 配置接口：

当前入口：

- `convert_audio.py`
- `update_metadata.py`
- `prepare_cover.py`
- `apply_cover.py`
- `split_audio.py`

### flows

flow 负责确定一个业务场景的步骤顺序，例如“发现文件 → 映射输出路径 → 转换 → 验证 → 汇总”。flow 从 `AppContext` 读取全局和场景配置，并通过 `FlowResult` 返回统一结果。音频转换流使用有界线程池调度外部 FFmpeg 进程，结果汇总和进度更新集中在调度线程完成。

flow 可以组合多个 modules，但不直接实现 FFmpeg 命令、标签格式或图片编码细节。

### modules

modules 提供小而稳定的能力：

- `files.py`：文件发现、扩展名过滤、递归深度、输出路径映射。
- `audio_converter.py`：FFmpeg 转换和快速解码验证。
- `metadata_editor.py`：标题规范化及 MP3/M4A 标签写入。
- `cover_editor.py`：图片裁剪、文字渲染及音频封面写入。
- `audio_splitter.py`：按时长切分并验证输出。

模块接收已经解析的 `Path` 和明确参数，不读取 `config.yaml`，因此可独立测试和复用。

## 配置生命周期

1. GUI 定位项目根目录和 `ui_config.yaml`，CLI 可继续读取 `config.yaml`。
2. `config_loader` 先读取 `common.env`，但不覆盖进程中已有的环境变量。
3. `config_loader` 按 Windows、macOS 或 Linux 选择对应的 `CLOUDSTATION_ROOT_*`，显式的 `CLOUDSTATION_ROOT` 优先。
4. YAML 中的 `${ENV_VAR:-default}` 被递归展开。
5. `AppContext.resolve_path()` 将相对路径统一解释为相对项目根目录。
6. GUI flow 读取自己的 `workflows.<name>` 节点；运行时表单参数优先于配置初始值。

界面中的修改只影响本次运行，不写回 YAML。重新加载配置只允许在没有任务运行时执行。

真实机器路径只放在 `common.env`。仓库中的 `config.yaml` 和 `common.env.example` 使用相对路径或通用示例。

## 数据安全边界

- 输入业务文件默认位于 Git 忽略目录。
- 转换与切分创建新文件，不删除源文件。音频转换会拒绝输入输出同路径，并跳过映射到同一目标文件的输入冲突。
- 元数据和封面写入需要入口显式收到 `--write`。
- `--max-files` 可用于小批量验证。
- 切分开始前会检查整组目标文件，避免发现冲突时只生成部分分段。
- 所有工作流用 `FlowResult` 记录成功、跳过、失败和输出路径。
- 元数据和封面嵌入默认预览，实际写入前由 GUI 二次确认。
- 取消转换任务后立即停止提交新文件；已经启动的并发 FFmpeg 进程完成后安全退出。其他工作流在文件或分段边界检查取消状态。

## 扩展新工作流

1. 先判断是否需要新的基础能力；需要时在 `modules/` 新增单一职责模块和测试。
2. 在 `flows/` 新增 `run(context, ...) -> FlowResult`，组合模块并处理阶段边界。
3. 在 `config.yaml` 增加 `flows.<name>` 默认配置。
4. 在根目录增加带完整中文 docstring 的薄入口。
5. 更新 README 的运行命令，并用受控样本完成预览和端到端测试。
