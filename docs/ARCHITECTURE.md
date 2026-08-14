# 架构说明

## 分层与依赖方向

项目只允许依赖由外向内流动：

```text
根目录入口脚本
    ↓
flows 场景编排层
    ↓
modules 基础能力层
```

`config_loader.py`、`context.py`、`platform_tools.py` 和 `logging_config.py` 为三层提供公共基础设施。基础模块不能反向导入 flow 或入口脚本。

## 各层职责

### 根目录入口

入口脚本负责解析命令行参数、创建 `AppContext`、调用一个 flow，并输出结构化结果。入口不实现文件遍历、音频读写或图片处理。

当前入口：

- `convert_audio.py`
- `update_metadata.py`
- `prepare_cover.py`
- `apply_cover.py`
- `split_audio.py`

### flows

flow 负责确定一个业务场景的步骤顺序，例如“发现文件 → 映射输出路径 → 转换 → 验证 → 汇总”。flow 从 `AppContext` 读取全局和场景配置，并通过 `FlowResult` 返回统一结果。

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

1. `bootstrap_context()` 定位项目根目录和 `config.yaml`。
2. `config_loader` 先读取 `common.env`，但不覆盖进程中已有的环境变量。
3. `config_loader` 按 Windows、macOS 或 Linux 选择对应的 `CLOUDSTATION_ROOT_*`，显式的 `CLOUDSTATION_ROOT` 优先。
4. YAML 中的 `${ENV_VAR:-default}` 被递归展开。
5. `AppContext.resolve_path()` 将相对路径统一解释为相对项目根目录。
6. flow 只读取自己的 `flows.<name>` 节点。

真实机器路径只放在 `common.env`。仓库中的 `config.yaml` 和 `common.env.example` 使用相对路径或通用示例。

## 数据安全边界

- 输入业务文件默认位于 Git 忽略目录。
- 转换与切分创建新文件，不删除源文件。
- 元数据和封面写入需要入口显式收到 `--write`。
- `--max-files` 可用于小批量验证。
- 切分开始前会检查整组目标文件，避免发现冲突时只生成部分分段。
- 所有工作流用 `FlowResult` 记录成功、跳过、失败和输出路径。

## 扩展新工作流

1. 先判断是否需要新的基础能力；需要时在 `modules/` 新增单一职责模块和测试。
2. 在 `flows/` 新增 `run(context, ...) -> FlowResult`，组合模块并处理阶段边界。
3. 在 `config.yaml` 增加 `flows.<name>` 默认配置。
4. 在根目录增加带完整中文 docstring 的薄入口。
5. 更新 README 的运行命令，并用受控样本完成预览和端到端测试。
