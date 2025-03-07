# 知识星球文章下载工具

## 项目介绍
这是一个用于下载知识星球文章的Python工具，支持批量下载文章内容、获取文章列表、下载单篇指定文章等功能。项目使用Python实现，通过调用知识星球的API接口获取文章内容并保存为本地文件。

## 环境要求
- Python 3.x
- 依赖包：requests

## 配置说明
1. 复制`config_example.json`为`config.json`
2. 在`config.json`中配置以下信息：
```json
{
  "api": {
    "baseUrl": "https://api.zsxq.com/v2",
    "groupId": "YOUR_GROUP_ID",    // 星球ID
    "topicsPath": "/topics",
    "defaultParams": {
      "scope": "all",
      "count": 20
    }
  },
  "auth": {
    "zsxq_access_token": "YOUR_ACCESS_TOKEN",  // 登录后的access_token
    "zsxqsessionid": "YOUR_SESSION_ID"        // 登录后的sessionid
  },
  "headers": {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "priority": "u=1, i"
  }
}
```

### 获取配置信息
1. 登录知识星球网页版
2. 打开浏览器开发者工具(F12)
3. 在Network标签页中找到任意API请求
4. 从Cookie中获取zsxq_access_token和zsxqsessionid
5. 从URL中获取groupId(形如48844242882218)

## 主要脚本说明

### 1. main.py
主要用于批量下载文章内容。

**功能：**
- 从配置文件加载认证信息
- 处理文章列表中的每个URL
- 下载文章内容并保存为txt文件
- 支持断点续传和错误重试

**使用方法：**
1. 确保config.json配置正确
2. 准备list.txt文件，包含要下载的文章URL列表
3. 运行脚本：
```bash
python main.py
```

### 2. get_article_list.py
用于获取文章列表信息。

**功能：**
- 读取articles_list.txt中的URL列表
- 提取每篇文章的topic_id和标题
- 生成all_list.txt文件，包含文章ID和标题对应关系
- 支持失败重试和日志记录

**使用方法：**
1. 准备articles_list.txt文件，每行一个文章列表页URL
2. 运行脚本：
```bash
python get_article_list.py
```

### 3. single_article.py
用于下载单篇或指定的文章，或批量下載 `all_list.txt` 裡面的文章。

可以通過 `get_article_list.py` 生成`all_list.txt`。

**功能：**
- 支持单篇文章的下载
- 支持失败文章的重试（最多3次）
- 记录下载失败的文章信息
- 支持文件完整性检查

**使用方法：**
1. 确保all_list.txt文件存在（包含文章ID和标题），可以通過 `get_article_list.py` 生成
2. 运行脚本：
```bash
python single_article.py
```

## 生成文件说明

### 1. 配置文件
- `config.json`: 主配置文件，包含API认证信息和请求头设置
- `config_example.json`: 配置文件示例模板

### 2. 输入文件
- `articles_list.txt`: 待获取的文章列表页URL， `get_article_list.py` 調用這個文件生成
- `list.txt`: 待下载的具体文章URL列表

### 3. 中间文件
- `all_list.txt`: 包含文章ID和标题的对应关系列表
- `missing_articles.txt`: 记录未能成功下载的文章列表

### 4. 输出文件
- `articles/`: 下载的文章内容保存目录
  - 文件命名格式：`{发布日期}_{标题}_{文章ID}.txt`
  - 文件内容包含：标题、作者、发布时间、正文、评论等

### 5. 日志文件
- `logs/failures_{timestamp}.json`: 获取文章列表时的失败记录
- `failed_down.txt`: 最终下载失败的文章详细信息
- `download_failed_ids.txt`: 下载过程中失败的文章ID列表
- `save_failed_ids.txt`: 保存文件时失败的文章ID列表

## 使用流程
1. 配置config.json文件
2. 准备articles_list.txt（文章列表页URL）
3. 运行get_article_list.py获取文章列表
4. 使用main.py批量下载或single_article.py下载指定文章
5. 查看articles目录获取下载的文章内容

## 注意事项
- 请勿频繁调用API，建议设置适当的请求间隔
- 确保网络连接稳定
- 定期更新token和sessionid
- 遵守知识星球的使用条款
- 下载失败时查看相应的日志文件，了解失败原因
- 建议定期备份已下载的文章内容