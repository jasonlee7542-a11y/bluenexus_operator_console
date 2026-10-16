"""Run: python -m unittest -v test_core.py (no plant files needed)."""
import unittest,json
from pathlib import Path
import numpy as np
import pandas as pd
from pipeline import parse_csv,ratio,prepare_performance
from detector import screen
from rules import evaluate,group_incidents
from playbooks import route
CFG=json.loads(Path(__file__).with_name('settings.json').read_text())
class CoreTests(unittest.TestCase):
 def test_duplicates_missing_zero_and_extreme_preserved(self):
  d,log,_=parse_csv(b'date,temp\n2026-01-01,212\n2026-01-01,212\n2026-01-02,NULL\n2026-01-03,0\n','test')
  self.assertEqual(len(d),3);self.assertEqual(d.temp.iloc[0],212);self.assertTrue(pd.isna(d.temp.iloc[1]));self.assertEqual(d.temp.iloc[2],0);self.assertEqual(log.iloc[0]['count'],1)
 def test_conflicting_daily_keys_block(self):
  with self.assertRaisesRegex(ValueError,'duplicate daily keys'):parse_csv(b'date,x\n2026-01-01,1\n2026-01-01,2\n','test')
 def test_ambiguous_dates_block(self):
  with self.assertRaisesRegex(ValueError,'ambiguous date'):parse_csv(b'date,x\n01/02/2026,1\n','test')
 def test_invalid_numeric_logged(self):
  d,l,_=parse_csv(b'date,x\n2026-01-01,bad\n2026-01-02,inf\n','test')
  self.assertTrue(d.x.isna().all());self.assertEqual(len(l[l.action.eq('Invalid numeric -> missing')]),2)
 def test_ratio_excludes_zero_negative(self):
  r=ratio(pd.Series([4.,4.,-4.,0.]),pd.Series([2.,0.,2.,2.]))
  self.assertEqual(r.iloc[0],2);self.assertTrue(r.iloc[1:3].isna().all());self.assertEqual(r.iloc[3],0)
 def test_prior_baseline_excludes_current_and_future(self):
  s=pd.Series(np.arange(30.),index=pd.date_range('2026-01-01',periods=30))
  r=screen(s);s.iloc[20:]=999;r2=screen(s)
  self.assertEqual(r.reference_median.iloc[20],r2.reference_median.iloc[20]);self.assertTrue(r.flag.iloc[:20].equals(r2.flag.iloc[:20]))
 def test_flat_reference_unscored(self):
  r=screen(pd.Series([1.]*20,index=pd.date_range('2026-01-01',periods=20)))
  self.assertFalse(r.flag.any());self.assertEqual(r.status.iloc[-1],'Flat reference: no IQR decision')
 def performance(self):
  return prepare_performance(pd.DataFrame({'date':pd.date_range('2026-01-01',periods=30),'daily_electricity_kwh':[100.]*30,'effluent_volume_m3':[100.]*30,'influent_volume_m3':[125.]*30}),CFG)
 def test_peer_comparison_excludes_future(self):
  p=self.performance();p.loc[20:,'daily_electricity_kwh']=10000;p2=prepare_performance(p,CFG)
  self.assertEqual(p2.peer_median_sec.iloc[20],1);self.assertEqual(p2.peer_count.iloc[20],20);self.assertTrue(pd.isna(p2.peer_median_sec.iloc[4]))
 def test_temperature_rules_and_episode_gap(self):
  e=pd.DataFrame({'date':pd.to_datetime(['2026-01-01','2026-01-02','2026-01-04','2026-01-05']),'1_rohigh_pressure_pump_qz_temp_o':[212.,213.,214.,-2.]})
  events,_=evaluate(e,self.performance(),'Plant A',CFG)
  high=events[events.rule_id.eq('TEMP_HIGH')];self.assertEqual(len(high),3);self.assertEqual(len(events[events.rule_id.eq('TEMP_LOW')]),1)
  self.assertEqual(sorted(group_incidents(high).days.tolist()),[1,2]);self.assertEqual(e.iloc[0,1],212)
 def test_historical_incident_not_dispatch(self):
  label,_=route('temperature','Verify promptly','Not confirmed in latest readings','Not completed')
  self.assertEqual(label,'Historical review only')
 def test_current_unexplained_condition_site_route(self):
  label,_=route('energy','Review','Confirmed in latest readings','Still unexplained after checks')
  self.assertEqual(label,'Targeted site inspection recommended')
if __name__=='__main__':unittest.main()
