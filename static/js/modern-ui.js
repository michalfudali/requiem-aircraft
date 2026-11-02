/**
 * BiPOL Requiem - Modern UI, Theme Engine & Command Palette
 * Wydział MEiL PW - Zakład Samolotów i Śmigłowców
 */

(function () {
  'use strict';

  const STORAGE_THEME_KEY = 'bipol_theme';

  /* ------------------------------------------------------------------------
     1. THEME MANAGER
     ------------------------------------------------------------------------ */
  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function getSavedTheme() {
    try {
      const saved = localStorage.getItem(STORAGE_THEME_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (_) {}
    return getSystemTheme();
  }

  function applyTheme(theme, save = true) {
    const isDark = theme === 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);

    if (save) {
      try {
        localStorage.setItem(STORAGE_THEME_KEY, theme);
      } catch (_) {}
    }

    // Update toggle buttons
    document.querySelectorAll('#themeToggleBtn, [data-theme-toggle]').forEach(btn => {
      btn.innerHTML = isDark ? '☀️' : '🌙';
      btn.setAttribute('aria-label', isDark ? 'Przełącz na tryb jasny (Alt+T)' : 'Przełącz na tryb ciemny (Alt+T)');
      btn.setAttribute('title', isDark ? 'Przełącz na tryb jasny (Alt+T)' : 'Przełącz na tryb ciemny (Alt+T)');
    });

    // Notify subsystems
    window.dispatchEvent(new CustomEvent('bipol:themechange', {
      detail: { theme, isDark }
    }));
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || getSavedTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next, true);
  }

  // Listen to OS theme changes if user has no explicit override
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      try {
        if (!localStorage.getItem(STORAGE_THEME_KEY)) {
          applyTheme(e.matches ? 'dark' : 'light', false);
        }
      } catch (_) {}
    });
  }

  /* ------------------------------------------------------------------------
     2. COMMAND PALETTE & PARAMETER QUICK FINDER (Ctrl+K)
     ------------------------------------------------------------------------ */
  const SEARCH_INDEX = [
    // Tabs & Workspaces
    { type: 'tab', target: 'tab-overview', icon: '📊', title: 'Podsumowanie projektu', tag: 'Widok główny' },
    { type: 'tab', target: 'tab-inputs', icon: '⚙️', title: 'Założenia i wymagania taktyczno-techniczne', tag: 'Dane wejściowe' },
    { type: 'tab', target: 'tab-trends', icon: '📈', title: 'Baza samolotów i trendy statystyczne', tag: 'Statystyka' },
    { type: 'tab', target: 'tab-cad', icon: '📐', title: 'Rysunek zestawieniowy CAD A3Z (3 rzuty)', tag: 'Geometria' },
    { type: 'tab', target: 'tab-variants', icon: '⚖️', title: 'Porównanie wariantów konstrukcyjnych', tag: 'Warianty' },
    { type: 'tab', target: 'tab-calculation-tree', icon: '🌳', title: 'Drzewo obliczeń i graf zależności', tag: 'Metodyka' },
    { type: 'tab', target: 'tab-p1-p2', icon: '📦', title: 'P1/P2: Bilans mas i wykres dopasowania (Matching Chart)', tag: 'Masy i napęd' },
    { type: 'tab', target: 'tab-p3', icon: '🪶', title: 'P3: Geometria skrzydła, Schrenk i wyważenie', tag: 'Geometria' },
    { type: 'tab', target: 'tab-p4', icon: '🦅', title: 'P4: Biegunowe aerodynamiczne i mechanizacja', tag: 'Aerodynamika' },
    { type: 'tab', target: 'tab-p5', icon: '⏱️', title: 'P5: Osiągi samolotu (prędkości, wznoszenie, zasięg)', tag: 'Osiągi' },
    { type: 'tab', target: 'tab-glide', icon: '🪂', title: 'Analiza lotu szybowego (dla motoszybowców i szybowców)', tag: 'Osiągi' },
    { type: 'tab', target: 'tab-p6', icon: '🛡️', title: 'P6: Obwiednia obciążeń V-n (manewrowa i podmuchowa)', tag: 'Wytrzymałość' },
    { type: 'tab', target: 'tab-compliance', icon: '✅', title: 'Weryfikacja założeń, flatter i audyt inżynierski', tag: 'Zgodność' },
    { type: 'tab', target: 'tab-reports', icon: '📄', title: 'Raport i generowanie dokumentacji DOCX / PDF', tag: 'Dokumentacja' },

    // Design Inputs & Core Parameters
    { type: 'tab', target: 'tab-p1-p2', icon: '⚖️', title: 'Masa startowa m₀ [kg] — wynik bilansu', tag: 'Wynik obliczeń' },
    { type: 'input', tab: 'tab-inputs', elemId: 'n_pax', icon: '👥', title: 'Liczba pasażerów n_pax (bez załogi)', tag: 'Parametr wejściowy' },
    { type: 'input', tab: 'tab-inputs', elemId: 'cruise_speed_kmh', icon: '💨', title: 'Prędkość przelotowa TAS [km/h]', tag: 'Osiągi' },
    { type: 'input', tab: 'tab-inputs', elemId: 'range_km', icon: '🗺️', title: 'Zasięg obliczeniowy R [km]', tag: 'Misja' },
    { type: 'input', tab: 'tab-inputs', elemId: 'wingspan_m', icon: '📏', title: 'Rozpiętość skrzydła b [m]', tag: 'Geometria' },
    { type: 'input', tab: 'tab-inputs', elemId: 'wing_area_m2', icon: '📐', title: 'Powierzchnia skrzydła S [m²]', tag: 'Geometria' },
    { type: 'input', tab: 'tab-inputs', elemId: 'aspect_ratio', icon: '📐', title: 'Wydłużenie skrzydła Λ (aspect ratio)', tag: 'Geometria' },
    { type: 'input', tab: 'tab-inputs', elemId: 'taper_ratio', icon: '📐', title: 'Zbieżność skrzydła η (taper ratio)', tag: 'Geometria' },
    { type: 'input', tab: 'tab-inputs', elemId: 'sweep_quarter_deg', icon: '📐', title: 'Kąt skosu skrzydła χ [°]', tag: 'Geometria' },
    { type: 'input', tab: 'tab-inputs', elemId: 'airfoil', icon: '🪶', title: 'Profil aerodynamiczny skrzydła', tag: 'Profil' },
    { type: 'input', tab: 'tab-inputs', elemId: 'engine_type', icon: '⚙️', title: 'Typ napędu (śmigłowy, odrzutowy, bez napędu)', tag: 'Napęd' },
    { type: 'input', tab: 'tab-inputs', elemId: 'engine_power_kw', icon: '⚡', title: 'Moc silnika P_max [kW]', tag: 'Napęd' },
    { type: 'input', tab: 'tab-inputs', elemId: 'cruise_altitude_m', icon: '⛰️', title: 'Wysokość przelotowa H_przelot [m]', tag: 'Atmosfera' },
    { type: 'input', tab: 'tab-inputs', elemId: 'cz_max_clean', icon: '🦅', title: 'Współczynnik siły nośnej cz_max gładki', tag: 'Aerodynamika' },
    { type: 'input', tab: 'tab-inputs', elemId: 'cx0', icon: '💨', title: 'Współczynnik oporu szkodliwego cx0', tag: 'Aerodynamika' },
    { type: 'input', tab: 'tab-inputs', elemId: 'gear_attachment', icon: '🛞', title: 'Mocowanie podwozia (kadłub, skrzydło)', tag: 'Podwozie' },

    { type: 'input', tab: 'tab-inputs', elemId: 'n_crew', icon: '👤', title: 'Liczba członków załogi n_crew', tag: 'Parametr wejściowy' },
    { type: 'input', elemId: 'cost_year', icon: '📅', title: 'Rok oszacowania kosztów produkcji', tag: 'P2 — koszty' },

    // Actions
    { type: 'action', action: 'recalculate', icon: '⚡', title: 'Przelicz projekt (Ctrl+Enter)', tag: 'Polecenie' },
    { type: 'action', action: 'toggle-theme', icon: '🌗', title: 'Przełącz motyw jasny / ciemny (Alt+T)', tag: 'Widok' },
    { type: 'action', action: 'open-report', icon: '📄', title: 'Otwórz raport bieżącego projektu', tag: 'Raport' },
    { type: 'action', action: 'new-project', icon: '＋', title: 'Utwórz nowy projekt w kreatorze', tag: 'Projekt' },
    { type: 'action', action: 'shortcuts', icon: '⌨️', title: 'Pokaż skróty klawiszowe (?)', tag: 'Pomoc' }
  ];

  let paletteBackdrop = null;
  let paletteInput = null;
  let paletteResults = null;
  let selectedIndex = 0;
  let filteredItems = [];

  function openCommandPalette() {
    if (!paletteBackdrop) {
      createPaletteDOM();
    }
    paletteBackdrop.style.display = 'flex';
    paletteInput.value = '';
    paletteInput.focus();
    updatePaletteResults('');
  }

  function closeCommandPalette() {
    if (paletteBackdrop) {
      paletteBackdrop.style.display = 'none';
    }
  }

  function createPaletteDOM() {
    paletteBackdrop = document.createElement('div');
    paletteBackdrop.className = 'bipol-palette-backdrop';
    paletteBackdrop.style.display = 'none';

    paletteBackdrop.innerHTML = `
      <div class="bipol-palette-card" role="dialog" aria-modal="true" aria-label="Szybkie wyszukiwanie">
        <div class="bipol-palette-header">
          <span class="bipol-palette-icon">🔍</span>
          <input type="text" class="bipol-palette-input" placeholder="Wyszukaj parametr, moduł, wykres lub polecenie..." autocomplete="off" spellcheck="false">
          <span class="bipol-palette-badge">ESC</span>
        </div>
        <div class="bipol-palette-results" role="listbox"></div>
        <div class="bipol-palette-footer">
          <span>Nawigacja: <kbd>↑</kbd> <kbd>↓</kbd> &bull; Wybierz: <kbd>Enter</kbd></span>
          <span>Przelicz: <kbd>Ctrl+Enter</kbd> &bull; Motyw: <kbd>Alt+T</kbd></span>
        </div>
      </div>
    `;

    document.body.appendChild(paletteBackdrop);

    paletteInput = paletteBackdrop.querySelector('.bipol-palette-input');
    paletteResults = paletteBackdrop.querySelector('.bipol-palette-results');

    paletteBackdrop.addEventListener('click', e => {
      if (e.target === paletteBackdrop) closeCommandPalette();
    });

    paletteInput.addEventListener('input', e => {
      updatePaletteResults(e.target.value);
    });

    paletteInput.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        closeCommandPalette();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(filteredItems.length - 1, selectedIndex + 1);
        renderPaletteItems();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(0, selectedIndex - 1);
        renderPaletteItems();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        executeSelectedItem();
      }
    });
  }

  function updatePaletteResults(query) {
    const q = (query || '').toLowerCase().trim();
    if (!q) {
      filteredItems = SEARCH_INDEX.slice(0, 8);
    } else {
      filteredItems = SEARCH_INDEX.filter(item => {
        return item.title.toLowerCase().includes(q) ||
               (item.tag && item.tag.toLowerCase().includes(q)) ||
               (item.elemId && item.elemId.toLowerCase().includes(q));
      }).slice(0, 10);
    }
    selectedIndex = 0;
    renderPaletteItems();
  }

  function renderPaletteItems() {
    if (!paletteResults) return;
    if (filteredItems.length === 0) {
      paletteResults.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:13px;">Brak pasujących wyników</div>';
      return;
    }

    paletteResults.innerHTML = filteredItems.map((item, index) => {
      const isSelected = index === selectedIndex;
      return `
        <div class="bipol-palette-item ${isSelected ? 'is-selected' : ''}" data-index="${index}" role="option" aria-selected="${isSelected}">
          <div class="bipol-palette-item-left">
            <span class="bipol-palette-item-icon">${item.icon}</span>
            <span class="bipol-palette-item-title">${escapeHtml(item.title)}</span>
          </div>
          <span class="bipol-palette-item-tag">${escapeHtml(item.tag)}</span>
        </div>
      `;
    }).join('');

    paletteResults.querySelectorAll('.bipol-palette-item').forEach(el => {
      el.addEventListener('mouseenter', () => {
        selectedIndex = parseInt(el.getAttribute('data-index'), 10);
        renderPaletteItems();
      });
      el.addEventListener('click', () => {
        selectedIndex = parseInt(el.getAttribute('data-index'), 10);
        executeSelectedItem();
      });
    });

    const activeEl = paletteResults.querySelector('.is-selected');
    if (activeEl) {
      activeEl.scrollIntoView({ block: 'nearest' });
    }
  }

  function executeSelectedItem() {
    const item = filteredItems[selectedIndex];
    if (!item) return;
    closeCommandPalette();

    if (item.type === 'tab') {
      navigateToTab(item.target);
    } else if (item.type === 'input') {
      window.focusDesignParameter?.(item.elemId);
    } else if (item.type === 'action') {
      if (item.action === 'recalculate') {
        triggerRecalculate();
      } else if (item.action === 'toggle-theme') {
        toggleTheme();
      } else if (item.action === 'open-report') {
        navigateToTab('tab-reports');
      } else if (item.action === 'new-project') {
        if (typeof window.openWizard === 'function') window.openWizard('new');
      } else if (item.action === 'shortcuts') {
        openShortcutsModal();
      }
    }
  }

  function navigateToTab(tabId) {
    const studioNav = document.querySelector(`[data-studio-nav="${tabId}"]`);
    if (studioNav) {
      studioNav.click();
    } else {
      const tabBtn = document.querySelector(`.bipol-tab[data-target="${tabId}"]`);
      if (tabBtn) tabBtn.click();
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  /* ------------------------------------------------------------------------
     3. KEYBOARD SHORTCUTS MODAL (?)
     ------------------------------------------------------------------------ */
  let shortcutsBackdrop = null;

  function openShortcutsModal() {
    if (!shortcutsBackdrop) {
      shortcutsBackdrop = document.createElement('div');
      shortcutsBackdrop.className = 'bipol-palette-backdrop';
      shortcutsBackdrop.style.display = 'none';

      shortcutsBackdrop.innerHTML = `
        <div class="bipol-palette-card bipol-shortcuts-card" role="dialog" aria-modal="true" aria-label="Skróty klawiszowe">
          <div class="bipol-palette-header">
            <span class="bipol-palette-icon">⌨️</span>
            <div style="flex:1; font-weight:650; font-size:14px; color:var(--text-primary);">Skróty klawiszowe BiPOL Requiem</div>
            <button type="button" class="btn-outline-sm" id="closeShortcutsBtn" style="padding:4px 8px;">✕</button>
          </div>
          <div class="bipol-shortcuts-grid">
            <span>Szybkie wyszukiwanie / Command Palette</span>
            <kbd>Ctrl + K</kbd>
            <span>Przeliczenie projektu w tle</span>
            <kbd>Ctrl + Enter</kbd>
            <span>Przełącz motyw (jasny / ciemny)</span>
            <kbd>Alt + T</kbd>
            <span>Pomoc i skróty klawiszowe</span>
            <kbd>?</kbd>
            <span>Zamknięcie otwartego okna / palety</span>
            <kbd>Esc</kbd>
          </div>
        </div>
      `;

      document.body.appendChild(shortcutsBackdrop);

      shortcutsBackdrop.addEventListener('click', e => {
        if (e.target === shortcutsBackdrop) shortcutsBackdrop.style.display = 'none';
      });
      shortcutsBackdrop.querySelector('#closeShortcutsBtn').addEventListener('click', () => {
        shortcutsBackdrop.style.display = 'none';
      });
    }

    shortcutsBackdrop.style.display = 'flex';
  }

  /* ------------------------------------------------------------------------
     4. RECALCULATE & DIRTY STATE TRACKER
     ------------------------------------------------------------------------ */
  function markDirty(event) {
    if (window.isDuplicateCalculatedChange?.(event)) return;
    const pill = document.getElementById('navRecalcPill');
    if (pill) {
      pill.className = 'nav-recalc-pill dirty';
      pill.innerHTML = `<span>⚠️ Przelicz</span> <kbd>Ctrl+Enter</kbd>`;
      pill.setAttribute('title', 'Parametry uległy zmianie. Kliknij lub naciśnij Ctrl+Enter aby zaktualizować aerodynamikę i osiągi.');
    }
  }

  function markClean() {
    const pill = document.getElementById('navRecalcPill');
    if (pill) {
      pill.className = 'nav-recalc-pill synced';
      pill.innerHTML = `<span>✓ Gotowe</span> <kbd>Ctrl+Enter</kbd>`;
      pill.setAttribute('title', 'Projekt jest zsynchronizowany i aktualny. Naciśnij Ctrl+Enter aby wymusić ponowne przeliczenie.');
    }
  }

  function syncCalculationState() {
    const pill = document.getElementById('navRecalcPill');
    if (!pill) return;
    if (document.getElementById('calcBtn')?.disabled) {
      pill.className = 'nav-recalc-pill calculating';
      pill.innerHTML = '<span>⏳ Obliczanie...</span>';
      pill.title = 'Trwają obliczenia projektu.';
    } else if (document.getElementById('calculationStatus')?.classList.contains('is-error')) {
      markDirty();
      pill.innerHTML = '<span>❌ Błąd obliczeń</span> <kbd>Ctrl+Enter</kbd>';
      pill.title = document.getElementById('calculationStatus').textContent;
    } else if (document.getElementById('openReportBtn')?.dataset.resultsStale === 'false') {
      markClean();
    } else {
      markDirty();
    }
  }

  function triggerRecalculate() {
    // The calculation function handles validation, rejected/stale responses and
    // failures internally. Resolving its promise does not prove fresh results.
    if (typeof window.performCalculation === 'function') return window.performCalculation();
    document.getElementById('calcBtn')?.click();
  }

  /* ------------------------------------------------------------------------
     5. GLOBAL KEYBOARD EVENT LISTENER
     ------------------------------------------------------------------------ */
  document.addEventListener('keydown', e => {
    // Escape: close any active palette or shortcuts modal
    if (e.key === 'Escape') {
      closeCommandPalette();
      if (shortcutsBackdrop) shortcutsBackdrop.style.display = 'none';
      return;
    }

    // Ctrl+K: Command Palette
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openCommandPalette();
      return;
    }

    // Ctrl+Enter: Recalculate
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      triggerRecalculate();
      return;
    }

    // Alt+T: Toggle Theme
    if (e.altKey && e.key.toLowerCase() === 't') {
      e.preventDefault();
      toggleTheme();
      return;
    }

    // ?: Keyboard shortcuts (when not typing in an input)
    if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      openShortcutsModal();
      return;
    }
  });

  /* ------------------------------------------------------------------------
     6. INITIALIZATION & EXPORTS
     ------------------------------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(getSavedTheme(), false);

    // Observe the same freshness flag and error state used by the report and
    // calculation workflow. Search, graph and exploratory sliders do not edit
    // the aircraft. Only actual model inputs invalidate its results.
    const observer = new MutationObserver(syncCalculationState);
    for (const id of ['openReportBtn', 'calcBtn', 'calculationStatus']) {
      const control = document.getElementById(id);
      if (control) observer.observe(control, {attributes: true, attributeFilter: ['data-results-stale', 'disabled', 'class'], childList: true});
    }
    for (const event of ['bipol:calculating', 'bipol:project']) {
      document.addEventListener(event, markDirty);
    }
    document.querySelectorAll('#designForm, [data-analysis-param]').forEach(control => {
      control.addEventListener('input', markDirty);
      control.addEventListener('change', markDirty);
    });
    syncCalculationState();

    // Wire search trigger in navbar if present
    document.querySelectorAll('.nav-search-trigger').forEach(btn => {
      btn.addEventListener('click', openCommandPalette);
    });

    // Wire theme toggle buttons
    document.querySelectorAll('#themeToggleBtn, [data-theme-toggle]').forEach(btn => {
      btn.addEventListener('click', toggleTheme);
    });

    // Wire recalculate pill
    const pill = document.getElementById('navRecalcPill');
    if (pill) {
      pill.addEventListener('click', triggerRecalculate);
    }

    // Wire shortcuts button
    const shortcutsBtn = document.getElementById('btnShortcutsNav');
    if (shortcutsBtn) {
      shortcutsBtn.addEventListener('click', openShortcutsModal);
    }
  });

  // Public API
  window.BipolModernUI = {
    toggleTheme,
    applyTheme,
    getTheme: () => document.documentElement.getAttribute('data-theme') || 'light',
    openCommandPalette,
    closeCommandPalette,
    openShortcutsModal,
    triggerRecalculate,
    markDirty,
    markClean
  };

})();
