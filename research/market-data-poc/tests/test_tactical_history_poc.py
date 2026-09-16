import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tactical_history_poc as th
import tactical_persistence_poc as tp
import tactical_tilt_poc as tt


def weekdays(start: date, count: int):
    out=[]
    d=start
    while len(out)<count:
        if d.weekday()<5:
            out.append(d)
        d += timedelta(days=1)
    return out


def target_with_closes(closes, start=date(2024,1,2)):
    days=weekdays(start,len(closes))
    bars=tuple(th.HistoricalBar(d,c,c,c,c,1000.0) for d,c in zip(days,closes))
    return th.HistoricalTarget('IE00BJ0KDQ92','World','XDWD.DEX','EUR','XETRA',bars)


def write_history(path: Path, closes, start=date(2024,1,2)):
    days=weekdays(start,len(closes))
    doc={
        'schema':1,'prototype_version':'0.4.4','source':'test','requested_outputsize':'synthetic',
        'targets':[{
            'isin':'IE00BJ0KDQ92','name':'World','symbol':'XDWD.DEX','currency':'EUR','region':'XETRA','status':'ok',
            'bars':[{'date':d.isoformat(),'open':c,'high':c,'low':c,'close':c,'volume':1000} for d,c in zip(days,closes)]
        }]
    }
    path.write_text(json.dumps(doc),encoding='utf-8')


class ScheduleTests(unittest.TestCase):
    def test_monthly_schedule_preserves_anchor_day_after_short_month(self):
        dates=th.generate_cycle_dates(date(2024,1,31),date(2024,1,1),date(2024,4,30),'monthly')
        self.assertEqual(dates,[date(2024,1,31),date(2024,2,29),date(2024,3,31),date(2024,4,30)])

    def test_quarterly_and_yearly_are_anchor_based(self):
        q=th.generate_cycle_dates(date(2024,2,29),date(2024,1,1),date(2025,3,1),'quarterly')
        self.assertEqual(q[:3],[date(2024,2,29),date(2024,5,29),date(2024,8,29)])
        y=th.generate_cycle_dates(date(2024,2,29),date(2024,1,1),date(2026,3,1),'yearly')
        self.assertEqual(y,[date(2024,2,29),date(2025,2,28),date(2026,2,28)])


class MetricsTests(unittest.TestCase):
    def test_cycle_on_weekend_uses_last_completed_session_without_future_data(self):
        closes=[100+i for i in range(30)]
        target=target_with_closes(closes)
        # 2024-02-10 is a Saturday. The evidence session must be Friday 2024-02-09.
        history, rows, err=th.build_cycle_history(
            target, frequency='weekly', anchor=date(2024,2,10), start=date(2024,2,10), end=date(2024,2,24), recovery_confirm_sessions=5
        )
        self.assertEqual(rows[0]['market_as_of'],'2024-02-09')
        self.assertIsNotNone(err)  # too few weekly cycles for governance, but evidence is still correct

    def test_historical_signal_reuses_tactical_tilt_formula(self):
        closes=[100.0]*21
        closes[-1]=90.0
        target=target_with_closes(closes)
        metrics=th._session_metrics(target.bars,20)
        expected=tt.tactical_signals(metrics)['rebound_aware']
        self.assertAlmostEqual(metrics['signals']['rebound_aware'],expected)

    def test_weekly_recovery_can_complete_on_current_cycle_session(self):
        weak={'as_of':'2026-08-03','return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm=[
            {'as_of':day,'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}}
            for day in ('2026-08-04','2026-08-05','2026-08-06','2026-08-07','2026-08-10')
        ]
        daily=[weak] + calm
        confirmation=th._recovery_confirmation(daily,0,5,5)
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation['run_started_on'],'2026-08-04')
        self.assertEqual(confirmation['confirmed_on'],'2026-08-10')
        self.assertTrue(confirmation['confirmation_includes_current_cycle_session'])

    def test_partial_recovery_streak_carries_across_previous_cycle_boundary(self):
        weak={'as_of':'2026-08-03','return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm=[
            {'as_of':day,'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}}
            for day in ('2026-08-04','2026-08-05','2026-08-06','2026-08-07','2026-08-10')
        ]
        daily=[weak] + calm
        # Simulate a PA cycle after the fourth calm session. The fifth session
        # arrives after that cycle and must complete the existing streak rather
        # than starting a new one from zero.
        confirmation=th._recovery_confirmation(daily,4,5,5)
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation['run_started_on'],'2026-08-04')
        self.assertEqual(confirmation['confirmed_on'],'2026-08-10')

    def test_recovery_confirmation_survives_restress_before_current_cycle(self):
        weak=lambda day: {'as_of':day,'return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm=lambda day: {'as_of':day,'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}}
        daily=[
            weak('2026-08-03'),
            calm('2026-08-04'), calm('2026-08-05'), calm('2026-08-06'),
            calm('2026-08-07'), calm('2026-08-10'),
            weak('2026-08-11'),
        ]
        confirmation=th._recovery_confirmation(daily,0,6,5)
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation['confirmed_on'],'2026-08-10')
        self.assertFalse(confirmation['confirmation_includes_current_cycle_session'])

    def test_already_confirmed_calm_run_is_not_rediscovered(self):
        weak={'as_of':'2026-08-03','return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm=[
            {'as_of':day,'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}}
            for day in ('2026-08-04','2026-08-05','2026-08-06','2026-08-07','2026-08-10','2026-08-11')
        ]
        daily=[weak] + calm
        # Recovery already crossed its five-session threshold on 2026-08-10.
        # A later PA cycle must not rediscover the same uninterrupted calm run.
        self.assertIsNone(th._recovery_confirmation(daily,5,6,5))

    def test_recovery_requires_configured_consecutive_nonstress_sessions(self):
        weak={'return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm={'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}}
        daily=[weak]*12
        daily[2:6]=[calm]*4
        self.assertFalse(th._confirmed_recovery(daily,0,10,5))
        daily[6]=calm
        self.assertTrue(th._confirmed_recovery(daily,0,10,5))


class ReplayTests(unittest.TestCase):
    def test_short_compact_like_history_reports_yearly_insufficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            write_history(path,[100-i*0.2 for i in range(100)])
            doc=th.replay_history(path,Path(tmp)/'out',anchor=date(2024,2,1),start=date(2024,2,1),end=date(2024,5,31),frequencies=('yearly',),recovery_confirm_sessions=5)
            row=doc['targets'][0]['cadences'][0]
            self.assertEqual(row['status'],'insufficient_history')

    def test_long_decline_can_reach_monthly_review_due(self):
        # Persistent decline supplies both signal and medium-horizon support.
        closes=[100.0*(0.997**i) for i in range(220)]
        target=target_with_closes(closes)
        history, rows, err=th.build_cycle_history(
            target,frequency='monthly',anchor=date(2024,2,15),start=date(2024,2,15),end=date(2024,8,15),recovery_confirm_sessions=5
        )
        self.assertIsNone(err)
        result=tp.evaluate_history(history)
        self.assertEqual(result['final_state'],'strategic_review_due')
        self.assertFalse(result['tactical_bonus_allowed'])
        self.assertGreaterEqual(sum(r['stress_qualified'] for r in rows),3)

    def test_report_contains_review_dates_and_human_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            write_history(path,[100.0*(0.997**i) for i in range(260)])
            out=Path(tmp)/'out'
            doc=th.replay_history(path,out,anchor=date(2024,2,15),start=date(2024,2,15),end=date(2024,10,15),frequencies=('monthly',),recovery_confirm_sessions=5)
            report=(out/'historical_replay_report.txt').read_text(encoding='utf-8')
            self.assertIn('review_entry_dates:',report)
            self.assertIn('target replacement remains human-owned',report)
            self.assertEqual(doc['prototype_version'],'0.4.4')


class ForensicsTests(unittest.TestCase):
    def test_recovery_confirmation_preserves_market_session_dates(self):
        weak={'as_of':'2026-01-02','return_20d':-0.08,'drawdown_from_20d_high':-0.08,'signals':{'rebound_aware':0.7}}
        calm=[]
        for idx, day in enumerate(weekdays(date(2026,1,5),8)):
            calm.append({'as_of':day.isoformat(),'return_20d':0.0,'drawdown_from_20d_high':0.0,'signals':{'rebound_aware':0.0}})
        daily=[weak] + calm + [weak]
        confirmation=th._recovery_confirmation(daily,0,len(daily)-1,5)
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation['run_started_on'],calm[0]['as_of'])
        self.assertEqual(confirmation['confirmed_on'],calm[4]['as_of'])
        self.assertEqual(confirmation['observed_nonstress_sessions'],5)

    def test_episode_forensics_splits_recovered_episode(self):
        evaluation={'observations':[
            {'cycle_date':'2026-01-15','tactical_signal':0.6,'return_5d':-0.02,'return_20d':-0.05,'drawdown_from_20d_high':-0.06,'stress_qualified':True,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_opportunity'},
            {'cycle_date':'2026-02-15','tactical_signal':0.7,'return_5d':-0.03,'return_20d':-0.06,'drawdown_from_20d_high':-0.07,'stress_qualified':True,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_watch'},
            {'cycle_date':'2026-03-15','tactical_signal':0.5,'return_5d':-0.01,'return_20d':-0.04,'drawdown_from_20d_high':-0.05,'stress_qualified':True,'recovered_since_previous_cycle':True,'state_after_cycle':'tactical_opportunity'},
        ]}
        raw=[
            {'cycle_date':'2026-01-15','market_as_of':'2026-01-15','recovery_confirmation':None},
            {'cycle_date':'2026-02-15','market_as_of':'2026-02-13','recovery_confirmation':None},
            {'cycle_date':'2026-03-15','market_as_of':'2026-03-13','recovery_confirmation':{'required_nonstress_sessions':5,'run_started_on':'2026-02-20','confirmed_on':'2026-02-26','observed_nonstress_sessions':5}},
        ]
        episodes=th._episode_forensics(evaluation,raw,recovery_confirm_sessions=5)
        self.assertEqual(len(episodes),2)
        self.assertEqual(episodes[0]['highest_state'],'tactical_watch')
        self.assertEqual(episodes[0]['closure']['reason'],'recovered_between_planning_cycles')
        self.assertEqual(episodes[0]['closure']['recovery_confirmation']['confirmed_on'],'2026-02-26')
        self.assertEqual(episodes[1]['status'],'active')
        self.assertEqual(episodes[1]['stressed_planning_cycles'],1)

    def test_nonqualified_cycle_without_between_cycle_recovery_stays_unresolved(self):
        evaluation={'observations':[
            {'cycle_date':'2026-01-15','tactical_signal':0.6,'return_5d':-0.02,'return_20d':-0.05,'drawdown_from_20d_high':-0.06,'stress_qualified':True,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_opportunity'},
            {'cycle_date':'2026-02-15','tactical_signal':0.1,'return_5d':0.01,'return_20d':0.01,'drawdown_from_20d_high':-0.01,'stress_qualified':False,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_opportunity'},
        ]}
        raw=[
            {'cycle_date':'2026-01-15','market_as_of':'2026-01-15','recovery_confirmation':None},
            {'cycle_date':'2026-02-15','market_as_of':'2026-02-13','recovery_confirmation':None},
        ]
        episode=th._episode_forensics(evaluation,raw,recovery_confirm_sessions=5)[0]
        self.assertIsNone(episode['closure'])
        self.assertEqual(episode['continuity_state'],'active_unresolved')
        self.assertEqual(episode['stressed_planning_cycles'],1)
        self.assertEqual(episode['unresolved_nonstress_planning_cycles'],1)
        self.assertEqual(episode['last_stressed_cycle'],'2026-01-15')
        self.assertEqual(episode['last_observed_cycle'],'2026-02-15')

    def test_forensics_keeps_stress_nonstress_stress_in_one_episode_without_recovery(self):
        evaluation={'observations':[
            {'cycle_date':'2026-01-15','tactical_signal':0.6,'return_5d':-0.02,'return_20d':-0.05,'drawdown_from_20d_high':-0.06,'stress_qualified':True,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_opportunity'},
            {'cycle_date':'2026-02-15','tactical_signal':0.1,'return_5d':0.01,'return_20d':0.01,'drawdown_from_20d_high':-0.01,'stress_qualified':False,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_opportunity'},
            {'cycle_date':'2026-03-15','tactical_signal':0.7,'return_5d':-0.03,'return_20d':-0.07,'drawdown_from_20d_high':-0.08,'stress_qualified':True,'recovered_since_previous_cycle':False,'state_after_cycle':'tactical_watch'},
        ]}
        raw=[
            {'cycle_date':'2026-01-15','market_as_of':'2026-01-15','recovery_confirmation':None},
            {'cycle_date':'2026-02-15','market_as_of':'2026-02-13','recovery_confirmation':None},
            {'cycle_date':'2026-03-15','market_as_of':'2026-03-13','recovery_confirmation':None},
        ]
        episodes=th._episode_forensics(evaluation,raw,recovery_confirm_sessions=5)
        self.assertEqual(len(episodes),1)
        self.assertEqual(episodes[0]['stressed_planning_cycles'],2)
        self.assertEqual(episodes[0]['unresolved_nonstress_planning_cycles'],1)
        self.assertEqual(episodes[0]['continuity_state'],'active_stressed')
        self.assertEqual(episodes[0]['highest_state'],'tactical_watch')

    def test_long_decline_forensics_reaches_review_and_remains_active(self):
        closes=[100.0*(0.997**i) for i in range(220)]
        target=target_with_closes(closes)
        history, raw, err=th.build_cycle_history(target,frequency='monthly',anchor=date(2024,2,15),start=date(2024,2,15),end=date(2024,8,15),recovery_confirm_sessions=5)
        self.assertIsNone(err)
        evaluation=tp.evaluate_history(history)
        episodes=th._episode_forensics(evaluation,raw,recovery_confirm_sessions=5)
        self.assertEqual(len(episodes),1)
        self.assertEqual(episodes[0]['status'],'active')
        self.assertEqual(episodes[0]['highest_state'],'strategic_review_due')
        self.assertGreaterEqual(episodes[0]['stressed_planning_cycles'],3)

    def test_replay_writes_episode_forensics_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            write_history(path,[100.0*(0.997**i) for i in range(260)])
            out=Path(tmp)/'out'
            th.replay_history(path,out,anchor=date(2024,2,15),start=date(2024,2,15),end=date(2024,10,15),frequencies=('monthly',),recovery_confirm_sessions=5)
            report_path=out/'episode_forensics_report.txt'
            self.assertTrue(report_path.exists())
            report=report_path.read_text(encoding='utf-8')
            self.assertIn('historical episode forensics',report)
            self.assertIn('highest_state=strategic_review_due',report)
            self.assertIn('max_drawdown=',report)
            self.assertIn('target replacement remains human-owned',report)

    def test_replay_json_carries_episode_forensics(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            write_history(path,[100.0*(0.997**i) for i in range(220)])
            out=Path(tmp)/'out'
            doc=th.replay_history(path,out,anchor=date(2024,2,15),start=date(2024,2,15),end=date(2024,8,15),frequencies=('monthly',),recovery_confirm_sessions=5)
            cadence=doc['targets'][0]['cadences'][0]
            self.assertIn('episode_forensics',cadence)
            self.assertGreaterEqual(len(cadence['episode_forensics']),1)
            self.assertIn('worst_return_20d',cadence['episode_forensics'][0])


class FetchTests(unittest.TestCase):
    def test_history_fetch_writes_only_after_all_targets_succeed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mapping={'targets':[
                {'isin':'IE00BJ0KDQ92','name':'World','status':'resolved','selected':{'symbol':'XDWD.DEX','currency':'EUR','region':'XETRA'}},
                {'isin':'IE00BTJRMP35','name':'EM','status':'resolved','selected':{'symbol':'XMME.DEX','currency':'EUR','region':'XETRA'}},
            ]}
            mp=root/'mapping.json'; mp.write_text(json.dumps(mapping),encoding='utf-8')
            out=root/'history.json'
            payload={'Time Series (Daily)':{}}
            for i in range(21):
                day=date(2026,8,1)+timedelta(days=i)
                payload['Time Series (Daily)'][day.isoformat()]={'1. open':'1','2. high':'1','3. low':'1','4. close':'1','5. volume':'1'}
            guard=mock.Mock(); guard.usage.return_value={'request_count':2,'daily_limit':25,'remaining':23}
            with mock.patch('tactical_history_poc.md._av_get',side_effect=[payload,tp.PersistenceError('boom')]):
                with self.assertRaises(tp.PersistenceError):
                    th.fetch_history(mp,out,'secret',guard,outputsize='compact')
            self.assertFalse(out.exists())

    def test_history_fetch_does_not_persist_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mapping={'targets':[{'isin':'IE00BJ0KDQ92','name':'World','status':'resolved','selected':{'symbol':'XDWD.DEX','currency':'EUR','region':'XETRA'}}]}
            mp=root/'mapping.json'; mp.write_text(json.dumps(mapping),encoding='utf-8')
            out=root/'history.json'
            payload={'Time Series (Daily)':{}}
            d=date(2026,1,1)
            for i in range(25):
                day=d+timedelta(days=i)
                payload['Time Series (Daily)'][day.isoformat()]={'1. open':'1','2. high':'1','3. low':'1','4. close':'1','5. volume':'1'}
            guard=mock.Mock(); guard.usage.return_value={'request_count':1,'daily_limit':25,'remaining':24}
            with mock.patch('tactical_history_poc.md._av_get',return_value=payload):
                th.fetch_history(mp,out,'SUPERSECRET',guard,outputsize='compact')
            self.assertNotIn('SUPERSECRET',out.read_text(encoding='utf-8'))



    def test_adjusted_bar_scales_ohlc_to_adjusted_close_basis(self):
        values={
            '1. open':'90', '2. high':'110', '3. low':'80', '4. close':'100',
            '5. adjusted close':'50', '6. volume':'1234',
            '7. dividend amount':'0.5', '8. split coefficient':'1.0',
        }
        bar=th._bar_from_av_adjusted('2026-01-02',values,'XDWD.DEX')
        self.assertAlmostEqual(bar['open'],45.0)
        self.assertAlmostEqual(bar['high'],55.0)
        self.assertAlmostEqual(bar['low'],40.0)
        self.assertAlmostEqual(bar['close'],50.0)
        self.assertEqual(bar['volume'],1234.0)

    def test_adjusted_history_fetch_uses_adjusted_endpoint_and_records_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mapping={'targets':[{'isin':'IE00BJ0KDQ92','name':'World','status':'resolved','selected':{'symbol':'XDWD.DEX','currency':'EUR','region':'XETRA'}}]}
            mp=root/'mapping.json'; mp.write_text(json.dumps(mapping),encoding='utf-8')
            out=root/'history.json'
            payload={'Time Series (Daily)':{}}
            for i, day in enumerate(weekdays(date(2026,1,1),25)):
                raw=100+i
                payload['Time Series (Daily)'][day.isoformat()]={
                    '1. open':str(raw-1), '2. high':str(raw+1), '3. low':str(raw-2), '4. close':str(raw),
                    '5. adjusted close':str(raw*0.5), '6. volume':'1000',
                    '7. dividend amount':'0.0', '8. split coefficient':'1.0',
                }
            guard=mock.Mock(); guard.usage.return_value={'request_count':1,'daily_limit':25,'remaining':24}
            with mock.patch('tactical_history_poc.md._av_get',return_value=payload) as get:
                doc=th.fetch_history(mp,out,'secret',guard,outputsize='full',price_basis='adjusted')
            params=get.call_args.args[0]
            self.assertEqual(params['function'],'TIME_SERIES_DAILY_ADJUSTED')
            self.assertEqual(params['outputsize'],'full')
            self.assertEqual(doc['price_basis'],'adjusted')
            self.assertEqual(doc['quote_type'],'daily_adjusted_ohlcv_derived')
            self.assertEqual(doc['alpha_vantage_function'],'TIME_SERIES_DAILY_ADJUSTED')
            self.assertEqual(doc['adjustment_method'],'scale_raw_ohlc_by_adjusted_close_over_raw_close')
            self.assertAlmostEqual(doc['targets'][0]['bars'][0]['close'],50.0)

    def test_raw_history_fetch_remains_default_and_uses_legacy_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mapping={'targets':[{'isin':'IE00BJ0KDQ92','name':'World','status':'resolved','selected':{'symbol':'XDWD.DEX','currency':'EUR','region':'XETRA'}}]}
            mp=root/'mapping.json'; mp.write_text(json.dumps(mapping),encoding='utf-8')
            out=root/'history.json'
            payload={'Time Series (Daily)':{}}
            for day in weekdays(date(2026,1,1),21):
                payload['Time Series (Daily)'][day.isoformat()]={'1. open':'1','2. high':'1','3. low':'1','4. close':'1','5. volume':'1'}
            guard=mock.Mock(); guard.usage.return_value={'request_count':1,'daily_limit':25,'remaining':24}
            with mock.patch('tactical_history_poc.md._av_get',return_value=payload) as get:
                doc=th.fetch_history(mp,out,'secret',guard,outputsize='compact')
            self.assertEqual(get.call_args.args[0]['function'],'TIME_SERIES_DAILY')
            self.assertEqual(doc['price_basis'],'raw')
            self.assertEqual(doc['quote_type'],'daily_raw_ohlcv')

    def test_adjusted_history_rejects_nonpositive_adjusted_close_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mapping={'targets':[{'isin':'IE00BJ0KDQ92','name':'World','status':'resolved','selected':{'symbol':'XDWD.DEX','currency':'EUR','region':'XETRA'}}]}
            mp=root/'mapping.json'; mp.write_text(json.dumps(mapping),encoding='utf-8')
            out=root/'history.json'
            payload={'Time Series (Daily)':{}}
            for day in weekdays(date(2026,1,1),21):
                payload['Time Series (Daily)'][day.isoformat()]={
                    '1. open':'1','2. high':'1','3. low':'1','4. close':'1','5. adjusted close':'0','6. volume':'1'
                }
            guard=mock.Mock(); guard.usage.return_value={'request_count':1,'daily_limit':25,'remaining':24}
            with mock.patch('tactical_history_poc.md._av_get',return_value=payload):
                with self.assertRaisesRegex(th.HistoryError,'invalid Alpha Vantage adjusted bar'):
                    th.fetch_history(mp,out,'secret',guard,outputsize='compact',price_basis='adjusted')
            self.assertFalse(out.exists())


class CsvImportTests(unittest.TestCase):
    def test_load_history_rejects_inconsistent_adjusted_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            days=weekdays(date(2026,1,1),21)
            doc={
                'schema':1,'prototype_version':'0.4.4','source':'test',
                'price_basis':'adjusted','quote_type':'daily_raw_ohlcv',
                'targets':[{'isin':'IE00BJ0KDQ92','name':'World','symbol':'XDWD.DEX','currency':'EUR','region':'XETRA','status':'ok',
                    'bars':[{'date':d.isoformat(),'open':100,'high':100,'low':100,'close':100,'volume':1000} for d in days]}]
            }
            path.write_text(json.dumps(doc),encoding='utf-8')
            with self.assertRaisesRegex(th.HistoryError,'adjusted history cannot declare daily_raw_ohlcv'):
                th.load_history(path)

    def test_provider_neutral_csv_import_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            csv_path=root/'history.csv'
            lines=['isin,name,symbol,currency,region,date,open,high,low,close,volume']
            for idx, day in enumerate(weekdays(date(2026,1,1),25)):
                value=100+idx
                lines.append(f'IE00BJ0KDQ92,World,XDWD.DEX,EUR,XETRA,{day.isoformat()},{value},{value},{value},{value},1000')
            csv_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            out=root/'history.json'
            doc=th.import_history_csv(csv_path,out)
            self.assertEqual(doc['source'],'imported_csv')
            _, targets=th.load_history(out)
            self.assertEqual(len(targets),1)
            self.assertEqual(len(targets[0].bars),25)

    def test_adjusted_csv_import_declares_basis_and_replay_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            csv_path=root/'history.csv'
            lines=['isin,name,symbol,currency,region,date,open,high,low,close,volume']
            for idx, day in enumerate(weekdays(date(2026,1,1),40)):
                value=100+idx
                lines.append(f'IE00BJ0KDQ92,World,XDWD.DEX,EUR,XETRA,{day.isoformat()},{value},{value},{value},{value},1000')
            csv_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            out=root/'history.json'
            doc=th.import_history_csv(csv_path,out,price_basis='adjusted')
            self.assertEqual(doc['price_basis'],'adjusted')
            self.assertEqual(doc['quote_type'],'daily_adjusted_ohlcv_imported')
            replay=th.replay_history(
                out,root/'replay',anchor=date(2026,2,1),start=date(2026,2,1),end=date(2026,2,28),
                frequencies=('weekly',),recovery_confirm_sessions=5
            )
            self.assertEqual(replay['history_price_basis'],'adjusted')
            self.assertEqual(replay['history_adjustment_method'],'imported_pre_adjusted_ohlc')

    def test_csv_import_rejects_duplicate_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            csv_path=root/'history.csv'
            header='isin,name,symbol,currency,region,date,open,high,low,close,volume\n'
            row='IE00BJ0KDQ92,World,XDWD.DEX,EUR,XETRA,2026-01-02,100,100,100,100,1000\n'
            csv_path.write_text(header + row*21,encoding='utf-8')
            with self.assertRaisesRegex(th.HistoryError,'duplicate session'):
                th.import_history_csv(csv_path,root/'history.json')


if __name__ == '__main__':
    unittest.main()
