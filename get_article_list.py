import os
import json
import requests
import time
import hashlib
from datetime import datetime

def load_config(config_file='config.json'):
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_url(url, headers, max_retries=3):
    """处理单个URL的请求，提取topic_id和title，支持重试"""
    for attempt in range(max_retries):
        try:
            print(f"\n开始请求URL: {url} (尝试 {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, verify=False)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            resp_data = response.json()
            # 检查响应数据结构
            if 'resp_data' in resp_data and 'topics' in resp_data['resp_data']:
                topics = resp_data['resp_data']['topics']
                
                results = []
                failed_extracts = []
                for topic in topics:
                    topic_id = topic.get('topic_id', '')
                    title = topic.get('title', '').split('\n')[0] if topic.get('title') else ''
                    if topic_id and title:
                        results.append(f"{topic_id} {title}")
                    else:
                        failed_extracts.append({
                            'topic': topic,
                            'reason': '缺少topic_id或title'
                        })
                
                print(f"成功提取 {len(results)} 条记录")
                if failed_extracts:
                    print(f"提取失败 {len(failed_extracts)} 条记录")
                return {
                    'success': results,
                    'failed': failed_extracts
                }
            else:
                print(f"警告：响应数据结构不符合预期：{resp_data}")
                if attempt < max_retries - 1:
                    print("等待2秒后重试...")
                    time.sleep(2)
                    continue
                return {
                    'success': [],
                    'failed': [{'url': url, 'reason': '响应数据结构不符合预期'}]
                }
        except Exception as e:
            print(f"处理URL时发生错误：{e}")
            if attempt < max_retries - 1:
                print("等待2秒后重试...")
                time.sleep(2)
                continue
            return {
                'success': [],
                'failed': [{'url': url, 'reason': str(e)}]
            }

def main():
    # 创建日志目录
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 加载配置文件
    print("加载配置文件...")
    config = load_config()
    
    # 设置请求头
    headers = config['headers'].copy()
    headers['Cookie'] = f"zsxq_access_token={config['auth']['zsxq_access_token']}; zsxqsessionid={config['auth']['zsxqsessionid']}"
    headers['Referer'] = config['headers'].get('Referer', 'https://wx.zsxq.com/')
    headers['Referrer-Policy'] = config['headers'].get('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    # 读取URL列表
    print("读取URL列表...")
    try:
        with open('articles_list.txt', 'r', encoding='utf-8') as f:
            urls = f.read().splitlines()
        
        all_results = []
        all_failures = []
        processed_count = 0
        failed_count = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n处理第 {i}/{len(urls)} 个URL")
            
            # 更新时间戳和签名
            timestamp = str(int(time.time()))
            headers['x-timestamp'] = timestamp
            signature = hashlib.sha1(timestamp.encode('utf-8')).hexdigest()
            headers['x-signature'] = signature
            
            # 处理URL并获取结果
            result = process_url(url.strip(), headers)
            all_results.extend(result['success'])
            if result['failed']:
                failed_count += 1
                all_failures.extend(result['failed'])
            processed_count += 1
            
            # 每次请求后暂停2秒
            print("暂停2秒...")
            time.sleep(2)
            
            # 每处理10个URL后暂停30秒
            if i % 10 == 0 and i < len(urls):
                print("暂停30秒...")
                time.sleep(30)
        
        # 保存成功结果
        print("\n保存结果到all_list.txt...")
        with open('all_list.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_results))
        
        # 保存失败记录
        if all_failures:
            failure_log = f"{log_dir}/failures_{timestamp}.json"
            print(f"保存失败记录到 {failure_log}")
            with open(failure_log, 'w', encoding='utf-8') as f:
                json.dump(all_failures, f, ensure_ascii=False, indent=2)
        
        # 输出统计信息
        print(f"\n处理完成：")
        print(f"总URL数: {len(urls)}")
        print(f"成功处理URL数: {processed_count}")
        print(f"提取失败URL数: {failed_count}")
        print(f"成功提取记录数: {len(all_results)}")
        print(f"失败记录数: {len(all_failures)}")
        
    except FileNotFoundError:
        print("错误：找不到articles_list.txt文件")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == '__main__':
    main()