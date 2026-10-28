# REGIME_BULL_VOLTARGET_V1 — BUGLOG

Note (written 2026-10-28 ~10:50 Asia/Shanghai by the report author): PARAMS.md requires this file. It did not exist when the report was written, although the fix itself was already applied and hashed. This entry is reconstructed only from the files in this directory (run.crash1.log, the kept original script, SCRIPT.sha256 / SCRIPT.sha256.orig / SCRIPT.after-fix.sha256, results.json) and their timestamps. Nothing was changed in the script, PARAMS or results while writing it.

## Bug 1 — off-by-one in the lookback assertion (2026-10-28 10:37 UTC+8)
- Symptom: first real run crashed (run.crash1.log, 10:37:01) at `vt_backtest.py` line 198, `assert i0 >= SMA_WIN, 'need >=200 prior closes'`, when evaluating the INFO window (Binance, first decision 2018-03-04). No results.json and no result were written by that run.
- Cause: PARAMS.md defines the first decision as the first day with 200 closes up to and including that day (INFO starts 2018-03-04 = index 199 of the Binance series), the same convention as `regime-bull-v3/paper_track.py::simulate` (t ≥ SMA_WIN − 1). The assertion demanded one more close than the rule. Implementation bug, not a rule question.
- Fix (one line, line 198): `assert i0 >= SMA_WIN - 1, ...`. It only changes when the guard fires; no computed number depends on it. The judged PRE window (starts 2013-01-01, lookback from 2011-09-13) was never near the guard.
- Hash before: `0fb97549c185e60940bd7a75ffd0ce927edb24dc7cbe2292a7d268cf9330b6ca` (SCRIPT.sha256, read-only; copy in SCRIPT.sha256.orig; original kept as vt_backtest.py.orig-0fb97549…b6ca).
- Hash after: `a05302d94be36520b7c325608214e02c3a6c178158cbd6c14768d6a8ccf82712` (SCRIPT.after-fix.sha256; also recorded in results.json → hashes.script).
- Motivation: the crash happened before any number was shown, so the fix could not be motivated by the direction of a result.
- Rerun: whole run repeated from scratch at 10:37:02 (run.log, results.json). Single rerun; no further runs.
- Synthetic validation: `python3 vt_backtest.py --selftest` run on the fixed script 2026-10-28 ~10:50 UTC+8 (synthetic data only, writes no files; results.json md5 unchanged before/after): max rel diff vs V3 engine 0.00e+00 for leverage line, V2b and BH; SELFTEST OK. (No record was found that the selftest was run between the fix and the rerun; this check was done afterwards.)
