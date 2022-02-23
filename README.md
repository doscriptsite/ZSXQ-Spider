# ZSXQ-Spider
 爬取知识星球内容，并制作成PDF电子书。

代码修改自：[zsxq-spider](https://github.com/wbsabc/zsxq-spider)

爬取知识星球，并制作 PDF 电子书。[https://www.zsxq.com/](https://www.zsxq.com/)

## 功能

* 支持下载图片并写入 PDF。
* 支持 PDF 中显示链接。
* 支持下载评论。
* 可控制只下载精华内容或下载全部内容。
* 支持按时间区间下载。
* ![New](https://via.placeholder.com/10/f03c15/000000?text=+) 使用最新接口(v2)。
* ![New](https://via.placeholder.com/10/f03c15/000000?text=+) 每次运行结果保存为单独文件夹。
* ![New](https://via.placeholder.com/10/f03c15/000000?text=+) 支持分片输出PDF。

## 环境

* Python 3.8 测试通过。
* 安装 [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) ，安装后将 bin 目录加入到环境变量。
* 安装相应依赖：pip install pdfkit
* 安装 BeautifulSoup：pip install BeautifulSoup4
* 安装 Requests：pip install requests
* ![New](https://via.placeholder.com/10/f03c15/000000?text=+) 或者使用poetry install


## 用法

参考以下配置内容
```python
ZSXQ_ACCESS_TOKEN = '00000000-0000-0000-0000-D09322903A59_6DF24A4ED3558CD4'    # 登录后Cookie中的Token（必须修改）
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'    # 登录时使用的User-Agent（必须修改）
GROUP_ID = '123456789123'                         # 知识星球中的小组ID
PDF_FILE_NAME = 'outfile'                         # 生成的PDF文件名，不带后缀
PDF_MAX_PAGE_NUM = 500                            # 单个PDF文件最大的页面数。windows下超过一定数量的页面会生成失败，所以需要调整此值
DOWNLOAD_PICS = True                              # 是否下载图片 True | False 下载会导致程序变慢
DOWNLOAD_COMMENTS = True                          # 是否下载评论
ONLY_DIGESTS = False                              # True-只精华 | False-全部
FROM_DATE_TO_DATE = False                         # 按时间区间下载
EARLY_DATE = '2017-05-25T00:00:00.000+0800'       # 最早时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
LATE_DATE = '2018-05-25T00:00:00.000+0800'        # 最晚时间 当FROM_DATE_TO_DATE=True时生效 为空表示不限制 形如'2017-05-25T00:00:00.000+0800'
COUNTS_PER_TIME = 30                              # 每次请求加载几个主题 最大可设置为30
DEBUG = False                                     # DEBUG开关
DEBUG_NUM = 120                                   # DEBUG时 跑多少条数据后停止 需与COUNTS_PER_TIME结合考虑
SLEEP_FLAG = True                                 # 请求之间是否SLEEP避免请求过于频繁
SLEEP_SEC = 5                                     # SLEEP秒数 SLEEP_FLAG=True时生效
```

修改main.py文件中的相应参数
`Spider('登录后Cookie中的Token', '登录时使用的User-Agent', '知识星球中的小组ID')`
然后运行main.py。

## 说明

1. 请大家合理使用本代码，不要随意传播生成的PDF，保护网站及作者的合法权益。
2. 爬虫会对网站性能造成一定影响，请勿频繁使用，在必要时合理使用，大家都是去学习知识的，体谅一下吴老板。
