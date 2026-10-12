"""Offline closeout invariant tests. Never fetch market data."""
import copy
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bundle/scripts'))
import availability_fill_v1 as sim
import track_kraken_prop_forward_observation as tracker

START = 1791766800.0  # 2026-10-12 01:00 UTC
CURSOR = 1791748800.0  # 2026-10-11 20:00 UTC
PAIRS = [f's{i}|PI_ETHUSD' for i in range(4)]

def fixture():
    state = sim.new_state()
    for i, pair in enumerate(PAIRS):
        state['position'][pair] = dict(side=-1, entry_time=sim._iso(CURSOR - 14400),
            entry_price=100.0, stop=101.0, target=98.5, instruction_id=str(i)*32, fees=.4)
        state['cursor_seconds'][pair] = CURSOR
        state['pending'][pair] = []
        state['last_observed_signal'][pair] = -1
    state['applied_rounds'] = {str(i).zfill(32):str(i) for i in range(12)}
    contract = dict(schema=1, mode='closeout_only', run_id='test-closeout',
        started_at=sim._iso(START), deadline_utc=sim._iso(START+7*86400),
        baseline_completed_rounds=12, max_additional_rounds=43,
        baseline_last_t3=sim._iso(CURSOR+14401),
        allowed_positions=copy.deepcopy(state['position']),
        baseline_cursor_seconds=copy.deepcopy(state['cursor_seconds']))
    return state, contract

def bar(t=CURSOR+14400, price=100, high=100.5, low=99.5):
    return dict(time=t, open=price, close=price, high=high, low=low,
                bar_open_at=sim._iso(t), bar_close_at=sim._iso(t+14400))

class CloseoutTests(unittest.TestCase):
    def setUp(self):
        self.net = patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))
        self.net.start()
        self.addCleanup(self.net.stop)
        self.state, self.contract = fixture()

    def bind(self):
        sim.bind_closeout(self.state, self.contract)

    def test_binding_requires_original_four_and_exact_cursors(self):
        self.state['position'][PAIRS[0]]['entry_price'] = 100.1
        with self.assertRaises(ValueError): self.bind()

    def test_changed_cursor_and_reset_contract_rejected(self):
        self.state['cursor_seconds'][PAIRS[0]] += 14400
        with self.assertRaises(ValueError): self.bind()
        self.state, self.contract = fixture(); self.bind()
        self.contract['started_at'] = sim._iso(START+10)
        self.contract['deadline_utc'] = sim._iso(START+10+7*86400)
        with self.assertRaises(ValueError): self.bind()

    def test_missing_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): sim.load_closeout_state(Path(td)/'missing', self.contract)

    def test_empty_baseline_pending_required(self):
        self.state['pending'][PAIRS[0]] = [dict(kind='ENTER', side=1)]
        with self.assertRaises(ValueError): self.bind()

    def test_reverse_neutral_same_and_flat_planning(self):
        self.bind()
        plan = sim.plan_round(self.state, round_id='a'*32,
            current_signals={PAIRS[0]:1, PAIRS[1]:0, PAIRS[2]:-1, 'flat|PI_XBTUSD':1},
            signal_bar_close_at={p:sim._iso(CURSOR+14400) for p in PAIRS})
        self.assertEqual(set(plan), set(PAIRS[:2]))
        self.assertTrue(all(x['kind']=='EXIT' and x['side']==0 for x in plan.values()))

    def test_strict_t3_then_reverse_closes_only(self):
        self.bind()
        p=PAIRS[0]; t=CURSOR+28800
        plan=sim.plan_round(self.state, round_id='a'*32, current_signals={p:1}, signal_bar_close_at={p:sim._iso(t)})
        sim.register_round(self.state, plan, {p:1}, t3=sim._iso(t), round_id='a'*32)
        events=[]
        sim._process_bar_open(self.state,p,bar(t=t),events)
        self.assertIsNotNone(self.state['position'][p])
        sim._process_bar_open(self.state,p,bar(t=t+14400),events)
        self.assertIsNone(self.state['position'][p])
        self.assertEqual([e['event'] for e in events],['close_leg'])
        self.assertEqual(self.state['trades'][p][0]['exit_reason'],'SIGNAL')
        self.assertAlmostEqual(self.state['trades'][p][0]['fees'],.8)

    def test_open_function_is_disabled(self):
        self.bind()
        with self.assertRaises(ValueError): sim._open_position(self.state, PAIRS[0], side=1, bar=bar(), instruction_id='new', events=[])

    def test_signal_bar_cannot_postdate_publication(self):
        self.bind(); p=PAIRS[0]
        plan=sim.plan_round(self.state,round_id='a'*32,current_signals={p:1},
            signal_bar_close_at={p:sim._iso(START+100)})
        with self.assertRaises(ValueError):
            sim.register_round(self.state,plan,{p:1},t3=sim._iso(START),round_id='a'*32)

    def test_malicious_pending_enter_fails_before_bar_processing(self):
        self.bind()
        self.state['pending'][PAIRS[0]]=[dict(kind='ENTER',side=1,t3=sim._iso(START),status='PENDING')]
        with self.assertRaises(ValueError): sim.apply_advance(self.state,{PAIRS[0]:[bar()]},round_id='a'*32)
        self.assertEqual(self.state['position'][PAIRS[0]],self.contract['allowed_positions'][PAIRS[0]])

    def test_gap_stop_then_exit_never_reopens(self):
        self.bind(); p=PAIRS[0]; t=CURSOR+28800
        plan=sim.plan_round(self.state,round_id='a'*32,current_signals={p:1},signal_bar_close_at={p:sim._iso(t-14400)})
        sim.register_round(self.state,plan,{p:1},t3=sim._iso(t-1),round_id='a'*32)
        events=[]; sim._process_bar_open(self.state,p,bar(t=t,price=102,high=102,low=102),events)
        self.assertIsNone(self.state['position'][p])
        self.assertEqual(len(self.state['trades'][p]),1)
        self.assertEqual(self.state['trades'][p][0]['exit_reason'],'GAP_STOP')
        self.assertFalse(any(e['event']=='open_leg' for e in events))

    def test_stop_target_rules_and_adverse_first_preserved(self):
        self.bind(); events=[]
        sim._process_bar_close(self.state,PAIRS[0],bar(high=102,low=97),events)
        sim._process_bar_close(self.state,PAIRS[1],bar(high=100,low=98),events)
        self.assertEqual(self.state['trades'][PAIRS[0]][0]['exit_reason'],'STOP')
        self.assertEqual(self.state['trades'][PAIRS[0]][0]['labels'],['ADVERSE_FIRST_ASSUMED'])
        self.assertEqual(self.state['trades'][PAIRS[1]][0]['exit_reason'],'TARGET')

    def test_closed_position_cannot_reappear(self):
        self.bind(); p=PAIRS[0]
        sim._close_position(self.state,p,bar_open_price=100,time_iso=sim._iso(START),reason='SIGNAL',labels=[],events=[])
        self.state['position'][p]=copy.deepcopy(self.contract['allowed_positions'][p])
        with self.assertRaises(ValueError): self.bind()

    def test_closed_bar_gap_and_future_rejected(self):
        self.bind(); now=CURSOR+3*14400+1
        missing={p:[bar(t=CURSOR+2*14400)] for p in PAIRS}
        with self.assertRaises(ValueError): sim.prepare_closeout_market(self.state,missing,observed_at=sim._iso(now))
        future={p:[bar(t=CURSOR+14400)] for p in PAIRS}
        with self.assertRaises(ValueError): sim.prepare_closeout_market(self.state,future,observed_at=sim._iso(CURSOR+14401))

    def test_marks_fees_funding_and_no_double_count(self):
        self.bind(); p=PAIRS[0]
        series={p:[bar(price=99.8)] for p in PAIRS}
        sim.prepare_closeout_market(self.state,series,observed_at=sim._iso(CURSOR+28801))
        sim._close_position(self.state,p,bar_open_price=99.8,time_iso=sim._iso(CURSOR+14400),reason='SIGNAL',labels=[],events=[])
        report=sim.closeout_report(self.state,as_of=sim._iso(CURSOR+28801))
        net=self.state['trades'][p][0]['pnl']
        self.assertEqual(report['open_position_count'],3)
        self.assertAlmostEqual(report['unrealized_gross_usd'],6)
        self.assertAlmostEqual(report['entry_fees_paid_usd'],1.6)
        self.assertAlmostEqual(report['open_entry_fees_paid_usd'],1.2)
        self.assertAlmostEqual(report['commissions_paid_usd'],2)
        self.assertAlmostEqual(report['realized_net_usd'],net)
        self.assertAlmostEqual(report['mark_to_market_ex_funding_usd'],net+6-1.2)
        self.assertAlmostEqual(report['hypothetical_exit_commission_usd'],1.2)
        self.assertAlmostEqual(report['hypothetical_exit_slippage_usd'],.5988)
        self.assertAlmostEqual(report['hypothetical_liquidation_ex_funding_usd'],net+6-1.2-1.2-.5988)
        self.assertIsNone(report['funding_usd'])
        self.assertEqual(report['funding_status'],'NOT_INCLUDED_UNKNOWN')
        self.assertTrue(all(x['mark']['as_of']==sim._iso(CURSOR+28800) for x in report['positions'] if x['status']=='OPEN'))

    def test_retry_no_duplicate_fill_fee_or_gap_t3(self):
        self.bind(); p=PAIRS[0]; t3=sim._iso(CURSOR+28801)
        series={p:[bar(high=102)] for p in PAIRS}
        sim.prepare_closeout_market(self.state,series,observed_at=t3)
        args=dict(round_id='a'*32,t3=t3,series_by_pair=series,current_signals={p:1 for p in PAIRS},signal_bar_close_at={p:sim._iso(CURSOR+28800) for p in PAIRS})
        sim.execute_round(self.state,**args)
        before=copy.deepcopy(self.state)
        args['t3']=sim._iso(CURSOR+28830)
        result=sim.execute_round(self.state,**args)
        self.assertEqual(self.state,before)
        self.assertFalse(result['report']['advance_applied'])
        self.assertEqual(result['report']['source_round_t3'],t3)
        self.assertEqual(result['report']['closeout']['signal_evidence_gap']['to'],t3)

    def test_post_deadline_publication_rejected(self):
        self.bind()
        with self.assertRaises(ValueError): sim.execute_round(self.state,round_id='a'*32,t3=self.contract['deadline_utc'],series_by_pair={},current_signals={},signal_bar_close_at={})

    def test_report_write_failure_retry_pays_once(self):
        self.bind(); t3=sim._iso(CURSOR+28801)
        series={p:[bar(high=102)] for p in PAIRS}
        sim.prepare_closeout_market(self.state,series,observed_at=t3)
        args=dict(round_id='c'*32,t3=t3,series_by_pair=series,current_signals={p:1 for p in PAIRS},signal_bar_close_at={p:sim._iso(CURSOR+28800) for p in PAIRS})
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'
            with self.assertRaises(OSError):
                sim.execute_round(self.state,**args,state_path=path,report_writer=lambda report: (_ for _ in ()).throw(OSError('disk')))
            recovered=sim.load_closeout_state(path,self.contract)
            before=copy.deepcopy(recovered)
            report=sim.execute_round(recovered,**args,state_path=path)['report']
            self.assertEqual(recovered,before)
            self.assertFalse(report['advance_applied'])
            self.assertEqual(report['closeout']['closed_position_count'],4)
            self.assertAlmostEqual(report['closeout']['commissions_paid_usd'],3.2)

    def test_tracker_missing_state_has_zero_network_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); contract_path=root/'contract.json'
            contract_path.write_text(json.dumps(self.contract))
            argv=['tracker','--closeout-contract',str(contract_path), '--sim-state-v1',str(root/'missing'),
                  '--round-record-dir',str(root/'rounds'), '--out-json',str(root/'report.json')]
            with patch.object(sys,'argv',argv), patch.object(tracker,'fetch_futures_ohlc') as fetch, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tracker.main(),1)
                fetch.assert_not_called()

    def test_tracker_end_to_end_public_fixture_and_saved_evidence(self):
        override = os.environ.get("D5_SIM_STATE_FIXTURE", "").strip()
        baseline = Path(override) if override else (
            Path(__file__).resolve().parents[2]
            / "fixtures/terminal-evidence-20261011/reports/reports/kraken_prop/sim-state-v1.json"
        )
        state=json.loads(baseline.read_text())
        contract=copy.deepcopy(self.contract)
        contract['allowed_positions']=copy.deepcopy(state['position'])
        contract['baseline_cursor_seconds']=copy.deepcopy(state['cursor_seconds'])
        contract['baseline_last_t3']='2026-10-11T08:21:28.946660+00:00'
        last_open=CURSOR
        def fetch_public(api,symbol,resolution,days):
            self.assertEqual((api,resolution,days),('https://futures.kraken.com','4h',180))
            price=2498 if symbol=='PI_ETHUSD' else 82500
            return [bar(t=last_open-(199-i)*14400,price=price,high=price,low=price) for i in range(200)]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); reports=root/'reports'; reports.mkdir()
            contract_path=root/'closeout-contract.json'; contract_path.write_text(json.dumps(contract))
            state_path=reports/'sim-state-v1.json'; state_path.write_text(json.dumps(state))
            observer_path=reports/'forward-observation-state.json'
            observer_path.write_text(json.dumps({'observation_started_at':'2026-10-09T07:00:00+00:00'}))
            argv=['tracker','--closeout-contract',str(contract_path),'--sim-state-v1',str(state_path),
                  '--state',str(observer_path),'--round-record-dir',str(reports/'rounds'),
                  '--out-json',str(reports/'a.json'),'--out-md',str(reports/'a.md'),
                  '--availability-out-json',str(reports/'b.json'),'--round-id','d'*32]
            ticks=iter(datetime.fromtimestamp(START+i/1000,timezone.utc) for i in range(50))
            with patch.object(sys,'argv',argv), patch.object(tracker,'fetch_futures_ohlc',side_effect=fetch_public) as fetch, patch.object(tracker,'clock',side_effect=lambda: next(ticks)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tracker.main(),0)
                self.assertEqual(fetch.call_count,2)
            saved=json.loads(state_path.read_text())
            a=json.loads((reports/'a.json').read_text()); b=json.loads((reports/'b.json').read_text())
            record=json.loads((reports/'rounds'/('round.'+'d'*32+'.json')).read_text())
            self.assertEqual(b['closeout']['open_position_count'],4)
            self.assertEqual(b['source_round_t3'],record['published_at'])
            self.assertLess(record['published_at'],record['simulation_v1']['b_published_at'])
            self.assertEqual(a['decision'],'CLOSEOUT_ONLY_OBSERVE')
            self.assertTrue((reports/'closeout-latest.json').is_file())
            evidence=json.loads((reports/'closeout-market'/('d'*32+'.json')).read_text())
            self.assertEqual(len(evidence['rows_by_symbol']),2)
            self.assertEqual(len(saved['applied_rounds']),13)
            self.assertTrue(all(p['kind']=='EXIT' for ps in saved['pending'].values() for p in ps))

if __name__=='__main__': unittest.main(verbosity=2)
