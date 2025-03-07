import os
import json
from datetime import datetime
import requests
import time
import hashlib
import re
from main import load_config, extract_and_save_article

def get_single_article(topic_id, download_failed_ids=None, save_failed_ids=None):
    """获取单篇文章的信息
    Args:
        topic_id: 文章ID
        download_failed_ids: 下载失败的ID列表，每个元素为字典，包含id和reason
        save_failed_ids: 保存失败的ID列表，每个元素为字典，包含id和reason
    Returns:
        bool: 是否成功处理文章
    """
    # 初始化失败列表
    if download_failed_ids is None:
        download_failed_ids = []
    if save_failed_ids is None:
        save_failed_ids = []
    # 加载配置文件
    print("开始加载配置文件...")
    config = load_config()
    print("配置文件加载成功")
    
    # 构建API URL
    url = f"https://api.zsxq.com/v2/topics/{topic_id}/info"
    print(f"\n请求URL: {url}")
    
    # 设置请求头
    headers = config['headers'].copy()
    headers['Cookie'] = f"zsxq_access_token={config['auth']['zsxq_access_token']}; zsxqsessionid={config['auth']['zsxqsessionid']}"
    headers['Referer'] = config['headers'].get('Referer', 'https://wx.zsxq.com/')
    headers['Referrer-Policy'] = config['headers'].get('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    # 更新时间戳和签名
    timestamp = str(int(time.time() * 1000))
    headers['x-timestamp'] = timestamp
    
    # 生成签名
    string_to_sign = f"{config['auth']['zsxq_access_token']}_{timestamp}"
    signature = hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()
    headers['x-signature'] = signature
    
    print("\n发送API请求...")
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # 发送GET请求
            response = requests.get(url, headers=headers, verify=False)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            print(f"API响应状态码: {response.status_code}")
            resp_data = response.json()
            # print("\nAPI响应数据：")
            # print(json.dumps(resp_data, ensure_ascii=False, indent=2))
            
            # 处理文章数据
            topic = resp_data.get('resp_data', {}).get('topic', {})
            if not topic:
                error_msg = "API响应中未找到文章数据"
                print(f"错误: {error_msg}")
                download_failed_ids.append({"id": topic_id, "reason": error_msg})
                return False
            
            # 使用现有的extract_and_save_article函数处理文章
            file_path = extract_and_save_article(topic)
            if file_path:
                print(f"已成功保存文章：{file_path}")
                return True
            else:
                error_msg = "文章内容提取或保存失败"
                print(error_msg)
                save_failed_ids.append({"id": topic_id, "reason": error_msg})
                return False
                
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {str(e)}"
            print(error_msg)
            retry_count += 1
            if retry_count < max_retries:
                print(f"第{retry_count}次重试...")
                time.sleep(2)
                continue
            download_failed_ids.append({"id": topic_id, "reason": error_msg})
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            print(error_msg)
            print(f"响应内容：{response.text}")
            retry_count += 1
            if retry_count < max_retries:
                print(f"第{retry_count}次重试...")
                time.sleep(2)
                continue
            download_failed_ids.append({"id": topic_id, "reason": error_msg})
        except UnicodeEncodeError as e:
            error_msg = f"编码错误: {str(e)}，请检查Cookie等请求头信息是否包含非法字符"
            print(error_msg)
            download_failed_ids.append({"id": topic_id, "reason": error_msg})
        except Exception as e:
            error_msg = f"未预期的错误: {str(e)}"
            print(error_msg)
            download_failed_ids.append({"id": topic_id, "reason": error_msg})
        return False

def save_failed_article(article_id, title, reason):
    """保存未成功下载的文章信息到文件"""
    failed_info = f"\n文章ID: {article_id}\n标题: {title}\n失败原因: {reason}\n"
    with open('failed_down.txt', 'a', encoding='utf-8') as f:
        f.write(failed_info)

def retry_failed_articles(failed_ids):
    """重试下载失败的文章
    Args:
        failed_ids: 失败的文章ID列表，每个元素为字典，包含id和reason
    Returns:
        list: 最终失败的文章ID列表
    """
    if not failed_ids:
        return []

    print(f"\n开始重试下载失败的文章...")
    final_failed_ids = []
    max_retries = 3

    for failed_item in failed_ids:
        article_id = failed_item['id']
        retry_count = 0
        success = False

        while retry_count < max_retries and not success:
            try:
                print(f"第{retry_count + 1}次尝试下载文章 {article_id}...")
                if get_single_article(article_id):
                    print(f"文章 {article_id} 重试成功")
                    success = True
                    break
                else:
                    print(f"文章 {article_id} 第{retry_count + 1}次重试失败")
            except Exception as e:
                print(f"文章 {article_id} 第{retry_count + 1}次重试失败: {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                print(f"等待5秒后进行第{retry_count + 1}次重试...")
                time.sleep(5)
        
        if not success:
            final_failed_ids.append(failed_item)
            print(f"文章 {article_id} 已达到最大重试次数，放弃重试")
    
    return final_failed_ids

def process_all_articles():
    """批量处理文章列表
    处理所有文章并记录失败的情况
    """
    try:
        # 读取文章列表文件
        with open('all_list.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_articles = len(lines)
        processed_count = 0
        success_count = 0
        download_failed_ids = []
        save_failed_ids = []
        
        print(f"\n开始批量处理文章，共{total_articles}篇...\n")
        
        # 记录所有文章ID
        all_topic_ids = [line.split()[0].strip() for line in lines]
        
        for i, line in enumerate(lines, 1):
            # 提取每行开头的数字作为topic_id
            topic_id = line.split()[0].strip()
            
            print(f"\n[{i}/{total_articles}] 正在处理文章 {topic_id}...")
            if get_single_article(topic_id, download_failed_ids, save_failed_ids):
                success_count += 1
            processed_count += 1
            
            # 每处理30篇文章暂停15秒
            if processed_count % 30 == 0 and i < total_articles:
                print(f"\n已处理{processed_count}篇文章，暂停15秒...")
                time.sleep(15)
        
        # 检查文件保存完整性
        print("\n开始检查文件保存完整性...")
        articles_dir = 'articles'
        if os.path.exists(articles_dir):
            saved_files = os.listdir(articles_dir)
            missing_articles = []
            missing_details = []
            
            for topic_id in all_topic_ids:
                # 检查是否存在包含该topic_id的文件
                found = False
                for filename in saved_files:
                    if topic_id in filename:
                        found = True
                        break
                if not found:
                    # 检查是否在已知的失败列表中
                    is_known_failed = any(item['id'] == topic_id for item in download_failed_ids)
                    if not is_known_failed:
                        missing_articles.append(topic_id)
                        # 尝试获取文章详细信息
                        try:
                            article_info = next((line for line in lines if line.split()[0].strip() == topic_id), None)
                            if article_info:
                                missing_details.append({"id": topic_id, "reason": "文件未能成功保存到articles目录"})
                        except Exception as e:
                            missing_details.append({"id": topic_id, "reason": f"文件未能成功保存到articles目录，获取详细信息时出错: {str(e)}"})
        
        # 合并所有失败记录
        all_failed_ids = []
        all_failed_ids.extend(download_failed_ids)
        all_failed_ids.extend(save_failed_ids)
        if 'missing_details' in locals():
            all_failed_ids.extend(missing_details)
        
        # 对失败的文章进行重试
        if all_failed_ids:
            print(f"\n开始重试失败的文章，共{len(all_failed_ids)}篇...")
            final_failed_ids = retry_failed_articles(all_failed_ids)
            
            # 保存最终失败的文章ID和失败原因
            if final_failed_ids:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open('failed_down.txt', 'w', encoding='utf-8') as f:
                    f.write(f"=== 保存时间：{current_time} ===\n\n")
                    f.write("=== 最终失败的文章列表 ===\n\n")
                    for failed_item in final_failed_ids:
                        f.write(f"文章ID: {failed_item['id']}\n失败原因: {failed_item['reason']}\n\n")
                print(f"\n最终失败的文章信息已保存到 failed_down.txt，共 {len(final_failed_ids)} 篇")
                print("最终失败的文章ID：", [item['id'] for item in final_failed_ids])
            else:
                print("\n所有失败的文章重试后均下载成功！")
        
        print(f"\n批量处理完成！总共处理{total_articles}篇文章，成功{success_count}篇，")
        print(f"下载失败{len(download_failed_ids)}篇，保存失败{len(save_failed_ids)}篇")
        if 'missing_articles' in locals() and missing_articles:
            print(f"未成功保存{len(missing_articles)}篇")
        
    except FileNotFoundError:
        print("错误：未找到all_list.txt文件")
    except Exception as e:
        print(f"批量处理过程中发生错误：{str(e)}")

if __name__ == '__main__':
    process_all_articles()