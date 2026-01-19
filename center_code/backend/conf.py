from pathlib import Path
import os
import shutil

BASE_DIR = Path(__file__).parent.resolve()
XHS_SERVER = "http://127.0.0.1:11901"

# Chrome 浏览器路径配置
# 优先级：环境变量 > 配置文件中的路径 > 自动检测
LOCAL_CHROME_PATH = os.environ.get('LOCAL_CHROME_PATH', '')

if not LOCAL_CHROME_PATH:
    # 尝试从配置文件读取（如果之前有配置）
    _config_path = r"C:\Users\33947\AppData\Local\Google\Chrome\Application\chrome.exe"
    if os.path.exists(_config_path):
        LOCAL_CHROME_PATH = _config_path
    else:
        # 自动检测常见路径
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe"),  # Edge 作为备选
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                LOCAL_CHROME_PATH = path
                print(f"[配置] 自动检测到浏览器路径: {LOCAL_CHROME_PATH}")
                break
        
        if not LOCAL_CHROME_PATH:
            # 尝试使用 which/where 命令查找
            chrome_exe = shutil.which('chrome') or shutil.which('google-chrome') or shutil.which('chromium')
            if chrome_exe:
                LOCAL_CHROME_PATH = chrome_exe
                print(f"[配置] 从系统 PATH 找到浏览器: {LOCAL_CHROME_PATH}")
            else:
                # 如果都找不到，设置为 None，使用 Playwright 自带的 Chromium
                LOCAL_CHROME_PATH = None
                print("[配置] 未找到 Chrome 浏览器，将使用 Playwright 自带的 Chromium")

LOCAL_CHROME_HEADLESS = os.environ.get('LOCAL_CHROME_HEADLESS', 'False').lower() == 'true'
