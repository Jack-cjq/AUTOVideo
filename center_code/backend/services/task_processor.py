"""
后台任务处理器
定期检查待处理的任务并执行
"""
import threading
import time
from datetime import datetime, timedelta
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
    
    def __init__(self, poll_interval: int = 180):
        """
        初始化任务处理器
        
        Args:
            poll_interval: 轮询间隔（秒），默认 180 秒（3分钟）
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
        print(f"[TASK POLL] 任务轮询器已启动，每 {self.poll_interval} 秒（{self.poll_interval // 60} 分钟）轮询一次")
        while self.is_running:
            try:
                print(f"[TASK POLL] 开始轮询任务...")
                self._process_pending_tasks()
                print(f"[TASK POLL] 本次轮询完成，等待 {self.poll_interval} 秒后进行下次轮询")
            except Exception as e:
                print(f"[TASK POLL] 任务处理错误: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(self.poll_interval)
    
    def _process_pending_tasks(self):
        """处理待处理的任务"""
        with get_db() as db:
            # 处理视频上传任务
            # 排除已完成的任务（status='completed'）和定时发布任务（publish_date 不为 None）
            # 处理 pending、uploading、failed 状态的任务
            video_tasks = db.query(VideoTask).filter(
                VideoTask.status != 'completed',  # 排除已完成的任务
                VideoTask.publish_date.is_(None)  # 排除定时发布任务（publish_date 不为 None 的）
            ).filter(
                VideoTask.status.in_(['pending', 'uploading', 'failed'])
            ).order_by(VideoTask.created_at.asc()).limit(10).all()
            
            if video_tasks:
                print(f"[TASK POLL] 发现 {len(video_tasks)} 个待处理的视频任务（已排除已完成和定时发布任务）")
            
            for task in video_tasks:
                # 再次确认跳过已完成的任务（双重检查）
                if task.status == 'completed':
                    print(f"[TASK POLL] 跳过已完成的任务 {task.id}")
                    continue
                
                # 再次确认跳过定时发布任务（双重检查）
                if task.publish_date is not None:
                    print(f"[TASK POLL] 跳过定时发布任务 {task.id} (发布时间: {task.publish_date})")
                    continue
                
                # 检查任务是否已经在处理中（通过started_at判断）
                if task.status == 'uploading' and task.started_at:
                    # 如果任务已经开始超过10分钟还没完成，可能是卡住了，重新处理
                    elapsed_seconds = (datetime.now() - task.started_at).total_seconds()
                    if elapsed_seconds < 600:  # 10分钟内，认为正在处理中
                        print(f"[TASK POLL] 任务 {task.id} 正在处理中（已运行 {int(elapsed_seconds)} 秒），跳过")
                        continue
                    else:
                        # 任务可能卡住了，重置状态
                        print(f"[TASK POLL] ⚠️ 任务 {task.id} 可能卡住了（已运行 {int(elapsed_seconds)} 秒），重置为 pending 状态")
                        task.status = 'pending'
                        task.started_at = None
                        task.error_message = None
                        db.commit()
                
                try:
                    # 在后台线程中执行
                    import asyncio
                    thread = threading.Thread(
                        target=lambda tid=task.id: asyncio.run(execute_video_upload(tid)),
                        daemon=True
                    )
                    thread.start()
                    print(f"[TASK POLL] ✓ 启动视频上传任务 {task.id}: {task.video_title} (状态: {task.status})")
                except Exception as e:
                    print(f"[TASK POLL] ✗ 启动视频上传任务 {task.id} 失败: {e}")
                    # 更新任务状态为失败
                    try:
                        task.status = 'failed'
                        task.error_message = f"启动任务失败: {str(e)}"
                        db.commit()
                    except:
                        pass
            
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
        # 默认每 3 分钟（180秒）轮询一次
        _task_processor = TaskProcessor(poll_interval=180)
    return _task_processor

