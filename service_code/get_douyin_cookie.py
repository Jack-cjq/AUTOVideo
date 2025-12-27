import asyncio
import sys
from pathlib import Path

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS
from uploader.douyin_uploader.main import set_init_script
from playwright.async_api import async_playwright
from client.db_reader import get_account_from_db

async def cookie_auth_keep_open(account_file):
    """检查 cookies 有效性，如果有效则保持浏览器打开"""
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(
            storage_state=account_file,
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
                'Upgrade-Insecure-Requests': '1'
            }
        )
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        print("[+] 正在访问上传页面...")
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        
        # 等待 URL 稳定
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=10000)
            print(f"[+] 当前URL: {page.url}")
        except:
            current_url = page.url
            print(f"[-] URL 未能在10秒内稳定，当前URL: {current_url}")
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                print("[!] 页面跳转到登录页面，cookie 可能已失效")
                print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
                print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
                # 保持浏览器打开，不关闭
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n[+] 收到中断信号，浏览器将保持打开...")
                    pass
                return False
            else:
                print("[+] URL 不稳定，但未跳转到登录页面，继续检查...")
        
        # 等待页面完全加载
        print("[+] 等待页面完全加载...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass
        
        # 额外等待 3 秒，确保页面完全渲染
        await asyncio.sleep(3)
        
        # 检查当前 URL
        current_url = page.url
        print(f"[+] 页面加载完成，当前URL: {current_url}")
        
        # 如果 URL 跳转到登录页面
        if 'login' in current_url.lower() or 'passport' in current_url.lower():
            print("[!] 页面已跳转到登录页面，cookie 可能已失效")
            print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
            print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
            # 保持浏览器打开，不关闭
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n[+] 收到中断信号，浏览器将保持打开...")
                pass
            return False
        
        # 检查是否有登录相关的文本（2024.06.17 抖音创作者中心改版）
        print("[+] 检查页面登录状态...")
        login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        
        if login_text_count > 0:
            print("[!] 检测到登录页面元素，cookie 可能已失效")
            print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
            print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
            # 保持浏览器打开，不关闭
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n[+] 收到中断信号，浏览器将保持打开...")
                pass
            return False
        
        # 检查是否真的在上传页面（检查上传元素）
        print("[+] 检查上传页面元素...")
        try:
            upload_elements = await page.locator('input[type="file"]').count()
            if upload_elements > 0:
                print("[+] 检测到上传元素，确认已进入上传页面")
            else:
                print("[!] 警告：未检测到上传元素，但也不在登录页面")
                print(f"[!] 当前页面标题: {await page.title()}")
        except Exception as e:
            print(f"[!] 检查上传元素时出错: {e}")
        
        print("[+] cookie 有效，已成功进入上传页面")
        print("[+] 浏览器将保持打开状态，您可以继续使用")
        print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
        # 保持浏览器打开，等待用户手动关闭或按 Ctrl+C
        try:
            # 无限等待，直到用户按 Ctrl+C 或浏览器关闭
            while True:
                await asyncio.sleep(1)  # 每秒检查一次
        except KeyboardInterrupt:
            print("\n[+] 收到中断信号，浏览器将保持打开...")
            print("[+] 您可以继续使用浏览器，完成后手动关闭即可")
            # 不关闭浏览器，让用户手动关闭
            # 注意：这里不 await playwright.stop()，让浏览器保持运行
            pass
        return True
    except Exception as e:
        print(f"[-] 发生错误: {e}")
        print("[+] 浏览器将保持打开，您可以手动检查")
        print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
        # 即使出错也保持浏览器打开
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[+] 收到中断信号，浏览器将保持打开...")
            pass
        return False

async def cookie_auth_from_db(account_id: int):
    """直接从数据库读取 cookies 并检查有效性"""
    print(f"[+] 从数据库读取账号 {account_id} 的 cookies...")
    
    # 从数据库读取
    account_info = get_account_from_db(account_id)
    if not account_info:
        print(f"[-] 账号 {account_id} 不存在于数据库中")
        return False
    
    cookies_json = account_info.get('cookies')
    if not cookies_json:
        print(f"[-] 账号 {account_id} 在数据库中没有 cookies")
        return False
    
    # 解析 cookies
    import json
    if isinstance(cookies_json, str):
        cookies_data = json.loads(cookies_json)
    else:
        cookies_data = cookies_json
    
    print(f"[+] 成功从数据库读取 cookies，类型: {type(cookies_data)}")
    if isinstance(cookies_data, dict):
        print(f"[+] Cookies 键: {list(cookies_data.keys())}")
        if 'cookies' in cookies_data:
            print(f"[+] Cookies 数量: {len(cookies_data.get('cookies', []))}")
    
    # 修复 storageState 格式问题（与 save_cookies_to_temp 相同的逻辑）
    print("[+] 修复 cookies 格式...")
    if isinstance(cookies_data, dict):
        # 确保origins是列表
        if 'origins' in cookies_data and isinstance(cookies_data['origins'], list):
            for origin in cookies_data['origins']:
                if isinstance(origin, dict):
                    # 修复localStorage格式：确保是数组而不是对象
                    if 'localStorage' in origin:
                        if isinstance(origin['localStorage'], dict):
                            # 如果是对象，转换为数组格式
                            localStorage_list = []
                            for key, value in origin['localStorage'].items():
                                localStorage_list.append({"name": key, "value": str(value)})
                            origin['localStorage'] = localStorage_list
                            print(f"[+] 修复了 localStorage 格式（对象 -> 数组）")
                        elif not isinstance(origin['localStorage'], list):
                            # 如果不是数组也不是对象，设为空数组
                            origin['localStorage'] = []
        
        # 确保cookies是列表
        if 'cookies' in cookies_data and not isinstance(cookies_data['cookies'], list):
            if isinstance(cookies_data['cookies'], dict):
                cookies_data['cookies'] = []
            elif cookies_data['cookies'] is None:
                cookies_data['cookies'] = []
    
    # 直接使用数据库中的 cookies 创建浏览器上下文
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        
        # 使用修复后的 cookies 数据创建浏览器上下文
        # 添加更真实的浏览器设置，避免被检测为自动化工具
        print("[+] 使用数据库 cookies 创建浏览器上下文...")
        context = await browser.new_context(
            storage_state=cookies_data,
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
                'Upgrade-Insecure-Requests': '1'
            }
        )
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 先访问首页，让 cookies 生效，然后再跳转到上传页面
        print("[+] 先访问首页，让 cookies 生效...")
        await page.goto("https://creator.douyin.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)  # 等待首页加载
        
        # 访问上传页面
        print("[+] 正在访问上传页面...")
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        
        # 等待 URL 稳定
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=10000)
            print(f"[+] 当前URL: {page.url}")
        except:
            current_url = page.url
            print(f"[-] URL 未能在10秒内稳定，当前URL: {current_url}")
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                print("[!] 页面跳转到登录页面，cookie 可能已失效")
                print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
                print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
                # 保持浏览器打开，不关闭
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n[+] 收到中断信号，浏览器将保持打开...")
                    pass
                return False
        
        # 等待页面完全加载
        print("[+] 等待页面完全加载...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass
        
        # 额外等待 3 秒
        await asyncio.sleep(3)
        
        # 检查登录状态
        current_url = page.url
        print(f"[+] 页面加载完成，当前URL: {current_url}")
        
        if 'login' in current_url.lower() or 'passport' in current_url.lower():
            print("[!] 页面已跳转到登录页面，cookie 可能已失效")
            print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
            print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
            # 保持浏览器打开，不关闭
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n[+] 收到中断信号，浏览器将保持打开...")
                pass
            return False
        
        login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        if login_text_count > 0:
            print("[!] 检测到登录页面元素，cookie 可能已失效")
            print("[+] 浏览器将保持打开，您可以手动检查或重新登录")
            print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
            # 保持浏览器打开，不关闭
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n[+] 收到中断信号，浏览器将保持打开...")
                pass
            return False
        
        print("[+] cookie 有效，已成功进入上传页面（使用数据库 cookies）")
        print("[+] 浏览器将保持打开状态，您可以继续使用")
        print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
        
        # 保持浏览器打开
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[+] 收到中断信号，浏览器将保持打开...")
            pass
        
        return True
    except Exception as e:
        print(f"[-] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        print("[+] 浏览器将保持打开，您可以手动检查")
        print("[+] 按 Ctrl+C 可以退出程序（浏览器仍会保持打开）")
        # 即使出错也保持浏览器打开
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[+] 收到中断信号，浏览器将保持打开...")
            pass
        return False

if __name__ == '__main__':
    # 支持命令行参数指定 account_id
    account_id = None
    use_db = False  # 是否直接从数据库读取
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        # 检查是否有 --db 参数
        if '--db' in sys.argv:
            use_db = True
            sys.argv.remove('--db')
        
        if len(sys.argv) > 1:
            try:
                account_id = int(sys.argv[1])
            except ValueError:
                print(f"无效的 account_id: {sys.argv[1]}")
                print("\n使用方法:")
                print("  python get_douyin_cookie.py [account_id]          # 使用本地文件")
                print("  python get_douyin_cookie.py --db [account_id]    # 直接从数据库读取")
                sys.exit(1)
    
    # 如果使用 --db 参数，直接从数据库读取
    if use_db:
        if not account_id:
            print("错误: 使用 --db 参数时必须指定 account_id")
            print("使用方法: python get_douyin_cookie.py --db <account_id>")
            sys.exit(1)
        
        print(f"[+] 直接从数据库读取账号 {account_id} 的 cookies...")
        try:
            result = asyncio.run(cookie_auth_from_db(account_id))
            if result:
                print(f"[+] Cookies 有效（来自数据库）")
                print("[+] 浏览器窗口已保持打开，您可以继续使用")
            else:
                print(f"[-] Cookies 已失效（来自数据库）")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n[+] 程序已退出，浏览器窗口仍保持打开")
            sys.exit(0)
    else:
        # 使用本地文件
        if account_id:
            account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / f"account_{account_id}.json")
            print(f"检查账号 {account_id} 的 cookies（本地文件）: {account_file}")
        else:
            account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
            print(f"检查默认账号的 cookies（本地文件）: {account_file}")
        
        account_file.parent.mkdir(exist_ok=True)
        
        if not account_file.exists():
            print(f"错误: Cookies 文件不存在: {account_file}")
            print(f"\n提示: 可以使用 --db 参数直接从数据库读取:")
            print(f"  python get_douyin_cookie.py --db {account_id if account_id else '<account_id>'}")
            sys.exit(1)
        
        # 使用 cookie_auth_keep_open 函数检查 cookies 有效性并保持浏览器打开
        try:
            result = asyncio.run(cookie_auth_keep_open(str(account_file)))
            if result:
                print(f"[+] Cookies 有效: {account_file}")
                print("[+] 浏览器窗口已保持打开，您可以继续使用")
            else:
                print(f"[-] Cookies 已失效: {account_file}")
                print(f"\n提示: 可以尝试直接从数据库读取测试:")
                print(f"  python get_douyin_cookie.py --db {account_id if account_id else '<account_id>'}")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n[+] 程序已退出，浏览器窗口仍保持打开")
            sys.exit(0)
