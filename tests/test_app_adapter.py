"""Billing regressions use literal expectations independent of adapter helpers."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).parents[1] / 'custom_components/state_grid_info/app_adapter.py'
if PATH.exists():
    spec=importlib.util.spec_from_file_location('app_adapter',PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    merge_app_history=module.merge_app_history
else:
    merge_app_history=lambda *args: {}

CONFIG={'billing_standard':'year_ladder_fpg','year_ladder_start':'0101','ladder_level_1':100,'ladder_level_2':200,
    **{f'ladder_price_{tier}_price_{band}':price for tier,price in [(1,0.5),(2,0.6),(3,0.8)] for band in ['tip','peak','flat','valley']}}

def daily(day,usage=10,**extra):
    return {'day':day,'usage':usage,'charge':None,'peak':usage,'valley':0,'flat':0,'tip':0,**extra}

class AppAdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PATH.exists(), 'App history adapter has not been implemented')
    def test_missing_data_retains_history_and_does_not_create_future_zero_days(self):
        old={'dayList':[{'day':'2025-12-31','dayEleNum':4,'dayEleCost':2}], 'monthList':[{'month':'2025-12','monthEleNum':4,'monthEleCost':2}], 'yearList':[{'year':'2025','yearEleNum':4,'yearEleCost':2}], 'balance':80}
        out=merge_app_history(old,{'date':'2026-01-02T10:00:00+08:00','daily_history':[daily('2026-01-01'),daily('2026-01-02',None,peak=None)]},CONFIG)
        self.assertEqual([x['day'] for x in out['dayList']],['2026-01-01','2025-12-31'])
        self.assertEqual(out['balance'],80)
        self.assertEqual(out['yearList'][-1]['yearEleCost'],2)

    def test_official_bill_replaces_estimate_and_year_avoids_double_counting(self):
        old={'monthList':[{'month':'2026-01','monthEleNum':80,'monthEleCost':40,'estimated':True}]}
        incoming={'date':'2026-02-02T10:00:00+08:00','monthly_bill_history':[{'month':'2026-01','usage':90,'charge':45}], 'daily_history':[daily('2026-02-01',20)]}
        out=merge_app_history(old,incoming,CONFIG)
        self.assertEqual(out['dayList'][0]['dayEleCost'],11)
        self.assertEqual(out['yearList'][0]['yearEleNum'],110)
        self.assertEqual(out['yearList'][0]['yearEleCost'],56)
        self.assertEqual(out['yearList'][0]['settled_cost'],45)
        self.assertTrue(out['yearList'][0]['estimated'])

    def test_unknown_peak_valley_prevents_false_zero_cost(self):
        out=merge_app_history({}, {'date':'2026-01-02','daily_history':[daily('2026-01-01',10,peak=None,valley=None)]},CONFIG)
        self.assertIsNone(out['dayList'][0]['dayEleCost'])
        self.assertIsNone(out['monthList'][0]['monthEleCost'])

    def test_missing_annual_baseline_prevents_underpriced_estimate(self):
        out=merge_app_history({}, {'date':'2026-09-02','daily_history':[daily('2026-09-01')]},CONFIG)
        self.assertIsNone(out['dayList'][0]['dayEleCost'])

    def test_null_incoming_field_cannot_erase_retained_official_cost(self):
        old={'dayList':[{'day':'2026-01-01','dayEleNum':10,'dayEleCost':6,'cost_source':'official'}]}
        out=merge_app_history(old,{'date':'2026-01-02','daily_history':[daily('2026-01-01')]},CONFIG)
        self.assertEqual(out['dayList'][0]['dayEleCost'],6)
        self.assertEqual(out['dayList'][0]['cost_source'],'official')

    def test_official_cost_and_zero_are_valid_without_tariff_inputs(self):
        out=merge_app_history({}, {'date':'2026-09-03','daily_history':[daily('2026-09-01',0,charge=0),daily('2026-09-02',10,charge=5.7)]},CONFIG)
        self.assertEqual(out['monthList'][0]['monthEleCost'],5.7)
        self.assertFalse(out['monthList'][0]['estimated'])

    def test_partial_month_cost_is_unknown(self):
        out=merge_app_history({}, {'date':'2026-01-04','daily_history':[daily('2026-01-01'),daily('2026-01-03')]},CONFIG)
        self.assertIsNone(out['monthList'][0]['monthEleCost'])
        self.assertFalse(out['monthList'][0]['complete'])

    def test_official_bill_with_noncalendar_dates_is_not_counted_twice(self):
        incoming={'date':'2026-02-03','monthly_bill_history':[{'month':'2026-01','usage':100,'charge':50,'start_date':'2026-01-01','end_date':'2026-02-01'}], 'daily_history':[daily('2026-02-01'),daily('2026-02-02')]}
        out=merge_app_history({},incoming,CONFIG)
        self.assertEqual(out['yearList'][0]['yearEleNum'],110)

    def test_daily_official_costs_do_not_freeze_an_unsettled_month(self):
        first=merge_app_history({}, {'date':'2026-01-02','daily_history':[daily('2026-01-01',10,charge=5)]},CONFIG)
        out=merge_app_history(first, {'date':'2026-01-03','daily_history':[daily('2026-01-02',10,charge=5)]},CONFIG)
        self.assertEqual(out['monthList'][0]['monthEleNum'],20)
        self.assertEqual(out['monthList'][0]['monthEleCost'],10)

if __name__=='__main__': unittest.main()
