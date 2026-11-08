"""Source engine hardware masses and explicitly documented installed assemblies."""
from copy import deepcopy
import math


def validate_hardware(record):
    """Validate an import observation without interpreting a dry mass as installation mass."""
    if not isinstance(record, dict):
        raise ValueError('Masa silnika: wymagany zapis danych źródłowych.')
    mass=record.get('mass_kg')
    if isinstance(mass,bool) or not isinstance(mass,(int,float)) or not math.isfinite(mass) or mass<=0:
        raise ValueError('Masa silnika ze źródła musi być dodatnia i skończona.')
    for key in ('definition','source_title','locator','checked_on'):
        if not isinstance(record.get(key),str) or not record[key].strip():
            raise ValueError(f'Masa silnika: brak pola {key}.')
    if not str(record.get('source_url','')).startswith('https://'):
        raise ValueError('Masa silnika: wymagany adres dokumentu producenta HTTPS.')
    return deepcopy(record)


def apply_mass_evidence(params, evidence, hardware=None):
    """Rebuild mass evidence from current model and independent source inputs."""
    count=int(params['n_engines'])
    known=validate_hardware(hardware) if hardware else None
    base=known['mass_kg'] if known else None
    installed=params.get('engine_installed_mass_kg')
    owner=(f"catalog:{params.get('engine_model_id')}" if params['engine_fuel_mode']=='catalog'
           else f"custom:{evidence['model']}")
    source=conditions=None
    if installed is not None:
        if params.get('engine_mass_owner',owner)!=owner:
            raise ValueError('Masa zabudowanego napędu dotyczy innego modelu silnika. Uzupełnij masę i źródło dla bieżącej propozycji.')
        for key in ('engine_mass_source','engine_mass_conditions'):
            value=params.get(key)
            if not isinstance(value,str) or not 5<=len(value.strip())<=2000:
                raise ValueError('Masa zabudowanego napędu: podaj źródło oraz opis elementów i płynów objętych podaną masą.')
            params[key]=value.strip()
        installed=float(installed)
        if not math.isfinite(installed) or installed<=0:
            raise ValueError('Masa zabudowanego napędu musi być dodatnia i skończona.')
        if base is not None and installed<base:
            raise ValueError(f'Masa zabudowanego napędu na silnik ({installed:g} kg) jest mniejsza od masy bazowej producenta ({base:g} kg).')
        params['engine_mass_owner']=owner
        source,conditions=params['engine_mass_source'],params['engine_mass_conditions']
    else:
        params.pop('engine_mass_owner',None)
    evidence['mass']=dict(hardware=known,base_mass_each_kg=base,
        installed_mass_each_kg=installed,installed_mass_total_kg=installed*count if installed is not None else None,
        installed_source=source,installed_conditions=conditions,
        fixed_mass_total_kg=(installed if installed is not None else base or 0)*count,
        basis='documented_installed_assembly' if installed is not None else 'manufacturer_base_minimum' if known else 'mass_not_documented')
