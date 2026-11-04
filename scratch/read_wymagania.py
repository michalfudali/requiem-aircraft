import pdfplumber
import glob
import os

pdf_files = glob.glob('scraped_materials/bipol/*.pdf')

for path in sorted(pdf_files):
    fname = os.path.basename(path)
    try:
        with pdfplumber.open(path) as pdf:
            found = []
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                for line in text.splitlines():
                    l = line.lower()
                    if ('cs-22' in l or 'cs 22' in l or 'motoszybow' in l or 'przeciąg' in l or 'v_s' in l or 'vs0' in l or 'vso' in l or 'stall' in l):
                        found.append(f"P{idx+1}: {line}")
            if found:
                print(f"=== {fname} ===")
                for f in found[:10]:
                    print(f)
                if len(found) > 10:
                    print(f"... and {len(found)-10} more lines")
    except Exception as e:
        pass
