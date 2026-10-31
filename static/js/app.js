/**
 * BiPOL Requiem - Główna logika interaktywna i dydaktyczna
 * Obsługa:
 * - 110 tematów wydziałowych ZSiS MEiL PW
 * - Encyklopedii każdego parametru projektowego (PARAMETER_ENCYCLOPEDIA)
 * - Kart plusów i minusów klap, slotów i układów nośnych wg monografii prof. C. Galińskiego
 * - Rysunku technicznego A3Z wg polskich norm PN-EN ISO / ZPK MEiL PW
 */

let currentResults = null;
let topicsData = [];
let categoriesData = {};
let formBaseParams = {};
let browserStorage = null;
try { browserStorage = window.localStorage; } catch (_) {}
const projectStore = BipolStudio.createStore(browserStorage, () => {
  document.dispatchEvent(new CustomEvent('bipol:storage'));
});
let activeProjectMemory = null;
function safeLocalItem(key) {
  try { return browserStorage?.getItem(key) ?? null; } catch (_) { return null; }
}

document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  initDidacticSystem();
  initWizardSystem();

  // 1. Pobierz tematy i kategorie wydziałowe
  try {
    const topResp = await fetch('/api/topics');
    const topJson = await topResp.json();
    categoriesData = topJson.categories;
    topicsData = topJson.topics;
    populateCategorySelect();
    populateTopicsSelect('all');
  } catch (err) {
    console.error('Błąd pobierania tematów:', err);
  }

  // 3. Pobierz listę materiałów z wydziału (BIPOL, Mechanika Lotu, ZPK CAD1)
  loadScrapedFiles();

  // 4. Listeners dla wyboru kategorii i tematu
  const catSelect = document.getElementById('categorySelect');
  if (catSelect) {
    catSelect.addEventListener('change', (e) => {
      populateTopicsSelect(e.target.value);
    });
  }

  const topicSelect = document.getElementById('topicSelect');
  if (topicSelect) {
    topicSelect.addEventListener('change', (e) => {
      loadTopic(e.target.value);
    });
  }

  const calcBtn = document.getElementById('calcBtn');
  if (calcBtn) {
    calcBtn.addEventListener('click', performCalculation);
  }

  // Inicjalizacja modularnego paska bocznego
  initSidebarModularity();

  // Inicjalizacja Systemu Dwuwersyjnego Portalu (Całościowy vs Projekty Semestralne P1-P6)
  initDualPortalSystem();

  // Inicjalizacja Systemu Projektowego (Project Management System & Session Starter)
  initProjectSystem();
});

// ==========================================
// MODULAR SIDEBAR & ACCORDION SYSTEM
// ==========================================
let currentSidebarMode = 'basic';

function syncFormPropulsionUI(triggerAutoSfc = false) {
  const engEl = document.getElementById('engine_type');
  const locEl = document.getElementById('engine_location');
  const acEl = document.getElementById('aircraft_type');
  const sfcEl = document.getElementById('sfc');
  const propGroup = document.getElementById('group_prop_efficiency');
  const titleMod4 = document.getElementById('title_mod4');
  const labelSfc = document.getElementById('label_sfc_text');

  const eng = engEl ? engEl.value : 'prop';
  const acType = acEl ? acEl.value : 'piston_ga';
  const isGlider = eng === 'none';
  window.BipolDesignBasis?.propulsion('');
  for (const [field, minimum, fallback] of [['takeoff_run_m', 50, 500], ['takeoff_distance_m', 0, 600], ['climb_rate_ms', 1.5, 4.1]]) {
    const input = document.getElementById(field);
    if (input) { input.min = isGlider ? '0' : String(minimum); if (isGlider) input.value = '0'; else if (minimum > 0 && Number(input.value) === 0) input.value = fallback; }
  }
  if (sfcEl) {
    sfcEl.readOnly = isGlider;
    sfcEl.closest('.input-group').style.display = isGlider ? 'none' : '';
  }
  if (isGlider) {
    if (sfcEl) { sfcEl.value = '0'; sfcEl.min = '0'; sfcEl.max = '0'; }
    if (propGroup) propGroup.style.display = 'none';
    if (titleMod4) titleMod4.textContent = '4. Lot bez napędu — szybowiec';
    return;
  }


  if (titleMod4) {
    titleMod4.textContent = eng === 'jet'
      ? '4. Zespół Napędowy Odrzutowy (P2/P5)'
      : '4. Zespół Napędowy & Śmigło (P2/P5)';
  }

  if (propGroup) {
    propGroup.style.display = eng === 'jet' ? 'none' : '';
  }

  if (locEl) {
    const noseOpt = locEl.querySelector('option[value="nose"]');
    const retrOpt = locEl.querySelector('option[value="retractable"]');
    if (noseOpt) {
      noseOpt.disabled = (eng === 'jet');
      noseOpt.hidden = (eng === 'jet');
    }
    if (retrOpt) {
      retrOpt.disabled = (eng === 'jet');
      retrOpt.hidden = (eng === 'jet');
    }
    if (eng === 'jet' && (locEl.value === 'nose' || locEl.value === 'retractable')) {
      locEl.value = (acType === 'jet_transport') ? 'wing' : 'rear';
    }
  }

  if (sfcEl) {
    const curVal = parseFloat(sfcEl.value);
    if (eng === 'jet') {
      if (labelSfc) labelSfc.innerHTML = 'Zużycie TSFC c_j [1/h]';
      sfcEl.min = '0.25';
      sfcEl.max = '1.80';
      sfcEl.step = 'any';
      if (triggerAutoSfc || isNaN(curVal) || curVal > 4.0) {
        sfcEl.value = (acType === 'jet_transport') ? '0.58' : '0.62';
      }
    } else {
      if (labelSfc) labelSfc.innerHTML = 'Zużycie SFC c_p [g/(kW&bull;h)]';
      sfcEl.min = '140';
      sfcEl.max = '500';
      sfcEl.step = 'any';
      if (triggerAutoSfc || isNaN(curVal) || curVal < 50.0) {
        if (!triggerAutoSfc && curVal >= 0.15 && curVal <= 1.5) {
          sfcEl.value = String(Math.round(curVal * 1000));
        } else {
          sfcEl.value = (acType === 'turboprop_regional') ? '280' : '265';
        }
      }
    }
  }
}

// CS 23.2005: poziom certyfikacji wynika z liczby miejsc pasażerskich, nie jest osobnym wyborem.
const CS23_SEAT_LEVELS = [[1, 'cs23_level1'], [6, 'cs23_level2'], [9, 'cs23_level3'], [19, 'cs23_commuter']];
function cs23LevelForPax(nPax) {
  const n = Math.max(0, Math.round(Number(nPax) || 0));
  return CS23_SEAT_LEVELS.find(([max]) => n <= max)?.[1] || null;
}

function syncAircraftClassAndEASAUI(isWizard = false, source = null) {
  const pfx = isWizard ? 'wiz_' : '';
  const acEl = document.getElementById(pfx + 'aircraft_type');
  const catEl = document.getElementById(pfx + 'category');
  const crewEl = document.getElementById(pfx + 'n_crew');
  const paxEl = document.getElementById(pfx + 'n_pax');
  const mpaxEl = document.getElementById(pfx + 'm_pax');


  const categoryIsUas = () => catEl?.value.startsWith('easa_uas_');
  if (source === 'aircraft') {
    if (acEl?.value === 'glider') {
      if (catEl) catEl.value = 'cs22_glider';
      const engEl = document.getElementById(pfx + 'engine_type');
      if (engEl) engEl.value = 'none';
      if (isWizard) syncWizardPropulsionUI(true);
      else syncFormPropulsionUI(true);
    } else if (acEl?.value === 'motoglider') {
      if (catEl) catEl.value = 'cs22_motoglider';
      const engEl = document.getElementById(pfx + 'engine_type');
      if (engEl && engEl.value === 'none') engEl.value = 'prop';
      if (isWizard) syncWizardPropulsionUI(true);
      else syncFormPropulsionUI(true);
    } else if (acEl?.value !== 'uav' && (categoryIsUas() || catEl?.value.startsWith('cs22_'))) {
      catEl.value = acEl.value === 'jet_transport' ? 'cs25_transport' : (cs23LevelForPax(paxEl?.value) || 'cs23_commuter');
    }
  }
  // Zmiana liczby pasażerów przestawia poziom CS-23 (L1–L4); kategorii akrobacyjnej, VLA, LSA itp. nie rusza.
  if (source === 'pax' && catEl && CS23_SEAT_LEVELS.some(([, level]) => level === catEl.value)) {
    const level = cs23LevelForPax(paxEl?.value);
    if (level) catEl.value = level;
  }
  if (source === 'category') {
    if (catEl?.value === 'cs22_glider') {
      if (acEl) acEl.value = 'glider';
      const engEl = document.getElementById(pfx + 'engine_type');
      if (engEl) engEl.value = 'none';
      if (isWizard) syncWizardPropulsionUI(true);
      else syncFormPropulsionUI(true);
    } else if (catEl?.value === 'cs22_motoglider') {
      if (acEl && acEl.value !== 'motoglider') acEl.value = 'motoglider';
      const engEl = document.getElementById(pfx + 'engine_type');
      if (engEl && engEl.value === 'none') engEl.value = 'prop';
      if (isWizard) syncWizardPropulsionUI(true);
      else syncFormPropulsionUI(true);
    }
  }
  if (source === 'category' && !categoryIsUas() && acEl?.value === 'uav') {
    acEl.value = catEl.value === 'cs25_transport' ? 'jet_transport' : 'piston_ga';
    const engEl = document.getElementById(pfx + 'engine_type');
    const locEl = document.getElementById(pfx + 'engine_location');
    if (engEl) engEl.value = acEl.value === 'jet_transport' ? 'jet' : 'prop';
    if (locEl) locEl.value = acEl.value === 'jet_transport' ? 'wing' : 'nose';
    if (isWizard) syncWizardPropulsionUI(true);
    else syncFormPropulsionUI(true);
  }
  const ac = acEl ? acEl.value : 'piston_ga';
  const cat = catEl ? catEl.value : 'cs23_level2';
  const isUas = ac === 'uav' || categoryIsUas();
  if (crewEl) crewEl.min = isUas ? '0' : (cat === 'cs25_transport' ? '2' : '1');

  // 1. Spójność dropdownów klasy i przepisów
  if (isUas) {
    if (acEl && acEl.value !== 'uav') acEl.value = 'uav';
    if (catEl && !catEl.value.startsWith('easa_uas_')) {
      catEl.value = 'easa_uas_specific';
    }
  } else {
    if (catEl && catEl.value.startsWith('easa_uas_')) {
      catEl.value = (ac === 'jet_transport') ? 'cs25_transport' : (ac === 'turboprop_regional' ? 'cs23_commuter' : (cs23LevelForPax(paxEl?.value) || 'cs23_commuter'));
    }
  }

  // 2. Banner EASA UAS
  const banner = document.getElementById(isWizard ? 'wiz_uav_easa_banner' : 'uav_easa_banner');
  if (banner) banner.style.display = isUas ? 'block' : 'none';

  // 3. Widoczność pól ludzi na pokładzie dla UAV vs Manned
  if (isWizard) {
    const rowOcc1 = document.getElementById('wiz_row_occupants_1');
    const groupMpax = document.getElementById('wiz_group_m_pax');
    const labelCargo = document.getElementById('label_wiz_m_cargo');
    if (rowOcc1) rowOcc1.style.display = isUas ? 'none' : '';
    if (groupMpax) groupMpax.style.display = isUas ? 'none' : '';
    if (labelCargo) {
      labelCargo.textContent = isUas
        ? 'Masa wyposażenia zadaniowego / sensorów UAV [kg]:'
        : 'Dodatkowy ładunek handlowy cargo [kg]:';
    }
  } else {
    const groupPax = document.getElementById('group_n_pax');
    const rowCrew = document.getElementById('row_main_crew');
    const labelCargoText = document.getElementById('label_m_cargo_text');
    if (groupPax) groupPax.style.display = isUas ? 'none' : '';
    if (rowCrew) rowCrew.style.display = isUas ? 'none' : '';
    if (labelCargoText) {
      labelCargoText.firstChild.textContent = isUas
        ? 'Wyposażenie zadaniowe / sensory UAV [kg] '
        : 'Ładunek cargo [kg] ';

    }
  }

  // 4. Ustawienie wartości numerycznych dla UAV vs Manned
  if (isUas) {
    if (crewEl) crewEl.value = '0';
    if (paxEl) paxEl.value = '0';
    if (mpaxEl) mpaxEl.value = '0';

  } else {
    if (crewEl && (parseFloat(crewEl.value) === 0 || isNaN(parseFloat(crewEl.value)))) {
      crewEl.value = (cat === 'cs25_transport') ? '2' : '1';
    }
    if (mpaxEl && (parseFloat(mpaxEl.value) === 0 || isNaN(parseFloat(mpaxEl.value)))) {
      mpaxEl.value = '100';
    }
    if (paxEl) {
      if (cat === 'cs_vla' || cat === 'cs_lsa' || cat === 'cs22_motoglider' || cat === 'cs22_glider' || cat === 'easa_optout_ul') {
        paxEl.max = '1';
      } else if (cat === 'easa_optout_ul115') {
        paxEl.max = '0';

      } else if (cat === 'cs23_level1') {
        paxEl.max = '1';
      } else if (cat === 'cs23_level2') {
        paxEl.max = '6';
      } else if (cat === 'cs23_level3') {
        paxEl.max = '9';
      } else if (cat === 'cs23_commuter') {
        paxEl.max = '19';
      } else {
        paxEl.max = '300';
      }
    }
    if (crewEl && cat === 'cs25_transport') {
      crewEl.min = '2';
      if (parseInt(crewEl.value, 10) < 2) crewEl.value = '2';
    }
  }
}

function syncEngineWithAircraft(isWizard = false) {
  const prefix = isWizard ? 'wiz_' : '';
  const engine = document.getElementById(prefix + 'engine_type');
  const aircraft = document.getElementById(prefix + 'aircraft_type');
  const previousClass = aircraft?.value;
  if (engine?.value === 'none') aircraft.value = 'glider';
  else if (aircraft?.value === 'glider') aircraft.value = engine.value === 'jet' ? 'jet_business' : 'motoglider';
  syncAircraftClassAndEASAUI(isWizard, 'aircraft');
  if (aircraft?.value !== previousClass) window.BipolDesignBasis?.classDefaults(prefix);
}

function initSidebarModularity() {
  const form = document.getElementById('designForm');
  const engEl = document.getElementById('engine_type');
  const acEl = document.getElementById('aircraft_type');
  const catEl = document.getElementById('category');

  if (engEl) {
    engEl.addEventListener('change', () => {
      syncEngineWithAircraft(false);
      syncFormPropulsionUI(true);
      updateAccordionPills();
      performCalculation();
    });
  }

  if (acEl) {
    acEl.addEventListener('change', () => {
      const ac = acEl.value;
      if (engEl) {
        if (ac === 'jet_business' || ac === 'jet_transport') {
          engEl.value = 'jet';
          const locEl = document.getElementById('engine_location');
          if (locEl) locEl.value = (ac === 'jet_transport') ? 'wing' : 'rear';
        } else if (ac === 'piston_ga' || ac === 'turboprop_regional' || ac === 'uav') {
          engEl.value = 'prop';
          const locEl = document.getElementById('engine_location');
          if (locEl) locEl.value = (ac === 'turboprop_regional') ? 'wing' : (ac === 'uav' ? 'rear' : 'nose');
        } else if (ac === 'motoglider') {
          engEl.value = 'prop';
          const locEl = document.getElementById('engine_location');
          if (locEl) locEl.value = 'retractable';
        } else if (ac === 'glider') {
          engEl.value = 'none';
        }
      }
      syncAircraftClassAndEASAUI(false, 'aircraft');
      window.BipolDesignBasis?.classDefaults('');
      syncFormPropulsionUI(true);
      updateAccordionPills();
      performCalculation();
    });
  }

  if (catEl) {
    catEl.addEventListener('change', () => {
      syncAircraftClassAndEASAUI(false, 'category');
      updateAccordionPills();
      performCalculation();
    });
  }
  document.getElementById('n_pax')?.addEventListener('change', () => syncAircraftClassAndEASAUI(false, 'pax'));

  if (form) {
    form.addEventListener('input', updateAccordionPills);
    form.addEventListener('change', updateAccordionPills);
  }
  syncAircraftClassAndEASAUI(false);
  syncFormPropulsionUI(false);
  updateAccordionPills();
}

function setSidebarMode(mode) {
  currentSidebarMode = mode;
  const form = document.getElementById('designForm');
  const basicBtn = document.getElementById('modeBasicBtn');
  const advBtn = document.getElementById('modeAdvancedBtn');

  if (form) {
    if (mode === 'advanced') {
      form.classList.remove('mode-basic');
      form.classList.add('mode-advanced');
    } else {
      form.classList.remove('mode-advanced');
      form.classList.add('mode-basic');
    }
  }

  if (basicBtn && advBtn) {
    basicBtn.classList.toggle('active', mode === 'basic');
    advBtn.classList.toggle('active', mode === 'advanced');
  }
}

function toggleFacultyDrawer() {
  const drawer = document.getElementById('facultyTopicsDrawer');
  const btn = document.getElementById('toggleFacultyTopicsBtn');
  if (!drawer) return;
  const isHidden = drawer.style.display === 'none' || drawer.style.display === '';
  drawer.style.display = isHidden ? 'block' : 'none';
  if (btn) {
    btn.innerHTML = isHidden
      ? '🏛️ Ukryj bazę tematów ▴'
      : '🏛️ Baza 110 tematów MEiL ▾';
  }
}

function toggleAccordion(modKey) {
  const header = document.querySelector(`.module-header[onclick*="${modKey}"]`);
  const body = document.getElementById(`body_${modKey}`);
  const chev = document.getElementById(`chev_${modKey}`);
  if (!body) return;

  const isCollapsed = body.classList.contains('collapsed');
  if (isCollapsed) {
    body.classList.remove('collapsed');
    if (header) header.classList.add('active');
    if (chev) chev.style.transform = 'rotate(0deg)';
  } else {
    body.classList.add('collapsed');
    if (header) header.classList.remove('active');
    if (chev) chev.style.transform = 'rotate(-90deg)';
  }
}

function toggleAllAccordions(expand) {
  ['mod1', 'mod2', 'mod3', 'mod4'].forEach(key => {
    const header = document.querySelector(`.module-header[onclick*="${key}"]`);
    const body = document.getElementById(`body_${key}`);
    const chev = document.getElementById(`chev_${key}`);
    if (body) {
      if (expand) {
        body.classList.remove('collapsed');
        if (header) header.classList.add('active');
        if (chev) chev.style.transform = 'rotate(0deg)';
      } else {
        body.classList.add('collapsed');
        if (header) header.classList.remove('active');
        if (chev) chev.style.transform = 'rotate(-90deg)';
      }
    }
  });
}

function updateAccordionPills() {
  // Moduł 1: Pasażerowie & Zasięg & Prędkość
  const ac = document.getElementById('aircraft_type')?.value || 'piston_ga';
  const nPax = document.getElementById('n_pax')?.value || '1';
  const mCargo = document.getElementById('m_cargo')?.value || '0';
  const rKm = document.getElementById('range_km')?.value || '640';
  const vCr = document.getElementById('cruise_speed_kmh')?.value || '174';
  const pill1 = document.getElementById('pill_mod1');
  if (pill1) {
    pill1.textContent = (ac === 'uav')
      ? `UAV (0 os.) • ${mCargo} kg sensory • ${rKm} km • ${vCr} km/h`
      : `${nPax} pas. • ${rKm} km • ${vCr} km/h`;
  }

  // Moduł 2: Układ skrzydła & Wydłużenie & Zbieżność
  const wingCfg = document.getElementById('wing_config')?.value || 'low';
  const cfgNames = { low: 'Dolnopłat', high: 'Górnopłat', braced_high: 'Zastrzałowy', mid: 'Średniopłat' };
  const ar = document.getElementById('aspect_ratio')?.value || '7.3';
  const pill2 = document.getElementById('pill_mod2');
  if (pill2) pill2.textContent = `${cfgNames[wingCfg] || wingCfg} • AR=${ar}`;

  // Moduł 3: Mechanizacja & Cz_max (Klapy + Lotki)
  const flap = document.getElementById('flap_type')?.value || 'single_slotted';
  const aileron = document.getElementById('aileron_type')?.value || 'differential';
  const flapShort = {
    plain: 'Zwykła',
    split: 'Krokodylowa',
    junkers: 'Junkersa',
    single_slotted: '1-szczelinowa',
    fowler: 'Fowlera',
    double_slotted: '2-szczelinowa',
    flaperon: 'Klapolotka'
  };
  const czLnd = document.getElementById('cz_max_lnd')?.value || '2.05';
  const pill3 = document.getElementById('pill_mod3');
  if (pill3) {
    if (flap === 'flaperon' || aileron === 'flaperon') {
      pill3.textContent = `Klapolotka (Flaperon) • Cz=${czLnd}`;
    } else {
      pill3.textContent = `Klapa ${flapShort[flap] || flap} + Lotki • Cz=${czLnd}`;
    }
  }

  // Moduł 4: Silnik & SFC
  const eng = document.getElementById('engine_type')?.value || 'prop';
  const sfc = document.getElementById('sfc')?.value || (eng === 'jet' ? '0.62' : '265');
  const etaP = document.getElementById('prop_efficiency')?.value || '0.80';
  const pill4 = document.getElementById('pill_mod4');
  if (pill4) {
    pill4.textContent = eng === 'none' ? 'Bez napędu — szybowiec' : eng === 'jet'
      ? `Odrzutowy • TSFC=${sfc} 1/h`
      : `Śmigłowy • ${sfc} g/kWh • ηp=${etaP}`;
  }
}

let popoverHideTimer = null;
let activeIconEl = null;

/**
 * INICJALIZACJA SYSTEMU DYDAKTYCZNEGO:
 * - Większość wskazówek pojawia się w pływającym dymku po najechaniu na okrągłą ikonkę (i) obok nazwy parametru
 * - Opcjonalnie można też rozwinąć skrócone podpowiedzi pod polami przyciskiem w pasku nawigacji
 * - Podpina karty Plusów i Minusów dla wyboru Klapy, Slotu i Układu Skrzydła
 */
function initDidacticSystem() {
  if (typeof PARAMETER_ENCYCLOPEDIA !== 'undefined') {
    for (const [paramKey, info] of Object.entries(PARAMETER_ENCYCLOPEDIA)) {
      const hintEl = document.getElementById(`hint_${paramKey}`);
      if (hintEl) {
        hintEl.innerHTML = `
          <strong>Co to jest (${info.symbol}):</strong> ${info.short_desc}
          <span class="hint-range">📏 Typowo: ${info.typical_ranges}</span>
        `;
      }
    }
  }

  // Obsługa najechania (hover / focus / click) na okrągłe ikonki informacyjne (i)
  const infoIcons = document.querySelectorAll('.info-circle-icon[data-param]');
  const popover = document.getElementById('didacticPopover');

  infoIcons.forEach(icon => {
    const paramKey = icon.getAttribute('data-param');
    icon.addEventListener('mouseenter', () => {
      clearTimeout(popoverHideTimer);
      showDidacticPopover(paramKey, icon);
    });
    icon.addEventListener('mouseleave', () => {
      scheduleHideDidacticPopover();
    });
    icon.addEventListener('focus', () => {
      clearTimeout(popoverHideTimer);
      showDidacticPopover(paramKey, icon);
    });
    icon.addEventListener('blur', () => {
      scheduleHideDidacticPopover();
    });
    icon.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      clearTimeout(popoverHideTimer);
      showDidacticPopover(paramKey, icon);
    });
  });

  if (popover) {
    popover.addEventListener('mouseenter', () => {
      clearTimeout(popoverHideTimer);
    });
    popover.addEventListener('mouseleave', () => {
      scheduleHideDidacticPopover();
    });
  }

  document.addEventListener('scroll', () => {
    if (activeIconEl && popover && popover.classList.contains('visible')) {
      positionPopoverNearIcon(popover, activeIconEl);
    }
  }, { passive: true });

  // Przycisk przełączania widoczności dodatkowych opisów pod wszystkimi polami naraz
  const toggleBtn = document.getElementById('toggleDidacticHintsBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      document.body.classList.toggle('show-inline-hints');
      const inlineShown = document.body.classList.contains('show-inline-hints');
      toggleBtn.textContent = inlineShown
        ? 'Ukryj objaśnienia'
        : 'Objaśnienia';
      toggleBtn.setAttribute('aria-pressed', String(inlineShown));
    });
  }

  // Obsługa wyboru Klapy, Lotki i Slotu -> Karta Plusy i Minusy + przeliczenie Cz_max,lnd
  const flapSel = document.getElementById('flap_type');
  const aileronSel = document.getElementById('aileron_type');
  const slatSel = document.getElementById('slat_type');
  const flapSpanInput = document.getElementById('flap_span_ratio');
  if (flapSel) {
    flapSel.addEventListener('change', () => {
      if (flapSel.value === 'flaperon' && aileronSel) {
        aileronSel.value = 'flaperon';
      } else if (flapSel.value !== 'flaperon' && aileronSel && aileronSel.value === 'flaperon') {
        aileronSel.value = 'differential';
      }
      renderFlapDidacticCard(true);
      performCalculation();
    });
  }
  if (aileronSel) {
    aileronSel.addEventListener('change', () => {
      if (aileronSel.value === 'flaperon' && flapSel) {
        flapSel.value = 'flaperon';
      } else if (aileronSel.value !== 'flaperon' && flapSel && flapSel.value === 'flaperon') {
        flapSel.value = 'single_slotted';
      }
      renderFlapDidacticCard(true);
      performCalculation();
    });
  }
  if (slatSel) {
    slatSel.addEventListener('change', () => {
      renderFlapDidacticCard(true);
      performCalculation();
    });
  }
  if (flapSpanInput) {
    flapSpanInput.addEventListener('change', () => {
      performCalculation();
    });
  }

  // Obsługa wyboru układu skrzydła -> Karta Plusy i Minusy układu nośnego
  const wingCfgSel = document.getElementById('wing_config');
  if (wingCfgSel) {
    wingCfgSel.addEventListener('change', () => {
      renderWingConfigDidacticCard();
      performCalculation();
    });
  }

  renderFlapDidacticCard(false);
  renderWingConfigDidacticCard();
}

function showDidacticPopover(paramKey, anchorEl) {
  if (typeof PARAMETER_ENCYCLOPEDIA === 'undefined') return;
  const info = PARAMETER_ENCYCLOPEDIA[paramKey];
  const popover = document.getElementById('didacticPopover');
  if (!info || !popover) return;
  clearTimeout(popoverHideTimer);

  if (activeIconEl && activeIconEl !== anchorEl) {
    activeIconEl.classList.remove('active');
    activeIconEl.setAttribute('aria-expanded', 'false');
  }
  activeIconEl = anchorEl;
  anchorEl.classList.add('active');
  anchorEl.setAttribute('aria-expanded', 'true');
  anchorEl.setAttribute('aria-controls', 'didacticPopover');

  // Okno modalne leży w warstwie górnej; kartoteka musi być w nim, żeby nie zniknęła pod spodem.
  const host = anchorEl.closest('dialog[open]') || document.body;
  if (popover.parentElement !== host) host.appendChild(popover);

  document.getElementById('popSymbol').textContent = info.symbol;
  document.getElementById('popTitle').textContent = info.title;
  // Treść karty i objaśnienia pod polem pochodzi z jednego miejsca (didactic_modes.js).
  document.getElementById('popBody').innerHTML = window.BipolDidactic
    ? window.BipolDidactic.cardHtml(paramKey, anchorEl)
    : `<div class="didactic-popover-section green">${info.short_desc}</div>`;
  popover.scrollTop = 0;

  popover.classList.add('visible');
  popover.setAttribute('aria-hidden', 'false');
  positionPopoverNearIcon(popover, anchorEl);
}

function positionPopoverNearIcon(popover, anchorEl) {
  const rect = anchorEl.getBoundingClientRect();
  const popRect = popover.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const gap = 10;

  // Preferuj wyświetlenie po prawej stronie ikonki (i); jeśli brak miejsca, po lewej lub pod spodem
  let left = rect.right + gap;
  if (left + popRect.width > vw - 14) {
    left = rect.left - popRect.width - gap;
  }
  if (left < 12) {
    left = Math.max(12, Math.min(vw - popRect.width - 12, rect.left));
  }

  let top = rect.top - 12;
  if (top + popRect.height > vh - 14) {
    top = vh - popRect.height - 14;
  }
  if (top < 12) {
    top = 12;
  }

  popover.style.left = `${Math.round(left)}px`;
  popover.style.top = `${Math.round(top)}px`;
}

// Jawne zamknięcie (×, Escape, dotknięcie obok) działa od razu; zjechanie kursorem — z opóźnieniem,
// żeby dało się przejść z ikonki na kartę.
function hideDidacticPopover() {
  clearTimeout(popoverHideTimer);
  const popover = document.getElementById('didacticPopover');
  if (popover) {
    popover.classList.remove('visible');
    popover.setAttribute('aria-hidden', 'true');
  }
  if (activeIconEl) {
    activeIconEl.classList.remove('active');
    activeIconEl.setAttribute('aria-expanded', 'false');
    activeIconEl = null;
  }
}

function scheduleHideDidacticPopover() {
  clearTimeout(popoverHideTimer);
  popoverHideTimer = setTimeout(hideDidacticPopover, 140);
}

// Renderowanie Karty Plusów i Minusów wybranej Klapy, Lotki oraz Slotu (wg Rozdz. 16 i 17 prof. C. Galińskiego)
function renderFlapDidacticCard(autoUpdateCz = false) {
  const card = document.getElementById('flapDidacticCard');
  if (!card || typeof DIDACTIC_DATABASE === 'undefined') return;

  const flapId = document.getElementById('flap_type')?.value || 'single_slotted';
  const aileronId = document.getElementById('aileron_type')?.value || 'differential';
  const slatId = document.getElementById('slat_type')?.value || 'none';

  const flap = DIDACTIC_DATABASE.flaps[flapId] || DIDACTIC_DATABASE.flaps.single_slotted;
  const aileron = (DIDACTIC_DATABASE.ailerons && DIDACTIC_DATABASE.ailerons[aileronId]) || null;
  const slat = DIDACTIC_DATABASE.slats[slatId] || DIDACTIC_DATABASE.slats.none;

  const czClean = parseFloat(document.getElementById('cz_max_clean')?.value || 1.40);
  const computedCzLnd = +(czClean + flap.delta_cz_max + slat.delta_cz_max).toFixed(2);

  if (autoUpdateCz) {
    setFieldValue('cz_max_lnd', computedCzLnd);
  }

  card.innerHTML = `
    <div class="flap-card-top">
      <div>
        <div style="font-size:0.72rem; text-transform:uppercase; font-weight:800; color:#0284c7;">
          📖 Krawędź Spływu: Klapy &bull; Lotki &bull; Sloty (${flap.reference})
        </div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">
          ${flap.name} + ${aileron ? aileron.name : 'Lotki konwencjonalne'} ${slatId !== 'none' ? '+ ' + slat.name : ''}
        </div>
        <div style="margin-top:4px; display:flex; flex-wrap:wrap; gap:0.35rem;">
          <span class="badge badge-success">ΔCz_klapy = +${flap.delta_cz_max.toFixed(2)}</span>
          ${aileron ? `<span class="badge badge-info">Lotki: +${aileron.delta_a_up_deg}° / -${aileron.delta_a_down_deg}°</span>` : ''}
          ${aileron ? `<span class="badge" style="background:#e0f2fe; color:#0369a1;">pb/(2V) ≈ ${aileron.typical_pb_2v}</span>` : ''}
          ${slat.delta_cz_max > 0 ? `<span class="badge badge-info">ΔCz_slotu = +${slat.delta_cz_max.toFixed(2)} (Δα_kryt +${slat.alpha_crit_inc_deg}°)</span>` : ''}
          <span class="badge badge-warning">ΔCx0_lnd = +${flap.delta_cx0_lnd.toFixed(3)}</span>
        </div>
      </div>
      <div style="display:flex; gap:0.5rem; align-items:center;">
        <div class="flap-svg-box" title="Schemat kinematyczny klapy">${flap.svg_icon}</div>
        ${aileron ? `<div class="flap-svg-box" title="Schemat lotki">${aileron.svg_icon}</div>` : ''}
      </div>
    </div>

    <div class="pros-cons-grid">
      <div class="pros-box">
        <h5>👍 PLUSY (Zalety klap i lotek):</h5>
        <ul>
          ${flap.pros.map(p => `<li><strong>[Klapa]</strong> ${p}</li>`).join('')}
          ${aileron ? aileron.pros.map(p => `<li><strong>[Lotka]</strong> ${p}</li>`).join('') : ''}
          ${slatId !== 'none' ? slat.pros.map(p => `<li><strong>[Slot]</strong> ${p}</li>`).join('') : ''}
        </ul>
      </div>
      <div class="cons-box">
        <h5>⚠️ MINUSY (Wady i zagrożenia konstrukcyjne):</h5>
        <ul>
          ${flap.cons.map(c => `<li><strong>[Klapa]</strong> ${c}</li>`).join('')}
          ${aileron ? aileron.cons.map(c => `<li><strong>[Lotka]</strong> ${c}</li>`).join('') : ''}
          ${slatId !== 'none' ? slat.cons.map(c => `<li><strong>[Slot]</strong> ${c}</li>`).join('') : ''}
        </ul>
      </div>
    </div>

    <div class="galinski-quote-box">
      <strong>📘 Prof. C. Galiński (PW MEiL):</strong> „${flap.galinski_quote}”
      ${aileron ? `<br><strong>📘 Sterowanie poprzeczne (lotki):</strong> „${aileron.galinski_quote}”` : ''}
      <div style="margin-top:4px; font-size:0.73rem; color:#0f172a;">
        <strong>✈️ Przykłady maszyn:</strong> ${flap.typical_aircraft} &bull; ${aileron ? aileron.typical_aircraft : ''} &bull;
        <strong>Wyliczony Cz_max,lnd = ${computedCzLnd}</strong>
      </div>
    </div>
  `;
}

// Widget podsumowania podziału rozpiętości krawędzi spływu (Klapy vs Lotki)
function updateTrailingEdgeLayoutWidget(res) {
  if (!res || !res.geometry || !res.geometry.control_surfaces) return;
  const cs = res.geometry.control_surfaces;
  const f = cs.flaps;
  const a = cs.ailerons;
  const part = cs.trailing_edge_partition;

  const badge = document.getElementById('cs_layout_badge');
  if (badge) {
    badge.textContent = cs.is_flaperon ? 'Klapolotka (Flaperon)' : 'Klapy wewn. + Lotki zewn.';
    badge.className = cs.is_flaperon ? 'badge badge-warning' : 'badge badge-info';
  }

  const bFus = document.getElementById('bar_fuselage');
  const bFlaps = document.getElementById('bar_flaps');
  const bGap = document.getElementById('bar_gap');
  const bAil = document.getElementById('bar_ailerons');
  const bTip = document.getElementById('bar_tip');

  if (bFus && bFlaps && bGap && bAil && bTip) {
    bFus.style.width = `${part.fuselage_gap_pct}%`;
    bFus.title = `Kadłub (${part.fuselage_gap_pct}%)`;

    bFlaps.style.width = `${part.flap_span_pct}%`;
    bFlaps.textContent = cs.is_flaperon ? `Klapolotka (${part.flap_span_pct}%)` : `Klapy (${part.flap_span_pct}%)`;
    bFlaps.title = `Klapy: bf=${f.b_f_m}m, Sf=${f.S_flap_surface_m2}m²`;

    bGap.style.width = `${part.clearance_gap_pct}%`;
    bGap.style.display = cs.is_flaperon ? 'none' : 'block';

    bAil.style.width = `${part.aileron_span_pct}%`;
    bAil.textContent = cs.is_flaperon ? '' : `Lotki (${part.aileron_span_pct}%)`;
    bAil.style.display = cs.is_flaperon ? 'none' : 'block';
    bAil.title = `Lotki: ba=${a.b_a_m}m, Sa=${a.S_aileron_surface_m2}m²`;

    bTip.style.width = `${part.tip_clearance_pct}%`;
  }

  const flapsText = document.getElementById('cs_flaps_text');
  if (flapsText) {
    flapsText.innerHTML = `bf = <b>${f.b_f_m} m</b> (${(f.bf_over_b * 100).toFixed(1)}% b), Sf = <b>${f.S_flap_surface_m2} m²</b> (${(f.s_flapped_over_s * 100).toFixed(1)}% S)`;
  }

  const aileronsText = document.getElementById('cs_ailerons_text');
  if (aileronsText) {
    aileronsText.innerHTML = `ba = <b>${a.b_a_m} m</b> (${(a.ba_over_b * 100).toFixed(1)}% b), Sa = <b>${a.S_aileron_surface_m2} m²</b> (${(a.s_aileron_over_s * 100).toFixed(1)}% S)`;
  }

  const rollText = document.getElementById('cs_roll_text');
  if (rollText) {
    rollText.innerHTML = `Skuteczność poprzeczna: <b>pb/(2V) = ${a.roll_helix_pb_2v}</b> [${a.roll_authority_ok ? '<span style="color:#059669;">Spełnione kryterium wstępne</span>' : '<span style="color:#d97706;">Poniżej kryterium wstępnego</span>'}] &bull; <b>${cs.stall_safety.verdict}</b>`;
  }
}

// Renderowanie Karty Plusów i Minusów wybranego Układu Skrzydła (Dolnopłat / Górnopłat / Zastrzałowy / Średniopłat)
function renderWingConfigDidacticCard() {
  const box = document.getElementById('wingConfigDidacticBox');
  if (!box || typeof DIDACTIC_DATABASE === 'undefined') return;

  const cfgId = document.getElementById('wing_config')?.value || 'low';
  const cfg = DIDACTIC_DATABASE.wing_config[cfgId] || DIDACTIC_DATABASE.wing_config.low;

  box.innerHTML = `
    <div style="font-size:0.78rem; font-weight:800; color:#0f172a; margin-bottom:0.35rem; display:flex; justify-content:space-between;">
      <span>📐 Układ Płata: ${cfg.name}</span>
      <span style="color:#0284c7; font-size:0.72rem;">${cfg.reference}</span>
    </div>
    <div class="pros-cons-grid" style="margin-bottom:0.35rem;">
      <div class="pros-box">
        <h5>👍 PLUSY układu:</h5>
        <ul>${cfg.pros.map(p => `<li>${p}</li>`).join('')}</ul>
      </div>
      <div class="cons-box">
        <h5>⚠️ MINUSY układu:</h5>
        <ul>${cfg.cons.map(c => `<li>${c}</li>`).join('')}</ul>
      </div>
    </div>
    <div class="galinski-quote-box">
      <strong>📘 Zasada prof. C. Galińskiego:</strong> ${cfg.galinski_quote}
    </div>
  `;
}

// Wypełnianie kategorii wydziałowych
function populateCategorySelect() {
  const sel = document.getElementById('categorySelect');
  if (!sel) return;
  sel.innerHTML = '<option value="all">-- Wszystkie 13 kategorii wydziałowych (110 tematów) --</option>';
  for (const [key, name] of Object.entries(categoriesData)) {
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = name;
    sel.appendChild(opt);
  }
}

// Wypełnianie listy 110 tematów
function populateTopicsSelect(filterCat) {
  const sel = document.getElementById('topicSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- Wybierz oficjalny temat z listy wydziałowej BIPOL I --</option>';
  
  const filtered = filterCat === 'all' 
    ? topicsData 
    : topicsData.filter(t => t.category === filterCat);

  filtered.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = t.title;
    sel.appendChild(opt);
  });
}

// Załadowanie tematu wybranego z listy wydziałowej
function loadTopic(topicId) {
  const topic = topicsData.find(t => String(t.id) === String(topicId));
  if (topic) BipolDesignBasis.loadTopic(topic);
}

function setFieldValue(id, val) {
  const el = document.getElementById(id);
  if (el && val !== undefined) {
    el.value = val;
  }
}

function collectFormData() {
  const data = { ...formBaseParams };
  const inputs = document.querySelectorAll('#designForm input, #designForm select, [data-analysis-param]');
  inputs.forEach(input => {
    if (!input.id || input.type === 'checkbox') return;
    const val = input.value;
    if (input.type === 'number') {
      data[input.id] = parseFloat(val);
    } else {
      data[input.id] = val;
    }
  });

  // Przekaż parametry wybranej klapy do obliczeń aerodynamicznych
  if (typeof DIDACTIC_DATABASE !== 'undefined') {
    const flap = DIDACTIC_DATABASE.flaps[data.flap_type] || DIDACTIC_DATABASE.flaps.single_slotted;
    data['delta_cx0_flaps_lnd'] = flap.delta_cx0_lnd;
    const sameLift = data.cz_max_clean === formBaseParams.cz_max_clean && data.cz_max_lnd === formBaseParams.cz_max_lnd;
    data.cz_max_to = sameLift && formBaseParams.cz_max_to != null
      ? formBaseParams.cz_max_to
      : +(data.cz_max_clean + 0.6 * (data.cz_max_lnd - data.cz_max_clean)).toFixed(2);
  }

  const activeProj = typeof getActiveProject === 'function' ? getActiveProject() : null;
  const nameEl = document.getElementById('projectNameDisplay');
  data['name'] = activeProj ? activeProj.name : (nameEl ? nameEl.textContent.trim() : 'Wstępny Projekt Samolotu');
  data['locked_params'] = Array.from(window.userLockedParams || []);
  const basis = window.BipolDesignBasis ? BipolDesignBasis.collect(data) : data;
  return window.Bipol1 ? Bipol1.collect(basis) : basis;
}

let calculationSequence = 0;
let calculationController = null;

function showCalculationStatus(message, error = false) {
  const status = document.getElementById('calculationStatus');
  if (status) {
    status.textContent = message;
    status.classList.toggle('is-error', error);
    status.setAttribute('role', error ? 'alert' : 'status');
  }
}

function validateNumericFields(root) {
  for (const input of root.querySelectorAll('input[type="number"]')) {
    if (input.disabled || input.readOnly) continue;
    if (input.value.trim() === '' || !Number.isFinite(Number(input.value)) || !input.checkValidity()) {
      const label = document.querySelector(`label[for="${input.id}"]`)?.textContent.trim() || input.id;
      throw new Error(`Sprawdź pole „${label}”. ${input.validationMessage || 'Podaj liczbę.'}`);
    }
  }
}

async function performCalculation() {
  document.dispatchEvent(new CustomEvent('bipol:calculating'));
  const sequence = ++calculationSequence;
  calculationController?.abort();
  const controller = new AbortController();
  calculationController = controller;
  const projectId = getActiveProjectId();
  const btn = document.getElementById('calcBtn');
  const reportBtn = document.getElementById('openReportBtn');
  if (reportBtn) reportBtn.setAttribute('data-results-stale', 'true');
  try {
    validateNumericFields(document.getElementById('designForm'));
    const analysisControls = document.getElementById('trendControls');
    if (analysisControls) validateNumericFields(analysisControls);
    const formData = collectFormData();
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Obliczanie…';
    }
    showCalculationStatus('Trwają obliczenia.');
    const resp = await fetch('/api/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData), signal: controller.signal
    });
    const result = await resp.json();
    if (!resp.ok) throw new Error(result.message || 'Błąd obliczeń');
    if (sequence !== calculationSequence || projectId !== getActiveProjectId()) return;
    if (JSON.stringify(formData) !== JSON.stringify(collectFormData())) {
      showCalculationStatus('Parametry zmieniły się w trakcie obliczeń. Oblicz projekt ponownie.');
      return;
    }
    currentResults = result;
    updateUI(result);
    if (typeof updateDerivedUI === 'function' && result.constraints && result.constraints.parameter_states) {
      updateDerivedUI(result.constraints.parameter_states);
    }
    autoSaveActiveProject(result);
    showCalculationStatus(projectStore.persistent ? 'Wyniki i zapis projektu są aktualne.' : 'Wyniki są aktualne. Zapis w przeglądarce jest niedostępny — pobierz JSON przed zamknięciem karty.');
    document.dispatchEvent(new CustomEvent('bipol:results', {detail: result}));
    if (reportBtn) reportBtn.setAttribute('data-results-stale', 'false');
  } catch (err) {
    if (err.name !== 'AbortError' && sequence === calculationSequence) {
      showCalculationStatus('Błąd: ' + err.message + ' Wyświetlane wyniki nie zostały zaktualizowane.', true);
    }
  } finally {
    if (btn && sequence === calculationSequence) {
      btn.disabled = false;
      btn.textContent = 'Przelicz projekt';
    }
  }
}

function updateUI(res) {
  if (!res) return;
  const scopeCard=document.getElementById('studioModelScope'), scopeList=document.getElementById('studioModelScopeList');
  if(scopeCard&&scopeList){
    const notes=res.model_scope?.limitations||[];
    scopeCard.hidden=notes.length===0;scopeList.replaceChildren();
    for(const note of notes){const item=document.createElement('li');item.textContent=note;scopeList.appendChild(item);}
  }
  // 1. Zaktualizuj KPI główne z bezpieczną obsługą brakujących wartości
  try {
    const kpiM0 = document.getElementById('kpi_m0');
    if (kpiM0) kpiM0.textContent = (res.mass?.m0 != null ? res.mass.m0.toFixed(1) : '---') + ' kg';

    const kpiS = document.getElementById('kpi_wing_s');
    if (kpiS) kpiS.textContent = (res.geometry?.wing?.S != null ? res.geometry.wing.S.toFixed(2) : '---') + ' m²';

    const kpiB = document.getElementById('kpi_wingspan');
    if (kpiB) kpiB.textContent = (res.geometry?.wing?.b != null ? res.geometry.wing.b.toFixed(2) : '---') + ' m';

    const kpiWy = document.getElementById('kpi_wy_max');
    if (kpiWy) kpiWy.textContent = (res.performance?.climb?.wy_max_ms != null ? res.performance.climb.wy_max_ms.toFixed(2) : '---') + ' m/s';

    const kpiVs0 = document.getElementById('kpi_vs0');
    if (kpiVs0) kpiVs0.textContent = (res.performance?.speeds?.vs_lnd_kmh != null ? res.performance.speeds.vs_lnd_kmh.toFixed(1) : '---') + ' km/h';

    const kpiSm = document.getElementById('kpi_sm');
    if (kpiSm) kpiSm.textContent = (res.balance?.stability?.static_margin_aft_pct != null ? res.balance.stability.static_margin_aft_pct.toFixed(1) : '---') + '% ŚDA';
  } catch (err) {
    console.warn('Błąd aktualizacji kafelków KPI:', err);
  }

  // 2. Odśwież wizualizacje dla aktualnie aktywnej zakładki
  try {
    const activeTab = document.querySelector('.tab-content.active');
    const activeTabId = activeTab ? activeTab.id : 'tab-cad';
    renderTabVisuals(activeTabId);
  } catch (err) {
    console.warn('Błąd renderTabVisuals:', err);
  }

  // 2b. Rozkład krawędzi spływu: Klapy i Lotki
  try { updateTrailingEdgeLayoutWidget(res); } catch (err) { console.warn('Błąd updateTrailingEdgeLayoutWidget:', err); }

  // 3. Moduł CAD: Wykaz Części (BOM) i Wymiary Główne
  try { populateCadTables(res); } catch (err) { console.warn('Błąd populateCadTables:', err); }

  // 4. Moduł P1/P2: Wymagania, MTOW, Torenbeek i Punkt Projektowy
  try { populateP1P2Tables(res); } catch (err) { console.warn('Błąd populateP1P2Tables:', err); }

  // 5. Moduł P3: Geometria Skrzydła, ŚDA/MAC, Kadłub, Usterzenia, Podwozie, Schrenk
  try { populateP3Tables(res); } catch (err) { console.warn('Błąd populateP3Tables:', err); }

  // 6. Moduł P4: Mechanizacja Płata i Punkty Optymalne Biegunowej
  try { populateP4Tables(res); } catch (err) { console.warn('Błąd populateP4Tables:', err); }

  // 7. Moduł P5: Spektrum Prędkości, Wznoszenie, Pułap, Start/Lądowanie, Zakręt
  try { populateP5Tables(res); } catch (err) { console.warn('Błąd populateP5Tables:', err); }

  // 8. Moduł P6: Obwiednia V-n, Stany Załadowania, Stateczność Statyczna
  try { populateP6Tables(res); } catch (err) { console.warn('Błąd populateP6Tables:', err); }

  // 9. Weryfikacja wymagań i Asystent Dydaktyczny
  try { updateDidacticAdvisor(res); } catch (err) { console.warn('Błąd updateDidacticAdvisor:', err); }

  try {
    const checksTbody = document.getElementById('complianceChecksBody');
    if (checksTbody && Array.isArray(res.compliance_checks)) {
      const rank = c => c.passed ? 2 : (c.severity === 'warning' ? 1 : 0);
      const sortedChecks = [...res.compliance_checks].sort((a, b) => rank(a) - rank(b));
      const passedCount = res.compliance_checks.filter(c => c.passed).length;
      const failedCount = res.compliance_checks.length - passedCount;
      const summaryEl = document.querySelector('#complianceChecksDisclosure > summary');
      if (summaryEl) {
        summaryEl.textContent = failedCount > 0
          ? `Weryfikacja Założeń Taktyczno-Technicznych (${passedCount}/${res.compliance_checks.length} spełnionych — ${failedCount} do poprawy)`
          : `Weryfikacja Założeń Taktyczno-Technicznych (wszystkie ${passedCount}/${res.compliance_checks.length} spełnione ✓)`;
      }
      checksTbody.innerHTML = sortedChecks.map(c => {
        return `
        <tr>
          <td><b>${c.parameter}</b><br><small style="color:#64748b;">${c.note}</small></td>
          <td>${c.required}</td>
          <td><b>${c.actual}</b></td>
          <td>
            <span class="badge ${c.passed ? 'badge-success' : (c.severity === 'warning' ? 'badge-warning' : 'badge-danger')}">
              ${c.passed ? '✓ Zgodne' : (c.severity === 'warning' ? 'Do oceny' : '✗ Niespełnione')}
            </span>
            ${complianceFixButton(c)}
          </td>
        </tr>`;
      }).join('');
    }
  } catch (err) {
    console.warn('Błąd complianceChecks:', err);
  }

  // 10. Aktualizacja pigułek nagłówków modułów (Live Modularity Badges)
  try { updateAccordionPills(); } catch (err) { console.warn('Błąd updateAccordionPills:', err); }

  // 11. Przycisk generowania raportu
  try {
    const reportBtn = document.getElementById('openReportBtn');
    if (reportBtn) {
      const currentParams = res.params;
      reportBtn.href = `/report?params_json=${encodeURIComponent(JSON.stringify(currentParams))}`;
      reportBtn.onclick = null;
    }
  } catch (err) {
    console.warn('Błąd konfiguracji przycisku raportu:', err);
  }

  // 12. Aktualizacja danych w Wersji 2 Portalu: Projekty Semestralne P1–P6
  try {
    if (typeof hydrateSemesterProjectsData === 'function') {
      hydrateSemesterProjectsData(res);
    }
  } catch (err) {
    console.warn('Błąd hydrateSemesterProjectsData:', err);
  }
}

// Renderowanie wizualizacji modułowych (Canvas / SVG) zależnie od aktywnego modułu
function renderTabVisuals(targetId) {
  if (!currentResults) return;
  setTimeout(() => {
    switch (targetId) {
      case 'tab-cad':
        render3ViewBlueprint('blueprintView', currentResults.geometry, currentResults);
        break;
      case 'tab-p1-p2':
        drawMatchingChart('chartMatching', currentResults.sizing);
        break;
      case 'tab-p3':
        drawSchrenkChart('chartSchrenk', currentResults.geometry.schrenk);
        break;
      case 'tab-p4':
        drawPolarChart('chartPolar', currentResults.aerodynamics);
        break;
      case 'tab-p5':
        drawClimbChart('chartClimb', currentResults.performance.climb);
        break;
      case 'tab-p6':
        drawVnEnvelope('chartVn', currentResults.envelope);
        drawBalanceDiagram('chartBalance', currentResults.balance);
        break;
    }
  }, 40);
}

// 3. Tabele Modułu CAD (BOM i Wymiarowanie PN-EN ISO 129 / 6433)
function populateCadTables(res) {
  const isJet = (res.sizing?.engine_type === 'jet') || (document.getElementById('engine_type')?.value === 'jet');
  const bomTbody = document.getElementById('cadBomTableBody');
  if (bomTbody) {
    const bd = res.mass?.breakdown || {};
    const propDesc = isJet
      ? '<b>Zespół napędowy</b> (silniki turboodrzutowe, gondole i pylony)'
      : '<b>Zespół napędowy</b> (silnik ze śmigłem i osprzętem)';
    const propMount = isJet
      ? 'Zabudowa w gondolach kadłubowych / podskrzydłowych'
      : 'Zabudowa w nosie kadłuba / gondoli skrzydłowej';
    bomTbody.innerHTML = `
      <tr><td>6</td><td class="num">1 kpl</td><td>${propDesc}</td><td>PW-ZPK-06</td><td>Inconel / Tytan / Dural</td><td class="num">${(bd.m_propulsion || 0).toFixed(1)}</td><td>${propMount}</td></tr>
      <tr><td>5</td><td class="num">1 kpl</td><td><b>Podwozie trójpodporowe</b> (przednie + główne)</td><td>PW-ZPK-05</td><td>Stal 30HGSA / Dural PA6</td><td class="num">${(bd.m_gear || 0).toFixed(1)}</td><td>Golenie teleskopowe z amortyzatorami</td></tr>
      <tr><td>4</td><td class="num">1 kpl</td><td><b>Usterzenie poziome</b> (statecznik + ster wys.)</td><td>PW-ZPK-04</td><td>Stop duralowy PA7 / Kompozyt</td><td class="num">${((bd.m_tail || 0) * 0.6).toFixed(1)}</td><td>Profil symetryczny NACA 0009 / 0012</td></tr>
      <tr><td>3</td><td class="num">1 kpl</td><td><b>Usterzenie pionowe</b> (statecznik + ster kier.)</td><td>PW-ZPK-03</td><td>Stop duralowy PA7 / Kompozyt</td><td class="num">${((bd.m_tail || 0) * 0.4).toFixed(1)}</td><td>Płetwa grzbietowa i wyważenie rogowe</td></tr>
      <tr><td>2</td><td class="num">1 kpl</td><td><b>Skrzydło nośne</b> (keson, dźwigar, lotki, klapy)</td><td>PW-ZPK-02</td><td>Dural PA7 (2024-T3) / PA9</td><td class="num">${(bd.m_wing || 0).toFixed(1)}</td><td>Dźwigar belkowy z kesonem noskowym</td></tr>
      <tr><td>1</td><td class="num">1 szt</td><td><b>Kadłub półskorupowy</b> (wręgi, podłużnice, poszycie)</td><td>PW-ZPK-01</td><td>Dural PA7 / Kratownica 30HGSA</td><td class="num">${(bd.m_fuselage || 0).toFixed(1)}</td><td>Konstrukcja półskorupowa, kabina załogi</td></tr>
    `;
  }

  const dimsTbody = document.getElementById('cadDimsTableBody');
  if (dimsTbody) {
    const w = res.geometry?.wing || {};
    const f = res.geometry?.fuselage || {};
    const v = res.geometry?.vertical_tail || {};
    const g = res.geometry?.gear || {};
    const hv = v.h_v != null ? v.h_v : 1.2;
    const totalHeight = (hv + 0.9).toFixed(2);
    const sweepVal = Number(w.sweep_deg ?? w.sweep_25_deg ?? 0);
    const lenNote = isJet
      ? 'Od nosa kadłuba do krawędzi spływu usterzenia kierunku'
      : 'Od kołpaka śmigła/dziobu do krawędzi spływu steru kierunku';
    dimsTbody.innerHTML = `
      <tr><td><b>b</b></td><td>Rozpiętość całkowita skrzydła</td><td class="num"><b>${(w.b ?? 0).toFixed(2)}</b></td><td>m</td><td>Wymiar skrajny do hangarowania i obrysu rzutów</td></tr>
      <tr><td><b>L</b></td><td>Długość całkowita samolotu</td><td class="num"><b>${(f.length ?? 0).toFixed(2)}</b></td><td>m</td><td>${lenNote}</td></tr>
      <tr><td><b>H</b></td><td>Wysokość całkowita na postoju</td><td class="num"><b>${totalHeight}</b></td><td>m</td><td>Od płaszczyzny ziemi do wierzchołka usterzenia pionowego</td></tr>
      <tr><td><b>B_p</b></td><td>Rozstaw kół podwozia głównego</td><td class="num"><b>${(g.track ?? 0).toFixed(2)}</b></td><td>m</td><td>Zapewnia stabilność przeciwwywrotną przy lądowaniu z wiatrem bocznym</td></tr>
      <tr><td><b>L_p</b></td><td>Baza podwozia trójpodporowego</td><td class="num"><b>${(g.wheelbase ?? 0).toFixed(2)}</b></td><td>m</td><td>Odległość między osią koła przedniego a osią kół głównych</td></tr>
      <tr><td><b>&Gamma;</b></td><td>Kąt wzniosu skrzydła</td><td class="num"><b>${(w.dihedral_deg ?? 0).toFixed(1)}</b></td><td>&deg;</td><td>Stateczność poprzeczna i samoczynne tłumienie przechyłu</td></tr>
      <tr><td><b>&chi;₂₅</b></td><td>Kąt skosu ćwierci cięciw</td><td class="num"><b>${sweepVal.toFixed(1)}</b></td><td>&deg;</td><td>Krytyczna liczba Macha oraz wyważenie podłużne</td></tr>
    `;
  }
}

// 4. Tabele Modułu P1/P2
function populateP1P2Tables(res) {
  const p1Cat = document.getElementById('p1CategoryBadge');
  if (p1Cat) {
    const easaCode = res.easa_compliance?.easa_code || res.envelope?.limits?.category_code || (res.envelope?.limits?.category || 'cs-23');
    p1Cat.textContent = `EASA: ${easaCode.toUpperCase()}`;
  }
  const p1M0 = document.getElementById('p1KpiM0');
  if (p1M0) p1M0.textContent = (res.mass?.m0 ?? 0).toFixed(1) + ' kg';
  const p1Me = document.getElementById('p1KpiMe');
  if (p1Me) p1Me.textContent = (res.mass?.m_empty ?? 0).toFixed(1) + ' kg';
  const p1Mf = document.getElementById('p1KpiMf');
  if (p1Mf) p1Mf.textContent = (res.mass?.m_fuel ?? 0).toFixed(1) + ' kg';
  const p1Mpl = document.getElementById('p1KpiMpl');
  if (p1Mpl) p1Mpl.textContent = ((res.mass?.m_payload ?? 0) + (res.mass?.m_crew ?? 0)).toFixed(1) + ' kg';

  const p1Req = document.getElementById('p1MissionReqBody');
  if (p1Req) {
    const fd = res.params;
    const isUas = res.mass?.unmanned || fd.aircraft_type === 'uav';
    const occRows = isUas ? `
      <tr><td>Załoga na pokładzie</td><td><b>n_crew</b></td><td class="num"><b>0</b></td><td>os.</td><td>EASA UAS: sterowanie ze stacji naziemnej (GCS)</td></tr>
      <tr><td>Pasażerowie</td><td><b>n_pax</b></td><td class="num"><b>0</b></td><td>os.</td><td>Statek bezzałogowy – brak kabiny pasażerskiej</td></tr>
      <tr><td>Ładunek zadaniowy (Payload)</td><td><b>m_cargo</b></td><td class="num"><b>${fd.m_cargo}</b></td><td>kg</td><td>Sensory, głowica optoelektroniczna, łącze C2</td></tr>
    ` : `
      <tr><td>Liczba pasażerów</td><td><b>n_pax</b></td><td class="num"><b>${fd.n_pax}</b></td><td>os.</td><td>Pasażerowie kabiny z bagażem podręcznym i rejestrowanym</td></tr>
      <tr><td>Ładunek cargo / chemikalia</td><td><b>m_cargo</b></td><td class="num"><b>${fd.m_cargo}</b></td><td>kg</td><td>Dodatkowy ładunek handlowy w luku bagażowym</td></tr>
      <tr><td>Załoga lotnicza</td><td><b>n_crew</b></td><td class="num"><b>${fd.n_crew}</b></td><td>os.</td><td>Liczba pilotów obsługujących statek powietrzny</td></tr>
    `;
    p1Req.innerHTML = `
      <tr><td>Zasięg obliczeniowy</td><td><b>R</b></td><td class="num"><b>${fd.range_km}</b></td><td>km</td><td>Zasięg przelotowy z uwzględnieniem rezerw przepisowych</td></tr>
      <tr><td>Wysokość przelotu</td><td><b>H</b></td><td class="num"><b>${fd.cruise_altitude_m}</b></td><td>m</td><td>Optymalna wysokość ekonomiczna w atmosferze ISA</td></tr>
      ${occRows}
      <tr><td>Prędkość przelotowa</td><td><b>V_cr</b></td><td class="num"><b>${fd.cruise_speed_kmh}</b></td><td>km/h</td><td>Prędkość marszowa w konfiguracji gładkiej</td></tr>
      <tr><td>Maks. prędkość przeciągnięcia</td><td><b>V_s0</b></td><td class="num"><b>${fd.v_stall_kmh}</b></td><td>km/h</td><td>Prędkość przeciągnięcia z pełnymi klapami lądowania</td></tr>
      <tr><td>Całkowita długość startu</td><td><b>S_to</b></td><td class="num"><b>${fd.takeoff_distance_m}</b></td><td>m</td><td>Start do wysokości przeszkody 15 m</td></tr>
      <tr><td>Wznoszenie przy ziemi</td><td><b>w_y</b></td><td class="num"><b>${fd.climb_rate_ms}</b></td><td>m/s</td><td>Minimalna prędkość wznoszenia w warunkach ISA MSL</td></tr>
    `;
  }

  const p2Mass = document.getElementById('p2MassTableBody');
  if (p2Mass) {
    const m0 = res.mass?.m0 || 1;
    const isUas = res.mass?.unmanned;
    const payloadLabel = isUas
      ? 'Wyposażenie zadaniowe UAV (sensory / głowica optoelektroniczna)'
      : 'Masa płatna (Payload: pasażerowie + bagaż + cargo)';
    const crewLabel = isUas
      ? 'Załoga na pokładzie (0 os. – pilot w stacji naziemnej GCS)'
      : 'Załoga (Crew)';
    p2Mass.innerHTML = `
      <tr><td>${payloadLabel}</td><td><b>m_pl</b></td><td class="num"><b>${(res.mass?.m_payload ?? 0).toFixed(1)}</b></td><td class="num">${((res.mass?.payload_fraction ?? 0) * 100).toFixed(1)}%</td><td>Zadanie projektowe (założenia P1)</td></tr>
      <tr><td>${crewLabel}</td><td><b>m_crew</b></td><td class="num"><b>${(res.mass?.m_crew ?? 0).toFixed(1)}</b></td><td class="num">${(((res.mass?.m_crew ?? 0) / m0) * 100).toFixed(1)}%</td><td>Liczba pilotów &times; masa 1 osoby</td></tr>
      <tr><td>Paliwo całkowite (Fuel wg Bregueta)</td><td><b>m_f</b></td><td class="num"><b>${(res.mass?.m_fuel ?? 0).toFixed(1)}</b></td><td class="num">${((res.mass?.fuel_fraction ?? 0) * 100).toFixed(1)}%</td><td>Równanie Bregueta + 45 min rezerwy</td></tr>
      <tr><td>Masa pusta wyposażona (OEW)</td><td><b>m_e</b></td><td class="num"><b>${(res.mass?.m_empty ?? 0).toFixed(1)}</b></td><td class="num">${((res.mass?.empty_fraction ?? 0) * 100).toFixed(1)}%</td><td>Korelacja statystyczna Torenbeeka</td></tr>
      <tr style="background:#f1f5f9; font-weight:bold;"><td>Maksymalna masa startowa (MTOW)</td><td><b>m₀</b></td><td class="num"><b>${(res.mass?.m0 ?? 0).toFixed(1)}</b></td><td class="num">100.0%</td><td>Wynik zbieżności iteracyjnej bilansu</td></tr>
    `;
  }

  const p2Empty = document.getElementById('p2EmptyTableBody');
  if (p2Empty) {
    const bd = res.mass?.breakdown || {};
    const me = res.mass?.m_empty || 1;
    const m0 = res.mass?.m0 || 1;
    const rows = [
      { name: 'Skrzydło (dźwigary, żebra, pokrycie, lotki, klapy)', m: bd.m_wing || 0 },
      { name: 'Kadłub (wręgi, podłużnice, oszklenie, wyposażenie kabiny)', m: bd.m_fuselage || 0 },
      { name: 'Usterzenia poziome i pionowe ze sterami', m: bd.m_tail || 0 },
      { name: 'Podwozie trójpodporowe z układem hamulcowym', m: bd.m_gear || 0 },
      { name: 'Zespół napędowy (silnik, łoże, osprzęt, śmigło)', m: bd.m_propulsion || 0 },
      { name: 'Instalacje pokładowe, sterowanie, awionika, akumulatory', m: bd.m_systems || 0 }
    ];
    p2Empty.innerHTML = rows.map(r => `
      <tr><td><b>${r.name}</b></td><td class="num"><b>${r.m.toFixed(1)}</b></td><td class="num">${((r.m / me) * 100).toFixed(1)}%</td><td class="num">${((r.m / m0) * 100).toFixed(1)}%</td></tr>
    `).join('') + `
      <tr style="background:#f8fafc; font-weight:bold;"><td>Suma masy pustej wyposażonej (OEW)</td><td class="num"><b>${me.toFixed(1)}</b></td><td class="num">100.0%</td><td class="num">${((me / m0) * 100).toFixed(1)}%</td></tr>
    `;
  }

  const p2Dp = document.getElementById('p2DesignPointBody');
  if (p2Dp) {
    const dp = res.sizing?.design_point || {};
    p2Dp.innerHTML = `
      <tr><td>Obciążenie powierzchni skrzydła <b>(W/S)</b></td><td class="num"><b>${(dp.ws ?? 0).toFixed(1)}</b></td><td>N/m²</td><td>Ograniczenie prędkości lądowania Vs0 (maksymalne dopuszczalne W/S)</td></tr>
      <tr><td>${dp.tw ? 'Obciążenie ciągu <b>(T/W)</b>' : 'Obciążenie mocy <b>(P/W)</b>'}</td><td class="num"><b>${dp.tw ? Number(dp.tw).toFixed(3) : (dp.pw ?? 0).toFixed(1) + ' (' + (dp.pw_hp_kg ?? 0).toFixed(3) + ' KM/kg)'}</b></td><td>${dp.tw ? '-' : 'W/N'}</td><td>Ograniczenie prędkości wznoszenia w_y oraz drogi rozbiegu S_to</td></tr>
      <tr><td>Obliczona powierzchnia nośna <b>S</b></td><td class="num"><b>${(res.geometry?.wing?.S ?? 0).toFixed(2)}</b></td><td>m²</td><td>Wyznaczona ze stosunku MTOW &bull; g / (W/S)</td></tr>
      <tr><td>${dp.power_kw ? 'Wymagana moc silnika <b>P_sil</b>' : 'Wymagany ciąg silnika <b>T</b>'}</td><td class="num"><b>${dp.power_kw ? Number(dp.power_kw).toFixed(1) + ' kW (' + (dp.power_hp ?? 0).toFixed(1) + ' KM)' : (dp.thrust_kn ?? 0).toFixed(2) + ' kN'}</b></td><td>${dp.power_kw ? 'kW (KM)' : 'kN'}</td><td>Minimalna moc zespołu napędowego spełniająca wszystkie wymogi</td></tr>
    `;
  }
}

// 5. Tabele Modułu P3
function populateP3Tables(res) {
  const p3Wing = document.getElementById('p3WingTableBody');
  if (p3Wing) {
    const w = res.geometry?.wing || {};
    const sweepVal = Number(w.sweep_deg ?? w.sweep_25_deg ?? 0);
    p3Wing.innerHTML = `
      <tr><td>Powierzchnia nośna skrzydła</td><td><b>S</b></td><td class="num"><b>${(w.S ?? 0).toFixed(2)}</b></td><td>m²</td><td>Wyznaczona z punktu projektowego Matching Chart</td></tr>
      <tr><td>Rozpiętość skrzydła</td><td><b>b</b></td><td class="num"><b>${(w.b ?? 0).toFixed(2)}</b></td><td>m</td><td>Wyliczona ze wzoru b = &radic;(S &bull; &Lambda;)</td></tr>
      <tr><td>Wydłużenie skrzydła</td><td><b>&Lambda; (AR)</b></td><td class="num"><b>${(w.AR ?? 0).toFixed(2)}</b></td><td>-</td><td>Wpływa bezpośrednio na opór indukowany k = 1/(&pi;&Lambda;e)</td></tr>
      <tr><td>Zbieżność trapezowa skrzydła</td><td><b>&eta; = c_t/c_r</b></td><td class="num"><b>${(w.eta ?? 0).toFixed(2)}</b></td><td>-</td><td>Optymalna &eta; &asymp; 0.45&ndash;0.60 dla minimalnego oporu indukowanego</td></tr>
      <tr><td>Cięciwa przykadłubowa</td><td><b>c_r</b></td><td class="num"><b>${(w.cr ?? 0).toFixed(3)}</b></td><td>m</td><td>Cięciwa u nasady skrzydła przy kadłubie</td></tr>
      <tr><td>Cięciwa końcowa</td><td><b>c_t</b></td><td class="num"><b>${(w.ct ?? 0).toFixed(3)}</b></td><td>m</td><td>Cięciwa na końcówce płata</td></tr>
      <tr><td>Kąt skosu ćwierci cięciw</td><td><b>&chi;₂₅%</b></td><td class="num"><b>${sweepVal.toFixed(1)}</b></td><td>&deg;</td><td>Dla samolotów poddźwiękowych &chi; &asymp; 0&deg;, dla odrzutowych 15&ndash;35&deg;</td></tr>
      <tr><td>Kąt wzniosu skrzydła</td><td><b>&Gamma;</b></td><td class="num"><b>${(w.dihedral_deg ?? 0).toFixed(1)}</b></td><td>&deg;</td><td>Dla dolnopłata typowo 4&ndash;6&deg;, dla górnopłata 0&ndash;2&deg;</td></tr>
    `;
  }

  const p3Mac = document.getElementById('p3MacTableBody');
  if (p3Mac) {
    const w = res.geometry?.wing || {};
    const xLeMac = Number(w.x_le_mac ?? w.x_lemac ?? 0);
    p3Mac.innerHTML = `
      <tr><td>Średnia Cięciwa Aerodynamiczna (ŚDA / MAC)</td><td><b>b_A</b></td><td class="num"><b>${(w.mac ?? 0).toFixed(3)}</b></td><td>m</td><td>Długość cięciwy odniesienia momentów aerodynamicznych</td></tr>
      <tr><td>Współrzędna poprzeczna położenia ŚDA</td><td><b>y_mac</b></td><td class="num"><b>${(w.y_mac ?? 0).toFixed(3)}</b></td><td>m</td><td>Odległość od osi symetrii samolotu: y_mac = (b/6)&bull;(1+2&eta;)/(1+&eta;)</td></tr>
      <tr><td>Współrzędna wzdłużna noska ŚDA od natarcia c_r</td><td><b>x_lemac</b></td><td class="num"><b>${xLeMac.toFixed(3)}</b></td><td>m</td><td>Przesunięcie noska ŚDA w osi X: x_lemac = y_mac &bull; tg(&chi;_LE)</td></tr>
    `;
  }

  const p3Fuse = document.getElementById('p3FuselageTableBody');
  if (p3Fuse) {
    const f = res.geometry?.fuselage || {};
    p3Fuse.innerHTML = `
      <tr><td>Długość całkowita kadłuba</td><td><b>L_k</b></td><td class="num"><b>${(f.length ?? 0).toFixed(2)}</b></td><td>m</td><td>Zapewnia wymagane ramiona sił usterzeń l_H i l_V</td></tr>
      <tr><td>Maksymalna średnica / szerokość</td><td><b>D_k</b></td><td class="num"><b>${(f.diameter ?? 0).toFixed(2)}</b></td><td>m</td><td>Uwarunkowana ergonomią kabiny (szerokość foteli pilotów)</td></tr>
      <tr><td>Smukłość kadłuba</td><td><b>&lambda;_k = L_k/D_k</b></td><td class="num"><b>${(f.fineness ?? 0).toFixed(2)}</b></td><td>-</td><td>Optymalna aerodynamicznie &lambda;_k &asymp; 6.0&ndash;9.5 (niski opór tarcia)</td></tr>
    `;
  }

  const p3Tails = document.getElementById('p3TailsTableBody');
  if (p3Tails) {
    const h = res.geometry?.horizontal_tail || {};
    const v = res.geometry?.vertical_tail || {};
    p3Tails.innerHTML = `
      <tr><td><b>Usterzenie poziome (UP)</b> &bull; Powierzchnia</td><td class="num"><b>${(h.S_h ?? 0).toFixed(2)}</b></td><td>m²</td><td>Typowo 18&ndash;25% powierzchni skrzydła S</td></tr>
      <tr><td><b>Usterzenie poziome (UP)</b> &bull; Rozpiętość b_H</td><td class="num"><b>${(h.b_h ?? 0).toFixed(2)}</b></td><td>m</td><td>Wydłużenie &Lambda;_H = ${(h.ar_h ?? 0).toFixed(1)}</td></tr>
      <tr><td><b>Usterzenie poziome (UP)</b> &bull; Ramię siły l_H</td><td class="num"><b>${(h.l_h ?? 0).toFixed(2)}</b></td><td>m</td><td>Odległość 0.25 ŚDA skrzydła do 0.25 ŚDA usterzenia</td></tr>
      <tr><td><b>Usterzenie poziome (UP)</b> &bull; Współczynnik V_H</td><td class="num"><b>${(h.vh_coeff ?? 0).toFixed(3)}</b></td><td>-</td><td>Wymóg zalecany: V_H &ge; 0.50 (dobra stateczność podłużna)</td></tr>
      <tr style="border-top:2px solid #cbd5e1;"><td><b>Usterzenie pionowe (UV)</b> &bull; Powierzchnia</td><td class="num"><b>${(v.S_v ?? 0).toFixed(2)}</b></td><td>m²</td><td>Typowo 10&ndash;16% powierzchni skrzydła S</td></tr>
      <tr><td><b>Usterzenie pionowe (UV)</b> &bull; Wysokość h_V</td><td class="num"><b>${(v.h_v ?? 0).toFixed(2)}</b></td><td>m</td><td>Wydłużenie &Lambda;_V = ${(v.ar_v ?? 0).toFixed(1)}</td></tr>
      <tr><td><b>Usterzenie pionowe (UV)</b> &bull; Ramię siły l_V</td><td class="num"><b>${(v.l_v ?? 0).toFixed(2)}</b></td><td>m</td><td>Odległość 0.25 ŚDA skrzydła do 0.25 ŚDA statecznika pionowego</td></tr>
      <tr><td><b>Usterzenie pionowe (UV)</b> &bull; Współczynnik V_V</td><td class="num"><b>${(v.vv_coeff ?? 0).toFixed(3)}</b></td><td>-</td><td>Wymóg zalecany: V_V &ge; 0.035 (stateczność kierunkowa)</td></tr>
    `;
  }

  const p3Gear = document.getElementById('p3GearTableBody');
  if (p3Gear) {
    const g = res.geometry?.gear || {};
    p3Gear.innerHTML = `
      <tr><td>Rozstaw kół podwozia głównego</td><td><b>B_p</b></td><td class="num"><b>${(g.track ?? 0).toFixed(2)}</b></td><td>m</td><td>Zapewnia stabilność przy lądowaniu (kąt wywrotu &gt; 35&deg;)</td></tr>
      <tr><td>Baza podwozia trójpodporowego</td><td><b>L_p</b></td><td class="num"><b>${(g.wheelbase ?? 0).toFixed(2)}</b></td><td>m</td><td>Dystans między osią przednią a główną (przeciwdziała kapotażowi)</td></tr>
      <tr><td>Wysokość goleni podwozia</td><td><b>H_p</b></td><td class="num"><b>${(g.height ?? 0.85).toFixed(2)}</b></td><td>m</td><td>Bezpieczny prześwit śmigła nad ziemią &ge; 230 mm wg CS-23</td></tr>
    `;
  }

  const p3Schrenk = document.getElementById('p3SchrenkTableBody');
  if (p3Schrenk && res.geometry?.schrenk) {
    const sList = Array.isArray(res.geometry.schrenk) ? res.geometry.schrenk : [];
    const stallEta = res.geometry?.schrenk_Pinpoint?.stall_eta_span;
    if (sList.length > 0) {
      const c0 = (sList[0].c_schrenk || 1);
      let html = '';
      sList.forEach((item, i) => {
        const etaNum = item.eta_span !== undefined ? Number(item.eta_span) : (i / Math.max(1, sList.length - 1));
        const etaVal = etaNum.toFixed(2);
        const liftPct = c0 > 0 ? ((item.c_schrenk / c0) * 100).toFixed(1) : '0.0';
        const cz1Val = (item.cz1 !== undefined ? Number(item.cz1) : ((item.c_schrenk || 0) / Math.max(0.01, item.c_geom || 1))).toFixed(3);
        const isStall = stallEta !== undefined && Math.abs(etaNum - Number(stallEta)) < 0.005;
        html += `
          <tr style="${isStall ? 'background:#fef3c7; font-weight:700;' : ''}">
            <td><b>${etaVal}</b> (${(etaNum * 100).toFixed(0)}% b/2) ${isStall ? '<span class="badge badge-warning">Początek oderwania</span>' : ''}</td>
            <td class="num">${(item.y ?? 0).toFixed(3)}</td>
            <td class="num">${(item.c_geom ?? 0).toFixed(3)}</td>
            <td class="num">${(item.c_ellip ?? 0).toFixed(3)}</td>
            <td class="num"><b>${(item.c_schrenk ?? 0).toFixed(3)}</b></td>
            <td class="num"><b>${cz1Val}</b></td>
            <td class="num">${liftPct}%</td>
          </tr>
        `;
      });
      p3Schrenk.innerHTML = html;
    }
  }
}

// 6. Tabele Modułu P4
function populateP4Tables(res) {
  const p4Card = document.getElementById('p4FlapJustificationCard');
  if (p4Card && typeof DIDACTIC_DATABASE !== 'undefined') {
    const fd = res.params;
    const flap = DIDACTIC_DATABASE.flaps[fd.flap_type] || DIDACTIC_DATABASE.flaps.single_slotted;
    const aileron = (DIDACTIC_DATABASE.ailerons && DIDACTIC_DATABASE.ailerons[fd.aileron_type]) || null;
    const slat = DIDACTIC_DATABASE.slats[fd.slat_type] || DIDACTIC_DATABASE.slats.none;
    p4Card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
        <div>
          <div style="font-size:0.75rem; text-transform:uppercase; font-weight:800; color:#0d9488;">
            Uzasadnienie Wyboru Mechanizacji Krawędzi Spływu i Natarcia (${flap.reference})
          </div>
          <div style="font-size:1.05rem; font-weight:800; color:#0f172a;">
            ${flap.name} + ${aileron ? aileron.name : 'Lotki'} ${fd.slat_type !== 'none' ? '+ ' + slat.name : ''}
          </div>
        </div>
        <div style="display:flex; gap:0.35rem; flex-wrap:wrap;">
          <span class="badge badge-success">&Delta;Cz_klapy = +${flap.delta_cz_max.toFixed(2)}</span>
          ${aileron ? `<span class="badge badge-info">pb/(2V) ≈ ${aileron.typical_pb_2v}</span>` : ''}
          ${slat.delta_cz_max > 0 ? `<span class="badge badge-info">&Delta;Cz_slotu = +${slat.delta_cz_max.toFixed(2)}</span>` : ''}
          <span class="badge badge-warning">&Delta;Cx0_lnd = +${flap.delta_cx0_lnd.toFixed(3)}</span>
        </div>
      </div>
      <div class="pros-cons-grid" style="margin-bottom:0.5rem;">
        <div class="pros-box">
          <h5>👍 Zalety konstrukcyjno-aerodynamiczne:</h5>
          <ul>
            ${flap.pros.map(p => `<li><strong>[Klapa]</strong> ${p}</li>`).join('')}
            ${aileron ? aileron.pros.map(p => `<li><strong>[Lotka]</strong> ${p}</li>`).join('') : ''}
            ${fd.slat_type !== 'none' ? slat.pros.map(p => `<li><strong>[Slot]</strong> ${p}</li>`).join('') : ''}
          </ul>
        </div>
        <div class="cons-box">
          <h5>⚠️ Wady, ograniczenia i kompromisy:</h5>
          <ul>
            ${flap.cons.map(c => `<li><strong>[Klapa]</strong> ${c}</li>`).join('')}
            ${aileron ? aileron.cons.map(c => `<li><strong>[Lotka]</strong> ${c}</li>`).join('') : ''}
            ${fd.slat_type !== 'none' ? slat.cons.map(c => `<li><strong>[Slot]</strong> ${c}</li>`).join('') : ''}
          </ul>
        </div>
      </div>
      <div class="galinski-quote-box">
        <strong>📘 Opinia prof. C. Galińskiego (MEiL PW):</strong> „${flap.galinski_quote}”
        ${aileron ? `<br><strong>📘 Sterowanie poprzeczne (lotki):</strong> „${aileron.galinski_quote}”` : ''}
      </div>
    `;
  }

  const p4Opt = document.getElementById('p4AeroOptimaTableBody');
  if (p4Opt) {
    const a = res.aerodynamics || {};
    p4Opt.innerHTML = `
      <tr><td><b>Maksymalna doskonałość (K_max)</b></td><td class="num"><b>${(a.cz_opt ?? 0).toFixed(3)}</b></td><td class="num">${(a.cx_opt ?? 0).toFixed(4)}</td><td class="num"><b>${(a.k_max ?? 0).toFixed(2)}</b></td><td>Optymalny kąt szybowania i maksymalny zasięg samolotu śmigłowego</td></tr>
      <tr><td><b>Prędkość ekonomiczna (min. moc silnika)</b></td><td class="num"><b>${(a.cz_econ ?? 0).toFixed(3)}</b></td><td class="num">${(a.cx_econ ?? 0).toFixed(4)}</td><td class="num"><b>${(a.k_econ ?? 0).toFixed(2)}</b></td><td>Maksymalna długotrwałość lotu dla silnika tłokowego / turboprop</td></tr>
      <tr><td><b>Daleki zasięg jet (min. paliwo)</b></td><td class="num"><b>${(a.cz_jet_range ?? 0).toFixed(3)}</b></td><td class="num">${(a.cx_jet_range ?? 0).toFixed(4)}</td><td class="num"><b>${(a.k_jet_range ?? 0).toFixed(2)}</b></td><td>Maksymalny zasięg samolotu z napędem turboodrzutowym</td></tr>
      <tr><td><b>Konfiguracja czysta (Clean)</b> &bull; Cz_max</td><td class="num"><b>${(a.cz_max_clean ?? 0).toFixed(2)}</b></td><td class="num">${(a.cx0_clean ?? 0).toFixed(4)}</td><td class="num">&mdash;</td><td>Profil bazowy skrzydła bez wychylenia klap</td></tr>
      <tr><td><b>Konfiguracja startowa (Takeoff)</b> &bull; Cz_max</td><td class="num"><b>${(a.cz_max_to ?? 0).toFixed(2)}</b></td><td class="num">${(a.cx0_to ?? 0).toFixed(4)}</td><td class="num">&mdash;</td><td>Klapy wychylone o 10&ndash;15&deg; (wzrost Cz przy umiarkowanym oporze)</td></tr>
      <tr><td><b>Konfiguracja lądowania (Landing)</b> &bull; Cz_max</td><td class="num"><b>${(a.cz_max_lnd ?? 0).toFixed(2)}</b></td><td class="num">${(a.cx0_lnd ?? 0).toFixed(4)}</td><td class="num">&mdash;</td><td>Klapy wychylone w pełni o 35&ndash;45&deg; (hamowanie aerodynamiczne)</td></tr>
    `;
  }

  // Podpunkt 4.4: Zestawienie Danych Statystycznych (Tabele A, B, C wg Z. Paturskiego)
  const paHolistic = res.bipol_projects?.p4?.paturski_aero || res.paturski_ml?.p3_aircraft_aero || {};
  const abcHolistic = paHolistic.statistical_benchmarks_abc;
  const holSumEl = document.getElementById('holistic_paturski_abc_summary');
  if (holSumEl && abcHolistic?.summary && abcHolistic.summary.matched_a_lp == null) {
    const s = abcHolistic.summary;
    holSumEl.innerHTML = `
      <div><strong>${s.matched_c_archetype}.</strong> ${s.verdict_text}
        Obliczone w projekcie: <code>C_x,min = ${s.project_cx_min}</code>, <code>(C_x,szk)_min = ${s.project_cx_szk_min}</code>.</div>
    `;
  } else if (holSumEl && abcHolistic?.summary) {
    const s = abcHolistic.summary;
    holSumEl.innerHTML = `
      <div style="display:flex; flex-wrap:wrap; justify-content:space-between; gap:0.5rem; align-items:center;">
        <div>
          <strong>Klasyfikacja wg Tabeli A (Lp. ${s.matched_a_lp}):</strong> ${s.matched_a_desc} &bull;
          Przedział statystyczny: <code>C_x,min = ${s.matched_a_range}</code> &bull;
          <strong>Obliczone w projekcie: <code>C_x,min = ${s.project_cx_min}</code></strong>
        </div>
        <span class="badge ${s.in_statistical_range ? 'badge-success' : 'badge-info'}">
          ${s.in_statistical_range ? '✓ Zgodne z Tabelą A i B' : 'ℹ️ Poza typowym przedziałem'}
        </span>
      </div>
      <div style="margin-top:0.35rem; color:#475569;">
        <strong>Tabela B (Lp. ${s.matched_b_lp}):</strong> ${s.matched_b_desc} &mdash;
        referencyjne <code>(C_x,szk)_min = ${s.matched_b_cx_szk_min}</code> vs. obliczone z Tabeli 3.1: <strong><code>(C_x,szk)_min = ${s.project_cx_szk_min}</code></strong> &bull;
        <strong>Wzorzec Tabeli C:</strong> ${s.matched_c_archetype}.
      </div>
    `;
  }
  const holTabCEl = document.getElementById('holistic_table_c_tbody');
  if (holTabCEl && Array.isArray(abcHolistic?.tabela_c_rows)) {
    const colKey = abcHolistic.summary?.matched_c_col_key || '';
    holTabCEl.innerHTML = abcHolistic.tabela_c_rows.map(r => `
      <tr>
        <td>${r.lp}</td>
        <td><b>${r.component}</b></td>
        <td class="num" style="${colKey === 'biplane_fixed_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.biplane_fixed_pct !== null ? r.biplane_fixed_pct + ' %' : '&ndash;'}</td>
        <td class="num" style="${colKey === 'high_wing_braced_fixed_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.high_wing_braced_fixed_pct !== null ? r.high_wing_braced_fixed_pct + ' %' : '&ndash;'}</td>
        <td class="num" style="${colKey === 'low_wing_retractable_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.low_wing_retractable_pct !== null ? r.low_wing_retractable_pct + ' %' : '&ndash;'}</td>
        <td class="num"><code>${Number(r.project_delta_cx).toFixed(4)}</code></td>
        <td class="num" style="background:#f0fdf4; font-weight:800; color:#065f46;">${Number(r.project_share_pct).toFixed(1)} %</td>
      </tr>
    `).join('');
  }
}

// 7. Tabele Modułu P5
function populateP5Tables(res) {
  const p5Speeds = document.getElementById('p5SpeedsTableBody');
  if (p5Speeds) {
    const sp = res.performance?.speeds || {};
    const vMax = Number(sp.v_max_sl_kmh ?? sp.v_max_kmh ?? 0);
    const vCr = Number(sp.v_cruise_kmh ?? 0);
    const vLnd = Number(sp.vs_lnd_kmh ?? 0);
    const vClean = Number(sp.vs_clean_kmh ?? 0);
    const machCr = Number(sp.mach_cruise ?? (vCr / 1225));
    p5Speeds.innerHTML = `
      <tr><td>Prędkość przeciągnięcia z klapami do lądowania</td><td><b>V_s0</b></td><td class="num"><b>${vLnd.toFixed(1)}</b></td><td class="num">${(vLnd/3.6).toFixed(1)}</td><td class="num">&mdash;</td><td>Ograniczenie przepisowe lądowania (Vs0 &le; zadana)</td></tr>
      <tr><td>Prędkość przeciągnięcia w konfiguracji gładkiej</td><td><b>V_s1</b></td><td class="num"><b>${vClean.toFixed(1)}</b></td><td class="num">${(vClean/3.6).toFixed(1)}</td><td class="num">&mdash;</td><td>Baza do wyznaczenia prędkości oderwania i manewrowej</td></tr>
      <tr><td>Prędkość oderwania przy starcie (1.15 &bull; Vs_TO)</td><td><b>V_LOF</b></td><td class="num"><b>${(sp.v_lof_kmh ?? 0).toFixed(1)}</b></td><td class="num">${((sp.v_lof_kmh ?? 0)/3.6).toFixed(1)}</td><td class="num">&mdash;</td><td>Bezpieczny margines prędkości przy oderwaniu kół</td></tr>
      <tr><td>Prędkość podejścia do lądowania (1.3 &bull; Vs przy masie do lądowania)</td><td><b>V_app</b></td><td class="num"><b>${(sp.v_app_kmh ?? 0).toFixed(1)}</b></td><td class="num">${((sp.v_app_kmh ?? 0)/3.6).toFixed(1)}</td><td class="num">&mdash;</td><td>Podejście po ścieżce schodzenia (H = 15 m)</td></tr>
      <tr><td>Prędkość przelotowa obliczeniowa</td><td><b>V_cr</b></td><td class="num"><b>${vCr.toFixed(1)}</b></td><td class="num">${(vCr/3.6).toFixed(1)}</td><td class="num"><b>M ${machCr.toFixed(3)}</b></td><td>Standardowa prędkość marszowa w fazie przelotu</td></tr>
      <tr><td>Maksymalna prędkość lotu poziomego przy ziemi</td><td><b>V_max</b></td><td class="num"><b>${vMax.toFixed(1)}</b></td><td class="num">${(vMax/3.6).toFixed(1)}</td><td class="num"><b>M ${(vMax/1225).toFixed(3)}</b></td><td>Punkt zrównania mocy rozporządzalnej i niezbędnej (w_y = 0)</td></tr>
    `;
  }

  const p5Climb = document.getElementById('p5KpiClimb');
  if (p5Climb) p5Climb.textContent = (res.performance?.climb?.wy_max_ms ?? 0).toFixed(2) + ' m/s';
  const p5Vwy = document.getElementById('p5KpiVwy');
  if (p5Vwy) p5Vwy.textContent = (res.performance?.climb?.v_wy_max_kmh ?? 0).toFixed(1) + ' km/h';

  const p5Ceil = document.getElementById('p5CeilingTableBody');
  if (p5Ceil) {
    const c = res.performance?.ceiling || {};
    const hServ = Number(c.service_ceiling_m ?? 5000);
    const hAbs = Number(c.absolute_ceiling_m);
    p5Ceil.innerHTML = `
      <tr><td><b>Pułap praktyczny</b> (Service Ceiling)</td><td class="num"><b>${hServ.toFixed(0)}</b></td><td class="num">${(hServ / 0.3048).toFixed(0)}</td><td>w_y = 0.5 m/s (100 ft/min)</td><td>Maksymalna wysokość użytkowa dla regularnych przelotów</td></tr>
      <tr><td><b>Pułap teoretyczny</b> (Absolute Ceiling)</td><td class="num"><b>${hAbs.toFixed(0)}</b></td><td class="num">${(hAbs / 0.3048).toFixed(0)}</td><td>w_y = 0.0 m/s (brak nadmiaru mocy)</td><td>Wysokość graniczna – brak możliwości dalszego wznoszenia</td></tr>
    `;
  }

  const p5Tolnd = document.getElementById('p5TakeoffLandingTableBody');
  if (p5Tolnd) {
    const to = res.performance?.takeoff || {};
    const lnd = res.performance?.landing || {};
    const runwayNumber=v=>v==null?'nieosiągalny':Number(v).toFixed(1);
    p5Tolnd.innerHTML = res.params.operating_surface==='water'
      ? `<tr><td colspan="4">${escapeHtml(to.note||'Operacji na wodzie nie wyznaczono.')}</td></tr>` : `
      <tr><td><b>1. Rozbieg samolotu</b> (Ground Roll S_g)</td><td class="num"><b>${runwayNumber(to.ground_roll_m)}</b></td><td>0 &rarr; V_LOF (efekt ziemi McCormicka)</td><td>Fiszdon / Raymer &bull; tarcie toczne i opór w efekcie ziemi</td></tr>
      <tr><td><b>2. Odcinek przejściowy i wznoszenie</b> (S_tr + S_climb)</td><td class="num"><b>${(to.air_distance_m ?? ((to.distance_to_15m ?? 0) - (to.ground_roll_m ?? 0))).toFixed(1)}</b></td><td>V_LOF &rarr; V₂ (kąt &gamma; = ${(to.climb_angle_deg ?? 0).toFixed(1)}&deg;)</td><td>Łuk wyrównania R_tr (${(to.transition_m ?? 0).toFixed(1)} m) + wznoszenie (${(to.climb_to_15m_m ?? 0).toFixed(1)} m)</td></tr>
      <tr style="background:#f8fafc;"><td><b>Całkowita droga startu nad H = 15 m</b></td><td class="num"><b>${runwayNumber(to.distance_to_15m)}</b></td><td>Wysokość ekranu H = 15 m (50 ft)</td><td>Wymóg certyfikacyjny CS-23.53</td></tr>
      <tr><td><b>3. Zniżanie z H = 15 m i wyrównanie</b> (S_air,lnd)</td><td class="num"><b>${(lnd.air_approach_m ?? 0).toFixed(1)}</b></td><td>V_app = 1.3 V_s0 &rarr; V_TD = 1.15 V_s0</td><td>Ścieżka podejścia i wytrzymanie nad pasem</td></tr>
      <tr><td><b>4. Dobieg na ziemi</b> (1.5s swobodny + hamowanie)</td><td class="num"><b>${(lnd.ground_roll_m ?? 0).toFixed(1)}</b></td><td>V_TD &rarr; 0 (${(lnd.free_roll_m ?? 0).toFixed(1)} m + ${(lnd.braking_roll_m ?? 0).toFixed(1)} m)</td><td>Hamowanie aerodynamiczne i kołowe (&mu;_ham = 0.40)</td></tr>
      <tr style="background:#f8fafc;"><td><b>Całkowita droga lądowania znad H = 15 m</b></td><td class="num"><b>${(lnd.distance_from_15m ?? 0).toFixed(1)}</b></td><td>Wysokość ekranu H = 15 m (50 ft)</td><td>Wymóg certyfikacyjny CS-23.73</td></tr>
    `;
  }

  const p5Man = document.getElementById('p5ManeuverTableBody');
  if (p5Man) {
    const t = res.performance?.turn || {};
    const nSus = Number(t.n_sustained ?? 0);
    const bankDeg = (t.bank_angle_deg !== undefined) ? Number(t.bank_angle_deg) : (Math.acos(1.0 / Math.max(1.01, nSus)) * 180 / Math.PI);
    const rMin = t.r_min_m;
    p5Man.innerHTML = `
      <tr><td>${t.mode === 'gliding' ? 'Kinematyka krążenia szybowego' : 'Maksymalne przeciążenie w zakręcie ustalonym'}</td><td><b>n_ust</b></td><td class="num"><b>${nSus.toFixed(2)}</b></td><td>-</td><td>${escapeHtml(t.note || '')}</td></tr>
      <tr><td>Kąt przechylenia</td><td><b>&phi;</b></td><td class="num"><b>${t.mode === 'unavailable' ? '—' : bankDeg.toFixed(1)}</b></td><td>&deg;</td><td>cos(&phi;) = 1/n, tylko dla wykonalnego zakrętu</td></tr>
      <tr><td>Promień dla badanego warunku</td><td><b>R</b></td><td class="num"><b>${Number.isFinite(rMin) ? rMin.toFixed(1) : '—'}</b></td><td>m</td><td>Prędkość ${t.v_turn_kmh} km/h; nie jest minimum po wszystkich prędkościach</td></tr>
    `;
  }
}

// 8. Tabele Modułu P6
function populateP6Tables(res) {
  const p6Env = document.getElementById('p6EnvelopeTableBody');
  if (p6Env) {
    const env = res.envelope || {};
    const nMax = Number(env.limits?.n_max ?? 3.8);
    const nMin = Number(env.limits?.n_min ?? -1.5);
    const vA = Number(env.speeds?.v_a_kmh ?? 0);
    const vC = env.speeds?.v_c_kmh;  // CS-22 nie definiuje VC
    const vD = Number(env.speeds?.v_d_kmh ?? 0);
    const nVd = Number(env.limits?.n_at_vd_pos ?? nMax);
    const gustText = (env.gust_factors?.gusts || []).map(g => `±${Number(g.u_ms).toFixed(2)} m/s przy ${g.speed}`).join(', ');
    p6Env.innerHTML = `
      <tr><td>Maksymalne przeciążenie dodatnie</td><td><b>n_pos,max</b></td><td class="num">&mdash;</td><td class="num"><b>+${nMax.toFixed(2)}</b></td><td>Współczynnik obciążenia manewrowego wg przepisów CS</td></tr>
      <tr><td>Maksymalne przeciążenie ujemne</td><td><b>n_neg,max</b></td><td class="num">&mdash;</td><td class="num"><b>${nMin.toFixed(2)}</b></td><td>Dopuszczalne przeciążenie w locie odwróconym / nurkowaniu</td></tr>
      <tr><td>Prędkość manewrowa</td><td><b>V_A</b></td><td class="num"><b>${vA.toFixed(1)}</b></td><td class="num">+${nMax.toFixed(2)}</td><td>Pełne wychylenie sterów nie przekroczy dopuszczalnego n</td></tr>
      ${vC == null ? '' : `<tr><td>Obliczeniowa prędkość przelotowa</td><td><b>V_C</b></td><td class="num"><b>${Number(vC).toFixed(1)}</b></td><td class="num">+${nMax.toFixed(2)}</td><td>Bazowa prędkość do analizy podmuchów pionowych</td></tr>`}
      <tr><td>Obliczeniowa prędkość nurkowania</td><td><b>V_D</b></td><td class="num"><b>${vD.toFixed(1)}</b></td><td class="num">+${nVd.toFixed(2)}</td><td>${escapeHtml(env.limits?.speed_rule || '')}</td></tr>
      <tr><td>Linie podmuchów</td><td><b>U_de</b></td><td class="num" colspan="2">${escapeHtml(gustText)}</td><td>${escapeHtml(env.gust_factors?.gust_basis || '')}</td></tr>
    `;
  }

  const p6Load = document.getElementById('p6LoadingStatesTableBody');
  if (p6Load && res.balance?.loading_states) {
    p6Load.innerHTML = res.balance.loading_states.map(s => {
      const xcgM = Number(s.xcg_m ?? s.x_cg_m ?? 0);
      const xcgPct = Number(s.xcg_mac_pct ?? s.x_cg_pct_mac ?? 0);
      const mass = Number(s.mass_kg ?? 0);
      const ground = s.in_flight === false;
      const ok = s.cg_criterion_passed === true && s.minimum_margin_passed === true;
      const status = ground ? 'Stan naziemny' : (ok ? '✓ Kryteria P3 spełnione' : '⚠️ Kryteria P3 niespełnione');
      return `
        <tr>
          <td><b>${escapeHtml(s.name)}</b></td>
          <td class="num"><b>${mass.toFixed(1)}</b></td>
          <td class="num">${xcgM.toFixed(3)}</td>
          <td class="num"><b>${xcgPct.toFixed(1)}%</b></td>
          <td><span class="badge ${ground ? '' : (ok ? 'badge-success' : 'badge-danger')}">${status}</span></td>
        </tr>
      `;
    }).join('');
  }

  const p6Stab = document.getElementById('p6StabilityTableBody');
  if (p6Stab) {
    const b = res.balance || {};
    const smAft = Number(b.stability?.static_margin_aft_pct ?? 10.0);
    const passed = smAft >= 5.0;
    const xLemac = Number(b.x_lemac_m ?? 0);
    const xNm = Number(b.neutral_point?.x_n_m ?? 0);
    const xNPct = Number(b.neutral_point?.x_n_mac_pct ?? 0);
    const cgFwd = Number(b.cg_range?.forward_pct ?? 0);
    const cgAft = Number(b.cg_range?.aft_pct ?? 0);
    const cgTrav = Number(b.cg_range?.delta_pct ?? 0);
    p6Stab.innerHTML = `
      <tr><td>Współrzędna noska ŚDA od dziobu kadłuba</td><td class="num"><b>${xLemac.toFixed(3)}</b></td><td>m</td><td>Początek bazy odniesienia (0% ŚDA)</td><td>Punkt bazowy</td></tr>
      <tr><td>Położenie punktu neutralnego płatowca ze statecznikiem (x_N)</td><td class="num"><b>${xNm.toFixed(3)}</b> (${xNPct.toFixed(1)}% ŚDA)</td><td>m (% ŚDA)</td><td>Musi leżeć za ŚM: x_N &gt; x_CG</td><td>Punkt obojętności momentowej</td></tr>
      <tr><td>Skrajne przednie położenie środka masy (x_CG,fwd)</td><td class="num"><b>${cgFwd.toFixed(1)}%</b></td><td>% ŚDA</td><td>Wymóg: sterowność przy lądowaniu</td><td>Maksymalny zapas stateczności</td></tr>
      <tr><td>Skrajne tylne położenie środka masy (x_CG,aft)</td><td class="num"><b>${cgAft.toFixed(1)}%</b></td><td>% ŚDA</td><td>Wymóg: stateczność statyczna Kn &ge; 5%</td><td>Minimalny zapas stateczności</td></tr>
      <tr><td>Całkowity zakres wędrówki środka masy (&Delta;x_CG)</td><td class="num"><b>${cgTrav.toFixed(1)}%</b></td><td>% ŚDA</td><td>Zakres obliczony dla rozpatrzonych stanów w locie</td><td>Wędrówka ŚM</td></tr>
      <tr style="background:#f8fafc; font-weight:bold;">
        <td>Zapas stateczności statycznej podłużnej (K_n,aft)</td>
        <td class="num"><b style="color:${passed ? '#16a34a' : '#dc2626'}; font-size:1.05rem;">${smAft.toFixed(2)}% ŚDA</b></td>
        <td>% ŚDA</td>
        <td>Przyjęte kryterium projektowe: <b>&ge; 5.0% ŚDA</b></td>
        <td><span class="badge ${passed ? 'badge-success' : 'badge-danger'}">${passed ? '✓ Zapas spełniony' : '✗ Za mały zapas stateczności'}</span></td>
      </tr>
    `;
  }
}

const WING_CONFIG_LABELS_PL = {
  low: 'dolnopłat wolnonośny',
  high: 'górnopłat wolnonośny',
  braced_high: 'górnopłat zastrzałowy',
  mid: 'średniopłat wolnonośny'
};
const FLAP_TYPE_LABELS_PL = {
  plain: 'klapa zwykła',
  split: 'klapa krokodylowa',
  single_slotted: 'klapa szczelinowa',
  fowler: 'klapa Fowlera',
  junkers: 'klapa zewnętrzna Junkersa',
  flaperon: 'klapolotka'
};
const SLAT_TYPE_LABELS_PL = {
  none: 'gładkie natarcie (brak slotu)',
  fixed_slot: 'stały slot',
  slats_auto: 'automatyczny slot ruchomy',
  krueger: 'klapa Kruegera'
};
const AIRCRAFT_CLASS_LABELS_PL = {
  piston_ga: 'Samolot tłokowy GA',
  motoglider: 'Motoszybowiec (TMG)',
  glider: 'Szybowiec',
  turboprop_regional: 'Samolot turbośmigłowy',
  jet_business: 'Odrzutowiec dyspozycyjny',
  jet_transport: 'Samolot komunikacyjny',
  uav: 'Bezzałogowy statek powietrzny (UAV)'
};

function getComplianceFixParam(check) {
  const param = String(check?.parameter || '').toLowerCase();
  // Zasięg i lot poziomy przy wymaganej prędkości poprawia bilans uściślony, nie obniżanie wymagań.
  if (param.includes('zasięg') || param.includes('lot poziomy')) return 'refine';
  if (param.includes('szybowc') || param.includes('prędkość maksymalna') || param.includes('moc silnika')) return 'engine_power_kw';
  if (param.includes('przeciągnięcia') || param.includes('vs0')) return 'v_stall_kmh';
  if (param.includes('wznoszenia') || param.includes('wy_max')) return 'climb_rate_ms';
  if (param.includes('dużej prędkości')) return 'cruise_speed_kmh';
  if (param.includes('długość startu')) return 'takeoff_distance_m';
  if (param.includes('długość lądowania')) return 'landing_distance_m';
  if (param.includes('stateczności') || param.includes('śc w locie')) return 'wing_config';
  if (param.includes('pasażer') || param.includes('miejsc') || param.includes('osób')) return 'n_pax';
  if (param.includes('rozpiętość') || param.includes('m/b²')) return 'aspect_ratio';
  if (param.includes('mtom') || param.includes('mas')) return 'category';
  return 'aircraft_type';
}
window.getComplianceFixParam = getComplianceFixParam;

function complianceFixButton(check) {
  if (check?.passed) return '';
  const param = getComplianceFixParam(check);
  if (param === 'refine') {
    return '<button type="button" class="compliance-fix-btn" data-studio-target="tab-coursework" data-reveal="courseworkIterate"'
      + ' title="Czysta merytoryka: bilans misji bierze biegunową z P4 i doskonałość przy zadanej prędkości TAS i wysokości.">'
      + 'Bilans uściślony P2←P4 →</button>';
  }
  return param ? `<button type="button" class="compliance-fix-btn" data-focus-param="${escapeHtml(param)}">Popraw →</button>` : '';
}
window.complianceFixButton = complianceFixButton;

// Asystent Dydaktyczny wykrywający błędy koncepcyjne w projekcie studenta
function updateDidacticAdvisor(res) {
  const advEl = document.getElementById('didacticAdvisorWarnings');
  if (!advEl) return;

  const p = collectFormData();
  const warnings = [];
  const wsVal = res.sizing?.design_point?.ws || res.sizing?.design_point?.ws_N_m2 || 0;

  if (p.wing_config === 'mid' && (p.n_pax >= 2 || p.m_cargo >= 150)) {
    warnings.push({
      type: 'warning',
      title: '⚠️ Uwaga Konstrukcyjna (Rozdz. 14 prof. Galińskiego): Średniopłat w samolocie pasażerskim/transportowym!',
      text: 'Wybrałeś układ średniopłata przy znacznym ładunku płatnym. Dźwigary łączące skrzydła przejdą przez sam środek kabiny (w środku ciężkości), uniemożliwiając rozmieszczenie pasażerów lub ładunku! Rozważ dolnopłat lub górnopłat.'
    });
  }

  if (p.wing_config === 'braced_high' && p.cruise_speed_kmh > 250) {
    warnings.push({
      type: 'warning',
      title: '⚠️ Nieoptymalna aerodynamika: Górnopłat zastrzałowy przy dużej prędkości przelotowej!',
      text: `Przy prędkości Vcr = ${p.cruise_speed_kmh} km/h opór szkodliwy zastrzałów (wzrost z V²) pochłania ogromną moc silnika. Powyżej 240 km/h zaleca się płat wolnonośny.`
    });
  }

  if ((p.flap_type === 'plain' || p.flap_type === 'split') && wsVal > 1400) {
    warnings.push({
      type: 'danger',
      title: '🛑 Zbyt słaba mechanizacja płata dla dużego obciążenia powierzchni W/S!',
      text: `Obciążenie powierzchni wynosi ${wsVal.toFixed(0)} N/m². Klapa zwykła lub krokodylowa daje zbyt mały Cz_max, co wymusza dużą powierzchnię skrzydła. Wybierz klapę szczelinową lub Fowlera!`
    });
  }

  if (p.slat_type === 'fixed_slot' && p.cruise_speed_kmh > 210) {
    warnings.push({
      type: 'warning',
      title: '⚠️ Stały slot przy wysokiej prędkości przelotowej!',
      text: 'Stałe przedskrzydło (Fixed Slat) generuje duży opór w locie poziomym. Przy prędkościach > 200 km/h zastosuj slot ruchomy (automatyczny/szynowy) lub klapę Kruegera.'
    });
  }

  if (p.taper_ratio < 0.35) {
    warnings.push({
      type: 'danger',
      title: '🛑 Niebezpieczeństwo oderwania strugi na końcówkach płata (Mała zbieżność η < 0.35)!',
      text: 'Przy bardzo małej cięciwie końcowej lokalny współczynnik Cz na końcu płata osiąga maksimum wcześniej niż przy kadłubie, powodując nagłe zwalenie się samolotu na skrzydło i utratę skuteczności lotek!'
    });
  }

  if (warnings.length === 0) {
    const wingLabel = WING_CONFIG_LABELS_PL[p.wing_config] || p.wing_config;
    const flapLabel = FLAP_TYPE_LABELS_PL[p.flap_type] || p.flap_type;
    advEl.innerHTML = `
      <div style="background:#f0fdf4; border-left:4px solid #16a34a; padding:0.75rem; border-radius:4px; color:#14532d; font-size:0.85rem;">
        <strong>✅ Konfiguracja poprawna dydaktycznie:</strong> Dobór układu nośnego (<b>${escapeHtml(wingLabel)}</b>), mechanizacji spływu (<b>${escapeHtml(flapLabel)}</b>), zbieżności (<code>η = ${p.taper_ratio}</code>) oraz prędkości jest spójny z wytycznymi konstrukcyjnymi MEiL PW.
      </div>
    `;
  } else {
    advEl.innerHTML = warnings.map(w => `
      <div style="background:${w.type === 'danger' ? '#fef2f2' : '#fffbeb'}; border-left:4px solid ${w.type === 'danger' ? '#dc2626' : '#d97706'}; padding:0.7rem; border-radius:4px; margin-bottom:0.5rem; font-size:0.82rem; color:#1e293b;">
        <div style="font-weight:800; margin-bottom:2px;">${w.title}</div>
        <div>${w.text}</div>
      </div>
    `).join('');
  }
}

// Pobranie i wyświetlenie listy pobranych plików wydziałowych (Danilecki, BIPOL, ZPK CAD1, Mechanika Lotu)
async function loadScrapedFiles() {
  const containerDanilecki = document.getElementById('scrapedDanileckiFiles');
  const containerBipol = document.getElementById('scrapedBipolFiles');
  const containerZpk = document.getElementById('scrapedZpkFiles');
  const containerMl = document.getElementById('scrapedMlFiles');
  const containerSources = document.getElementById('facultySources');
  const badgeTotal = document.getElementById('facultyFilesTotalBadge');
  if (!containerBipol || !containerMl) return;

  try {
    const resp = await fetch('/api/scraped-files');
    const data = await resp.json();

    const row = 'display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:0.5rem 0.75rem; border-bottom:1px solid #e2e8f0;';
    const renderList = (items, icon) => (items || []).length ? items.map(f => `
      <div style="${row}">
        <div>
          <strong>${icon} ${escapeHtml(f.name)}</strong> <small style="color:#64748b;">(${(f.size/1024).toFixed(0)} KB)</small>
        </div>
        <a href="${escapeHtml(f.path)}" target="_blank" class="btn btn-outline" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Podgląd</a>
      </div>
    `).join('') : `<div style="${row} color:#64748b; font-size:0.82rem;">Brak kopii lokalnej.</div>`;

    if (containerSources) containerSources.innerHTML = (data.sources || []).map(s => `
      <div style="${row}">
        <div><strong>🔗 ${escapeHtml(s.name)}</strong><br><small style="color:#64748b;">${escapeHtml(s.note)}</small></div>
        <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="btn btn-outline" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Otwórz źródło</a>
      </div>
    `).join('');
    if (containerDanilecki) containerDanilecki.innerHTML = renderList(data.danilecki, '📖');
    containerBipol.innerHTML = renderList(data.bipol, '📄');
    if (containerZpk) containerZpk.innerHTML = renderList(data.zpk_cad, '📐');
    containerMl.innerHTML = renderList(data.mechanika_lotu, '📘');

    if (badgeTotal) {
      badgeTotal.textContent = data.total_count ? `${data.total_count} kopii lokalnych PDF` : 'Brak kopii lokalnych';
    }

  } catch (err) {
    console.error('Błąd wczytywania plików:', err);
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll('.bipol-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-target');
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.classList.add('active');

      renderTabVisuals(targetId);
      document.dispatchEvent(new CustomEvent('bipol:tab'));
    });
  });

  // Responsywne przerysowanie wykresów po zmianie rozmiaru okna przeglądarki
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const activeTab = document.querySelector('.tab-content.active');
      if (activeTab && currentResults) {
        renderTabVisuals(activeTab.id);
      }
      if (currentPortalMode === 'projects' && currentResults) renderSemesterProjectCharts(currentSemesterProject, currentResults);
    }, 150);
  });
}

/* ========================================================
   WIZARD / KONFIGURATOR PROJEKTU KROK PO KROKU
   ======================================================== */
let currentWizardStep = 1;

// ==========================================
// BIPOL STUDIO - SYSTEM ZARZĄDZANIA PROJEKTAMI (PROJECT SYSTEM)
// ==========================================
const STORAGE_PROJECTS_KEY = 'bipol_projects_v2';
const STORAGE_ACTIVE_PROJ_KEY = 'bipol_active_project_id';
const SESSION_INITIALIZED_KEY = 'bipol_session_initialized';

let wizardProjectMode = 'create'; // 'create' lub 'edit'

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getProjectsList() {
  const list = projectStore.read(STORAGE_PROJECTS_KEY, []);
  return Array.isArray(list) ? list.filter(p => p && p.id && p.params && typeof p.params === 'object') : [];
}

function saveProjectsList(list) {
  return projectStore.write(STORAGE_PROJECTS_KEY, list);
}

function getActiveProjectId() {
  return activeProjectMemory || safeLocalItem(STORAGE_ACTIVE_PROJ_KEY);
}

function setActiveProjectId(id) {
  activeProjectMemory = id;
  try {
    if (!browserStorage) throw new Error('Brak pamięci przeglądarki');
    browserStorage.setItem(STORAGE_ACTIVE_PROJ_KEY, id);
  } catch (_) { projectStore.write('bipol_active_project_fallback', id); }
}

function getActiveProject() {
  const list = getProjectsList();
  if (list.length === 0) return null;
  const activeId = getActiveProjectId();
  let found = list.find(p => p.id === activeId);
  if (!found) {
    found = list[0];
    setActiveProjectId(found.id);
  }
  return found;
}

function saveProject(project) {
  const list = getProjectsList();
  const idx = list.findIndex(p => p.id === project.id);
  project.updatedAt = new Date().toISOString();
  if (idx >= 0) {
    list[idx] = project;
  } else {
    list.unshift(project);
  }
  saveProjectsList(list);
  renderProjectSwitcher();
  renderProjectManagerModal();
}

function loadProjectIntoForm(project) {
  if (!project || !project.params) return;
  const params = { runway_surface: 'paved', ...project.params };
  params.m_pax = (params.m_pax || 0) + (params.m_bag || 0);
  params.m_bag = 0;
  formBaseParams = { ...params };

  for (const [key, val] of Object.entries(params)) {
    const el = document.getElementById(key);
    if (el) {
      el.value = val;
    }
  }

  window.BipolDesignBasis?.restore(params);

  const pnd = document.getElementById('projectNameDisplay');
  if (pnd) pnd.textContent = project.name;

  syncAircraftClassAndEASAUI(false);
  syncFormPropulsionUI(false);
  renderWingConfigDidacticCard();
  renderFlapDidacticCard(false);
  updateAccordionPills();
  restoreProjectChecklist(project);

  const reportBtn = document.getElementById('openReportBtn');
  if (reportBtn) {
    const sName = params.student_name || document.getElementById('student_name')?.value || '';
    const aNo = params.album_no || document.getElementById('album_no')?.value || '';
    const gNo = params.group_no || document.getElementById('group_no')?.value || '';
    const sup = params.supervisor || document.getElementById('supervisor')?.value || '';
    const subDate = params.submission_date || document.getElementById('submission_date')?.value || '';
    const paramsJson = encodeURIComponent(JSON.stringify(params));
    reportBtn.href = `/report?params_json=${paramsJson}&student=${encodeURIComponent(sName)}&album=${encodeURIComponent(aNo)}&group=${encodeURIComponent(gNo)}&supervisor=${encodeURIComponent(sup)}&date=${encodeURIComponent(subDate)}`;
  }
  document.dispatchEvent(new CustomEvent('bipol:project'));
}

function renderProjectSwitcher() {
  const sel = document.getElementById('projectSwitcherSelect');
  const countBadge = document.getElementById('projectCountBadge');
  const navCount = document.getElementById('navProjectCount');
  const list = getProjectsList();
  const activeId = getActiveProjectId();

  if (countBadge) countBadge.textContent = list.length;
  if (navCount) navCount.textContent = list.length;

  if (!sel) return;
  sel.innerHTML = '';
  list.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.id === activeId ? '✈️ ' : '📁 '} ${p.name}`;
    if (p.id === activeId) opt.selected = true;
    sel.appendChild(opt);
  });
}

function switchActiveProject(projectId) {
  const list = getProjectsList();
  const proj = list.find(p => p.id === projectId);
  if (!proj) return;

  setActiveProjectId(proj.id);
  loadProjectIntoForm(proj);
  renderProjectSwitcher();
  performCalculation();
  flashSaveStatus(`Załadowano: ${proj.name}`);
}

function flashSaveStatus(msg) {
  const statusEl = document.getElementById('projectAutoSaveStatus');
  if (!statusEl) return;
  statusEl.innerHTML = projectStore.persistent
    ? `<span class="icon">💾</span> ${escapeHtml(msg)}`
    : 'Tylko pamięć karty — pobierz kopię JSON';
  statusEl.style.opacity = '1';
  statusEl.style.color = projectStore.persistent ? '#10b981' : '#a2691c';
}

function autoSaveActiveProject(res) {
  const active = getActiveProject();
  if (!active) return;
  active.params = res ? res.params : collectFormData();
  active.updatedAt = new Date().toISOString();
  if (res) {
    active.summary = {
      mtow: res.mass?.m0,
      wingspan: res.geometry?.wing?.b,
      wingArea: res.geometry?.wing?.S,
      vStall: res.performance?.speeds?.vs_lnd_kmh,
      wyMax: res.performance?.climb?.wy_max_ms
    };
  }
  const list = getProjectsList();
  const idx = list.findIndex(p => p.id === active.id);
  if (idx >= 0) list[idx] = active;
  saveProjectsList(list);
  renderProjectSwitcher();
  flashSaveStatus(`Zapisano automatycznie (${new Date().toLocaleTimeString('pl-PL', {hour:'2-digit', minute:'2-digit'})})`);
}

function duplicateActiveProject() {
  const active = getActiveProject();
  if (!active) return;
  duplicateProject(active.id);
}

function duplicateProject(projectId) {
  const list = getProjectsList();
  const src = list.find(p => p.id === projectId);
  if (!src) return;

  const newId = 'proj_' + Date.now();
  const cloned = {
    ...JSON.parse(JSON.stringify(src)),
    id: newId,
    name: `${src.name} (Kopia)`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };

  list.unshift(cloned);
  saveProjectsList(list);
  setActiveProjectId(newId);
  loadProjectIntoForm(cloned);
  renderProjectSwitcher();
  renderProjectManagerModal();
  performCalculation();
  flashSaveStatus(`Zduplikowano jako: ${cloned.name}`);
}

function deleteProject(projectId) {
  const list = getProjectsList();
  if (list.length <= 1) {
    alert('W pracowni musi pozostać co najmniej jeden projekt!');
    return;
  }
  const target = list.find(p => p.id === projectId);
  if (!target) return;

  if (!confirm(`Czy na pewno chcesz usunąć projekt:\n"${target.name}"?`)) {
    return;
  }

  const updatedList = list.filter(p => p.id !== projectId);
  saveProjectsList(updatedList);

  const activeId = getActiveProjectId();
  if (activeId === projectId) {
    const nextProj = updatedList[0];
    setActiveProjectId(nextProj.id);
    loadProjectIntoForm(nextProj);
    performCalculation();
  }

  renderProjectSwitcher();
  renderProjectManagerModal();
  flashSaveStatus('Usunięto projekt');
}

function promptRenameProject(projectId) {
  const list = getProjectsList();
  const proj = list.find(p => p.id === projectId);
  if (!proj) return;

  const newName = prompt('Podaj nową nazwę projektu:', proj.name);
  if (newName && newName.trim() && newName.trim() !== proj.name) {
    proj.name = newName.trim();
    saveProject(proj);
    const pnd = document.getElementById('projectNameDisplay');
    if (pnd && getActiveProjectId() === proj.id) pnd.textContent = proj.name;
    flashSaveStatus(`Zmieniono nazwę na: ${proj.name}`);
  }
}

function exportActiveProjectJSON() {
  const active = getActiveProject();
  if (active) exportProjectJSON(active.id);
}

function exportProjectJSON(projectId) {
  const list = getProjectsList();
  const proj = list.find(p => p.id === projectId);
  if (!proj) return;

  const exportObj = {
    bipol_version: '2.0',
    export_date: new Date().toISOString(),
    project: proj
  };

  const jsonStr = JSON.stringify(exportObj, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const safeName = proj.name.replace(/[^a-zA-Z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ_\-\s]/g, '').trim().replace(/\s+/g, '_');
  a.href = url;
  a.download = `${safeName || 'projekt_bipol'}.bipol.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function importProjectFromFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      let importedProj = null;

      if (data.project && data.project.name && data.project.params) {
        importedProj = data.project;
      } else if (data.params && data.name) {
        importedProj = data;
      } else {
        throw new Error('Plik nie zawiera poprawnej struktury projektu BIPOL.');
      }

      const newId = 'proj_imp_' + Date.now();
      const projToSave = {
        id: newId,
        name: importedProj.name.includes('(Import)') ? importedProj.name : `${importedProj.name} (Import)`,
        aircraft_type: importedProj.aircraft_type || 'piston_ga',
        category: importedProj.category || 'normal',
        createdAt: importedProj.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        params: importedProj.params,
        summary: importedProj.summary || {},
        editorial: importedProj.editorial || {}
      };

      const list = getProjectsList();
      list.unshift(projToSave);
      saveProjectsList(list);
      setActiveProjectId(newId);
      loadProjectIntoForm(projToSave);
      renderProjectSwitcher();
      renderProjectManagerModal();
      performCalculation();
      alert(`Pomyślnie zaimportowano projekt:\n"${projToSave.name}"!`);
    } catch (err) {
      alert('Błąd importu pliku JSON: ' + err.message);
    }
  };
  reader.readAsText(file);
}

function renderProjectManagerModal() {
  const grid = document.getElementById('projectCardsGrid');
  const countEl = document.getElementById('hubProjectsTotalCount');
  if (!grid) return;

  const list = getProjectsList();
  const activeId = getActiveProjectId();
  if (countEl) countEl.textContent = list.length;

  if (list.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:2rem; color:#64748b;">Brak projektów. Kliknij „Nowy Projekt”, aby uruchomić kreator!</div>`;
    return;
  }

  grid.innerHTML = list.map(p => {
    const isActive = p.id === activeId;
    const mtowStr = p.summary?.mtow ? `${p.summary.mtow.toFixed(0)} kg` : '---';
    const spanStr = p.summary?.wingspan ? `${p.summary.wingspan.toFixed(1)} m` : '---';
    const vStallStr = p.summary?.vStall ? `${p.summary.vStall.toFixed(0)} km/h` : '---';
    const wyStr = p.summary?.wyMax ? `${p.summary.wyMax.toFixed(1)} m/s` : '---';
    const updatedDate = p.updatedAt ? new Date(p.updatedAt).toLocaleString('pl-PL', {dateStyle:'short', timeStyle:'short'}) : '---';

    return `
      <div class="project-card ${isActive ? 'active' : ''}">
        <div>
          <div class="project-card-header">
            <div class="project-card-title">${escapeHtml(p.name)}</div>
            <span class="project-card-badge ${isActive ? 'current' : ''}">
              ${isActive ? '★ Aktywny' : (p.category || 'Projekt')}
            </span>
          </div>
          <div class="project-card-meta">
            <div><strong>Typ:</strong> ${escapeHtml(p.aircraft_type || 'piston_ga')}</div>
            <div><strong>Ostatnia zmiana:</strong> ${updatedDate}</div>
          </div>
          <div class="project-card-specs">
            <span class="spec-tag" title="Masa startowa MTOW">MTOW: ${mtowStr}</span>
            <span class="spec-tag" title="Rozpiętość skrzydła">b: ${spanStr}</span>
            <span class="spec-tag" title="Prędkość przeciągnięcia z klapami">Vs0: ${vStallStr}</span>
            <span class="spec-tag" title="Maksymalna prędkość wznoszenia">w_y,max: ${wyStr}</span>
          </div>
        </div>
        <div class="project-card-actions">
          ${!isActive ? `<button type="button" class="btn btn-primary btn-sm" onclick="switchActiveProject('${p.id}'); closeProjectManagerModal();" style="font-size:0.75rem; padding:0.25rem 0.6rem;">🚀 Otwórz</button>` : `<span class="badge badge-success" style="font-size:0.75rem; padding:0.3rem 0.5rem;">Aktualnie otwarty</span>`}
          <button type="button" class="btn btn-outline btn-sm" onclick="promptRenameProject('${p.id}')" style="font-size:0.75rem; padding:0.25rem 0.5rem;" title="Zmień nazwę projektu">✏️ Nazwa</button>
          <button type="button" class="btn btn-outline btn-sm" onclick="duplicateProject('${p.id}')" style="font-size:0.75rem; padding:0.25rem 0.5rem;" title="Zduplikuj ten projekt">📋 Kopia</button>
          <button type="button" class="btn btn-outline btn-sm" onclick="exportProjectJSON('${p.id}')" style="font-size:0.75rem; padding:0.25rem 0.5rem;" title="Pobierz plik .json">💾 JSON</button>
          <button type="button" class="btn btn-danger btn-sm" onclick="deleteProject('${p.id}')" style="font-size:0.75rem; padding:0.25rem 0.5rem;" title="Usuń projekt">🗑️</button>
        </div>
      </div>
    `;
  }).join('');
}

function openProjectManagerModal() {
  renderProjectManagerModal();
  const backdrop = document.getElementById('projectManagerModalBackdrop');
  if (backdrop) {
    backdrop.classList.add('active');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
}

function closeProjectManagerModal() {
  const backdrop = document.getElementById('projectManagerModalBackdrop');
  if (backdrop) {
    backdrop.classList.remove('active');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
}

function openSessionStarterModal() {
  const backdrop = document.getElementById('sessionStarterModalBackdrop');
  if (backdrop) {
    backdrop.classList.add('active');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
}

function closeSessionStarterModal() {
  const backdrop = document.getElementById('sessionStarterModalBackdrop');
  if (backdrop) {
    backdrop.classList.remove('active');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  try { sessionStorage.setItem(SESSION_INITIALIZED_KEY, 'true'); } catch (_) {}
}

function initProjectSystem() {
  let list = getProjectsList();

  // Usuń dawny przykładowy projekt wzorcowy (PZL-102B Kos) z listy projektów
  const sampleIds = ['proj_pzl_kos'];
  if (list.some(p => sampleIds.includes(p.id))) {
    list = list.filter(p => !sampleIds.includes(p.id));
    saveProjectsList(list);
    if (sampleIds.includes(getActiveProjectId())) localStorage.removeItem(STORAGE_ACTIVE_PROJ_KEY);
  }

  // Jeśli brak projektów (pierwsze uruchomienie), utwórz pusty projekt roboczy
  if (list.length === 0) {
    const initProj = {
      id: 'proj_' + Date.now(),
      name: 'Mój projekt samolotu',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      params: {},
      summary: {}
    };
    list = [initProj];
    saveProjectsList(list);
    setActiveProjectId(initProj.id);
  }

  // Wczytaj aktywny projekt do formularza
  const activeProj = getActiveProject();
  if (activeProj) {
    if (!activeProj.semesterChecklist) {
      try { activeProj.semesterChecklist = JSON.parse(localStorage.getItem(SEMESTER_CHECKLIST_KEY) || '{}'); }
      catch (_) { activeProj.semesterChecklist = {}; }
      saveProject(activeProj);
    }
    loadProjectIntoForm(activeProj);
  }
  renderProjectSwitcher();

  // Open the saved workspace directly; the wizard remains available under project options.
  closeSessionStarterModal();
  performCalculation();

  setupProjectEventListeners();
}

function setupProjectEventListeners() {
  const switcher = document.getElementById('projectSwitcherSelect');
  if (switcher) {
    switcher.addEventListener('change', (e) => {
      switchActiveProject(e.target.value);
    });
  }

  const btnNewProj = document.getElementById('btnNewProjectWizard');
  if (btnNewProj) {
    btnNewProj.addEventListener('click', () => openWizard('create'));
  }

  const btnOpenMgr = document.getElementById('btnOpenProjectManager');
  if (btnOpenMgr) {
    btnOpenMgr.addEventListener('click', openProjectManagerModal);
  }

  const btnOpenMgrNav = document.getElementById('btnOpenProjectManagerNav');
  if (btnOpenMgrNav) {
    btnOpenMgrNav.addEventListener('click', openProjectManagerModal);
  }

  const closeMgrBtn = document.getElementById('closeProjectManagerBtn');
  if (closeMgrBtn) {
    closeMgrBtn.addEventListener('click', closeProjectManagerModal);
  }

  const mgrBackdrop = document.getElementById('projectManagerModalBackdrop');
  if (mgrBackdrop) {
    mgrBackdrop.addEventListener('click', (e) => {
      if (e.target === mgrBackdrop) closeProjectManagerModal();
    });
  }

  const starterBackdrop = document.getElementById('sessionStarterModalBackdrop');
  if (starterBackdrop) {
    starterBackdrop.addEventListener('click', (e) => {
      if (e.target === starterBackdrop) closeSessionStarterModal();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (mgrBackdrop && mgrBackdrop.classList.contains('active')) closeProjectManagerModal();
      if (starterBackdrop && starterBackdrop.classList.contains('active')) closeSessionStarterModal();
    }
  });

  const btnDup = document.getElementById('btnDuplicateCurrentProject');
  if (btnDup) {
    btnDup.addEventListener('click', duplicateActiveProject);
  }

  const btnExport = document.getElementById('btnExportCurrentProject');
  if (btnExport) {
    btnExport.addEventListener('click', exportActiveProjectJSON);
  }

  const hubNew = document.getElementById('hubNewProjectBtn');
  if (hubNew) {
    hubNew.addEventListener('click', () => {
      closeProjectManagerModal();
      openWizard('create');
    });
  }

  const hubImport = document.getElementById('hubImportProjectBtn');
  const importInput = document.getElementById('projectImportFileInput');
  if (hubImport && importInput) {
    hubImport.addEventListener('click', () => importInput.click());
    importInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        importProjectFromFile(e.target.files[0]);
        e.target.value = '';
      }
    });
  }

  // Session Starter Dual-Portal & Project choices
  const starterHolisticBtn = document.getElementById('starterHolisticBtn');
  const starterHolisticCard = document.getElementById('starterHolisticCard');
  const handleStarterHolistic = (e) => {
    if (e) e.stopPropagation();
    closeSessionStarterModal();
    setPortalMode('holistic');
    performCalculation();
  };
  if (starterHolisticBtn) starterHolisticBtn.addEventListener('click', handleStarterHolistic);
  if (starterHolisticCard) starterHolisticCard.addEventListener('click', handleStarterHolistic);

  const starterProjectsBtn = document.getElementById('starterProjectsBtn');
  const starterProjectsCard = document.getElementById('starterProjectsCard');
  const handleStarterProjects = (e) => {
    if (e) e.stopPropagation();
    closeSessionStarterModal();
    setPortalMode('projects');
    performCalculation();
  };
  if (starterProjectsBtn) starterProjectsBtn.addEventListener('click', handleStarterProjects);
  if (starterProjectsCard) starterProjectsCard.addEventListener('click', handleStarterProjects);

  const starterNewBtn = document.getElementById('starterNewProjectBtn');
  const starterNewCard = document.getElementById('starterNewProjectCard');
  const handleStarterNew = (e) => {
    if (e) e.stopPropagation();
    closeSessionStarterModal();
    openWizard('create');
  };
  if (starterNewBtn) starterNewBtn.addEventListener('click', handleStarterNew);
  if (starterNewCard) starterNewCard.addEventListener('click', handleStarterNew);

  const starterExistBtn = document.getElementById('starterExistingProjectBtn');
  const starterExistCard = document.getElementById('starterExistingProjectCard');
  const handleStarterExist = (e) => {
    if (e) e.stopPropagation();
    closeSessionStarterModal();
    openProjectManagerModal();
  };
  if (starterExistBtn) starterExistBtn.addEventListener('click', handleStarterExist);
  if (starterExistCard) starterExistCard.addEventListener('click', handleStarterExist);
}

// Udostępnienie metod globalnie dla onclick w wygenerowanych kartach HTML
window.switchActiveProject = switchActiveProject;
window.closeProjectManagerModal = closeProjectManagerModal;
window.promptRenameProject = promptRenameProject;
window.duplicateProject = duplicateProject;
window.deleteProject = deleteProject;
window.exportProjectJSON = exportProjectJSON;

function syncWizardPropulsionUI(triggerAutoSfc = false) {
  const engEl = document.getElementById('wiz_engine_type');
  const locEl = document.getElementById('wiz_engine_location');
  const acEl = document.getElementById('wiz_aircraft_type');
  const sfcEl = document.getElementById('wiz_sfc');
  const propGroup = document.getElementById('wiz_group_prop_efficiency');
  const pane3Title = document.getElementById('wiz_pane3_title');
  const labelWizSfc = document.getElementById('label_wiz_sfc');

  const eng = engEl ? engEl.value : 'prop';
  const acType = acEl ? acEl.value : 'piston_ga';
  const isGlider = eng === 'none';
  window.BipolDesignBasis?.propulsion('wiz_');
  for (const [field, minimum, fallback] of [['takeoff_run_m', 50, 500], ['takeoff_distance_m', 0, 600], ['climb_rate_ms', 1.5, 4.1]]) {
    const input = document.getElementById('wiz_' + field);
    if (input) { input.min = isGlider ? '0' : String(minimum); if (isGlider) input.value = '0'; else if (minimum > 0 && Number(input.value) === 0) input.value = fallback; }
  }
  if (sfcEl) {
    sfcEl.readOnly = isGlider;
    sfcEl.closest('.input-group').style.display = isGlider ? 'none' : '';
  }
  if (isGlider) {
    if (sfcEl) { sfcEl.value = '0'; sfcEl.min = '0'; sfcEl.max = '0'; }
    const prop = document.getElementById('wiz_prop_efficiency');
    if (prop) prop.closest('.input-group').style.display = 'none';
    return;
  }
  const prop = document.getElementById('wiz_prop_efficiency');
  if (prop) prop.closest('.input-group').style.display = eng === 'jet' ? 'none' : '';


  if (pane3Title) {
    pane3Title.textContent = eng === 'jet'
      ? 'Krok 3: Zespół Napędowy Odrzutowy i Zużycie Paliwa TSFC (Projekt P2 / P4)'
      : 'Krok 3: Zespół Napędowy i Sprawność Propulsywna Śmigła (Projekt P2 / P4)';
  }

  if (propGroup) {
    propGroup.style.display = eng === 'jet' ? 'none' : '';
  }

  if (locEl) {
    const noseOpt = locEl.querySelector('option[value="nose"]');
    if (noseOpt) {
      noseOpt.disabled = (eng === 'jet');
      noseOpt.hidden = (eng === 'jet');
    }
    if (eng === 'jet' && locEl.value === 'nose') {
      locEl.value = (acType === 'jet_transport') ? 'wing' : 'rear';
    }
  }

  if (sfcEl) {
    const curVal = parseFloat(sfcEl.value);
    if (eng === 'jet') {
      if (labelWizSfc) {
        labelWizSfc.innerHTML = 'Jednostkowe zużycie paliwa TSFC c_j [1/h]:';
      }
      sfcEl.min = '0.25';
      sfcEl.max = '1.80';
      sfcEl.step = 'any';
      if (triggerAutoSfc || isNaN(curVal) || curVal > 4.0) {
        sfcEl.value = (acType === 'jet_transport') ? '0.58' : '0.62';
      }
    } else {
      if (labelWizSfc) {
        labelWizSfc.innerHTML = 'Jednostkowe zużycie paliwa SFC c_p [g/(kW&bull;h)]:';
      }
      sfcEl.min = '140';
      sfcEl.max = '500';
      sfcEl.step = 'any';
      if (triggerAutoSfc || isNaN(curVal) || curVal < 50.0) {
        if (!triggerAutoSfc && curVal >= 0.15 && curVal <= 1.5) {
          sfcEl.value = String(Math.round(curVal * 1000));
        } else {
          sfcEl.value = (acType === 'turboprop_regional') ? '280' : '265';
        }
      }
    }
  }
}

function initWizardSystem() {
  const openBtnNav = document.getElementById('launchWizardBtnNav');
  const openBtnSidebar = document.getElementById('launchWizardBtnSidebar');
  const closeBtn = document.getElementById('closeWizardBtn');
  const cancelBtn = document.getElementById('wizCancelBtn');
  const backdrop = document.getElementById('projectWizardBackdrop');
  const nextBtn = document.getElementById('wizNextBtn');
  const backBtn = document.getElementById('wizBackBtn');
  const finishBtn = document.getElementById('wizFinishBtn');
  const suggestBtn = document.getElementById('wizSuggestSpeedsBtn');

  if (openBtnNav) openBtnNav.addEventListener('click', () => openWizard('create'));
  if (openBtnSidebar) openBtnSidebar.addEventListener('click', () => openWizard('create'));
  if (closeBtn) closeBtn.addEventListener('click', closeWizard);
  if (cancelBtn) cancelBtn.addEventListener('click', closeWizard);

  if (backdrop) {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeWizard();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && backdrop && backdrop.classList.contains('active')) {
      closeWizard();
    }
  });

  // Przełączanie kroków przyciskami
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      try { validateNumericFields(document.getElementById(`wizardPane${currentWizardStep}`)); }
      catch (err) { showWizardError(err.message); return; }
      if (currentWizardStep < 5) goToWizardStep(currentWizardStep + 1);
    });
  }

  if (backBtn) {
    backBtn.addEventListener('click', () => {
      if (currentWizardStep > 1) goToWizardStep(currentWizardStep - 1);
    });
  }

  if (finishBtn) {
    finishBtn.addEventListener('click', commitWizardToForm);
  }

  // Zakładki kroków na pasku postępu (stepper)
  document.querySelectorAll('.wizard-step-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const step = parseInt(tab.getAttribute('data-step') || '1', 10);
      goToWizardStep(step);
    });
  });



  if (suggestBtn) {
    suggestBtn.addEventListener('click', () => suggestStepDefaults(2));
  }

  // Live change listeners dla rodzaju napędu i klasy statku w Kreatorze
  const wizEngSel = document.getElementById('wiz_engine_type');
  const wizAcSel = document.getElementById('wiz_aircraft_type');
  const wizCatSel = document.getElementById('wiz_category');
  if (wizEngSel) {
    wizEngSel.addEventListener('change', () => {
      syncEngineWithAircraft(true);
      syncWizardPropulsionUI(true);
    });
  }
  if (wizAcSel) {
    wizAcSel.addEventListener('change', () => {
      const ac = wizAcSel.value;
      if (wizEngSel) {
        if (ac === 'jet_business' || ac === 'jet_transport') {
          wizEngSel.value = 'jet';
          const wizLoc = document.getElementById('wiz_engine_location');
          if (wizLoc) wizLoc.value = (ac === 'jet_transport') ? 'wing' : 'rear';
          const wizSweep = document.getElementById('wiz_sweep_quarter_deg');
          if (wizSweep) wizSweep.value = (ac === 'jet_transport') ? 25 : 15;
          const wizFlap = document.getElementById('wiz_flap_type');
          if (wizFlap) wizFlap.value = 'fowler';
        } else if (ac === 'piston_ga' || ac === 'turboprop_regional' || ac === 'uav') {
          wizEngSel.value = 'prop';
          const wizLoc = document.getElementById('wiz_engine_location');
          if (wizLoc) wizLoc.value = (ac === 'turboprop_regional') ? 'wing' : (ac === 'uav' ? 'rear' : 'nose');
          const wizSweep = document.getElementById('wiz_sweep_quarter_deg');
          if (wizSweep) wizSweep.value = (ac === 'turboprop_regional') ? 2 : 0;
          const wizWingCfg = document.getElementById('wiz_wing_config');
          if (wizWingCfg && wizWingCfg.value === 'mid') wizWingCfg.value = (ac === 'piston_ga') ? 'low' : 'high';
          const wizFlap = document.getElementById('wiz_flap_type');
          if (wizFlap && (wizFlap.value === 'flaperon' || (ac !== 'turboprop_regional' && wizFlap.value === 'fowler'))) {
            wizFlap.value = 'single_slotted';
          }
        } else if (ac === 'motoglider') {
          wizEngSel.value = 'prop';
          const wizLoc = document.getElementById('wiz_engine_location');
          if (wizLoc) wizLoc.value = 'retractable';
          const wizSweep = document.getElementById('wiz_sweep_quarter_deg');
          if (wizSweep) wizSweep.value = 0;
          const wizWingCfg = document.getElementById('wiz_wing_config');
          if (wizWingCfg) wizWingCfg.value = 'mid';
          const wizFlap = document.getElementById('wiz_flap_type');
          if (wizFlap) wizFlap.value = 'flaperon';
        } else if (ac === 'glider') {
          wizEngSel.value = 'none';
          const wizSweep = document.getElementById('wiz_sweep_quarter_deg');
          if (wizSweep) wizSweep.value = 0;
          const wizWingCfg = document.getElementById('wiz_wing_config');
          if (wizWingCfg) wizWingCfg.value = 'mid';
        }
      }
      syncAircraftClassAndEASAUI(true, 'aircraft');
      window.BipolDesignBasis?.classDefaults('wiz_');
      suggestStepDefaults(2);
      syncWizardPropulsionUI(true);
    });
  }
  if (wizCatSel) {
    wizCatSel.addEventListener('change', () => {
      syncAircraftClassAndEASAUI(true, 'category');
    });
  }
  document.getElementById('wiz_n_pax')?.addEventListener('change', () => syncAircraftClassAndEASAUI(true, 'pax'));

  // Live change listeners dla mechanizacji w kroku 4
  const flapSel = document.getElementById('wiz_flap_type');
  const slatSel = document.getElementById('wiz_slat_type');
  if (flapSel) flapSel.addEventListener('change', renderWizardStep4Mechanics);
  if (slatSel) slatSel.addEventListener('change', renderWizardStep4Mechanics);
}

function openWizard(mode = 'create') {
  wizardProjectMode = mode;
  const wizardModalTitle = document.querySelector('.wizard-header h3');

  if (mode === 'create') {
    if (wizardModalTitle) {
      wizardModalTitle.textContent = 'Nowy projekt';
    }
    const list = getProjectsList();
    const wizNameInput = document.getElementById('wiz_name');
    if (wizNameInput) {
      wizNameInput.value = `Projekt Samolotu #${list.length + 1}`;
    }
    syncFormToWizard();
    if (wizNameInput) wizNameInput.value = `Projekt Samolotu #${list.length + 1}`;
  } else {
    if (wizardModalTitle) {
      wizardModalTitle.textContent = 'Edytuj założenia projektu';
    }
    syncFormToWizard();
    const active = getActiveProject();
    const wizNameInput = document.getElementById('wiz_name');
    if (wizNameInput && active) {
      wizNameInput.value = active.name;
    }
  }

  // Zacznij od kroku 1
  currentWizardStep = 1;
  goToWizardStep(1);

  // Pokaż modal
  const backdrop = document.getElementById('projectWizardBackdrop');
  if (backdrop) {
    backdrop.classList.add('active');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
}

function closeWizard() {
  const backdrop = document.getElementById('projectWizardBackdrop');
  if (backdrop) {
    backdrop.classList.remove('active');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
}

function syncFormToWizard() {
  const mappings = [
    { formId: 'aircraft_type', wizId: 'wiz_aircraft_type' },
    { formId: 'category', wizId: 'wiz_category' },
    { formId: 'n_crew', wizId: 'wiz_n_crew' },
    { formId: 'n_pax', wizId: 'wiz_n_pax' },
    { formId: 'm_pax', wizId: 'wiz_m_pax' },
    { formId: 'm_cargo', wizId: 'wiz_m_cargo' },
    { formId: 'range_km', wizId: 'wiz_range_km' },
    { formId: 'cruise_altitude_m', wizId: 'wiz_cruise_altitude_m' },
    { formId: 'cruise_speed_kmh', wizId: 'wiz_cruise_speed_kmh' },
    { formId: 'v_stall_kmh', wizId: 'wiz_v_stall_kmh' },
    { formId: 'takeoff_run_m', wizId: 'wiz_takeoff_run_m' },
    { formId: 'climb_rate_ms', wizId: 'wiz_climb_rate_ms' },
    { formId: 'engine_type', wizId: 'wiz_engine_type' },
    { formId: 'engine_location', wizId: 'wiz_engine_location' },
    { formId: 'n_engines', wizId: 'wiz_n_engines' },
    { formId: 'prop_efficiency', wizId: 'wiz_prop_efficiency' },
    { formId: 'sfc', wizId: 'wiz_sfc' },
    { formId: 'wing_config', wizId: 'wiz_wing_config' },
    { formId: 'aspect_ratio', wizId: 'wiz_aspect_ratio' },
    { formId: 'taper_ratio', wizId: 'wiz_taper_ratio' },
    { formId: 'sweep_quarter_deg', wizId: 'wiz_sweep_quarter_deg' },
    { formId: 'flap_type', wizId: 'wiz_flap_type' },
    { formId: 'slat_type', wizId: 'wiz_slat_type' }
  ];

  mappings.forEach(m => {
    const fEl = document.getElementById(m.formId);
    const wEl = document.getElementById(m.wizId);
    if (fEl && wEl && fEl.value !== undefined && fEl.value !== '') {
      wEl.value = fEl.value;
    }
  });

  syncAircraftClassAndEASAUI(true);
  syncWizardPropulsionUI(false);

  const projNameEl = document.getElementById('projectNameDisplay');
  const wizNameEl = document.getElementById('wiz_name');
  if (projNameEl && wizNameEl && projNameEl.textContent.trim()) {
    wizNameEl.value = projNameEl.textContent.trim();
  }
  window.BipolDesignBasis?.openWizard();
}

function goToWizardStep(step) {
  if (step < 1) step = 1;
  if (step > 5) step = 5;
  currentWizardStep = step;

  syncAircraftClassAndEASAUI(true);
  syncWizardPropulsionUI(false);

  // 1. Zaktualizuj stepper tabs
  document.querySelectorAll('.wizard-step-tab').forEach(tab => {
    const s = parseInt(tab.getAttribute('data-step') || '1', 10);
    tab.classList.remove('active', 'completed');
    if (s < currentWizardStep) {
      tab.classList.add('completed');
      const circle = tab.querySelector('.step-circle');
      if (circle) circle.textContent = '✓';
    } else if (s === currentWizardStep) {
      tab.classList.add('active');
      const circle = tab.querySelector('.step-circle');
      if (circle) circle.textContent = s;
    } else {
      const circle = tab.querySelector('.step-circle');
      if (circle) circle.textContent = s;
    }
  });

  // 2. Przełącz widoczność paneli
  for (let i = 1; i <= 5; i++) {
    const pane = document.getElementById(`wizardPane${i}`);
    if (pane) {
      if (i === currentWizardStep) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    }
  }

  // 3. Przyciski stopki
  const backBtn = document.getElementById('wizBackBtn');
  const nextBtn = document.getElementById('wizNextBtn');
  const finishBtn = document.getElementById('wizFinishBtn');

  if (backBtn) {
    backBtn.style.visibility = currentWizardStep === 1 ? 'hidden' : 'visible';
  }

  if (nextBtn && finishBtn) {
    if (currentWizardStep === 5) {
      nextBtn.style.display = 'none';
      finishBtn.style.display = 'inline-flex';
      renderWizardStep5Summary();
    } else {
      nextBtn.style.display = 'inline-flex';
      finishBtn.style.display = 'none';
      if (currentWizardStep === 4) {
        renderWizardStep4Mechanics();
      }
    }
  }

  // Przewiń ciało modala na górę
  const body = document.querySelector('.wizard-body');
  if (body) body.scrollTop = 0;
}

function suggestStepDefaults(step) {
  const acType = document.getElementById('wiz_aircraft_type')?.value || 'piston_ga';

  if (step === 2) {
    const rangeChk = document.querySelector('[data-wizard-assumption="range_km"]');
    const isRangeLocked = rangeChk && rangeChk.checked;
    if (!isRangeLocked) {
      if (acType === 'piston_ga') setFieldValue('wiz_range_km', 750);
      else if (acType === 'motoglider') setFieldValue('wiz_range_km', 600);
      else if (acType === 'glider') setFieldValue('wiz_range_km', 250);
      else if (acType === 'turboprop_regional') setFieldValue('wiz_range_km', 2000);
      else if (acType === 'jet_business') setFieldValue('wiz_range_km', 2400);
      else if (acType === 'jet_transport') setFieldValue('wiz_range_km', 5000);
      else if (acType === 'uav') setFieldValue('wiz_range_km', 1500);
      const bR = document.getElementById('wiz_basis_range_km');
      if (bR) bR.value = document.getElementById('wiz_range_km')?.value || '';
    }

    const spdChk = document.querySelector('[data-wizard-assumption="cruise_speed_kmh"]');
    const isSpdLocked = spdChk && spdChk.checked;
    if (!isSpdLocked) {
      if (acType === 'piston_ga') setFieldValue('wiz_cruise_speed_kmh', 190);
      else if (acType === 'motoglider') setFieldValue('wiz_cruise_speed_kmh', 160);
      else if (acType === 'glider') setFieldValue('wiz_cruise_speed_kmh', 120);
      else if (acType === 'turboprop_regional') setFieldValue('wiz_cruise_speed_kmh', 450);
      else if (acType === 'jet_business') setFieldValue('wiz_cruise_speed_kmh', 680);
      else if (acType === 'jet_transport') setFieldValue('wiz_cruise_speed_kmh', 840);
      else if (acType === 'uav') setFieldValue('wiz_cruise_speed_kmh', 140);
      const bV = document.getElementById('wiz_basis_cruise_speed_kmh');
      if (bV) bV.value = document.getElementById('wiz_cruise_speed_kmh')?.value || '';
    }

    const stallChk = document.querySelector('[data-wizard-assumption="v_stall_kmh"]');
    const isStallLocked = stallChk && stallChk.checked;
    if (!isStallLocked) {
      if (acType === 'piston_ga') setFieldValue('wiz_v_stall_kmh', 85);
      else if (acType === 'motoglider') setFieldValue('wiz_v_stall_kmh', 68);
      else if (acType === 'glider') setFieldValue('wiz_v_stall_kmh', 62);
      else if (acType === 'turboprop_regional') setFieldValue('wiz_v_stall_kmh', 135);
      else if (acType === 'jet_business') setFieldValue('wiz_v_stall_kmh', 160);
      else if (acType === 'jet_transport') setFieldValue('wiz_v_stall_kmh', 190);
      else if (acType === 'uav') setFieldValue('wiz_v_stall_kmh', 70);
      const bVs = document.getElementById('wiz_basis_v_stall_kmh');
      if (bVs) bVs.value = document.getElementById('wiz_v_stall_kmh')?.value || '';
    }

    if (acType === 'piston_ga') {
      setFieldValue('wiz_cruise_altitude_m', 2000);
      setFieldValue('wiz_takeoff_run_m', 220);
      setFieldValue('wiz_takeoff_distance_m', 600);
      setFieldValue('wiz_landing_distance_m', 600);
      setFieldValue('wiz_climb_rate_ms', 4.5);
    } else if (acType === 'motoglider') {
      setFieldValue('wiz_cruise_altitude_m', 1500);
      setFieldValue('wiz_takeoff_run_m', 250);
      setFieldValue('wiz_takeoff_distance_m', 500);
      setFieldValue('wiz_landing_distance_m', 500);
      setFieldValue('wiz_climb_rate_ms', 3.2);
    } else if (acType === 'glider') {
      setFieldValue('wiz_cruise_altitude_m', 1500);
      setFieldValue('wiz_takeoff_run_m', 0);
      setFieldValue('wiz_takeoff_distance_m', 0);
      setFieldValue('wiz_landing_distance_m', 350);
      setFieldValue('wiz_climb_rate_ms', 0);
    } else if (acType === 'turboprop_regional') {
      setFieldValue('wiz_cruise_altitude_m', 6000);
      setFieldValue('wiz_takeoff_run_m', 700);
      setFieldValue('wiz_takeoff_distance_m', 1100);
      setFieldValue('wiz_landing_distance_m', 1000);
      setFieldValue('wiz_climb_rate_ms', 8.5);
    } else if (acType === 'jet_business') {
      setFieldValue('wiz_cruise_altitude_m', 11000);
      setFieldValue('wiz_takeoff_run_m', 950);
      setFieldValue('wiz_takeoff_distance_m', 1400);
      setFieldValue('wiz_landing_distance_m', 1200);
      setFieldValue('wiz_climb_rate_ms', 14.0);
    } else if (acType === 'jet_transport') {
      setFieldValue('wiz_cruise_altitude_m', 11500);
      setFieldValue('wiz_takeoff_run_m', 1600);
      setFieldValue('wiz_takeoff_distance_m', 2400);
      setFieldValue('wiz_landing_distance_m', 1900);
      setFieldValue('wiz_climb_rate_ms', 12.0);
    } else if (acType === 'uav') {
      setFieldValue('wiz_cruise_altitude_m', 5000);
      setFieldValue('wiz_takeoff_run_m', 180);
      setFieldValue('wiz_takeoff_distance_m', 400);
      setFieldValue('wiz_landing_distance_m', 400);
      setFieldValue('wiz_climb_rate_ms', 4.0);
    }
  }
}

function renderWizardStep4Mechanics() {
  const card = document.getElementById('wizFlapDidacticCard');
  if (!card || typeof DIDACTIC_DATABASE === 'undefined') return;

  const flapId = document.getElementById('wiz_flap_type')?.value || 'single_slotted';
  const slatId = document.getElementById('wiz_slat_type')?.value || 'none';

  const flap = DIDACTIC_DATABASE.flaps[flapId] || DIDACTIC_DATABASE.flaps.single_slotted;
  const slat = DIDACTIC_DATABASE.slats[slatId] || DIDACTIC_DATABASE.slats.none;

  const czClean = 1.40;
  const totalCzLnd = +(czClean + flap.delta_cz_max + slat.delta_cz_max).toFixed(2);

  card.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.4rem;">
      <div>
        <div style="font-size:0.75rem; font-weight:800; color:#0284c7; text-transform:uppercase;">
          Ocena Dydaktyczna Wybranej Mechanizacji (${flap.reference})
        </div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a;">
          ${flap.name} ${slatId !== 'none' ? '+ ' + slat.name : ''}
        </div>
      </div>
      <div style="display:flex; gap:0.35rem; flex-wrap:wrap;">
        <span class="badge badge-success">&Delta;Cz = +${flap.delta_cz_max.toFixed(2)}</span>
        <span class="badge badge-warning">&Delta;Cx0 = +${flap.delta_cx0_lnd.toFixed(3)}</span>
        <span class="badge badge-info">Szacowany Cz_max,lnd = ${totalCzLnd}</span>
      </div>
    </div>
    <div class="pros-cons-grid" style="margin-bottom:0.4rem;">
      <div class="pros-box">
        <h5>👍 Zalety układu:</h5>
        <ul>${flap.pros.slice(0, 2).map(p => `<li>${p}</li>`).join('')}</ul>
      </div>
      <div class="cons-box">
        <h5>⚠️ Ograniczenia i kompromisy:</h5>
        <ul>${flap.cons.slice(0, 2).map(c => `<li>${c}</li>`).join('')}</ul>
      </div>
    </div>
    <div class="galinski-quote-box" style="font-size:0.72rem;">
      <strong>📘 Prof. C. Galiński:</strong> „${flap.galinski_quote}”
    </div>
  `;
}

function renderWizardStep5Summary() {
  const tbody = document.getElementById('wizardSummaryTableBody');
  const auditBox = document.getElementById('wizardAuditBox');
  if (!tbody || !auditBox) return;

  const getV = (id) => document.getElementById(id)?.value || '';
  const getN = (id) => parseFloat(document.getElementById(id)?.value || '0');

  const name = getV('wiz_name');
  const acType = getV('wiz_aircraft_type');
  const cat = getV('wiz_category');
  const nCrew = getN('wiz_n_crew');
  const nPax = getN('wiz_n_pax');
  const mCargo = getN('wiz_m_cargo');
  const R = getN('wiz_range_km');
  const H = getN('wiz_cruise_altitude_m');
  const Vcr = getN('wiz_cruise_speed_kmh');
  const Vs0 = getN('wiz_v_stall_kmh');
  const Sto = getN('wiz_takeoff_distance_m');
  const wy = getN('wiz_climb_rate_ms');
  const engType = getV('wiz_engine_type');
  const engLoc = getV('wiz_engine_location');
  const sfcVal = getN('wiz_sfc');
  const etaP = getN('wiz_prop_efficiency');
  const wingCfg = getV('wiz_wing_config');
  const AR = getN('wiz_aspect_ratio');
  const eta = getN('wiz_taper_ratio');
  const flap = getV('wiz_flap_type');
  const slat = getV('wiz_slat_type');

  const locNames = { nose: 'Dziób kadłuba', wing: 'Gondole skrzydłowe', rear: 'Tył kadłuba / gondole ogonowe', retractable: 'Napęd chowany w kadłubie' };
  const nEng = getN('wiz_n_engines') || 1;
  const engCountText = engType === 'none' ? '' : `${nEng}× `;
  const propSummaryText = engType === 'none' ? 'Bez napędu — szybowiec' : engType === 'jet'
    ? `${engCountText}Odrzutowy (Turbofan) &bull; ${locNames[engLoc] || engLoc} &bull; TSFC = ${sfcVal} 1/h`
    : `${engCountText}Śmigłowy &bull; ${locNames[engLoc] || engLoc} &bull; SFC = ${sfcVal} g/(kW&bull;h), &eta;_p = ${etaP}`;

  const catNames = {
    cs23_level1: 'EASA CS-23 Level 1 (0–1 pax)',
    cs23_level2: 'EASA CS-23 Level 2 (2–6 pax)',
    cs23_level3: 'EASA CS-23 Level 3 (7–9 pax)',
    cs23_commuter: 'EASA CS-23 Level 4 / Commuter (10–19 pax)',
    cs23_aerobatic: 'EASA CS-23 Certified for Aerobatics',
    cs_vla: 'EASA CS-VLA (MTOM ≤ 750 kg, max 2 os.)',
    cs_lsa: 'EASA CS-LSA (MTOM ≤ 600 kg, max 2 os.)',
    cs22_glider: 'EASA CS-22 (Szybowiec)',
    cs22_motoglider: 'EASA CS-22 (TMG Motoszybowiec)',
    cs25_transport: 'EASA CS-25 (Large Aeroplanes)',
    easa_optout_ul: 'EASA Annex I Opt-out / UL-A (600 kg)',
    easa_optout_ul115: 'EASA Annex I / UL-115 (≤ 115 kg)',
    easa_uas_specific: 'EASA UAS Specific (ocena ryzyka operacji)',
    easa_uas_certified: 'EASA UAS Certified (ocena ryzyka operacji)'
  };
  const catLabel = catNames[cat] || `EASA (${cat.toUpperCase()})`;
  const acClassLabel = AIRCRAFT_CLASS_LABELS_PL[acType] || acType.toUpperCase();
  const flapLabel = FLAP_TYPE_LABELS_PL[flap] || flap;
  const slatLabel = SLAT_TYPE_LABELS_PL[slat] || slat;
  const wingMode = getV('wiz_wing_input_mode') || 'loading';
  const bWiz = getN('wiz_wingspan_m');
  const sWiz = getN('wiz_wing_area_m2');
  const wingSummaryVal = wingMode === 'span_aspect'
    ? `b = ${bWiz} m; Λ = ${AR} (S = ${AR > 0 ? (bWiz * bWiz / AR).toFixed(2) : '—'} m²)`
    : wingMode === 'span_area'
      ? `b = ${bWiz} m; S = ${sWiz} m² (Λ = ${sWiz > 0 ? (bWiz * bWiz / sWiz).toFixed(2) : '—'})`
      : wingMode === 'area_aspect'
        ? `S = ${sWiz} m²; Λ = ${AR} (b = ${sWiz > 0 && AR > 0 ? Math.sqrt(sWiz * AR).toFixed(2) : '—'} m)`
        : `Λ = ${AR} (S i b wyznaczane z MTOW oraz VS0)`;
  const runwaySummaryVal = engType === 'none'
    ? 'Start na holu / za wyciągarką'
    : `S_to = ${Sto > 0 ? Sto + ' m' : 'nie narzucono'}, w_y = ${wy} m/s`;
  const isUasSummary = (acType === 'uav' || cat.startsWith('easa_uas_'));
  const occSummaryText = isUasSummary
    ? `0 osób na pokładzie (sterowanie z GCS) &bull; ${mCargo} kg wyposażenie zadaniowe / sensory`
    : `${nCrew} pilot(ów), ${nPax} pasażer(ów), ${mCargo} kg cargo`;

  tbody.innerHTML = `
    <tr><td><b>Projekt i Klasa</b></td><td>Nazwa statku powietrznego</td><td class="num"><b>${escapeHtml(name)}</b></td><td><span class="badge badge-info">${escapeHtml(acClassLabel)}</span></td></tr>
    <tr><td><b>Przepisy EASA</b></td><td>Kategoria certyfikacyjna</td><td class="num"><b>${catLabel}</b></td><td>Wymóg przepisowy EASA</td></tr>
    <tr><td><b>Załoga i Ładunek</b></td><td>Piloci / Pasażerowie / Ładunek</td><td class="num"><b>${occSummaryText}</b></td><td>Ładunek płatny</td></tr>
    <tr><td><b>Zasięg i Pułap</b></td><td>Zasięg R / Wysokość przelotu H</td><td class="num"><b>R = ${R} km, H = ${H} m</b></td><td>Profil misji przelotowej</td></tr>
    <tr><td><b>Prędkości</b></td><td>Przelotowa Vcr / Lądowania Vs0</td><td class="num"><b>Vcr = ${Vcr} km/h, Vs0 = ${Vs0} km/h</b></td><td>Stosunek Vcr/Vs0 = ${(Vcr/Vs0).toFixed(2)}</td></tr>
    <tr><td><b>Osiągi lotniskowe</b></td><td>Całkowity start do 15 m / Wznoszenie w_y</td><td class="num"><b>${runwaySummaryVal}</b></td><td>Długość pasa i odejście na 2. krąg</td></tr>
    <tr><td><b>Zespół Napędowy</b></td><td>Rodzaj, zabudowa i zużycie paliwa</td><td class="num"><b>${propSummaryText}</b></td><td>Zespół napędowy</td></tr>
    <tr><td><b>Założenia skrzydła</b></td><td>${escapeHtml(document.getElementById('wiz_wing_input_mode').selectedOptions[0].textContent)}</td><td class="num"><b>${wingSummaryVal}</b></td><td>Wielkości zależne są obliczane</td></tr>
    <tr><td><b>Mechanizacja</b></td><td>Klapy spływu i sloty natarcia</td><td class="num"><b>${escapeHtml(flapLabel)} &bull; ${escapeHtml(slatLabel)}</b></td><td>Zapewnienie wymaganego Vs0</td></tr>
  `;

  // Audyt spójności
  const issues = [];
  if (isUasSummary && (nCrew > 0 || nPax > 0)) {
    issues.push('🛑 Błąd przepisów EASA: Bezzałogowy statek powietrzny (UAS) nie może mieć pilotów ani pasażerów na pokładzie!');
  }
  if ((cat === 'cs_vla' || cat === 'cs_lsa' || cat === 'cs22_motoglider' || cat === 'cs22_glider' || cat === 'easa_optout_ul') && (nCrew + nPax > 2)) {
    issues.push(`🛑 Błąd przepisów EASA: ${catLabel} dopuszcza maksymalnie 2 osoby na pokładzie (załoga + pasażerowie = ${nCrew + nPax}).`);
  }
  if ((cat === 'cs_vla' || cat === 'cs_lsa' || cat === 'easa_optout_ul') && Vs0 > 83.3) {
    issues.push(`⚠️ Przekroczony limit EASA: Prędkość przeciągnięcia VS0 (${Vs0} km/h) przekracza maksymalne dopuszczalne 45 kt (83.3 km/h). Zwiększ powierzchnię nośną lub zastosuj bardziej efektywne klapy.`);
  }
  if (cat === 'cs23_level1' && nPax > 1) {
    issues.push(`⚠️ Niezgodność z EASA CS 23.2005: Poziom Level 1 dopuszcza maksymalnie 1 pasażera (obecnie: ${nPax}). Wybierz Level 2.`);
  }
  if (cat === 'cs23_level2' && nPax > 6) {
    issues.push(`⚠️ Niezgodność z EASA CS 23.2005: Poziom Level 2 dopuszcza maksymalnie 6 pasażerów (obecnie: ${nPax}). Wybierz Level 3.`);
  }
  if (cat === 'cs23_level3' && nPax > 9) {
    issues.push(`⚠️ Niezgodność z EASA CS 23.2005: Poziom Level 3 dopuszcza maksymalnie 9 pasażerów (obecnie: ${nPax}). Wybierz Level 4.`);
  }
  if (cat === 'cs23_commuter' && nPax > 19) {
    issues.push(`⚠️ Niezgodność z EASA CS 23.2005: Poziom Level 4 / Commuter dopuszcza maksymalnie 19 pasażerów (obecnie: ${nPax}). Dla większej liczby pasażerów wymagana jest certyfikacja CS-25.`);
  }
  if (Vs0 >= Vcr) {
    issues.push('🛑 Błąd krytyczny: Prędkość przeciągnięcia VS0 nie może być większa lub równa prędkości przelotowej Vcr!');
  }
  if (engType === 'jet' && Vcr < 400) {
    issues.push(`⚠️ Nieoptymalny napęd: Napęd odrzutowy przy niskiej prędkości przelotowej (${Vcr} km/h) cechuje się bardzo niską sprawnością propulsywną i ogromnym zużyciem paliwa.`);
  }
  if (engType === 'prop' && Vcr > 620) {
    issues.push(`⚠️ Ograniczenie ściśliwości śmigła: Przy prędkości ${Vcr} km/h końcówki łopat śmigła przekroczą krytyczną liczbę Macha (M_tip > 0.90). Zastosuj napęd odrzutowy.`);
  }
  if (wingCfg === 'mid' && (nPax >= 2 || mCargo >= 150)) {
    issues.push('⚠️ Uwaga konstrukcyjna: Średniopłat przy pasażerach lub cargo wymusza przejście dźwigara przez kabinę (Rozdz. 14 prof. Galińskiego).');
  }
  if (wingCfg === 'braced_high' && Vcr > 240) {
    issues.push(`⚠️ Uwaga oporowa: Górnopłat zastrzałowy przy prędkości ${Vcr} km/h generuje bardzo duży opór szkodliwy.`);
  }
  if (slat === 'fixed_slot' && Vcr > 210) {
    issues.push('⚠️ Stałe przedskrzydło (slot) przy prędkości > 200 km/h generuje nieakceptowalny opór przelotowy.');
  }

  if (issues.length === 0) {
    auditBox.className = 'wizard-audit-box success';
    auditBox.innerHTML = `
      <strong>✅ Założenia gotowe do przeliczenia.</strong><br>
      Przy zatwierdzeniu program sprawdzi bilans masy, geometrię i osiągi. Projekt zostanie zapisany dopiero po poprawnym przeliczeniu.
    `;
  } else {
    auditBox.className = 'wizard-audit-box warning';
    auditBox.innerHTML = `
      <strong>⚠️ Zidentyfikowano zalecenia do skorygowania:</strong>
      <ul style="margin:4px 0 0 16px; padding:0;">
        ${issues.map(it => `<li>${it}</li>`).join('')}
      </ul>
      <div style="margin-top:4px; font-size:0.75rem;">Możesz cofnąć się przyciskiem <em>„Wstecz”</em> lub kontynuować mimo to.</div>
    `;
  }
}

function showWizardError(message) {
  const el = document.getElementById('wizardValidationStatus');
  if (el) el.textContent = message;
}

async function commitWizardToForm() {
  syncAircraftClassAndEASAUI(true);
  syncWizardPropulsionUI(false);
  BipolDesignBasis.sync('wiz_');
  for (let step = 1; step <= 4; step++) {
    try { validateNumericFields(document.getElementById(`wizardPane${step}`)); }
    catch (err) { goToWizardStep(step); showWizardError(err.message); return; }
  }
  const params = BipolDesignBasis.snapshot();
  const finish = document.getElementById('wizFinishBtn');
  const originalText = finish.textContent;
  finish.disabled = true; finish.textContent = 'Sprawdzanie projektu…';
  showWizardError('');
  try {
    const response = await fetch('/api/calculate', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(params)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || 'Nie udało się obliczyć projektu.');
    if (!document.getElementById('projectWizardBackdrop').classList.contains('active')) return;
    if (JSON.stringify(params) !== JSON.stringify(BipolDesignBasis.snapshot())) {
      throw new Error('Założenia zmieniły się podczas obliczeń. Zatwierdź je ponownie.');
    }
    calculationSequence++; calculationController?.abort();
    const active = wizardProjectMode === 'edit' ? getActiveProject() : null;
    const project = active || {id:'proj_'+Date.now(), createdAt:new Date().toISOString()};
    Object.assign(project, {name:params.name, aircraft_type:result.params.aircraft_type,
      category:result.params.category, params:result.params, summary:{}});
    saveProject(project); setActiveProjectId(project.id); loadProjectIntoForm(project);
    currentResults = result; updateUI(result); updateDerivedUI(result.constraints.parameter_states);
    autoSaveActiveProject(result); renderProjectSwitcher();
    showCalculationStatus('Wyniki i zapis projektu są aktualne.');
    document.getElementById('openReportBtn')?.setAttribute('data-results-stale','false');
    document.dispatchEvent(new CustomEvent('bipol:results', {detail:result}));
    closeWizard();
    if (currentPortalMode === 'holistic') {
      document.querySelector('.bipol-tab[data-target="tab-overview"]')?.click();
    }
  } catch (error) { showWizardError(error.message); }
  finally { finish.disabled = false; finish.textContent = originalText; }
}

// =========================================================================
// SYSTEM DWU-PORTALOWY (WERSJA 1: CAŁOŚCIOWA vs WERSJA 2: PROJEKTY P1-P6)
// =========================================================================
const PORTAL_MODE_KEY = 'bipol_portal_mode';
const ACTIVE_SEMESTER_P_KEY = 'bipol_active_semester_p';
const SEMESTER_CHECKLIST_KEY = 'bipol_semester_checklist_v1';

let currentPortalMode = 'holistic';
let currentSemesterProject = 'p1';

// Definicja wag punktowych dla wszystkich 19 podpunktów P1–P6 wg regulaminu MEiL PW
const SEMESTER_RUBRIC = {
  p1: [
    { id: 'chk_p1_1', pts: 3, type: 'obow' },
    { id: 'chk_p1_2', pts: 2, type: 'opcj' }
  ],
  p2: [
    { id: 'chk_p2_1', pts: 5, type: 'obow' },
    { id: 'chk_p2_2', pts: 3, type: 'opcj' },
    { id: 'chk_p2_3', pts: 2, type: 'opcj' },
    { id: 'chk_p2_4', pts: 5, type: 'obow' },
    { id: 'chk_p2_5', pts: 3, type: 'obow' }
  ],
  p3: [
    { id: 'chk_p3_1', pts: 15, type: 'obow' },
    { id: 'chk_p3_2', pts: 5, type: 'obow' },
    { id: 'chk_p3_3', pts: 2, type: 'obow' },
    { id: 'chk_p3_4', pts: 5, type: 'opcj' }
  ],
  p4: [
    { id: 'chk_p4_1', pts: 5, type: 'obow' },
    { id: 'chk_p4_2', pts: 3, type: 'opcj' },
    { id: 'chk_p4_3', pts: 5, type: 'opcj' },
    { id: 'chk_p4_4', pts: 2, type: 'opcj' }
  ],
  p5: [
    { id: 'chk_p5_1', pts: 5, type: 'opcj' },
    { id: 'chk_p5_2', pts: 4, type: 'opcj' },
    { id: 'chk_p5_3', pts: 4, type: 'opcj' },
    { id: 'chk_p5_4', pts: 2, type: 'obow' }
  ],
  p6: [
    { id: 'chk_p6_1', pts: 15, type: 'obow' },
    { id: 'chk_p6_2', pts: 5, type: 'opcj' }
  ]
};

function initDualPortalSystem() {
  // 1. Odtwórz stany checklisty punktacji z localStorage
  try {
    const savedRaw = localStorage.getItem(SEMESTER_CHECKLIST_KEY);
    if (savedRaw) {
      const savedMap = JSON.parse(savedRaw);
      Object.entries(savedMap).forEach(([chkId, isChecked]) => {
        const el = document.getElementById(chkId);
        if (el) el.checked = Boolean(isChecked);
      });
    }
  } catch (e) {
    console.warn('Nie udało się odczytać checklisty semestralnej:', e);
  }

  updateSemesterScores(false);

  // 2. Odtwórz aktywny projekt semestralny (p1..p6)
  const savedP = safeLocalItem(ACTIVE_SEMESTER_P_KEY);
  if (savedP && ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'].includes(savedP)) {
    currentSemesterProject = savedP;
  }

  // 3. Ustal początkowy tryb portalu (z URL Flask lub localStorage)
  const urlMode = (typeof window.INITIAL_PORTAL_MODE === 'string' && window.INITIAL_PORTAL_MODE.trim())
    ? window.INITIAL_PORTAL_MODE.trim()
    : null;
  const storedMode = safeLocalItem(PORTAL_MODE_KEY);
  const initialMode = urlMode || storedMode || 'holistic';

  setPortalMode(initialMode === 'projects' ? 'projects' : 'holistic');
}

function setPortalMode(mode) {
  currentPortalMode = (mode === 'projects') ? 'projects' : 'holistic';
  try {
    localStorage.setItem(PORTAL_MODE_KEY, currentPortalMode);
  } catch (e) {}

  const btnHolistic = document.getElementById('btnModeHolistic');
  const btnProjects = document.getElementById('btnModeProjects');
  const holisticWs = document.getElementById('holisticWorkspace');
  const semesterBar = document.getElementById('semesterProjectBar');
  const semesterWs = document.getElementById('semesterWorkstation');

  if (currentPortalMode === 'projects') {
    if (btnHolistic) btnHolistic.classList.remove('active');
    if (btnProjects) btnProjects.classList.add('projects-active');
    if (holisticWs) holisticWs.style.display = 'none';
    if (semesterBar) semesterBar.style.display = 'block';
    if (semesterWs) semesterWs.style.display = 'block';

    selectSemesterProject(currentSemesterProject || 'p1');
  } else {
    if (btnHolistic) btnHolistic.classList.add('active');
    if (btnProjects) btnProjects.classList.remove('projects-active');
    if (holisticWs) holisticWs.style.display = 'block';
    if (semesterBar) semesterBar.style.display = 'none';
    if (semesterWs) semesterWs.style.display = 'none';

    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab && currentResults) {
      renderTabVisuals(activeTab.id);
    }
  }
  document.dispatchEvent(new CustomEvent('bipol:mode'));
}

function selectSemesterProject(pId) {
  if (!['p1', 'p2', 'p3', 'p4', 'p5', 'p6'].includes(pId)) pId = 'p1';
  currentSemesterProject = pId;
  try {
    localStorage.setItem(ACTIVE_SEMESTER_P_KEY, pId);
  } catch (e) {}

  // 1. Zaktualizuj aktywną pigułkę P1–P6
  document.querySelectorAll('.semester-project-pill').forEach(pill => {
    pill.classList.toggle('active', pill.id === `pill-${pId}`);
  });

  // 2. Przełącz widoczny panel roboczy projektu
  ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'].forEach(id => {
    const panel = document.getElementById(`panel-${id}`);
    if (panel) {
      panel.style.display = (id === pId) ? 'block' : 'none';
    }
  });

  // 2b. Zaktualizuj tytuł projektu na podglądzie 1:1 Strony Tytułowej (Rys. 2)
  const r2TitleMap = {
    p1: ['Projekt 1', 'Projekt Koncepcyjny'],
    p2: ['Projekt 2', 'Studium Wykonalności'],
    p3: ['Projekt 3', 'Projekt Wstępny i Analiza Masowa'],
    p4: ['Projekt 4', 'Charakterystyki aerodynamiczne samolotu'],
    p5: ['Projekt 5', 'Osiągi Samolotu'],
    p6: ['Projekt 6', 'Obwiednia Obciążeń Dopuszczalnych']
  };
  const r2Lines = r2TitleMap[pId] || ['Projekt 1', 'Projekt Koncepcyjny'];
  const l1El = document.getElementById('prev_r2_line1');
  const l2El = document.getElementById('prev_r2_line2');
  if (l1El) l1El.textContent = r2Lines[0];
  if (l2El) l2El.textContent = r2Lines[1];

  // 3. Dopasuj otwarty moduł parametrów w lewym pasku bocznym do tematyki projektu
  const sidebarMapping = {
    p1: ['mod1'],
    p2: ['mod1', 'mod2'],
    p3: ['mod2', 'mod4'],
    p4: ['mod3'],
    p5: ['mod1'],
    p6: ['mod1', 'mod4']
  };
  const activeMods = sidebarMapping[pId] || ['mod1'];
  ['mod1', 'mod2', 'mod3', 'mod4'].forEach(modKey => {
    const header = document.querySelector(`.module-header[onclick*="${modKey}"]`);
    const body = document.getElementById(`body_${modKey}`);
    const chev = document.getElementById(`chev_${modKey}`);
    if (body) {
      if (activeMods.includes(modKey)) {
        body.classList.remove('collapsed');
        if (header) header.classList.add('active');
        if (chev) chev.style.transform = 'rotate(0deg)';
      } else {
        body.classList.add('collapsed');
        if (header) header.classList.remove('active');
        if (chev) chev.style.transform = 'rotate(-90deg)';
      }
    }
  });

  // 4. Przerysuj wykresy dedykowane dla wybranego projektu semestralnego
  if (currentResults) {
    renderSemesterProjectCharts(pId, currentResults);
  }
}

function renderSemesterProjectCharts(pId, res) {
  if (!res) return;
  setTimeout(() => {
    switch (pId) {
      case 'p2':
        if (typeof drawMatchingChart === 'function' && res.sizing) {
          drawMatchingChart('chartMatchingP2', res.sizing);
        }
        break;
      case 'p3':
        if (typeof drawSchrenkChart === 'function' && res.geometry?.schrenk) {
          drawSchrenkChart('chartSchrenkP3', res.geometry.schrenk);
        }
        break;
      case 'p4':
        if (typeof drawPolarChart === 'function' && res.aerodynamics) {
          drawPolarChart('chartPolarP4', res.aerodynamics);
        }
        break;
      case 'p6':
        if (typeof drawVnEnvelope === 'function' && res.envelope) {
          drawVnEnvelope('chartVnP6', res.envelope);
        }
        break;
    }
  }, 50);
}

function restoreProjectChecklist(project) {
  const state = project.semesterChecklist || {};
  Object.values(SEMESTER_RUBRIC).flat().forEach(item => {
    const input = document.getElementById(item.id);
    if (input) input.checked = state[item.id] === true;
  });
  updateSemesterScores(false);
}

function updateSemesterScores(persist = true) {
  let totalObow = 0;
  let totalOpcj = 0;
  const stateMap = {};

  Object.entries(SEMESTER_RUBRIC).forEach(([pKey, items]) => {
    let projScore = 0;
    items.forEach(item => {
      const el = document.getElementById(item.id);
      const checked = el ? el.checked : false;
      stateMap[item.id] = checked;
      if (checked) {
        projScore += item.pts;
        if (item.type === 'obow') totalObow += item.pts;
        else totalOpcj += item.pts;
      }
    });
    const projDisplay = document.getElementById(`score_${pKey}_display`);
    if (projDisplay) projDisplay.textContent = projScore;
    const badge = document.getElementById(`pts-badge-${pKey}`);
    if (badge) badge.textContent = `${projScore} / ${items.reduce((sum, item) => sum + item.pts, 0)} pkt`;
  });

  const totalScore = totalObow + totalOpcj;

  const elTotal = document.getElementById('semTotalPointsDisplay');
  if (elTotal) elTotal.textContent = totalScore;

  const elObow = document.getElementById('semObligatoryPointsDisplay');
  if (elObow) elObow.textContent = totalObow;

  const elOpcj = document.getElementById('semOptionalPointsDisplay');
  if (elOpcj) elOpcj.textContent = totalOpcj;

  const elStatus = document.getElementById('semStatusBadge');
  if (elStatus) {
    if (totalScore >= 50) {
      elStatus.className = 'score-badge success';
      elStatus.innerHTML = `Realizacja checklisty: <strong>${totalScore}/100 pkt</strong> (ocenia prowadzący)`;
    } else {
      elStatus.className = 'score-badge warn';
      elStatus.innerHTML = `Do progu 50 pkt w checkliście: <strong>${50 - totalScore} pkt</strong>`;
    }
  }

  if (persist) {
    try {
      const active = getActiveProject();
      if (active) {
        active.semesterChecklist = stateMap;
        saveProject(active);
      }
    } catch (e) {}
  }
}

function hydrateSemesterProjectsData(res) {
  const bp = res?.bipol_projects;
  if (!bp) return;

  const isJet = (res?.sizing?.design_point?.engine_type || document.getElementById('engine_type')?.value) === 'jet';
  const isGlider = res.params?.engine_type === 'none';

  // --- PROJEKT 1: PROJEKT KONCEPCYJNY ---
  if (bp.p1) {
    const p1 = bp.p1;
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    setTxt('p1_concept_text', p1.concept_description);
    setTxt('p1_swet_ratio', `${p1.swet_over_s} (Swet = ${p1.s_wet_m2} m²)`);
    setTxt('p1_kmax_est', p1.k_max_est);
    if (p1.engine_type === 'jet' || isJet) {
      setTxt('p1_preq_label', 'Wstępny ciąg do lotu T_req:');
      setTxt('p1_preq_est', `${p1.t_req_est_kn} kN (P_eff = ${p1.p_req_est_kw} kW)`);
      setTxt('p1_sim_power_th', 'Ciąg T₀ [kN]');
    } else {
      setTxt('p1_preq_label', 'Wstępna moc do lotu P_req:');
      setTxt('p1_preq_est', `${p1.p_req_est_kw} kW`);
      setTxt('p1_sim_power_th', 'Moc [kW]');
    }
    setTxt('p1_we_trend', p1.trend_analysis?.we_wo_trend);
    setTxt('p1_we_actual', p1.trend_analysis?.we_wo_actual);

    const simTbody = document.getElementById('p1_similar_tbody');
    if (simTbody && Array.isArray(p1.trend_analysis?.similar_aircraft)) {
      simTbody.innerHTML = p1.trend_analysis.similar_aircraft.map(a => {
        const powerOrThrust = a.engine_type === 'jet'
          ? (a.t_kn == null ? '—' : `${a.t_kn.toFixed(1)} kN`)
          : (a.p_kw == null ? '—' : `${a.p_kw.toFixed(1)} kW`);
        return `
        <tr>
          <td><b>${escapeHtml(a.model)}</b></td>
          <td>${a.m0}</td>
          <td>${a.me ?? '—'}</td>
          <td>${a.s ?? '—'}</td>
          <td>${powerOrThrust}</td>
          <td>${a.v_max ?? '—'}</td>
          <td>${a.ar?.toFixed(2) ?? '—'}</td>
          <td>${a.prop_diameter_m != null ? `${a.prop_diameter_m.toFixed(2)} m` : '—'}</td>
        </tr>
      `;
      }).join('');
    }
  }

  // --- PROJEKT 2: STUDIUM WYKONALNOŚCI ---
  if (bp.p2) {
    const p2 = bp.p2;
    const missTbody = document.getElementById('p2_mission_tbody');
    if (missTbody && Array.isArray(p2.mission_profile)) {
      missTbody.innerHTML = p2.mission_profile.map(m => `
        <tr>
          <td>${escapeHtml(m.phase)}</td>
          <td><b>${Number.isFinite(Number(m.fraction)) ? Number(m.fraction).toFixed(4) : m.fraction}</b></td>
          <td>${Number.isFinite(Number(m.mass_end_kg)) ? Number(m.mass_end_kg).toFixed(1) : m.mass_end_kg} kg</td>
        </tr>
      `).join('');
    }

    const afSel = p2.airfoil_selection || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    setTxt('p2_re_val', afSel.reynolds_cruise?.toLocaleString('pl-PL'));
    setTxt('p2_mach_val', afSel.mach_max);
    setTxt('p2_catalog_val', afSel.recommended_catalog);
    setTxt('p2_czproj_val', afSel.cz_proj);

    const afTbody = document.getElementById('p2_airfoil_tbody');
    if (afTbody && Array.isArray(afSel.candidates)) {
      afTbody.innerHTML = afSel.candidates.map(c => `
        <tr style="${c.recommended ? 'background:#ecfdf5;' : ''}">
          <td><b>${escapeHtml(c.name)}</b></td>
          <td>${c.cx_min ?? "—"}</td>
          <td>${c.cx_cz_proj ?? "—"}</td>
          <td>${c.cz_max ?? "—"}</td>
          <td>${c.k_max ?? "—"}</td>
          <td>${escapeHtml(c.stall)}</td>
          <td><span class="badge ${c.recommended ? 'badge-success' : 'badge-info'}">${c.recommended ? '✓ Wybrany' : 'Alternatywa'}</span></td>
        </tr>
      `).join('');
    }

    const sensTbody = document.getElementById('p2_sensitivity_tbody');
    if (sensTbody && Array.isArray(p2.sensitivity?.table)) {
      sensTbody.innerHTML = p2.sensitivity.table.map(s => `
        <tr>
          <td><b>${escapeHtml(s.var)}</b></td>
          <td>${s.delta}</td>
          <td><b>${s.d_mtow_kg > 0 ? '+' : ''}${s.d_mtow_kg} kg</b></td>
          <td>${s.pct_change > 0 ? '+' : ''}${s.pct_change}%</td>
        </tr>
      `).join('');
    }

    const mcs = p2.matching_chart_summary || {};
    setTxt('p2_ws_pt', mcs.ws_design);
    const pwTwBox = document.getElementById('p2_pw_tw_box');
    if (pwTwBox) {
      if (mcs.engine_type === 'jet' || mcs.tw_design != null) {
        pwTwBox.innerHTML = `Ciąg do ciężaru: <b>T/W = <span id="p2_pw_pt">${mcs.tw_design}</span> [-]</b> ${mcs.thrust_kn != null ? `(T₀ = <b>${mcs.thrust_kn} kN</b>)` : ''}`;
      } else {
        pwTwBox.innerHTML = `Moc do ciężaru: <b>P/W = <span id="p2_pw_pt">${mcs.pw_design}</span> W/N</b> ${mcs.power_kw != null ? `(P₀ = <b>${mcs.power_kw} kW</b>)` : ''}`;
      }
    }
    setTxt('p2_s_pt', mcs.s_wing_m2);

    const costs = p2.cost_analysis || {};
    setTxt('p2_rdte_hours', costs.rdte_hours?.toLocaleString('pl-PL'));
    setTxt('p2_labor_hours', costs.manufacturing_hours_total?.toLocaleString('pl-PL'));
    setTxt('p2_qc_hours', costs.quality_control_hours?.toLocaleString('pl-PL'));
    setTxt('p2_unit_cost', `$${(costs.unit_cost_usd || 0).toLocaleString('pl-PL')} USD`);
    setTxt('p2_selling_price', `${(costs.selling_price_pln || 0).toLocaleString('pl-PL')} PLN ($${(costs.selling_price_usd || 0).toLocaleString('pl-PL')} USD)`);
  }

  // --- PROJEKT 3: PROJEKT WSTĘPNY I ANALIZA MASOWA ---
  if (bp.p3) {
    const p3 = bp.p3;
    const bchk = p3.blueprint_checks || {};
    const chkMachEl = document.getElementById('p3_chk_prop_mach');
    const chkClearEl = document.getElementById('p3_chk_prop_clear');
    if (chkMachEl) chkMachEl.textContent = bchk.engine_type==='prop'
      ? `Liczba Macha końcówki śmigła: ${bchk.propeller_tip_mach}; ${bchk.propeller_tip_mach<=.85?'spełnia roboczy limit 0,85':'przekracza roboczy limit 0,85 — zmień średnicę lub obroty'}.`
      : bchk.engine_type==='jet'?'Wlot silnika: brak geometrii i danych silnika do oceny.':'Śmigło i silnik: nie dotyczy.';
    if (chkClearEl) chkClearEl.textContent = 'Prześwit: wymaga wymiarów zabudowy i podwozia; nie został zweryfikowany.';
    // Puste pole = profil przyjęty w P2; wpisany profil trafia do parametrów projektu (data-analysis-param).
    const afNameEl = document.getElementById('airfoil');
    if (afNameEl) afNameEl.placeholder = bp.p2?.airfoil_selection?.selected_airfoil || 'np. NACA 23012';
    if (!airfoilProfile) {
      const afDescEl = document.getElementById('p3_airfoil_desc');
      if (afDescEl) afDescEl.textContent = p3.airfoil_coordinates_note;
      if (p3.airfoil_200mm_svg) renderAirfoil200mm({svg: p3.airfoil_200mm_svg, table: p3.airfoil_200mm_table, note: p3.airfoil_coordinates_note});
    }

    const t31Tbody = document.getElementById('p3_table31_tbody');
    if (t31Tbody && Array.isArray(p3.table_3_1_components)) {
      t31Tbody.innerHTML = p3.table_3_1_components.map(c => `
        <tr>
          <td>${escapeHtml(c.item)}</td>
          <td><b>${Number(c.mass_kg).toFixed(1)}</b></td>
          <td>${Number(c.x_m).toFixed(3)}</td>
          <td>${Number(c.y_m).toFixed(3)}</td>
          <td>${Number(c.z_m).toFixed(3)}</td>
        </tr>
      `).join('');
    }

    const loadTbody = document.getElementById('p3_loading_tbody');
    if (loadTbody && Array.isArray(p3.table_3_2_loading_states)) {
      loadTbody.innerHTML = p3.table_3_2_loading_states.map(st => {
        const ground = st.in_flight === false;
        const ok = st.cg_criterion_passed === true && st.minimum_margin_passed === true;
        const status = ground ? 'Stan naziemny' : (ok ? '✓ Kryteria P3 spełnione' : '⚠️ Kryteria P3 niespełnione');
        return `
          <tr>
            <td><b>${escapeHtml(st.name)}</b></td>
            <td>${Number(st.mass_kg).toFixed(1)}</td>
            <td>${Number(st.xcg_m).toFixed(3)}</td>
            <td><b>${Number(st.xcg_mac_pct).toFixed(1)}% ŚDA</b></td>
            <td><span class="badge ${ground ? '' : (ok ? 'badge-success' : 'badge-danger')}">${status}</span></td>
          </tr>
        `;
      }).join('');
    }

    const im = p3.inertia_moments || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    setTxt('p3_jx', im.jx_cg_kgm2);
    setTxt('p3_jy', im.jy_cg_kgm2);
    setTxt('p3_jz', im.jz_cg_kgm2);
    setTxt('p3_jy_steiner', im.jy_quarter_mac_kgm2);
    setTxt('p3_jz_steiner', im.jz_quarter_mac_kgm2);

    const iwa = p3.isolated_wing_aero || {};
    setTxt('p3_aw_deg', iwa.cz_alpha_deg);
    setTxt('p3_aw_paturski_rad', iwa.cz_alpha_paturski_rad);
    setTxt('p3_tau_glauert', iwa.tau_glauert);
    setTxt('p3_delta_glauert', iwa.delta_glauert);
    setTxt('p3_re1_stall', iwa.re_1_stall ? Number(iwa.re_1_stall).toLocaleString('pl-PL') : '—');
    setTxt('p3_cxmin2', iwa.cx_min_2_corrected);
    setTxt('p3_dcx_tech', iwa.delta_cx_tech);
    setTxt('p3_ca_paturski', iwa.ca_paturski_m);
    setTxt('p3_xn_paturski', iwa.xn_mac_m);
    setTxt('p3_cm0_wing', iwa.cm_0_wing);
    setTxt('p3_cx0_wing', iwa.cx_0_wing);
    setTxt('p3_czmax_wing', p3.schrenk_summary?.cz_max_wing_est);
  }

  // --- PROJEKT 4: CHARAKTERYSTYKI AERODYNAMICZNE ---
  if (bp.p4) {
    const p4 = bp.p4;
    const dragTbody = document.getElementById('p4_drag_tbody');
    if (dragTbody && Array.isArray(p4.drag_breakdown)) {
      dragTbody.innerHTML = p4.drag_breakdown.map(d => `
        <tr>
          <td><b>${escapeHtml(d.component)}</b></td>
          <td class="num">${d.re ? Number(d.re).toLocaleString('pl-PL') : '—'}</td>
          <td class="num">${d.cf ? Number(d.cf).toFixed(5) : '—'}</td>
          <td class="num">${d.ff ? Number(d.ff).toFixed(3) : '—'}</td>
          <td class="num">${d.q ? Number(d.q).toFixed(2) : '—'}</td>
          <td class="num">${d.swet_m2 ? Number(d.swet_m2).toFixed(2) : '—'}</td>
          <td class="num"><b>${Number(d.cx0_i || 0).toFixed(5)}</b></td>
          <td class="num">${d.share_pct}%</td>
        </tr>
      `).join('');
    }

    // Podsumowanie Projektu nr 3 Z. Paturskiego, Tabele A, B, C oraz Tabela 2.2
    const pa = p4.paturski_aero || {};
    const abc = pa.statistical_benchmarks_abc || {};
    const aeroSumEl = document.getElementById('p4_paturski_aero_summary');
    if (aeroSumEl && pa.analytical_polar_fit) {
      const af = pa.analytical_polar_fit;
      const ht = pa.horizontal_tail_trim || {};
      const fus = pa.fuselage || {};
      const sb = abc.summary || {};
      aeroSumEl.innerHTML = `
        <b>Metodyka Z. Paturskiego (Projekty nr 2 i 3 ML):</b>
        Kadłub: <code>S_k = ${fus.sk_frontal_m2} m²</code>, <code>S_ck = ${fus.sck_wetted_m2} m²</code>, <code>Λ_k = ${fus.lambda_k}</code>, <code>C_xk = ${fus.cx_k_frontal}</code> &bull;
        Usterzenie poziome (${ht.tail_airfoil || 'NACA 0012'}): <code>(V_H/V_∞)² = ${ht.vh_vinf_sq}</code>, <code>κ'_H = ${ht.kappa_h_prime}</code>, <code>Λ_eH = ${ht.lambda_eh}</code> &bull;
        Opór szkodliwy: <code>(C_x,szk)_min = ${pa.cx_szk_min}</code>, <code>ζ = ${pa.zeta_szk}</code>, interferencja <code>K_interf = ${pa.k_interf}</code> &bull;
        <b>Aproksymacja biegunowej analitycznej (wzór 3.11):</b> <code>C_x0 = ${af.cx0_approx}</code>, <code>ΔC_x/Δ(C_z²) = ${af.slope_d_cx_d_cz2}</code> &rArr; <b><code>Λ_e = ${af.lambda_e_approx}</code></b> (współczynnik Oswalda <b><code>e = ${af.oswald_e_approx}</code></b>).
        ${sb.matched_a_lp ? `<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px dashed #cbd5e1; color:#0f172a;">
          <strong>📊 Weryfikacja statystyczna wg Tabel A, B, C:</strong>
          Tabela A (Lp. ${sb.matched_a_lp}): <code>C_x,min = ${sb.matched_a_range}</code> vs. <strong>projekt: <code>C_x,min = ${sb.project_cx_min}</code></strong> &bull;
          Tabela B (Lp. ${sb.matched_b_lp}): <code>C_x,szk,min = ${sb.matched_b_cx_szk_min}</code> vs. <strong>projekt: <code>${sb.project_cx_szk_min}</code></strong> &bull;
          Wzorzec Tabeli C: <em>${sb.matched_c_archetype}</em>.
        </div>` : (sb.verdict_text ? `<div style="margin-top:0.4rem; padding-top:0.4rem; border-top:1px dashed #cbd5e1; color:#0f172a;">
          <strong>📊 Tabele A, B, C:</strong> ${sb.matched_c_archetype}. ${sb.verdict_text}
        </div>` : '')}
      `;
    }

    const tabCTbody = document.getElementById('p4_table_c_tbody');
    if (tabCTbody && Array.isArray(abc.tabela_c_rows)) {
      const colKey = abc.summary?.matched_c_col_key || '';
      tabCTbody.innerHTML = abc.tabela_c_rows.map(r => `
        <tr>
          <td>${r.lp}</td>
          <td><b>${r.component}</b></td>
          <td class="num" style="${colKey === 'biplane_fixed_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.biplane_fixed_pct !== null ? r.biplane_fixed_pct + ' %' : '&ndash;'}</td>
          <td class="num" style="${colKey === 'high_wing_braced_fixed_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.high_wing_braced_fixed_pct !== null ? r.high_wing_braced_fixed_pct + ' %' : '&ndash;'}</td>
          <td class="num" style="${colKey === 'low_wing_retractable_pct' ? 'background:#eff6ff;font-weight:700;' : ''}">${r.low_wing_retractable_pct !== null ? r.low_wing_retractable_pct + ' %' : '&ndash;'}</td>
          <td class="num"><code>${Number(r.project_delta_cx).toFixed(4)}</code></td>
          <td class="num" style="background:#f0fdf4; font-weight:800; color:#065f46;">${Number(r.project_share_pct).toFixed(1)} %</td>
        </tr>
      `).join('');
    }

    const tabATbody = document.getElementById('p4_table_a_tbody');
    if (tabATbody && Array.isArray(abc.tabela_a_rows)) {
      tabATbody.innerHTML = abc.tabela_a_rows.map(r => `
        <tr style="${r.is_matched ? 'background:#ecfdf5; font-weight:700;' : ''}">
          <td>${r.lp}</td>
          <td>${r.class_desc} ${r.is_matched ? '<span class="badge badge-success" style="font-size:0.68rem;">Twój samolot</span>' : ''}</td>
          <td class="num"><code>${r.cx_min_range}</code></td>
        </tr>
      `).join('');
    }

    const tabBTbody = document.getElementById('p4_table_b_tbody');
    if (tabBTbody && Array.isArray(abc.tabela_b_rows)) {
      tabBTbody.innerHTML = abc.tabela_b_rows.map(r => `
        <tr style="${r.is_matched ? 'background:#ecfdf5; font-weight:700;' : ''}">
          <td>${r.lp}</td>
          <td>${r.class_desc} ${r.is_matched ? '<span class="badge badge-success" style="font-size:0.68rem;">Twój samolot</span>' : ''}</td>
          <td class="num"><code>${Number(r.cx_szk_min).toFixed(3)}</code></td>
        </tr>
      `).join('');
    }

    const t22Tbody = document.getElementById('p4_table22_tbody');
    if (t22Tbody && Array.isArray(pa.table_2_2_complete)) {
      t22Tbody.innerHTML = pa.table_2_2_complete.map(r => `
        <tr>
          <td>${r.lp}</td>
          <td><b>${r.cz_inf}</b></td>
          <td>${r.cx_inf}</td>
          <td>${r.alpha_inf_deg}°</td>
          <td>${r.cx_inf_prime}</td>
          <td>${r.alpha_i_deg}°</td>
          <td>${r.alpha_p_deg}°</td>
          <td>${r.cx_i}</td>
          <td>${r.cx_p_prime}</td>
          <td>${r.cz_h}</td>
          <td>${r.cx_h}</td>
          <td>${r.cx_szk_prime}</td>
          <td><b>${r.cx_total}</b></td>
          <td>${r.delta_cz_h}</td>
          <td><b>${r.cz_prime}</b></td>
          <td><b>${r.k_ld}</b></td>
          <td><b>${r.e_energy}</b></td>
        </tr>
      `).join('');
    }

    const gp = p4.glide_polar || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    const fmtNum = (v, d) => (v === null || v === undefined || v === '' || !Number.isFinite(Number(v))) ? v : Number(v).toFixed(d);
    setTxt('p4_vekon', fmtNum(gp.v_ekon_kmh, 1));
    setTxt('p4_wmin', fmtNum(gp.w_min_ms, 2));
    setTxt('p4_vopt', fmtNum(gp.v_opt_kmh, 1));
    setTxt('p4_kmax', fmtNum(gp.k_max, 2));

    const gCompEl = document.getElementById('p4_glide_comparison_box');
    if (gCompEl && gp.comparison_paturski) {
      const ex = gp.comparison_paturski.exact_from_table_4_1 || {};
      const an = gp.comparison_paturski.analytical_eq_4_8_to_4_11 || {};
      const ms = gp.comparison_paturski.masses_kg || {};
      gCompEl.innerHTML = `
        <b>Porównanie metod lotu szybowego wg Z. Paturskiego (Projekt nr 4, wzory 4.3–4.12 dla m₁ = ${ms.m1_mtow} kg):</b><br>
        &bull; <b>Metoda dokładna (Tabela 4.1):</b> <code>V_opt = ${ex.v_opt_kmh} km/h</code>, <code>w_opt = ${ex.w_opt_ms} m/s</code> (<code>γ_min = ${ex.gamma_min_deg}°</code>) | <code>V_ek = ${ex.v_ek_kmh} km/h</code>, <code>w_ek = ${ex.w_ek_ms} m/s</code>.<br>
        &bull; <b>Metoda przybliżona analityczna (wzory 4.8–4.12):</b> <code>V_opt = ${an.v_opt_kmh} km/h</code>, <code>w_opt = ${an.w_opt_ms} m/s</code> | <code>V_ek = ${an.v_ek_kmh} km/h</code>, <code>w_ek = ${an.w_ek_ms} m/s</code>
        (relacje teoretyczne: <code>V_opt/V_ek = ${an.ratio_v_opt_v_ek} = 3^(1/4)</code>, <code>w_opt/w_ek = ${an.ratio_w_opt_w_ek}</code>).
      `;
    }

    const t41Tbody = document.getElementById('p4_table41_tbody');
    if (t41Tbody && Array.isArray(gp.table_4_1_paturski)) {
      t41Tbody.innerHTML = gp.table_4_1_paturski.map(r => `
        <tr>
          <td><b>${r.cz}</b></td>
          <td>${r.cx}</td>
          <td>${r.term_v}</td>
          <td>${r.term_w}</td>
          <td>${r.gamma_deg}°</td>
          <td><b>${r.v1_kmh}</b></td>
          <td><b>${r.w1_ms}</b></td>
          <td>${r.v2_kmh}</td>
          <td>${r.w2_ms}</td>
          <td>${r.v3_kmh}</td>
          <td>${r.w3_ms}</td>
        </tr>
      `).join('');
    }

    const hl = p4.high_lift;
    const hlTbody = document.getElementById('p4_high_lift_tbody');
    if (hlTbody && hl) {
      const stallCheck = hl.stall_requirement;
      const stallLabel = stallCheck
        ? `${stallCheck.passed ? '✓ Wymaganie projektu spełnione' : '⚠️ Wymaganie projektu niespełnione'} (≤ ${Number(stallCheck.limit_kmh).toFixed(2)} km/h EAS przy MTOW)`
        : 'Brak oceny wymagania projektu';
      const stallNote = document.getElementById('p4_stall_requirement_note');
      if (stallNote) stallNote.textContent = stallCheck?.note || '';
      hlTbody.innerHTML = `
        <tr>
          <td><b>Gładka (Clean)</b></td>
          <td>${Number(hl.clean.cz_max).toFixed(3)}</td>
          <td>${hl.clean.vs_kmh} km/h EAS</td>
          <td>—</td>
          <td>Konfiguracja przelotowa</td>
        </tr>
        <tr>
          <td><b>Startowa — klapy ${hl.takeoff.flap_deflection_deg}°</b></td>
          <td>${Number(hl.takeoff.cz_max).toFixed(3)}</td>
          <td>${hl.takeoff.vs_kmh} km/h EAS</td>
          <td>+${hl.takeoff.delta_cz}</td>
          <td>Konfiguracja startowa</td>
        </tr>
        <tr>
          <td><b>Do lądowania — klapy ${hl.landing.flap_deflection_deg}°</b></td>
          <td><b>${Number(hl.landing.cz_max).toFixed(3)}</b></td>
          <td><b>${stallCheck ? Number(stallCheck.actual_kmh).toFixed(3) : hl.landing.vs_kmh} km/h EAS</b></td>
          <td>+${hl.landing.delta_cz}</td>
          <td><span class="badge ${stallCheck ? (stallCheck.passed ? 'badge-success' : 'badge-danger') : 'badge-info'}">${stallLabel}</span></td>
        </tr>
      `;
    }

    const csTbody = document.getElementById('p4_control_surfaces_tbody');
    if (csTbody && res.geometry && res.geometry.control_surfaces) {
      const cs = res.geometry.control_surfaces;
      const f = cs.flaps;
      const a = cs.ailerons;
      const dCz = (res.aerodynamics?.cz_max_lnd - res.aerodynamics?.cz_max_clean).toFixed(2);
      csTbody.innerHTML = `
        <tr>
          <td><b>Klapy wysklepiające (wewnętrzne)</b></td>
          <td>${escapeHtml(f.name)}</td>
          <td>${f.b_f_m} m</td>
          <td>${(f.bf_over_b * 100).toFixed(1)}% rozpiętości</td>
          <td>${(f.cf_over_c * 100).toFixed(0)}% cięciwy</td>
          <td>${f.S_flap_surface_m2} m² (${(f.s_flapped_over_s * 100).toFixed(1)}% S_flapped)</td>
          <td>&Delta;Cz_max = +${dCz}</td>
          <td><span class="badge badge-info">Oszacowanie przyrostu nośności</span></td>
        </tr>
        <tr>
          <td><b>Lotki sterowania poprzecznego (zewnętrzne)</b></td>
          <td>${escapeHtml(a.name)}</td>
          <td>${a.b_a_m} m</td>
          <td>${(a.ba_over_b * 100).toFixed(1)}% rozpiętości</td>
          <td>${(a.ca_over_c * 100).toFixed(0)}% cięciwy</td>
          <td>${a.S_aileron_surface_m2} m² (${(a.s_aileron_over_s * 100).toFixed(1)}% S)</td>
          <td>pb/(2V) = ${a.roll_helix_pb_2v} (kąt spiralny)</td>
          <td><span class="badge ${a.roll_authority_ok ? 'badge-success' : 'badge-warning'}">${a.roll_authority_ok ? `✓ Kryterium wstępne spełnione (&ge; ${a.min_pb_2v_req})` : `⚠️ Poniżej kryterium wstępnego ${a.min_pb_2v_req}`}</span></td>
        </tr>
        <tr>
          <td colspan="8" style="background:#f8fafc; font-size:0.8rem; color:#1e293b;">
            <strong>Wstępna ocena rozkładu Schrenka:</strong> ${escapeHtml(cs.stall_safety.verdict)}
          </td>
        </tr>
      `;
    }

    const p4PropTitle = document.getElementById('p4_propulsion_title');
    const p4PropDesc = document.getElementById('p4_propulsion_desc');
    const p4PropBox = document.getElementById('p4_paturski_propulsion_box');
    const pp5 = p4.paturski_propulsion || {};
    const rawSfcVal = parseFloat(document.getElementById('sfc')?.value || (isJet ? '0.62' : '265'));
    if (isJet) {
      const tsfcDisp = (rawSfcVal > 5.0 || rawSfcVal <= 0.05) ? 0.62 : rawSfcVal;
      const t0Kn = res?.sizing?.design_point?.thrust_kn ?? pp5.pr0_total_kn ?? '';
      if (p4PropTitle) p4PropTitle.textContent = '4.4. Charakterystyka Zespołu Napędowego (Silnik Odrzutowy — Tabela 5-3 Z. Paturskiego)';
      if (p4PropDesc) {
        p4PropDesc.innerHTML = `Zależność ciągu rozporządzalnego wg wzorów (5.18)–(5.20) Z. Paturskiego: <b>P_r*(h) = P_r0 · (ρ/ρ₀)^0.85</b>, <b>P_r(Ma, h) = P_r*(h) · (1 − K_P · Ma)</b> (ciąg statyczny <b>P_r0 = ${t0Kn} kN</b>, <b>K_P = ${pp5.kp_bypass_factor ?? 0.45}</b>) oraz jednostkowe zużycie paliwa <b>q_e (TSFC) = <span id="p4_sfc_val">${tsfcDisp} 1/h</span></b>.`;
      }
      if (p4PropBox && Array.isArray(pp5.table_5_3_jet)) {
        p4PropBox.innerHTML = `
          <div style="font-weight:700; color:#005691; font-size:0.82rem; margin-bottom:0.3rem;">Tabela 5-3 (Z. Paturski): Charakterystyki prędkościowo-wysokościowe zespołu napędowego Pr(Ma, h) [kN]:</div>
          <table class="b-table" style="font-size:0.78rem;">
            <thead>
              <tr><th>Liczba Macha Ma</th><th>h = 0 km</th><th>h = 2 km</th><th>h = 4 km</th><th>h = 6 km</th><th>h = 8 km</th><th>h = 10 km</th><th>h = 12 km</th></tr>
            </thead>
            <tbody>
              ${pp5.table_5_3_jet.map(r => `
                <tr>
                  <td><b>Ma = ${r.mach.toFixed(1)}</b></td>
                  <td><b>${r.h_0km_kn} kN</b></td>
                  <td>${r.h_2km_kn} kN</td>
                  <td>${r.h_4km_kn} kN</td>
                  <td>${r.h_6km_kn} kN</td>
                  <td>${r.h_8km_kn} kN</td>
                  <td>${r.h_10km_kn} kN</td>
                  <td>${r.h_12km_kn} kN</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }
    } else {
      const sfcDisp = rawSfcVal <= 2.0 ? Math.round(rawSfcVal * 1000) : Math.round(rawSfcVal);
      const etaDisp = document.getElementById('prop_efficiency')?.value || '0.82';
      const psel = pp5.propeller_selection || {};
      if (p4PropTitle) p4PropTitle.textContent = '4.4. Dobór Śmigła i Charakterystyka Zespołu Napędowego (Tabela 5-1 / 5-2 Z. Paturskiego)';
      if (p4PropDesc) {
        p4PropDesc.innerHTML = `Dobór śmigła wg Z. Paturskiego (wzory 5.1–5.5): cecha bezśrednicowa <b>C_D = ${psel.cd_dimensionless ?? '—'}</b>, posuw optymalny <b>J_opt = ${psel.j_opt ?? '—'}</b>, średnica śmigła <b>D = ${psel.diameter_m ?? '—'} m</b> (przy <b>n_s = ${psel.rpm_prop ?? 2400} obr/min</b>), liczba Macha końcówki łopaty <b>Ma_kl = ${psel.ma_tip_kl ?? '—'} ≤ 0.85</b>, sprawność max <b>η_s = <span id="p4_eta_prop">${etaDisp}</span></b>, jednostkowe zużycie paliwa <b>q_e = <span id="p4_sfc_val">${sfcDisp} g/(kW·h) (${(sfcDisp / 1000).toFixed(3)} kg/(kW·h))</span></b>.`;
      }
      if (p4PropBox && Array.isArray(pp5.table_5_1_variable_pitch)) {
        p4PropBox.innerHTML = `
          <div style="font-weight:700; color:#005691; font-size:0.82rem; margin-bottom:0.3rem;">Tabela 5-1 / 5-2 (Z. Paturski): Charakterystyka prędkościowa śmigła przestawialnego i stałego na h = 0 m:</div>
          <table class="b-table" style="font-size:0.78rem;">
            <thead>
              <tr>
                <th>L.p.</th><th>V [m/s]</th><th>V [km/h]</th><th>Posuw J = V/(n_s·D)</th>
                <th>Kąt łopat β_s [°]</th><th>η_s (przestawialne)</th><th>N_r [kW] (przestawialne)</th>
                <th>Obroty n_s [obr/min] (stałe)</th><th>N_r [kW] (śmigło stałe)</th>
              </tr>
            </thead>
            <tbody>
              ${pp5.table_5_1_variable_pitch.map((r, i) => {
                const fx = (pp5.table_5_2_fixed_pitch || [])[i] || {};
                return `
                  <tr>
                    <td>${r.lp}</td>
                    <td>${r.v_ms}</td>
                    <td><b>${r.v_kmh}</b></td>
                    <td>${r.j_advance}</td>
                    <td>${r.beta_s_deg}°</td>
                    <td>${r.eta_s}</td>
                    <td><b>${r.nr_kw} kW</b></td>
                    <td>${fx.rpm ?? '—'} ${fx.throttled ? '<span class="badge badge-warning" style="font-size:0.65rem;">dławiony n_max</span>' : ''}</td>
                    <td>${fx.nr_kw ?? '—'} kW</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        `;
      }
    }
  }

  // --- PROJEKT 5: OSIĄGI SAMOLOTU ---
  if (bp.p5) {
    const p5 = bp.p5;
    const cs = p5.ceiling_summary || {};
    const p6ml = p5.paturski_p6 || {};
    const li = p6ml.load_indicators_eq_6_1 || {};
    const ceilBanner = document.getElementById('p5_paturski_ceiling_banner');
    if (ceilBanner) {
      const indStr = li.q_pr_kg_kn != null
        ? `Wskaźnik obciążenia ciągu (wzór 6.1): <b>q_Pr = ${li.q_pr_kg_kn} kg/kN</b> ${li.power_method_valid ? '(≥ 300 kg/kN — metoda mocy dokładna)' : '(< 300 kg/kN — samolot o dużym nadmiarze ciągu)'}`
        : `Wskaźnik obciążenia mocy (wzór 6.1): <b>q_N = ${li.q_n_kg_kw} kg/kW</b> ${li.power_method_valid ? '(≥ 6 kg/kW — metoda mocy dokładna)' : '(< 6 kg/kW — samolot o dużym nadmiarze mocy)'}`;
      ceilBanner.innerHTML = `
        ${indStr} &bull;
        Pułap praktyczny (w_max = 0.5 m/s): <b>h_p = ${cs.hp_service_m ?? '—'} m</b> &bull;
        Pułap teoretyczny (w_max = 0): <b>h_t = ${cs.ht_theoretical_m ?? '—'} m</b> &bull;
        Czas wznoszenia na pułap praktyczny (całkowanie dh/w_y,max przy stałej masie): <b>t_hp = ${cs.thp_min ?? '—'} min (${cs.thp_s ?? '—'} s)</b>.
      `;
    }

    const offerTbody = document.getElementById('p5_offer_tbody');
    if (offerTbody && Array.isArray(p5.offer_chart)) {
      offerTbody.innerHTML = p5.offer_chart.map(r => `
        <tr>
          <td><b>${r.h_m} m</b></td>
          <td>${r.v_min_kmh}</td>
          <td><b>${r.v_max_kmh}</b></td>
          <td><b>${r.wy_max_ms}</b></td>
          <td>${r.v_wy_kmh}</td>
          <td>${r.gamma_max_deg}°</td>
          <td>${r.v_gamma_kmh ?? r.v_wy_kmh}</td>
          <td>${r.inv_wy_sm != null ? r.inv_wy_sm : '—'}</td>
          <td>${r.time_to_climb_min != null ? `${r.time_to_climb_min} min (${r.time_to_climb_s ?? Math.round(r.time_to_climb_min * 60)} s)` : '—'}</td>
        </tr>
      `).join('');
    }

    const rngTbody = document.getElementById('p5_range_tbody');
    if (rngTbody && Array.isArray(p5.range_endurance_comparison)) {
      rngTbody.innerHTML = p5.range_endurance_comparison.map(m => `
        <tr>
          <td>${escapeHtml(m.method)}</td>
          <td><b>${m.range_km == null ? '—' : `${Number(m.range_km).toFixed(1)} km`}</b></td>
          <td><b>${m.endurance_h == null ? '—' : `${Number(m.endurance_h).toFixed(2)} h`}</b></td>
        </tr>
      `).join('');
    }

    const re65 = p6ml.range_endurance_6_5 || {};
    const rngSumEl = document.getElementById('p5_paturski_range_summary');
    if (rngSumEl && re65.optimization?.available) {
      rngSumEl.innerHTML = `
        <b>Optima stałego TAS i wysokości H = ${re65.h_cruise_m} m dla paliwa pierwszego odcinka przelotu ${re65.mp_cruise_fuel_kg} kg:</b><br>
        &bull; Największa długotrwałość: <b>T_max = ${Number(re65.t_max_h).toFixed(3)} h</b> przy <b>V_T = ${Number(re65.v_t_max_kmh).toFixed(1)} km/h TAS</b> &bull;
        Największy zasięg: <b>L_max = ${Number(re65.l_max_km).toFixed(1)} km</b> przy <b>V_L = ${Number(re65.v_l_max_kmh).toFixed(1)} km/h TAS</b>.<br>
        ${escapeHtml(re65.optimization.basis)} Tabela 6.3 poniżej porównuje także idealne modele Bregueta.
      `;
    } else if (rngSumEl) {
      rngSumEl.textContent = isGlider ? 'Paliwowe optima zasięgu i długotrwałości nie dotyczą szybowca.'
        : 'Nie wyznaczono optimum: brak paliwa przelotowego lub osiągalnego lotu poziomego na tej wysokości.';
    }
    const t63EnergyTh = document.getElementById('p5_t63_col_energy');
    if (t63EnergyTh) {
      t63EnergyTh.textContent = isJet ? 'Cz^(1/2)/Cx' : 'Cz^(3/2)/Cx';
    }
    const t63Tbody = document.getElementById('p5_table63_tbody');
    if (t63Tbody && Array.isArray(re65.table_6_3)) {
      t63Tbody.innerHTML = re65.table_6_3.map(r => `
        <tr>
          <td>${r.lp}</td>
          <td><b>${r.cz}</b></td>
          <td>${r.cx}</td>
          <td>${isJet ? r.cz12_cx : r.cz32_cx}</td>
          <td>${r.cz_cx}</td>
          <td><b>${r.v_kmh}</b></td>
          <td><b>${r.t_breguet_h} h</b></td>
          <td><b>${r.l_breguet_km} km</b></td>
          <td>${r.t_const_v_h} h</td>
          <td>${r.l_const_v_km} km</td>
        </tr>
      `).join('');
    }

    const tl = p5.takeoff_landing || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.textContent = val;
    };
    setTxt('p5_sto_ground', tl.ground_roll_m==null?'Nieosiągalny':`${tl.ground_roll_m} m`);
    setTxt('p5_sto_15m', tl.takeoff_to_15m_m==null?'Nieosiągalny':`${tl.takeoff_to_15m_m} m`);
    setTxt('p5_slnd_ground', `${tl.landing_ground_roll_m} m`);
    setTxt('p5_slnd_15m', `${tl.landing_from_15m_m} m`);

    const critTbody = document.getElementById('p5_critical_tbody');
    if (critTbody && Array.isArray(p5.critical_evaluation_table_5_1)) {
      const fmtCell = v => (typeof v === 'number' && !Number.isInteger(v)) ? (Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(3).replace(/\.?0+$/, '')) : v;
      critTbody.innerHTML = p5.critical_evaluation_table_5_1.map(c => `
        <tr>
          <td><b>${escapeHtml(c.param)}</b></td>
          <td>${fmtCell(c.project_assumed) ?? '—'}</td>
          <td><b>${fmtCell(c.actual_calc) ?? '—'}</b></td>
          <td>${escapeHtml(c.comment)}</td>
        </tr>
      `).join('');
    }
  }

  // --- PROJEKT 6: OBWIEDNIA OBCIĄŻEŃ DOPUSZCZALNYCH ---
  if (bp.p6) {
    const p6 = bp.p6;
    const ptsTbody = document.getElementById('p6_points_tbody');
    if (ptsTbody && Array.isArray(p6.points_table)) {
      ptsTbody.innerHTML = p6.points_table.map(pt => `
        <tr>
          <td><b>${escapeHtml(pt.point)}</b></td>
          <td>${pt.v_kmh} km/h</td>
          <td><b>${pt.n}</b></td>
          <td>${escapeHtml(pt.type)}</td>
        </tr>
      `).join('');
    }

    const vfEl = document.getElementById('p6_vf_val');
    if (vfEl && p6.v_f_kmh != null) vfEl.textContent = p6.v_f_kmh;

    const flapLoopTbody = document.getElementById('p6_flap_loop_tbody');
    if (flapLoopTbody && Array.isArray(p6.flap_envelope_loop)) {
      flapLoopTbody.innerHTML = p6.flap_envelope_loop.map(fl => `
        <tr>
          <td><b>${escapeHtml(fl.point)}</b></td>
          <td>${fl.v_kmh} km/h</td>
          <td><b>${fl.n}</b></td>
        </tr>
      `).join('');
    }
  }

  // Jeśli aktualnie jesteśmy w trybie Projektów Semestralnych, przerysuj aktywny wykres
  if (currentPortalMode === 'projects') {
    renderSemesterProjectCharts(currentSemesterProject, res);
  }
}

// Profil o cięciwie 200 mm: NACA liczony analitycznie albo rzędne wklejone z katalogu; SVG ma wymiary w mm.
let airfoilProfile = null;

function renderAirfoil200mm(data) {
  const fmtMm = v => v == null ? '' : Number(v).toFixed(2).replace('.', ',');
  const afDescEl = document.getElementById('p3_airfoil_desc');
  if (afDescEl) {
    afDescEl.classList.remove('airfoil-error');
    afDescEl.textContent = data.thickness_pct
      ? `${data.note} Grubość względna: ${String(data.thickness_pct).replace('.', ',')}% przy ${String(data.thickness_x_pct).replace('.', ',')}% cięciwy.`
      : data.note;
  }
  const afSvgEl = document.getElementById('p3_airfoil_svg_container');
  if (afSvgEl) afSvgEl.innerHTML = data.svg || '';
  const coordsTbody = document.getElementById('p3_airfoil_coords_tbody');
  if (coordsTbody && Array.isArray(data.table)) {
    coordsTbody.innerHTML = data.table.map(pt => `<tr><td>${pt.xc_pct == null ? '' : String(pt.xc_pct).replace('.', ',')}</td>`
      + `<td><b>${fmtMm(pt.xu_mm)}</b></td><td>${fmtMm(pt.yu_mm)}</td><td><b>${fmtMm(pt.xl_mm)}</b></td><td>${fmtMm(pt.yl_mm)}</td><td>${fmtMm(pt.thick_mm)}</td></tr>`).join('');
  }
  ['btn_print_airfoil', 'btn_download_airfoil'].forEach(id => { const el = document.getElementById(id); if (el) el.disabled = !data.svg; });
}

async function fetchAirfoil200mm(fromPaste = false) {
  const btn = document.getElementById('btn_fetch_airfoil');
  const typed = (document.getElementById('airfoil')?.value || '').trim();
  const name = typed || currentResults?.bipol_projects?.p2?.airfoil_selection?.selected_airfoil || '';
  const pasted = document.getElementById('airfoil_coordinates')?.value || '';
  const coordinates = fromPaste ? pasted : '';
  if (btn) btn.disabled = true;
  try {
    const res = coordinates.trim()
      ? await fetch('/api/airfoil/200mm', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({airfoil: name, coordinates})})
      : await fetch(`/api/airfoil/200mm?airfoil=${encodeURIComponent(name)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Nie udało się wyznaczyć rzędnych profilu.');
    airfoilProfile = data;
    renderAirfoil200mm(data);
    // Nowy profil zapisuje się w projekcie i trafia do P2, P3 i raportów po przeliczeniu.
    const saved = currentResults?.params || {};
    if ((typed !== (saved.airfoil || '').trim() || pasted !== (saved.airfoil_coordinates || '')) && typeof performCalculation === 'function') performCalculation();
    const box = document.getElementById('airfoilCoordsBox');
    if (box) box.style.display = 'block';
  } catch (err) {
    const afDescEl = document.getElementById('p3_airfoil_desc');
    if (afDescEl) { afDescEl.textContent = err.message; afDescEl.classList.add('airfoil-error'); }
  } finally {
    if (btn) btn.disabled = false;
  }
}

function printAirfoil200mm() {
  const svg = document.querySelector('#p3_airfoil_svg_container svg');
  if (!svg) return;
  const win = window.open('', '_blank');
  if (!win) return;
  win.document.write(`<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>${escapeHtml(svg.getAttribute('aria-label') || 'Profil 200 mm')}</title>`
    + '<style>@page{size:A4 landscape;margin:12mm}body{margin:0;font:12px sans-serif}svg{display:block}</style></head><body>'
    + `${svg.outerHTML}<p>Drukuj w skali 100% (bez „dopasuj do strony”). Odcinek kontrolny ma mieć 100 mm.</p></body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

function downloadAirfoilSvg() {
  const svg = document.querySelector('#p3_airfoil_svg_container svg');
  if (!svg) return;
  const url = URL.createObjectURL(new Blob([svg.outerHTML], {type: 'image/svg+xml'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${(airfoilProfile?.airfoil || 'profil').replace(/[^\p{L}\p{N}_-]+/gu, '_')}_200mm.svg`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function toggleAirfoilCoordsTable() {
  const box = document.getElementById('airfoilCoordsBox');
  if (!box) return;
  const isHidden = (box.style.display === 'none' || box.style.display === '');
  box.style.display = isHidden ? 'block' : 'none';
  if (isHidden) {
    const tbody = document.getElementById('p3_airfoil_coords_tbody');
    if (tbody && tbody.children.length === 0) {
      fetchAirfoil200mm();
    }
  }
}

function toggleMassTable31() {
  const box = document.getElementById('massTable31Box');
  if (!box) return;
  box.style.display = (box.style.display === 'none' || box.style.display === '') ? 'block' : 'none';
}

function syncStudentDesignerFields(source) {
  let s = '';
  let a = '';
  let g = '';
  let p = '';
  let d = '';
  let y = '';

  if (source === 'workstation') {
    s = document.getElementById('ws_student_name')?.value ?? s;
    a = document.getElementById('ws_album_no')?.value ?? a;
    g = document.getElementById('ws_group_no')?.value ?? g;
    p = document.getElementById('ws_supervisor')?.value ?? p;
    d = document.getElementById('ws_submission_date')?.value ?? d;
    y = document.getElementById('ws_academic_year')?.value ?? y;
  } else if (source === 'wizard') {
    s = document.getElementById('wiz_student_name')?.value ?? s;
    a = document.getElementById('wiz_album_no')?.value ?? a;
    g = document.getElementById('wiz_group_no')?.value ?? g;
    p = document.getElementById('wiz_supervisor')?.value ?? p;
    d = document.getElementById('submission_date')?.value ?? d;
    y = document.getElementById('academic_year')?.value ?? y;
  } else {
    s = document.getElementById('student_name')?.value ?? s;
    a = document.getElementById('album_no')?.value ?? a;
    g = document.getElementById('group_no')?.value ?? g;
    p = document.getElementById('supervisor')?.value ?? p;
    d = document.getElementById('submission_date')?.value ?? d;
    y = document.getElementById('academic_year')?.value ?? y;
  }

  const setVal = (id, v) => {
    const el = document.getElementById(id);
    if (el && el.value !== v) el.value = v;
  };
  setVal('student_name', s);
  setVal('album_no', a);
  setVal('group_no', g);
  setVal('supervisor', p);
  setVal('submission_date', d);
  setVal('academic_year', y);

  setVal('ws_student_name', s);
  setVal('ws_album_no', a);
  setVal('ws_group_no', g);
  setVal('ws_supervisor', p);
  setVal('ws_submission_date', d);
  setVal('ws_academic_year', y);

  setVal('wiz_student_name', s);
  setVal('wiz_album_no', a);
  setVal('wiz_group_no', g);
  setVal('wiz_supervisor', p);

  const setTxt = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.textContent = v;
  };
  setTxt('prev_r2_student', s);
  setTxt('prev_r2_album', a);
  setTxt('prev_r2_group', g);
  setTxt('prev_r2_supervisor', p);
  setTxt('prev_r2_date', d);

  setTxt('prev_r1_student', s);
  setTxt('prev_r1_album', a);
  setTxt('prev_r1_year', y);

  const activeProj = typeof getActiveProject === 'function' ? getActiveProject() : null;
  if (activeProj?.name) {
    setTxt('prev_r1_project', activeProj.name);
  }

  const pillMod0 = document.getElementById('pill_mod0');
  if (pillMod0) {
    pillMod0.textContent = `${s.split(' ').slice(-1)[0] || 'Student'} • ${a}`;
  }

  try {
    localStorage.setItem('bipol_student_designer_info', JSON.stringify({
      student_name: s,
      album_no: a,
      group_no: g,
      supervisor: p,
      submission_date: d,
      academic_year: y
    }));
  } catch (e) {}
}

window.addEventListener('DOMContentLoaded', () => {
  try {
    const saved = JSON.parse(localStorage.getItem('bipol_student_designer_info') || 'null');
    if (saved) {
      const setVal = (id, v) => {
        const el = document.getElementById(id);
        if (el && v) el.value = v;
      };
      setVal('student_name', saved.student_name);
      setVal('album_no', saved.album_no);
      setVal('group_no', saved.group_no);
      setVal('supervisor', saved.supervisor);
      setVal('submission_date', saved.submission_date);
      setVal('academic_year', saved.academic_year);
      syncStudentDesignerFields('sidebar');
    }
  } catch (e) {}
});

function openIndividualProjectReport(pId) {
  const presetKey = 'custom';
  const currentParams = { ...((currentResults && currentResults.params) || collectFormData()) };
  const activeProj = getActiveProject();
  if (activeProj && activeProj.name) currentParams.name = activeProj.name;
  try {
    localStorage.setItem('bipol_custom_report_data', JSON.stringify({
      res: currentResults,
      params: currentParams
    }));
  } catch (e) {}
  const q = new URLSearchParams({
    preset: presetKey,
    student: currentParams.student_name || '',
    album: currentParams.album_no || '',
    group: currentParams.group_no || '',
    supervisor: currentParams.supervisor || '',
    date: currentParams.submission_date || '',
    academic_year: currentParams.academic_year || '',
    params_json: JSON.stringify(currentParams)
  });
  const url = `/report/project/${encodeURIComponent(pId)}?${q.toString()}`;
  window.open(url, '_blank');
}

function openFolderCoverReport() {
  openIndividualProjectReport('folder_cover');
}

// Udostępnij funkcje globalnie dla atrybutów onclick w HTML
window.setPortalMode = setPortalMode;
window.selectSemesterProject = selectSemesterProject;
window.updateSemesterScores = updateSemesterScores;
window.toggleAirfoilCoordsTable = toggleAirfoilCoordsTable;
window.fetchAirfoil200mm = fetchAirfoil200mm;
window.printAirfoil200mm = printAirfoil200mm;
window.downloadAirfoilSvg = downloadAirfoilSvg;
window.toggleMassTable31 = toggleMassTable31;
window.openIndividualProjectReport = openIndividualProjectReport;
window.openFolderCoverReport = openFolderCoverReport;
window.syncStudentDesignerFields = syncStudentDesignerFields;



document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('designForm');
  const markChanged = () => {
    showCalculationStatus('Parametry zostały zmienione. Oblicz projekt, aby zapisać je i odświeżyć wyniki.');
    document.getElementById('openReportBtn')?.setAttribute('data-results-stale', 'true');
    const status = document.getElementById('projectAutoSaveStatus');
    if (status) { status.textContent = 'Zmiany oczekują na obliczenie i zapis'; status.style.color = '#92400e'; }
  };
  form?.addEventListener('input', markChanged, true);
  form?.addEventListener('change', markChanged, true);
  form?.addEventListener('submit', event => { event.preventDefault(); performCalculation(); });
  document.getElementById('openReportBtn')?.addEventListener('click', event => {
    if (event.currentTarget.getAttribute('aria-disabled') === 'true') event.preventDefault();
  });
  document.querySelectorAll('.semester-project-pill, .wizard-step-tab, .module-header').forEach(el => {
    el.tabIndex = 0;
    el.setAttribute('role', 'button');
    el.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); el.click(); }
    });
  });
  document.querySelectorAll('.project-modal-backdrop, .wizard-backdrop').forEach(dialog => {
    const heading = dialog.querySelector('h3');
    if (heading) { heading.id ||= `${dialog.id}-title`; dialog.setAttribute('aria-labelledby', heading.id); }
    let previousFocus = null;
    new MutationObserver(() => {
      if (dialog.classList.contains('active')) {
        previousFocus = document.activeElement;
        dialog.querySelector('button, input, select')?.focus();
      } else if (previousFocus?.isConnected) previousFocus.focus();
    }).observe(dialog, { attributes: true, attributeFilter: ['aria-hidden'] });
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const controls = [...dialog.querySelectorAll('button, input, select, a[href], [tabindex="0"]')]
        .filter(el => !el.disabled && el.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    });
  });
});
