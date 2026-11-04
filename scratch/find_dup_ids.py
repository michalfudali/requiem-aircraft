import glob
import re

inputs = {}
for path in glob.glob('templates/**/*.html', recursive=True):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'<(?:input|select|textarea)[^>]+id=["\']([^"\']+)["\']', content):
        fid = m.group(1)
        inputs.setdefault(fid, []).append(path)

print("=== DUPLICATE ELEMENT IDs ACROSS TEMPLATES ===")
for fid, paths in sorted(inputs.items()):
    if len(paths) > 1:
        print(f"{fid:30} in {len(paths)} files: {paths}")
