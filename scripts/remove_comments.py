import sys 
from pathlib import Path 
 
files = sys.argv[1:] 
if not files: 
    print('Usage: remove_comments.py <file1> <file2> ...') 
    sys.exit(1) 
 
for fp in files:
    p = Path(fp)
    if not p.exists():
        print(f'Skipping {fp}: not found')
        continue
    txt = p.read_text(encoding='utf-8')
    lines = txt.splitlines()
    new_lines = []
    for line in lines:
        s = line.lstrip()
        if s.startswith('#'):
            continue
        if s.startswith('//'):
            continue
        if s.startswith('<!--') and s.rstrip().endswith('-->'):
            continue
        if '//' in line:
            idx = line.find('//')
            prefix = line[:idx]
            if 'http://' in prefix or 'https://' in prefix:
                new_lines.append(line)
            else:
                trimmed = prefix.rstrip()
                if trimmed:
                    new_lines.append(trimmed)
        else:
            new_lines.append(line)
    backup = p.with_suffix(p.suffix + '.bak')
    backup.write_text('\n'.join(lines), encoding='utf-8')
    p.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
    print(f'Cleaned {fp}, backup -> {backup}')
