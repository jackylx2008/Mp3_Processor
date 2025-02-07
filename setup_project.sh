#!/bin/bash

# 创建项目根目录
echo "Setting up project structure..."

# 创建主目录
mkdir -p ./{assets/cover_images,mp3_files/{input,output},src,tests,config,logs}

# 创建空的配置文件
touch ./config/config.yaml
touch ./.env

# 创建空的日志文件
touch ./logs/mp3_processor.log

# 创建requirements.txt
echo "pydub" > ./requirements.txt
echo "eyed3" >> ./requirements.txt
echo "Pillow" >> ./requirements.txt

# 创建README.md
echo "# MP3 Processor" > ./README.md
echo "This project processes MP3 files: splitting, adding covers, and updating metadata." >> ./README.md

# 创建src文件夹中的初始化文件
touch ./src/{__init__.py,file_handler.py,mp3_metadata.py,cover_handler.py,utils.py}

# 创建测试文件
touch ./tests/{test_file_handler.py,test_mp3_metadata.py,test_cover_handler.py,test_utils.py}

echo "Project structure created successfully!"
