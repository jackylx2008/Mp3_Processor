import os

audio_folder = "D:/CloudStation/有声书/哈利·波特/哈利波特（7部全集）/第1部"

if os.path.exists(audio_folder):
    files = os.listdir(audio_folder)
    print(f"目录 '{audio_folder}' 中的文件: {files}")
else:
    print(f"目录 '{audio_folder}' 不存在。")
