"""
客户端主程序
启动客户端，连接到中心服务器，处理任务
"""

import os
import sys
import signal
import requests
from client.center_client import CenterClient
from client.task_handler import create_task_handler
from utils.log import douyin_logger

# 从环境变量或配置文件读取中心服务器地址
# 默认连接本机中心服务，可通过环境变量 CENTER_BASE_URL 覆盖
# 例如：
#   Windows PowerShell: $env:CENTER_BASE_URL="http://192.168.1.100:8080"
#   Linux/Mac: export CENTER_BASE_URL="http://192.168.1.100:8080"
DEFAULT_CENTER_BASE_URL = os.getenv('CENTER_BASE_URL', None)

def detect_center_server():
    """
    自动检测中心服务器地址
    尝试常见的端口：8080, 8081, 8082
    """
    if DEFAULT_CENTER_BASE_URL:
        return DEFAULT_CENTER_BASE_URL
    
    # 尝试检测中心服务器
    common_ports = [8080, 8081, 8082]
    for port in common_ports:
        url = f'http://127.0.0.1:{port}'
        try:
            response = requests.get(f'{url}/api/health', timeout=2)
            if response.status_code == 200:
                douyin_logger.info(f"Detected center server at {url}")
                return url
        except:
            continue
    
    # 如果都检测不到，使用默认值
    default_url = 'http://127.0.0.1:8080'
    douyin_logger.warning(f"Could not detect center server, using default: {default_url}")
    douyin_logger.warning("You can set CENTER_BASE_URL environment variable to specify the server address")
    return default_url

CENTER_BASE_URL = detect_center_server()

def main():
    """主函数"""
    # 创建客户端
    client = CenterClient(
        center_base_url=CENTER_BASE_URL,
        device_name=os.getenv('DEVICE_NAME', None)
    )
    
    # 创建任务处理器
    task_handler = create_task_handler(client)
    
    # 启动客户端
    douyin_logger.info(f"Starting center client, connecting to: {CENTER_BASE_URL}")
    client.start(task_handler=task_handler)
    
    # 等待中断信号
    def signal_handler(sig, frame):
        douyin_logger.info("Received interrupt signal, stopping client...")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 保持运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()

