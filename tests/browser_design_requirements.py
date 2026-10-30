"""Browser round trips, engineering iteration and concrete topic-constraint repros."""
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
OUT = ROOT / "work" / "design-integrity-20261030"
os.environ["BIPOL_AIRCRAFT_DB"] = str(OUT / "requirements-catalogue.sqlite3")
OUT.mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/"data/aircraft/aircraft.sqlite3",OUT/"requirements-catalogue.sqlite3")
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, edit_inputs


def save(records):
    (OUT / "interaction-audit.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    server = make_server("127.0.0.1", 5088, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
        page.goto("http://127.0.0.1:5088")
        page.wait_for_function("currentResults !== null", timeout=60000)
        for number in [7, 17, 20, 28, 32, 42, 43, 63, 68, 82, 94, 95, 101]:
            record = dict(topic=number)
            try:
                file = OUT / ("topic-%03d" % number) / "project.json"
                for _ in range(120):
                    if file.exists():
                        break
                    time.sleep(.5)
                exported = json.loads(file.read_text(encoding="utf-8"))
                expected = json.loads((file.parent / "edited-results.json").read_text(encoding="utf-8"))
                old_id = page.evaluate("getActiveProjectId()")
                page.locator("#projectImportFileInput").set_input_files(file)
                page.wait_for_function("getActiveProjectId() !== " + json.dumps(old_id) + " && currentResults?.params?.topic_id === " + str(number), timeout=60000)
                page.wait_for_function("!document.querySelector('#calcBtn').disabled")
                before = page.evaluate("currentResults")
                assert abs(before["mass"]["m0"] - expected["mass"]["m0"]) < .01
                assert before["params"]["range_km"] == expected["params"]["range_km"]
                source_id = page.evaluate("getActiveProjectId()")
                original_params = page.evaluate("JSON.stringify(getActiveProject().params)")
                record["import_roundtrip"] = True
                navigate(page, "tab-coursework")
                page.locator("#courseworkIterate").click()
                page.wait_for_function("getActiveProjectId() !== " + json.dumps(source_id) + " && currentResults?.params?.name?.includes('P2←P4')", timeout=60000)
                page.wait_for_function("!document.querySelector('#calcBtn').disabled")
                after = page.evaluate("currentResults")
                assert after['performance']['paturski_p6']['range_endurance_6_5']['range_at_requested_speed_km'] >= after['params']['range_km']
                assert after['mass']['preliminary_polar']['cx0'] == after['params']['cx0']
                assert abs(after["params"]["cx0"] - before["aerodynamics"]["cx0_clean"]) < .000001
                assert abs(after["params"]["oswald_e"] - before["aerodynamics"]["oswald_e"]) < .000001
                unchanged = page.evaluate("JSON.stringify(getProjectsList().find(p => p.id === " + json.dumps(source_id) + ").params)")
                assert unchanged == original_params
                record["polar_iteration"] = dict(source_preserved=True, mtow_before=before["mass"]["m0"],
                    mtow_after=after["mass"]["m0"], required_range=after["params"]["range_km"],
                    range_before=before["performance"]["paturski_p6"]["range_endurance_6_5"]["range_at_requested_speed_km"],
                    range_after=after["performance"]["paturski_p6"]["range_endurance_6_5"]["range_at_requested_speed_km"])
                page.locator("#projectSwitcherSelect").select_option(source_id)
                page.wait_for_function("getActiveProjectId() === " + json.dumps(source_id) + " && !currentResults?.params?.name?.includes('P2←P4')", timeout=60000)
                record["switch_back"] = True
                record["passed"] = True
            except Exception:
                record["passed"] = False
                record["failure"] = traceback.format_exc()
                page.screenshot(path=str(OUT / ("interaction-failure-%03d.png" % number)), full_page=True)
            records.append(record)
            save(records)
            print(json.dumps(record, ensure_ascii=True), flush=True)
        # Work modes and recovery from an invalid design assumption, using visible controls.
        recovery = {"probe": "work_modes_and_invalid_input"}
        try:
            navigate(page, "tab-inputs")
            for mode in ["construction", "didactic"]:
                page.locator('[data-work-mode="' + mode + '"]').click()
                assert page.locator("body").evaluate("(el)=>el.classList.contains('mode-" + mode + "')")
                for width in [1440, 390, 320]:
                    page.set_viewport_size({"width": width, "height": 900})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (mode, width)
            page.set_viewport_size({"width": 1440, "height": 1000})
            field = edit_inputs(page, "aspect_ratio")
            original = field.input_value()
            field.fill("0")
            page.locator("#calcBtn").click()
            page.wait_for_function("document.querySelector('#calculationStatus').classList.contains('is-error')")
            field.fill(original)
            page.locator("#calcBtn").click()
            page.wait_for_function("document.querySelector('#openReportBtn').dataset.resultsStale === 'false'")
            recovery["passed"] = True
        except Exception:
            recovery["passed"] = False
            recovery["failure"] = traceback.format_exc()
        records.append(recovery)
        # Reproduce the 100-kW topic accepting a 180-kW engine through the wizard.
        limit = {"probe": "topic32_180kw_ui"}
        try:
            page.locator(".quiet-project-menu>summary").click()
            page.locator("#btnNewProjectWizard").click()
            page.locator("#wiz_topic").select_option("topic_32")
            page.locator("#wiz_name").fill("Dowód: temat 32, moc 180 kW")
            page.locator('.wizard-step-tab[data-step="3"]').click()
            page.locator("#wiz_power_input_mode").select_option("fixed")
            page.locator("#wiz_engine_power_kw").fill("180")
            page.screenshot(path=str(OUT / "topic32-180kw-wizard.png"), full_page=True)
            page.locator('.wizard-step-tab[data-step="5"]').click()
            page.locator("#wizFinishBtn").click()
            page.wait_for_function("!document.querySelector('#projectWizardBackdrop').classList.contains('active')", timeout=60000)
            r = page.evaluate("currentResults")
            limit.update(accepted=r["status"] == "success", actual_power_kw=r["sizing"]["design_point"]["power_kw"],
                         explicit_limit_checks=[c for c in r["compliance_checks"] if "100 kW" in str(c)])
            power_check=next(c for c in r['compliance_checks'] if 'Maksymalna moc zainstalowana' in c['parameter'])
            assert not power_check['passed'] and power_check['required']=='≤ 100 kW'
            limit['detected']=True
            limit['passed']=True
            navigate(page, "tab-compliance")
            page.screenshot(path=str(OUT / "topic32-180kw-checks.png"), full_page=True)
        except Exception:
            limit['passed']=False
            limit["failure"] = traceback.format_exc()
        records.append(limit)
        for number, count in [(38,2),(7,1),(37,1)]:
            check=dict(probe='engine_topic_switch',topic=number,expected=count)
            try:
                page.locator('.quiet-project-menu>summary').click()
                page.locator('#btnNewProjectWizard').click()
                page.locator('#wiz_topic').select_option('topic_'+str(number))
                page.locator('.wizard-step-tab[data-step="3"]').click()
                assert int(page.locator('#wiz_n_engines').input_value())==count
                page.screenshot(path=str(OUT/('engine-switch-%03d.png'%number)),full_page=True)
                page.locator('.wizard-step-tab[data-step="5"]').click()
                page.locator('#wizFinishBtn').click()
                page.wait_for_function("!document.querySelector('#projectWizardBackdrop').classList.contains('active')",timeout=60000)
                assert page.evaluate('currentResults.params.n_engines')==count
                check['passed']=True
            except Exception:
                check['passed']=False;check['failure']=traceback.format_exc()
            records.append(check)
        assert not errors, errors
        records.append(dict(probe="javascript_errors", errors=errors, passed=not errors))
        save(records)
        context.close()
        browser.close()
    server.shutdown()
    return 0 if all(record['passed'] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
