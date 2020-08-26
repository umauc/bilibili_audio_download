# bilibili_audio_download
Bilibili收藏视频下载并转成音频文件

# 特点
1. 多线程下载（百度的代码）

2. 支持分P

3. 支持长视频（理论）

4. 支持断点续传

5. 支持在添加新视频后无需重新下载整个收藏夹

6. 支持自动添加ID3Tag

# 部署
```
git clone https://github.com/umauc/bilibili_audio_download.git
cd bilibili_audio_download
pip3 install -r requirements.txt
# win用户请找个ffmpeg的可执行文件放到bilibili_audio_download目录下并将文件重命名为ffmpeg.exe
python3 bilibili_audio_download_win.py
# linux请验证是否已安装ffmpeg（ffmpeg  -version）
python3 bilibili_audio_download_linux.py
```

# 使用
打开一个Bilibili收藏夹（公开）

复制链接中的fid（例：链接：https://space.bilibili.com/6601679/favlist?fid=1042069179&ftype=create ，fid为1042069179）

所得的fid即为media_id，复制粘贴回车即可

# 更新日志
v1.0.1：

1. 添加对ID3Tag的支持

2. 修复在部分情况下会重置info.json的bug

3. 修复win下文件重命名出错的bug

4. 优化使用体验

v1.0.0：

初次上传