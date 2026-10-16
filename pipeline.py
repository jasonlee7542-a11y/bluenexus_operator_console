"""Deterministic, non-destructive CSV preparation and prior-only comparisons."""
from io import BytesIO
import hashlib
import numpy as np
import pandas as pd
from tags import definition

FILES={'Plant A':'plant_A_equipment_daily.csv','Plant B':'plant_B_equipment_daily.csv','Performance':'plant_daily_performance.csv'}

def parse_csv(data,source):
    raw=pd.read_csv(BytesIO(data),dtype=str,keep_default_na=False)
    if 'date' not in raw:raise ValueError(f'{source}: required column date is missing.')
    log=[];exact=int(raw.duplicated().sum());df=raw.drop_duplicates().copy()
    log.append(dict(source=source,date='',column='ALL',action='Exact source duplicate rows removed',count=exact,original=''))
    for col in df:
        cleaned=df[col].str.strip();missing=cleaned.str.upper().isin(['','NULL','NAN','NA','N/A'])
        df[col]=cleaned.mask(missing)
    dates=df.date.str.replace('/','-',regex=False)
    parsed=pd.to_datetime(dates.where(dates.str.match(r'^\d{4}-\d{1,2}-\d{1,2}$',na=False)),format='%Y-%m-%d',errors='coerce')
    if parsed.isna().any():raise ValueError(f'{source}: invalid or ambiguous date at source row(s) {(df.index[parsed.isna()]+2).tolist()}. Use YYYY-MM-DD.')
    df['date']=parsed
    for col in df.columns.difference(['date','plant']):
        n=pd.to_numeric(df[col],errors='coerce');invalid=df[col].notna()&(n.isna()|~np.isfinite(n))
        for idx in df.index[invalid]:log.append(dict(source=source,date=str(df.loc[idx,'date'].date()),column=col,action='Invalid numeric -> missing',count=1,original=df.loc[idx,col]))
        df[col]=n.where(np.isfinite(n))
    keys=['plant','date'] if 'plant' in df else ['date']
    if df.duplicated(keys).any():raise ValueError(f'{source}: duplicate daily keys remain after exact-row deduplication. Review the source; conflicting or differently encoded duplicate dates are not averaged or silently discarded.')
    if df.empty:raise ValueError(f'{source}: no records.')
    if 'plant' in df and (df.plant.isna().any() or not df.plant.isin(['Plant A','Plant B']).all()):raise ValueError(f'{source}: plant must be Plant A or Plant B.')
    return df.sort_values(keys).reset_index(drop=True),pd.DataFrame(log),dict(source=source,rows_raw=len(raw),rows_prepared=len(df),sha256=hashlib.sha256(data).hexdigest(),start=str(df.date.min().date()),end=str(df.date.max().date()))

def audit(df,source):
    rows=[]
    for col in df.columns.difference(['date','plant']):
        s=df[col];n=int(s.notna().sum())
        state='Unavailable' if not n else 'All zero — verify channel' if s.dropna().eq(0).all() else 'Constant — context needed' if s.nunique()==1 else 'Varying'
        rows.append(dict(source=source,signal=col,observed=n,missing=int(s.isna().sum()),zeros=int(s.eq(0).sum()),availability_pct=100*n/len(s),minimum=s.min(),median=s.median() if n else np.nan,maximum=s.max(),status=state))
    return pd.DataFrame(rows)

def ratio(numerator,denominator):
    return numerator.where(numerator>=0).div(denominator.where(denominator>0))

def prepare_performance(p,cfg):
    required=['daily_electricity_kwh','effluent_volume_m3','influent_volume_m3']
    if not set(required)<=set(p):raise ValueError('Performance file is missing: '+', '.join(sorted(set(required)-set(p))))
    p=p.copy().sort_values('date').reset_index(drop=True)
    p['sec']=ratio(p.daily_electricity_kwh,p.effluent_volume_m3)
    p['recovery']=ratio(p.effluent_volume_m3,p.influent_volume_m3)*100
    if {'influent_conductivity_us_cm','effluent_conductivity_us_cm'}<=set(p):
        p['conductivity_ratio_pct']=ratio(p.effluent_conductivity_us_cm,p.influent_conductivity_us_cm)*100
    if 'planned_specific_energy_kwh_m3' in p:
        plan=p.planned_specific_energy_kwh_m3.where(p.planned_specific_energy_kwh_m3>0)
        p['plan_sec_gap_pct']=(p.sec/plan-1)*100
        p['energy_gap_plan']=p.daily_electricity_kwh.where(p.daily_electricity_kwh>=0)-p.effluent_volume_m3.where(p.effluent_volume_m3>=0)*plan
    if {'reclaimed_supply_volume_m3','customer_end_volume_m3'}<=set(p):
        supply=p.reclaimed_supply_volume_m3.where(p.reclaimed_supply_volume_m3>=0);customer=p.customer_end_volume_m3.where(p.customer_end_volume_m3>=0)
        p['delivery_gap']=supply-customer;p['delivery_gap_pct']=p.delivery_gap/supply.where(supply>0)*100
    full=p.set_index('date').reindex(pd.date_range(p.date.min(),p.date.max()))
    w=cfg['baseline_days'];minimum=max(3,int(np.ceil(w*cfg['minimum_coverage'])))
    for source,out in [('sec','sec_baseline'),('effluent_volume_m3','output_baseline'),('recovery','recovery_baseline')]:
        vals=full[source].where(full[source]>=0)
        p[out]=full[source].where(vals.notna()).shift(1).rolling(w,min_periods=minimum).median().reindex(p.date).to_numpy()
    p['sec_recent_gap_pct']=(p.sec/p.sec_baseline.where(p.sec_baseline>0)-1)*100
    peer_counts=[];peer_medians=[];peer_dates=[]
    for _,r in p.iterrows():
        history=p.loc[(p.date<r.date)&(p.date>=r.date-pd.Timedelta(days=cfg['peer_lookback_days']))&p.sec.notna()]
        peers=history.loc[history.effluent_volume_m3.between(r.effluent_volume_m3*(1-cfg['peer_output_tolerance']),r.effluent_volume_m3*(1+cfg['peer_output_tolerance']))] if pd.notna(r.sec) else history.iloc[:0]
        peer_counts.append(len(peers));peer_medians.append(peers.sec.median() if len(peers)>=cfg['minimum_peers'] else np.nan)
        peer_dates.append(', '.join(peers.date.dt.strftime('%Y-%m-%d')))
    p['peer_count']=peer_counts;p['peer_median_sec']=peer_medians;p['peer_dates']=peer_dates
    p['peer_gap_pct']=(p.sec/p.peer_median_sec.where(p.peer_median_sec>0)-1)*100
    p['peer_status']=np.select([p.sec.isna(),p.peer_gap_pct.isna(),p.peer_gap_pct>cfg['sec_rise_pct']],['Unavailable SEC','Insufficient similar-output history','Elevated at similar output'],default='Below review threshold at similar output')
    return p

def eligible_signals(e):
    return [c for c in e.select_dtypes('number') if e[c].nunique()>2 and definition(c)['kind'] not in ['counter','binary']]

def load_all(blobs,cfg):
    equipment={};performance={};logs=[];manifest=[];audits=[]
    for key in ['Plant A','Plant B','Performance']:
        frame,log,meta=parse_csv(blobs[key],FILES[key]);logs.append(log);manifest.append(meta)
        if key=='Performance':
            if 'plant' not in frame:raise ValueError('Performance file requires plant column.')
            for plant in ['Plant A','Plant B']:
                subset=frame.loc[frame.plant.eq(plant)].copy()
                if subset.empty:raise ValueError(f'Performance file has no records for {plant}.')
                audits.append(audit(subset,plant+' · Performance'));performance[plant]=prepare_performance(subset,cfg)
        else:
            if 'plant' in frame and not frame.plant.eq(key).all():raise ValueError(f'{key}: equipment plant column conflicts with selected file.')
            equipment[key]=frame;audits.append(audit(frame,key+' · Equipment'))
    return equipment,performance,pd.concat(audits,ignore_index=True),pd.concat(logs,ignore_index=True),pd.DataFrame(manifest)
