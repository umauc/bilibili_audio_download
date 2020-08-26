#!/usr/bin/python3

import requests
import math
import os
import json
import threading
import sys
from mutagen.id3 import ID3, APIC, TIT2, TPE1, COMM
from tenacity import retry


media_id = input('media_id:')

#这个多线程下载是抄的，我自己不会多线程（
#链接：https://www.jianshu.com/p/5c71ad87a52c
#为什么他print都没加括号
class downloader:
    def __init__(self,url,name):
        self.url = url
        self.num = 8
        self.name = name
        r = requests.head(self.url,headers={'user-agent': 'my-app/0.0.1', 'referer':'https://www.bilibili.com'})
        # 获取文件大小
        self.total = int(r.headers['Content-Length'])

    # 获取每个线程下载的区间
    def get_range(self):
        ranges = []
        offset = int(self.total/self.num)
        for i in range(self.num):
            if i == self.num-1:
                ranges.append((i*offset, ''))
            else:
                ranges.append((i*offset, (i+1)*offset))
        return ranges  # [(0,100),(100,200),(200,"")]

    # 通过传入开始和结束位置来下载文件
    def download(self, start, end):
        headers = {
            'Range': 'Bytes=%s-%s' % (start, end), 'Accept-Encoding': '*', 'user-agent': 'my-app/0.0.1', 'referer': 'https://www.bilibili.com'}
        res = requests.get(self.url, headers=headers)
        # 将文件指针移动到传入区间开始的位置
        self.fd.seek(start)
        self.fd.write(res.content)

    def run(self):
        self.fd = open(self.name, "wb")
        thread_list = []
        n = 0
        for ran in self.get_range():
            # 获取每个线程下载的数据块
            start, end = ran
            n += 1
            thread = threading.Thread(target=self.download, args=(start, end))
            thread.start()
            thread_list.append(thread)
        for i in thread_list:
            # 设置等待，避免上一个数据块还没写入，下一数据块对文件seek，会报错
            i.join()
        self.fd.close()

#同样是百度的代码
#链接：https://blog.csdn.net/weixin_38587484/article/details/97802917
def SetMp3Info(path, info):
    songFile = ID3(path)
    songFile['APIC'] = APIC(  # 插入封面
        encoding=3,
        mime='image/png',
        type=3,
        desc=u'Cover',
        data=info['picData']
    )
    songFile['TIT2'] = TIT2(  # 插入歌名
        encoding=3,
        text=info['title']
    )
    songFile['TXXX'] = COMM( # 插入详细信息
        encoding=3,
        text=info['desc']
    )
    songFile['TPE1'] = TPE1(  # 插入第一演奏家、歌手、等
        encoding=3,
        text=info['artist']
    )
    songFile
    songFile.save()

print('开始处理')

def get_video_list(media_id):
    media_id = str(media_id)
    print('获取收藏夹数据')
    like_list_info = requests.get(f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&pn=1&ps=20&jsonp=jsonp').json()
    video_count = int(like_list_info.get('data').get('info').get('media_count'))
    page_count = math.ceil(video_count/20)
    page = 1
    like_list = []
    while True:
        medias = requests.get(f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&pn={page}&ps=20&jsonp=jsonp').json().get('data').get('medias')
        for i in medias:
            like_list.append(i.get('bvid'))
        if page == page_count:
            break
        else:
            page = page + 1
    return like_list

def get_like_list_title(media_id):
    media_id = str(media_id)
    print('获取收藏夹标题')
    like_list_info = requests.get(f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&pn=1&ps=20&jsonp=jsonp').json()
    title = like_list_info.get('data').get('info').get('title')
    return title

def get_video_info(bvid):
    video_info = requests.get(f'http://api.bilibili.com/x/web-interface/view?bvid={bvid}').json()
    title = video_info.get('data').get('title')
    pic = video_info.get('data').get('pic')
    owner = video_info.get('data').get('owner').get('name')
    desc = video_info.get('data').get('desc')
    pages_cid = []
    pages_title = {}
    for i in video_info.get('data').get('pages'):
        pages_cid.append(i.get('cid'))
        if i.get('part') != '':
            pages_title[i.get('cid')] = i.get('part')
        else:
            pages_title[i.get('cid')] = title
    return {'title':title,'pic':pic,'pages_cid':pages_cid,'pages_title':pages_title,'owner':owner,'desc':desc}

@retry((stop=stop_after_attempt(1)))
def download_video(bvid,cid,like_list_title):
    cid = str(cid)
    info = get_video_info(bvid)
    print(f'获取视频数据({bvid})')
    video_download_info = requests.get(f'http://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}').json()
    video_download_url = []
    for i in video_download_info.get('data').get('durl'):
        video_download_url.append(i.get('url'))
    n = 1
    title = info.get('title')
    page_title = info.get('pages_title').get(int(cid))
    page_num = int(info.get('pages_cid').index(int(cid)))+1
    for i in video_download_url:
        print(f'正在下载：{title}-{page_title}-{page_num}')
        dl = downloader(i,f'tmp/tmp_{n}.flv')
        dl.run()
    video_part_list = os.listdir('tmp')
    video_part_list_str = ''
    for i in video_part_list:
        video_part_list_str = video_part_list_str + "file '" + i +"'\n"
    open('tmp/filename.txt','w').write(video_part_list_str)
    print('转换中...')
    os.system('ffmpeg -f concat -i tmp/filename.txt -c copy tmp/output.aac -loglevel quiet')
    path = f'download/{like_list_title}'
    try:
        os.makedirs(f'download/{like_list_title}')
    except:
        pass
    os.system(f'ffmpeg -i tmp/output.aac {path}/output.mp3 -loglevel quiet')
    pic_data = requests.get(info.get('pic')).content
    artist = info.get('owner')
    desc = info.get('desc')
    media_info ={'picData': pic_data, 'title': title, 'artist': artist, 'desc': desc}
    try:
        if len(info.get('pages_cid')) != 1:
            os.rename(f'{path}/output.mp3',f'{path}/{title}-{page_title}-{page_num}.mp3')
            songPath = f'{path}/{title}-{page_title}-{page_num}.mp3'
        else:
            os.rename(f'{path}/output.mp3', f'{path}/{title}.mp3')
            songPath = f'{path}/{title}.mp3'
        SetMp3Info(songPath, media_info)
        print('写入ID3Tag...')
    except:
        os.remove(f'{path}/output.mp3')
    already_list = json.loads(open(f'download/{like_list_title_get}/info.json', 'r').read())
    already_list.get('info').append(bvid)
    for i in os.listdir('tmp'):
        os.remove(f'tmp/{i}')
    open(f'{path}/info.json','w').write(json.dumps(already_list))

like_list = get_video_list(media_id)
like_list_title_get = get_like_list_title(media_id)
try:
    os.makedirs('download')
    os.makedirs('tmp')
except:
    pass
try:
    for i in os.listdir('tmp'):
        os.remove(f'tmp/{i}')
except:
    pass
try:
    info = open(f'download/{like_list_title_get}/info.json','r').read()
    already_list_file = json.loads(info)
    for i in already_list_file.get('info'):
        try:
            like_list.remove(str(i))
        except:
            pass
except:
    try:
        os.makedirs(f'download/{like_list_title_get}')
    except:
        pass
    error = input('在获取下载记录时出现错误，是否创建新的下载记录？（Y/N）：').upper()
    if error == 'Y':
        init_json = json.dumps({'info': []})
        open(f'download/{like_list_title_get}/info.json','w').write(init_json)
        print('创建成功')
    elif error == 'N':
        raise
    else:
        print('wdnmd你选的什么鬼东西')
        sys.exit()
for bvid in like_list:
    info = get_video_info(bvid)
    for cid in info.get('pages_cid'):
        download_video(bvid,cid,like_list_title_get)
print('处理完成')
