import codecs

src = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py'
bak = src + '.gbk.bak'

with open(src, 'rb') as f:
    raw = f.read()

# Write backup
with open(bak, 'wb') as f:
    f.write(raw)

# Decode with replacement for invalid UTF-8
text = raw.decode('utf-8', errors='replace')
# Clean up replacement chars
text = text.replace('\ufffd', '')

# Write back as UTF-8
with open(src, 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Fixed: {src}')
print(f'Backup: {bak}')
print(f'First 200 chars: {text[:200]}')
