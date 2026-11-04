import glob, re

files = [
    'templates/inputs_panel.html',
    'templates/engine_fuel_panel.html',
    'templates/bipol1_panel.html',
    'templates/trends_panel.html',
    'templates/coursework_panel.html',
    'templates/openvsp_panel.html',
    'templates/index.html',
    'templates/studio_panels.html',
    'templates/wizard_basis.html',
    'templates/pilot_loading.html'
]

inputs_by_file = {}
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            text = fp.read()
    except Exception as e:
        continue
    # find all inputs/selects with id
    matches = re.findall(r'<(?:input|select|textarea)\b[^>]*id=[\'"]([^\'"]+)[\'"]', text)
    inputs_by_file[f] = matches

for f, inp in inputs_by_file.items():
    print(f"\n=== {f} ({len(inp)} fields) ===")
    print(', '.join(inp[:25]))
    if len(inp) > 25:
        print('...', ', '.join(inp[25:50]))
    if len(inp) > 50:
        print('...', ', '.join(inp[50:75]))

