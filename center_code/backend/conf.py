"""
配置文件
兼容service_code的conf.py
"""
from pathlib import Path
import os

# 基础目录 - 指向backend目录
BASE_DIR = Path(__file__).parent.resolve()

# Chrome配置
LOCAL_CHROME_PATH = os.getenv('LOCAL_CHROME_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
LOCAL_CHROME_HEADLESS = os.getenv('LOCAL_CHROME_HEADLESS', 'False').lower() == 'true'

# 其他配置
XHS_SERVER = os.getenv('XHS_SERVER', "http://127.0.0.1:11901")

