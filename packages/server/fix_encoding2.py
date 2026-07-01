import codecs, re

src = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py'
bak = src + '.gbk.bak'

with open(src, 'rb') as f:
    raw = f.read()

# Write backup
with open(bak, 'wb') as f:
    f.write(raw)

# Try to decode with errors='replace' (replaces invalid sequences)
text, errors = codecs.decode(raw, 'utf-8', errors='replace')
# Remove the replacement characters for clean output
text = text.replace('\ufffd', '')

# Write back as UTF-8
with open(src, 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Fixed: {src}')
print(f'Backup: {bak}')
