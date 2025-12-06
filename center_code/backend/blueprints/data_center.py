"""
数据中心API
"""
from flask import Blueprint, request
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Account, AccountStats, VideoTask
from db import get_db

data_center_bp = Blueprint('data_center', __name__, url_prefix='/api/data-center')


@data_center_bp.route('/video-stats', methods=['GET'])
@login_required
def get_video_stats():
    """
    获取视频数据统计接口
    
    请求方法: GET
    路径: /api/data-center/video-stats
    认证: 需要登录
    
    查询参数:
        account_id (int, 可选): 账号ID，筛选指定账号的统计
        platform (string, 可选): 平台类型，筛选指定平台的统计（douyin/kuaishou/xiaohongshu）
        start_date (string, 可选): 开始日期（ISO 格式），如未指定则默认最近7天
        end_date (string, 可选): 结束日期（ISO 格式），如未指定则默认最近7天
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "authorized_accounts": int,    # 授权账号数
                "published_videos": int,       # 已发布视频数
                "total_followers": int,        # 总粉丝数
                "playbacks": int,              # 播放量
                "likes": int,                 # 点赞数
                "comments": int,              # 评论数
                "net_followers": int,          # 净增粉丝数（待实现）
                "shares": int,                # 分享数
                "pending_videos": int          # 待发布视频数
            }
        }
        
        失败 (500):
        {
            "code": 500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 统计数据来源于 AccountStats 表和 VideoTask 表
        - 如果未指定日期范围，默认统计最近7天的数据
        - net_followers（净增粉丝数）功能待实现
    """
    try:
        account_id = request.args.get('account_id', type=int)
        platform = request.args.get('platform')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        with get_db() as db:
            # 构建查询
            query = db.query(Account)
            
            if account_id:
                query = query.filter(Account.id == account_id)
            
            if platform:
                query = query.filter(Account.platform == platform)
            
            accounts = query.all()
            
            # 统计信息
            total_accounts = len(accounts)
            logged_in_accounts = len([a for a in accounts if a.login_status == 'logged_in'])
            
            # 统计视频任务
            video_query = db.query(VideoTask)
            if account_id:
                video_query = video_query.filter(VideoTask.account_id == account_id)
            
            total_videos = video_query.count()
            published_videos = video_query.filter(VideoTask.status == 'completed').count()
            pending_videos = video_query.filter(VideoTask.status.in_(['pending', 'uploading'])).count()
            
            # 获取账号统计数据
            stats_query = db.query(AccountStats)
            if account_id:
                stats_query = stats_query.filter(AccountStats.account_id == account_id)
            if platform:
                stats_query = stats_query.filter(AccountStats.platform == platform)
            
            # 如果指定了日期范围
            if start_date and end_date:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                stats_query = stats_query.filter(
                    AccountStats.stat_date >= start,
                    AccountStats.stat_date <= end
                )
            else:
                # 默认最近7天
                end = datetime.now()
                start = end - timedelta(days=7)
                stats_query = stats_query.filter(
                    AccountStats.stat_date >= start,
                    AccountStats.stat_date <= end
                )
            
            stats = stats_query.all()
            
            # 汇总统计数据
            total_followers = sum(s.followers for s in stats)
            total_playbacks = sum(s.playbacks for s in stats)
            total_likes = sum(s.likes for s in stats)
            total_comments = sum(s.comments for s in stats)
            total_shares = sum(s.shares for s in stats)
            
            # 计算净增粉丝（需要对比前后数据，这里简化处理）
            net_followers = 0  # TODO: 实现净增粉丝计算
            
            return response_success({
                'authorized_accounts': total_accounts,
                'published_videos': published_videos,
                'total_followers': total_followers,
                'playbacks': total_playbacks,
                'likes': total_likes,
                'comments': total_comments,
                'net_followers': net_followers,
                'shares': total_shares,
                'pending_videos': pending_videos
            })
    except Exception as e:
        return response_error(str(e), 500)


@data_center_bp.route('/account-stats', methods=['GET'])
@login_required
def get_account_stats():
    """
    获取账号统计数据接口
    
    请求方法: GET
    路径: /api/data-center/account-stats
    认证: 需要登录
    
    查询参数:
        account_id (int, 必填): 账号ID
        platform (string, 可选): 平台类型，筛选指定平台的统计
        days (int, 可选): 统计天数，默认 7
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "account_id": int,
                "stats": [
                    {
                        "date": "string",           # 统计日期（ISO 格式）
                        "followers": int,           # 粉丝数
                        "playbacks": int,           # 播放量
                        "likes": int,               # 点赞数
                        "comments": int,            # 评论数
                        "shares": int,              # 分享数
                        "published_videos": int     # 发布视频数
                    }
                ]
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - account_id 为必填参数，如果未提供返回 400 错误
        - 返回指定天数内的统计数据，按日期升序排列
    """
    try:
        account_id = request.args.get('account_id', type=int)
        platform = request.args.get('platform')
        days = request.args.get('days', type=int, default=7)
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        with get_db() as db:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            stats = db.query(AccountStats).filter(
                AccountStats.account_id == account_id,
                AccountStats.stat_date >= start_date,
                AccountStats.stat_date <= end_date
            ).order_by(AccountStats.stat_date.asc()).all()
            
            stats_list = []
            for stat in stats:
                stats_list.append({
                    'date': stat.stat_date.isoformat() if stat.stat_date else None,
                    'followers': stat.followers,
                    'playbacks': stat.playbacks,
                    'likes': stat.likes,
                    'comments': stat.comments,
                    'shares': stat.shares,
                    'published_videos': stat.published_videos
                })
            
            return response_success({
                'account_id': account_id,
                'stats': stats_list
            })
    except Exception as e:
        return response_error(str(e), 500)


@data_center_bp.route('/account-stats', methods=['POST'])
@login_required
def create_account_stat():
    """
    创建账号统计数据接口（占位接口，通常由定时任务调用）
    
    请求方法: POST
    路径: /api/data-center/account-stats
    认证: 需要登录
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "stat_date": "string",    # 必填，统计日期（ISO 格式）
            "platform": "string",     # 可选，平台类型
            "followers": int,         # 可选，粉丝数
            "playbacks": int,         # 可选，播放量
            "likes": int,             # 可选，点赞数
            "comments": int,          # 可选，评论数
            "shares": int,            # 可选，分享数
            "published_videos": int   # 可选，发布视频数
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Stat created",
            "data": {
                "message": "Account stat created (placeholder)"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口为占位接口，具体实现待开发
        - 通常由定时任务调用，用于定期更新账号统计数据
        - account_id 和 stat_date 为必填参数
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        stat_date = data.get('stat_date')
        
        if not account_id or not stat_date:
            return response_error('account_id and stat_date are required', 400)
        
        # TODO: 实现统计数据创建逻辑
        return response_success({'message': 'Account stat created (placeholder)'}, 'Stat created', 201)
    except Exception as e:
        return response_error(str(e), 500)

