"""Operator-first screens: exceptions, compact evidence and staged actions."""
from io import BytesIO
import html,json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from tags import definition
from playbooks import playbook,route

BLUE='#276c98';AMBER='#b47a20';RED='#bf4545';MUTED='#718392'
DATA_RULES={'VALUE_INVALID','RECOVERY_INVALID','PH_PLAUSIBILITY','STATE_CONFLICT','COUNTER_RESET','NEGATIVE_TOTAL','TEMP_INVALID'}
TITLES={'TEMP_HIGH':'High temperature','TEMP_LOW':'Low temperature','TEMP_INVALID':'Temperature scale mismatch','PERSISTENT_RISE':'Rising sensor trend','DELIVERY_GAP':'Delivery volume mismatch','RECOVERY_CHANGE':'Recovery change','VALUE_INVALID':'Measurement outside assumed range','PH_REVIEW':'Product pH outside review range','STATE_CONFLICT':'Frequency / electrical mismatch','COUNTER_RESET':'Meter counter decreased','RECOVERY_INVALID':'Water balance inconsistent','NEGATIVE_TOTAL':'Negative daily total','PH_PLAUSIBILITY':'pH measurement needs verification','ZERO_PRODUCT_ENERGY':'Energy used with zero product'}
FIRST={'temperature':'Verify current temperature and sensor units.','vibration':'Compare vibration at the same speed and load.','energy':'Reconcile energy, output and operating hours.','delivery':'Align meter times and reconcile tank storage.','recovery':'Check flow periods and meter boundaries.','quality':'Verify the probe and an independent sample.','data':'Verify tag mapping, scale and source timestamps.'}
REMOTE={
 'temperature':[('Check sensor','Confirm units, timestamp and pump identity.'),('Compare signals','Check speed, current, vibration and recent alarms.'),('Verify independently','Obtain a second temperature measurement if still high.')],
 'vibration':[('Match conditions','Compare the same speed and operating load.'),('Cross-check','Compare axes, temperature and current.'),('Request evidence','Obtain a waveform/spectrum and pressure readings.')],
 'energy':[('Reconcile meters','Align electricity and product reporting periods.'),('Check operation','Review runtime, production demand and cleaning/standby.'),('Compare conditions','Check similar-output days and feed conditions.')],
 'delivery':[('Align meters','Confirm timestamps, units and counter resets.'),('Check inventory','Reconcile tank level changes, transfers and branches.'),('Verify persistence','Check whether the current discrepancy remains.')],
 'recovery':[('Align flows','Confirm feed/product units and reporting periods.'),('Check boundaries','Separate plant recovery, RO recovery and tank storage.'),('Check operation','Review cleaning and process change records.')],
 'quality':[('Verify sample','Confirm timestamp, instrument and sample point.'),('Review calibration','Check probe calibration and feedwater changes.'),('Confirm result','Request an independent sample against the site specification.')],
 'data':[('Verify definition','Confirm tag identity, units and scaling.'),('Check source','Compare PLC/historian and export timestamps.'),('Reconcile records','Check resets and daily aggregation rules.')]
}

def esc(x):return html.escape(str(x))
def number(x,d=0):return '—' if pd.isna(x) else f'{x:,.{d}f}'
def kind(r):return 'data' if r.rule_id in DATA_RULES else r.family

def short_title(r):
 if r.rule_id=='SEC_RISE':
  return 'High energy per m³' if 'not elevated' not in r.title else 'SEC rise explained by output comparison'
 return TITLES.get(r.rule_id,r.title)

def sort_queue(v):
 v=v.copy();v['_rank']=np.where(v.priority.eq('Verify promptly'),0,np.where(v.rule_id.isin(DATA_RULES),3,np.where(v.title.str.contains('not elevated',case=False),2,1)))
 return v.sort_values(['_rank','end'],ascending=[True,False]).drop(columns='_rank')

def badge(text,tone='neutral'):
 return f'<span class="status status-{tone}">{esc(text)}</span>'

def lineplot(fig,height=245,key=None):
 fig.update_layout(template='plotly_white',font=dict(family='Arial, sans-serif',size=11,color='#40586c'),paper_bgcolor='white',plot_bgcolor='white',height=height,margin=dict(l=8,r=10,t=25,b=12),colorway=[BLUE,'#70bacf','#9a8bc0'],hovermode='x unified',legend=dict(orientation='h',y=1.18,x=0,title=None),xaxis=dict(showgrid=False,title=None,zeroline=False),yaxis=dict(gridcolor='#edf1f4',zeroline=False),title=None)
 st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})

def section(title,sub=None):
 st.markdown(f'<div class="section-title">{esc(title)}</div>'+ (f'<div class="micro">{esc(sub)}</div>' if sub else ''),unsafe_allow_html=True)

def kpis(items):
 for c,(label,value,unit,note,tone) in zip(st.columns(len(items)),items):
  c.markdown(f'<div class="stat stat-{tone}"><div class="stat-label">{esc(label)}</div><div class="stat-value">{esc(value)} <span>{esc(unit)}</span></div><div class="stat-note">{esc(note)}</div></div>',unsafe_allow_html=True)

def trail(stages,active):
 parts=[]
 for i,label in enumerate(stages):parts.append(f'<span class="stage {"stage-active" if i==active else ""}"><b>{i+1}</b>{esc(label)}</span>')
 st.markdown('<div class="stagebar">'+''.join(parts)+'</div>',unsafe_allow_html=True)

def overview(ctx):
 p=pd.concat([ctx['perf'][n].loc[ctx['perf'][n].date.between(ctx['start'],ctx['end'])].assign(Plant=n) for n in ctx['plants']],ignore_index=True)
 v=sort_queue(ctx['visible']);valid=p.sec.notna();den=p.loc[valid,'effluent_volume_m3'].sum();sec=p.loc[valid,'daily_electricity_kwh'].sum()/den if den>0 else np.nan
 kpis([('PRODUCT WATER',number(p.effluent_volume_m3.where(p.effluent_volume_m3.ge(0)).sum(min_count=1)),'m³','Selected period','blue'),('ENERGY PER m³',number(sec,3),'kWh/m³','Energy ÷ product · matching valid days','blue'),('PRIORITY EPISODES',str(int(v.priority.eq('Verify promptly').sum())),'','Historical · current check needed','red' if v.priority.eq('Verify promptly').any() else 'neutral'),('PERFORMANCE COVERAGE',f'{int(valid.sum())}/{len(p)}','days','Valid energy and product pair','neutral')])
 section('Plant status','Latest reported performance day in the selected window')
 rows=[]
 for n in ctx['plants']:
  q=p[p.Plant.eq(n)];a=v[v.plant.eq(n)]
  if q.empty:rows.append({'Plant':n,'Last record':'Unavailable','Product · m³':'—','SEC · kWh/m³':'—','SEC vs prior median':'Unscored','Priority episodes':int(a.priority.eq('Verify promptly').sum()),'Operating mode':'Unknown'});continue
  r=q.iloc[-1]
  rows.append({'Plant':n,'Last record':r.date.strftime('%d %b %Y'),'Product · m³':number(r.effluent_volume_m3),'SEC · kWh/m³':number(r.sec,3),'SEC vs prior median':f'{r.sec_recent_gap_pct:+.1f}%' if pd.notna(r.sec_recent_gap_pct) else 'Unscored','Priority episodes':int(a.priority.eq('Verify promptly').sum()),'Operating mode':'Unknown'})
 st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',height=36+35*len(rows),column_config={'Plant':st.column_config.TextColumn(width='small'),'Operating mode':st.column_config.TextColumn(help='No verified production, cleaning or standby labels are available.')})
 left,right=st.columns([1.2,1],gap='large')
 with left:
  section('Investigation queue')
  scope=st.segmented_control('Queue category',['Process & equipment','Data quality'],default='Process & equipment',key='overview_category',label_visibility='collapsed')
  queue=v.loc[v.rule_id.isin(DATA_RULES) if scope=='Data quality' else ~v.rule_id.isin(DATA_RULES)]
  if queue.empty:st.info('No matching flags. Check data coverage.');chosen=None
  else:
   shown=queue.head(5);labels={r.incident_id:f'{"P1" if r.priority=="Verify promptly" else "P2"}  ·  {r.plant}  ·  {short_title(r)}  ·  {r.end:%d %b}' for _,r in shown.iterrows()}
   selected=st.radio('Choose an incident',shown.incident_id.tolist(),format_func=lambda x:labels[x],key=f'overview_queue_{ctx["plant"]}_{ctx["start"]}_{ctx["end"]}_{scope}',label_visibility='collapsed')
   chosen=shown.loc[shown.incident_id.eq(selected)].iloc[0]
   st.caption(f'Showing {len(shown)} of {len(queue)} episodes · P1 verify promptly / P2 review')
  older=ctx['incidents'].loc[ctx['incidents'].plant.isin(ctx['plants'])&ctx['incidents'].priority.eq('Verify promptly')&ctx['incidents'].end.lt(ctx['start'])]
  if not older.empty:st.button(f'{len(older)} earlier priority episode(s) →',key='older_queue',on_click=ctx['go'],args=('Incidents',ctx['plant'],'All available history',older.iloc[0].incident_id))
 with right:
  section('Next action')
  with st.container(border=True):
   if chosen is None:st.write('Select an episode to view the first check.')
   else:
    tone='red' if chosen.priority=='Verify promptly' else 'amber'
    st.markdown(badge(chosen.priority,tone)+' '+badge(chosen.asset),unsafe_allow_html=True)
    st.markdown(f'#### {short_title(chosen)}')
    st.markdown(f'<div class="reading">{number(chosen.value,3)} <span>{esc(chosen.unit)}</span></div><div class="micro">{chosen.start:%d %b}–{chosen.end:%d %b %Y} · {chosen.days} flagged day(s)</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="next-action"><b>1</b><span>{esc(FIRST.get(kind(chosen),FIRST["data"]))}</span></div>',unsafe_allow_html=True)
    st.button('Open investigation →',type='primary',width='stretch',key='open_focused',on_click=ctx['go'],args=('Incidents',chosen.plant,None,chosen.incident_id))
 section('Performance trends')
 a,b=st.columns(2)
 with a:
  with st.container(border=True):
   section('Product water','m³/day');lineplot(px.line(p,x='date',y='effluent_volume_m3',color='Plant'))
 with b:
  with st.container(border=True):
   section('Energy per m³','kWh/m³');lineplot(px.line(p,x='date',y='sec',color='Plant'))

def evidence_chart(row,ctx,height=220):
 source=ctx['eq'][row.plant] if row.signal in ctx['eq'][row.plant] else ctx['perf'][row.plant]
 if row.signal not in source:return
 q=source.loc[source.date.between(row.start-pd.Timedelta(days=14),row.end+pd.Timedelta(days=7))].copy()
 scale=definition(row.signal)['scale'] if row.signal in ctx['eq'][row.plant] else 1
 fig=go.Figure();fig.add_scatter(x=q.date,y=q[row.signal]*scale,name='Reading',line=dict(color=BLUE,width=2),connectgaps=False)
 fig.add_vrect(x0=row.start,x1=row.end+pd.Timedelta(days=1),fillcolor=AMBER,opacity=.10,line_width=0)
 if row.rule_id in ['TEMP_HIGH','TEMP_LOW']:fig.add_hline(y=ctx['cfg']['temperature_high_c' if row.rule_id=='TEMP_HIGH' else 'temperature_low_c'],line_dash='dash',line_color=RED,annotation_text='Review threshold')
 if row.rule_id=='SEC_RISE':fig.add_scatter(x=q.date,y=q.peer_median_sec,name='Similar-output reference',line=dict(color=MUTED,dash='dash'))
 fig.update_yaxes(title=row.unit);lineplot(fig,height)

def save_answer(incident,field,key):
 reviews=dict(st.session_state.get('operator_reviews',{}));record=dict(reviews.get(incident,{}))
 record[field]=st.session_state[key];reviews[incident]=record;st.session_state['operator_reviews']=reviews

def trigger_label(row,cfg):
 return {'TEMP_HIGH':f'> {cfg["temperature_high_c"]:g} °C','TEMP_LOW':f'< {cfg["temperature_low_c"]:g} °C','SEC_RISE':f'> +{cfg["sec_rise_pct"]:g}%','DELIVERY_GAP':f'> ±{cfg["delivery_gap_pct"]:g}%','PH_REVIEW':f'{cfg["ph_low"]}–{cfg["ph_high"]}','RECOVERY_CHANGE':f'> ±{cfg["recovery_change_pp"]:g} pp','VALUE_INVALID':'Definition check','PERSISTENT_RISE':f'{cfg["persistent_days"]} rising days'}.get(row.rule_id,'Consistency check')

def investigation(ctx):
 focus=st.session_state.pop('focus_incident',None)
 if focus is not None:
  st.session_state['case_scope']='All episodes';st.session_state['case_priority']='All priorities';st.session_state['selected_case']=focus
 v=sort_queue(ctx['visible'])
 a,b,c=st.columns([1,1,2]);scope=a.selectbox('Category',['Process & equipment','Data quality','All episodes'],key='case_scope');priority=b.selectbox('Priority',['All priorities','Verify promptly','Review'],key='case_priority')
 c.caption('Historical evidence · verify current conditions before dispatch')
 if scope!='All episodes':v=v.loc[v.rule_id.isin(DATA_RULES) if scope=='Data quality' else ~v.rule_id.isin(DATA_RULES)]
 if priority!='All priorities':v=v[v.priority.eq(priority)]
 if v.empty:st.info('No matching episodes. Change the category or review dates.');return
 left,right=st.columns([.85,1.65],gap='large')
 with left:
  section(f'Episodes · {len(v)}')
  # Pagination keeps a long history from pushing the investigation off screen.
  size=6;pages=int(np.ceil(len(v)/size))
  if focus in v.incident_id.values:st.session_state['case_page']=int(v.index.get_indexer([v.index[v.incident_id.eq(focus)][0]])[0]//size)+1
  if st.session_state.get('case_page',1)>pages:st.session_state['case_page']=1
  page=st.number_input('Page',1,pages,step=1,key='case_page')
  shown=v.iloc[(page-1)*size:page*size]
  preferred=st.session_state.get('selected_case');default=shown.incident_id.tolist().index(preferred) if preferred in shown.incident_id.values else 0
  labels={r.incident_id:f'{"P1" if r.priority=="Verify promptly" else "P2"} · {r.plant} · {short_title(r)}\n{r.asset} · {r.start:%d %b}–{r.end:%d %b} · {r.days}d' for _,r in shown.iterrows()}
  choice_key=f'case_choice_{ctx["plant"]}_{ctx["start"]}_{ctx["end"]}_{scope}_{priority}_{page}'
  if focus in shown.incident_id.values:st.session_state[choice_key]=focus
  selected=st.radio('Select one episode',shown.incident_id.tolist(),index=None if focus in shown.incident_id.values else default,format_func=lambda x:labels[x],key=choice_key,label_visibility='collapsed')
  st.session_state['selected_case']=selected
  csv=v.drop(columns=['evidence','threshold','basis'],errors='ignore').to_csv(index=False,date_format='%Y-%m-%d')
  st.download_button('Export episode list',csv,file_name='incident_list.csv',mime='text/csv',width='stretch')
 row=v.loc[v.incident_id.eq(selected)].iloc[0];family=kind(row);book=playbook(family,row.asset)
 review=st.session_state.get('operator_reviews',{}).get(selected,{})
 with right:
  st.markdown(badge(row.priority,'red' if row.priority=='Verify promptly' else 'amber')+' '+badge(row.plant)+' '+badge(row.asset),unsafe_allow_html=True)
  st.subheader(short_title(row))
  if row.signal in ctx['eq'][row.plant]:st.markdown(badge('Tag meaning / units provisional'),unsafe_allow_html=True)
  st.caption(f'{row.start:%d %b} – {row.end:%d %b %Y} · {row.days} flagged day(s) · Resolution unverified')
  a,b,c=st.columns(3);a.metric('Last flagged reading',number(row.value,3)+' '+row.unit);b.metric('Review trigger',trigger_label(row,ctx['cfg']));c.metric('Current check',{'Not checked':'Unverified','Confirmed in latest readings':'Confirmed','Not confirmed in latest readings':'Not present'}[review.get('current','Not checked')])
  evidence_chart(row,ctx)
  if row.rule_id=='SEC_RISE':
   r=ctx['perf'][row.plant].loc[ctx['perf'][row.plant].date.eq(row.end)].iloc[0]
   if pd.isna(r.peer_gap_pct):st.markdown(badge(f'{int(r.peer_count)}/{ctx["cfg"]["minimum_peers"]} peer days · comparison unavailable','amber'),unsafe_allow_html=True)
   elif r.peer_gap_pct<=ctx['cfg']['sec_rise_pct']:st.markdown(badge(f'Similar-output SEC {r.peer_gap_pct:+.1f}% · below review trigger'),unsafe_allow_html=True)
   else:st.markdown(badge(f'Similar-output SEC +{r.peer_gap_pct:.1f}%','amber'),unsafe_allow_html=True)
  stage=st.segmented_control('Investigation step',['1 · Verify','2 · Remote checks','3 · Site decision'],default=None if 'step_'+selected in st.session_state else '1 · Verify',key='step_'+selected,label_visibility='collapsed')
  current=review.get('current','Not checked');checked=review.get('remote','Not completed')
  if stage=='1 · Verify':
   section('Verify the current condition')
   options=['Not checked','Confirmed in latest readings','Not confirmed in latest readings']
   st.radio('Current reading check',options,index=options.index(current),key='verify_widget_'+selected,on_change=save_answer,args=(selected,'current','verify_widget_'+selected))
   st.caption('Check the current timestamp, instrument units and actual asset identity.')
   st.button('Continue to remote checks →',key='next_remote_'+selected,on_click=lambda k:st.session_state.update({k:'2 · Remote checks'}),args=('step_'+selected,),type='primary')
  elif stage=='2 · Remote checks':
   section('Complete these checks')
   steps=REMOTE.get(family,REMOTE['data'])
   for i,(title,copy) in enumerate(steps,1):
    a,b=st.columns([.12,1]);a.markdown(f'<span class="step-number">{i}</span>',unsafe_allow_html=True)
    with b:st.markdown(f'**{title}**');st.caption(copy)
   options=['Not completed','Still unexplained after checks','Explained by records / independent verification']
   st.radio('Investigation result',options,index=options.index(checked),key='remote_widget_'+selected,on_change=save_answer,args=(selected,'remote','remote_widget_'+selected))
   with st.expander('Detailed checklist & possible causes'):
    for step in book['remote']:st.write('• '+step)
    st.write('Possible causes: '+ '; '.join(book['causes']))
   st.button('Continue to site decision →',key='next_site_'+selected,on_click=lambda k:st.session_state.update({k:'3 · Site decision'}),args=('step_'+selected,),type='primary')
  else:
   section('Attendance recommendation')
   label,explanation=route(family,row.priority,current,checked)
   st.markdown(f'<div class="decision"><div class="decision-title">{esc(label)}</div><div>{esc(explanation)}</div></div>',unsafe_allow_html=True)
   st.caption(f'Current check: {current} · Remote result: {checked}')
   with st.expander('Technician handoff',expanded='Site' in label or 'site' in label):
    st.markdown('**Start here**');st.write(book['location'])
    for i,step in enumerate(book['site'],1):st.write(f'{i}. {step}')
    st.caption('Confirm the equipment ID. Follow site isolation and OEM procedures for physical work.')
   with st.expander('Remote AI scope'):
    st.write(book['ai']);st.caption('No AquaxGo, PLC or dispatch connection is configured.')
  with st.expander('Evidence & rule details'):
   st.write(row.evidence);st.write('Trigger: '+row.threshold);st.caption(row.basis+' · '+row.confidence)
   st.code(row.signal,language=None);st.caption('Missing evidence: '+book['missing'])
   detail=ctx['events'].loc[ctx['events'].plant.eq(row.plant)&ctx['events'].rule_id.eq(row.rule_id)&ctx['events'].signal.eq(row.signal)&ctx['events'].date.between(row.start,row.end)]
   st.dataframe(detail[['date','value','unit']],hide_index=True,width='stretch')
  notes=st.text_input('Investigation notes',value=review.get('notes',''),key='notes_'+selected,on_change=save_answer,args=(selected,'notes','notes_'+selected),placeholder='Confirmed asset ID, checks completed, supporting readings…')
  label,explanation=route(family,row.priority,review.get('current','Not checked'),review.get('remote','Not completed'))
  report=['# Investigation handoff',f'{row.plant} / {row.asset} / {short_title(row)}',f'Incident {selected}; {row.start:%Y-%m-%d} to {row.end:%Y-%m-%d}',f'Evidence: {row.evidence}',f'Trigger: {row.threshold}',f'Current check: {review.get("current","Not checked")}',f'Remote result: {review.get("remote","Not completed")}',f'Route: {label}. {explanation}','## Remote checks']+book['remote']+['## Technician location',book['location']]+book['site']+['## Escalation',book['trigger'],'## Missing evidence',book['missing'],'## Notes',notes or 'None','## Source manifest',ctx['manifest'].to_csv(index=False),'## Settings',json.dumps(ctx['cfg'],indent=2),'Historical evidence only; no control commands or dispatch have been sent.']
  st.download_button('Download technician / remote handoff','\n\n'.join(report),file_name=f'{selected}_handoff.md',mime='text/markdown',width='stretch')

def energy(ctx):
 n=st.selectbox('Facility',ctx['plants'],key='energy_plant');p=ctx['perf'][n].loc[ctx['perf'][n].date.between(ctx['start'],ctx['end'])]
 if p.empty:st.info('No performance data in these dates.');return
 valid=p.sec.notna();den=p.loc[valid,'effluent_volume_m3'].sum();sec=p.loc[valid,'daily_electricity_kwh'].sum()/den if den>0 else np.nan
 match=p.peer_gap_pct.notna();above=p.peer_gap_pct.gt(ctx['cfg']['sec_rise_pct'])
 kpis([('ENERGY PER m³',number(sec,3),'kWh/m³','Selected period','blue'),('ABOVE REFERENCE',str(int(above.sum())),'days','Similar-output comparison','amber' if above.any() else 'neutral'),('COMPARABLE HISTORY',f'{int(match.sum())}/{len(p)}','days','At least 5 earlier similar-output days','neutral'),('ELECTRICITY',number(p.daily_electricity_kwh.where(p.daily_electricity_kwh.ge(0)).sum(min_count=1)),'kWh','Selected period','neutral')])
 left,right=st.columns([1.6,1])
 with left:
  with st.container(border=True):
   section('Energy per m³','Dashed line: similar-output reference')
   fig=go.Figure();fig.add_scatter(x=p.date,y=p.sec,name='Observed',line_color=BLUE);fig.add_scatter(x=p.date,y=p.peer_median_sec,name='Reference',line=dict(color=MUTED,dash='dash'));f=p.loc[above];fig.add_scatter(x=f.date,y=f.sec,mode='markers',name='Above reference',marker=dict(color=AMBER,size=8));fig.update_yaxes(title='kWh/m³');lineplot(fig,300)
 with right:
  with st.container(border=True):
   section('Energy versus production');lineplot(px.scatter(p,x='effluent_volume_m3',y='daily_electricity_kwh',hover_data=['date','sec'],labels={'effluent_volume_m3':'Product · m³/day','daily_electricity_kwh':'kWh/day'}),300)
 queue=ctx['visible'].loc[ctx['visible'].plant.eq(n)&ctx['visible'].family.eq('energy')]
 if not queue.empty:
  section('Energy investigations');r=sort_queue(queue).iloc[0];st.button(f'{short_title(r)} · {r.end:%d %b} →',on_click=ctx['go'],args=('Incidents',n,None,r.incident_id),type='primary')
 with st.expander('Daily comparisons & method'):
  st.caption(f'Prior {ctx["cfg"]["peer_lookback_days"]} days · production within ±{ctx["cfg"]["peer_output_tolerance"]:.0%} · minimum {ctx["cfg"]["minimum_peers"]} peers. Operating mode and feed conditions remain unconfirmed. No membrane normalization is claimed.')
  st.dataframe(p[['date','effluent_volume_m3','daily_electricity_kwh','sec','peer_count','peer_gap_pct','peer_status']],hide_index=True,width='stretch')
  if 'energy_gap_plan' in p:
   st.write(f'Net energy versus supplied plan: {number(p.energy_gap_plan.sum(min_count=1))} kWh. Positive daily gaps: {number(p.energy_gap_plan.clip(lower=0).sum(min_count=1))} kWh. These are not verified achievable savings.')

def water(ctx):
 n=st.selectbox('Facility',ctx['plants'],key='water_plant');p=ctx['perf'][n].loc[ctx['perf'][n].date.between(ctx['start'],ctx['end'])]
 if p.empty:st.info('No water-performance data in these dates.');return
 r=p.iloc[-1];gap=p.delivery_gap_pct.abs().max() if 'delivery_gap_pct' in p else np.nan
 kpis([('VOLUME RECOVERY',number(r.recovery,1),'%',f'Latest · {r.date:%d %b}','neutral'),('LARGEST DELIVERY GAP',number(gap,1),'%','Meter reconciliation required' if gap>10 else 'Selected period','amber' if gap>10 else 'neutral'),('PRODUCT pH',number(r.get('effluent_ph',np.nan),2),'',f'Latest · {r.date:%d %b}','neutral'),('CONDUCTIVITY RATIO',number(r.get('conductivity_ratio_pct',np.nan),2),'%','Product / feed · latest','neutral')])
 a,b=st.columns(2)
 with a:
  with st.container(border=True):
   section('Supply versus customer','m³/day')
   if {'reclaimed_supply_volume_m3','customer_end_volume_m3'}<=set(p):lineplot(px.line(p.rename(columns={'reclaimed_supply_volume_m3':'Supply','customer_end_volume_m3':'Customer'}),x='date',y=['Supply','Customer']))
 with b:
  with st.container(border=True):
   section('Recovery','Product / feed · %')
   if p.recovery.dropna().round(4).nunique()<=1:st.metric('Fixed reported ratio',number(p.recovery.median(),1)+'%');st.caption('Not an independent membrane-health indicator.')
   else:lineplot(px.line(p,x='date',y='recovery'))
 a,b=st.columns(2)
 with a:
  with st.container(border=True):
   section('Product pH','Shading: provisional review interval')
   if 'effluent_ph' in p:
    fig=px.line(p,x='date',y='effluent_ph');fig.add_hrect(y0=ctx['cfg']['ph_low'],y1=ctx['cfg']['ph_high'],fillcolor=BLUE,opacity=.06,line_width=0);lineplot(fig)
 with b:
  with st.container(border=True):
   section('Conductivity ratio','Product / feed · %')
   if 'conductivity_ratio_pct' in p:lineplot(px.line(p,x='date',y='conductivity_ratio_pct'))
 queue=ctx['visible'].loc[ctx['visible'].plant.eq(n)&ctx['visible'].family.isin(['quality','recovery','delivery'])]
 if not queue.empty:
  r=sort_queue(queue).iloc[0];st.button(f'Investigate {short_title(r).lower()} →',on_click=ctx['go'],args=('Incidents',n,None,r.incident_id),type='primary')
 with st.expander('Quality limits, chemical records & interpretation'):
  st.caption('Review thresholds are provisional, not compliance limits. Volume discrepancies require storage/time reconciliation. Chemical dose units are unverified.')
  cols=[c for c in p if c.startswith('actual_') and 'dose' in c]
  st.dataframe(pd.DataFrame([{'Chemical':c.replace('actual_','').replace('_dose_reported','').replace('_',' '),'Recorded days':int(p[c].notna().sum()),'Period days':len(p)} for c in cols]),hide_index=True,width='stretch')
