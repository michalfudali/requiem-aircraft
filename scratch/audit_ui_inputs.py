import glob, re
from collections import defaultdict

templates = glob.glob('templates/**/*.html', recursive=True)

# Map param/id to list of files and snippet
fields_by_name = defaultdict(list)

for tpath in templates:
    if 'report' in tpath and not any(k in tpath for k in ['inputs_panel', 'engine_fuel', 'trends_panel', 'bipol1_panel', 'openvsp_panel', 'coursework_panel']):
        continue
    with open(tpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # find all inputs, selects
    tag_matches = re.finditer(r'<(?:input|select|textarea)\b([^>]*)>', content, re.IGNORECASE)
    for tm in tag_matches:
        attrs = tm.group(1)
        id_m = re.search(r'\bid=[\'"]([^\'"]+)[\'"]', attrs)
        name_m = re.search(r'\bname=[\'"]([^\'"]+)[\'"]', attrs)
        dp_m = re.search(r'\bdata-param=[\'"]([^\'"]+)[\'"]', attrs)
        field_id = id_m.group(1) if id_m else (name_m.group(1) if name_m else None)
        if field_id:
            # find surrounding label
            start = max(0, tm.start() - 150)
            end = min(len(content), tm.end() + 150)
            context = content[start:end]
            lbl_m = re.search(r'<(?:label|span|th)[^>]*>([^<]+)</(?:label|span|th)>', context)
            lbl = lbl_m.group(1).strip() if lbl_m else ''
            fields_by_name[field_id].append((tpath, lbl, attrs[:80]))

print(f"Total unique input IDs found: {len(fields_by_name)}")

# Check duplicate IDs
duplicates = {k: v for k, v in fields_by_name.items() if len(v) > 1}
print(f"Duplicate IDs across templates ({len(duplicates)}):")
for k, v in duplicates.items():
    print(f"\nID: '{k}'")
    for f, lbl, attrs in v:
        print(f"  file: {f} | label: {lbl} | attrs: {attrs}")

