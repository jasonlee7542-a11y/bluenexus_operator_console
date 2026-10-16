"""Explicit rules, preserved evidence, grouped episodes; no failure labels."""
import hashlib
import numpy as np
import pandas as pd
from detector import screen
from tags import definition

EVENT_COLS=['plant','date','rule_id','family','priority','asset','signal','title','value','unit','evidence','threshold','basis','confidence']
INC_COLS=EVENT_COLS+['incident_id','start','end','days','minimum','maximum','classification']

def run_length(mask):
    full=mask.reindex(pd.date_range(mask.index.min(),mask.index.max()),fill_value=False).fillna(False)
    return full.groupby((~full).cumsum()).cumsum().astype(int).reindex(mask.index)

def evaluate(equipment,performance,plant,cfg):
    events=[];coverage=[];e=equipment.set_index('date').sort_index();p=performance.set_index('date').sort_index()
    def emit(date,rule,family,signal,title,value,unit,evidence,threshold,priority='Review',asset=None,confidence=None,basis='Provisional assessment rule'):
        d=definition(signal)
        events.append(dict(zip(EVENT_COLS,[plant,pd.Timestamp(date),rule,family,priority,asset or d['asset'],signal,title,float(value),unit,evidence,threshold,basis,confidence or d['confidence']])))
    for tag in e.select_dtypes('number'):
        d=definition(tag);s=e[tag]*d['scale'];kind=d['kind']
        status='Unavailable' if s.notna().sum()==0 else 'All zero — verify channel' if s.dropna().eq(0).all() else 'Constant — context needed' if s.nunique()==1 else 'Available'
        checks=[]
        if kind=='temperature':
            checks+=['High/low temperature review','Absolute-zero consistency']
            for date,v in s[s>cfg['temperature_high_c']].items():
                emit(date,'TEMP_HIGH','temperature',tag,'High temperature reading',v,d['unit'],f'{d["label"]}: {v:.3f} assumed °C; raw reading {e.loc[date,tag]:.3f}.',f'> {cfg["temperature_high_c"]:g} °C','Verify promptly')
            for date,v in s[(s<cfg['temperature_low_c'])&(s>=-273.15)].items():
                emit(date,'TEMP_LOW','temperature',tag,'Unexpected low temperature',v,d['unit'],f'{d["label"]}: {v:.3f} assumed °C. A low reading is possible but needs context.',f'< {cfg["temperature_low_c"]:g} °C')
            for date,v in s[s<-273.15].items():
                emit(date,'TEMP_INVALID','data',tag,'Temperature inconsistent with Celsius scale',v,d['unit'],f'Reading {v:g} is below absolute zero under the assumed unit.','< −273.15 °C',basis='Physical consistency conditional on correct unit')
        bad=pd.Series(False,index=s.index)
        if kind=='recovery':bad=(s<0)|(s>100);checks.append('Recovery 0–100% consistency')
        elif kind=='power_factor':bad=s.abs()>1;checks.append('Power-factor magnitude ≤1')
        elif kind=='binary':bad=s.notna()&~s.isin([0,1]);checks.append('Binary 0/1 consistency')
        elif kind in ['current','voltage','vibration','frequency','counter','turbidity','flux']:bad=s<0;checks.append('Nonnegative magnitude consistency')
        for date,v in s[bad].items():
            emit(date,'VALUE_INVALID','recovery' if kind=='recovery' else 'data',tag,'Reading inconsistent with assumed definition',v,d['unit'],f'{d["label"]}: {v:.4g} {d["unit"]}. Check unit, definition and time boundaries.',checks[-1],basis='Definition consistency; recovery may be affected by inventory/period mismatch')
        if kind=='counter':
            checks.append('Counter decrease')
            for date,v in s[s.diff()<0].items():emit(date,'COUNTER_RESET','data',tag,'Counter decreased',v,d['unit'],f'Counter fell to {v:.4g}; reset, rollover or data issue. Interval consumption is not calculated across this decrease.','Current < previous observed counter')
        if kind in ['vibration','turbidity','temperature'] and s.notna().sum()>=12:
            checks.append('Persistent upward historical deviation')
            r=screen(s,cfg['baseline_days'],cfg['iqr_multiplier']).set_index('date')
            up=r.flag&r.value.gt(r.upper_fence)
            # Extreme temperature already receives an immediate independent rule.
            if kind=='temperature':up=up&r.value.le(cfg['temperature_high_c'])
            streak=run_length(up)
            # Once an episode qualifies, expose all its qualifying dates and group later.
            for date in r.index[up&streak.ge(cfg['persistent_days'])]:
                v=r.loc[date,'value'];emit(date,'PERSISTENT_RISE','quality' if kind=='turbidity' else 'vibration' if kind=='vibration' else 'temperature',tag,'Persistent upward trend',v,d['unit'],f'{d["label"]} {v:.4g}; prior upper IQR fence {r.loc[date,"upper_fence"]:.4g}; {streak.loc[date]} consecutive upward deviations. Operating mode is unconfirmed.',f'Prior {cfg["baseline_days"]}-day Q3 + {cfg["iqr_multiplier"]}×IQR; persistence ≥{cfg["persistent_days"]}')
        coverage.append(dict(plant=plant,signal=tag,meaning=d['label'],kind=kind,status=status,observed=int(s.notna().sum()),missing=int(s.isna().sum()),rule_coverage='; '.join(checks) if checks else 'Statistical exploration only; no absolute engineering rule',confidence=d['confidence']))
    for k in ([1,2] if plant=='Plant A' else [1,2,3,4]):
        f=f'{k}_rohigh_pressure_pump_frequency_feedback_o' if plant=='Plant A' else f'c_m_ro{k}_high_pressure_pump_fre_out'
        electrical=f'zz_{k}_rohigh_pressure_pump_power' if plant=='Plant A' else f'c_m_ro{k}_high_pressure_pump_a_out'
        if f in e and electrical in e:
            for date in e.index[e[f].eq(0)&e[electrical].gt(0)]:
                emit(date,'STATE_CONFLICT','data',f,'Frequency and electrical readings disagree',0,'Hz',f'Frequency 0 Hz; {electrical}={e.loc[date,electrical]:.4g} recorded units. Different daily aggregation or tag mapping may explain the pair.','Frequency =0; paired electrical reading >0',asset=f'RO pump {k}')
    # Daily performance guards.
    for col in ['effluent_volume_m3','influent_volume_m3','daily_electricity_kwh']:
        for date,v in p.loc[p[col]<0,col].items():emit(date,'NEGATIVE_TOTAL','data',col,'Invalid negative daily total',v,'recorded unit',f'{col}={v:g}; excluded from relevant ratio calculations.','Daily consumed/produced total <0',asset='Whole plant',confidence='High for numeric inconsistency')
    for date,r in p.iterrows():
        if pd.notna(r.sec) and ((pd.notna(r.sec_recent_gap_pct) and r.sec_recent_gap_pct>cfg['sec_rise_pct']) or (pd.notna(r.peer_gap_pct) and r.peer_gap_pct>cfg['sec_rise_pct'])):
            evidence=f'SEC {r.sec:.3f} kWh/m³; product {r.effluent_volume_m3:,.0f} m³; electricity {r.daily_electricity_kwh:,.0f} kWh. '
            if pd.notna(r.sec_baseline):evidence+=f'Prior median {r.sec_baseline:.3f} ({r.sec_recent_gap_pct:+.1f}%). '
            if pd.notna(r.peer_gap_pct):evidence+=f'Similar-output median {r.peer_median_sec:.3f}; difference {r.peer_gap_pct:+.1f}%; {int(r.peer_count)} earlier peers.'
            else:evidence+=f'Only {int(r.peer_count)} similar-output peers; insufficient for comparison.'
            title='Energy intensity elevated at similar output' if r.peer_status=='Elevated at similar output' else 'High SEC — similar-output comparison not elevated' if pd.notna(r.peer_gap_pct) else 'High SEC — comparable history insufficient'
            emit(date,'SEC_RISE','energy','sec',title,r.sec,'kWh/m³',evidence,f'> {cfg["sec_rise_pct"]:g}% above prior median or similar-output median',asset='Whole plant',confidence='Calculated ratio; cause unconfirmed')
        if r.effluent_volume_m3==0 and r.daily_electricity_kwh>0:emit(date,'ZERO_PRODUCT_ENERGY','energy','daily_electricity_kwh','Electricity with zero reported product',r.daily_electricity_kwh,'kWh',f'{r.daily_electricity_kwh:g} kWh and zero product; SEC unavailable. Check cleaning/standby and meter validity.','Product=0; electricity>0',asset='Whole plant')
        if pd.notna(r.recovery) and (r.recovery<0 or r.recovery>100):
            emit(date,'RECOVERY_INVALID','recovery','recovery','Product volume exceeds feed',r.recovery,'%',f'Apparent recovery {r.recovery:.2f}%; reconcile storage, periods and meter boundaries.','Apparent recovery outside 0–100%',asset='Whole plant')
        # Fixed Plant A ratio is not an independent process-health indicator.
        elif plant=='Plant B' and pd.notna(r.recovery_baseline) and abs(r.recovery-r.recovery_baseline)>cfg['recovery_change_pp']:
            emit(date,'RECOVERY_CHANGE','recovery','recovery','Recovery changed from recent operation',r.recovery,'%',f'Whole-plant recovery {r.recovery:.2f}% vs prior median {r.recovery_baseline:.2f}%; RO recovery has a different boundary.',f'Change > {cfg["recovery_change_pp"]:g} percentage points',asset='Whole plant')
        if 'delivery_gap_pct' in r and pd.notna(r.delivery_gap_pct) and abs(r.delivery_gap_pct)>cfg['delivery_gap_pct']:
            emit(date,'DELIVERY_GAP','delivery','delivery_gap_pct','Supply and customer totals disagree',r.delivery_gap_pct,'%',f'Supply {r.reclaimed_supply_volume_m3:,.0f} m³; customer {r.customer_end_volume_m3:,.0f} m³; gap {r.delivery_gap:,.0f} m³ ({r.delivery_gap_pct:+.2f}%). Not confirmed leakage.',f'Absolute gap >{cfg["delivery_gap_pct"]:g}% of supply','Verify promptly' if abs(r.delivery_gap_pct)>cfg['large_delivery_gap_pct'] else 'Review',asset='Delivery meters / storage',confidence='Arithmetic verified; boundary unverified')
        if 'effluent_ph' in r and pd.notna(r.effluent_ph):
            v=r.effluent_ph
            if v<0 or v>14:emit(date,'PH_PLAUSIBILITY','quality','effluent_ph','pH outside expected aqueous plant range',v,'pH',f'Reported product pH {v:g}; check calibration and sample identity. Values outside 0–14 are not universally physically impossible.','Provisional plausibility range 0–14',asset='Product-water sample point')
            elif v<cfg['ph_low'] or v>cfg['ph_high']:emit(date,'PH_REVIEW','quality','effluent_ph','Product pH outside review interval',v,'pH',f'Reported product pH {v:g}; confirm against site product specification.',f'Outside {cfg["ph_low"]}–{cfg["ph_high"]}; not a compliance limit',asset='Product-water sample point')
    out=pd.DataFrame(events,columns=EVENT_COLS)
    if not out.empty:out=out.sort_values(['date','rule_id','signal']).reset_index(drop=True)
    return out,pd.DataFrame(coverage)

def group_incidents(events):
    rows=[]
    if events.empty:return pd.DataFrame(columns=INC_COLS)
    for keys,g in events.groupby(['plant','rule_id','signal']):
        g=g.sort_values('date');blocks=g.date.diff().ne(pd.Timedelta(days=1)).cumsum()
        for _,b in g.groupby(blocks):
            first,last=b.iloc[0],b.iloc[-1];r=last.to_dict()
            r.update(incident_id=hashlib.sha256(('|'.join(keys)+'|'+str(first.date.date())).encode()).hexdigest()[:12],start=first.date,end=last.date,days=len(b),minimum=b.value.min(),maximum=b.value.max(),priority='Verify promptly' if b.priority.eq('Verify promptly').any() else 'Review',classification='Data consistency' if last.family=='data' else 'Possible inefficiency' if last.family=='energy' else 'Engineering review')
            rows.append(r)
    inc=pd.DataFrame(rows);inc['_priority']=inc.priority.map({'Verify promptly':0,'Review':1})
    return inc.sort_values(['_priority','end'],ascending=[True,False]).drop(columns='_priority').reset_index(drop=True)
