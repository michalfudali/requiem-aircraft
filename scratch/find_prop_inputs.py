import glob, re

for p in glob.glob('templates/**/*.html', recursive=True):
    with open(p, 'r', encoding='utf-8') as f:
        t = f.read()
    # find all inputs/selects/textareas
    fields = re.findall(r'<(?:input|select|textarea)[^>]*id=[\'"]([^\'"]+)[\'"][^>]*>', t, re.IGNORECASE)
    prop_fields = [f for f in fields if any(k in f.lower() for k in ['sfc', 'prop', 'engine', 'fuel', 'spalanie', 'napęd', 'naped'])]
    if prop_fields:
        print(f"=== {p} ===")
        for pf in prop_fields:
            # find label or nearby text
            match = re.search(r'<(?:label|th|td)[^>]*for=[\'"]' + re.escape(pf) + r'[\'"][^>]*>([^<]+)', t)
            label = match.group(1).strip() if match else ''
            print(f"  id: {pf} | label: {label}")

