/* Navigation and progressive disclosure only; the engineering pipeline is unchanged. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const {escape: esc} = BipolStudio;

  function disclosure(node, title, open = false) {
    if (!node || node.parentElement?.classList.contains('quiet-disclosure')) return;
    const details = document.createElement('details');
    details.className = 'quiet-disclosure'; details.open = open;
    const summary = document.createElement('summary'); summary.textContent = title;
    node.before(details); details.append(summary, node);
    details.addEventListener('toggle', () => {
      if (!details.open || !currentResults) return;
      requestAnimationFrame(() => {
        const active = document.querySelector('.tab-content.active');
        if (active) renderTabVisuals(active.id);
        if (currentPortalMode === 'projects') renderSemesterProjectCharts(currentSemesterProject, currentResults);
      });
    });
    return details;
  }

  function help(node, title) {
    if (!node || node.parentElement?.classList.contains('quiet-help-content')) return;
    const details = document.createElement('details'); details.className = 'quiet-help-content';
    const summary = document.createElement('summary'); summary.textContent = title;
    node.before(details); details.append(summary, node);
  }

  function tabset(root, groups, name) {
    const tabs = document.createElement('div'); tabs.className = 'quiet-section-tabs';
    tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', name);
    const buttons = [];
    function activate(index, focus = false) {
      groups.forEach((g, i) => {
        g.panel.hidden = i !== index;
        buttons[i].setAttribute('aria-selected', String(i === index)); buttons[i].tabIndex = i === index ? 0 : -1;
      });
      if (focus) buttons[index].focus();
    }
    groups.forEach((g, i) => {
      const button = document.createElement('button'); button.type = 'button';
      button.id = g.panel.id+'-tab'; button.textContent = g.title;
      button.setAttribute('role', 'tab'); button.setAttribute('aria-controls', g.panel.id);
      g.panel.setAttribute('role', 'tabpanel'); g.panel.setAttribute('aria-labelledby', button.id);
      g.panel.classList.add('quiet-section');
      button.addEventListener('click', () => activate(i));
      button.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (i+1)%groups.length;
        if (event.key === 'ArrowLeft') next = (i+groups.length-1)%groups.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = groups.length-1;
        if (next != null) { event.preventDefault(); activate(next, true); }
      });
      tabs.append(button); buttons.push(button);
    });
    root.prepend(tabs); activate(0);
    return {activate, tabs};
  }

  function organizeTrends() {
    const root = $('tab-trends');
    const charts = document.createElement('div'); charts.id = 'trendResultsPanel';
    const selection = document.createElement('div'); selection.id = 'trendSelectionPanel';
    const method = document.createElement('div'); method.id = 'trendMethodPanel';
    const mount = document.createElement('div'); mount.id = 'trendViews';
    const stats = $('trendMassChart').closest('section'), time = $('trendTimeChart').closest('section');
    const relation = $('trendRelationChart').closest('section');
    const averages = $('trendAverages').closest('section');
    const catalog = $('trendAircraftRows').closest('section');
    const prelim = $('trendPreliminary').closest('section'), sources = $('trendSources').closest('section');
    const oldGrid = stats.parentElement;
    charts.append(stats, time, relation); oldGrid.remove();
    selection.append($('trendControls'), catalog);
    const importCard = $('trendObservationFile')?.closest('section');
    if(importCard)selection.append(importCard);
    const reportPlan = $('trendReportPlan')?.closest('section');
    if(reportPlan)charts.append(reportPlan);
    method.append(averages, prelim, sources);
    mount.append(charts, selection, method);root.append(mount);
    tabset(mount, [{title:'Wykresy i wyniki',panel:charts},{title:'Samoloty w bazie',panel:selection},{title:'Metoda i źródła',panel:method}], 'Analiza trendów');
    const chooser = document.createElement('label'); chooser.htmlFor = 'trendChartView'; chooser.className = 'quiet-chart-chooser';
    chooser.innerHTML = 'Wykres<select id="trendChartView"><option value="0">Udział masy pustej</option><option value="1">Trend w czasie</option><option value="2">Osiągi a geometria</option></select>';
    charts.prepend(chooser);
    const chartCards = [stats,time,relation];
    function selectChart() { chartCards.forEach((node,i) => { node.hidden = i !== Number($('trendChartView').value); }); }
    $('trendChartView').addEventListener('change', selectChart); selectChart();
    const controls = $('trendControls').querySelector('.trend-controls');
    const advanced = document.createElement('div');
    [...controls.children].slice(3).forEach(node => advanced.append(node));advanced.className = 'trend-controls';
    controls.after(advanced);help(advanced,'Lata i wagi obserwacji');
    const notes = $('trendControls').querySelector('.studio-fine-print');
    if (notes) { notes.style.display = 'block';sources.append(notes); }
    const warnings = $('trendWarnings');
    const d = disclosure(warnings,'Uwagi do danych'); d.id = 'trendWarningDetails';
    const summary = d.querySelector('summary');
    new MutationObserver(() => {
      const count = warnings.querySelectorAll('p').length;
      d.hidden = count === 0; summary.textContent = `Uwagi do danych (${count})`;
    }).observe(warnings,{childList:true});
    disclosure($('trendSuggestionsPanel'),'Parametry z trendów — sprawdź i zastosuj w projekcie',true);
  }

  function organizeAnalyses() {
    const labels = {'tab-cad':'Rysunek samolotu','tab-p1-p2':'Masy i dobór napędu','tab-p3':'Geometria i wyważenie',
      'tab-p4':'Aerodynamika','tab-p5':'Osiągi','tab-p6':'Obwiednia obciążeń','tab-compliance':'Weryfikacja założeń'};
    for (const [id,title] of Object.entries(labels)) {
      const root = $(id); if (!root) continue;
      const heading = document.createElement('div'); heading.className = 'studio-heading';
      heading.innerHTML = `<div><h1>${esc(title)}</h1></div><div class="quiet-analysis-actions"><button type="button" class="btn btn-outline" data-toggle-explanations aria-pressed="false">Objaśnienia</button><button type="button" class="btn btn-outline" data-studio-target="tab-inputs">Zmień założenia</button></div>`;
      root.prepend(heading);
      const cards = [...root.children].filter(node => node.matches('.b-card,.subpoint-card'));
      cards.forEach((node,index) => {
        const header = node.querySelector('.b-card-header,.subpoint-header');
        const text = BipolSymbols.source(header?.querySelector('h3,h4')).replace(/Podpunkt\s+[\w.]+\s*/,'').replace(/^[^\p{L}\p{N}]+/u,'').trim() || 'Dane szczegółowe';
        const d = disclosure(node,text,index===0 || id==='tab-compliance');
        if (d && id==='tab-compliance' && index===1) d.id = 'complianceChecksDisclosure';
        if (header && !header.querySelector('button,a,input,select')) header.classList.add('quiet-original-heading');
        if (d && index===0) d.classList.add('quiet-primary-analysis');
        node.querySelectorAll('.formula-box').forEach(formula=>help(formula,'Wzory i objaśnienia'));
      });
    }
    document.querySelectorAll('.project-workstation').forEach(root => {
      root.querySelectorAll(':scope > .subpoint-card').forEach((node,index) => {
        const title=BipolSymbols.source(node.querySelector('h4')).replace(/Podpunkt\s+[\w.]+\s*/,'').trim()||'Szczegóły';
        disclosure(node,title,index===0); node.querySelector('.subpoint-header')?.classList.add('quiet-original-heading');
      });
      const checklist=root.querySelector('.project-checklist-box');if(checklist)disclosure(checklist,'Lista kontrolna zaliczenia');
    });
  }

  function formPresentation() {
    ['mod0','mod2','mod3','mod4'].forEach(key => {
      $('body_'+key)?.classList.add('collapsed');
      const header=$('accordion_'+key)?.querySelector('.module-header');
      header?.classList.remove('active'); header?.setAttribute('aria-expanded','false');
    });
    document.querySelectorAll('.module-header').forEach(header => {
      const body=header.nextElementSibling;
      header.tabIndex=0;header.setAttribute('role','button');header.setAttribute('aria-controls',body.id);
      const sync=()=>header.setAttribute('aria-expanded',String(!body.classList.contains('collapsed')));
      sync();new MutationObserver(sync).observe(body,{attributes:true,attributeFilter:['class']});
    });
    const drawer=$('constraintsDrawerBody'),header=drawer.previousElementSibling;
    header.tabIndex=0;header.setAttribute('role','button');header.setAttribute('aria-controls',drawer.id);
    const sync=()=>header.setAttribute('aria-expanded',String(drawer.style.display!=='none'));
    sync();new MutationObserver(sync).observe(drawer,{attributes:true,attributeFilter:['style']});
    header.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();header.click();}});
    for(const [id,title] of [['wingConfigDidacticBox','Dobór układu skrzydła'],['wingPlanformDidacticBox','Obrys skrzydła — opis'],['flapDidacticCard','Klapy i lotki — opis'],['trailingEdgeLayoutCard','Podział krawędzi spływu']])help($(id),title);
    const names={piston_ga:'Samolot tłokowy GA',motoglider:'Motoszybowiec',glider:'Szybowiec',turboprop_regional:'Samolot turbośmigłowy',jet_business:'Odrzutowiec biznesowy',jet_transport:'Samolot komunikacyjny',uav:'Bezzałogowiec (UAV)'};
    [...$('aircraft_type').options].forEach(option=>{option.title=option.text;option.text=names[option.value]||option.text;});
    const titleMap={mod1:'Misja i wymagania',mod2:'Skrzydło i geometria',mod3:'Aerodynamika i mechanizacja',mod4:'Napęd'};
    for(const [key,title] of Object.entries(titleMap))$('accordion_'+key)?.querySelector('.module-title b')?.replaceChildren(document.createTextNode(title));
  }

  function refreshDynamicNotes() {
    document.querySelectorAll('.tab-content table').forEach(table=>{
      const headings=[...table.querySelectorAll('thead th')];
      headings.forEach((th,index)=>{
        if(!/^(uzasadnienie|znaczenie|definicja|metodyka)/i.test(th.textContent.trim()))return;
        th.dataset.quietExplanation='';
        table.querySelectorAll('tbody tr').forEach(row=>{if(row.children[index])row.children[index].dataset.quietExplanation='';});
      });
    });
    const stats=$('trendMassStats');
    if(stats?.children.length===3 && !stats.querySelector('details')) {
      const explanation=document.createElement('div');
      explanation.append(stats.firstElementChild,stats.lastElementChild);stats.append(explanation);
      help(explanation,'Wzór i sposób obliczeń');
    }
    if ($('title_mod4')) $('title_mod4').textContent='Napęd';
    document.querySelectorAll('[id^=lock_btn_]').forEach(button=>{
      const key=button.id.replace('lock_btn_',''), label=document.querySelector(`label[for="${key}"]`)?.textContent.replace(/\s+i\s*$/,'').trim()||key;
      button.setAttribute('aria-label',button.disabled?`Wartość obliczana: ${label}`:`${window.userLockedParams?.has(key)?'Odblokuj':'Zablokuj'} parametr: ${label}`);
      button.setAttribute('aria-pressed',String(!!window.userLockedParams?.has(key)));
    });
  }

  function setupParameterFinder() {
    const search = $('studioParameterSearch'), list = $('studioParameterResults'), status = $('studioParameterCount');
    const normalize = text => text.toLocaleLowerCase('pl').normalize('NFD').replace(/\p{Diacritic}/gu,'').replace(/ł/g,'l');
    function openSection(key) {
      const header = $('accordion_'+key)?.querySelector('.module-header');
      if ($('body_'+key)?.classList.contains('collapsed')) header.click();
      return header;
    }
    function reveal(control) {
      if (control.closest('.advanced-only')) setSidebarMode('advanced');
      const module = control.closest('.module-accordion');
      if (module) openSection(module.id.replace('accordion_',''));
      for (let node=control.parentElement; node; node=node.parentElement) if (node.tagName==='DETAILS') node.open=true;
      requestAnimationFrame(() => {
        control.focus({preventScroll:true});
        const grp = control.closest('.input-group'); grp?.scrollIntoView({block:'center',behavior:'instant'}); if (grp) { grp.classList.add('is-quickfix-target'); setTimeout(() => grp.classList.remove('is-quickfix-target'), 2200); }
      });
    }
    window.focusDesignParameter = paramId => { const control = $(paramId); if (!control) return; if (typeof setPortalMode === 'function') setPortalMode('holistic'); document.querySelector('.bipol-tab[data-target="tab-inputs"]')?.click(); reveal(control); };
    function update() {
      const query = normalize(search.value.trim());
      list.replaceChildren(); list.hidden = !query;
      if (!query) { status.textContent = 'Wpisz nazwę, aby przejść prosto do pola.'; return; }
      // Najpierw nazwa pola, potem tytuł i symbol z kartoteki (np. „Cx0”, „propeller”), na końcu jej opis.
      const cards = typeof PARAMETER_ENCYCLOPEDIA === 'undefined' ? {} : PARAMETER_ENCYCLOPEDIA;
      const compact = text => normalize(text).replace(/[\s_.,·()-]/g,''), symbol = compact(query);
      const rank = (name, info) => normalize(name).includes(query) ? 0
        : info && (normalize(info.title).includes(query) || (symbol && compact(info.symbol).includes(symbol))) ? 1
        : info && normalize(info.plain || info.short_desc || '').includes(query) ? 2 : -1;
      const fields = [...$('designForm').querySelectorAll('.input-group label[for]')].map(label => {
        const control = $(label.htmlFor), copy = label.cloneNode(true);
        copy.querySelectorAll('button,.info-circle-icon').forEach(node=>node.remove());
        const name = copy.textContent.replace(/\s+/g,' ').trim();
        const info = control && cards[window.BipolDidactic?.keyFor(control.id) ?? control.id];
        return {control,name,module:control?.closest('.module-accordion'),rank:rank(name,info)};
      }).filter(field => field.control && field.module && field.module.id!=='accordion_mod0'
        && !field.control.closest('[hidden]') && field.rank>=0).sort((a,b)=>a.rank-b.rank);
      status.textContent = fields.length ? `Znalezione parametry: ${fields.length}. Wybierz pole poniżej.` : 'Nie znaleziono parametru. Spróbuj krótszej nazwy, np. „masa” lub „skrzydło”.';
      fields.slice(0,8).forEach(field => {
        const item=document.createElement('li'), button=document.createElement('button');button.type='button';
        const name=document.createElement('span');name.textContent=field.name;
        const group=document.createElement('small');group.textContent=(field.control.readOnly?'Obliczany · ':'')+(field.rank?'Z kartoteki · ':'')+(field.module.querySelector('.module-title b')?.textContent || 'Parametry');
        button.append(name,group);button.addEventListener('click',()=>reveal(field.control));
        item.append(button);list.append(item);
      });
      if (fields.length>8) status.textContent += ' Wyświetlamy pierwszych 8 — doprecyzuj nazwę.';
      if (!fields.length) list.hidden=true;
    }
    search.addEventListener('input', update);
    search.addEventListener('keydown', event => {
      if (event.key==='Escape') { search.value=''; update(); }
      if (event.key==='ArrowDown' && list.firstElementChild) { event.preventDefault();list.querySelector('button').focus(); }
    });
    document.querySelectorAll('[data-input-section]').forEach(button=>button.addEventListener('click',()=> {
      const header=openSection(button.dataset.inputSection);
      header?.focus({preventScroll:true});header?.scrollIntoView({block:'start',behavior:'instant'});
    }));
    for (const id of ['modeBasicBtn','modeAdvancedBtn']) {
      const button=$(id), sync=()=>button.setAttribute('aria-pressed',String(button.classList.contains('active')));
      sync();new MutationObserver(sync).observe(button,{attributes:true,attributeFilter:['class']});
    }
    document.addEventListener('bipol:results',()=>{if(search.value.trim())update();});
    document.addEventListener('bipol:project',()=>{search.value='';update();});
  }

  document.addEventListener('DOMContentLoaded',()=>{
    organizeTrends();organizeAnalyses();formPresentation();refreshDynamicNotes();setupParameterFinder();
    const metadata=$('tab-reports').querySelector('.studio-metadata-grid');help(metadata,'Dane autora');
    const reportNotes=$('studioNotes').closest('section');disclosure(reportNotes,'Wnioski i własne źródła');
    const extraExports=document.createElement('div');
    document.querySelectorAll('#tab-reports [data-studio-action="export-csv"], #tab-reports [data-studio-action="export-json"]').forEach(button=>extraExports.append(button));
    $('tab-reports').querySelector('.studio-stack-actions').append(extraExports);help(extraExports,'Inne formaty danych');
    const glideNotes=document.createElement('div');
    const glideCard=$('studioGlideChart').closest('section');
    [...glideCard.querySelectorAll(':scope > p')].forEach(p=>glideNotes.append(p));
    glideCard.append(glideNotes);help(glideNotes,'Wzory i założenia modelu');
    const semesterHeader=$('semesterProjectBar').querySelector('.semester-header-bar');
    disclosure(semesterHeader,'Punktacja i wymagania zaliczenia');
    const notice=document.createElement('div');notice.id='workspaceNotice';notice.hidden=true;notice.setAttribute('role','alert');
    notice.innerHTML='<span></span><button type="button" class="btn btn-outline" data-studio-target="tab-inputs">Sprawdź założenia</button>';
    document.querySelector('.project-bar-container').after(notice);
    const status=$('calculationStatus');
    function syncStatus(){notice.hidden=!status.classList.contains('is-error');notice.querySelector('span').textContent=notice.hidden?'':status.textContent;}
    new MutationObserver(syncStatus).observe(status,{subtree:true,childList:true,attributes:true});syncStatus();
    document.addEventListener('click',event=>{
      const button=event.target.closest('.quiet-project-menu button');
      if(button){const menu=button.closest('details');menu.open=false;menu.querySelector('summary').focus();}
    },true);
    $('toggleDidacticHintsBtn').addEventListener('click',()=>{
      const shown=document.body.classList.contains('show-inline-hints');
      document.querySelectorAll('[data-toggle-explanations]').forEach(button=>{button.setAttribute('aria-pressed',String(shown));button.textContent=shown?'Ukryj objaśnienia':'Objaśnienia';});
    });
    document.addEventListener('click',event=>{
      const fixBtn=event.target.closest('[data-focus-param]');
      if(fixBtn){event.preventDefault();window.focusDesignParameter?.(fixBtn.dataset.focusParam);return;}
      // Przycisk prowadzący do akcji w innej zakładce: po przejściu pokaż i zaznacz tę akcję.
      const revealBtn=event.target.closest('[data-reveal]');
      if(revealBtn)requestAnimationFrame(()=>{const target=$(revealBtn.dataset.reveal);target?.scrollIntoView({block:'center',behavior:'instant'});target?.focus({preventScroll:true});});
      if(event.target.closest('[data-toggle-explanations]'))$('toggleDidacticHintsBtn').click();
      if(event.target.closest('[data-studio-target="tab-inputs"]')&&$('calculationStatus').classList.contains('is-error')) {
        const invalid=[...$('designForm').querySelectorAll('input[type=number]')].find(input=>!input.value.trim()||!Number.isFinite(Number(input.value))||!input.checkValidity());
        if(invalid) {
          invalid.closest('.module-body')?.classList.remove('collapsed');
          if(invalid.closest('.advanced-only'))setSidebarMode('advanced');
          invalid.focus();invalid.scrollIntoView({block:'center'});
        }
      }
      const menu=event.target.closest('.quiet-project-menu');
      if(!menu||event.target.closest('button'))document.querySelectorAll('.quiet-project-menu').forEach(d=>{
        const returnFocus=d.open&&d.contains(event.target);d.open=false;
        if(returnFocus)d.querySelector('summary').focus();
      });
    });
    document.addEventListener('keydown',event=>{if(event.key==='Escape')document.querySelectorAll('.quiet-project-menu[open]').forEach(d=>{d.open=false;d.querySelector('summary').focus();});});
    document.addEventListener('bipol:results',refreshDynamicNotes);
  });
})();
