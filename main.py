import os
import json
from datetime import datetime
import requests
import time
import hashlib

def load_config(config_file='config.json'):
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def sanitize_filename(title):
    # 移除文件名中的非法字符和控制字符
    invalid_chars = '<>:"/\\|?*\x00-\x1f'
    # 替换非法字符为下划线
    filename = ''
    for char in title:
        if char in invalid_chars or ord(char) < 32:
            filename += '_'
        else:
            filename += char
    # 去除首尾空格和点
    filename = filename.strip('. ')
    # 如果文件名为空，使用默认名称
    if not filename:
        filename = 'untitled'
    # 限制文件名长度，预留扩展名空间
    return filename[:80]

def extract_and_save_article(topic, output_dir='articles'):
    print("\n开始处理文章...")
    print(f"文章数据: {json.dumps(topic, ensure_ascii=False, indent=2)}")
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 提取文章信息
    topic_id = topic.get('topic_id', '')
    talk = topic.get('talk', {})
    if not talk:
        print(f"警告: 文章 {topic_id} 没有talk字段，将使用整个topic内容")
        title = topic.get('title', '').split('\n')[0]
        content = json.dumps(topic, ensure_ascii=False, indent=2)
    else:
        title = topic.get('title', '').split('\n')[0]
        content = '\n'.join(talk.get('text', '').split('\n')[1:])
    
    owner = talk.get('owner', {}) if talk else topic.get('owner', {})
    author = owner.get('name', 'Unknown')
    publish_time = topic.get('create_time', '')
    comments_count = topic.get('comments_count', 0)
    comments = topic.get('show_comments', [])
    
    print(f"提取的文章信息:")
    print(f"- 主题ID: {topic_id}")
    print(f"- 标题: {title}")
    print(f"- 作者: {author}")
    print(f"- 发布时间: {publish_time}")
    print(f"- 评论数: {comments_count}")
    
    # 创建文件名
    safe_title = sanitize_filename(title)
    # 从create_time中提取日期并格式化为yyyymmdd
    # 处理ISO 8601格式的时间字符串
    publish_date = datetime.fromisoformat(publish_time.replace('Z', '+00:00')).strftime('%Y%m%d')
    filename = f"{publish_date}_{safe_title}_{topic_id}.txt"
    file_path = os.path.join(output_dir, filename)
    print(f"将保存到文件: {file_path}")
    
    # 组织文章信息
    article_text = f"主题ID：{topic_id}\n"
    article_text += f"标题：{title}\n"
    article_text += f"发布时间：{publish_time}\n"
    article_text += f"作者：{author}\n"
    article_text += f"评论数：{comments_count}\n"
    article_text += f"\n正文内容：\n{content}\n"
    
    # 添加评论信息
    if comments:
        article_text += "\n评论列表：\n"
        for i, comment in enumerate(comments, 1):
            article_text += f"\n评论 {i}:\n"
            article_text += f"评论者：{comment.get('owner', {}).get('name', 'Unknown')}\n"
            article_text += f"评论时间：{comment.get('create_time', '')}\n"
            article_text += f"评论内容：{comment.get('text', '')}\n"
    
    # 保存到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(article_text)
    
    print(f"文章已成功保存到: {file_path}")
    return file_path

def process_articles(resp_data):
    """处理resp_data.topics中的文章列表并保存为单独的txt文件"""
    print("\n开始处理文章列表...")
    try:
        print(f"响应数据结构: {json.dumps(list(resp_data.keys()), ensure_ascii=False)}")
    except (AttributeError, TypeError) as e:
        print(f"错误: 无法获取响应数据结构: {e}")
        return
    
    if not isinstance(resp_data, dict):
        print(f"错误: resp_data不是字典类型，实际类型为: {type(resp_data)}")
        return
    
    # 从resp_data['resp_data']中获取topics数组
    topics = resp_data.get('resp_data', {}).get('topics', [])
    if not topics:
        print("错误: 在resp_data.resp_data.topics中未找到文章")
        print(f"完整响应数据: {json.dumps(resp_data, ensure_ascii=False, indent=2)}")
        return
    
    print(f"找到 {len(topics)} 篇文章待处理")
    failed_articles = []
    for i, topic in enumerate(topics, 1):
        print(f"\n处理第 {i}/{len(topics)} 篇文章")
        try:
            file_path = extract_and_save_article(topic)
            if file_path:
                print(f"已成功保存文章：{file_path}")
            else:
                article_id = topic.get('topic_id', 'unknown')
                failed_articles.append({'id': article_id, 'reason': '保存失败'})
                print("文章处理失败，跳过")
        except Exception as e:
            article_id = topic.get('topic_id', 'unknown')
            failed_articles.append({'id': article_id, 'reason': str(e)})
            print(f"处理文章时发生错误：{e}")
    
    if failed_articles:
        print("\n发现以下文章保存失败:")
        with open('failed_articles.txt', 'w', encoding='utf-8') as f:
            for article in failed_articles:
                f.write(f"文章ID: {article['id']}, 失败原因: {article['reason']}\n")
                print(f"文章ID: {article['id']}, 失败原因: {article['reason']}")

def process_url(url, headers):
    """处理单个URL的请求"""
    print(f"\n处理URL: {url}")
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        print(f"API响应状态码: {response.status_code}")
        resp_data = response.json()
        
        # 处理文章数据
        process_articles(resp_data)
        return True
    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
    except json.JSONDecodeError as e:
        print(f"JSON解析失败：{e}")
        print(f"响应内容：{response.text}")
    except Exception as e:
        print(f"处理URL时发生错误：{e}")
    return False

# 示例使用
if __name__ == '__main__':
    # 加载配置文件
    print("开始加载配置文件...")
    config = load_config()
    print("配置文件加载成功")
    
    # 设置请求头
    headers = config['headers'].copy()
    headers['Cookie'] = f"zsxq_access_token={config['auth']['zsxq_access_token']}; zsxqsessionid={config['auth']['zsxqsessionid']}"
    headers['Referer'] = config['headers'].get('Referer', 'https://wx.zsxq.com/')
    headers['Referrer-Policy'] = config['headers'].get('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    # 读取URL列表文件
    print("\n开始读取URL列表...")
    try:
        with open('list.txt', 'r', encoding='utf-8') as f:
            urls = f.read().splitlines()
        
        print(f"共读取到 {len(urls)} 个URL")
        
        # 处理每个URL
        for i, url in enumerate(urls, 1):
            # 更新时间戳和签名
            timestamp = str(int(time.time()))
            headers['x-timestamp'] = timestamp
            signature = hashlib.sha1(timestamp.encode('utf-8')).hexdigest()
            headers['x-signature'] = signature
            
            # 处理URL
            success = process_url(url.strip(), headers)
            
            # 每处理10个URL后暂停30秒
            if i % 10 == 0 and i < len(urls):
                print(f"\n已处理{i}个URL，暂停30秒...")
                time.sleep(30)
                print("继续处理...")
        
        print("\n所有URL处理完成")
    except FileNotFoundError:
        print("错误：找不到list.txt文件")
    except Exception as e:
        print(f"处理URL列表时发生错误：{e}")

    
    print(f"\n请求URL: {url}")
    
    # 设置请求头
    headers = config['headers'].copy()  # 创建headers的副本以避免修改原始配置
    headers['Cookie'] = f"zsxq_access_token={config['auth']['zsxq_access_token']}; zsxqsessionid={config['auth']['zsxqsessionid']}"
    # 设置referrer和referrerPolicy
    headers['Referer'] = config['headers'].get('Referer', 'https://wx.zsxq.com/')
    headers['Referrer-Policy'] = config['headers'].get('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    # 更新时间戳和签名
    timestamp = str(int(time.time()))
    headers['x-timestamp'] = timestamp
    
    # 生成签名
    string_to_sign = timestamp
    signature = hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()
    headers['x-signature'] = signature
    
    print("\n发送API请求...")
    try:
        # 发送GET请求
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'  # 设置响应编码
        response.raise_for_status()  # 检查响应状态
        
        print(f"API响应状态码: {response.status_code}")
        resp_data = response.json()
        print("\nAPI响应数据：")
        print(json.dumps(resp_data, ensure_ascii=False, indent=2))
        
        # 处理文章数据
        process_articles(resp_data)
        print("\n所有文章处理完成")
    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
    except json.JSONDecodeError as e:
        print(f"JSON解析失败：{e}")
        print(f"响应内容：{response.text}")
    except UnicodeEncodeError as e:
        print(f"编码错误：{e}，请检查Cookie等请求头信息是否包含非法字符")
    except Exception as e:
        print(f"发生未预期的错误：{e}")