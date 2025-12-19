"""
中心服务器客户端模块
负责与中心服务器通信：心跳、任务拉取、结果上报
"""

import os
import json
import time
import threading
import requests
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from utils.log import douyin_logger

class CenterClient:
    """中心服务器客户端"""
    
    def __init__(self, center_base_url: str, device_id: Optional[str] = None, device_name: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            center_base_url: 中心服务器地址，例如 http://your-server.com:5000
            device_id: 设备ID，如果不提供则自动生成
            device_name: 设备名称，如果不提供则使用主机名
        """
        self.center_base_url = center_base_url.rstrip('/')
        self.device_id = device_id or self._generate_device_id()
        self.device_name = device_name or self._get_hostname()
        self.is_running = False
        self.heartbeat_thread = None
        self.task_poll_thread = None
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.task_poll_interval = 10  # 任务轮询间隔（秒）
        
    def _generate_device_id(self) -> str:
        """生成设备ID"""
        # 尝试从文件读取已保存的设备ID
        device_id_file = os.path.join(os.path.dirname(__file__), '..', '.device_id')
        if os.path.exists(device_id_file):
            try:
                with open(device_id_file, 'r', encoding='utf-8') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
            except Exception as e:
                douyin_logger.warning(f"Failed to read device_id file: {e}")
        
        # 生成新的设备ID
        device_id = f"device_{uuid.uuid4().hex[:12]}"
        
        # 保存设备ID
        try:
            with open(device_id_file, 'w', encoding='utf-8') as f:
                f.write(device_id)
        except Exception as e:
            douyin_logger.warning(f"Failed to save device_id file: {e}")
        
        return device_id
    
    def _get_hostname(self) -> str:
        """获取主机名"""
        try:
            import socket
            return socket.gethostname()
        except:
            return "Unknown Device"
    
    def register_device(self) -> bool:
        """
        注册设备到中心服务器
        
        Returns:
            bool: 注册是否成功
        """
        try:
            import socket
            # 获取本机IP地址
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                ip_address = s.getsockname()[0]
            except:
                ip_address = '127.0.0.1'
            finally:
                s.close()
            
            response = requests.post(
                f'{self.center_base_url}/api/devices/register',
                json={
                    'device_id': self.device_id,
                    'device_name': self.device_name,
                    'ip_address': ip_address
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                if response_data.get('code') in [200, 201]:
                    message = response_data.get('message', 'Device registered successfully')
                    douyin_logger.success(f"{message}: {self.device_id}")
                    return True
                else:
                    # 即使返回200/201，但code不是200/201，也记录警告但继续
                    douyin_logger.warning(f"Device registration response: {response_data.get('message')}")
                    return True
            else:
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', response.text)
                    # 如果是设备已存在的错误，也认为成功（兼容旧版本API）
                    if 'already exists' in error_msg.lower() or response.status_code == 400:
                        douyin_logger.info(f"Device already exists, continuing: {self.device_id}")
                        return True
                except:
                    pass
                
                douyin_logger.error(f"Failed to register device: {response.text}")
                return False
        except Exception as e:
            douyin_logger.error(f"Error registering device: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """
        发送心跳
        
        Returns:
            bool: 心跳是否成功
        """
        try:
            response = requests.post(
                f'{self.center_base_url}/api/devices/{self.device_id}/heartbeat',
                timeout=10
            )
            
            if response.status_code == 200:
                # 记录心跳成功（每10次心跳记录一次，避免日志过多）
                if not hasattr(self, '_heartbeat_count'):
                    self._heartbeat_count = 0
                self._heartbeat_count += 1
                if self._heartbeat_count % 10 == 0:
                    douyin_logger.debug(f"Heartbeat sent successfully ({self._heartbeat_count} times)")
                return True
            else:
                douyin_logger.warning(f"Heartbeat failed: {response.text}")
                return False
        except Exception as e:
            douyin_logger.warning(f"Heartbeat error: {e}")
            return False
    
    def get_account_id(self) -> Optional[int]:
        """
        获取当前设备关联的账号ID
        
        Returns:
            Optional[int]: 账号ID，如果不存在则返回None
        """
        try:
            # 通过device_id查找账号
            response = requests.get(
                f'{self.center_base_url}/api/accounts',
                params={'device_id': self.device_id},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    # 接口返回的数据结构：{ "data": { "accounts": [...], ... } }
                    response_data = data.get('data', {})
                    if isinstance(response_data, dict):
                        accounts = response_data.get('accounts', [])
                    else:
                        # 兼容旧版本：直接返回数组
                        accounts = response_data if isinstance(response_data, list) else []
                    
                    if accounts:
                        # 返回第一个账号的ID（一对一关系）
                        return accounts[0].get('id')
            
            return None
        except Exception as e:
            douyin_logger.error(f"Error getting account_id: {e}")
            return None
    
    def get_pending_tasks(self, account_id: Optional[int] = None) -> List[Dict]:
        """
        获取待处理的任务（通过account_id）
        
        Args:
            account_id: 账号ID，如果不提供则自动获取
        
        Returns:
            List[Dict]: 任务列表
        """
        try:
            if account_id is None:
                account_id = self.get_account_id()
                if account_id is None:
                    return []
            
            # 获取视频任务（使用account_id）
            response = requests.get(
                f'{self.center_base_url}/api/video/tasks',
                params={
                    'account_id': account_id,
                    'status': 'pending'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    tasks = data.get('data', [])
                    return [{'type': 'video', **task} for task in tasks]
            
            return []
        except Exception as e:
            douyin_logger.error(f"Error getting pending tasks: {e}")
            return []
    
    def get_pending_chat_tasks(self, account_id: Optional[int] = None) -> List[Dict]:
        """
        获取待处理的对话任务（通过account_id）
        
        Args:
            account_id: 账号ID，如果不提供则自动获取
        
        Returns:
            List[Dict]: 任务列表
        """
        try:
            if account_id is None:
                account_id = self.get_account_id()
                if account_id is None:
                    return []
            
            # 获取对话任务（使用account_id）
            response = requests.get(
                f'{self.center_base_url}/api/chat/tasks',
                params={
                    'account_id': account_id,
                    'status': 'pending'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    tasks = data.get('data', [])
                    return [{'type': 'chat', **task} for task in tasks]
            
            return []
        except Exception as e:
            douyin_logger.error(f"Error getting pending chat tasks: {e}")
            return []
    
    def get_pending_listen_tasks(self, account_id: Optional[int] = None) -> List[Dict]:
        """
        获取待处理的监听任务（通过account_id）
        
        Args:
            account_id: 账号ID，如果不提供则自动获取
        
        Returns:
            List[Dict]: 任务列表
        """
        try:
            if account_id is None:
                account_id = self.get_account_id()
                if account_id is None:
                    return []
            
            # 获取监听任务（使用account_id）
            response = requests.get(
                f'{self.center_base_url}/api/listen/tasks',
                params={
                    'account_id': account_id,
                    'status': 'pending'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    tasks = data.get('data', [])
                    return [{'type': 'listen', **task} for task in tasks]
            
            return []
        except Exception as e:
            douyin_logger.error(f"Error getting pending listen tasks: {e}")
            return []
    
    def update_task_status(self, task_id: int, task_type: str, status: str, error_message: Optional[str] = None, progress: Optional[int] = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            task_type: 任务类型 ('video', 'chat' 或 'listen')
            status: 任务状态
            error_message: 错误信息（可选）
            progress: 进度（可选）
        """
        try:
            if task_type == 'video':
                callback_url = f'{self.center_base_url}/api/video/callback'
            elif task_type == 'chat':
                callback_url = f'{self.center_base_url}/api/chat/callback'
            elif task_type == 'listen':
                callback_url = f'{self.center_base_url}/api/listen/callback'
            else:
                douyin_logger.error(f"Unknown task type: {task_type}")
                return
            
            data = {
                'task_id': task_id,
                'status': status
            }
            if error_message:
                data['error_message'] = error_message
            if progress is not None:
                data['progress'] = progress
            
            response = requests.post(
                callback_url,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                douyin_logger.success(f"Task {task_id} status updated to {status}")
            else:
                douyin_logger.error(f"Failed to update task status: {response.text}")
        except Exception as e:
            douyin_logger.error(f"Error updating task status: {e}")
    
    def get_account_info(self, account_id: int) -> Optional[Dict]:
        """
        获取账号信息（包括cookies）
        
        Args:
            account_id: 账号ID
            
        Returns:
            Optional[Dict]: 账号信息，如果不存在则返回None
        """
        try:
            response = requests.get(
                f'{self.center_base_url}/api/accounts/{account_id}',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    return data.get('data')
            
            return None
        except Exception as e:
            douyin_logger.error(f"Error getting account info: {e}")
            return None
    
    def update_account_cookies(self, account_id: int, cookies: Dict):
        """
        更新账号cookies
        
        Args:
            account_id: 账号ID
            cookies: cookies数据（storage_state格式）
        """
        try:
            cookies_json = json.dumps(cookies, ensure_ascii=False) if isinstance(cookies, dict) else cookies
            
            response = requests.put(
                f'{self.center_base_url}/api/accounts/{account_id}/cookies',
                json={'cookies': cookies_json},
                timeout=10
            )
            
            if response.status_code == 200:
                douyin_logger.success(f"Account {account_id} cookies updated")
            else:
                douyin_logger.error(f"Failed to update account cookies: {response.text}")
        except Exception as e:
            douyin_logger.error(f"Error updating account cookies: {e}")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            self.send_heartbeat()
            time.sleep(self.heartbeat_interval)
    
    def _task_poll_loop(self):
        """任务轮询循环"""
        while self.is_running:
            try:
                # 获取所有待处理任务
                video_tasks = self.get_pending_tasks()
                chat_tasks = self.get_pending_chat_tasks()
                listen_tasks = self.get_pending_listen_tasks()
                all_tasks = video_tasks + chat_tasks + listen_tasks
                
                if all_tasks:
                    douyin_logger.info(f"Found {len(all_tasks)} pending tasks")
                    # 处理任务（由外部调用者处理）
                    # 这里只是轮询，实际处理在 start() 方法中
                
            except Exception as e:
                douyin_logger.error(f"Task poll error: {e}")
            
            time.sleep(self.task_poll_interval)
    
    def start(self, task_handler=None):
        """
        启动客户端（开始心跳和任务轮询）
        
        Args:
            task_handler: 任务处理函数，接收任务字典，返回处理结果
        """
        if self.is_running:
            douyin_logger.warning("Client is already running")
            return
        
        # 先注册设备（带重试机制）
        max_retries = 5
        retry_delay = 3  # 秒
        for attempt in range(max_retries):
            if self.register_device():
                break
            if attempt < max_retries - 1:
                douyin_logger.warning(f"Failed to register device (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                douyin_logger.error("Failed to register device after all retries, client will not start")
                douyin_logger.error(f"Please ensure the center server is running at {self.center_base_url}")
                douyin_logger.error("")
                douyin_logger.error("Troubleshooting:")
                douyin_logger.error("  1. Check if the center server is running")
                douyin_logger.error("  2. Verify the server address is correct")
                douyin_logger.error("  3. Set CENTER_BASE_URL environment variable if needed:")
                douyin_logger.error("     Windows PowerShell: $env:CENTER_BASE_URL='http://127.0.0.1:5000'")
                douyin_logger.error("     Linux/Mac: export CENTER_BASE_URL='http://127.0.0.1:5000'")
                return
        
        self.is_running = True
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        douyin_logger.info("Heartbeat thread started")
        
        # 启动任务轮询线程
        if task_handler:
            def poll_and_handle():
                account_id = None
                while self.is_running:
                    try:
                        # 获取账号ID（如果还没有）
                        if account_id is None:
                            account_id = self.get_account_id()
                            if account_id is None:
                                douyin_logger.warning("No account found for this device. Waiting for account creation...")
                                time.sleep(self.task_poll_interval)
                                continue
                        
                        # 获取任务
                        video_tasks = self.get_pending_tasks(account_id)
                        chat_tasks = self.get_pending_chat_tasks(account_id)
                        listen_tasks = self.get_pending_listen_tasks(account_id)
                        all_tasks = video_tasks + chat_tasks + listen_tasks
                        
                        if all_tasks:
                            douyin_logger.info(f"Found {len(all_tasks)} pending tasks for account {account_id}")
                        
                        for task in all_tasks:
                            try:
                                task_handler(task, self)
                            except Exception as e:
                                douyin_logger.error(f"Error handling task {task.get('id')}: {e}")
                        
                    except Exception as e:
                        douyin_logger.error(f"Task poll error: {e}")
                    
                    time.sleep(self.task_poll_interval)
            
            self.task_poll_thread = threading.Thread(target=poll_and_handle, daemon=True)
            self.task_poll_thread.start()
            douyin_logger.info("Task poll thread started")
        else:
            self.task_poll_thread = threading.Thread(target=self._task_poll_loop, daemon=True)
            self.task_poll_thread.start()
            douyin_logger.info("Task poll thread started (no handler)")
        
        douyin_logger.success(f"Center client started (device_id: {self.device_id})")
    
    def stop(self):
        """停止客户端"""
        self.is_running = False
        douyin_logger.info("Center client stopped")

