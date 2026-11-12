/* User-visible assumptions and equivalent wing-section inputs. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const mode = () => $('aeroelastic_input_mode').value === 'documented';
  function visibility() {
    const fieldset = $('aeroelasticDeclaredData');
    fieldset.hidden = !mode(); fieldset.disabled = !mode();
    fieldset.querySelectorAll('input, textarea').forEach(el => { el.required = mode(); });
  }
  function restore() {
    const p = window.formBaseParams || {};
    $('aeroelasticPanel').querySelectorAll('[data-analysis-param]').forEach(el => {
      el.value = p[el.id] ?? (el.id === 'wing_structure_material' ? 'auto' :
        el.id === 'aeroelastic_input_mode' ? 'estimated' : '');
    });
    visibility();
  }
  const number = (n, unit) => n == null ? 'Nie wyznaczono' :
    `${Number(n).toLocaleString('pl-PL', {maximumFractionDigits: 2})} ${unit}`;
  function render(result) {
    const a = result?.aeroelastics;
    if (!a) return;
    $('aeroelasticStatus').textContent = `${a.material}. ${a.input_basis.mode === 'documented'
      ? 'Zadeklarowane dane przekroju.' : 'Założone dane kesonu i rozkładu masy.'} Analiza wstępna; zgodność nie została wykazana.`;
    const rows = [
      ['Sztywność giętna EI', number(a.bending_stiffness_ei, 'N·m²')],
      ['Sztywność skrętna GJ', number(a.torsional_stiffness_gj, 'N·m²')],
      ['Pierwsza częstość giętna / skrętna', `${number(a.bending_frequency_hz, 'Hz')} / ${number(a.torsion_frequency_hz, 'Hz')}`],
      ['VD (EAS)', number(a.dive_speed_vd_kmh, 'km/h')],
      ['Zbiegnięcie częstości 2DOF (EAS)', number(a.flutter_speed_kmh, 'km/h')],
      ['Dywergencja skrętna (EAS)', number(a.divergence_speed_kmh, 'km/h')],
      ['Rewers lotek', 'Nieobliczony — brak modelu lotki i skręcania'],
    ];
    $('aeroelasticResults').replaceChildren(...rows.map(row => {
      const tr = document.createElement('tr');
      row.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
      return tr;
    }));
    const basis = a.comparison_basis;
    $('aeroelasticBasis').replaceChildren(document.createTextNode(`${basis.label}. ${basis.note} `));
    if (basis.source_url) {
      const link = document.createElement('a'); link.href = basis.source_url;
      link.textContent = 'Dokument źródłowy'; link.target = '_blank'; link.rel = 'noopener';
      $('aeroelasticBasis').append(link);
    }
    $('aeroelasticSource').textContent = a.input_basis.source
      ? `Źródło zadeklarowane: ${a.input_basis.source}. Konfiguracja: ${a.input_basis.conditions}` :
      'Brak źródłowych danych sztywności i bezwładności rzeczywistego skrzydła.';
    $('aeroelasticLimitations').replaceChildren(...a.limitations.map(text => {
      const li = document.createElement('li'); li.textContent = text; return li;
    }));
  }
  document.addEventListener('DOMContentLoaded', () => {
    restore();
    $('aeroelastic_input_mode').addEventListener('change', visibility);
    $('applyAeroelasticData').addEventListener('click', () => {
      try {
        const panel = $('aeroelasticPanel');
        // Arrow steps aid editing; typed source precision must be retained.
        if (mode() && ![...panel.querySelectorAll('input[type="text"], textarea')].every(el => el.reportValidity())) return;
        validateNumericFields(panel);
        performCalculation();
      } catch (error) { $('aeroelasticStatus').textContent = error.message; }
    });
  });
  document.addEventListener('bipol:project', restore);
  document.addEventListener('bipol:results', event => render(event.detail));
})();
