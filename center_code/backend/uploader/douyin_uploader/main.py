# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import douyin_logger


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def douyin_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await douyin_cookie_gen(account_file)
    return True


async def douyin_cookie_gen(account_file):
    """生成 cookies（旧版本，使用 pause）"""
    async with async_playwright() as playwright:
        options = {
            'headless': LOCAL_CHROME_HEADLESS
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


async def douyin_auto_login(account_id: int = None, timeout: int = 300) -> dict:
    """
    自动登录流程：打开浏览器让用户扫码登录，登录成功后返回新的 cookies
    
    Args:
        account_id: 账号ID（可选，用于日志）
        timeout: 超时时间（秒），默认5分钟
    
    Returns:
        dict: 新的 storage_state 格式的 cookies 数据
    
    Raises:
        Exception: 如果登录超时或失败
    """
    douyin_logger.info(f"[LOGIN] 开始自动登录流程{' (账号ID: ' + str(account_id) + ')' if account_id else ''}")
    douyin_logger.info("[LOGIN] 正在打开浏览器，请扫码登录...")
    
    # 确保使用非 headless 模式，让用户看到浏览器
    launch_options = {
        'headless': False,  # 强制非 headless，让用户看到登录页面
        'slow_mo': 100  # 减慢操作速度，更接近人类行为
    }
    if LOCAL_CHROME_PATH and os.path.exists(LOCAL_CHROME_PATH):
        launch_options['executable_path'] = LOCAL_CHROME_PATH
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch_options)
        
        try:
            # 创建浏览器上下文
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )
            context = await set_init_script(context)
            
            # 创建页面
            page = await context.new_page()
            page.set_default_navigation_timeout(60000)
            
            # 访问登录页面
            douyin_logger.info("[LOGIN] 正在访问抖音创作者中心...")
            await page.goto("https://creator.douyin.com/", wait_until="domcontentloaded")
            
            # 等待用户登录（检测登录成功）
            douyin_logger.info("[LOGIN] 等待用户扫码登录...")
            douyin_logger.info("[LOGIN] 请在浏览器中扫码登录，登录成功后系统会自动继续")
            
            start_time = asyncio.get_event_loop().time()
            login_success = False
            
            # 轮询检查登录状态
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                await asyncio.sleep(2)  # 每2秒检查一次
                
                try:
                    current_url = page.url
                    
                    # 检查是否跳转到登录页面（说明还没登录）
                    if 'login' in current_url.lower() or 'passport' in current_url.lower():
                        # 还在登录页面，继续等待
                        continue
                    
                    # 检查是否在主页或上传页面（说明已登录）
                    if 'creator.douyin.com' in current_url and ('login' not in current_url.lower() and 'passport' not in current_url.lower()):
                        # 检查页面是否有登录元素
                        login_elements = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                        
                        if login_elements == 0:
                            # 没有登录元素，说明已登录成功
                            # 再等待一下，确保页面完全加载
                            await asyncio.sleep(2)
                            
                            # 最终确认：检查是否真的登录成功
                            final_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                            if final_check == 0:
                                login_success = True
                                douyin_logger.success("[LOGIN] 登录成功！正在保存 cookies...")
                                break
                except Exception as e:
                    douyin_logger.debug(f"[LOGIN] 检查登录状态时出错（继续等待）: {e}")
                    continue
            
            if not login_success:
                await browser.close()
                raise Exception(f"登录超时（{timeout}秒），请重试")
            
            # 登录成功，保存 cookies
            storage_state = await context.storage_state()
            
            # 验证 cookies 是否有效
            cookies_count = len(storage_state.get('cookies', []))
            origins_count = len(storage_state.get('origins', []))
            
            if cookies_count == 0 and origins_count == 0:
                await browser.close()
                raise Exception("登录成功但未获取到 cookies，请重试")
            
            douyin_logger.success(f"[LOGIN] Cookies 已获取: {cookies_count} cookies, {origins_count} origins")
            
            await browser.close()
            return storage_state
            
        except Exception as e:
            try:
                await browser.close()
            except:
                pass
            raise


class DouYinVideo(object):
    def __init__(self, title, file_path, tags, publish_date, account_file, thumbnail_path=None,
                 action_delay: float = 0.8, final_display_delay: float = 100.0, account_id: int = None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags if isinstance(tags, list) else (tags.split(',') if tags else [])  # 确保tags是列表
        # 记录日志，确保title和tags正确接收
        douyin_logger.info(f"DouYinVideo initialized - title: '{self.title}', tags: {self.tags}")
        self.publish_date = publish_date
        self.account_file = account_file
        self.account_id = account_id  # 账号ID，用于自动登录时保存cookies
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path
        self.action_delay = max(action_delay, 0.1)
        self.final_display_delay = max(final_display_delay, 0)

    async def _human_pause(self, multiplier: float = 1.0):
        """统一的操作延迟，避免页面响应过快导致元素未渲染。"""
        await asyncio.sleep(self.action_delay * multiplier)

    async def set_schedule_time_douyin(self, page, publish_date):
        # 选择包含特定文本内容的 label 元素
        await self._human_pause()
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await self._human_pause(1.5)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await self._human_pause()
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await self._human_pause()
        await page.keyboard.press("Control+KeyA")
        await self._human_pause()
        await page.keyboard.type(str(publish_date_hour))
        await self._human_pause()
        await page.keyboard.press("Enter")

        await self._human_pause()

    async def _handle_cookies_expired(self):
        """
        处理 cookies 失效：自动打开浏览器让用户登录，登录成功后更新 cookies
        """
        douyin_logger.info("[AUTO-LOGIN] 检测到 cookies 失效，开始自动登录流程...")
        
        try:
            # 调用自动登录函数
            new_cookies = await douyin_auto_login(account_id=self.account_id, timeout=300)
            
            # 保存新的 cookies 到临时文件
            import json
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
            json.dump(new_cookies, temp_file, ensure_ascii=False)
            temp_file.close()
            
            # 更新 account_file 路径
            self.account_file = temp_file.name
            douyin_logger.success(f"[AUTO-LOGIN] 登录成功，新的 cookies 已保存到: {self.account_file}")
            
            # 如果有 account_id，更新数据库中的 cookies
            if self.account_id:
                try:
                    from services.task_executor import save_cookies_to_db
                    from db import get_db
                    with get_db() as db:
                        save_cookies_to_db(self.account_id, new_cookies, db)
                    douyin_logger.success(f"[AUTO-LOGIN] Cookies 已更新到数据库 (账号ID: {self.account_id})")
                except Exception as e:
                    douyin_logger.warning(f"[AUTO-LOGIN] 更新数据库 cookies 失败: {e}")
            
        except Exception as e:
            douyin_logger.error(f"[AUTO-LOGIN] 自动登录失败: {e}")
            raise Exception(f"自动登录失败: {e}。请手动登录后重试。")
    
    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)
        await self._human_pause(2)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=self.headless)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        # 验证文件是否存在且格式正确
        import json
        import os
        if not os.path.exists(self.account_file):
            raise Exception(f"Cookies file not found: {self.account_file}")
        
        # 验证文件格式
        try:
            with open(self.account_file, 'r', encoding='utf-8') as f:
                storage_state = json.load(f)
                if not isinstance(storage_state, dict):
                    raise Exception(f"Invalid cookies file format: {self.account_file}")
                if 'cookies' not in storage_state and 'origins' not in storage_state:
                    douyin_logger.warning(f"Cookies file may be invalid: {self.account_file}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in cookies file {self.account_file}: {e}")
        
        douyin_logger.info(f"Loading cookies from: {self.account_file}")
        
        # 读取并验证 storage_state
        import json
        with open(self.account_file, 'r', encoding='utf-8') as f:
            storage_state_data = json.load(f)
        
        # 记录 cookies 和 origins 信息用于调试
        cookies_count = len(storage_state_data.get('cookies', []))
        origins_count = len(storage_state_data.get('origins', []))
        douyin_logger.info(f"[COOKIES DEBUG] Storage state loaded: {cookies_count} cookies, {origins_count} origins")
        
        # 检查关键 cookies
        cookie_names = [c.get('name', '') for c in storage_state_data.get('cookies', []) if isinstance(c, dict)]
        important_cookies = ['sessionid', 'passport_auth', 'passport_csrf_token', 'sid_guard', 'uid_tt', 'sid_tt']
        missing_important = [name for name in important_cookies if name not in cookie_names]
        if missing_important:
            douyin_logger.warning(f"[COOKIES DEBUG] Missing important cookies in storage_state: {missing_important}")
        
        # 使用更完整的浏览器上下文配置，模拟真实浏览器
        context = await browser.new_context(
            storage_state=self.account_file,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            # 增强浏览器指纹伪装
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            # 添加更多真实的浏览器特征
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            },
            # 添加权限，模拟真实浏览器
            permissions=['geolocation', 'notifications'],
            # 添加地理位置（可选）
            geolocation={'longitude': 116.3974, 'latitude': 39.9093},  # 北京
            color_scheme='light'
        )
        context = await set_init_script(context)
        
        # 在页面加载前，先访问一个简单的页面来"预热"cookies
        # 这可以帮助确保 cookies 正确加载
        page_prewarm = await context.new_page()
        try:
            douyin_logger.debug("[COOKIES DEBUG] Pre-warming cookies by visiting homepage...")
            await page_prewarm.goto("https://creator.douyin.com/", wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(1)  # 等待 cookies 完全加载
            douyin_logger.debug("[COOKIES DEBUG] Pre-warm completed")
        except Exception as e:
            douyin_logger.warning(f"[COOKIES DEBUG] Pre-warm failed (may be normal): {e}")
        finally:
            await page_prewarm.close()

        # 创建一个新的页面
        page = await context.new_page()
        
        # 关键改进：先访问主页，让 cookies 在正确的域名下加载
        # 这可以确保 cookies 的 domain 属性正确匹配，避免直接访问上传页面时 cookies 失效
        douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
        douyin_logger.info(f'[-] 先访问主页以激活 cookies...')
        page.set_default_navigation_timeout(30000)
        
        try:
            # 先访问主页，让 cookies 在 creator.douyin.com 域名下激活
            await page.goto("https://creator.douyin.com/", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)  # 等待 cookies 完全激活
            douyin_logger.debug('[-] 主页访问完成，cookies 已激活')
            
            # 检查是否在主页成功加载（而不是跳转到登录页）
            current_url = page.url
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                douyin_logger.warning(f'[-] 访问主页时被重定向到登录页: {current_url}')
                await browser.close()
                # 触发自动登录
                await self._handle_cookies_expired()
                # 登录成功后，重新创建浏览器上下文并重试
                return await self.upload(playwright)
            
            # 检查主页是否有登录元素
            login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
            if login_check > 0:
                douyin_logger.warning('[-] 主页显示登录页面，cookies已失效')
                await browser.close()
                # 触发自动登录
                await self._handle_cookies_expired()
                # 登录成功后，重新创建浏览器上下文并重试
                return await self.upload(playwright)
            
        except Exception as e:
            if "Cookies已失效" in str(e) or "重新登录" in str(e):
                try:
                    await browser.close()
                except:
                    pass
                # 触发自动登录
                await self._handle_cookies_expired()
                # 登录成功后，重新创建浏览器上下文并重试
                return await self.upload(playwright)
            douyin_logger.warning(f'[-] 访问主页时出现异常（继续尝试）: {e}')
        
        # 现在访问上传页面
        douyin_logger.info(f'[-] 正在打开上传页面...')
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        
        # 使用与 cookie_auth 完全相同的逻辑来验证 cookies
        douyin_logger.info('[-] 等待页面验证和加载...')
        
        # 等待 URL 稳定（与 cookie_auth 一致）
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=10000)
            douyin_logger.debug('[-] URL 已稳定')
        except Exception as e:
            douyin_logger.warning(f'[-] URL 未能在10秒内稳定: {e}')
            # 检查是否跳转到登录页面
            current_url = page.url
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                douyin_logger.warning('[-] 页面跳转到登录页面，cookies已失效，将自动登录...')
                await browser.close()
                # 触发自动登录
                await self._handle_cookies_expired()
                # 登录成功后，重新创建浏览器上下文并重试
                return await self.upload(playwright)
            else:
                douyin_logger.warning(f'[-] 页面未能加载到目标URL，当前URL: {current_url}，继续尝试...')
        
        # 额外等待页面完全加载（给抖音的反爬虫机制更多时间）
        douyin_logger.debug('[-] 等待页面完全加载...')
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            # 如果 networkidle 超时，至少等待 domcontentloaded
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass
        
        # 额外等待 3 秒，确保页面完全渲染（抖音页面可能需要更长时间）
        await asyncio.sleep(3)
        
        # 检查登录元素（与 cookie_auth 完全相同的逻辑）
        douyin_logger.debug('[-] 检查页面登录状态...')
        login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        
        if login_text_count > 0:
            # 如果检测到登录元素，再等待 3 秒并再次检查（避免误判）
            douyin_logger.debug('[-] 检测到可能的登录元素，等待 3 秒再次确认...')
            await asyncio.sleep(3)
            login_text_count_confirm = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
            if login_text_count_confirm > 0:
                # 最后确认：检查是否有上传页面的关键元素
                upload_elements = await page.locator('input[type="file"]').count()
                if upload_elements == 0:
                    # 获取当前URL用于诊断
                    current_url = page.url
                    douyin_logger.error('[-] 确认检测到登录页面元素且无上传元素，cookies已失效')
                    douyin_logger.error(f'[-] 当前页面URL: {current_url}')
                    douyin_logger.error('[-] 可能的原因：')
                    douyin_logger.error('[-] 1. Cookies不完整（缺少HttpOnly cookies，如sessionid、passport_auth等）')
                    douyin_logger.error('[-] 2. Cookies已过期')
                    douyin_logger.error('[-] 3. 授权页面和发布页面的验证机制不同')
                    douyin_logger.error('[-] 解决方案：使用Network标签页获取完整的cookies')
                    raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号。建议使用Network标签页获取完整的HttpOnly cookies。")
                else:
                    douyin_logger.info('[-] 虽然检测到登录元素，但上传元素也存在，继续...')
            else:
                douyin_logger.info('[-] 登录元素已消失，页面加载完成')
        else:
            douyin_logger.info('[-] 未检测到登录元素，页面加载成功')
        
        # 最终确认：检查上传页面的关键元素
        try:
            # 等待上传元素出现（最多等待 5 秒）
            await page.wait_for_selector('input[type="file"]', timeout=5000, state='attached')
            douyin_logger.info(f'[-] 成功进入上传页面: {page.url}')
        except:
            # 如果上传元素不存在，检查是否真的在登录页面
            login_text_count_final = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
            if login_text_count_final > 0:
                douyin_logger.error('[-] 最终确认：页面在登录页面，cookies已失效')
                raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号")
            else:
                douyin_logger.warning('[-] 上传元素未找到，但也不在登录页面，继续尝试...')
        
        # 最终检查：如果等待超时，再次确认当前状态
        final_url = page.url
        douyin_logger.info(f'[-] 最终页面URL: {final_url}')
        
        if 'login' in final_url.lower() or 'passport' in final_url.lower():
            douyin_logger.error(f'[-] 最终检测：页面在登录页面: {final_url}')
            raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号")
        
        # 再次确认不在登录页面
        try:
            login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
            if login_text_count > 0:
                douyin_logger.error('[-] 最终检测：发现登录页面元素，cookies已失效')
                raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号")
        except Exception as e:
            if "Cookies已失效" in str(e):
                raise
            # 元素不存在，说明不在登录页面，继续
            pass
        
        await self._human_pause()
        
        # 使用更精确的定位器：先查找上传容器，再找input
        # 尝试多种定位器，找到文件上传输入框
        file_input = None
        upload_selectors = [
            # 优先使用更精确的选择器
            "div[class*='upload'] input[type='file']",
            "div[class*='container'] input[type='file']",
            "input[type='file']",
            # 兼容旧版本
            "div[class^='container'] input",
        ]
        
        for selector in upload_selectors:
            try:
                count = await page.locator(selector).count()
                if count == 1:
                    file_input = page.locator(selector).first
                    douyin_logger.info(f'[-] 找到文件上传输入框，选择器: {selector}')
                    break
                elif count > 1:
                    douyin_logger.warning(f'[-] 选择器 {selector} 匹配到 {count} 个元素，尝试下一个')
                    continue
            except Exception as e:
                douyin_logger.debug(f'[-] 选择器 {selector} 失败: {e}')
                continue
        
        if not file_input:
            # 如果所有选择器都失败，检查是否在登录页面
            current_url = page.url
            page_content = await page.content()
            if '手机号登录' in page_content or '扫码登录' in page_content or 'login' in current_url.lower():
                raise Exception("Cookies已失效，无法找到文件上传输入框，页面可能已跳转到登录页面，请重新登录账号")
            else:
                raise Exception(f"无法找到文件上传输入框，当前URL: {current_url}")
        
        # 上传文件
        await file_input.set_input_files(self.file_path)
        await self._human_pause(2)

        # 等待页面跳转到指定的 URL 2025.01.08修改在原有基础上兼容两种页面
        while True:
            try:
                # 尝试等待第一个 URL
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page", timeout=3000)
                douyin_logger.info("[+] 成功进入version_1发布页面!")
                break  # 成功进入页面后跳出循环
            except Exception:
                try:
                    # 如果第一个 URL 超时，再尝试等待第二个 URL
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=3000)
                    douyin_logger.info("[+] 成功进入version_2发布页面!")

                    break  # 成功进入页面后跳出循环
                except:
                    print("  [-] 超时未进入视频发布页面，重新尝试...")
                    await asyncio.sleep(0.5)  # 等待 0.5 秒后重新尝试
        # 填充标题和话题
        # 检查是否存在包含输入框的元素
        # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
        await self._human_pause(1.5)
        douyin_logger.info(f'  [-] 正在填充标题和话题...')
        douyin_logger.info(f'  [-] 标题内容: "{self.title}"')
        douyin_logger.info(f'  [-] 标签列表: {self.tags}')
        
        # 先填充标题（确保标题不为空）
        if self.title and self.title.strip():
            title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
            if await title_container.count():
                await title_container.fill(self.title[:30])
                douyin_logger.info(f'  [-] 已填充标题到输入框: "{self.title[:30]}"')
                await self._human_pause()
            else:
                titlecontainer = page.locator(".notranslate")
                await titlecontainer.click()
                await self._human_pause()
                await page.keyboard.press("Backspace")
                await self._human_pause()
                await page.keyboard.press("Control+KeyA")
                await self._human_pause()
                await page.keyboard.press("Delete")
                await self._human_pause()
                await page.keyboard.type(self.title)
                await page.keyboard.press("Enter")
                douyin_logger.info(f'  [-] 已通过键盘输入标题: "{self.title}"')
                await self._human_pause()
        else:
            douyin_logger.warning('  [-] 标题为空，跳过标题填充')
        
        # 再填充标签（确保标签是列表且不为空）
        if self.tags and isinstance(self.tags, list) and len(self.tags) > 0:
            css_selector = ".zone-container"
            for index, tag in enumerate(self.tags, start=1):
                if tag and tag.strip():  # 确保标签不为空
                    await self._human_pause()
                    tag_text = tag.strip()
                    await page.type(css_selector, "#" + tag_text)
                    await page.press(css_selector, "Space")
                    douyin_logger.info(f'  [-] 已添加标签 {index}: #{tag_text}')
            douyin_logger.info(f'总共添加{len([t for t in self.tags if t and t.strip()])}个话题')
        else:
            douyin_logger.warning('  [-] 标签列表为空，跳过标签填充')
        while True:
            # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
            try:
                #  新版：定位重新上传
                number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    douyin_logger.success("  [-]视频上传完毕")
                    break
                else:
                    douyin_logger.info("  [-] 正在上传视频中...")
                    await self._human_pause(2.5)

                    if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                        douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                        await self.handle_upload_error(page)
            except:
                douyin_logger.info("  [-] 正在上传视频中...")
                await self._human_pause(2.5)

        #上传视频封面
        await self.set_thumbnail(page, self.thumbnail_path)

        # 更换可见元素
        await self.set_location(page, "")


        # 頭條/西瓜
        third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        # 定位是否有第三方平台
        if await page.locator(third_part_element).count():
            # 检测是否是已选中状态
            if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
                await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

        if self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            # 判断视频是否发布成功
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**",
                                        timeout=3000)  # 如果自动跳转到作品页面，则代表发布成功
                douyin_logger.success("  [-]视频发布成功")
                break
            except:
                douyin_logger.info("  [-] 视频正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)  # 保存cookie
        douyin_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(self.final_display_delay)  # 结束前额外等待，方便查看状态
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()
    
    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            douyin_logger.info('  [-] 正在设置视频封面...')
            await self._human_pause()
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.dy-creator-content-modal")
            await self._human_pause()
            await page.click('text="设置竖封面"')
            await self._human_pause(2)
            # 定位到上传区域并点击
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await self._human_pause(2)
            await page.locator("div#tooltip-container button:visible:has-text('完成')").click()
            await self._human_pause()
            # finish_confirm_element = page.locator("div[class^='confirmBtn'] >> div:has-text('完成')")
            # if await finish_confirm_element.count():
            #     await finish_confirm_element.click()
            # await page.locator("div[class^='footer'] button:has-text('完成')").click()
            douyin_logger.info('  [+] 视频封面设置完成！')
            # 等待封面设置对话框关闭
            await page.wait_for_selector("div.extractFooter", state='detached')
            

    async def set_location(self, page: Page, location: str = ""):
        if not location:
            return
        # todo supoort location later
        # await page.get_by_text('添加标签').locator("..").locator("..").locator("xpath=following-sibling::div").locator(
        #     "div.semi-select-single").nth(0).click()
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await self._human_pause()
        await page.keyboard.press("Backspace")
        await self._human_pause(2)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await self._human_pause()
        await page.locator('div[role="listbox"] [role="option"]').first.click()


    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)


