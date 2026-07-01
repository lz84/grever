import sys

# Try to import error_handler specifically and see what encoding it uses
path = r'D:\work\research\agents-nexus\packages\server\src\api\error_handler.py'
with open(path, 'rb') as f:
    raw = f.read()

print(f'File size: {len(raw)}')
print(f'First 100 bytes: {raw[:100]}')
try:
    text = raw.decode('utf-8')
    print(f'UTF-8 OK, first 100 chars: {text[:100]}')
except Exception as e:
    print(f'UTF-8 failed: {e}')
    try:
        text = raw.decode('gbk')
        print(f'GBK OK, first 100 chars: {text[:100]}')
    except Exception as e2:
        print(f'GBK failed: {e2}')
        try:
            text = raw.decode('latin1')
            print(f'Latin1 OK (raw bytes)')
        except:
            pass
