import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Find all tabs and their includes
tab_matches = list(re.finditer(r'<div\s+id=[\'"](tab-[^\'"]+)[\'"][^>]*>', text))
for i, tm in enumerate(tab_matches):
    tname = tm.group(1)
    start = tm.end()
    end = tab_matches[i+1].start() if i+1 < len(tab_matches) else len(text)
    chunk = text[start:end]
    inc = re.findall(r'{%\s*include\s*[\'"]([^\'"]+)[\'"]\s*%}', chunk)
    inputs = re.findall(r'<(?:input|select)\b[^>]*id=[\'"]([^\'"]+)[\'"]', chunk)
    print(f"Tab: {tname}")
    if inc:
        print(f"  Includes: {inc}")
    if inputs:
        print(f"  Direct Inputs ({len(inputs)}): {inputs[:10]}")
