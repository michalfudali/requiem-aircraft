/* Shared P2 workspace: one set of controls in both studio and semester modes. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const drafts = new Map();
  const draftLabels = new Map(), sourceDrafts = new Map();
  let fileSequence = 0, semesterHost;
  const key = name => String(name || '').toUpperCase().replace(/\s/g, '');
  const emit = field => field.dispatchEvent(new Event('input', {bubbles: true}));
  const move = (node, parent) => { if (node.parentElement !== parent) parent.append(node); };

  function mount() {
    const panel = $('panel-p2');
    if (!panel || !semesterHost) return;
    const semester = currentPortalMode === 'projects';
    move(panel, semester ? semesterHost : $('p2StudioHost'));
    panel.style.display = !semester || currentSemesterProject === 'p2' ? 'block' : 'none';
    move($('p2DesignDecisions'), semester ? $('p2SemesterDecisionsHost') : $('p2DecisionsHost'));
    const profileHost = semester && currentSemesterProject === 'p3' ? $('p3AirfoilEditorHost') : $('p2AirfoilEditorHost');
    move($('p2AirfoilEditor'), profileHost);
    if (currentResults && (semester ? currentSemesterProject === 'p2' : $('tab-feasibility').classList.contains('active'))) renderSemesterProjectCharts('p2', currentResults);
  }

  function availability() {
    const geometryFixed = $('wing_input_mode').value !== 'loading';
    $('matching_design_mode').disabled = geometryFixed || $('engine_type').value === 'none';
    $('matching_design_mode').title = geometryFixed ? 'Geometria jest zadana niezależnie. Zmień sposób doboru skrzydła na obciążenie powierzchni, aby wybrać punkt A/B.' : '';
    $('turbocharged').disabled = $('engine_type').value !== 'prop' || $('aircraft_type').value === 'turboprop_regional';
  }

  function profileChoices(result) {
    const select = $('p2AirfoilSelect');
    for (const option of [...select.querySelectorAll('[data-candidate]')]) option.remove();
    const names = [...(result?.bipol_projects?.p2?.airfoil_selection?.candidates?.map(c => c.name) || []), ...draftLabels.values()];
    for (const name of names) {
      if ([...select.options].some(o => key(o.value) === key(name))) continue;
      const option = new Option(name + ' — dane katalogowe autora / import rzędnych', name);
      option.dataset.candidate = 'true'; select.add(option, select.options.length - 1);
    }
    const typed = $('airfoil').value.trim();
    const match = [...select.options].find(o => o.value !== '__custom__' && key(o.value) === key(typed));
    select.value = typed ? match?.value || '__custom__' : '';
  }

  function restore(params) {
    for (const field of document.querySelectorAll('[data-optional-param]')) field.value = params[field.id] ?? '';
    $('matching_design_mode').value = params.matching_design_mode || 'wing_limit';
    $('turbocharged').value = String(params.turbocharged || false);
    $('airfoil_source').value = params.airfoil_source || '';
    profileChoices(null);
    availability();
  }

  function validate() {
    for (const field of document.querySelectorAll('[data-optional-param]')) {
      if (field.type !== 'number' || !field.value.trim() || field.matches(':disabled') || field.readOnly) continue;
      const val=field.validity; if (!Number.isFinite(Number(field.value)) || (val&&(val.badInput||val.rangeUnderflow||val.rangeOverflow||val.valueMissing))) {
        throw new Error(`Sprawdź: ${field.labels?.[0]?.textContent.trim() || field.id}. ${field.validationMessage}`);
      }
    }
  }

  function focus(id) {
    if ($(id)?.closest('#designForm')) { window.focusDesignParameter(id); return; }
    document.querySelector('[data-studio-nav="tab-feasibility"]').click();
    const field = $(id);
    if (!field) return;
    for (const details of document.querySelectorAll('#tab-feasibility details')) {
      if (details.contains(field)) details.open = true;
    }
    if (!field.matches('input,select,textarea,button')) field.tabIndex = -1;
    field.scrollIntoView({block: 'center'}); field.focus({preventScroll: true});
  }

  function render(result) {
    profileChoices(result);
    const decision = result.sizing?.design_point;
    if (decision) $('p2DecisionStatus').textContent = decision.selection_note ||
      `Punkt projektowy: W/S = ${decision.ws.toFixed(1)} N/m². Ograniczenie: ${decision.limit_by}.`;
    availability();
    const preview = $('p2ProfilePreview');
    preview.innerHTML = result.bipol_projects?.p3?.airfoil_200mm_svg || '';
    const info = result.bipol_projects?.p3?.airfoil_200mm_info;
    $('p2ProfileStatus').textContent = info
      ? `${info.name}: t/c = ${info.thickness_pct}%, cięciwa rysunku 200 mm. ${info.kind === 'pasted' ? 'Rzędne autora.' : 'Geometria analityczna NACA.'}`
      : result.bipol_projects?.p3?.airfoil_coordinates_note || 'Dodaj rzędne wybranego profilu.';
  }

  document.addEventListener('DOMContentLoaded', () => {
    semesterHost = document.createElement('div'); semesterHost.id = 'p2SemesterHost';
    $('panel-p2').before(semesterHost);
    const decisionsHost = document.createElement('div'); decisionsHost.id = 'p2SemesterDecisionsHost';
    $('panel-p2').querySelector('.project-hero-header').after(decisionsHost);
    const preview = document.createElement('div'); preview.id = 'p2ProfilePreview'; preview.className = 'p2-profile-preview';
    $('p2AirfoilEditorHost').after(preview);
    mount();
    restore(formBaseParams || {});
    if (currentResults) render(currentResults);

    $('p2AirfoilSelect').addEventListener('change', event => {
      const name = event.target.value;
      if (name === '__custom__') { $('airfoil').focus(); return; }
      const previous = $('airfoil').value;
      drafts.set(key(previous), $('airfoil_coordinates').value);
      if (previous) draftLabels.set(key(previous), previous);
      sourceDrafts.set(key(previous), $('airfoil_source').value);
      $('airfoil').value = name;
      $('airfoil_coordinates').value = drafts.get(key(name)) || '';
      $('airfoil_source').value = sourceDrafts.get(key(name)) || '';
      emit($('airfoil')); emit($('airfoil_coordinates'));
      if (previous !== name) $('p2ProfileStatus').textContent = 'Zmieniono profil. Zastosuj wybór i przelicz projekt; rzędne poprzedniego profilu pozostają w szkicu do ponownego wyboru.';
    });
    $('airfoil').addEventListener('input', () => profileChoices(currentResults));
    $('p2AirfoilFile').addEventListener('change', async event => {
      const file = event.target.files?.[0];
      if (!file) return;
      const sequence = ++fileSequence, project = getActiveProjectId();
      try {
        if (file.size > 100000) throw new Error('Plik rzędnych jest za duży (limit 60 000 znaków).');
        const text = await file.text();
        if (sequence !== fileSequence || project !== getActiveProjectId()) return;
        if (text.length > 60000) throw new Error('Plik rzędnych przekracza limit 60 000 znaków.');
        const header = text.split(/\r?\n/).find(line => line.trim())?.trim() || '';
        const previous = $('airfoil').value;
        drafts.set(key(previous), $('airfoil_coordinates').value);
        if (previous) draftLabels.set(key(previous), previous);
        sourceDrafts.set(key(previous), $('airfoil_source').value);
        if (/[a-zA-Z]/.test(header) && !/^[-+\d.,\sEe]+$/.test(header)) {
          $('airfoil').value = header.slice(0,80);
          if (key(previous) !== key($('airfoil').value)) $('airfoil_source').value = sourceDrafts.get(key($('airfoil').value)) || '';
        }
        $('airfoil_coordinates').value = text;
        draftLabels.set(key($('airfoil').value), $('airfoil').value);
        drafts.set(key($('airfoil').value), text);
        emit($('airfoil')); emit($('airfoil_coordinates'));
        profileChoices(currentResults);
        $('p2ProfileStatus').textContent = `Wczytano ${file.name}. Sprawdź źródło i zastosuj profil, aby zweryfikować rzędne.`;
      } catch (error) { $('p2ProfileStatus').textContent = error.message; }
      finally { event.target.value = ''; }
    });
    document.addEventListener('click', event => {
      const calculate = event.target.closest('[data-p2-calculate]');
      if (calculate) performCalculation();
      const button = event.target.closest('[data-p2-focus]');
      if (button) focus(button.dataset.p2Focus);
    });
    document.addEventListener('input', event => {
      if (['airfoil', 'airfoil_coordinates'].includes(event.target.id)) $('p2ProfilePreview').replaceChildren();
    });
    document.addEventListener('change', event => {
      if (['wing_input_mode','engine_type','aircraft_type'].includes(event.target.id)) availability();
    });
  });
  for (const event of ['bipol:mode','bipol:tab','bipol:semester']) document.addEventListener(event, mount);
  document.addEventListener('bipol:project', () => {
    fileSequence++; drafts.clear(); draftLabels.clear(); sourceDrafts.clear(); restore(formBaseParams);
  });
  document.addEventListener('bipol:results', event => { render(event.detail); mount(); });
  window.BipolP2 = {restore, validate, focus};
})();
