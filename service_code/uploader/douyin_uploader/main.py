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
                 action_delay: float = 0.8, final_display_delay: float = 100.0):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags if isinstance(tags, list) else (tags.split(',') if tags else [])  # 确保tags是列表
        # 记录日志，确保title和tags正确接收
        douyin_logger.info(f"DouYinVideo initialized - title: '{self.title}', tags: {self.tags}")
        self.publish_date = publish_date
        self.account_file = account_file
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
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
        douyin_logger.info(f'[-] 正在打开主页...')
        
        # 设置较长的导航超时，给页面足够时间完成验证和跳转
        page.set_default_navigation_timeout(30000)
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        
        # 等待页面稳定，给足够时间让 cookies 验证完成
        douyin_logger.info('[-] 等待页面验证和加载...')
        await self._human_pause(3)  # 先等待3秒，让页面完成初始验证
        
        # 智能等待：等待页面要么跳转到目标URL，要么跳转到登录页面
        max_wait_time = 15  # 最多等待15秒
        check_interval = 0.5  # 每0.5秒检查一次
        waited_time = 0
        
        while waited_time < max_wait_time:
            current_url = page.url
            douyin_logger.debug(f'[-] 检查中... 当前URL: {current_url}, 已等待: {waited_time}秒')
            
            # 如果已经跳转到登录页面，立即报错
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                douyin_logger.error(f'[-] 检测到页面跳转到登录页面: {current_url}')
                raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号")
            
            # 如果已经在目标URL，检查页面内容确认不是登录页面
            if 'creator.douyin.com/creator-micro/content/upload' in current_url:
                # 等待页面元素加载
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=3000)
                except:
                    pass
                
                # 检查是否有登录相关的文本（页面可能还在加载中，所以用try-except）
                try:
                    login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
                    if login_text_count > 0:
                        douyin_logger.error('[-] 检测到登录页面元素，cookies已失效')
                        raise Exception("Cookies已失效，页面跳转到登录页面，请重新登录账号")
                except Exception as e:
                    if "Cookies已失效" in str(e):
                        raise
                    # 如果元素不存在（说明不在登录页面），继续
                    pass
                
                # 如果URL正确且没有登录元素，说明成功进入上传页面
                douyin_logger.info(f'[-] 成功进入上传页面: {current_url}')
                break
            
            # 等待一段时间后再次检查
            await asyncio.sleep(check_interval)
            waited_time += check_interval
        
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


