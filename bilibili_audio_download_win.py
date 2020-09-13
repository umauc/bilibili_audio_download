#!/usr/bin/python3

import requests
import math
import os
import json
import threading
import sys
from mutagen.id3 import ID3, APIC, TIT2, TPE1, COMM
from tenacity import retry, stop_after_attempt
from concurrent.futures import ThreadPoolExecutor, wait
from threading import Lock
from requests import get, head
lock = Lock()

media_id = input('media_id:')

ng_str = r'\/:*?"<>|' #win特供文件命名规则
translate_str = r"¦¦：x？'《》¦" #不满意重命名的用户改这里
trantab = str.maketrans(ng_str,translate_str)

#这个多线程下载是抄的，我自己不会多线程（
#链接：https://www.jianshu.com/p/5c71ad87a52c
class downloader():
    def __init__(self, url, nums, file):
        self.url = url
        self.num = nums
        self.name = file
        r = head(self.url,headers={'user-agent': 'my-app/0.0.1', 'referer': 'https://www.bilibili.com'})
        # 若资源显示302,则迭代找寻源文件
        while r.status_code == 302:
            self.url = r.headers['Location']
            print("该url已重定向至{}".format(self.url))
            r = head(self.url)
        self.size = int(r.headers['Content-Length'])
        print('该文件大小为：{} bytes'.format(self.size))

    def down(self, start, end):
        headers = {'Range': 'bytes={}-{}'.format(start, end),'user-agent': 'my-app/0.0.1', 'referer': 'https://www.bilibili.com'}
        # stream = True 下载的数据不会保存在内存中
        r = get(self.url, headers=headers, stream=True)
        # 写入文件对应位置,加入文件锁
        lock.acquire()
        with open(self.name, "rb+") as fp:
            fp.seek(start)
            fp.write(r.content)
            lock.release()
            # 释放锁

    def run(self):
        # 创建一个和要下载文件一样大小的文件
        fp = open(self.name, "wb")
        fp.truncate(self.size)
        fp.close()
        # 启动多线程写文件
        part = self.size // self.num
        pool = ThreadPoolExecutor(max_workers=self.num)
        futures = []
        for i in range(self.num):
            start = part * i
            # 最后一块
            if i == self.num - 1:
                end = self.size -1
            else:
                end = start + part - 1
            futures.append(pool.submit(self.down, start, end))
        wait(futures)
        print('%s 下载完成' % self.name)

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
            pages_title[i.get('cid')] = i.get('part').translate(trantab)
        else:
            pages_title[i.get('cid')] = title.translate(trantab)
    return {'title':title,'pic':pic,'pages_cid':pages_cid,'pages_title':pages_title,'owner':owner,'desc':desc}


@retry(stop=stop_after_attempt(1))
def download_video(bvid,cid,like_list_title,mthead):
    cid = str(cid)
    info = get_video_info(bvid)
    print(f'获取视频数据({bvid})')
    video_download_info = requests.get(f'http://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}').json()
    video_download_url = []
    for i in video_download_info.get('data').get('durl'):
        video_download_url.append(i.get('url'))
    n = 1
    title = info.get('title').translate(trantab)
    page_title = info.get('pages_title').get(int(cid))
    page_num = int(info.get('pages_cid').index(int(cid)))+1
    for i in video_download_url:
        print(f'正在下载：{title}-{page_title}-{page_num}')
        if mthead == True:
            os.system(f'aria2c.exe "{i}" -d "tmp" -s16 -x16 -k1M -j16 -o "tmp_{n}.flv" --referer "https://www.bilibili.com" -U "my-app/0.0.1" --file-allocation=none')
            n = n + 1
        else:
            video = requests.get(i,headers={'user-agent': 'my-app/0.0.1', 'referer': 'https://www.bilibili.com'}).content
            video_file = open(f'tmp/tmp_{n}.flv','wb')
            video_file.write(video)
            video_file.close()
            n = n + 1
    video_part_list = os.listdir('tmp')
    video_part_list_str = ''
    for i in video_part_list:
        video_part_list_str = video_part_list_str + "file '" + i +"'\n"
    open('tmp/filename.txt','w').write(video_part_list_str)
    print('转换中...')
    os.system('ffmpeg.exe -f concat -i tmp/filename.txt -c copy tmp/output.aac')
    path = f'download/{like_list_title}'
    try:
        os.makedirs(f'download/{like_list_title}')
    except:
        pass
    os.system(f'ffmpeg.exe -i tmp/output.aac {path}/output.mp3')
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
thead = input('多线程（实验性）？(Y/N)：').upper()
if thead == 'Y':
    mthead = True
elif thead == 'N':
    mthead = False
else:
    print('wdnmd你选的什么鬼东西')
    sys.exit()
for bvid in like_list:
    info = get_video_info(bvid)
    for cid in info.get('pages_cid'):
        download_video(bvid,cid,like_list_title_get,mthead)
print('处理完成')
