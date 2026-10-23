# Funding cache directory

`PF_XBTUSD_gaps_summary.json` is a gap map from a public PF_XBTUSD fetch on 2026-10-23. It is not a rate book and it is not an input to `eval_scoring`.

`fetch_pf_xbtusd_funding.py` can write `PF_XBTUSD_historicalfundingrates.jsonl` and raw response bodies under a chosen `--out-dir`. Those outputs are local. Missing hours stay `GAP` records. They are not zero-filled.

The Official writer does not import the fetch script, and this directory does not enable live `funding_pnl`.
