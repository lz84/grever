import codecs

path = r'D:\work\research\agents-nexus\packages\server\src\reins\scheduler\verification\rules.py'
with open(path, 'rb') as f:
    raw = f.read()

# Try to detect encoding
for enc in ['gbk', 'gb2312', 'utf-8', 'latin1']:
    try:
        text = raw.decode(enc)
        print(f'Encoding {enc} works')
        # Check if it starts with valid Python
        if '"""' in text[:100]:
            print(f'Using encoding: {enc}')
            # Re-write with UTF-8
            # First line is the docstring, try to encode/decode
            try:
                text.encode('utf-8')
                print('Can re-encode as UTF-8')
            except:
                print('Cannot re-encode as UTF-8')
            break
    except Exception as e:
        print(f'Encoding {enc} failed: {e}')
