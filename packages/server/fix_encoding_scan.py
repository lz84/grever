import os, glob

src_dir = r'D:\work\research\agents-nexus\packages\server\src'

for root, dirs, files in os.walk(src_dir):
    if '__pycache__' in root or '.git' in root:
        continue
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'rb') as f:
                raw = f.read()
            # Try UTF-8
            try:
                raw.decode('utf-8')
                continue  # OK
            except UnicodeDecodeError:
                pass
            # Try GBK
            try:
                raw.decode('gbk')
                print(f'GBK: {os.path.relpath(fpath, src_dir)}')
                continue
            except:
                pass
            # Try latin1
            try:
                raw.decode('latin1')
                print(f'Latin1: {os.path.relpath(fpath, src_dir)}')
            except:
                print(f'UNKNOWN: {os.path.relpath(fpath, src_dir)}')
        except Exception as e:
            print(f'ERROR reading {fpath}: {e}')

print('Done')
