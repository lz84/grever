with open(r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py', 'rb') as f:
    data = f.read()
print(f'File size: {len(data)} bytes')
print(f'First 100 bytes: {data[:100]}')
print(f'BOM check: {data[:3] == bytes([0xef, 0xbb, 0xbf])}')
try:
    text = data.decode('utf-8')
    print('UTF-8 decode: OK')
except Exception as e:
    print(f'UTF-8 decode ERROR: {e}')
    try:
        text = data.decode('gbk')
        print('GBK decode: OK')
    except Exception as e2:
        print(f'GBK decode ERROR: {e2}')
