import requests
import json
import time
import threading
import logging
from queue import Queue
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import tkinter as tk
from tkinter import ttk
import webbrowser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = 'config.json'
OUTPUT_FILE = 'cloudflare_ips.json'

# 读取配置
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"配置文件 {CONFIG_FILE} 未找到。请确保配置文件存在。")
        exit(1)

# 保存结果
def save_results(results):
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=4)

# 获取Cloudflare IP范围
def get_cloudflare_ip_ranges():
    url = 'https://www.cloudflare.com/ips/'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # 只保留纯IP地址行，过滤HTML内容
        return [line.strip() for line in response.text.splitlines() if '.' in line]
    except requests.RequestException as e:
        logger.error(f"获取Cloudflare IP范围时出错: {e}")
        return []

# 检查IP是否为Cloudflare反代
def is_cloudflare_reverse_proxy(ip):
    # 添加IP格式验证
    if not ip or '/' in ip or '<' in ip or '>' in ip:
        logger.warning(f"跳过无效IP: {ip}")
        return False
        
    url = f"http://{ip}"
    try:
        response = requests.get(url, timeout=5)  # 缩短超时时间
        response.raise_for_status()
        
        # 检查响应头
        headers = response.headers
        if 'Server' in headers and 'cloudflare' in headers['Server'].lower():
            return True
        
        # 检查HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')
        if soup.find(text=lambda text: 'cloudflare' in str(text).lower()):
            return True
        
        # 检查JavaScript内容
        for script in soup.find_all('script'):
            if 'cloudflare' in script.text.lower():
                return True
        
        # 检查重定向
        if response.history:
            for resp in response.history:
                if 'cloudflare' in resp.headers.get('Server', '').lower():
                    return True
        
        return False
    except requests.RequestException as e:
        logger.warning(f"检查IP {ip} 时出错: {e}")
        return False

# 爬虫任务
def crawl_task(ip_queue, results, lock):
    while not ip_queue.empty():
        ip = ip_queue.get()
        if is_cloudflare_reverse_proxy(ip):
            with lock:
                results.append(ip)
                logger.info(f"发现Cloudflare反代IP: {ip}")
        else:
            logger.info(f"IP {ip} 不是Cloudflare反代")
        time.sleep(0.5)  # 适当调整请求频率
        ip_queue.task_done()

# 主函数
def main():
    config = load_config()
    ip_ranges = get_cloudflare_ip_ranges()
    
    if not ip_ranges:
        logger.error("无法获取Cloudflare IP范围。")
        return
    
    logger.info("开始扫描Cloudflare反代IP...")
    
    ip_queue = Queue()
    results = []
    lock = threading.Lock()
    
    # 将所有IP添加到队列
    for ip_range in ip_ranges:
        for ip in ip_range.split('/'):
            ip_queue.put(ip)
    
    # 启动多线程
    threads = []
    for _ in range(config['num_threads']):
        thread = threading.Thread(target=crawl_task, args=(ip_queue, results, lock))
        thread.start()
        threads.append(thread)
    
    # 等待所有线程完成
    ip_queue.join()
    for thread in threads:
        thread.join()
    
    logger.info(f"扫描完成，共发现 {len(results)} 个Cloudflare反代IP")
    save_results(results)
    
    # 创建可视化界面
    root = tk.Tk()
    root.title("Cloudflare反代IP扫描结果")
    
    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    tree = ttk.Treeview(frame, columns=("IP",), show="headings")
    tree.heading("IP", text="Cloudflare反代IP")
    tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    tree.configure(yscrollcommand=scrollbar.set)
    
    for ip in results:
        tree.insert("", "end", values=(ip,))
    
    def open_url(event):
        item = tree.selection()[0]
        ip = tree.item(item, "values")[0]
        webbrowser.open(f"http://{ip}")
    
    tree.bind("<Double-1>", open_url)
    
    root.mainloop()

if __name__ == "__main__":
    main()