import pymysql

print('Testing MySQL connection...')

try:
    # 尝试连接MySQL服务器
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456'
    )
    print('Connection successful!')
    conn.close()
    
except Exception as e:
    print(f'Connection failed: {e}')
    print(f'Error type: {type(e).__name__}')
    print(f'Error args: {e.args}')