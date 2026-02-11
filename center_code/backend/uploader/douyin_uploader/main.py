# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, Union

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


class DouYinVideo(object):
    def __init__(self, title, file_path, tags, publish_date, account_file, thumbnail_path=None,
                 action_delay: float = 0.3, final_display_delay: float = 100.0, account_id: int = None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags if isinstance(tags, list) else (tags.split(',') if tags else [])  # 确保tags是列表
        # 记录日志，确保title和tags正确接收
        douyin_logger.info(f"DouYinVideo initialized - title: '{self.title}', tags: {self.tags}, account_id: {account_id}")
        self.publish_date = publish_date
        self.account_file = account_file
        self.account_id = account_id  # 账号ID，用于从数据库获取和更新cookies
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path
        self.action_delay = max(action_delay, 0.1)
        self.final_display_delay = max(final_display_delay, 0)

    async def _human_pause(self, multiplier: float = 1.0):
        """统一的操作延迟，避免页面响应过快导致元素未渲染。"""
        await asyncio.sleep(self.action_delay * multiplier)
    
    async def _wait_for_login(self, page, context, browser, max_wait_time: int = 300):
        """
        等待用户登录完成
        
        Args:
            page: Playwright 页面对象
            context: 浏览器上下文
            browser: 浏览器实例
            max_wait_time: 最大等待时间（秒），默认5分钟
        """
        douyin_logger.info("=" * 60)
        douyin_logger.info("⚠️  Cookies已失效，请扫码登录")
        douyin_logger.info("📱 浏览器将保持打开，请在页面中完成登录")
        douyin_logger.info(f"⏱️  系统将等待最多 {max_wait_time} 秒，等待您完成登录...")
        douyin_logger.info("=" * 60)
        
        start_time = asyncio.get_event_loop().time()
        check_interval = 3  # 每3秒检查一次
        
        while True:
            # 检查是否超时
            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time >= max_wait_time:
                douyin_logger.error(f"等待登录超时（{max_wait_time}秒），任务失败")
                await context.close()
                await browser.close()
                raise Exception(f"等待登录超时（{max_wait_time}秒），请重新尝试")
            
            # 等待一段时间后检查
            await asyncio.sleep(check_interval)
            
            try:
                # 检查当前URL是否已跳转到上传页面
                current_url = page.url
                if "creator.douyin.com/creator-micro/content/upload" in current_url:
                    # 再次检查登录元素是否消失
                    login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                    if login_check == 0:
                        douyin_logger.success("✅ 检测到登录成功，继续执行上传流程...")
                        
                        # 保存更新后的cookies
                        await context.storage_state(path=self.account_file)
                        douyin_logger.success('  [-] 登录后的cookies已保存到临时文件')
                        
                        # 如果提供了 account_id，更新数据库中的cookies
                        if self.account_id:
                            try:
                                import json
                                from db import get_db
                                from services.task_executor import save_cookies_to_db
                                
                                # 读取更新后的cookies
                                with open(self.account_file, 'r', encoding='utf-8') as f:
                                    updated_cookies = json.load(f)
                                
                                # 更新到数据库
                                with get_db() as db:
                                    save_cookies_to_db(self.account_id, updated_cookies, db)
                                douyin_logger.success(f'  [-] 账号 {self.account_id} 的 cookies 已更新到数据库')
                            except Exception as e:
                                douyin_logger.warning(f'  [-] 更新数据库 cookies 失败: {e}')
                        
                        # 登录成功，重新导航到上传页面
                        douyin_logger.info("  [-] 重新导航到上传页面...")
                        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
                        await self._human_pause()  # 使用统一的延迟配置，减少等待时间
                        return
                
                # 检查登录元素是否还存在
                login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                if login_check == 0:
                    # 登录元素消失，可能已登录，但需要确认URL
                    await asyncio.sleep(2)  # 等待页面稳定
                    current_url = page.url
                    if "creator.douyin.com" in current_url and "login" not in current_url.lower():
                        douyin_logger.success("✅ 检测到登录成功，继续执行上传流程...")
                        
                        # 保存更新后的cookies
                        await context.storage_state(path=self.account_file)
                        douyin_logger.success('  [-] 登录后的cookies已保存到临时文件')
                        
                        # 如果提供了 account_id，更新数据库中的cookies
                        if self.account_id:
                            try:
                                import json
                                from db import get_db
                                from services.task_executor import save_cookies_to_db
                                
                                # 读取更新后的cookies
                                with open(self.account_file, 'r', encoding='utf-8') as f:
                                    updated_cookies = json.load(f)
                                
                                # 更新到数据库
                                with get_db() as db:
                                    save_cookies_to_db(self.account_id, updated_cookies, db)
                                douyin_logger.success(f'  [-] 账号 {self.account_id} 的 cookies 已更新到数据库')
                            except Exception as e:
                                douyin_logger.warning(f'  [-] 更新数据库 cookies 失败: {e}')
                        
                        # 登录成功，重新导航到上传页面
                        douyin_logger.info("  [-] 重新导航到上传页面...")
                        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
                        await asyncio.sleep(2)  # 等待页面加载
                        return
                
                # 显示等待提示（每30秒提示一次）
                elapsed_seconds = int(elapsed_time)
                if elapsed_seconds > 0 and elapsed_seconds % 30 == 0:
                    remaining_time = max_wait_time - elapsed_seconds
                    douyin_logger.info(f"⏳ 仍在等待登录... 已等待 {elapsed_seconds} 秒，剩余 {remaining_time} 秒")
                    
            except Exception as e:
                douyin_logger.warning(f"检查登录状态时出错: {e}，继续等待...")
                await asyncio.sleep(check_interval)

    async def set_schedule_time_douyin(self, page, publish_date: Optional[Union[datetime, int, str]]):
        """
        设置定时发布
        
        Args:
            page: Playwright 页面对象
            publish_date: 发布时间，可以是 datetime 对象、None、0 或 "0"
        """
        # 检查 publish_date 是否有效
        # 首先检查是否为 None
        if publish_date is None:
            douyin_logger.warning("publish_date 为 None，跳过定时发布设置")
            return
        
        # 如果 publish_date 是数字 0 或字符串 "0"，表示立即发布，不需要设置定时
        if publish_date == 0 or publish_date == "0":
            douyin_logger.info("publish_date 为 0，立即发布，跳过定时设置")
            return
        
        # 检查是否为 datetime 对象
        if not isinstance(publish_date, datetime):
            douyin_logger.warning(f"publish_date 类型无效: {type(publish_date)}，跳过定时发布设置")
            return
        
        # 选择包含特定文本内容的 label 元素
        await self._human_pause()
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await self._human_pause()
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)
        await self._human_pause(2)

    async def _validate_cookies_from_db(self):
        """从数据库获取并验证cookies"""
        if not self.account_id:
            douyin_logger.warning("未提供 account_id，跳过数据库 cookies 验证")
            return False
        
        try:
            from db import get_db
            from services.task_executor import get_account_from_db
            import json
            
            with get_db() as db:
                account_info = get_account_from_db(self.account_id, db)
                if not account_info:
                    douyin_logger.error(f"账号 {self.account_id} 不存在于数据库中")
                    return False
                
                cookies_json = account_info.get('cookies')
                if not cookies_json:
                    douyin_logger.error(f"账号 {self.account_id} 没有 cookies")
                    return False
                
                # 解析cookies
                if isinstance(cookies_json, str):
                    cookies_data = json.loads(cookies_json)
                else:
                    cookies_data = cookies_json
                
                # 验证cookies格式
                if not isinstance(cookies_data, dict):
                    douyin_logger.error(f"账号 {self.account_id} 的 cookies 格式无效")
                    return False
                
                # 检查关键cookies
                cookies_list = cookies_data.get('cookies', [])
                cookie_names = [c.get('name', '') for c in cookies_list if isinstance(c, dict)]
                important_cookies = ['sessionid', 'passport_auth', 'passport_csrf_token', 'sid_guard', 'uid_tt', 'sid_tt']
                missing_important = [name for name in important_cookies if name not in cookie_names]
                
                if missing_important:
                    douyin_logger.warning(f"账号 {self.account_id} 缺少关键 cookies: {missing_important}")
                
                douyin_logger.info(f"从数据库验证 cookies: 账号 {self.account_id}, {len(cookies_list)} 个 cookies")
                return True
                
        except Exception as e:
            douyin_logger.error(f"从数据库验证 cookies 失败: {e}")
            return False

    async def upload(self, playwright: Playwright):
        # 验证cookies（从数据库）
        await self._validate_cookies_from_db()
        
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            # 检查路径是否存在
            if not os.path.exists(self.local_executable_path):
                error_msg = (
                    f"Chrome 浏览器路径不存在: {self.local_executable_path}\n"
                    f"请检查 conf.py 中的 LOCAL_CHROME_PATH 配置，或设置环境变量 LOCAL_CHROME_PATH\n"
                    f"常见路径：\n"
                    f"  - C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\n"
                    f"  - C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe\n"
                    f"  - {os.path.expanduser('~')}\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
                )
                douyin_logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            browser_name = "Edge" if "Edge" in self.local_executable_path else "Chrome" if "Chrome" in self.local_executable_path else "Chromium"
            douyin_logger.info(f"[浏览器] 使用 {browser_name} 浏览器: {self.local_executable_path}")
            try:
                browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
            except Exception as e:
                error_msg = (
                    f"无法启动 Chrome 浏览器: {e}\n"
                    f"路径: {self.local_executable_path}\n"
                    f"请确保：\n"
                    f"  1. Chrome 浏览器已正确安装\n"
                    f"  2. 路径配置正确\n"
                    f"  3. 有足够的权限访问该路径"
                )
                douyin_logger.error(error_msg)
                raise
        else:
            douyin_logger.info("[浏览器] 使用默认 Chromium 浏览器（未指定路径）")
            browser = await playwright.chromium.launch(headless=self.headless)
        
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        douyin_logger.info(f"Loading cookies from: {self.account_file}")
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
        douyin_logger.info(f'[-] 正在打开上传页面...')
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        await self._human_pause(2)
        
        # 验证cookies是否有效（检查是否跳转到登录页面）
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            douyin_logger.warning("页面未能在5秒内加载到上传页面，可能cookies失效")
            # 检查是否有登录元素
            login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
            if login_check > 0:
                douyin_logger.warning("检测到登录页面，cookies已失效，等待用户重新登录...")
                # 不关闭浏览器，等待用户登录
                await self._wait_for_login(page, context, browser)
        
        # 再次检查登录元素（双重验证）
        login_check = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        if login_check > 0:
            douyin_logger.warning("检测到登录页面元素，cookies已失效，等待用户重新登录...")
            # 不关闭浏览器，等待用户登录
            await self._wait_for_login(page, context, browser)
        
        douyin_logger.info("Cookies验证通过，继续上传流程")
        await self._human_pause()
        # 点击 "上传视频" 按钮
        await page.locator("div[class^='container'] input").set_input_files(self.file_path)
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
                    await self._human_pause(1.0)

                    if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                        douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                        await self.handle_upload_error(page)
            except:
                douyin_logger.info("  [-] 正在上传视频中...")
                await self._human_pause(1.0)

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

        # 设置定时发布（如果提供了有效的 publish_date）
        # 检查 publish_date 是否为有效的 datetime 对象
        if self.publish_date is not None and self.publish_date != 0 and self.publish_date != "0":
            if isinstance(self.publish_date, datetime):
                try:
                    await self.set_schedule_time_douyin(page, self.publish_date)
                except Exception as e:
                    douyin_logger.error(f"设置定时发布失败: {e}")
                    # 不阻止发布流程，继续执行
            else:
                douyin_logger.warning(f"publish_date 类型无效: {type(self.publish_date)}，跳过定时发布设置")

        # 判断视频是否发布成功
        publish_button_clicked = False
        max_wait_time = 120  # 最大等待时间（秒）
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 检查是否超时
            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time > max_wait_time:
                douyin_logger.error(f"  [-] 等待发布完成超时（{max_wait_time}秒），可能发布失败")
                raise TimeoutError(f"等待发布完成超时（{max_wait_time}秒）")
            
            # 判断视频是否发布成功
            try:
                if not publish_button_clicked:
                    publish_button = page.get_by_role('button', name="发布", exact=True)
                    if await publish_button.count():
                        await publish_button.click()
                        publish_button_clicked = True
                        douyin_logger.info("  [-] 已点击发布按钮，正在等待发布完成...")
                        await self._human_pause(1.0)  # 点击后等待一下
                
                # 检查当前URL，如果已经跳转到作品管理页面，说明发布成功
                current_url = page.url
                if "creator.douyin.com/creator-micro/content/manage" in current_url:
                    douyin_logger.success("  [-]视频发布成功（已跳转到作品管理页面）")
                    break
                
                # 尝试等待URL跳转（使用较短的超时时间，避免阻塞）
                try:
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**",
                                            timeout=2000)  # 2秒超时
                    douyin_logger.success("  [-]视频发布成功（URL已跳转）")
                    break
                except:
                    # URL未跳转，继续检查其他成功标志
                    pass
                
                # 检查是否有成功提示或错误提示
                # 检查是否有"发布成功"或类似的提示
                success_indicators = [
                    page.locator('text=发布成功'),
                    page.locator('text=发布完成'),
                    page.locator('[class*="success"]'),
                ]
                
                for indicator in success_indicators:
                    if await indicator.count() > 0:
                        douyin_logger.success("  [-]视频发布成功（检测到成功提示）")
                        # 等待一下，确保页面跳转
                        await asyncio.sleep(2)
                        break
                else:
                    # 没有找到成功提示，继续等待
                    pass
                
                # 检查是否有错误提示
                error_indicators = [
                    page.locator('text=发布失败'),
                    page.locator('text=上传失败'),
                    page.locator('[class*="error"]'),
                ]
                
                for indicator in error_indicators:
                    if await indicator.count() > 0:
                        error_text = await indicator.first.inner_text() if await indicator.count() > 0 else "未知错误"
                        douyin_logger.error(f"  [-] 检测到错误提示: {error_text}")
                        raise Exception(f"发布失败: {error_text}")
                
            except TimeoutError:
                raise  # 重新抛出超时错误
            except Exception as e:
                if "发布失败" in str(e) or "上传失败" in str(e):
                    raise  # 重新抛出错误
                # 其他异常，继续等待
                pass
            
            # 等待一段时间后继续检查
            douyin_logger.info(f"  [-] 视频正在发布中...（已等待 {int(elapsed_time)} 秒）")
            await asyncio.sleep(1.0)  # 增加等待时间到1秒，减少日志输出频率

        # 保存更新后的cookies
        await context.storage_state(path=self.account_file)  # 保存cookie到临时文件
        douyin_logger.success('  [-]cookie更新完毕！')
        
        # 读取更新后的cookies（用于返回给调用方）
        updated_cookies = None
        try:
            if os.path.exists(self.account_file):
                import json
                with open(self.account_file, 'r', encoding='utf-8') as f:
                    updated_cookies = json.load(f)
                douyin_logger.info(f'  [-]成功读取更新后的cookies，准备返回给 task_executor 更新任务状态')
        except Exception as e:
            douyin_logger.warning(f'  [-]读取cookies文件失败: {e}，但上传已成功，将返回成功标记')
        
        # 如果提供了 account_id，更新数据库中的cookies
        if self.account_id and updated_cookies:
            try:
                from db import get_db
                from services.task_executor import save_cookies_to_db
                
                # 更新到数据库
                with get_db() as db:
                    save_cookies_to_db(self.account_id, updated_cookies, db)
                douyin_logger.success(f'  [-]账号 {self.account_id} 的 cookies 已更新到数据库')
            except Exception as e:
                douyin_logger.warning(f'  [-]更新数据库 cookies 失败: {e}')
        
        # 准备返回结果（在关闭浏览器之前返回，以便任务状态能及时更新）
        result = None
        if updated_cookies:
            douyin_logger.info(f'  [-]返回更新后的cookies给 task_executor，任务状态将被更新为 completed')
            result = updated_cookies
        else:
            # 即使 cookies 读取失败，也返回成功标记，确保任务状态能正确更新
            douyin_logger.info(f'  [-]cookies读取失败，返回成功标记给 task_executor，任务状态将被更新为 completed')
            result = {"upload_success": True}
        
        # 在后台异步关闭浏览器（不阻塞返回）
        async def close_browser_async():
            try:
                # 等待一小段时间，确保cookies已保存和结果已返回
                await asyncio.sleep(1)
                await context.close()
                await browser.close()
                douyin_logger.info('  [-]浏览器已关闭')
            except Exception as e:
                douyin_logger.warning(f'  [-]关闭浏览器时出错: {e}')
        
        # 创建后台任务关闭浏览器，不等待完成
        # 使用 get_event_loop() 确保在正确的循环中创建任务
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果循环正在运行，创建后台任务
                asyncio.create_task(close_browser_async())
            else:
                # 如果循环未运行，直接关闭（这种情况不应该发生）
                await close_browser_async()
        except Exception as e:
            # 如果创建任务失败，尝试直接关闭（同步方式）
            douyin_logger.warning(f'  [-]创建后台任务失败: {e}，将直接关闭浏览器')
            try:
                await context.close()
                await browser.close()
            except:
                pass
        
        # 立即返回结果，不等待浏览器关闭
        return result
    
    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            douyin_logger.info('  [-] 正在设置视频封面...')
            await self._human_pause()
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.dy-creator-content-modal")
            await self._human_pause()
            await page.click('text="设置竖封面"')
            await self._human_pause(2)
            # 定位到上传区域并上传文件
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            douyin_logger.info('  [-] 封面图片已上传，等待处理...')
            # 等待图片上传和处理完成（等待上传进度消失或预览图出现）
            try:
                # 等待上传完成，检查上传进度元素消失或预览图出现
                await page.wait_for_selector("div[class*='upload'] div[class*='progress']", state='hidden', timeout=10000)
            except:
                # 如果进度条不存在，等待一段时间让图片处理完成
                await self._human_pause(3)
            
            # 尝试多种方式定位"完成"按钮
            douyin_logger.info('  [-] 正在查找并点击完成按钮...')
            button_clicked = False
            
            # 方法1: 尝试通过 tooltip-container 定位
            try:
                complete_button = page.locator("div#tooltip-container button:visible:has-text('完成')")
                if await complete_button.count() > 0:
                    # 等待按钮变为可点击状态
                    await complete_button.wait_for(state='visible', timeout=5000)
                    # 检查按钮是否被禁用
                    is_disabled = await complete_button.get_attribute('disabled')
                    if not is_disabled:
                        await complete_button.click()
                        button_clicked = True
                        douyin_logger.info('  [-] 通过 tooltip-container 找到并点击了完成按钮')
            except Exception as e:
                douyin_logger.warning(f'  [-] 方法1失败: {e}')
            
            # 方法2: 尝试通过 footer 定位
            if not button_clicked:
                try:
                    complete_button = page.locator("div[class*='footer'] button:has-text('完成')")
                    if await complete_button.count() > 0:
                        await complete_button.wait_for(state='visible', timeout=5000)
                        is_disabled = await complete_button.get_attribute('disabled')
                        if not is_disabled:
                            await complete_button.click()
                            button_clicked = True
                            douyin_logger.info('  [-] 通过 footer 找到并点击了完成按钮')
                except Exception as e:
                    douyin_logger.warning(f'  [-] 方法2失败: {e}')
            
            # 方法3: 尝试通过 confirmBtn 定位
            if not button_clicked:
                try:
                    complete_button = page.locator("div[class*='confirmBtn'] button:has-text('完成'), div[class*='confirmBtn'] div:has-text('完成')")
                    if await complete_button.count() > 0:
                        await complete_button.wait_for(state='visible', timeout=5000)
                        is_disabled = await complete_button.get_attribute('disabled')
                        if not is_disabled:
                            await complete_button.click()
                            button_clicked = True
                            douyin_logger.info('  [-] 通过 confirmBtn 找到并点击了完成按钮')
                except Exception as e:
                    douyin_logger.warning(f'  [-] 方法3失败: {e}')
            
            # 方法4: 尝试通过文本直接定位
            if not button_clicked:
                try:
                    complete_button = page.get_by_role('button', name='完成', exact=False)
                    if await complete_button.count() > 0:
                        # 找到在模态框内的完成按钮
                        modal_button = complete_button.filter(has=page.locator("div.dy-creator-content-modal"))
                        if await modal_button.count() > 0:
                            await modal_button.wait_for(state='visible', timeout=5000)
                            is_disabled = await modal_button.get_attribute('disabled')
                            if not is_disabled:
                                await modal_button.click()
                                button_clicked = True
                                douyin_logger.info('  [-] 通过文本定位找到并点击了完成按钮')
                except Exception as e:
                    douyin_logger.warning(f'  [-] 方法4失败: {e}')
            
            # 方法5: 尝试通过键盘回车（如果按钮有焦点）
            if not button_clicked:
                try:
                    # 尝试按回车键（如果完成按钮有焦点）
                    await page.keyboard.press('Enter')
                    await self._human_pause(1)
                    # 检查对话框是否关闭
                    if await page.locator("div.dy-creator-content-modal").count() == 0:
                        button_clicked = True
                        douyin_logger.info('  [-] 通过键盘回车触发了完成操作')
                except Exception as e:
                    douyin_logger.warning(f'  [-] 方法5失败: {e}')
            
            if not button_clicked:
                douyin_logger.error('  [-] 无法找到或点击完成按钮，封面可能未应用')
                # 尝试等待对话框自动关闭（某些情况下可能自动应用）
                try:
                    await page.wait_for_selector("div.dy-creator-content-modal", state='hidden', timeout=5000)
                    douyin_logger.info('  [-] 对话框已自动关闭，封面可能已应用')
                except:
                    douyin_logger.warning('  [-] 对话框未自动关闭，封面设置可能失败')
            else:
                douyin_logger.info('  [+] 视频封面设置完成！')
                await self._human_pause()
            
            # 等待封面设置对话框关闭
            try:
                await page.wait_for_selector("div.dy-creator-content-modal", state='hidden', timeout=5000)
            except:
                douyin_logger.warning('  [-] 等待对话框关闭超时，但继续执行后续流程')
            

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
            return await self.upload(playwright)


