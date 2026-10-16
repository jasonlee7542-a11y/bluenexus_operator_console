"""Optional UI checks using the three CSVs beside app2.py.
Run: python -m unittest -v test_dashboard.py
"""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parent
@unittest.skipUnless(all((ROOT/n).exists() for n in ['plant_A_equipment_daily.csv','plant_B_equipment_daily.csv','plant_daily_performance.csv']),'Put the three challenge CSVs beside app2.py to run UI tests')
class DashboardTests(unittest.TestCase):
 def app(self):return AppTest.from_file(str(ROOT/'app2.py'),default_timeout=60).run()
 def test_pages(self):
  at=self.app()
  for plant in ['All plants','Plant A','Plant B']:
   at.selectbox(key='plant').set_value(plant).run()
   for page in ['Overview','Energy','Water & Quality','Equipment','Incidents','Data & Methods']:
    at.radio(key='page').set_value(page).run()
    self.assertFalse(at.exception,msg=f'{plant}/{page}: {[x.message for x in at.exception]}')
 def test_verification_persists_through_workflow(self):
  at=self.app();at.button(key='open_focused').click().run()
  self.assertEqual(at.radio(key='page').value,'Incidents')
  incident=at.session_state['selected_case']
  at.radio(key='verify_widget_'+incident).set_value('Confirmed in latest readings').run()
  at.button(key='next_remote_'+incident).click().run()
  at.radio(key='remote_widget_'+incident).set_value('Still unexplained after checks').run()
  at.button(key='next_site_'+incident).click().run()
  self.assertFalse(at.exception)
  self.assertIn('Site / engineering verification recommended',' '.join(x.value for x in at.markdown))
  at.radio(key='page').set_value('Overview').run();at.radio(key='page').set_value('Incidents').run()
  saved=at.session_state['operator_reviews'][incident]
  self.assertEqual(saved['current'],'Confirmed in latest readings');self.assertEqual(saved['remote'],'Still unexplained after checks')
 def test_exact_older_incident_opens(self):
  at=self.app();at.button(key='older_queue').click().run()
  self.assertEqual(at.selectbox(key='period').value,'All available history')
  self.assertIn('High temperature',[x.value for x in at.subheader]);self.assertFalse(at.exception)
if __name__=='__main__':unittest.main()
