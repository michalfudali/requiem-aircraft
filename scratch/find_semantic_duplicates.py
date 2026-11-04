import glob, re

templates = [
    'templates/inputs_panel.html',
    'templates/engine_fuel_panel.html',
    'templates/bipol1_panel.html',
    'templates/trends_panel.html',
    'templates/openvsp_panel.html',
    'templates/coursework_panel.html',
    'templates/index.html',
    'templates/studio_panels.html'
]

param_groups = {
    'SFC & Fuel': ['sfc', 'fuel', 'spalanie', 'c_p', 'c_j'],
    'Engine & Power & Thrust': ['engine_power', 'thrust', 'power_kw', 'moc', 'ciąg', 'ciag'],
    'Engine Type & Location': ['engine_type', 'engine_location', 'n_engines'],
    'Propeller': ['prop_efficiency', 'prop_diameter', 'śmigło', 'smiglo', 'prop_type'],
    'Mass & Loading': ['m0', 'mtow', 'm_pax', 'm_crew', 'm_baggage', 'n_pax', 'n_crew', 'pax', 'crew', 'cargo'],
    'Speeds & Altitudes': ['v_cruise', 'v_stall', 'v_max', 'climb_rate', 'h_cruise', 'takeoff_distance'],
    'Wing Geometry': ['aspect_ratio', 'wing_area', 'wing_span', 'taper_ratio', 'sweep_deg', 'dihedral_deg'],
}

for group_name, patterns in param_groups.items():
    print(f"\n=================== GROUP: {group_name} ===================")
    for tpath in templates:
        with open(tpath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Find inputs
        for match in re.finditer(r'<(?:input|select|textarea)\b([^>]*)>', content, re.IGNORECASE):
            attrs = match.group(1)
            id_m = re.search(r'\bid=[\'"]([^\'"]+)[\'"]', attrs)
            if not id_m:
                continue
            fid = id_m.group(1)
            if any(p in fid.lower() for p in patterns):
                # find label
                start = max(0, match.start() - 120)
                end = min(len(content), match.end() + 120)
                context = content[start:end]
                lbl_m = re.search(r'<(?:label|span|th)[^>]*>([^<]+)</(?:label|span|th)>', context)
                lbl = lbl_m.group(1).strip() if lbl_m else ''
                print(f"  [{tpath}] ID: {fid} | Label: {lbl}")

