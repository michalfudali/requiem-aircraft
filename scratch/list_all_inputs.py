import glob
import re

print("=== ALL INPUTS/SELECTS GROUPED BY TEMPLATE ===")
templates = [
    'templates/inputs_panel.html',
    'templates/engine_fuel_panel.html',
    'templates/bipol1_panel.html',
    'templates/trends_panel.html',
    'templates/openvsp_panel.html',
    'templates/index.html'
]

for t in templates:
    with open(t, encoding='utf-8') as f:
        content = f.read()
    # Find all input, select, textarea
    matches = re.findall(r'<(?:input|select|textarea)[^>]+id=["\']([^"\']+)["\'][^>]*>', content)
    print(f"\n--- {t} ({len(matches)} inputs) ---")
    for m in matches:
        print(f"  {m}")
