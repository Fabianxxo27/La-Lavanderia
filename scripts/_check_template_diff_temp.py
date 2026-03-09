import subprocess

proc = subprocess.run(['git', 'diff', '--', 'templates'], capture_output=True, text=True, encoding='utf-8', errors='replace')
lines = proc.stdout.splitlines()

extra = []
for line in lines:
    if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
        continue
    if line.startswith('+') or line.startswith('-'):
        if 'url_for' in line:
            continue
        if line.strip() in ['+', '-']:
            continue
        extra.append(line)

print('NON url_for template diff lines:', len(extra))
for item in extra[:50]:
    print(item)
if len(extra) > 50:
    print('...')
