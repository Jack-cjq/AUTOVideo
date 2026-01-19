"""
后台任务处理器
定期检查待处理的任务并执行
"""
import threading
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import VideoTask, ChatTask, ListenTask, PublishPlan, PlanVideo
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
    
    def _process_video_tasks(self, db: Session):
        """处理立即发布的视频任务"""
        # 排除已完成的任务（status='completed'）和未到期的定时发布任务（publish_date 不为 None）
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
    
    def _process_pending_tasks(self):
        """处理待处理的任务"""
        with get_db() as db:
            # 1. 处理发布计划
            # 查找所有状态为pending且publish_time已到的发布计划
            now = datetime.now()
            publish_plans = db.query(PublishPlan).filter(
                PublishPlan.status == 'pending',
                PublishPlan.publish_time <= now
            ).all()
            
            if publish_plans:
                print(f"[TASK POLL] 发现 {len(publish_plans)} 个到期的发布计划")
                
                for plan in publish_plans:
                    try:
                        print(f"[TASK POLL] 处理发布计划: {plan.plan_name} (ID: {plan.id})")
                        # 更新计划状态为publishing
                        plan.status = 'publishing'
                        plan.updated_at = now
                        db.commit()
                        
                        # 获取计划关联的视频
                        plan_videos = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id
                        ).all()
                        
                        if not plan_videos:
                            print(f"[TASK POLL] 发布计划 {plan.id} 没有关联的视频，跳过")
                            plan.status = 'completed'
                            plan.updated_at = now
                            db.commit()
                            continue
                        
                        # 获取该平台下的所有已登录账号
                        from models import Account
                        accounts = db.query(Account).filter(
                            Account.platform == plan.platform,
                            Account.login_status == 'logged_in'
                        ).all()
                        
                        if not accounts:
                            print(f"[TASK POLL] 发布计划 {plan.id} 的平台 {plan.platform} 没有已登录的账号，跳过")
                            plan.status = 'failed'
                            plan.updated_at = now
                            db.commit()
                            continue
                        
                        # 为每个视频分配到账号并创建视频任务
                        from pathlib import Path
                        import os
                        
                        for i, video in enumerate(plan_videos):
                            # 检查视频文件是否存在
                            video_path = video.video_url
                            file_exists = False
                            
                            # 尝试解析视频路径
                            if video_path.startswith('http://') or video_path.startswith('https://'):
                                # HTTP URL，无法预先检查存在性，假设存在
                                file_exists = True
                            else:
                                # 本地文件路径
                                if video_path.startswith('file://'):
                                    video_path = video_path[7:]
                                elif video_path.startswith('/'):
                                    # 相对路径，转换为绝对路径
                                    backend_dir = Path(__file__).parent.parent
                                    if video_path.startswith('/uploads/'):
                                        uploads_path = backend_dir.parent / 'uploads'
                                        full_path = uploads_path / video_path.lstrip('/uploads/')
                                        video_path = str(full_path)
                                    else:
                                        video_path = str(backend_dir / video_path.lstrip('/'))
                                
                                # 检查文件是否存在
                                file_exists = os.path.exists(video_path)
                            
                            if file_exists:
                                # 文件存在，创建视频任务
                                # 简单的轮询分配策略
                                account = accounts[i % len(accounts)]
                                
                                # 创建视频任务
                                video_task = VideoTask(
                                    account_id=account.id,
                                    device_id=account.device_id,
                                    video_url=video.video_url,
                                    video_title=video.video_title or f"视频 {i+1}",
                                    thumbnail_url=video.thumbnail_url,
                                    status='pending'
                                )
                                db.add(video_task)
                                
                                # 更新视频状态
                                video.status = 'published'
                            else:
                                # 文件不存在，标记视频状态为failed
                                print(f"[TASK POLL] 视频文件不存在，跳过: {video.video_url}")
                                video.status = 'failed'
                                # 不创建视频任务
                        
                        # 更新计划统计信息
                        # 统计成功发布的视频数量
                        published_count = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id,
                            PlanVideo.status == 'published'
                        ).count()
                        
                        plan.status = 'completed'
                        plan.published_count = published_count
                        plan.pending_count = 0  # 所有视频都已处理，无论成功失败
                        plan.updated_at = now
                        db.commit()
                        
                        print(f"[TASK POLL] 发布计划 {plan.id} 处理完成，创建了 {len(plan_videos)} 个视频任务")
                        
                        # 立即执行一次任务处理，避免等待下一次轮询
                        print(f"[TASK POLL] 立即处理新创建的视频任务，避免延迟")
                        self._process_video_tasks(db)
                        
                    except Exception as e:
                        print(f"[TASK POLL] 处理发布计划 {plan.id} 错误: {e}")
                        import traceback
                        traceback.print_exc()
                        plan.status = 'failed'
                        plan.updated_at = now
                        db.commit()
            
            # 2. 处理定时发布任务（publish_date 已到的任务）
            now = datetime.now()
            scheduled_tasks = db.query(VideoTask).filter(
                VideoTask.status == 'pending',
                VideoTask.publish_date <= now
            ).all()
            
            if scheduled_tasks:
                print(f"[TASK POLL] 发现 {len(scheduled_tasks)} 个到期的定时发布任务")
                
                for task in scheduled_tasks:
                    try:
                        print(f"[TASK POLL] 处理定时发布任务: {task.video_title} (ID: {task.id})")
                        # 将任务的publish_date设置为None，变为立即发布任务
                        task.publish_date = None
                        db.commit()
                        print(f"[TASK POLL] 定时发布任务 {task.id} 已转为立即发布任务")
                    except Exception as e:
                        print(f"[TASK POLL] 处理定时发布任务 {task.id} 错误: {e}")
                        import traceback
                        traceback.print_exc()
            
            # 3. 处理立即发布任务
            self._process_video_tasks(db)
            
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

