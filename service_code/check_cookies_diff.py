"""
对比数据库中的 cookies 和本地文件中的 cookies，找出差异
"""
import asyncio
import sys
import json
from pathlib import Path

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS
from client.db_reader import get_account_from_db
from uploader.douyin_uploader.main import set_init_script
from playwright.async_api import async_playwright

async def compare_cookies(account_id: int):
    """对比数据库和本地文件中的 cookies"""
    print(f"[+] 检查账号 {account_id} 的 cookies...")
    
    # 1. 从数据库读取 cookies
    print("\n[1] 从数据库读取 cookies...")
    account_info = get_account_from_db(account_id)
    if not account_info:
        print(f"[-] 账号 {account_id} 不存在于数据库中")
        return
    
    cookies_from_db = account_info.get('cookies')
    if not cookies_from_db:
        print(f"[-] 账号 {account_id} 在数据库中没有 cookies")
        return
    
    # 解析数据库中的 cookies
    if isinstance(cookies_from_db, str):
        cookies_db_data = json.loads(cookies_from_db)
    else:
        cookies_db_data = cookies_from_db
    
    print(f"[+] 数据库 cookies 类型: {type(cookies_db_data)}")
    print(f"[+] 数据库 cookies 键: {list(cookies_db_data.keys()) if isinstance(cookies_db_data, dict) else 'Not a dict'}")
    if isinstance(cookies_db_data, dict):
        if 'cookies' in cookies_db_data:
            print(f"[+] 数据库 cookies 数量: {len(cookies_db_data.get('cookies', []))}")
        if 'origins' in cookies_db_data:
            print(f"[+] 数据库 origins 数量: {len(cookies_db_data.get('origins', []))}")
    
    # 2. 从本地文件读取 cookies
    print("\n[2] 从本地文件读取 cookies...")
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / f"account_{account_id}.json")
    if not account_file.exists():
        print(f"[-] 本地文件不存在: {account_file}")
        return
    
    with open(account_file, 'r', encoding='utf-8') as f:
        cookies_file_data = json.load(f)
    
    print(f"[+] 本地文件 cookies 类型: {type(cookies_file_data)}")
    print(f"[+] 本地文件 cookies 键: {list(cookies_file_data.keys()) if isinstance(cookies_file_data, dict) else 'Not a dict'}")
    if isinstance(cookies_file_data, dict):
        if 'cookies' in cookies_file_data:
            print(f"[+] 本地文件 cookies 数量: {len(cookies_file_data.get('cookies', []))}")
        if 'origins' in cookies_file_data:
            print(f"[+] 本地文件 origins 数量: {len(cookies_file_data.get('origins', []))}")
    
    # 3. 对比差异
    print("\n[3] 对比差异...")
    if isinstance(cookies_db_data, dict) and isinstance(cookies_file_data, dict):
        # 对比 cookies 列表
        db_cookies = cookies_db_data.get('cookies', [])
        file_cookies = cookies_file_data.get('cookies', [])
        
        print(f"[+] 数据库 cookies 数量: {len(db_cookies)}")
        print(f"[+] 本地文件 cookies 数量: {len(file_cookies)}")
        
        if len(db_cookies) != len(file_cookies):
            print(f"[!] 警告: cookies 数量不一致!")
        
        # 检查每个 cookie 的字段
        if db_cookies and file_cookies:
            db_cookie_names = {c.get('name') for c in db_cookies}
            file_cookie_names = {c.get('name') for c in file_cookies}
            
            missing_in_file = db_cookie_names - file_cookie_names
            extra_in_file = file_cookie_names - db_cookie_names
            
            if missing_in_file:
                print(f"[!] 本地文件缺少的 cookies: {missing_in_file}")
            if extra_in_file:
                print(f"[!] 本地文件多余的 cookies: {extra_in_file}")
            
            # 检查关键 cookie 的字段
            print("\n[4] 检查关键 cookies 的字段...")
            key_cookies = ['passport_auth_mix_state', 'passport_assist_user', 'passport_csrf_token']
            for cookie_name in key_cookies:
                db_cookie = next((c for c in db_cookies if c.get('name') == cookie_name), None)
                file_cookie = next((c for c in file_cookies if c.get('name') == cookie_name), None)
                
                if db_cookie and file_cookie:
                    print(f"\n[{cookie_name}]")
                    print(f"  数据库: {json.dumps(db_cookie, ensure_ascii=False, indent=2)}")
                    print(f"  本地文件: {json.dumps(file_cookie, ensure_ascii=False, indent=2)}")
                    
                    # 检查字段差异
                    db_keys = set(db_cookie.keys())
                    file_keys = set(file_cookie.keys())
                    if db_keys != file_keys:
                        print(f"  [!] 字段不一致!")
                        print(f"  数据库字段: {db_keys}")
                        print(f"  本地文件字段: {file_keys}")
                elif db_cookie and not file_cookie:
                    print(f"[!] {cookie_name} 在数据库中存在，但在本地文件中不存在")
                elif not db_cookie and file_cookie:
                    print(f"[!] {cookie_name} 在本地文件中存在，但在数据库中不存在")
    
    # 4. 测试使用数据库中的 cookies 直接加载
    print("\n[5] 测试使用数据库中的 cookies 直接加载...")
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        
        # 直接使用数据库中的 cookies
        context = await browser.new_context(storage_state=cookies_db_data)
        context = await set_init_script(context)
        page = await context.new_page()
        
        print("[+] 使用数据库 cookies 访问上传页面...")
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"[+] 当前URL: {current_url}")
        
        login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        if login_text_count > 0:
            print("[!] 使用数据库 cookies 仍然显示登录页面")
        else:
            print("[+] 使用数据库 cookies 成功进入上传页面")
        
        await context.close()
        await browser.close()
        await playwright.stop()
    except Exception as e:
        print(f"[-] 测试数据库 cookies 时出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 测试使用本地文件中的 cookies
    print("\n[6] 测试使用本地文件中的 cookies...")
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        
        # 使用本地文件中的 cookies
        context = await browser.new_context(storage_state=str(account_file))
        context = await set_init_script(context)
        page = await context.new_page()
        
        print("[+] 使用本地文件 cookies 访问上传页面...")
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"[+] 当前URL: {current_url}")
        
        login_text_count = await page.get_by_text('手机号登录').count() + await page.get_by_text('扫码登录').count()
        if login_text_count > 0:
            print("[!] 使用本地文件 cookies 显示登录页面")
        else:
            print("[+] 使用本地文件 cookies 成功进入上传页面")
        
        await context.close()
        await browser.close()
        await playwright.stop()
    except Exception as e:
        print(f"[-] 测试本地文件 cookies 时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    account_id = 2
    if len(sys.argv) > 1:
        try:
            account_id = int(sys.argv[1])
        except ValueError:
            print(f"无效的 account_id: {sys.argv[1]}")
            sys.exit(1)
    
    asyncio.run(compare_cookies(account_id))

