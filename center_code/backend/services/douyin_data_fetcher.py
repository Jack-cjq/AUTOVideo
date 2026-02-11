"""
抖音视频数据获取服务
使用 cookies 从抖音创作者中心获取视频详细数据（播放量、点赞数、评论数、分享数等）
"""
import os
import json
import asyncio
import tempfile
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page
from sqlalchemy.orm import Session

from services.config import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from services.task_executor import get_account_from_db, save_cookies_to_temp
from utils.base_social_media import set_init_script
from utils.log import douyin_logger


async def fetch_video_data_from_douyin(account_id: int, db: Session, max_videos: int = 100) -> List[Dict]:
    """
    从抖音创作者中心获取视频详细数据
    
    Args:
        account_id: 账号ID
        db: 数据库会话
        max_videos: 最大获取视频数量，默认100
        
    Returns:
        List[Dict]: 视频数据列表，每个视频包含：
            - video_id: 视频ID
            - title: 视频标题
            - publish_time: 发布时间
            - playbacks: 播放量
            - likes: 点赞数
            - comments: 评论数
            - shares: 分享数
            - video_url: 视频链接
    """
    try:
        # 从数据库获取账号信息
        account_info = get_account_from_db(account_id, db)
        if not account_info:
            douyin_logger.error(f"账号 {account_id} 不存在")
            return []
        
        cookies_json = account_info.get('cookies')
        if not cookies_json:
            douyin_logger.error(f"账号 {account_id} 没有 cookies")
            return []
        
        # 解析 cookies
        if isinstance(cookies_json, str):
            cookies_data = json.loads(cookies_json)
        else:
            cookies_data = cookies_json
        
        # 保存 cookies 到临时文件
        account_file = save_cookies_to_temp(cookies_data, account_id)
        
        douyin_logger.info(f"开始获取账号 {account_id} 的视频数据...")
        
        # 使用 Playwright 获取视频数据
        async with async_playwright() as playwright:
            # 启动浏览器
            if LOCAL_CHROME_PATH and os.path.exists(LOCAL_CHROME_PATH):
                browser = await playwright.chromium.launch(
                    headless=LOCAL_CHROME_HEADLESS,
                    executable_path=LOCAL_CHROME_PATH
                )
            else:
                browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
            
            # 创建浏览器上下文
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            
            try:
                # 访问作品管理页面
                douyin_logger.info("正在访问作品管理页面...")
                await page.goto("https://creator.douyin.com/creator-micro/content/manage", wait_until="domcontentloaded")
                await asyncio.sleep(3)  # 等待页面加载
                
                # 检查是否需要登录
                login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                if login_check > 0:
                    douyin_logger.warning("检测到登录页面，cookies 可能已失效")
                    await context.close()
                    await browser.close()
                    return []
                
                # 等待视频列表加载
                douyin_logger.info("等待视频列表加载...")
                try:
                    # 等待视频列表容器出现
                    await page.wait_for_selector('[class*="content-list"], [class*="video-list"], [class*="item"]', timeout=10000)
                except Exception as e:
                    douyin_logger.warning(f"等待视频列表超时: {e}")
                
                await asyncio.sleep(2)
                
                # 获取视频数据
                videos = await _extract_video_data(page, max_videos)
                
                douyin_logger.info(f"成功获取 {len(videos)} 个视频的数据")
                
                # 保存更新后的 cookies（如果有更新）
                try:
                    await context.storage_state(path=account_file)
                    # 更新数据库中的 cookies
                    from services.task_executor import save_cookies_to_db
                    with open(account_file, 'r', encoding='utf-8') as f:
                        updated_cookies = json.load(f)
                    save_cookies_to_db(account_id, updated_cookies, db)
                except Exception as e:
                    douyin_logger.warning(f"更新 cookies 失败: {e}")
                
                return videos
                
            except Exception as e:
                douyin_logger.error(f"获取视频数据时出错: {e}")
                return []
            finally:
                await context.close()
                await browser.close()
                # 清理临时文件
                try:
                    if os.path.exists(account_file):
                        os.remove(account_file)
                except Exception:
                    pass
                    
    except Exception as e:
        douyin_logger.error(f"获取视频数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []


async def _extract_video_data(page: Page, max_videos: int) -> List[Dict]:
    """
    从页面中提取视频数据
    
    Args:
        page: Playwright 页面对象
        max_videos: 最大获取视频数量
        
    Returns:
        List[Dict]: 视频数据列表
    """
    videos = []
    
    try:
        # 尝试多种选择器来定位视频列表
        video_selectors = [
            '[class*="content-item"]',
            '[class*="video-item"]',
            '[class*="item-card"]',
            'div[class*="list-item"]',
            'div[class*="card"]',
        ]
        
        video_elements = None
        for selector in video_selectors:
            try:
                video_elements = await page.query_selector_all(selector)
                if video_elements and len(video_elements) > 0:
                    douyin_logger.info(f"使用选择器 {selector} 找到 {len(video_elements)} 个视频元素")
                    break
            except Exception:
                continue
        
        if not video_elements or len(video_elements) == 0:
            # 如果找不到视频元素，尝试通过页面内容解析
            douyin_logger.info("尝试通过页面内容解析视频数据...")
            videos = await _parse_videos_from_page_content(page, max_videos)
            return videos
        
        # 限制视频数量
        video_elements = video_elements[:max_videos]
        
        # 提取每个视频的数据
        for idx, element in enumerate(video_elements):
            try:
                video_data = await _extract_single_video_data(page, element, idx)
                if video_data:
                    videos.append(video_data)
            except Exception as e:
                douyin_logger.warning(f"提取第 {idx+1} 个视频数据失败: {e}")
                continue
        
        # 如果通过元素提取失败，尝试通过页面内容解析
        if len(videos) == 0:
            douyin_logger.info("元素提取失败，尝试通过页面内容解析...")
            videos = await _parse_videos_from_page_content(page, max_videos)
        
    except Exception as e:
        douyin_logger.error(f"提取视频数据时出错: {e}")
        import traceback
        traceback.print_exc()
    
    return videos


async def _extract_single_video_data(page: Page, element, index: int) -> Optional[Dict]:
    """
    提取单个视频的数据
    
    Args:
        page: Playwright 页面对象
        element: 视频元素
        index: 视频索引
        
    Returns:
        Optional[Dict]: 视频数据
    """
    try:
        # 获取视频标题
        title = ""
        title_selectors = [
            '[class*="title"]',
            '[class*="name"]',
            'a[class*="title"]',
            'span[class*="title"]',
        ]
        for selector in title_selectors:
            try:
                title_elem = await element.query_selector(selector)
                if title_elem:
                    title = await title_elem.inner_text()
                    if title:
                        break
            except Exception:
                continue
        
        # 获取发布时间
        publish_time = None
        time_selectors = [
            '[class*="time"]',
            '[class*="date"]',
            'span[class*="time"]',
        ]
        for selector in time_selectors:
            try:
                time_elem = await element.query_selector(selector)
                if time_elem:
                    time_text = await time_elem.inner_text()
                    if time_text:
                        publish_time = _parse_time_string(time_text)
                        break
            except Exception:
                continue
        
        # 获取统计数据（播放量、点赞数、评论数、分享数）
        stats = await _extract_video_stats(element)
        
        # 获取视频链接
        video_url = ""
        link_selectors = [
            'a[href*="/video/"]',
            'a[href*="/creator-micro/content/"]',
            'a',
        ]
        for selector in link_selectors:
            try:
                link_elem = await element.query_selector(selector)
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            video_url = f"https://creator.douyin.com{href}"
                        else:
                            video_url = href
                        break
            except Exception:
                continue
        
        return {
            'video_id': f"video_{index}",
            'title': title.strip() if title else f"视频 {index + 1}",
            'publish_time': publish_time,
            'playbacks': stats.get('playbacks', 0),
            'likes': stats.get('likes', 0),
            'comments': stats.get('comments', 0),
            'shares': stats.get('shares', 0),
            'video_url': video_url,
        }
        
    except Exception as e:
        douyin_logger.warning(f"提取单个视频数据失败: {e}")
        return None


async def _extract_video_stats(element) -> Dict:
    """
    提取视频统计数据
    
    Args:
        element: 视频元素
        
    Returns:
        Dict: 统计数据
    """
    stats = {
        'playbacks': 0,
        'likes': 0,
        'comments': 0,
        'shares': 0,
    }
    
    try:
        # 获取元素的所有文本内容
        text_content = await element.inner_text()
        
        # 尝试匹配统计数据
        # 播放量：通常包含"播放"或数字后跟"万"、"k"等
        import re
        
        # 匹配播放量（可能包含"播放"、"观看"等关键词）
        playback_patterns = [
            r'(\d+(?:\.\d+)?)[万千]?\s*播放',
            r'播放[：:]\s*(\d+(?:\.\d+)?)[万千]?',
            r'(\d+(?:\.\d+)?)[万千]?\s*次播放',
        ]
        for pattern in playback_patterns:
            match = re.search(pattern, text_content)
            if match:
                value = match.group(1)
                stats['playbacks'] = _parse_number(value)
                break
        
        # 匹配点赞数
        like_patterns = [
            r'(\d+(?:\.\d+)?)[万千]?\s*点赞',
            r'点赞[：:]\s*(\d+(?:\.\d+)?)[万千]?',
            r'(\d+(?:\.\d+)?)[万千]?\s*个赞',
        ]
        for pattern in like_patterns:
            match = re.search(pattern, text_content)
            if match:
                value = match.group(1)
                stats['likes'] = _parse_number(value)
                break
        
        # 匹配评论数
        comment_patterns = [
            r'(\d+(?:\.\d+)?)[万千]?\s*评论',
            r'评论[：:]\s*(\d+(?:\.\d+)?)[万千]?',
            r'(\d+(?:\.\d+)?)[万千]?\s*条评论',
        ]
        for pattern in comment_patterns:
            match = re.search(pattern, text_content)
            if match:
                value = match.group(1)
                stats['comments'] = _parse_number(value)
                break
        
        # 匹配分享数
        share_patterns = [
            r'(\d+(?:\.\d+)?)[万千]?\s*分享',
            r'分享[：:]\s*(\d+(?:\.\d+)?)[万千]?',
            r'(\d+(?:\.\d+)?)[万千]?\s*次分享',
        ]
        for pattern in share_patterns:
            match = re.search(pattern, text_content)
            if match:
                value = match.group(1)
                stats['shares'] = _parse_number(value)
                break
        
        # 如果通过文本匹配失败，尝试查找统计元素
        stat_selectors = [
            '[class*="stat"]',
            '[class*="data"]',
            '[class*="count"]',
            'span[class*="number"]',
        ]
        
        for selector in stat_selectors:
            try:
                stat_elements = await element.query_selector_all(selector)
                if stat_elements:
                    for stat_elem in stat_elements:
                        stat_text = await stat_elem.inner_text()
                        # 根据文本内容判断是哪种统计
                        if '播放' in stat_text or '观看' in stat_text:
                            stats['playbacks'] = _parse_number(stat_text)
                        elif '点赞' in stat_text or '赞' in stat_text:
                            stats['likes'] = _parse_number(stat_text)
                        elif '评论' in stat_text:
                            stats['comments'] = _parse_number(stat_text)
                        elif '分享' in stat_text:
                            stats['shares'] = _parse_number(stat_text)
            except Exception:
                continue
                
    except Exception as e:
        douyin_logger.warning(f"提取统计数据失败: {e}")
    
    return stats


async def _parse_videos_from_page_content(page: Page, max_videos: int) -> List[Dict]:
    """
    通过页面内容解析视频数据（备用方法）
    
    Args:
        page: Playwright 页面对象
        max_videos: 最大获取视频数量
        
    Returns:
        List[Dict]: 视频数据列表
    """
    videos = []
    
    try:
        # 获取页面内容
        content = await page.content()
        
        # 使用正则表达式或 JSON 解析来提取数据
        # 抖音页面可能包含 JSON 数据
        import re
        
        # 尝试查找 JSON 数据
        json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.+?});'
        match = re.search(json_pattern, content, re.DOTALL)
        
        if match:
            try:
                json_data = json.loads(match.group(1))
                # 从 JSON 中提取视频数据
                videos = _extract_videos_from_json(json_data, max_videos)
            except Exception:
                pass
        
        # 如果 JSON 解析失败，尝试从 HTML 中提取
        if len(videos) == 0:
            # 这里可以添加更多的 HTML 解析逻辑
            pass
            
    except Exception as e:
        douyin_logger.warning(f"通过页面内容解析失败: {e}")
    
    return videos


def _extract_videos_from_json(json_data: Dict, max_videos: int) -> List[Dict]:
    """
    从 JSON 数据中提取视频信息
    
    Args:
        json_data: JSON 数据
        max_videos: 最大获取视频数量
        
    Returns:
        List[Dict]: 视频数据列表
    """
    videos = []
    
    try:
        # 根据抖音页面的实际 JSON 结构来提取数据
        # 这里需要根据实际页面结构调整
        # 示例结构（需要根据实际情况调整）:
        # json_data['content']['videoList'] 或类似路径
        
        # 递归查找视频列表
        def find_video_list(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    if 'video' in key.lower() or 'content' in key.lower():
                        if isinstance(value, list):
                            return value
                    result = find_video_list(value, f"{path}.{key}")
                    if result:
                        return result
            elif isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    # 检查是否包含视频相关字段
                    first_item = data[0]
                    if any(key in first_item for key in ['title', 'video_id', 'aweme_id', 'play_count']):
                        return data
                for item in data:
                    result = find_video_list(item, path)
                    if result:
                        return result
            return None
        
        video_list = find_video_list(json_data)
        
        if video_list:
            for item in video_list[:max_videos]:
                video_data = {
                    'video_id': item.get('aweme_id') or item.get('video_id') or item.get('id', ''),
                    'title': item.get('title') or item.get('desc') or item.get('description', ''),
                    'publish_time': item.get('create_time') or item.get('publish_time'),
                    'playbacks': item.get('statistics', {}).get('play_count') or item.get('play_count') or 0,
                    'likes': item.get('statistics', {}).get('digg_count') or item.get('like_count') or 0,
                    'comments': item.get('statistics', {}).get('comment_count') or item.get('comment_count') or 0,
                    'shares': item.get('statistics', {}).get('share_count') or item.get('share_count') or 0,
                    'video_url': item.get('video_url') or item.get('share_url') or '',
                }
                videos.append(video_data)
                
    except Exception as e:
        douyin_logger.warning(f"从 JSON 提取视频数据失败: {e}")
    
    return videos


def _parse_number(text: str) -> int:
    """
    解析数字字符串（支持"万"、"千"等单位）
    
    Args:
        text: 数字字符串，如 "1.5万"、"1000" 等
        
    Returns:
        int: 解析后的数字
    """
    try:
        import re
        # 移除所有非数字、小数点、万、千的字符
        text = re.sub(r'[^\d.万千]', '', text)
        
        if '万' in text:
            number = float(re.sub(r'[万千]', '', text))
            return int(number * 10000)
        elif '千' in text:
            number = float(re.sub(r'[千]', '', text))
            return int(number * 1000)
        else:
            return int(float(text))
    except Exception:
        return 0


def _parse_time_string(time_str: str) -> Optional[str]:
    """
    解析时间字符串
    
    Args:
        time_str: 时间字符串
        
    Returns:
        Optional[str]: ISO 格式的时间字符串
    """
    try:
        # 尝试解析各种时间格式
        try:
            from dateutil import parser
            dt = parser.parse(time_str)
            return dt.isoformat()
        except ImportError:
            # 如果 dateutil 未安装，使用简单的解析
            from datetime import datetime
            # 尝试常见格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            return time_str
    except Exception:
        # 如果解析失败，返回原始字符串
        return time_str

