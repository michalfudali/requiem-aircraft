"""Isolated application regression: 13 official aircraft workflows in Chrome.

Run from this worktree with its Flask server on port 5087. Browser actions use
visible controls; JavaScript evaluation only reads application results and DOM.
"""
from __future__ import annotations

import json
import math
import sys
import time
import traceback
import argparse
import os
import threading
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright
from browser_helpers import navigate, reveal_details
from calculations.atmosphere import G0, RHO0
from calculations.official_topics import ALL_TOPICS

OUT = ROOT / "work" / "design-integrity-20261030"
BASE = "http://127.0.0.1:5087"
CHOSEN = [7, 17, 20, 28, 32, 42, 43, 63, 68, 82, 94, 95, 101]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def physics(result):
    m, g, a, p, perf = (result[k] for k in ("mass", "geometry", "aerodynamics", "params", "performance"))
    wing = g["wing"]
    checks = []

    def check(name, actual, expected, tolerance):
        checks.append(dict(name=name, actual=actual, expected=expected, tolerance=tolerance,
                           passed=abs(actual - expected) <= tolerance))

    check("mass_balance_kg", m["m0"], m["m_empty"] + m["m_fuel"] + m["m_payload"] + m["m_crew"], 1.0)
    check("aspect_ratio", wing["AR"], wing["b"] ** 2 / wing["S"], .04)
    for phase, coefficient in [("clean", "cz_max_clean"), ("to", "cz_max_to"), ("lnd", "cz_max_lnd")]:
        expected = math.sqrt(2 * m["m0"] * G0 / (RHO0 * wing["S"] * a[coefficient])) * 3.6
        check("stall_" + phase + "_kmh", perf["speeds"]["vs_" + phase + "_kmh"], expected, .06)
    cruise = perf["cruise_check"]
    check("excess_power_climb_ms", cruise["climb_ms"],
          (cruise["available_w"] - cruise["required_w"]) / (cruise["mass_kg"] * G0), .000001)
    rows = result["bipol_projects"]["p3"]["table_3_1_components"]
    cg = sum(row["mass_kg"] * row["x_m"] for row in rows) / sum(row["mass_kg"] for row in rows)
    cg_result = next(state["xcg_m"] for state in result["balance"]["loading_states"] if state["key"] == "mtow")
    check("component_moment_cg_m", cg_result, cg, .006)
    phases = m.get("mission_phases", [])
    for before, after in zip(phases, phases[1:]):
        check("phase_continuity_" + after["key"], before["mass_end_kg"], after["mass_start_kg"], .2)
    checks.append(dict(name="mission_mass_nonincreasing", passed=all(
        phase["mass_end_kg"] <= phase["mass_start_kg"] + .1 for phase in phases)))
    if p['operating_surface']=='water':
        checks.append(dict(name='water_takeoff_unmodelled',passed=perf['takeoff']['distance_to_15m'] is None))
        checks.append(dict(name='water_landing_unmodelled',passed=perf['landing']['distance_from_15m'] is None))
    else:
        checks.append(dict(name='landing_distance_includes_ground_roll',passed=perf['landing']['distance_from_15m']>=perf['landing']['ground_roll_m']))
        check('takeoff_distance_components_m',perf['takeoff']['distance_to_15m'],perf['takeoff']['ground_roll_m']+perf['takeoff']['air_distance_m'],.2)
    return checks


def run_case(browser, topic):
    case_dir = OUT / ("topic-%03d" % topic["num"])
    case_dir.mkdir(exist_ok=True)
    record = dict(num=topic["num"], category=topic["category"], title=topic["title"], steps=[], errors=[])
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page = context.new_page()
    page.on("pageerror", lambda error: record["errors"].append(str(error)))
    responses = []
    page.on("response", lambda response: responses.append(dict(status=response.status, url=response.url))
            if response.status >= 400 else None)
    started = time.monotonic()
    try:
        page.goto(BASE)
        page.wait_for_function("typeof currentResults !== 'undefined' && currentResults !== null", timeout=60000)
        page.locator(".quiet-project-menu>summary").click()
        page.locator("#btnNewProjectWizard").click()
        page.locator("#wiz_topic").select_option("topic_" + str(topic["num"]))
        case_name = "Audyt %03d %s" % (topic["num"], topic["category"])
        page.locator("#wiz_name").fill(case_name)
        record["steps"].append("new_project_topic_selected")
        for step in range(1, 6):
            page.locator('.wizard-step-tab[data-step="%d"]' % step).click()
            record["steps"].append("wizard_step_%d" % step)
        page.screenshot(path=str(case_dir / "wizard-summary.png"), full_page=True, animations="disabled")
        page.locator("#wizFinishBtn").click()
        page.wait_for_function("!document.querySelector('#projectWizardBackdrop').classList.contains('active') || !!document.querySelector('#wizardValidationStatus').textContent.trim()", timeout=60000)
        if page.locator("#projectWizardBackdrop.active").count():
            raise AssertionError("Wizard rejected topic: " + page.locator("#wizardValidationStatus").inner_text())
        page.wait_for_function("currentResults?.params?.name === " + json.dumps(case_name), timeout=60000)
        result = page.evaluate("currentResults")
        write_json(case_dir / "results.json", result)
        assert result['params']['n_engines']==topic['parameters']['n_engines']
        assert result['params']['n_pax']==topic['parameters']['n_pax']
        assert result['design_iteration']['converged']
        assert result['performance']['paturski_p6']['range_endurance_6_5']['range_at_requested_speed_km']>=result['params']['range_km']
        if topic['category']=='wyscigowe_akro':
            assert result['envelope']['limits']['n_max']==6
        if result['params']['operating_surface']=='water':
            assert result['performance']['takeoff']['distance_to_15m'] is None
            assert page.locator('#studioModelScope').is_visible()

        record["steps"].append("calculated_saved")
        record["result"] = dict(params=result["params"], mass=result["mass"]["m0"],
                                geometry=result["geometry"]["wing"],
                                engine=result["sizing"]["design_point"],
                                checks=result["compliance_checks"])
        record["physics"] = physics(result)
        assert all(c['passed'] for c in record['physics']), record['physics']
        for target in ["tab-overview", "tab-trends", "tab-p1-p2", "tab-p3", "tab-p4", "tab-p5", "tab-p6", "tab-compliance"]:
            navigate(page, target)
            page.wait_for_timeout(120)
            if not page.locator("#" + target).is_visible():
                raise AssertionError("Analysis pane not visible: " + target)
            record["steps"].append(target)
            if target in ("tab-overview", "tab-p3", "tab-p5", "tab-p6"):
                page.screenshot(path=str(case_dir / (target + ".png")), full_page=True, animations="disabled")
        # A real edit and recomputation, followed by reload, must keep the selected topic.
        page.locator(".quiet-project-menu>summary").click()
        page.locator("#btnEditProjectWizard").click()
        edited_range = float(result["params"]["range_km"]) + 10
        page.locator("#wiz_basis_range_km").fill(str(edited_range))
        page.locator('.wizard-step-tab[data-step="5"]').click()
        page.locator("#wizFinishBtn").click()
        page.wait_for_function("!document.querySelector('#projectWizardBackdrop').classList.contains('active')", timeout=60000)
        page.wait_for_function("currentResults.params.range_km === " + str(edited_range), timeout=60000)
        page.reload()
        page.wait_for_function("currentResults?.params?.range_km === " + str(edited_range), timeout=60000)
        assert page.evaluate("currentResults.params.topic_id") == topic["num"]
        record["steps"].append("edit_recalculate_reload")
        final = page.evaluate("currentResults")
        write_json(case_dir / "edited-results.json", final)
        assert final['design_iteration']['converged'], final['design_iteration']
        assert final['performance']['mission_range']['passed'], final['performance']['mission_range']
        record['edited_physics'] = physics(final)
        assert all(c['passed'] for c in record['edited_physics']), record['edited_physics']
        navigate(page, "tab-reports")
        for checkbox in page.locator('[name="studio-report-section"]').all():
            reveal_details(checkbox)
            checkbox.check()
        for action, filename in [("download-report", "report.html"), ("export-json", "project.json"),
                                 ("export-csv", "results.csv"), ("download-report-docx", "report.docx")]:
            control = page.locator('[data-studio-action="' + action + '"]')
            reveal_details(control)
            with page.expect_download(timeout=90000) as download:
                control.click()
            download.value.save_as(case_dir / filename)
            record["steps"].append(action)
        # Reopen the actual downloaded report with networking disabled.
        offline = browser.new_context(offline=True, viewport={"width": 1200, "height": 1000})
        report = offline.new_page()
        report.on("pageerror", lambda error: record["errors"].append("REPORT: " + str(error)))
        report.goto((case_dir / "report.html").as_uri(), wait_until="load")
        report.evaluate("document.fonts.ready")
        record["report"] = dict(sections=report.locator("[data-report-section]").count(),
                                formulas=report.locator(".katex").count(),
                                formula_errors=report.locator(".katex-error").count(),
                                figures=report.locator("figure svg").count(),
                                contains_name=case_name in report.locator("body").inner_text())
        assert record["report"]["sections"] == 6, record["report"]
        assert record["report"]["formula_errors"] == 0, record["report"]
        assert record["report"]["formulas"] > 30, record["report"]
        assert record["report"]["contains_name"], record["report"]
        report.screenshot(path=str(case_dir / "report-offline.png"), full_page=False, animations="disabled")
        report.emulate_media(media="print")
        report.pdf(path=str(case_dir / "report.pdf"), prefer_css_page_size=True, print_background=True)
        offline.close()
        record["steps"].append("offline_report_pdf")
        for width in [390, 320]:
            page.set_viewport_size({"width": width, "height": 900})
            for target in ["tab-overview", "tab-inputs", "tab-p5"]:
                navigate(page, target)
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                if overflow:
                    record.setdefault("mobile_overflow", []).append(dict(width=width, target=target))
            if width == 390:
                page.screenshot(path=str(case_dir / "mobile-390.png"), full_page=True, animations="disabled")
        record["steps"].append("mobile_320_390")
        record["http_errors"] = responses
        record["passed"] = not record["errors"] and not responses and not record.get('mobile_overflow')
    except Exception:
        record["passed"] = False
        record["failure"] = traceback.format_exc()
        page.screenshot(path=str(case_dir / "failure.png"), full_page=True, animations="disabled")
    finally:
        record["seconds"] = round(time.monotonic() - started, 1)
        write_json(case_dir / "audit.json", record)
        context.close()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", nargs="+", type=int, default=CHOSEN)
    parser.add_argument("--serve", action="store_true", help="Run this worktree's isolated server in a thread")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True, parents=True)
    server = None
    if args.serve:
        os.environ["BIPOL_AIRCRAFT_DB"] = str(OUT / "browser-catalogue.sqlite3")
        shutil.copyfile(ROOT / "data" / "aircraft" / "aircraft.sqlite3",OUT / "browser-catalogue.sqlite3")
        from app import app
        from werkzeug.serving import make_server
        server = make_server("127.0.0.1", 5087, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", headless=True)
        for number in args.topics:
            topic = next(t for t in ALL_TOPICS if t["num"] == number)
            record = run_case(browser, topic)
            records.append(record)
            write_json(OUT / ("browser-summary-" + "-".join(map(str, args.topics)) + ".json"), records)
            print(json.dumps(dict(num=number, passed=record["passed"], steps=record["steps"],
                                  failure=record.get("failure"), physics_error=record.get("physics_error"),
                                  seconds=record["seconds"]), ensure_ascii=True), flush=True)
        browser.close()
    if server:
        server.shutdown()
    return 0 if all(r["passed"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
