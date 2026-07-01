import shutil, os

src = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py'
bak = src + '.gbk.bak'

# Restore from backup
shutil.copy2(bak, src)
print(f'Restored: {src}')

# Now fix by reading as GBK and writing as UTF-8
with open(src, 'rb') as f:
    raw = f.read()

text = raw.decode('gbk', errors='replace')
# Write as UTF-8
with open(src, 'w', encoding='utf-8') as f:
    f.write(text)
print(f'Re-encoded as UTF-8: {src}')
