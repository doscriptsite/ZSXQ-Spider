import re
import requests
import json
import os
import pdfkit
import datetime
import base64
import time
import traceback
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import quote
from urllib.parse import unquote
from urllib.error import ContentTooShortError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body>
<h1>{title}</h1>
<br>{author} - {cretime}<br>
<p>{text}</p>
</body>
</html>
"""


class Spider:
    ZSXQ_ACCESS_TOKEN = ''          # 登录后Cookie中的Token（必须修改）
    USER_AGENT = ''                 # 登录时使用的User-Agent（必须修改）
    GROUP_ID = ''                   # 知识星球中的小组ID
    PDF_FILE_NAME = 'output'        # 生成的PDF文件名，不带后缀
    PDF_MAX_PAGE_NUM = 500          # 单个PDF文件最大的页面数。windows下超过一定数量的页面会生成失败，所以需要调整此值
    DOWNLOAD_PICS = True            # 是否下载图片 True | False ;下载会导致程序变慢
    DOWNLOAD_COMMENTS = True        # 是否下载评论
    ONLY_DIGESTS = False            # True-只精华 | False-全部
    FROM_DATE_TO_DATE = False       # 按时间区间下载
    EARLY_DATE = ''                 # 最早时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
    LATE_DATE = ''                  # 最晚时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
    COUNTS_PER = 30                 # 每次请求加载几个主题 最大可设置为30
    DEBUG = False                   # DEBUG开关
    DEBUG_NUM = 120                 # DEBUG时 跑多少条数据后停止 需与COUNTS_PER结合考虑
    SLEEP_FLAG = True               # 请求之间是否SLEEP避免请求过于频繁
    SLEEP_SEC = 5                   # SLEEP秒数 SLEEP_FLAG=True时生效

    OVER_DATE_BREAK = False
    htmls_file = []
    num = 1
    output_dir = ''
    html_output_dir = ''
    image_output_dir = ''
    data_output_dir = ''
    start_url = ''
    headers = {}
    pdf_options = None

    def __init__(self, access_token=None, user_agent=None, group_id=None):
        self.ZSXQ_ACCESS_TOKEN = access_token or self.ZSXQ_ACCESS_TOKEN
        self.USER_AGENT = user_agent or self.USER_AGENT
        self.GROUP_ID = group_id or self.GROUP_ID
        self.headers = {
            'Cookie': 'abtest_env=product;zsxq_access_token=' + self.ZSXQ_ACCESS_TOKEN,
            'User-Agent': self.USER_AGENT,
            'accept': 'application/json, text/plain, */*',
            'sec-ch-ua-platform': '"Windows"',
            'origin': 'https://wx.zsxq.com',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="98", "Google Chrome";v="98"',
            'referer': 'https://wx.zsxq.com/',
            'dnt': '1',
        }
        self.pdf_options = {
            "page-size": "A4",
            "margin-top": "0.35in",
            "margin-right": "0.65in",
            "margin-bottom": "0.35in",
            "margin-left": "0.65in",
            "encoding": "UTF-8",
            "custom-header": [("Accept-Encoding", "gzip")],
            "cookie": [],
            "outline-depth": 10,
        }

    def get_url_data(self, url):
        rsp = requests.get(url, headers=self.headers)
        rsp_data = rsp.json()

        if not rsp_data.get('succeeded'):
            if rsp_data.get('code') == 1059:
                if self.SLEEP_FLAG:
                    time.sleep(self.SLEEP_SEC)
                return self.get_url_data(url)
            raise Exception('访问错误：\n' + json.dumps(rsp_data, indent=2, ensure_ascii=False))
        else:
            return rsp_data.get('resp_data')

    def get_data(self, url):
        rsp_data = self.get_url_data(url)
        self.save_data_json(self.COUNTS_PER, self.num, rsp_data)
        topics = rsp_data.get('topics')
        for topic in topics:
            if self.FROM_DATE_TO_DATE and self.EARLY_DATE.strip():
                if topic.get('create_time') < self.EARLY_DATE.strip():
                    self.OVER_DATE_BREAK = True
                    break

            content = topic.get('question', topic.get('talk', topic.get('task', topic.get('solution'))))

            anonymous = content.get('anonymous')
            if anonymous:
                author = '匿名用户'
            else:
                author = content.get('owner').get('name')

            cretime = (topic.get('create_time')[:23]).replace('T', ' ')

            text = content.get('text', '')
            # 排除不需要的文章
            # if text.strip().startswith(u'') or text.find(u'') != -1:
            #     continue
            text = self.handle_link(text)
            title = str(self.num) + '_' + cretime[:16]
            if topic.get('digested') == True:
                title += ' {精华}'

            if self.DOWNLOAD_PICS and content.get('images'):
                soup = BeautifulSoup(HTML_TEMPLATE, 'html.parser')
                images_index = 0
                _images = content.get('images')
                print(f'Crawling images: {len(_images)}')
                for img in _images:
                    url = img.get('large').get('url')
                    local_url = os.path.join(self.image_output_dir, f'{self.num}_{images_index}.jpg')
                    images_index += 1
                    self.download_image(url, local_url)
                    # img_tag = soup.new_tag('img', src=local_url)
                    # 直接写入路径可能无法正常将图片写入PDF，此处写入转码后的图片数据
                    img_tag = soup.new_tag('img', src=self.encode_image(local_url))
                    soup.body.append(img_tag)
                html_img = str(soup)
                html = html_img.format(title=title, text=text, author=author, cretime=cretime)
            else:
                html = HTML_TEMPLATE.format(title=title, text=text, author=author, cretime=cretime)

            if topic.get('question'):
                answer_author = topic.get('answer').get('owner').get('name', '')
                answer = topic.get('answer').get('text', "")
                answer = self.handle_link(answer)

                soup = BeautifulSoup(html, 'html.parser')
                answer_tag = soup.new_tag('p')

                answer = '【' + answer_author + '】 回答：<br>' + answer
                soup_temp = BeautifulSoup(answer, 'html.parser')
                answer_tag.append(soup_temp)

                soup.body.append(answer_tag)
                html = str(soup)

            files = content.get('files')
            if files:
                files_content = '<i>文件列表(需访问网站下载) :<br>'
                for f in files:
                    files_content += f.get('name') + '<br>'
                files_content += '</i>'
                soup = BeautifulSoup(html, 'html.parser')
                files_tag = soup.new_tag('p')
                soup_temp = BeautifulSoup(files_content, 'html.parser')
                files_tag.append(soup_temp)
                soup.body.append(files_tag)
                html = str(soup)

            comments = topic.get('show_comments')
            if self.DOWNLOAD_COMMENTS and comments:
                soup = BeautifulSoup(html, 'html.parser')
                hr_tag = soup.new_tag('hr')
                soup.body.append(hr_tag)
                for comment in comments:
                    if comment.get('repliee'):
                        comment_str = '[' + comment.get('owner').get('name') + ' 回复 ' + comment.get('repliee').get('name') + '] : ' + self.handle_link(comment.get('text'))
                    else:
                        comment_str = '[' + comment.get('owner').get('name') + '] : ' + self.handle_link(comment.get('text'))

                    comment_tag = soup.new_tag('p')
                    soup_temp = BeautifulSoup(comment_str, 'html.parser')
                    comment_tag.append(soup_temp)
                    soup.body.append(comment_tag)
                html = str(soup)

            file_name = self.save_html(self.num, html)
            self.num += 1
            self.htmls_file.append(file_name)

        # DEBUG 仅导出部分数据时使用
        if self.DEBUG and self.num >= self.DEBUG_NUM:
            return self.htmls_file

        if self.OVER_DATE_BREAK:
            return self.htmls_file

        if topics:
            create_time = topics[-1].get('create_time')
            if create_time[20:23] == "000":
                end_time = create_time[:20] + "999" + create_time[23:]
                str_date_time = end_time[:19]
                delta = datetime.timedelta(seconds=1)
                date_time = datetime.datetime.strptime(str_date_time, '%Y-%m-%dT%H:%M:%S')
                date_time = date_time - delta
                str_date_time = date_time.strftime('%Y-%m-%dT%H:%M:%S')
                end_time = str_date_time + end_time[19:]
            else:
                res = int(create_time[20:23]) - 1
                end_time = create_time[:20] + str(res).zfill(3) + create_time[23:]  # zfill 函数补足结果前面的零，始终为3位数
            end_time = quote(end_time)
            if len(end_time) == 33:
                end_time = end_time[:24] + '0' + end_time[24:]
            next_url = self.start_url + '&end_time=' + end_time
            if self.SLEEP_FLAG:
                time.sleep(self.SLEEP_SEC)
            print(f'Next url: {next_url}')
            self.get_data(next_url)

        return self.htmls_file

    def encode_image(self, image_url):
        with open(image_url, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        return 'data:image/png;base64,' + encoded_string.decode('utf-8')

    def download_image(self, url, local_url):
        try:
            urllib.request.urlretrieve(url, local_url)
        except ContentTooShortError:
            print('Network not good. Reloading ' + url)
            self.download_image(url, local_url)

    def handle_link(self, text):
        soup = BeautifulSoup(text, "html.parser")

        mention = soup.find_all('e', attrs={'type': 'mention'})
        if len(mention):
            for m in mention:
                mention_name = m.attrs['title']
                new_tag = soup.new_tag('span')
                new_tag.string = mention_name
                m.replace_with(new_tag)

        hashtag = soup.find_all('e', attrs={'type': 'hashtag'})
        if len(hashtag):
            for tag in hashtag:
                tag_name = unquote(tag.attrs['title'])
                new_tag = soup.new_tag('span')
                new_tag.string = tag_name
                tag.replace_with(new_tag)

        links = soup.find_all('e', attrs={'type': 'web'})
        if len(links):
            for link in links:
                title = unquote(link.attrs['title'])
                href = unquote(link.attrs['href'])
                new_a_tag = soup.new_tag('a', href=href)
                new_a_tag.string = title
                link.replace_with(new_a_tag)

        text = str(soup)
        text = re.sub(r'<e[^>]*>', '', text).strip()
        text = text.replace('\n', '<br>')
        return text

    def _make_pdf(self, html_files):
        if len(html_files) > self.PDF_MAX_PAGE_NUM:
            _html_files = html_files
            html_files = [_html_files[i:i + self.PDF_MAX_PAGE_NUM] for i in range(0, len(_html_files), self.PDF_MAX_PAGE_NUM)]
        else:
            html_files = [html_files]
        self.pdf_options['user-style-sheet'] = str(self.get_dir_path('temp.css'))
        try:
            for i, files in enumerate(html_files, start=1):
                pdfkit.from_file(files, os.path.join(self.output_dir, f'{self.PDF_FILE_NAME}_{i}.pdf'), options=self.pdf_options, verbose=True)
            print("电子书生成成功！")
        except Exception as e:
            print("电子书生成失败：\n" + traceback.format_exc())

    def generate_pdf(self, html_files):
        self._make_pdf(html_files)

    def regenerate_pdf(self, dir_name):
        self.output_dir = self.get_dir_path(dir_name)
        html_dir = os.path.join(self.output_dir, 'html')
        html_files = os.listdir(html_dir)
        html_files.sort(key=lambda x: int(x[:-5]))
        html_files = [os.path.join(html_dir, i) for i in html_files if i.endswith('.html')]
        self._make_pdf(html_files)

    def generate_merge_pdf(self, dir_name):
        # 多个html合并成一个html后，再生成PDF，生成时间会比较长，会分页混乱
        output_dir = self.get_dir_path(dir_name)
        html_dir = os.path.join(output_dir, 'html')
        html_files = os.listdir(html_dir)
        html_files.sort(key=lambda x: int(x[:-5]))
        html_files = [os.path.join(html_dir, i) for i in html_files if i.endswith('.html')]
        single_html = os.path.join(output_dir, 'single.html')
        with open(single_html, 'w+', encoding='utf-8') as f:
            for i in html_files:
                with open(i, 'r+', encoding='utf-8') as fr:
                    f.write(fr.read() + '\n\n')
        try:
            pdfkit.from_file(single_html, os.path.join(output_dir, self.PDF_FILE_NAME + '.pdf'), options=self.pdf_options, css=self.get_dir_path('temp.css'), verbose=True)
            print("电子书生成成功！")
        except Exception as e:
            print("电子书生成失败：\n" + traceback.format_exc())

    def save_html(self, num, data):
        file_name = os.path.join(self.html_output_dir, f'{num}.html')
        with open(file_name, 'w+', encoding='utf-8') as f:
            f.write(data)
        return file_name

    def save_data_json(self, counts_per, num, data, url=None):
        url = f'# {url}\n\n' if url else ''
        with open(os.path.join(self.data_output_dir, f'{num}_{counts_per}.json'), 'w+', encoding='utf-8') as f:
            f.write(url + json.dumps(data, indent=2, ensure_ascii=False))

    def get_dir_path(self, *paths):
        return os.path.join(BASE_DIR, *paths)

    def mkdir(self):
        self.output_dir = self.get_dir_path(time.strftime("%Y-%m-%d.%H%M%S", time.localtime()))
        self.html_output_dir = os.path.join(self.output_dir, 'html')
        self.image_output_dir = os.path.join(self.output_dir, 'image')
        self.data_output_dir = os.path.join(self.output_dir, 'data')
        os.mkdir(self.output_dir)
        os.mkdir(self.html_output_dir)
        os.mkdir(self.image_output_dir)
        os.mkdir(self.data_output_dir)

    def run(self):
        self.htmls_file = []
        self.num = 1
        self.mkdir()
        if self.ONLY_DIGESTS:
            self.start_url = 'https://api.zsxq.com/v2/groups/' + self.GROUP_ID + '/topics?scope=digests&count=' + str(self.COUNTS_PER)
        else:
            self.start_url = 'https://api.zsxq.com/v2/groups/' + self.GROUP_ID + '/topics?scope=all&count=' + str(self.COUNTS_PER)

        url = self.start_url
        if self.FROM_DATE_TO_DATE and self.LATE_DATE.strip():
            url = self.start_url + '&end_time=' + quote(self.LATE_DATE.strip())
        print(f'Start Url: {url}')
        self.get_data(url)
        print(f'Generating PDF...')
        self.generate_pdf(self.htmls_file)


if __name__ == '__main__':
    _ = Spider('登录后Cookie中的Token', '登录时使用的User-Agent', '知识星球中的小组ID')
    _.run()
    # _.regenerate_pdf('2022-02-01.000000')
