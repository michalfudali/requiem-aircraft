/* Pracownia inspirowana załączonym projektem; wykorzystuje istniejące API BIPOL. */
(function () {
  'use strict';
  const {escape: esc, format: fmt, filename, snapshot, metrics, csv, resultRows} = BipolStudio;
  const VARIANTS_KEY = 'bipol_studio_variants_v1';
  const wideTabs = new Set(['tab-overview', 'tab-inputs', 'tab-calculation-tree', 'tab-variants', 'tab-reports', 'tab-glide', 'tab-methods', 'tab-trends', 'tab-coursework']);
  let view = 'iso', fresh = false, resultProject = null, messageTimer;
  let aircraftModel, aircraftResult, aircraftCamera = BipolAircraftPreview.camera(), aircraftFrame;
  let aircraftProportions = 'concept';
  const $ = id => document.getElementById(id);
  const announce = (message, error = false) => {
    const el = $('studioMessage');
    el.textContent = message;
    el.classList.toggle('error', error);
    el.hidden = !message;
    clearTimeout(messageTimer);
    messageTimer = setTimeout(() => { el.hidden = true; }, error ? 9000 : 5000);
  };

  function navigationOpen(open, restoreFocus = false) {
    document.body.classList.toggle('studio-nav-open', open);
    $('studioMenuToggle').setAttribute('aria-expanded', String(open));
    const sidebar = $('studioSidebar');
    sidebar.inert = window.innerWidth <= 1100 && !open;
    if (open) {
      sidebar.scrollTop = 0;
      sidebar.querySelector('button')?.focus({preventScroll: true});
    } else if (restoreFocus && window.innerWidth <= 1100) $('studioMenuToggle').focus({preventScroll: true});
  }

  function navigate(target) {
    const nav = document.querySelector(`[data-studio-nav="${target}"]`);
    if (nav?.closest('details')) nav.closest('details').open = true;
    setPortalMode('holistic');
    document.querySelector(`.bipol-tab[data-target="${target}"]`)?.click();
    navigationOpen(false, true);
    window.scrollTo({top: 0, behavior: 'instant'});
  }

  function syncNavigation() {
    const target = document.querySelector('.tab-content.active')?.id || 'tab-overview';
    document.body.dataset.workspaceView = currentPortalMode === 'projects' ? 'semester' : target;
    const selectedNav = document.querySelector(`[data-studio-nav="${target}"]`);
    if (selectedNav?.closest('details')) selectedNav.closest('details').open = true;
    document.body.classList.toggle('studio-wide', currentPortalMode === 'holistic' && wideTabs.has(target));
    document.body.classList.toggle('studio-trends', currentPortalMode === 'holistic' && target === 'tab-trends');
    document.querySelectorAll('[data-studio-nav]').forEach(button => {
      const selected = currentPortalMode === 'holistic' && button.dataset.studioNav === target;
      button.classList.toggle('active', selected);
      if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
    });
    const current = document.querySelector('.studio-nav-item.active');
    $('studioBreadcrumb').textContent = currentPortalMode === 'projects' ? 'Projekty semestralne P1–P6' : current?.querySelector('span:nth-of-type(2)')?.textContent.trim() || 'Pracownia';
  }

  function variants() {
    const list = projectStore.read(VARIANTS_KEY, []);
    return Array.isArray(list) ? list.filter(v => v?.schema === 1 && v.params && v.metrics && typeof v.name === 'string').slice(0, 8) : [];
  }

  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const a = document.createElement('a');
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function calculated() {
    if (!fresh || resultProject !== getActiveProjectId()) await performCalculation();
    if (!fresh || !currentResults || resultProject !== getActiveProjectId()) throw new Error('Uzupełnij poprawnie parametry i oblicz projekt.');
    return currentResults;
  }

  function renderAircraft() {
    if (!currentResults) return;
    if (aircraftResult !== currentResults) {
      aircraftResult = currentResults;
      aircraftModel = BipolAircraftPreview.model(currentResults, {proportions:aircraftProportions});
      $('studioAircraftLegend').innerHTML = aircraftModel.parts.filter(part => ['engine','propeller','flap','aileron','flaperon','slat'].includes(part.id))
        .map(part => `<span><i style="background:${part.color}"></i>${esc(part.label)}</span>`).join('');
    }
    const stage=$('studioAircraft');
    let mesh=stage.querySelector('canvas');
    stage.querySelector('svg')?.remove();
    stage.insertAdjacentHTML('afterbegin',BipolAircraftPreview.render(aircraftModel, view, aircraftCamera));
    if(!mesh) {mesh=document.createElement('canvas');mesh.setAttribute('aria-hidden','true');stage.append(mesh);}
    const svg=stage.querySelector('svg'), box=svg.getBoundingClientRect();
    let solid=false;
    if(box.width&&box.height) solid=BipolAircraftPreview.draw(mesh,aircraftModel,view,aircraftCamera,
      {width:box.width,height:box.height,pixelRatio:window.devicePixelRatio});
    mesh.style.width=`${box.width}px`;mesh.style.height=`${box.height}px`;mesh.hidden=!solid;
    stage.classList.toggle('is-solid-preview',solid);
    for (const key of ['yaw','elevation']) {
      $(`studioAircraft_${key}`).value = Math.round(aircraftCamera[key]);
      $(`studioAircraft_${key}Value`).value = `${Math.round(aircraftCamera[key])}°`;
    }
    document.querySelectorAll('[data-aircraft-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.aircraftView === view)));
  }

  function rotateAircraft(orientation) {
    aircraftCamera = BipolAircraftPreview.camera('iso', orientation);
    view = 'custom';
    if (aircraftFrame) return;
    aircraftFrame = requestAnimationFrame(() => { aircraftFrame = null; renderAircraft(); });
  }

  function renderProjectGuidance() {
    const card = $('studioProjectHealth'), button = $('studioNextAction');
    if (!card || !button) return;
    const failed = currentResults?.compliance_checks?.filter(check => !check.passed).length || 0;
    let state, title, description, label, target = 'tab-inputs';
    if ($('calcBtn').disabled) {
      state = 'calculating'; title = 'Obliczamy Twój projekt';
      description = 'Za chwilę pojawią się zaktualizowane wyniki i podgląd samolotu.'; label = 'Obliczanie…';
    } else if ($('calculationStatus').classList.contains('is-error')) {
      state = 'error'; title = 'Sprawdź wprowadzone dane';
      description = 'Nie udało się odświeżyć wyników. Szczegóły znajdziesz przy przycisku przeliczania w założeniach.'; label = 'Popraw założenia';
    } else if (!fresh || resultProject !== getActiveProjectId()) {
      state = currentResults ? 'stale' : 'waiting'; title = currentResults ? 'Przelicz po zmianach' : 'Zacznij od założeń';
      description = currentResults ? 'Wyświetlane wyniki pochodzą z poprzednich obliczeń. Odśwież je dla obecnych założeń.' : 'Uzupełnij wymagania misji. Na ich podstawie obliczymy parametry samolotu.';
      label = currentResults ? 'Przelicz projekt' : 'Uzupełnij założenia';
    } else if (failed) {
      state = 'attention'; title = 'Wyniki gotowe. Zobacz uwagi';
      description = 'Nie wszystkie wymagania są spełnione. Zobacz, które parametry warto zmienić przed przygotowaniem raportu.';
      label = 'Sprawdź wymagania'; target = 'tab-compliance';
    } else {
      state = 'ready'; title = 'Możesz przygotować raport';
      description = 'Wyniki są aktualne. Dodaj wnioski i wybierz, które części projektu chcesz zapisać.';
      label = 'Przygotuj raport'; target = 'tab-reports';
    }
    card.dataset.state = state;
    $('studioNextTitle').textContent = title;
    $('studioNextDescription').textContent = description;
    button.textContent = label; button.disabled = state === 'calculating';
    button.removeAttribute('data-studio-action'); button.removeAttribute('data-studio-target');
    if (state === 'stale') button.dataset.studioAction = 'recalculate'; else button.dataset.studioTarget = target;
    const checks = currentResults?.compliance_checks || [];
    $('studioChecksSummary').textContent = ['ready','attention'].includes(state)
      ? `${checks.filter(check => check.passed).length} z ${checks.length} warunków spełnionych`
      : state === 'calculating' ? 'Trwają obliczenia' : state === 'error' ? 'Wyniki wymagają poprawnych danych' : 'Wyniki wymagają przeliczenia';
  }

  function setupAircraftRotation() {
    const canvas = $('studioAircraft');
    new ResizeObserver(()=>{if(currentResults&&canvas.getClientRects().length)requestAnimationFrame(renderAircraft);}).observe(canvas);
    $('studioAircraftProportions').addEventListener('change', event => {
      aircraftProportions = event.target.value; aircraftResult = null;
      $('studioAircraftModelNote').textContent = aircraftProportions === 'concept'
        ? 'Bryła poglądowa. Czytelne proporcje dopasowane do klasy samolotu.'
        : 'Długości i średnice pochodzą z obliczeń wstępnych projektu.';
      renderAircraft();
    });
    let drag;
    canvas.addEventListener('pointerdown', event => {
      if (!currentResults || !event.isPrimary || event.button !== 0) return;
      drag = {id:event.pointerId, x:event.clientX, y:event.clientY, camera:{...aircraftCamera}};
      canvas.setPointerCapture(event.pointerId);
      canvas.classList.add('is-rotating');
      canvas.focus({preventScroll:true});
      event.preventDefault();
    });
    canvas.addEventListener('pointermove', event => {
      if (!drag || event.pointerId !== drag.id) return;
      rotateAircraft({yaw:drag.camera.yaw+(event.clientX-drag.x)*.45,
        elevation:drag.camera.elevation+(event.clientY-drag.y)*.45});
    });
    const finish = event => {
      if (!drag || event.pointerId !== drag.id) return;
      drag = null; canvas.classList.remove('is-rotating');
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    };
    for (const name of ['pointerup','pointercancel','lostpointercapture']) canvas.addEventListener(name, finish);
    canvas.addEventListener('keydown', event => {
      if (event.key === 'Home') {
        event.preventDefault(); view = 'iso'; aircraftCamera = BipolAircraftPreview.camera(); renderAircraft(); return;
      }
      if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const step = event.shiftKey ? 2 : 10;
      rotateAircraft({yaw:aircraftCamera.yaw+({'ArrowLeft':-step,'ArrowRight':step}[event.key] || 0),
        elevation:aircraftCamera.elevation+({'ArrowUp':step,'ArrowDown':-step}[event.key] || 0)});
    });
    for (const key of ['yaw','elevation']) $(`studioAircraft_${key}`).addEventListener('input', event => {
      rotateAircraft({...aircraftCamera,[key]:Number(event.target.value)});
    });
  }

  function renderOverview(result) {
    const p = result.params, m = result.mass, w = result.geometry.wing;
    for (const [id,value,digits,unit] of [['kpi_m0',m.m0,1,'kg'],['kpi_wing_s',w.S,2,'m²'],
      ['kpi_wingspan',w.b,2,'m'],['kpi_wy_max',result.performance.climb.wy_max_ms,2,'m/s']]) {
      $(id).textContent = `${fmt(value,digits)} ${unit}`;
    }
    $('studioProjectName').textContent = getActiveProject()?.name || p.name;
    const engine = p.engine_type === 'none' ? 'Bez napędu' : p.engine_type === 'jet' ? 'Napęd odrzutowy' : 'Napęd śmigłowy';
    const layout = {low: 'Dolnopłat', mid: 'Średniopłat', high: 'Górnopłat', braced_high: 'Górnopłat zastrzałowy'}[w.wing_config] || 'Płat stały';
    $('studioProjectDescription').textContent = `${layout} · ${m.unmanned ? 'UAV, bez załogi na pokładzie' : `${m.n_crew + m.n_pax} os. na pokładzie`} · ${engine}`;
    const checks = result.compliance_checks || [];
    $('studioChecksSummary').textContent = `${checks.filter(c => c.passed).length} / ${checks.length} sprawdzeń spełnionych`;
    const total = m.m0;
    $('studioMassBars').innerHTML = [
      ['Masa pusta', m.m_empty, '#168c83'], ['Załoga i ładunek', m.m_crew + m.m_payload, '#667ed5'], ['Paliwo', m.m_fuel, '#d89b45']
    ].map(([label, value, color]) => `<div class="studio-mass-row"><span>${label}</span><strong>${fmt(value)} kg <small class="studio-mass-share">${fmt(value / total * 100,0)}%</small></strong><div><i style="width:${Math.min(100, value / total * 100)}%;background:${color}"></i></div></div>`).join('');
    $('studioMassClosure').textContent = `Masa startowa ${fmt(total)} kg · suma składników ${fmt(m.m_empty + m.m_crew + m.m_payload + m.m_fuel)} kg`;
    const orderedChecks = [...checks].sort((a, b) => Number(a.passed) - Number(b.passed));
    $('studioChecks').innerHTML = orderedChecks.slice(0, 4).map(c => {
      return `<div class="studio-check"><span class="studio-check-icon ${c.passed ? 'pass' : 'attention'}">${c.passed ? '✓' : '!'}</span><div><strong>${esc(c.parameter)}</strong><small>${esc(c.required)} · wynik: ${esc(c.actual)}${typeof window.complianceFixButton === 'function' ? ' ' + window.complianceFixButton(c) : ''}</small></div></div>`;
    }).join('');
    $('studioMission').innerHTML = `<svg viewBox="0 0 650 145" role="img" aria-label="Schemat misji: start, wznoszenie, przelot i rezerwa"><path d="M25 95H625" stroke="#cbdadd" stroke-dasharray="4 4"/><path d="M25 95H90L175 40H470L535 78H625" fill="none" stroke="#168c83" stroke-width="3"/><text x="25" y="122">Start</text><text x="108" y="122">Wznoszenie</text><text x="245" y="24">${fmt(p.cruise_altitude_m, 0)} m ISA · ${fmt(p.cruise_speed_kmh, 0)} km/h TAS</text><text x="280" y="122">Przelot · ${fmt(p.range_km, 0)} km</text><text x="510" y="122">Rezerwa · ${fmt(p.loiter_time_min ?? 45, 0)} min</text></svg>`;
    if (p.engine_type === 'none') $('studioMission').innerHTML = `<p>Lot bez napędu · wysokość odniesienia ${fmt(p.cruise_altitude_m, 0)} m ISA.</p><p>Założony zasięg misji nie jest prognozą lotu termicznego. Sprawdź doskonałość i opadanie w module lotu szybowego.</p>`;
    renderAircraft();
    renderProjectGuidance();
  }

  function renderGlide(result) {
    const glide = result.performance.glide;
    if (!glide) return;
    const best = glide.best_glide, min = glide.minimum_sink;
    $('studioGlideMetrics').innerHTML = [
      ['Doskonałość maksymalna', fmt(best.ld, 2), '−'],
      ['Prędkość najlepszej doskonałości', fmt(best.v_kmh), 'km/h TAS'],
      ['Minimalne opadanie', fmt(min.sink_ms, 2), 'm/s'],
      ['Wysokość obliczeniowa', fmt(glide.altitude_m, 0), 'm ISA']
    ].map(([label, value, unit]) => `<div><span>${label}</span><strong>${value} <small>${unit}</small></strong></div>`).join('');
    // Zakres czytelny dla lotu szybowego; pełne punkty trafiają do eksportu CSV.
    const points = glide.points.filter(point => point.v_kmh <= best.v_kmh * 2.2);
    $('studioGlideChart').innerHTML = BipolVisuals.chart({
      title: 'Dokładna biegunowa szybowania', xLabel: 'V TAS [km/h]', yLabel: 'Opadanie [m/s]',
      series: [{name: 'Model równowagi sił', data: points.map(point => [point.v_kmh, point.sink_ms])}],
      points: [
        {x: best.v_kmh, y: best.sink_ms, label: 'Najlepsza doskonałość', dx: 10, dy: -11},
        {x: min.v_kmh, y: min.sink_ms, label: 'Min. opadanie', dx: 0, dy: 18, anchor: 'middle'}
      ]
    });
    $('studioGlideModel').textContent = glide.model;
  }

  function comparisonRows() {
    const list = variants();
    const current = currentResults && resultProject === getActiveProjectId() ? snapshot(currentResults, fresh ? 'Aktualny projekt' : 'Ostatni obliczony wynik') : null;
    const all = current ? [current, ...list] : list;
    return {all, rows: [['Parametr', 'Jednostka', ...all.map(v => v.name)], ...metrics.map(([key, label, unit]) => [label, unit, ...all.map(v => v.metrics[key])])]};
  }

  function renderComparison() {
    const {all, rows} = comparisonRows(), saved = variants();
    $('studioComparison').innerHTML = !saved.length ? '<div class="studio-empty"><h2>Zapisz pierwszy wariant bazowy</h2><p>Zmień potem wymagania lub geometrię i porównaj wyniki.</p></div>' : `<div class="table-responsive"><table class="b-table studio-comparison"><thead><tr>${rows[0].map(v => `<th>${esc(v)}</th>`).join('')}</tr></thead><tbody>${metrics.map(([key, label, unit, , precision]) => `<tr><th>${label}</th><td>${unit}</td>${all.map(v => `<td class="num">${fmt(v.metrics[key], precision)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    $('studioVariantList').innerHTML = saved.map(v => `<article class="studio-card"><h2>${esc(v.name)}</h2><p>${esc(new Date(v.date).toLocaleString('pl-PL'))} · MTOW ${fmt(v.metrics.mtow)} kg</p><div class="studio-button-row"><button class="btn btn-outline" data-load-variant="${esc(v.id)}">Otwórz jako nowy projekt</button><button class="btn btn-outline" data-export-variant="${esc(v.id)}">JSON</button><button class="studio-text-button studio-danger" data-delete-variant="${esc(v.id)}" aria-label="Usuń wariant ${esc(v.name)}">Usuń</button></div></article>`).join('');
  }

  function loadEditorial() {
    const editorial = getActiveProject()?.editorial || {};
    $('studioNotes').value = editorial.notes || '';
    $('studioSources').value = editorial.sources || '';
    document.querySelectorAll('[data-studio-metadata]').forEach(input => {
      input.value = document.getElementById(input.dataset.studioMetadata)?.value || getActiveProject()?.params?.[input.dataset.studioMetadata] || '';
    });
  }

  function saveEditorial() {
    const active = getActiveProject();
    if (!active) return;
    active.editorial = {notes: $('studioNotes').value, sources: $('studioSources').value};
    saveProject(active);
  }

  async function downloadRenderedDocx(html) {
    const frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden', 'true');
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:1200px;height:900px;visibility:hidden;pointer-events:none';
    document.body.append(frame);
    try {
      frame.contentDocument.open();
      frame.contentDocument.write(html);
      frame.contentDocument.close();
      await frame.contentWindow.BipolReportEditor.ready;
      const {blob, filename: docName} = await frame.contentWindow.BipolReportEditor.buildDocx();
      download(docName, blob, blob.type);
      return docName;
    } finally {
      frame.remove();
    }
  }

  async function downloadIndividualProjectDocx(pId, btn) {
    const origText = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Generowanie DOCX…'; }
    try {
      saveEditorial();
      const result = await calculated(), editorial = getActiveProject()?.editorial || {};
      const params = {...result.params, report_notes: editorial.notes || '', source_notes: editorial.sources || ''};
      const q = new URLSearchParams({
        student: params.student_name || '',
        album: params.album_no || '',
        group: params.group_no || '',
        supervisor: params.supervisor || '',
        date: params.submission_date || '',
        academic_year: params.academic_year || ''
      });
      const response = await fetch(`/report/project/${encodeURIComponent(pId)}?${q}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(params)
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).message || 'Nie udało się przygotować raportu DOCX.');
      const html = await response.text();
      await downloadRenderedDocx(html);
      announce(`Pobrano edytowalny raport DOCX (${String(pId).toUpperCase()}).`);
    } catch (error) {
      announce(error.message, true);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = origText; }
    }
  }
  window.downloadIndividualProjectDocx = downloadIndividualProjectDocx;

  async function report(mode = 'preview') {
    saveEditorial();
    const sections = [...document.querySelectorAll('[name="studio-report-section"]:checked')].map(el => el.value);
    if (!sections.length) throw new Error('Wybierz co najmniej jeden etap raportu.');
    // Otwórz okno w obsłudze kliknięcia, aby przeglądarka nie blokowała podglądu.
    const popup = mode === 'preview' ? window.open('', '_blank') : null;
    if (mode === 'preview' && !popup) throw new Error('Zezwól na otwarcie okna raportu lub pobierz plik.');
    try {
      if (popup) popup.document.body.textContent = 'Przygotowywanie raportu…';
      if (mode === 'docx') $('studioReportStatus').textContent = 'Przygotowywanie pliku DOCX…';
      const result = await calculated(), editorial = getActiveProject()?.editorial || {};
      const response = await fetch(`/report?sections=${sections.join(',')}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({...result.params, report_notes: editorial.notes || '', source_notes: editorial.sources || ''})
      });
      if (!response.ok) throw new Error((await response.json()).message || 'Nie udało się przygotować raportu.');
      const html = await response.text();
      if (mode === 'html') download(`${filename(result.params.name)}-raport.html`, html, 'text/html;charset=utf-8');
      else if (mode === 'docx') await downloadRenderedDocx(html);
      else { popup.document.open(); popup.document.write(html); popup.document.close(); }
      $('studioReportStatus').textContent = `Raport przygotowany: ${sections.map(s => s.toUpperCase()).join(', ')}.`;
    } catch (error) { popup?.close(); throw error; }
  }

  async function parameterReport(mode = 'preview') {
    const {keys, chain, iterations, start} = BipolParamReport.options();
    if (!keys.length) throw new Error('Wybierz co najmniej jeden parametr raportu.');
    const popup = mode === 'preview' ? window.open('', '_blank') : null;
    if (mode === 'preview' && !popup) throw new Error('Zezwól na otwarcie okna raportu lub pobierz plik.');
    try {
      if (popup) popup.document.body.textContent = 'Przygotowywanie karty obliczeń…';
      if (mode === 'docx') $('studioReportStatus').textContent = 'Przygotowywanie karty obliczeń DOCX…';
      const result = await calculated();
      const params = {...result.params};
      if (start) params.mass_iteration_start_kg = Number(start); else delete params.mass_iteration_start_kg;
      const query = new URLSearchParams({keys: keys.join(','), chain, iterations});
      const response = await fetch(`/report/parameters?${query}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(params)
      });
      if (!response.ok) throw new Error((await response.json()).message || 'Nie udało się przygotować raportu parametrów.');
      const html = await response.text();
      if (mode === 'html') download(`${filename(result.params.name)}-karta-obliczen.html`, html, 'text/html;charset=utf-8');
      else if (mode === 'docx') await downloadRenderedDocx(html);
      else { popup.document.open(); popup.document.write(html); popup.document.close(); }
      $('studioReportStatus').textContent = `Karta obliczeń przygotowana: ${keys.length} ${keys.length === 1 ? 'pozycja' : 'pozycje'}.`;
    } catch (error) { popup?.close(); throw error; }
  }

  async function loadParameterCatalog() {
    if (document.querySelector('.tab-content.active')?.id !== 'tab-reports') return;
    try { await BipolParamReport.load(await calculated()); }
    catch (error) { $('paramCatalog').innerHTML = `<p class="studio-fine-print">${esc(error.message)}</p>`; }
  }

  async function action(name) {
    if (name === 'recalculate') { await performCalculation(); return; }
    if (name === 'reports') return navigate('tab-reports');
    if (name === 'preview-report') return report('preview');
    if (name === 'download-report') return report('html');
    if (name === 'download-report-docx') return report('docx');
    if (name === 'preview-param-report') return parameterReport('preview');
    if (name === 'download-param-report') return parameterReport('html');
    if (name === 'download-param-report-docx') return parameterReport('docx');
    if (name === 'export-json') { saveEditorial(); exportActiveProjectJSON(); return; }
    if (name === 'compare-csv') {
      const {rows} = comparisonRows();
      download('BIPOL-porownanie-wariantow.csv', csv(rows), 'text/csv;charset=utf-8'); return;
    }
    const result = await calculated();
    if (name === 'save-variant') {
      const list = variants();
      if (list.length >= 8) throw new Error('Zapisano już 8 wariantów. Usuń niepotrzebny wariant przed dodaniem kolejnego.');
      const label = $('studioVariantName').value.trim() || `${getActiveProject().name} · wariant ${list.length + 1}`;
      projectStore.write(VARIANTS_KEY, [snapshot(result, label), ...list]);
      $('studioVariantName').value = '';
      renderComparison(); announce(`Zapisano wariant „${label}”${projectStore.persistent ? '.' : ' tylko w pamięci karty — pobierz JSON.'}`);
    } else if (name === 'export-csv') download(`${filename(result.params.name)}-wyniki.csv`, csv(resultRows(result)), 'text/csv;charset=utf-8');
    else if (name === 'export-svg') {
      renderAircraft();
      const svg = $('studioAircraft').querySelector('svg').cloneNode(true);
      svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      download(`${filename(result.params.name)}-${view}.svg`, new XMLSerializer().serializeToString(svg), 'image/svg+xml;charset=utf-8');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('studio-layout');
    setupAircraftRotation();
    const guidanceObserver = new MutationObserver(renderProjectGuidance);
    guidanceObserver.observe($('calculationStatus'), {attributes:true,childList:true,subtree:true});
    guidanceObserver.observe($('calcBtn'), {attributes:true,attributeFilter:['disabled']});
    document.querySelectorAll('[data-studio-icon]').forEach(el => { el.innerHTML = BipolVisuals.icon(el.dataset.studioIcon, 19); });
    $('openReportBtn').addEventListener('click', event => { event.preventDefault(); event.stopImmediatePropagation(); navigate('tab-reports'); }, true);
    document.querySelectorAll('[data-studio-metadata]').forEach(input => input.addEventListener('input', () => {
      const key = input.dataset.studioMetadata, active = getActiveProject();
      if (!active) return;
      const source = document.getElementById(key);
      if (source) source.value = input.value;
      active.params[key] = input.value;
      formBaseParams[key] = input.value;
      if (currentResults && resultProject === active.id) currentResults.params[key] = input.value;
      saveProject(active);
      syncStudentDesignerFields('sidebar');
    }));
    document.querySelector('[data-studio-home]').addEventListener('click', event => { event.preventDefault(); navigate('tab-overview'); });
    $('studioMenuToggle').addEventListener('click', () => {
      navigationOpen(!document.body.classList.contains('studio-nav-open'));
    });
    $('studioNavBackdrop').addEventListener('click', () => navigationOpen(false, true));
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && document.body.classList.contains('studio-nav-open')) $('studioNavBackdrop').click(); });
    $('studioSidebar').addEventListener('keydown', event => {
      if (event.key !== 'Tab' || !document.body.classList.contains('studio-nav-open')) return;
      const controls = [...$('studioSidebar').querySelectorAll('a, button, summary')].filter(el => el.getClientRects().length), first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth > 1100) navigationOpen(false);
      else $('studioSidebar').inert = !document.body.classList.contains('studio-nav-open');
    });
    navigationOpen(false);
    document.addEventListener('click', async event => {
      const button = event.target.closest('button');
      if (!button) return;
      try {
        if (button.dataset.studioNav) navigate(button.dataset.studioNav);
        else if (button.dataset.studioTarget) navigate(button.dataset.studioTarget);
        else if (button.dataset.aircraftView) {
          view = button.dataset.aircraftView; aircraftCamera = BipolAircraftPreview.camera(view); renderAircraft();
        }
        else if (button.dataset.studioAction) await action(button.dataset.studioAction);
        else if (button.dataset.loadVariant) {
          const variant = variants().find(v => v.id === button.dataset.loadVariant);
          if (!variant) return;
          saveEditorial();
          const project = {id: BipolStudio.uniqueId('proj_'), name: variant.name, params: variant.params, summary: {}, createdAt: new Date().toISOString(), semesterChecklist: {}};
          saveProject(project); switchActiveProject(project.id); navigate('tab-overview');
        } else if (button.dataset.deleteVariant) { projectStore.write(VARIANTS_KEY, variants().filter(v => v.id !== button.dataset.deleteVariant)); renderComparison(); }
        else if (button.dataset.exportVariant) {
          const variant = variants().find(v => v.id === button.dataset.exportVariant);
          if (variant) download(`${filename(variant.name)}.bipol.json`, JSON.stringify({bipol_version: '2.0', project: {name: variant.name, params: variant.params}}, null, 2), 'application/json');
        }
      } catch (error) { announce(error.message, true); }
    });
    $('studioVariantForm').addEventListener('submit', event => { event.preventDefault(); action('save-variant').catch(error => announce(error.message, true)); });
    for (const id of ['studioNotes', 'studioSources']) $(id).addEventListener('input', saveEditorial);
    document.addEventListener('bipol:results', event => {
      fresh = true; resultProject = getActiveProjectId();
      renderOverview(event.detail); renderGlide(event.detail); renderComparison();
      $('studioResultStatus').textContent = 'Wyniki aktualne';
      $('studioResultStatus').classList.remove('attention');
    });
    document.addEventListener('bipol:project', () => { fresh = false; loadEditorial(); renderComparison(); $('studioResultStatus').textContent = 'Oczekiwanie na obliczenia'; renderProjectGuidance(); });
    document.addEventListener('bipol:tab', syncNavigation);
    document.addEventListener('bipol:tab', loadParameterCatalog);
    document.addEventListener('bipol:results', loadParameterCatalog);
    document.addEventListener('bipol:mode', syncNavigation);
    document.addEventListener('bipol:storage', () => {
      $('studioStorageStatus').textContent = projectStore.persistent ? 'Zapis w przeglądarce' : 'Tylko pamięć karty — pobierz JSON';
      $('studioStorageStatus').classList.toggle('attention', !projectStore.persistent);
    });
    const markStale = () => { fresh = false; $('studioResultStatus').textContent = 'Wyniki wymagają przeliczenia'; $('studioResultStatus').classList.add('attention'); renderProjectGuidance(); };
    document.addEventListener('bipol:calculating', markStale);
    $('designForm').addEventListener('input', markStale, true);
    $('designForm').addEventListener('change', markStale, true);
    document.querySelectorAll('.quick-preset-chip').forEach(button => button.addEventListener('click', markStale, true));
    loadEditorial(); renderComparison(); syncNavigation();
    if (currentResults) { fresh = true; resultProject = getActiveProjectId(); renderOverview(currentResults); renderGlide(currentResults); }
  });
})();
