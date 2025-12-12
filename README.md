# Mp3 Processor

这是一个用于批量处理音频文件的 Python 工具集。主要功能包括音频格式转换（如 MP4/M4A 转 MP3）、音频元数据（ID3 标签）批量修改以及封面图片处理。

## 功能特性

* **音频格式转换**:
  * 支持将 MP4 视频文件转换为 M4A 音频。
  * 支持将 M4A 音频文件批量转换为 MP3 格式。
  * 支持 WMA 转 M4A (实验性)。
* **元数据管理**:
  * 批量修改 MP3 和 M4A 文件的元数据（艺术家、专辑、标题）。
  * 自动根据文件名设置标题（支持去除文件名前的序号）。
* **封面处理**:
  * 批量裁剪图片，用于制作音频封面。

## 环境要求

* Python 3.x
* FFmpeg (必须安装并添加到系统环境变量中，用于音频转换)

## 安装步骤

1. 克隆或下载本项目。
2. 安装 Python 依赖包：

   ```bash
   pip install -r requirements.txt
   ```

## 配置说明

项目使用 YAML 文件进行配置，请根据需要修改根目录下的配置文件。

### 1. 音频转换配置 (`audio_convert.yaml`)

用于配置音频转换的目标目录和遍历深度。

```yaml
target_directory: "你的音频文件夹路径"  # 例如: "C:/Music/MyAlbum"
depth: 1                              # 遍历子目录的深度
```

### 2. 元数据配置 (`mp3_metadata.yaml`)

用于配置批量修改元数据时的艺术家和专辑信息。

```yaml
artist: "艺术家名称"      # 例如: "周杰伦"
album: "专辑名称"        # 例如: "范特西"
```

## 使用方法

### 1. 音频格式转换

该脚本主要用于将指定目录下的 M4A 文件转换为 MP3 文件。

1. 修改 `audio_convert.yaml` 中的 `target_directory` 为你包含音频文件的目录。
2. 运行脚本：

   ```bash
   python src/audio_convert.py
   ```

   *注意：脚本默认行为是查找指定目录下的子目录，并将 M4A 转换为 MP3。如需启用 MP4 转 M4A 功能，可能需要取消代码中的注释。*

### 2. 修改音频元数据

该脚本用于批量更新音频文件的标签信息。

1. 修改 `mp3_metadata.yaml` 设置艺术家和专辑信息。
2. **注意**：目前 `src/mp3_metadata.py` 中可能包含硬编码的路径，请在运行前检查并修改 `process_audio_files` 调用的路径。
3. 运行脚本：

   ```bash
   python src/mp3_metadata.py
   ```

### 3. 封面图片处理

`src/cover_handler.py` 提供了图片裁剪功能，可用于批量处理封面图。

## 项目结构

```text
Mp3_Processor/
├── assets/                 # 资源文件（如封面图）
├── logs/                   # 运行日志
├── src/                    # 源代码
│   ├── audio_convert.py    # 音频转换逻辑
│   ├── cover_handler.py    # 封面处理逻辑
│   ├── mp3_metadata.py     # 元数据处理逻辑
│   └── ...
├── audio_convert.yaml      # 转换配置文件
├── mp3_metadata.yaml       # 元数据配置文件
├── requirements.txt        # 项目依赖
└── README.md               # 项目说明文档
```

## 注意事项

* 请确保在运行转换脚本前备份您的原始音频文件。
* 使用 FFmpeg 相关功能时，请确保系统已正确安装 FFmpeg。
