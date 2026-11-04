/* The wizard is a persistent workspace. Drafts never update calculated projects. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const KEY = 'bipol_wizard_drafts_v1';
  const esc = BipolStudio.escape;
  const fmt = (n, digits = 2) => BipolStudio.format(n, digits);
  let ready = false, owner = null, dirty = false, applying = false, timer, controller, previewSequence = 0;

  function started() {
    ready = true; owner = getActiveProjectId(); dirty = false;
    $('wizardDraftStatus').textContent = 'Szkic gotowy do edycji';
    refresh();
  }

  function syncRecalculate() {
    if (!ready || !$('tab-wizard').classList.contains('active')) return;
    if ($('wizRestoreSaved')) $('wizRestoreSaved').hidden = !dirty;
    const pill = $('navRecalcPill');
    pill.classList.toggle('synced', !dirty); pill.classList.toggle('stale', dirty);
    pill.innerHTML = `<span>${dirty ? 'Oblicz szkic' : 'Oblicz projekt'}</span> <kbd>Ctrl+Enter</kbd>`;
    pill.title = 'Oblicz i zapisz założenia z kreatora (Ctrl+Enter).';
  }

  function persist() {
    if (!ready || !dirty) return;
    const fields = {};
    $('projectWizardBackdrop').querySelectorAll('input[id], select[id], textarea[id]').forEach(el => {
      if (el.id.startsWith('wiz_')) fields[el.id] = el.type === 'checkbox' ? el.checked : el.value;
    });
    const drafts = projectStore.read(KEY, {});
    const safe = drafts && typeof drafts === 'object' && !Array.isArray(drafts) ? drafts : {};
    safe[owner] = {schema:1, mode:wizardProjectMode, step:currentWizardStep,
      params:BipolDesignBasis.snapshot(), fields};
    const saved = projectStore.write(KEY, safe);
    $('wizardDraftStatus').textContent = saved ? 'Szkic zapisany w tej przeglądarce' : 'Szkic zachowany w tej karcie — zapis przeglądarki niedostępny';
  }

  function ensure() {
    const id = getActiveProjectId();
    if (ready && owner === id) return;
    const draft = projectStore.read(KEY, {})?.[id];
    // Set readiness before navigation to avoid re-entering through the tab event.
    ready = true; owner = id;
    openWizard('edit');
    if (draft?.schema === 1 && draft.params && typeof draft.params === 'object') {
      wizardProjectMode = draft.mode === 'create' ? 'create' : 'edit';
      BipolDesignBasis.seed(draft.params);
      for (const [key, value] of Object.entries(draft.fields || {})) {
        const el = $(key); if (!key.startsWith('wiz_') || !el?.closest('#projectWizardBackdrop')) continue;
        if (el.type === 'checkbox') el.checked = Boolean(value); else el.value = String(value ?? '');
      }
      BipolDesignBasis.sync('wiz_');
      $('wizardWorkspaceTitle').textContent = wizardProjectMode === 'create' ? 'Nowy projekt' : 'Edytuj założenia projektu';
      dirty = true;
      goToWizardStep(Math.max(1, Math.min(5, Number(draft.step) || 1)), {focus:false});
      $('wizardDraftStatus').textContent = 'Przywrócono niezastosowany szkic';
    }
    refresh();
  }

  function refresh() {
    if (!ready) return;
    syncRecalculate();
    const p = BipolDesignBasis.snapshot();
    $('wizardDraftName').textContent = p.name;
    const direct = p.preliminary_polar_mode === 'input';
    $('wizardLiveSummary').innerHTML = [
      ['Misja', `${p.range_km} km · ${p.cruise_speed_kmh} km/h`],
      ['Załoga i pasażerowie', `${Number(p.n_crew) + Number(p.n_pax)} os.`],
      ['Wydłużenie skrzydła', fmt(p.aspect_ratio)],
      ['Podstawa oporu', direct ? `C_D0 = ${fmt(p.cx0, 4)}` : p.wetted_example === 'sketch' ? `S_wet/S = ${fmt(p.sketch_swet_ratio)}` : 'S_wet/S z układu samolotu']
    ].map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('');
    controller?.abort(); clearTimeout(timer);
    const sequence = ++previewSequence;
    if (currentWizardStep !== 4 && currentWizardStep !== 5) return;
    $('wizardPolarPreview').textContent = 'Przeliczanie biegunowej wstępnej…';
    timer = setTimeout(() => preview(p, sequence), 250);
  }

  async function preview(params, sequence) {
    controller = new AbortController();
    try {
      const response = await fetch('/api/preliminary-polar', {method:'POST',
        headers:{'Content-Type':'application/json'}, body:JSON.stringify(params), signal:controller.signal});
      const data = await response.json();
      if (sequence !== previewSequence) return;
      if (!response.ok) throw Error(data.message || 'Sprawdź założenia biegunowej.');
      const p = data.polar;
      const route = p.mode === 'input'
        ? `Podany C_D0 = ${fmt(p.cx0, 5)} → K_max = ½√(πΛe/C_D0) = ${fmt(p.kmax)}`
        : `S_wet/S = ${fmt(p.swet_ratio)} → Λ_wet = ${fmt(p.wetted_aspect_ratio)} → K_max = ${fmt(p.kmax)} → C_D0 = πΛe/(4K_max²) = ${fmt(p.cx0, 5)}`;
      const check = p.cx0_in_range ? 'W przedziale typowym dla wybranej klasy.' : 'Poza przedziałem typowym — sprawdź i uzasadnij przyjętą wartość.';
      $('wizardPolarPreview').innerHTML = `<strong>${esc(route)}</strong><p>C_D = C_D0 + C_L²/(πΛe). ${esc(check)}${p.extrapolated ? ' Odczyt Raymera poza zakresem narysowanej krzywej — ekstrapolacja do potwierdzenia.' : ''}</p>`;
    } catch (error) {
      if (error.name !== 'AbortError' && sequence === previewSequence) $('wizardPolarPreview').textContent = error.message;
    }
  }

  function stepChanged() {
    document.querySelectorAll('.wizard-step-tab').forEach(tab => {
      tab.setAttribute('aria-controls', `wizardPane${tab.dataset.step}`);
    });
    refresh(); persist();
  }

  function suspend() {
    persist(); controller?.abort(); clearTimeout(timer); previewSequence++;
  }

  function committed() {
    const drafts = projectStore.read(KEY, {});
    if (drafts && typeof drafts === 'object') { delete drafts[owner]; projectStore.write(KEY, drafts); }
    dirty = false; ready = false; owner = null;
  }

  window.BipolWizardWorkspace = {ensure, started, stepChanged, suspend, committed,
    beginApply:() => { applying = true; }, endApply:() => { applying = false; }};
  document.addEventListener('DOMContentLoaded', () => {
    const root = $('projectWizardBackdrop');
    const changed = event => {
      if (!ready || !event.target.matches('input, select, textarea') || event.target.closest('.wizard-trend-chart-box')) return;
      dirty = true; showWizardError(''); refresh(); persist();
    };
    root.addEventListener('input', changed); root.addEventListener('change', changed);
    $('wizRestoreSaved')?.addEventListener('click', () => { committed(); ensure(); });
    $('wizExplanationToggle').addEventListener('click', event => {
      const show = $('tab-wizard').dataset.explanations !== 'true';
      $('tab-wizard').dataset.explanations = String(show);
      event.currentTarget.setAttribute('aria-pressed', String(show));
      event.currentTarget.textContent = show ? 'Ukryj objaśnienia' : 'Pokaż objaśnienia';
    });
    document.addEventListener('bipol:results', () => {
      // Other tabs can refine the same project. Refresh an untouched wizard;
      // retain an unapplied draft independently from newly calculated results.
      if (ready && !dirty && !applying) {
        const step = currentWizardStep;
        ready = false;
        if ($('tab-wizard').classList.contains('active')) { ensure(); goToWizardStep(step, {focus:false}); }
      }
      queueMicrotask(syncRecalculate);
    });
    document.addEventListener('bipol:tab', syncRecalculate);
    document.addEventListener('bipol:project', () => {
      if (applying) return;
      if (ready && owner !== getActiveProjectId()) {
        suspend(); ready = false;
        if ($('tab-wizard').classList.contains('active')) ensure();
      }
    });
    window.addEventListener('pagehide', persist);
  });
})();
