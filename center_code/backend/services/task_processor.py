"""
后台任务处理器
定期检查待处理的任务并执行
"""
import threading
import time
from datetime import datetime
from sqlalchemy.orm import Session

from models import VideoTask, ChatTask, ListenTask
from db import get_db
from services.task_executor import (
    execute_video_upload,
    execute_chat_send,
    execute_listen_start,
    execute_listen_stop
)

class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, poll_interval: int = 5):
        """
        初始化任务处理器
        
        Args:
            poll_interval: 轮询间隔（秒）
        """
        self.poll_interval = poll_interval
        self.is_running = False
        self.thread = None
    
    def start(self):
        """启动任务处理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("任务处理器已启动")
    
    def stop(self):
        """停止任务处理器"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)  # 减少超时时间，避免阻塞重载
        # 不打印消息，避免在重载时产生噪音
    
    def _process_loop(self):
        """任务处理循环"""
        while self.is_running:
            try:
                self._process_pending_tasks()
            except Exception as e:
                print(f"任务处理错误: {e}")
            
            time.sleep(self.poll_interval)
    
    def _process_pending_tasks(self):
        """处理待处理的任务"""
        with get_db() as db:
            # 处理视频上传任务（包括pending和uploading状态，防止任务卡住）
            video_tasks = db.query(VideoTask).filter(
                VideoTask.status.in_(['pending', 'uploading'])
            ).limit(10).all()
            
            for task in video_tasks:
                # 检查任务是否已经在处理中（通过started_at判断）
                if task.status == 'uploading' and task.started_at:
                    # 如果任务已经开始超过10分钟还没完成，可能是卡住了，重新处理
                    from datetime import datetime, timedelta
                    if (datetime.now() - task.started_at).total_seconds() < 600:
                        continue  # 任务正在处理中，跳过
                    else:
                        # 任务可能卡住了，重置状态
                        task.status = 'pending'
                        task.started_at = None
                        db.commit()
                
                try:
                    # 在后台线程中执行
                    import asyncio
                    thread = threading.Thread(
                        target=lambda tid=task.id: asyncio.run(execute_video_upload(tid)),
                        daemon=True
                    )
                    thread.start()
                    print(f"✓ 启动视频上传任务 {task.id}: {task.video_title}")
                except Exception as e:
                    print(f"✗ 启动视频上传任务 {task.id} 失败: {e}")
            
            # 处理对话发送任务
            chat_tasks = db.query(ChatTask).filter(
                ChatTask.status == 'pending'
            ).limit(10).all()
            
            for task in chat_tasks:
                try:
                    # 在后台线程中执行
                    import asyncio
                    thread = threading.Thread(
                        target=lambda: asyncio.run(execute_chat_send(task.id)),
                        daemon=True
                    )
                    thread.start()
                except Exception as e:
                    print(f"启动对话发送任务 {task.id} 失败: {e}")
            
            # 处理监听任务
            listen_tasks = db.query(ListenTask).filter(
                ListenTask.status == 'pending'
            ).limit(10).all()
            
            for task in listen_tasks:
                try:
                    # 在后台线程中执行
                    import asyncio
                    if task.action == 'start':
                        thread = threading.Thread(
                            target=lambda: asyncio.run(execute_listen_start(task.id)),
                            daemon=True
                        )
                    elif task.action == 'stop':
                        thread = threading.Thread(
                            target=lambda: asyncio.run(execute_listen_stop(task.id)),
                            daemon=True
                        )
                    else:
                        continue
                    thread.start()
                except Exception as e:
                    print(f"启动监听任务 {task.id} 失败: {e}")


# 全局任务处理器实例
_task_processor = None

def get_task_processor() -> TaskProcessor:
    """获取任务处理器实例（单例）"""
    global _task_processor
    if _task_processor is None:
        _task_processor = TaskProcessor()
    return _task_processor

