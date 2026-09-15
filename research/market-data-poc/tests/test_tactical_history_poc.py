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
        'schema':1,'prototype_version':'0.4.0','source':'test','requested_outputsize':'synthetic',
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
            self.assertEqual(doc['prototype_version'],'0.4.0')


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


class CsvImportTests(unittest.TestCase):
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
