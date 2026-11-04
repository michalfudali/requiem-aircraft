import pdfplumber

with pdfplumber.open('scraped_materials/bipol/okBIPOL_1_handout_2.pdf') as pdf:
    for i, p in enumerate(pdf.pages):
        txt = p.extract_text() or ''
        lines = txt.splitlines()
        for line in lines:
            l = line.lower()
            if any(k in l for k in ['prędkość', 'vs', 'przeciąg', 'stall', 'km/h', 'węzł', 'cs-23', 'cs-22', 'limit', 'vso', 'vs1']):
                print(f"P{i+1}: {line}")
