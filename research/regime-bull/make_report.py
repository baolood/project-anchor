import json
R=json.load(open('results.json')); I=json.load(open('info_null_all_variants.json'))
sel=R['selected']; B=R['btc']; E=R['eth']; J=R['judged']
VARS=list(B['variants'].keys())
def p(x,d=1): return 'n/a' if x is None else f'{x*100:.{d}f}%'
def f(x,d=2): return 'n/a' if x is None else f'{x:.{d}f}'
def vt(res,w,title):
    s=f'**{title}** (net of 15 bp/side; buy-and-hold charged one entry)\n\n| Variant | CAGR | Max DD | Calmar | Sharpe | Avg exposure | Entries | Bull capture | CAGR @45bp stress |\n|---|---|---|---|---|---|---|---|---|\n'
    b=res['bh'][w]
    s+=f"| Buy & hold | {p(b['cagr'])} | {p(b['max_dd'])} | {f(b['calmar'])} | {f(b['sharpe'])} | 100% | 1 | 100% | {p(res['bh_stress'][w]['cagr'])} |\n"
    for v in VARS:
        m=res['variants'][v][w]; star=' ← selected' if v==sel else ''
        s+=f"| {v}{star} | {p(m['cagr'])} | {p(m['max_dd'])} | {f(m['calmar'])} | {f(m['sharpe'])} | {p(m['avg_exposure'],0)} | {m['entries']} | {p(m['bull_capture'],0)} | {p(m['stress_cagr'])} |\n"
    return s+'\n'
def bull_tab(res,w):
    m=res['variants'][sel][w]; s='| Bull leg (asset) | Leg gain | Days | Strategy | Buy&hold | Capture | Strat max DD |\n|---|---|---|---|---|---|---|\n'
    for r in m['bull_table']:
        s+=f"| {r['start']} → {r['end']}{'' if r['finished'] else ' (unfinished)'} | {p(r['asset_leg_change'],0)} | {r['days_in_window']} | {p(r['strat_ret'])} | {p(r['bh_ret'])} | {p(r['capture'],0)} | {p(r['strat_maxdd'])} |\n"
    return s+f"\nAggregate bull capture (sum of log returns over {m['bull_days']} bull days): **{p(m['bull_capture'],0)}**\n\n"
def bear_tab(res,w):
    m=res['variants'][sel][w]; s='| Bear leg (asset) | Leg drop | Days | Strategy return | Buy&hold return | Strat max DD | B&H max DD |\n|---|---|---|---|---|---|---|\n'
    for r in m['bear_table']:
        s+=f"| {r['start']} → {r['end']} | {p(r['asset_leg_change'],0)} | {r['days_in_window']} | {p(r['strat_ret'])} | {p(r['bh_ret'])} | {p(r['strat_maxdd'])} | {p(r['bh_maxdd'])} |\n"
    return s+'\n'
def crit(sym):
    j=J[sym]; m=(B if sym=='BTCUSDT' else E)['variants'][sel]['OOS']; b=(B if sym=='BTCUSDT' else E)['bh']['OOS']
    return j,m,b
jb,mb,bb=crit('BTCUSDT'); je,me,be=crit('ETHUSDT')
def v(ok): return 'PASS' if ok else 'FAIL'
def final(bt,et,name):
    if bt=='FAIL': return 'FAIL'
    if bt=='PASS' and et=='FAIL': return 'WARN'
    return bt
c1=final(v(jb['c1']),v(je['c1']),'c1'); c2=final(v(jb['c2']),v(je['c2']),'c2'); c3=final(v(jb['c3']),v(je['c3']),'c3'); c4=final(jb['c4'],je['c4'],'c4')
overall='PASS' if all(x=='PASS' for x in (c1,c2,c3,c4)) else ('FAIL' if 'FAIL' in (c1,c2,c3,c4) else 'NOT PASS (conditional)')
json.dump(dict(c1=c1,c2=c2,c3=c3,c4=c4,overall=overall),open('verdict.json','w'))
g=R['gate']
md=f"""# REGIME_BULL_SURVIVE_V1 — REPORT

PARAMS.md sha256: `{open('PARAMS.lock').read().split()[0]}` (see PARAMS.lock, locked 2026-10-27 10:58:50 Asia/Shanghai before any backtest).
Run: 2026-10-27, `rbs_backtest.py` + `charts_info.py` + `make_report.py`; log in run.log, all numbers in results.json / info_null_all_variants.json.

## 中文摘要（大白话，结论先说）

**结论：不及格（FAIL）。** 按事先锁定的规则，只用样本内（2018-03 到 2022-12）选变体，选出来的是 "50/200 均线交叉 + 20 日低点止损"。它在样本外（2023-01 到 2026-09）的 BTC 表现：年化 {p(mb['cagr'])}，同期一直拿着不动是 {p(bb['cagr'])}；最大回撤 {p(mb['max_dd'])}，拿着不动是 {p(bb['max_dd'])}；牛市阶段只抓到 {p(mb['bull_capture'],0)} 的涨幅（要求 ≥50%）。四条及格线里：回撤那条 {c1}、牛市抓取 {c2}、年化/Calmar {c3}、胜过随机择时 {c4}。ETH 也一样不过。

**但有一个重要的发现：**"在熊市活下来"这一半是真的，"在牛市赚到钱"这一半没做到。
- 熊市保护：所有变体的最大回撤都比拿着不动小（样本内 BTC 拿着不动 {p(B['bh']['IS']['max_dd'],0)}，趋势过滤版本 {p(B['variants']['b_SMA200_VOLTARGET']['IS']['max_dd'],0)} 到 {p(B['variants']['a_SMA200']['IS']['max_dd'],0)}；样本外拿着不动 {p(bb['max_dd'],0)}，被选中的 c 版本 {p(mb['max_dd'],0)}，其余三个 {p(B['variants']['b_SMA200_VOLTARGET']['OOS']['max_dd'],0)} 到 {p(B['variants']['a_SMA200']['OOS']['max_dd'],0)}），现货 1 倍、没有杠杆，不会被强平。
- 牛市收益：被选中的变体因为反复被假突破洗出去，样本外只剩 {p(mb['cagr'])} 年化。另外三个变体（只看信息、不作裁决）样本外年化分别是 a {p(B['variants']['a_SMA200']['OOS']['cagr'],0)}、b 和 d {p(B['variants']['b_SMA200_VOLTARGET']['OOS']['cagr'],0)}，回撤、Calmar 和牛市抓取都看着不错（简单 200 日均线抓取 {p(B['variants']['a_SMA200']['OOS']['bull_capture'],0)}）。可是它们也没有通过"胜过随机择时 p95"这一条（BTC 上分别排在随机分布的第 {I['btc']['a_SMA200']['pct']:.0f}/{I['btc']['b_SMA200_VOLTARGET']['pct']:.0f} 百分位），而且事后挑它们是偷看答案，不能算数。
- 一句话：这类"趋势过滤"能明显削掉熊市的亏损，但它的优势没有大到能和"随机择时同样的在场比例"拉开统计差距；而且一旦选错变体，牛市收益会大幅缩水。**不放行实盘，也不进影子期。**如果要继续这个方向，必须作为 V2 重新预注册；没有新的历史可测，只能往前做纸面影子。

## 1. What was tested

- Question: can a long-only, 1x, spot-style regime filter on BTC (primary) and ETH (secondary) keep most of the bull-market return while avoiding most of the bear-market loss?
- Data: Binance public archive, spot 1d klines BTCUSDT and ETHUSDT, {R['btc']['first_date']} to {R['btc']['last_date']} ({R['btc']['n_days']} daily bars each). Integrity check: BTC {json.dumps(R['integrity']['BTCUSDT'])}; ETH {json.dumps(R['integrity']['ETHUSDT'])}. No gaps or non-positive prices.
- First tradable day {B['first_tradable']} (200-bar warm-up). IS 2018-03-05..2022-12-31. OOS 2023-01-01..2026-09-30 (one bull 2023→Oct 2025 and one bear Oct 2025→mid-2026 for BTC).
- Costs 15 bp/side (10 fee + 5 slippage); 45 bp/side stress shown for information. Execution: signal on close(t-1), trade at open(t). Weights drift between days and the drift is traded back (turnover is charged on it).
- 4 pre-declared variants; multiple-testing discount: criterion 4 requires the p98.75 of the random-timing null (0.05/4) for a clean PASS.

## 2. Pre-run fee gate and variant selection (IS, BTC)

| Variant | IS gross CAGR | IS annual cost drag | Gross / cost | Gate (≥2×) | IS net Calmar | Entries |
|---|---|---|---|---|---|---|
""" + ''.join(f"| {k} | {p(x['gross_cagr'])} | {p(x['annual_cost'],2)} | {x['ratio']:.1f}× | {'pass' if x['passes'] else 'FAIL'} | {f(x['is_calmar'])} | {x['entries']} |\n" for k,x in g.items()) + f"""
All four clear the fee gate easily because these are slow strategies (turnover is tiny compared with the 65 bp wall that killed the basis families). Selection rule (highest IS Calmar among gate-passers): **{sel}** (IS Calmar {f(g[sel]['is_calmar'])}). ETH uses the same variant unchanged. Note that b and d are identical in IS and on BTC OOS: the 25% equity brake never triggered on BTC.

## 3. Per-variant tables

""" + vt(B,'IS','BTC in-sample 2018-03-05..2022-12-31') + vt(B,'OOS','BTC out-of-sample 2023-01-01..2026-09-30 (only the selected variant is judged; the others are information)') + vt(B,'FULL','BTC full period (information)') + vt(E,'IS','ETH in-sample') + vt(E,'OOS','ETH out-of-sample (information beside the BTC verdict)') + vt(E,'FULL','ETH full period (information)') + f"""
## 4. Bull-phase and bear-phase breakdowns — selected variant {sel}

Phases come from the ex-post 20% zig-zag (bull = leg ≥ +50%, bear = leg ≤ −30%), used for scoring only.

### BTC out-of-sample — bull phases
""" + bull_tab(B,'OOS') + "### BTC out-of-sample — bear phases\n\n" + bear_tab(B,'OOS') + "### BTC in-sample — bull phases\n\n" + bull_tab(B,'IS') + "### BTC in-sample — bear phases\n\n" + bear_tab(B,'IS') + "### ETH out-of-sample — bull phases\n\n" + bull_tab(E,'OOS') + "### ETH out-of-sample — bear phases\n\n" + bear_tab(E,'OOS') + f"""
## 5. Verdict by criterion (OOS, selected variant {sel}, BTC primary, ETH secondary)

| # | Criterion | BTC result | ETH result | Verdict |
|---|---|---|---|---|
| C1 | Max DD ≥ −35% AND better than buy-and-hold | strategy {p(mb['max_dd'])} vs B&H {p(bb['max_dd'])} → {v(jb['c1'])} | {p(me['max_dd'])} vs {p(be['max_dd'])} → {v(je['c1'])} | **{c1}** |
| C2 | Bull capture ≥ 50% | {p(mb['bull_capture'],0)} → {v(jb['c2'])} | {p(me['bull_capture'],0)} → {v(je['c2'])} | **{c2}** |
| C3 | OOS CAGR ≥ 70% of B&H, or Calmar > B&H | CAGR {p(mb['cagr'])} vs {p(bb['cagr'])} (ratio {p(jb['c3_cagr_ratio'],0)}); Calmar {f(mb['calmar'])} vs {f(bb['calmar'])} → {v(jb['c3'])} | CAGR {p(me['cagr'])} vs {p(be['cagr'])} (ratio {p(je['c3_cagr_ratio'],0)}); Calmar {f(me['calmar'])} vs {f(be['calmar'])} → {v(je['c3'])} | **{c3}** |
| C4 | Calmar above random-timing null (1000 seeds), discounted p98.75 for a PASS, p95 for a WARN | strategy {f(jb['strat_calmar'])} sits at the {jb['strat_percentile']:.0f}th percentile; null p50 {f(jb['null_p50'])}, p95 {f(jb['null_p95'])}, p98.75 {f(jb['null_p9875'])} → {jb['c4']} | {f(je['strat_calmar'])} at the {je['strat_percentile']:.0f}th pct; null p95 {f(je['null_p95'])}, p98.75 {f(je['null_p9875'])} → {je['c4']} | **{c4}** |

**Overall: {overall}.** (PASS needs all four PASS.) Fee gate: passed (gross ≥ 2× cost, see §2). Number of seeds: {jb['null_n']} (≥200 required).
Sanity check: the recomputed OOS CAGR from the weight series equals the reported one ({p(jb['recompute_cagr_check'],2)} vs {p(jb['reported_cagr'],2)}).

### Not judged, for information only: how the other three variants would have looked OOS (BTC)
These cannot change the verdict. Picking one of them now would be choosing with knowledge of the OOS answer, which is exactly what the pre-registration is meant to prevent.

| Variant | OOS Max DD | OOS Calmar | OOS CAGR | Bull capture | Null percentile (Calmar) | Null p95 | Null p98.75 |
|---|---|---|---|---|---|---|---|
""" + ''.join(f"| {k} | {p(B['variants'][k]['OOS']['max_dd'])} | {f(B['variants'][k]['OOS']['calmar'])} | {p(B['variants'][k]['OOS']['cagr'])} | {p(B['variants'][k]['OOS']['bull_capture'],0)} | {I['btc'][k]['pct']:.0f} | {f(I['btc'][k]['null_p95'])} | {f(I['btc'][k]['null_p9875'])} |\n" for k in VARS) + f"""
Even the three unselected variants would not clear C4 on BTC (best: the {max(I['btc'][k]['pct'] for k in VARS):.0f}th percentile). On ETH only the vol-targeted variant reaches {I['eth']['b_SMA200_VOLTARGET']['pct']:.0f}th percentile, which clears p95 (WARN level) but is far below the discounted p98.75 bar.

## 6. Charts

- `chart_btc_oos_selected.png` — BTC OOS equity (log) and drawdown, selected variant vs buy-and-hold, bull (green) and bear (red) phases shaded.
- `chart_btc_oos_all_variants_info.png` — same, all four variants (information).
- `chart_btc_full_all_variants.png` — BTC 2018-03..2026-09, all variants vs buy-and-hold.
- `chart_eth_oos_selected.png`, `chart_eth_full_all_variants.png` — ETH equivalents.
- `chart_null_calmar.png` — random-timing null distributions with the strategy and p95/p98.75 lines.

## 7. What this can't catch

- **Few independent cycles.** Roughly three bull/bear cycles for two correlated assets. The OOS window holds one big bull and one bear; a pass or fail here is a small sample, not proof.
- **Survivorship and hindsight.** BTC and ETH are the assets that survived and grew. A trend filter looks great on assets that ended up high. The 200-day SMA is a famous rule, so the idea was not found blind.
- **Data is a proxy.** Binance USDT spot, not USD at Kraken. Tether basis, venue-specific outages and Kraken's actual fills are not modelled. Early Binance 2017–18 data is thin.
- **Daily bars only.** Intraday crashes (e.g. wicks through a stop) and gap risk between a signal and the next open are not captured. The max drawdowns are daily close-to-open marks; the real intraday drawdown is worse.
- **"Never forced offline" is only partly tested.** 1x spot cannot be liquidated, but the report cannot catch exchange failure, API/key problems, account freezes, or withdrawal limits. It says nothing about a Kraken evaluation account's own drawdown rules.
- **Costs are flat.** 15 bp/side is assumed on every trade; real slippage in a crash is larger. Stress at 45 bp is shown but not judged. Taxes are not modelled.
- **Selection by IS Calmar can pick a whipsaw-prone variant.** That is what happened with the 50/200 + 20-day-low rule: it did well in the two big IS bulls and was repeatedly stopped out by false breakouts in the OOS choppy bull. That is a real weakness of the pre-registered selection rule, not a bug, and the verdict stands.
- **The random-timing null is generous in a bull market.** Circularly shifted copies of the weights have the same exposure, and in a strongly rising market random exposure earns a lot. Passing it is hard, which is the point: a regime filter is only worth having if it beats luck with the same market exposure.
- Market regimes that have not happened yet (a multi-year sideways market, a slow-bleed bear rather than a crash) are not in the sample, so nothing here says how the filter behaves in them.
- Data ends 2026-09-30 (last complete monthly archive); October 2026 is not included.

## 8. Honest read

The approach delivers half of the founder goal. "Survive bears" works in this data, mostly because a 200-day filter spends roughly 35–75% of the time in cash and 1x spot cannot be liquidated; in the IS the selected family cut BTC's −77% buy-and-hold drawdown to about −46%, and the simpler filters roughly −43% to −64%. "Earn in bulls" did not hold up for the variant the rules picked: it captured only {p(mb['bull_capture'],0)} of the OOS bull-phase gains and earned {p(mb['cagr'])} a year against {p(bb['cagr'])} for buy-and-hold. Under the pre-registered bar the family FAILS, and none of the four variants beats random timing by a clear margin on BTC. The useful lesson is a design one, not a strategy: for Anchor the survival layer (1x, drawdown brake, regime filter as a guardrail) is worth keeping as a risk tool, but this family is not an edge that should be sold or traded with real money as the thing that "makes money in bulls".
"""
open('REPORT.md','w').write(md)
print(md[:6000]); print(overall,c1,c2,c3,c4)
