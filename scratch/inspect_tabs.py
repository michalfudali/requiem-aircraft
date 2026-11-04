with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
tabs = re.findall(r'<div\s+id=[\'"](tab-[^\'"]+)[\'"]\s+class=[\'"]tab-content[^\'"]*[\'"]>', text)
print(f"Tabs in index.html ({len(tabs)}):")
for t in tabs:
    # find where this tab ends and what inputs it has
    start = text.find(f'id="{t}"')
    # find next tab
    next_tab = re.search(r'<div\s+id=[\'"]tab-[^\'"]+[\'"]\s+class=[\'"]tab-content', text[start+20:])
    end = start + 20 + next_tab.start() if next_tab else start + 5000
    tab_html = text[start:end]
    inputs = re.findall(r'<(?:input|select)\b[^>]*id=[\'"]([^\'"]+)[\'"]', tab_html)
    print(f"\nTab: {t} (inputs: {len(inputs)})")
    if inputs:
        print("  Inputs:", inputs[:15])

