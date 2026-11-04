(function(root) {
  'use strict';
  const direct = {ar:'aspect_ratio', vh:'v_h', v_h:'v_h', v_v:'v_v', dihedral_deg:'dihedral_deg',
    b_ail_ratio:'aileron_span_ratio', c_ail_ratio:'aileron_chord_ratio',
    c_e_ratio:'elevator_chord_ratio', c_r_ratio:'rudder_chord_ratio'};
  function patch(key, value, params, mass, suggestion) {
    // BIPOL_1, s. 4: eq. (1) of the trend analysis always goes into the mass balance.
    if (key === 'me_m0') return {empty_mass_model:'trend'};
    if (!Number.isFinite(value)) throw Error('Brak liczbowej propozycji.');
    if (key === 'ws') {
      if (!(value > 0 && mass > 0)) throw Error('Najpierw oblicz masę projektu.');
      return {wing_input_mode:'area_aspect', wing_area_m2:mass/value};
    }
    if (key === 'pw') {
      if (params.engine_type !== 'prop' || !(value>0 && mass>0)) throw Error('Moc dotyczy napędu śmigłowego.');
      return {power_input_mode:'fixed', engine_power_kw:mass/value};
    }
    const field = direct[key];
    if (!field) throw Error('Ten wynik służy do porównania; nie jest wejściem modelu.');
    const update = {[field]:value};
    if (key === 'ar' && params.wing_input_mode === 'span_area') update.wing_input_mode='span_aspect';
    return update;
  }
  const api={patch, supports:key=>key in direct || ['ws','pw'].includes(key)};
  root.BipolTrendInputs=api;
  if (typeof module !== 'undefined') module.exports=api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
