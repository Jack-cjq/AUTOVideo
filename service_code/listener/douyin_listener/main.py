# -*- coding: utf-8 -*-
"""
抖音聊天消息监听启动代码。

功能目标（当前阶段）：
1. 复用上传模块的浏览器启动与 cookie 加载逻辑；
2. 打开抖音创作者中心的聊天页面：
   https://creator.douyin.com/creator-micro/data/following/chat
3. 保持页面与浏览器打开，后续你可以在本文件中继续扩展“消息监听”的逻辑。
"""

import asyncio
import os
import random
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Playwright, Page, Locator

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS, BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import douyin_logger


CHAT_URL = "https://creator.douyin.com/creator-micro/data/following/chat"


async def _get_first_dialog_snapshot(page: Page) -> str:
    """获取当前对话面板中第一条消息块的文本快照，用于后续判断对话是否发生切换。"""
    try:
        first_block = await page.query_selector("div.box-item-dSA1TJ")
        if not first_block:
            return ""
        text = await first_block.inner_text()
        return (text or "").strip()
    except Exception:
        return ""


async def _wait_conversation_switched(
    page: Page,
    user_name: str,
    prev_first_snapshot: str,
    timeout: float = 10.0,
    poll_interval: float = 0.3,
) -> bool:
    """
    更健壮的会话切换检测：
    1. 左侧激活态 li.active-vBCZvL 的用户名是否变为 user_name；
    2. 右侧标题（如存在）是否包含 user_name；
    3. 第一条消息块内容是否与切换前不同。
    任一条件满足即认为切换成功。
    """
    start = time.monotonic()
    active_li_locator: Locator = page.locator(
        "div.chat-content.semi-tabs-pane-active li.semi-list-item.active-vBCZvL span.item-header-name-vL_79m"
    )
    header_locator: Locator = page.locator("div.box-header-Qq0ZO_ strong.box-header-name-YOrIxz")

    while True:
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            return False

        # 条件 1：左侧激活 li 是否为当前用户
        try:
            active_count = await active_li_locator.filter(has_text=user_name).count()
        except Exception:
            active_count = 0

        # 条件 2：右侧标题是否包含用户名（如果有标题区域的话）
        try:
            header_count = await header_locator.filter(has_text=user_name).count()
        except Exception:
            header_count = 0

        # 条件 3：第一条消息块内容是否发生变化
        try:
            first_snapshot = await _get_first_dialog_snapshot(page)
        except Exception:
            first_snapshot = ""

        content_changed = bool(first_snapshot and first_snapshot != prev_first_snapshot)

        if active_count > 0 or header_count > 0 or content_changed:
            return True

        await asyncio.sleep(poll_interval)


async def _send_chat_message(page: Page, user_name: str, message: str) -> bool:
    """
    在当前已打开、且会话已切换到 user_name 的前提下，将 message 发送到聊天输入框并回车发送。
    模拟人类输入行为：逐字输入、随机延迟、输入后稍等再发送。
    """
    if not message:
        douyin_logger.warning(f"[SEND] 要发送给 '{user_name}' 的消息内容为空，跳过发送。")
        return False

    try:
        # 定位可编辑输入框
        input_locator = page.locator("div.chat-editor-vw2mZE div.chat-input-dccKiL[contenteditable='true']")
        await input_locator.first.wait_for(state="visible", timeout=5000)

        # 点击输入框，模拟人类点击行为
        await input_locator.click()
        # 等待输入框获得焦点（随机延迟 0.3-0.8 秒）
        await asyncio.sleep(random.uniform(0.3, 0.8))

        # 清空旧内容
        await page.keyboard.press("Control+A")
        await asyncio.sleep(random.uniform(0.1, 0.3))
        await page.keyboard.press("Backspace")
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # 逐字输入消息内容，模拟人类打字速度（每个字符间隔 0.05-0.15 秒）
        douyin_logger.info(f"[SEND] 正在向 '{user_name}' 输入消息...")
        for char in message:
            await page.keyboard.type(char)
            # 随机延迟，模拟真实打字速度（中文可能稍慢，英文稍快）
            delay = random.uniform(0.05, 0.15)
            await asyncio.sleep(delay)

        # 输入完成后，稍等片刻再发送（模拟人类检查消息的习惯，0.5-1.5 秒）
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # 按 Enter 发送（shift+enter 为换行，这里用回车直接发送）
        await page.keyboard.press("Enter")
        douyin_logger.info(f"[SEND] 已向 '{user_name}' 发送消息: {message}")
        return True
    except Exception as e:
        douyin_logger.error(f"[SEND] 向 '{user_name}' 发送消息失败: {e}")
        return False


async def open_douyin_chat(playwright: Playwright, account_file: str) -> Page:
    """
    使用已有的 cookie 启动浏览器并打开抖音创作者中心聊天页面。

    :param playwright: Playwright 实例
    :param account_file: cookies 存储文件路径（与上传模块共用）
    :return: 已打开聊天页面的 Page 对象
    """
    options = {
        "headless": LOCAL_CHROME_HEADLESS
    }
    if LOCAL_CHROME_PATH and os.path.exists(LOCAL_CHROME_PATH):
        options["executable_path"] = LOCAL_CHROME_PATH

    douyin_logger.info(f"[+] 正在启动浏览器，准备打开聊天页面: {CHAT_URL}")
    browser = await playwright.chromium.launch(**options)

    context = await browser.new_context(storage_state=account_file)
    context = await set_init_script(context)

    page = await context.new_page()
    # 统一放宽导航超时时间，并仅等待 DOMContentLoaded，避免某些静态资源拖慢 load 事件
    page.set_default_navigation_timeout(60000)
    await page.goto(CHAT_URL, wait_until="domcontentloaded", timeout=60000)
    douyin_logger.info("[-] 正在等待聊天页面加载完成...")
    # 首次进入聊天页，给足 60s 加载时间，防止网络慢导致 load 事件迟到
    await page.wait_for_url(CHAT_URL, timeout=60000)
    douyin_logger.success("[+] 聊天页面加载完成，可以开始后续监听逻辑。")

    try:
        # 尝试清理可能遮挡左侧列表的弹框（指引气泡、弹窗等）
        try:
            await page.keyboard.press("Escape")
            await page.evaluate(
                """
() => {
  const selectors = [
    '[role="dialog"]',
    '.semi-modal-wrap',
    '.semi-modal-mask',
    '.semi-popover',
    '.semi-tooltip'
  ];
  selectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => el.remove());
  });
}
                """
            )
        except Exception as _:
            # 清理弹框失败不致命，继续后续逻辑
            pass
        # 先等待左侧会话列表渲染出来，如果 20s 内还没出来则刷新一次页面
        try:
            await page.wait_for_selector("li.semi-list-item", timeout=20000)
        except Exception:
            douyin_logger.warning("[*] 20 秒内未检测到消息列表，刷新页面重试一次")
            await page.reload(wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_url(CHAT_URL, timeout=60000)
            await page.wait_for_selector("li.semi-list-item", timeout=30000)

        # 有些情况下页面首次进入时右侧对话栏是空的，需要先点击一条会话激活布局
        dialog_panel = await page.query_selector("div.box-item-dSA1TJ")
        if not dialog_panel:
            douyin_logger.info("[*] 初始无对话侧边栏，先点击第一条会话以激活对话区域")
            first_conv = page.locator("li.semi-list-item").first
            try:
                await first_conv.click(force=True, timeout=5000)
                await asyncio.sleep(1.0)
            except Exception as e:
                douyin_logger.error(f"[!] 预激活第一条会话失败: {e}")

        # 只取“当前激活”的聊天面板里的会话列表，避免同时匹配到隐藏面板导致重复/错位
        active_list_selector = "div.chat-content.semi-tabs-pane-active li.semi-list-item"
        await page.wait_for_selector(active_list_selector, timeout=20000)
        # 初始时记录一份稳定的会话句柄列表，避免列表长度在滚动过程中变化导致尾部会话被遗漏
        conv_items = await page.query_selector_all(active_list_selector)
        total = len(conv_items)
        douyin_logger.info(f"[*] 当前消息会话条数（激活面板 li.semi-list-item）: {total}")

        # 读取待发送的用户名和消息内容（若 chat.txt 存在）
        chat_file = Path(BASE_DIR) / "chat.txt"
        target_user = ""
        target_message = ""
        if chat_file.exists():
            try:
                lines = chat_file.read_text(encoding="utf-8").splitlines()
                if len(lines) >= 2:
                    target_user = lines[0].strip()
                    target_message = lines[1].strip()
                    douyin_logger.info(f"[SEND] 读取到待发送配置 -> 用户: '{target_user}', 消息: '{target_message}'")
                else:
                    douyin_logger.warning(f"[SEND] chat.txt 内容不足两行，忽略发送配置。")
            except Exception as e:
                douyin_logger.error(f"[SEND] 读取 chat.txt 失败: {e}")

        send_done = False

        for idx, item in enumerate(conv_items):
            try:
                # 先拿到用户名用于日志，再做点击
                name_el = await item.query_selector("span.item-header-name-vL_79m")
                if not name_el:
                    # 某些占位/不可点击项没有用户名，直接跳过
                    continue
                user_name = (await name_el.inner_text()).strip()
                if not user_name:
                    # 用户名为空的一般是系统提示/空白占位，也跳过
                    continue
                douyin_logger.info(f"[CHAT_LIST] 第 {idx + 1} 条会话，用户名: {user_name}")

                # 点击前记录当前第一条消息快照，用于判断对话内容是否发生切换
                prev_snapshot = await _get_first_dialog_snapshot(page)

                # 对单条会话的点击 + 切换检测增加重试，避免被弹窗/动画打断
                switched = False
                for attempt in range(3):
                    try:
                        await item.scroll_into_view_if_needed()
                        await item.click(force=True, timeout=8000)
                    except Exception as click_e:
                        douyin_logger.debug(
                            f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击失败: {click_e}"
                        )
                        await asyncio.sleep(0.5)
                        continue

                    # 等待会话真正切换成功（激活态 / 标题 / 内容任意一项发生变化）
                    switched = await _wait_conversation_switched(
                        page, user_name, prev_snapshot, timeout=8.0
                    )
                    if switched:
                        break
                    douyin_logger.debug(
                        f"[!] 第 {idx + 1} 条会话（{user_name}）第 {attempt + 1} 次点击后未检测到切换，重试..."
                    )
                    await asyncio.sleep(0.5)

                if not switched:
                    douyin_logger.warning(
                        f"[!] 会话 '{user_name}' 在多次重试后仍未成功切换，跳过该会话。"
                    )
                    continue

                await asyncio.sleep(0.5)

                # 如果 chat.txt 中配置了要发送的用户名，并且匹配当前会话，则发送消息
                if target_user and not send_done and user_name == target_user:
                    ok = await _send_chat_message(page, user_name, target_message)
                    if ok:
                        send_done = True

                # 解析右侧对话框中的聊天记录：
                # 时间行：div.box-item-dSA1TJ.time-Za5gKL
                # 消息行：div.box-item-dSA1TJ[包含 is-me-TJHr4A 或无该类] + 内部 pre.text-X2d7fS.text-item-message-YBtflz
                try:
                    await page.locator("div.box-item-dSA1TJ").first.wait_for(state="attached", timeout=10000)
                except Exception as wait_e:
                    douyin_logger.error(f"[!] 等待对话内容出现失败（会话: {user_name}）: {wait_e}")
                    continue

                message_blocks = await page.query_selector_all("div.box-item-dSA1TJ")

                current_time = ""
                for block in message_blocks:
                    class_attr = await block.get_attribute("class") or ""

                    # 时间行：只记录当前时间上下文
                    if "time-Za5gKL" in class_attr:
                        current_time = (await block.inner_text()).strip()
                        continue

                    # 消息行：包含真实对话内容
                    text_el = await block.query_selector("pre.text-X2d7fS.text-item-message-YBtflz")
                    if not text_el:
                        continue

                    text = (await text_el.inner_text()).strip()

                    # 判断是自己还是对方发的消息
                    is_me = "is-me-TJHr4A" in class_attr
                    direction = "我" if is_me else "对方"

                    douyin_logger.info(
                        f"[DIALOG] 会话用户: {user_name} | 方向: {direction} | 时间: {current_time} | 文本: {text}"
                    )

                # 为避免触发风控，可在会话之间稍微停顿
                await asyncio.sleep(2)

            except Exception as sub_e:
                douyin_logger.error(f"[!] 处理第 {idx + 1} 条会话时出错: {sub_e}")
                # 出错后继续处理下一条
                continue

    except Exception as e:
        douyin_logger.error(f"[!] 无法解析消息列表区域或对话内容: {e}")

    # 当前阶段：仅保持浏览器与页面打开，不做自动关闭
    return page


async def douyin_chat_main(account_file: str):
    """
    聊天监听入口：负责创建 Playwright 上下文并打开聊天页面。

    后续如果你希望在这里轮询消息、挂事件等，都可以在本函数中继续扩展。
    """
    async with async_playwright() as playwright:
        page = await open_douyin_chat(playwright, account_file)

        # 这里先简单保持运行，避免脚本立即退出。
        douyin_logger.info("[*] 聊天页面已打开，当前暂不自动退出。你可以在这里扩展消息监听逻辑。")
        while True:
            await asyncio.sleep(10)



