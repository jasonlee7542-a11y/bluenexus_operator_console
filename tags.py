"""Provisional tag interpretations; retained independently from source readings."""
import re
import pandas as pd

def definition(tag):
    """Mapping is explicit and exportable; unknown tags stay in recorded units."""
    name,unit,scale,confidence,kind=tag,'recorded units',1.,'Unmapped','other'
    if 'qz_temp' in tag: name,unit,confidence,kind='Front bearing temperature','°C','Medium','temperature'
    elif 'hz_temp' in tag: name,unit,confidence,kind='Rear bearing temperature','°C','Medium','temperature'
    elif tag.endswith('_wd'): name,unit,confidence,kind='Pump temperature (location unconfirmed)','°C','Medium','temperature'
    elif '_tt_zjs_' in tag: name,unit,confidence,kind='RO common feedwater temperature','°C','Medium','temperature'
    elif tag.endswith('_cz_o'): name,unit,confidence,kind='Vertical vibration velocity','mm/s','Medium-low','vibration'
    elif re.search(r'_[xyz]sd$',tag): name,unit,confidence,kind=f'{tag[-3].upper()} vibration velocity','mm/s','Medium','vibration'
    elif re.search(r'_[xyz]wy$',tag): name,unit,confidence,kind=f'{tag[-3].upper()} vibration displacement','µm','Medium','vibration'
    elif 'tur_zcs' in tag: name,unit,confidence,kind='UF product turbidity','NTU','Medium','turbidity'
    elif tag in ['rohsl','ufhsl']: name,unit,confidence,kind=f'{tag[:2].upper()} recovery','%','High','recovery'
    elif 'fluxf' in tag: name,unit,confidence,kind='UF membrane flux (flow is an alternative)','L/m²/h','Low','flux'
    elif 'cumulative' in tag: name,unit,confidence,kind='Cumulative runtime','h','Medium','counter'
    elif tag.startswith('advancedtags_') and tag.endswith('_lj'): name,unit,confidence,kind='Cumulative electrical energy','kWh','Medium','counter'
    elif tag.endswith('_ep'): name,unit,scale,confidence,kind='Cumulative electrical energy','kWh',.001,'Low','counter'
    elif tag.endswith('_costheta'): name,unit,scale,confidence,kind='Power factor','1',.001,'High','power_factor'
    elif re.search(r'_u[abc]$',tag): name,unit,scale,confidence,kind='Phase voltage','V',.1,'Medium','voltage'
    elif re.search(r'_i[abc]$',tag): name,unit,scale,confidence,kind='Phase current','A',.1,'Low','current'
    elif tag.endswith('_power'): name,unit,confidence,kind='Active electrical power','kW','Low','power'
    elif any(t in tag for t in ['frequency_feedback','fre_out','fr_out','pumpll']): name,unit,confidence,kind='Motor frequency / requested frequency','Hz','Medium','frequency'
    elif 'current_feedback' in tag or tag.endswith('_a_out'): name,unit,confidence,kind='Motor current feedback','A','Medium','current'
    elif tag.startswith('wg_'):
        suffix=tag.rsplit('_',1)[-1]
        if suffix in ['a1','a2','a3']: name,unit,confidence,kind='Phase voltage','V','High','voltage'
        elif suffix in ['a7','a8','a9']: name,unit,confidence,kind='Phase current','A','High','current'
        elif suffix=='a13': name,unit,confidence,kind='Three-phase active power','kW','High','power'
        elif suffix=='a58': name,unit,confidence,kind='Power factor','1','High','power_factor'
    elif tag.endswith('_fault_count'): name,unit,confidence,kind='Fault count','count','Medium','counter'
    elif re.search(r'_(bt_start|bt_stop|fault|output|rfb|run|start|stop)$',tag):
        name,unit,confidence,kind=tag.rsplit('_',1)[-1].replace('rfb','Running feedback'),'0/1','Medium','binary'
    asset='Plant / meter'
    m=re.search(r'(?:^|zz_|p_)([12])_rohigh_pressure',tag)
    b=re.search(r'ro([1-4])_high_pressure',tag)
    if m: asset='Pump '+m.group(1)
    elif b: asset='RO pump '+b.group(1)
    elif tag.startswith('wg_'): asset=tag.rsplit('_',1)[0]+' (asset association unconfirmed)'
    return dict(tag=tag,label=name,unit=unit,scale=scale,confidence=confidence,kind=kind,asset=asset,
                basis='Assessment assumption from tag context and ranges; not OEM verified')

def dictionary(df):
    return pd.DataFrame([definition(c) for c in df if c not in ['date','plant'] and '__' not in c and not c.startswith('pump_')])

