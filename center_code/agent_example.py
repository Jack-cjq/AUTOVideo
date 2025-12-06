"""
设备端Agent示例代码
用于演示如何在设备上实现Agent程序，与中心平台进行通信
"""

import requests
import time
import json
import uuid
from datetime import datetime

class DouyinAgent:
    """抖音设备Agent"""
    
    def __init__(self, api_base='http://localhost:5000/api', device_id=None):
        self.api_base = api_base
        self.device_id = device_id or f'device_{uuid.uuid4().hex[:8]}'
        self.device_name = f'Agent-{self.device_id}'
        self.ip_address = '127.0.0.1'
        self.running = False
        
    def register(self):
        """注册设备到中心平台"""
        try:
            data = {
                'device_id': self.device_id,
                'device_name': self.device_name,
                'ip_address': self.ip_address
            }
            response = requests.post(f'{self.api_base}/devices/register', json=data, timeout=5)
            result = response.json()
            
            if result['code'] in [200, 201]:
                print(f'✓ 设备注册成功: {self.device_id}')
                return True
            else:
                print(f'✗ 设备注册失败: {result["message"]}')
                return False
        except Exception as e:
            print(f'✗ 注册异常: {e}')
            return False
    
    def heartbeat(self):
        """发送心跳"""
        try:
            response = requests.post(f'{self.api_base}/devices/{self.device_id}/heartbeat', timeout=5)
            result = response.json()
            
            if result['code'] == 200:
                print(f'♥ 心跳发送成功 [{datetime.now().strftime("%H:%M:%S")}]')
                return True
            else:
                print(f'✗ 心跳发送失败: {result["message"]}')
                return False
        except Exception as e:
            print(f'✗ 心跳异常: {e}')
            return False
    
    def get_pending_tasks(self):
        """获取待处理任务"""
        try:
            # 获取登录任务
            login_response = requests.get(
                f'{self.api_base}/login/tasks?device_id=1&status=pending',
                timeout=5
            )
            login_tasks = login_response.json().get('data', [])
            
            # 获取视频任务
            video_response = requests.get(
                f'{self.api_base}/video/tasks?device_id=1&status=pending',
                timeout=5
            )
            video_tasks = video_response.json().get('data', [])
            
            # 获取对话任务
            chat_response = requests.get(
                f'{self.api_base}/chat/tasks?device_id=1&status=pending',
                timeout=5
            )
            chat_tasks = chat_response.json().get('data', [])
            
            return {
                'login': login_tasks,
                'video': video_tasks,
                'chat': chat_tasks
            }
        except Exception as e:
            print(f'✗ 获取任务异常: {e}')
            return {'login': [], 'video': [], 'chat': []}
    
    def execute_login_task(self, task):
        """执行登录任务"""
        task_id = task['id']
        print(f'→ 执行登录任务 #{task_id}')
        
        try:
            # 模拟登录过程
            time.sleep(2)
            
            # 上报成功
            callback_data = {
                'task_id': task_id,
                'status': 'success',
                'cookie_file': '/path/to/cookie.json',
                'error_message': None
            }
            
            response = requests.post(f'{self.api_base}/login/callback', json=callback_data, timeout=5)
            result = response.json()
            
            if result['code'] == 200:
                print(f'✓ 登录任务完成 #{task_id}')
                return True
            else:
                print(f'✗ 登录任务上报失败: {result["message"]}')
                return False
        except Exception as e:
            # 上报失败
            callback_data = {
                'task_id': task_id,
                'status': 'failed',
                'error_message': str(e)
            }
            
            try:
                requests.post(f'{self.api_base}/login/callback', json=callback_data, timeout=5)
            except:
                pass
            
            print(f'✗ 登录任务异常: {e}')
            return False
    
    def execute_video_task(self, task):
        """执行视频上传任务"""
        task_id = task['id']
        print(f'→ 执行视频上传任务 #{task_id}')
        
        try:
            # 模拟下载视频
            print(f'  下载视频: {task["video_url"]}')
            time.sleep(1)
            
            # 模拟上传过程
            for progress in [25, 50, 75, 100]:
                time.sleep(1)
                callback_data = {
                    'task_id': task_id,
                    'status': 'uploading' if progress < 100 else 'success',
                    'progress': progress,
                    'error_message': None
                }
                
                response = requests.post(f'{self.api_base}/video/callback', json=callback_data, timeout=5)
                result = response.json()
                
                if result['code'] == 200:
                    print(f'  上传进度: {progress}%')
                else:
                    print(f'  上报失败: {result["message"]}')
            
            print(f'✓ 视频上传任务完成 #{task_id}')
            return True
        except Exception as e:
            # 上报失败
            callback_data = {
                'task_id': task_id,
                'status': 'failed',
                'error_message': str(e)
            }
            
            try:
                requests.post(f'{self.api_base}/video/callback', json=callback_data, timeout=5)
            except:
                pass
            
            print(f'✗ 视频上传任务异常: {e}')
            return False
    
    def execute_chat_task(self, task):
        """执行对话任务"""
        task_id = task['id']
        print(f'→ 执行对话任务 #{task_id}')
        
        try:
            # 模拟发送消息
            print(f'  目标用户: {task["target_user"]}')
            print(f'  消息内容: {task["message"]}')
            time.sleep(1)
            
            # 上报成功
            callback_data = {
                'task_id': task_id,
                'status': 'success',
                'error_message': None
            }
            
            response = requests.post(f'{self.api_base}/chat/callback', json=callback_data, timeout=5)
            result = response.json()
            
            if result['code'] == 200:
                print(f'✓ 对话任务完成 #{task_id}')
                return True
            else:
                print(f'✗ 对话任务上报失败: {result["message"]}')
                return False
        except Exception as e:
            # 上报失败
            callback_data = {
                'task_id': task_id,
                'status': 'failed',
                'error_message': str(e)
            }
            
            try:
                requests.post(f'{self.api_base}/chat/callback', json=callback_data, timeout=5)
            except:
                pass
            
            print(f'✗ 对话任务异常: {e}')
            return False
    
    def process_tasks(self):
        """处理所有待处理任务"""
        tasks = self.get_pending_tasks()
        
        # 处理登录任务
        for task in tasks['login']:
            self.execute_login_task(task)
        
        # 处理视频任务
        for task in tasks['video']:
            self.execute_video_task(task)
        
        # 处理对话任务
        for task in tasks['chat']:
            self.execute_chat_task(task)
    
    def start(self):
        """启动Agent"""
        print(f'启动Agent: {self.device_id}')
        
        # 注册设备
        if not self.register():
            print('设备注册失败，退出')
            return
        
        self.running = True
        heartbeat_counter = 0
        
        try:
            while self.running:
                # 每30秒发送一次心跳
                if heartbeat_counter % 3 == 0:
                    self.heartbeat()
                
                # 每10秒轮询一次任务
                self.process_tasks()
                
                heartbeat_counter += 1
                time.sleep(10)
        except KeyboardInterrupt:
            print('\nAgent已停止')
            self.running = False
    
    def stop(self):
        """停止Agent"""
        self.running = False


if __name__ == '__main__':
    # 创建并启动Agent
    agent = DouyinAgent(device_id='device_001')
    agent.start()
