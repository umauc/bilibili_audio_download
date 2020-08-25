#!/usr/bin/python3

import requests
import math
import os
import json
import threading

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
    pages_cid = []
    pages_title = {}
    for i in video_info.get('data').get('pages'):
        pages_cid.append(i.get('cid'))
        if i.get('part') != '':
            pages_title[i.get('cid')] = i.get('part').replace('/', '¦')
        else:
            pages_title[i.get('cid')] = title.replace('/', '¦')
    return {'title':title,'pic':pic,'pages_cid':pages_cid,'pages_title':pages_title}

def download_video(bvid,cid,like_list_title):
    cid = str(cid)
    info = get_video_info(bvid)
    print('获取视频数据')
    video_download_info = requests.get(f'http://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}').json()
    video_download_url = []
    for i in video_download_info.get('data').get('durl'):
        video_download_url.append(i.get('url'))
    n = 1
    title = info.get('title').replace('/', '¦')
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
    os.system('ffmpeg.exe -f concat -i tmp/filename.txt -c copy tmp/output.aac -loglevel quiet')
    path = f'download/{like_list_title}'
    try:
        os.makedirs(f'download/{like_list_title}')
    except:
        pass
    os.system(f'ffmpeg.exe -i tmp/output.aac {path}/output.mp3 -loglevel quiet')
    try:
        if page_title != title:
            os.rename(f'{path}/output.mp3',f'{path}/{title}-{page_title}-{page_num}.mp3')
        else:
            os.rename(f'{path}/output.mp3', f'{path}/{title}.mp3')
    except:
        os.remove('download/output.mp3')
    already_list = json.loads(open(f'download/{like_list_title_get}/info.json', 'r').read())
    already_list.get('info').append(bvid)
    open(f'{path}/info.json','w').write(json.dumps(already_list))
    for i in os.listdir('tmp'):
        os.remove(f'tmp/{i}')

like_list = get_video_list(media_id)
like_list_title_get = get_like_list_title(media_id)
try:
    os.makedirs('download')
    os.makedirs('tmp')
except:
    pass
try:
    info = open(f'download/{like_list_title_get}/info.json','r').read()
    already_list_file = json.loads(info)
    for i in already_list_file.get('info'):
        like_list.remove(i)
except:
    try:
        os.makedirs(f'download/{like_list_title_get}')
    except:
        pass
    init_json = json.dumps({'info': []})
    open(f'download/{like_list_title_get}/info.json','w').write(init_json)
for bvid in like_list:
    info = get_video_info(bvid)
    for cid in info.get('pages_cid'):
        download_video(bvid,cid,like_list_title_get)
print('处理完成')