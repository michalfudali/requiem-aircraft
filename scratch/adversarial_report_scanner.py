"""Adversarial scanner script for BIPOL reports (M1 empirical challenge) using standard library only."""
import re
import sys
from copy import deepcopy

# Ensure BIPOL root is in path
sys.path.insert(0, r'C:\Users\Michał\Documents\antigravity\bipol')

from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.report_document import report_document

def _document_text(html):
    start = html.find('<main class="document')
    end = html.rfind('</main>')
    if start != -1 and end != -1:
        return html[start:end+7]
    return html

def run_adversarial_scan():
    client = app.test_client()
    findings = []
    
    print(f"=== 1. PRESET RENDERING AND KEYWORD SCAN (10 PRESETS) ===")
    
    BLACKLIST_EXACT = [
        "ŚDA",
        "ft/s",
        "lbf/ft",
        "simplex",
        "wierzchołkow",
        "przypadków zdegenerowanych",
        "nie gorszych niż",
        "Większe wydłużenie zmniejsza opór",
        "Opór zerowy wyznaczono w trzech krokach",
        "guideline-steps",
        "1. Zakłada się masę startową",
        "różnica wynosi 0,00 kg",
        "nierówności liniowej względem masy osoby",
        "Jednostka współczynnika a wynika",
        "klapa jednoszczelinowa wychylane",
        "pułap teoretyczny jest osiągany asymptotycznie",
        "nie zastępują badań w locie ani wykazania zgodności",
        "Każdą obliczaną wielkość zapisano wzorem ogólnym",
        "commuter..",
        # Test tags blacklist
        'BIPOL_', 'calc-source', 'Wytyczne z zajęć', 'wytycznymi prowadzącego',
        'Do uzupełnienia', 'Kompletność BIPOL', 'submission-review',
        'Identyfikator wariantu', 'maks. ', 'pkt', 'Skąd?', 'w programie',
        'Domknięcie P2', 'Biegunowa P4', 'Wybierz oznaczenie', 'wklej rzędne',
        'IMG2026', 'class="xref"', 'data-cite='
    ]
    
    for preset_name, preset_params in AIRCRAFT_PRESETS.items():
        print(f"\nScanning preset: {preset_name} ...")
        res = client.get(f'/report?preset={preset_name}')
        if res.status_code != 200:
            findings.append(f"HTTP ERROR: Preset {preset_name} returned status {res.status_code}")
            continue
            
        html = res.get_data(as_text=True)
        body = _document_text(html)
        
        # Check blacklist
        for term in BLACKLIST_EXACT:
            if term in body:
                findings.append(f"BLACKLIST HIT in preset {preset_name}: '{term}'")
                
        # Check double periods in text nodes (excluding ellipsis '...' and numbers like '1.2')
        double_dots = re.findall(r'([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,}\.\.[^\.])', body)
        if double_dots:
            findings.append(f"DOUBLE DOT PUNCTUATION in preset {preset_name}: {double_dots}")
            
        # Check required semantic IDs
        if 'id="tab-requirements"' not in body:
            findings.append(f"MISSING ID in {preset_name}: tab-requirements")
        if 'id="tab-predecessors"' not in body:
            findings.append(f"MISSING ID in {preset_name}: tab-predecessors")
        if 'id="tab-summary-p6"' not in body:
            findings.append(f"MISSING ID in {preset_name}: tab-summary-p6")
            
        # Check figures based on aircraft type
        is_glider = preset_name in ('glider_pw5', 'motoglider_aos')
        is_powered = preset_params.get('engine_type', 'none') != 'none'
        is_propeller = preset_params.get('engine_type') in ('piston', 'turboprop')
        
        if not is_glider:
            if 'id="fig-corke"' not in body:
                findings.append(f"MISSING ID in {preset_name}: fig-corke")
        else:
            if 'id="fig-glide-masses"' not in body:
                findings.append(f"MISSING ID in {preset_name}: fig-glide-masses")
                
        for req_fig in ['fig-mass-trend', 'fig-mission', 'fig-schrenk', 'fig-glauert', 'fig-cg']:
            if f'id="{req_fig}"' not in body:
                findings.append(f"MISSING ID in {preset_name}: {req_fig}")
                
        if is_propeller:
            if 'id="fig-propeller"' not in body:
                findings.append(f"MISSING ID in {preset_name}: fig-propeller")
                
        if is_powered:
            for req_fig in ['fig-offer-speeds', 'fig-offer-climb', 'fig-altitude']:
                if f'id="{req_fig}"' not in body:
                    findings.append(f"MISSING ID in {preset_name}: {req_fig}")
                    
        # Check compressibility assessment element count (class="compressibility-assessment" or contains that class)
        comp_count = len(re.findall(r'class="[^"]*compressibility-assessment[^"]*"', body))
        if comp_count != 2:
            findings.append(f"COMPRESSIBILITY COUNT MISMATCH in {preset_name}: found {comp_count}, expected 2")
            
        # Check p4-stall-requirement
        if 'id="p4-stall-requirement"' not in body:
            findings.append(f"MISSING ELEMENT #p4-stall-requirement in {preset_name}")
            
        # Check required data attributes
        for attr in ['data-report-section', 'data-calc', 'data-mass-iteration']:
            if attr not in body:
                findings.append(f"MISSING DATA ATTR in {preset_name}: {attr}")
                
        print(f"  Preset {preset_name}: HTML size={len(html)} chars, Findings so far={len(findings)}")

    print(f"\n=== 2. SEMANTIC VERDICT INTERFACE CONTRACTS ===")
    base_result = run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos']))
    
    # Contract 1: P3 static margin not met -> 'nie jest spełnione'
    c1_res = deepcopy(base_result)
    c1_res['balance']['stability']['static_margin_aft_pct'] = 2
    c1_doc = report_document(c1_res, ['p3'])
    p3_text = ' '.join(c1_doc['conclusions']['p3'])
    if 'nie jest spełnione' not in p3_text:
        findings.append(f"CONTRACT 1 FAILED: 'nie jest spełnione' not in P3 conclusion: {p3_text}")
    else:
        print("  Contract 1 (P3 static margin 'nie jest spełnione'): PASS")
        
    # Contract 2: P5 climb rate not met -> 'nie jest spełniony'
    c2_res = deepcopy(base_result)
    c2_res['performance']['climb']['wy_max_ms'] = 0
    c2_doc = report_document(c2_res, ['p5'])
    p5_text = ' '.join(c2_doc['conclusions']['p5'])
    if 'nie jest spełniony' not in p5_text:
        findings.append(f"CONTRACT 2 FAILED: 'nie jest spełniony' not in P5 conclusion: {p5_text}")
    else:
        print("  Contract 2 (P5 climb 'nie jest spełniony'): PASS")
        
    # Contract 3: P6 gust governing -> 'Wymiarujące są również obciążenia podmuchowe'
    c3_res = deepcopy(base_result)
    c3_res['envelope']['limits']['n_gust_max'] = c3_res['envelope']['limits']['n_max'] + 1
    c3_doc = report_document(c3_res, ['p6'])
    p6_text = ' '.join(c3_doc['conclusions']['p6'])
    if 'Wymiarujące są również obciążenia podmuchowe' not in p6_text:
        findings.append(f"CONTRACT 3 FAILED: 'Wymiarujące są również obciążenia podmuchowe' not in P6: {p6_text}")
    else:
        print("  Contract 3 (P6 gust governing): PASS")
        
    # Contract 4: Glider P2 -> 'Dla szybowca pominięto dobór mocy'
    # Contract 5: Glider P5 -> 'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano'
    glider_res = run_bipol_project(dict(AIRCRAFT_PRESETS['glider_pw5']))
    glider_doc = report_document(glider_res, ['p2', 'p5'])
    p2_g_text = ' '.join(glider_doc['conclusions']['p2'])
    p5_g_text = ' '.join(glider_doc['conclusions']['p5'])
    if 'Dla szybowca pominięto dobór mocy' not in p2_g_text:
        findings.append(f"CONTRACT 4 FAILED: 'Dla szybowca pominięto dobór mocy' not in P2 glider: {p2_g_text}")
    else:
        print("  Contract 4 (P2 glider power): PASS")
    if 'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano' not in p5_g_text:
        findings.append(f"CONTRACT 5 FAILED: 'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano' not in P5 glider: {p5_g_text}")
    else:
        print("  Contract 5 (P5 glider climb): PASS")

    print(f"\n=== 3. DIRECT FILE SCAN OF 11 TEMPLATE AND SOURCE FILES ===")
    FILES_TO_SCAN = [
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\report.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p1.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p2.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p3.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p4.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p5.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\p6.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\mass_iteration.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\ballast.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\templates\reports\compressibility.html',
        r'C:\Users\Michał\Documents\antigravity\bipol\calculations\report_document.py',
    ]
    
    SOURCE_BLACKLIST = [
        "ŚDA", "ft/s", "lbf/ft", "simplex", "przypadków zdegenerowanych",
        "nie gorszych niż", "Większe wydłużenie zmniejsza opór",
        "w trzech krokach", "guideline-steps", "1. Zakłada się masę startową",
        "różnica wynosi 0,00 kg", "nierówności liniowej względem masy osoby",
        "Jednostka współczynnika a wynika", "pułap teoretyczny jest osiągany asymptotycznie",
        "nie zastępują badań w locie", "Każdą obliczaną wielkość zapisano wzorem ogólnym",
        "commuter.."
    ]
    
    for fpath in FILES_TO_SCAN:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        for term in SOURCE_BLACKLIST:
            if term in content:
                findings.append(f"SOURCE BLACKLIST HIT in {fpath}: '{term}'")
        # Check for double dots
        double_dots = re.findall(r'([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,}\.\.[^\.])', content)
        if double_dots:
            findings.append(f"SOURCE DOUBLE DOT in {fpath}: {double_dots}")
            
    print(f"\n=== SUMMARY OF FINDINGS ===")
    if not findings:
        print("ALL TESTS PASSED! ZERO FINDINGS FOUND.")
    else:
        print(f"FOUND {len(findings)} ISSUES:")
        for idx, f in enumerate(findings, 1):
            print(f"[{idx}] {f}")
            
    return findings

if __name__ == '__main__':
    findings = run_adversarial_scan()
    sys.exit(0 if not findings else 1)
