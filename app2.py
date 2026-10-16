"""BlueNexus operator review. Run: python -m streamlit run app2.py"""
from pathlib import Path
from io import BytesIO
import html
import json
import zipfile
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pipeline import FILES,load_all,eligible_signals
from rules import evaluate,group_incidents
from tags import definition,dictionary
from ranking import rank_signals
import operator_ui as ui
from playbooks import playbook,route,SOURCES

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='BlueNexus | Operator Review',layout='wide',initial_sidebar_state='expanded')
st.markdown('<style>'+(ROOT/'dashboard.css').read_text()+'</style>',unsafe_allow_html=True)

@st.cache_data(show_spinner=False,max_entries=8)
def analyse(blobs,cfg):
    eq,perf,audit,logs,manifest=load_all(blobs,cfg)
    ev=[];cov=[]
    for plant in ['Plant A','Plant B']:
        event,coverage=evaluate(eq[plant],perf[plant],plant,cfg);ev.append(event);cov.append(coverage)
    events=pd.concat(ev,ignore_index=True)
    return eq,perf,audit,logs,manifest,events,group_incidents(events),pd.concat(cov,ignore_index=True)

@st.cache_data(show_spinner=False,max_entries=8)
def scan(frame,signals,days,mult):return rank_signals(frame,signals,days,mult)

def go_page(name,plant=None,history=None,incident=None):
    st.session_state['page']=name
    if plant:st.session_state['plant']=plant
    if history:st.session_state['period']=history
    if incident:st.session_state['focus_incident']=incident

def plot(fig,key=None):
    fig.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='white',font=dict(color='#29475d',size=12),colorway=['#287eae','#78cde0','#d89b50','#667caa'],hovermode='x unified',margin=dict(l=20,r=20,t=35,b=25),height=330,legend=dict(orientation='h',y=1.16,x=0),xaxis=dict(showgrid=False,zeroline=False),yaxis=dict(gridcolor='#eef2f6',zeroline=False))
    st.plotly_chart(fig,width='stretch',key=key)

def csv_button(label,df,name,key=None):st.download_button(label,df.to_csv(index=False,date_format='%Y-%m-%d').encode(),file_name=name,mime='text/csv',key=key)

def fmt(v,suffix='',digits=0):return 'Unavailable' if pd.isna(v) else f'{v:,.{digits}f}{suffix}'

def render_metrics(p):
    cols=st.columns(3);valid=p.sec.notna() if not p.empty else pd.Series(False,index=p.index)
    water=p.effluent_volume_m3.where(p.effluent_volume_m3>=0).sum(min_count=1)
    energy=p.daily_electricity_kwh.where(p.daily_electricity_kwh>=0).sum(min_count=1)
    denom=p.loc[valid,'effluent_volume_m3'].sum();weighted=p.loc[valid,'daily_electricity_kwh'].sum()/denom if denom>0 else np.nan
    cols[0].metric('Treated water · m³',fmt(water));cols[1].metric('Electricity · kWh',fmt(energy));cols[2].metric('Energy per m³ · kWh/m³',fmt(weighted,digits=3))
    st.caption(f'{len(p)} reported performance days; SEC uses total energy ÷ total product on {int(valid.sum())} matching valid days. Missing readings are not zero.')

def in_period(df):return df.loc[df.date.between(start,end)]

def friendly(tag):
    d=definition(tag);return d['asset']+' · '+d['label']

with st.sidebar:
    st.markdown('<div class="sidebar-brand">Blue<span>Nexus</span></div><div class="sidebar-tag">WATER OPERATIONS CENTRE</div>',unsafe_allow_html=True)
    st.radio('Workspace',['Overview','Energy','Water & Quality','Equipment','Incidents','Data & Methods'],key='page',label_visibility='collapsed')
    st.markdown('---')
    plant=st.selectbox('Plant',['All plants','Plant A','Plant B'],key='plant')
    period=st.selectbox('Review period',['Performance period','All available history','Latest 30 equipment days','Custom dates'],key='period')
    st.markdown('---')
    with st.expander('Data inputs'):
        st.caption('Defaults to the three CSV files beside app2.py. Uploads replace inputs for this session only.')
        uploads={k:st.file_uploader(FILES[k],type=['csv'],key='upload_'+k) for k in FILES}
    st.caption('Historical CSV review. No live plant control or automatic dispatch.')
try:
    cfg=json.loads((ROOT/'settings.json').read_text())
    blobs={k:(uploads[k].getvalue() if uploads[k] is not None else (ROOT/FILES[k]).read_bytes()) for k in FILES}
    with st.spinner('Preparing data and engineering review…'):
        eq,perf,audits,logs,manifest,events,incidents,coverage=analyse(blobs,cfg)
except (OSError,ValueError,KeyError,pd.errors.ParserError) as exc:
    st.title('Load plant data');st.error(str(exc));st.info('Place all three CSVs in the app folder, or upload each file under Data inputs. Keep settings.json and all supplied Python modules beside app2.py.');st.stop()
plants=['Plant A','Plant B'] if plant=='All plants' else [plant]
first=min(eq[x].date.min() for x in plants);last=max(eq[x].date.max() for x in plants)
if period=='Performance period':start=min(perf[x].date.min() for x in plants);end=max(perf[x].date.max() for x in plants)
elif period=='Latest 30 equipment days':start=last-pd.Timedelta(days=29);end=last
elif period=='Custom dates':
    dates=st.sidebar.date_input('Start and end',value=(first.date(),last.date()),min_value=first.date(),max_value=last.date())
    if len(dates)!=2:st.info('Select both a start and end date.');st.stop()
    start,end=map(pd.Timestamp,dates)
else:start,end=first,last
st.sidebar.caption(f'{start:%d %b %Y} — {end:%d %b %Y}')
st.sidebar.caption(f'Latest equipment record: {last:%d %b %Y}')
page=st.session_state['page']
st.markdown('<div class="brand">AQUAXGO / OPERATIONS ANALYTICS</div>',unsafe_allow_html=True)
st.title(page)
st.caption(f'{plant}  /  {start:%d %b} – {end:%d %b %Y}  /  Historical CSV · not live')
visible=incidents.loc[incidents.plant.isin(plants)&incidents.start.le(end)&incidents.end.ge(start)].copy()

ctx=dict(eq=eq,perf=perf,events=events,incidents=incidents,visible=visible,cfg=cfg,manifest=manifest,plants=plants,plant=plant,start=start,end=end,go=go_page)
if page=='Overview':ui.overview(ctx)
elif page=='Energy':ui.energy(ctx)
elif page=='Water & Quality':ui.water(ctx)

elif page=='Equipment':
    st.caption('Ranked signals · select a measurement to inspect its trend')
    name=st.selectbox('Equipment plant',plants,key='equipment_plant')
    e=eq[name];signals=eligible_signals(e)
    a,b=st.columns(2);days=a.slider('Prior baseline · calendar days',7,30,cfg['baseline_days']);mult=b.slider('Statistical sensitivity · IQR multiplier',1.,3.,float(cfg['iqr_multiplier']),.25)
    if not signals:st.info('No varying continuous equipment signals available.')
    else:
        ranking,screened=scan(e[['date']+signals],signals,days,mult)
        # Recompute count columns for reporting dates, retaining full baseline history.
        for i,r in ranking.iterrows():
            q=screened[r.signal].loc[screened[r.signal].date.between(start,end)];screened[r.signal]=q
            scored=q.status.isin(['Within statistical band','Statistical deviation']);f=q.flag
            ranking.loc[i,['flagged_days','scored_days','unscored_days']]=[int(f.sum()),int(scored.sum()),int((~scored).sum())]
            ranking.loc[i,'flag_rate_pct']=100*f.sum()/scored.sum() if scored.sum() else np.nan
            ranking.loc[i,'upward_flags']=int((f&q.value.gt(q.upper_fence)).sum())
            ranking.loc[i,'downward_flags']=int((f&q.value.lt(q.lower_fence)).sum())
            ranking.loc[i,'last_flag']=q.loc[f,'date'].max()
            ranking.loc[i,'status']='Flags to investigate' if f.any() else 'No statistical flags' if scored.any() else 'Unscored — insufficient / flat reference'
        ranking=ranking.sort_values(['flagged_days','scored_days','signal'],ascending=[False,False,True]).reset_index(drop=True);ranking['rank']=range(1,len(ranking)+1)
        st.caption('Sorted by flagged days · counts indicate review workload, not danger.')
        display=ranking[['rank','name','flagged_days','flag_rate_pct','scored_days','unscored_days']].copy()
        st.dataframe(display,hide_index=True,width='stretch',height=260,column_config={'rank':st.column_config.NumberColumn('Rank',width='small'),'name':st.column_config.TextColumn('Equipment · Measurement',width='large'),'flagged_days':'Flagged days','flag_rate_pct':st.column_config.NumberColumn('Flag rate',format='%.1f%%'),'scored_days':'Scored days','unscored_days':'Unscored days'})
        target=st.selectbox('Ranked signal',ranking.signal.tolist(),format_func=lambda t:f'{int(ranking.loc[ranking.signal.eq(t),"rank"].iloc[0]):02d} · {friendly(t)}',key=f'signal_{name}_{days}_{mult}_{start}_{end}')
        q=screened[target];d=definition(target)
        if q.empty:st.info('No equipment readings fall in these dates.')
        else:
            a,b,c=st.columns(3);a.metric('Statistical flags',int(q.flag.sum()));b.metric('Scored days',int(q.status.isin(['Within statistical band','Statistical deviation']).sum()));c.metric('Engineering flag days',events.loc[events.plant.eq(name)&events.signal.eq(target)&events.date.between(start,end),'date'].nunique())
            fig=go.Figure();fig.add_scatter(x=q.date,y=q.lower_fence*d['scale'],name='Lower statistical band',line_color='#c5dce1');fig.add_scatter(x=q.date,y=q.upper_fence*d['scale'],name='Upper statistical band',fill='tonexty',fillcolor='rgba(8,127,140,.08)',line_color='#c5dce1');fig.add_scatter(x=q.date,y=q.value*d['scale'],name=d['label'],line_color='#287eae');f=q[q.flag];fig.add_scatter(x=f.date,y=f.value*d['scale'],mode='markers',name='Statistical flag',marker_color='#d58b36')
            eng=events.loc[events.plant.eq(name)&events.signal.eq(target)&events.date.between(start,end)]
            fig.add_scatter(x=eng.date,y=eng.value,mode='markers',name='Engineering review',marker=dict(color='#bb4242',symbol='diamond',size=8))
            if d['kind']=='temperature':fig.add_hline(y=cfg['temperature_high_c'],line_dash='dash',annotation_text='Provisional high review');fig.add_hline(y=cfg['temperature_low_c'],line_dash='dash')
            fig.update_layout(yaxis_title='Assumed '+d['unit']);plot(fig)
            st.caption(f'Original tag: {target} · Scale: raw × {d["scale"]:g} · Meaning/unit confidence: {d["confidence"]}. Statistical bands are not safe limits.')
            if q.flag.any():
                down=int((q.flag&q.value.lt(q.lower_fence)).sum());up=int(q.flag.sum())-down
                st.caption(f'{up} rising / {down} falling deviations · verify operating load and run state.')
        with st.expander('Compare related signals'):
            query=st.text_input('Filter signals',key='overlay_search');choices=[c for c in signals if query.lower() in c.lower()];cols=st.columns(4);selected=[]
            for i,tag in enumerate(choices):
                if cols[i%4].checkbox(friendly(tag),key='overlay_'+name+tag,help=tag):selected.append(tag)
            if selected:
                overlay=in_period(e)[['date']+selected].copy()
                for col in selected:
                    span=overlay[col].max()-overlay[col].min();overlay[col]=(overlay[col]-overlay[col].min())/span*100 if span>0 else overlay[col].where(overlay[col].isna(),0)
                plot(px.line(overlay,x='date',y=selected,labels={'value':'Within-period min–max index · 0–100','date':'Date'},title='Signal shape comparison'));st.caption('A shared trend is an investigation clue, not a calculated causal relationship.')
        csv_button('Download ranking',ranking,'signal_ranking.csv')
        st.button('Open '+name+' engineering incidents',on_click=go_page,args=('Incidents',name))

elif page=='Incidents':ui.investigation(ctx)

elif page=='Data & Methods':
    st.write('Data reliability, engineering assumptions and reproducible exports.')
    a,b,c=st.columns(3)
    a.metric('Missing numeric readings',int(audits.loc[audits.source.str.startswith(tuple(plants)),'missing'].sum()))
    b.metric('Exact duplicate source rows removed',int(logs.loc[logs.action.eq('Exact source duplicate rows removed'),'count'].sum()))
    c.metric('Invalid numeric tokens',int(logs.loc[logs.action.eq('Invalid numeric -> missing'),'count'].sum()))
    st.caption('Audit and source-file metrics use the complete inputs. They are not limited by the page date filter. Duplicate/invalid-token counts cover all supplied files.')
    with st.expander('Cleaning decisions',expanded=True):
        st.dataframe(pd.DataFrame([
            ['Exact duplicate source rows','Remove and count; preserve source files'],
            ['Duplicate plant/date keys','Stop with an actionable error; do not average conflicting daily records'],
            ['Blank / NULL / NA','Missing; leave missing'],
            ['Invalid numeric / infinite values','Log source token, then mark missing'],
            ['Zero','Preserve as observed; interpret using the tag and operating context'],
            ['Constant or all-zero channel','Retain in audit; avoid treating it as proof of healthy equipment'],
            ['Extreme sensor reading','Preserve and flag; no clipping or interpolation'],
            ['Negative totals / zero denominators','Preserve input; exclude from affected ratio calculations'],
            ['Calendar gaps','Keep gaps; break persistence and reduce baseline coverage'],
            ['Counter decrease','Flag reset/rollover; do not calculate consumption across it']
        ],columns=['Condition','Handling']),hide_index=True,width='stretch')
    st.subheader('Channel coverage')
    source=st.selectbox('Source to inspect',audits.source.unique());a=audits.loc[audits.source.eq(source)]
    st.dataframe(a,hide_index=True,width='stretch')
    with st.expander('Source files and parsing log'):
        st.dataframe(manifest,hide_index=True,width='stretch');st.dataframe(logs.astype(str),hide_index=True,width='stretch')
    with st.expander('Tag meanings, units and engineering coverage'):
        for name in plants:
            st.markdown('**'+name+'**');st.dataframe(dictionary(eq[name]),hide_index=True,width='stretch')
        st.dataframe(coverage.loc[coverage.plant.isin(plants)],hide_index=True,width='stretch')
        st.write('Tag meanings and scales are assessment assumptions. Plant A electrical current/power scaling does not reconcile; those signals support relative trends only. Whole-plant SEC uses performance-file totals. Vibration RMS/peak convention and precise sensor location are unconfirmed.')
    with st.expander('Rules and reference windows'):
        st.json(cfg)
        st.write('Engineering thresholds are provisional and independent of statistical baselines. High/low temperatures are flagged immediately. Statistical references exclude the current day and future data; 14 days and 80% coverage require 12 prior observations. Flat references remain unscored. Persistent rising temperature/vibration/turbidity is surfaced after three consecutive deviations; the incident begins on the first day meeting that persistence rule, not necessarily the first physical change. Changing page dates does not retrain or truncate baselines.')
        st.write('Energy: flag >20% above prior median or prior similar-output median. Similar output means ±20% volume over up to 60 prior days, minimum five peers. Operating modes, feed changes and cleaning remain unconfirmed. No historical electricity regression or machine-learning health score is used: those need separately documented validation.')
        st.write('Water: Plant B whole-plant recovery change >10 percentage points from recent median; supply/customer discrepancy >10%, prompt reconciliation above 50%; product pH outside 6.5–8.5. All are assessment review rules. These are not certified operating, safety or regulatory limits. Plant A fixed 75% ratio is not used as an independent recovery-deterioration flag.')
    with st.expander('Engineering references and limitations'):
        st.write('General troubleshooting guidance is informed by the references below. No manufacturer-specific numerical limit is claimed for these anonymized assets. Normalized membrane performance, pressure-drop trends, verified labels and maintenance outcomes are unavailable.')
        for label,url in SOURCES.items():st.markdown(f'[{label}]({url})')
        st.write('The standard PFD does not establish exact asset locations. The handoff tells technicians which measurement points to confirm, not an invented physical bay. Qualified personnel must follow site isolation and OEM maintenance procedures. This prototype does not issue chemical-dose, pressure, speed or shutdown commands.')
    payload=BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
        tables={'column_audit.csv':audits,'parsing_log.csv':logs,'source_manifest.csv':manifest,'daily_events.csv':events,'grouped_incidents.csv':incidents,'rule_coverage.csv':coverage}
        for name in ['Plant A','Plant B']:
            tables[name.replace(' ','_')+'_prepared_equipment.csv']=eq[name]
            tables[name.replace(' ','_')+'_performance.csv']=perf[name]
            tables[name.replace(' ','_')+'_tag_dictionary.csv']=dictionary(eq[name])
        for filename,table in tables.items():z.writestr(filename,table.to_csv(index=False,date_format='%Y-%m-%d'))
        z.writestr('settings.json',json.dumps(cfg,indent=2));z.writestr('view.json',json.dumps({'plant':plant,'start':str(start.date()),'end':str(end.date()),'version':'Operator review 1.0'},indent=2))
    st.download_button('Download reproducible analysis bundle',payload.getvalue(),file_name='BlueNexus_analysis_bundle.zip',mime='application/zip')
    st.caption('Exports contain the supplied plant data and should be handled under the challenge confidentiality requirements.')

st.divider()
st.caption('BlueNexus · Historical decision support · No live control or dispatch')
