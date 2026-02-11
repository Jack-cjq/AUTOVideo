"""
数据模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Text, Float, REAL, Boolean
from sqlalchemy.orm import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())
    
    def set_password(self, password):
        """设置密码（加密）"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)


class EmailVerification(Base):
    """???????????????"""
    __tablename__ = 'email_verifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())


class Device(Base):
    """设备表"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    device_name = Column(String(255))
    ip_address = Column(String(50))
    status = Column(String(50), default='offline')
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(), 
                       onupdate=lambda: __import__('datetime').datetime.now())


class Account(Base):
    """账号表"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    account_name = Column(String(255), nullable=False, index=True)
    platform = Column(String(50), default='douyin')
    cookie_file_path = Column(String(500))
    cookies = Column(Text)  # JSON字符串
    login_status = Column(String(50), default='logged_out')
    last_login_time = Column(DateTime)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class VideoTask(Base):
    """视频任务表"""
    __tablename__ = 'video_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    video_url = Column(String(1000), nullable=False)
    video_title = Column(String(500))
    video_tags = Column(String(500))
    publish_date = Column(DateTime)
    thumbnail_url = Column(String(1000))
    status = Column(String(50), default='pending')
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class ChatTask(Base):
    """对话任务表"""
    __tablename__ = 'chat_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    target_user = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class ListenTask(Base):
    """监听任务表"""
    __tablename__ = 'listen_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    action = Column(String(50), default='start')
    status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class Message(Base):
    """消息表"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, index=True)
    user_name = Column(String(255), nullable=False, index=True)
    text = Column(Text, nullable=False)
    is_me = Column(Integer, default=0)
    message_time = Column(String(100))
    timestamp = Column(DateTime, default=lambda: __import__('datetime').datetime.now(), index=True)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())


class PublishPlan(Base):
    """发布计划表"""
    __tablename__ = 'publish_plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(255), nullable=False)
    platform = Column(String(50), default='douyin')
    merchant_id = Column(Integer, ForeignKey('merchants.id'), nullable=True)
    video_count = Column(Integer, default=0)
    published_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    claimed_count = Column(Integer, default=0)
    account_count = Column(Integer, default=0)
    distribution_mode = Column(String(50), default='manual')  # manual, sms, qrcode, ai
    status = Column(String(50), default='pending')  # pending, publishing, completed, failed
    publish_time = Column(DateTime)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class PlanVideo(Base):
    """发布计划关联的视频表"""
    __tablename__ = 'plan_videos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey('publish_plans.id'), nullable=False)
    video_url = Column(String(1000), nullable=False)
    video_title = Column(String(500))
    thumbnail_url = Column(String(1000))
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())


class Merchant(Base):
    """商家表"""
    __tablename__ = 'merchants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_name = Column(String(255), nullable=False, unique=True)
    contact_person = Column(String(100))
    contact_phone = Column(String(50))
    contact_email = Column(String(100))
    address = Column(String(500))
    status = Column(String(50), default='active')  # active, inactive
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class VideoLibrary(Base):
    """云视频库表"""
    __tablename__ = 'video_library'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # 用户ID，用于数据隔离
    video_name = Column(String(255), nullable=False)
    video_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000))
    video_size = Column(Integer)  # 文件大小（字节）
    duration = Column(Integer)  # 视频时长（秒）
    platform = Column(String(50))  # 来源平台
    tags = Column(String(500))  # 标签，逗号分隔
    description = Column(Text)
    upload_time = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class AccountStats(Base):
    """账号统计数据表（用于数据中心）"""
    __tablename__ = 'account_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    stat_date = Column(DateTime, nullable=False)  # 统计日期
    platform = Column(String(50), default='douyin')
    followers = Column(Integer, default=0)  # 粉丝数
    playbacks = Column(Integer, default=0)  # 播放量
    likes = Column(Integer, default=0)  # 点赞数
    comments = Column(Integer, default=0)  # 评论数
    shares = Column(Integer, default=0)  # 分享数
    published_videos = Column(Integer, default=0)  # 发布视频数
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())


class Material(Base):
    """素材表（视频/音频素材）"""
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)  # 文件名
    status = Column(String(50), default='ready')  # ready/processing/failed
    path = Column(String(500), nullable=True)  # 当前可用的文件路径（相对 BASE_DIR）
    original_path = Column(String(500), nullable=True)  # 仅当发生转码时保留（方案C）
    meta_json = Column(Text, nullable=True)  # ffprobe 结果摘要，便于排查/展示
    type = Column(String(50), nullable=False)  # video/audio
    duration = Column(REAL)  # 时长（秒），使用 REAL 支持小数
    width = Column(Integer)  # 宽（视频）
    height = Column(Integer)  # 高（视频）
    size = Column(Integer)  # 文件大小（字节）
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class VideoEditTask(Base):
    """视频剪辑任务表"""
    __tablename__ = 'video_edit_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # 用户ID，用于数据隔离
    video_ids = Column(Text, nullable=False)  # 视频ID列表，逗号分隔
    voice_id = Column(Integer, nullable=True)  # 配音音频ID
    bgm_id = Column(Integer, nullable=True)  # BGM音频ID
    speed = Column(Float, default=1.0)  # 播放速度（1.0=正常速度）
    subtitle_path = Column(String(1000), nullable=True)  # 字幕文件路径
    output_path = Column(String(1000), nullable=True)  # 输出文件路径（相对路径）
    output_filename = Column(String(255), nullable=True)  # 输出文件名
    preview_url = Column(String(1000), nullable=True)  # 预览URL
    status = Column(String(50), default='pending')  # pending/running/success/fail
    progress = Column(Integer, default=0)  # 进度（0-100）
    error_message = Column(Text, nullable=True)  # 错误信息
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now(),
                       onupdate=lambda: __import__('datetime').datetime.now())


class MaterialTranscodeTask(Base):
    """素材转码任务表（DB 队列）"""
    __tablename__ = 'material_transcode_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False, index=True)

    input_path = Column(String(500), nullable=False)  # 原始文件相对路径
    output_path = Column(String(500), nullable=False)  # 转码产物相对路径
    kind = Column(String(50), nullable=False)  # video/audio

    status = Column(String(50), default='pending')  # pending/running/success/fail
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)

    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    locked_by = Column(String(100), nullable=True)
    locked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.now())
    updated_at = Column(
        DateTime,
        default=lambda: __import__('datetime').datetime.now(),
        onupdate=lambda: __import__('datetime').datetime.now(),
    )


# 创建索引
Index('idx_messages_account_id', Message.account_id)
Index('idx_messages_timestamp', Message.timestamp)
Index('idx_messages_user_name', Message.user_name)
Index('idx_publish_plans_status', PublishPlan.status)
Index('idx_publish_plans_platform', PublishPlan.platform)
Index('idx_account_stats_account_date', AccountStats.account_id, AccountStats.stat_date)
Index('idx_materials_type_time', Material.type, Material.created_at)
Index('idx_materials_status_time', Material.status, Material.updated_at)
# 注意：path 字段的唯一性由应用层保证，因为 MySQL 对长字段的唯一索引有限制
# 如果需要数据库层面的唯一性，可以考虑使用哈希字段或缩短路径长度
Index('idx_video_edit_tasks_status_time', VideoEditTask.status, VideoEditTask.created_at)
Index('idx_video_edit_tasks_update_time', VideoEditTask.updated_at)

Index('idx_material_transcode_tasks_status_time', MaterialTranscodeTask.status, MaterialTranscodeTask.created_at)
Index('idx_material_transcode_tasks_lock', MaterialTranscodeTask.status, MaterialTranscodeTask.locked_at)

