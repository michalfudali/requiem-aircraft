import pdfplumber
import glob

def check_file(path, words):
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages):
            txt = page.extract_text() or ''
            for line in txt.splitlines():
                if any(w.lower() in line.lower() for w in words):
                    try:
                        print(f"{path} P{idx+1}: {line}")
                    except Exception:
                        pass

for f in sorted(glob.glob('scraped_materials/bipol/okBIPOL_1_handout_*.pdf')):
    check_file(f, ['cs-22', 'cs 22', 'motoszybowiec', 'przeciąg', 'prędkość min'])
