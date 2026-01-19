"""
后台任务处理器
按需处理待处理的任务，定时任务使用轻量级定时检查
"""
import threading
import time
from datetime import datetime
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
    """任务处理器（定时任务使用轻量级定时检查，其他任务按需触发）"""
    
    def __init__(self, poll_interval: int = None):
        """
        初始化任务处理器
        
        Args:
            poll_interval: 定时任务检查间隔（秒），默认 60 秒（1分钟）
        """
        self.poll_interval = poll_interval or 60  # 默认1分钟检查一次定时任务
        self.is_running = False
        self.thread = None
    
    def start(self):
        """启动定时任务检查器（轻量级，只检查定时任务）"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._schedule_check_loop, daemon=True)
        self.thread.start()
        print(f"定时任务检查器已启动，每 {self.poll_interval} 秒检查一次定时任务")
    
    def stop(self):
        """停止定时任务检查器"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _schedule_check_loop(self):
        """定时任务检查循环（轻量级，只检查定时任务）"""
        while self.is_running:
            try:
                self._check_scheduled_tasks()
            except Exception as e:
                print(f"[定时检查] 检查定时任务时出错: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(self.poll_interval)
    
    def _check_scheduled_tasks(self):
        """检查并处理到期的定时任务（轻量级检查）"""
        with get_db() as db:
            now = datetime.now()
            
            # 1. 检查到期的发布计划
            publish_plans = db.query(PublishPlan).filter(
                PublishPlan.status == 'pending',
                PublishPlan.publish_time <= now,
                PublishPlan.publish_time.isnot(None)
            ).limit(10).all()  # 限制每次最多处理10个，避免阻塞
            
            if publish_plans:
                print(f"[定时检查] 发现 {len(publish_plans)} 个到期的发布计划，触发处理")
                # 触发完整处理（在后台线程中）
                def trigger_processing():
                    try:
                        self._process_pending_tasks()
                    except Exception as e:
                        print(f"[定时检查] 触发任务处理失败: {e}")
                
                thread = threading.Thread(target=trigger_processing, daemon=True)
                thread.start()
            
            # 2. 检查到期的 VideoTask 定时发布任务
            # 设计思路：一旦到达发布时间，就把这些任务当作“立即发布”来处理
            # 做法：将 publish_date 置为空，让它们走与立即发布相同的处理逻辑
            scheduled_tasks = db.query(VideoTask).filter(
                VideoTask.status == 'pending',
                VideoTask.publish_date <= now,
                VideoTask.publish_date.isnot(None)
            ).limit(10).all()  # 限制每次最多处理10个
            
            if scheduled_tasks:
                print(f"[定时检查] 发现 {len(scheduled_tasks)} 个到期的定时发布任务，转为立即发布并触发处理")
                
                # 将这些任务的 publish_date 清空，让它们与“立即发布”任务使用同一套逻辑
                for task in scheduled_tasks:
                    task.publish_date = None
                db.commit()
                
                # 触发完整处理（在后台线程中），内部会按“立即发布”逻辑处理这些任务
                def trigger_processing():
                    try:
                        self._process_pending_tasks()
                    except Exception as e:
                        print(f"[定时检查] 触发任务处理失败: {e}")
                
                thread = threading.Thread(target=trigger_processing, daemon=True)
                thread.start()
    
    def _process_video_tasks(self, db: Session):
        """处理立即发布的视频任务"""
        # 排除已完成的任务（status='completed'）和未到期的定时发布任务（publish_date 不为 None）
        # 只处理 pending、uploading 状态的任务（failed 任务由上层逻辑决定是否重置为 pending）
        video_tasks = db.query(VideoTask).filter(
            VideoTask.status != 'completed',  # 排除已完成的任务
            VideoTask.publish_date.is_(None)  # 排除定时发布任务（publish_date 不为 None 的）
        ).filter(
            VideoTask.status.in_(['pending', 'uploading'])
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
                # 如果任务已经开始超过一定时间还没完成，可能是卡住了，重新处理
                elapsed_seconds = (datetime.now() - task.started_at).total_seconds()
                # 阈值从 10 分钟改为 3 分钟，加快卡死任务的自动恢复
                if elapsed_seconds < 180:  # 3分钟内，认为正在处理中
                    print(f"[TASK POLL] 任务 {task.id} 正在处理中（已运行 {int(elapsed_seconds)} 秒），跳过")
                    continue
                else:
                    # 任务可能卡住了，重置状态
                    print(f"[TASK POLL] ⚠️ 任务 {task.id} 可能卡住了（已运行 {int(elapsed_seconds)} 秒），重置为 pending 状态，准备重新发布")
                    task.status = 'pending'
                    task.started_at = None
                    task.error_message = None
                    db.commit()
            
            # 立即更新任务状态为 uploading，避免重复处理
            # 注意：这里需要刷新对象以确保获取最新状态
            db.refresh(task)
            if task.status != 'pending':
                print(f"[TASK POLL] 任务 {task.id} 当前状态为 {task.status}（非 pending），跳过（可能已被其他进程处理或已重置）")
                continue
            
            try:
                # 立即更新任务状态为 uploading，防止重复处理
                # 注意：不设置 started_at，让任务执行器来设置，避免时序问题
                task.status = 'uploading'
                task.progress = 0
                # 不设置 started_at，让 execute_video_upload 来设置
                db.commit()
                print(f"[TASK POLL] 任务 {task.id} 状态已更新为 uploading，准备启动")
                
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
            # 排除已完成、失败和正在处理中的计划，避免重复处理
            now = datetime.now()
            publish_plans = db.query(PublishPlan).filter(
                PublishPlan.status == 'pending',
                PublishPlan.publish_time <= now,
                PublishPlan.publish_time.isnot(None)  # 确保有发布时间
            ).all()
            
            if publish_plans:
                print(f"[TASK POLL] 发现 {len(publish_plans)} 个到期的发布计划")
                
                for plan in publish_plans:
                    try:
                        # 双重检查：确保计划状态仍然是pending（防止并发处理）
                        db.refresh(plan)
                        if plan.status != 'pending':
                            print(f"[TASK POLL] 发布计划 {plan.id} 状态已变更为 {plan.status}，跳过处理（可能已被其他进程处理）")
                            continue
                        
                        print(f"[TASK POLL] 处理发布计划: {plan.plan_name} (ID: {plan.id})")
                        # 更新计划状态为publishing（防止重复处理）
                        plan.status = 'publishing'
                        plan.updated_at = now
                        db.commit()
                        
                        # 获取计划关联的视频（只处理状态为pending的视频，避免重复发布）
                        plan_videos = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id,
                            PlanVideo.status == 'pending'  # 只处理未发布的视频
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
                                
                                # 检查是否已经存在相同的任务（相同的video_url和account_id，且状态不是completed）
                                existing_task = db.query(VideoTask).filter(
                                    VideoTask.video_url == video.video_url,
                                    VideoTask.account_id == account.id,
                                    VideoTask.status != 'completed'
                                ).first()
                                
                                if existing_task:
                                    print(f"[TASK POLL] 视频任务已存在（任务ID: {existing_task.id}, 状态: {existing_task.status}），处理策略中: {video.video_url}")
                                    
                                    # 如果任务已经在队列中待处理或正在处理中，视频标记为 processing，等待任务执行即可
                                    if existing_task.status in ['pending', 'uploading']:
                                        video.status = 'processing'
                                        continue
                                    
                                    # 如果任务之前失败了，则重置该任务为 pending，允许重新发布
                                    if existing_task.status == 'failed':
                                        print(f"[TASK POLL] 任务 {existing_task.id} 之前失败，本次将重置为 pending 重新发布")
                                        existing_task.status = 'pending'
                                        existing_task.started_at = None
                                        existing_task.completed_at = None
                                        existing_task.error_message = None
                                        video.status = 'processing'
                                        # 不再 continue，后续统计和任务处理会把该任务当作新的待处理任务
                                        continue
                                
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
                                
                                # 更新视频状态为 processing（处理中），等待任务完成后更新为 published
                                video.status = 'processing'
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
                        
                        # 统计处理中的视频数量
                        processing_count = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id,
                            PlanVideo.status == 'processing'
                        ).count()
                        
                        # 统计失败的视频数量
                        failed_count = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id,
                            PlanVideo.status == 'failed'
                        ).count()
                        
                        # 统计待处理的视频数量
                        pending_count = db.query(PlanVideo).filter(
                            PlanVideo.plan_id == plan.id,
                            PlanVideo.status == 'pending'
                        ).count()
                        
                        plan.published_count = published_count
                        plan.pending_count = pending_count
                        plan.updated_at = now
                        
                        # 只有当所有视频都已处理完成（没有 pending 和 processing 状态）时，才标记计划为 completed
                        if pending_count == 0 and processing_count == 0:
                            plan.status = 'completed'
                            print(f"[TASK POLL] 发布计划 {plan.id} 所有视频已处理完成，状态更新为 completed")
                        else:
                            # 还有视频在处理中，保持 publishing 状态
                            print(f"[TASK POLL] 发布计划 {plan.id} 还有视频在处理中（pending: {pending_count}, processing: {processing_count}），保持 publishing 状态")
                        
                        db.commit()
                        
                        print(f"[TASK POLL] 发布计划 {plan.id} 已创建 {len(plan_videos)} 个视频任务，统计：已发布={published_count}, 处理中={processing_count}, 失败={failed_count}, 待处理={pending_count}")
                        # 注意：不在这里立即处理视频任务，避免重复处理
                        # 视频任务会在 _process_pending_tasks 的最后统一处理
                        
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
        _task_processor = TaskProcessor()
    return _task_processor

