import codecs

src = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py'
bak = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py.gbk.bak'

# Restore from backup
with open(bak, 'rb') as f:
    raw = f.read()

print(f'Restore size: {len(raw)}')

# GBK decode should work on Chinese Windows files
try:
    text = raw.decode('gbk')
    print(f'GBK decode OK, length: {len(text)}')
except Exception as e:
    print(f'GBK failed: {e}')
    # Try with errors='replace'
    text = raw.decode('gbk', errors='replace')
    print(f'GBK replace OK, length: {len(text)}')

# Write as UTF-8
with open(src, 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Written as UTF-8 to: {src}')
