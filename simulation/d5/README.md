# D5 public-market simulation

This tree is the D5 simulation that was deployed outside the repository as two systemd units. It is a public-market simulation. It does not place exchange orders. Nothing here is an MF4 evaluation, and this pull request does not add a separate Kraken account evaluation.

Both deployed copies are kept:

- `closeout/` is `anchor-d5-closeout-20261012` (the later closeout loop).
- `original/` is `anchor-native-dryrun-20261010` (the original 12-round loop).

The engines differ in three scripts: `availability_fill_v1.py`, `run_forward_round_v1.py`, and `track_kraken_prop_forward_observation.py`. The startup-entry fix is in `plan_round` of both `availability_fill_v1.py` copies. A missing `last_observed_signal` is not an adjacent-bar direction change, so startup does not open when the first observation is already `-1` or `1`. Closeout can still exit an open position. Strategy parameters (slippage, commission, notional, stop, target) are unchanged.

`backtest_kraken_prop_strategy.py`, `research_kraken_prop_strategies.py`, and `walk_forward_kraken_prop_strategies.py` live only under `closeout/bundle/scripts/`. The original package omitted them because they were byte-identical. The original tracker still imports those module names from its own script directory.

## Paths

Staged sources replaced an admin home directory with `<ADMIN_HOME>`. That placeholder stays in `closeout/independent-review-receipt.json` and is not a runtime path. Do not restore a home directory, host address, or username.

- `D5_SIM_STATE_FIXTURE` overrides the terminal sim-state read by `closeout/tests/test_engine.py`. The default is `simulation/d5/fixtures/terminal-evidence-20261011/reports/reports/kraken_prop/sim-state-v1.json`.
- `D5_LEGACY_EVIDENCE_DIR` overrides the sibling evidence directory used by `closeout/deploy_closeout.py`. The historical default remains a sibling `dry-run-migration` directory.

`deploy_closeout.py` and `verify_closeout.py` can open SSH. Do not run them from this checkout. Deploying the systemd units is a separate later step; this tree does not do it.

## Checks

```bash
cd /path/to/project-anchor
python3 -m unittest simulation.d5.closeout.tests.test_startup_entry simulation.d5.original.tests.test_startup_entry
python3 -m unittest discover -s simulation/d5/closeout/tests -v
python3 -m unittest discover -s simulation/d5/original -p 'test_*.py' -v
```

`simulation/d5/ORIGINAL_SHA256.txt` lists SHA-256 values of the unredacted staged originals, which stay off-repo. The in-repo `availability_fill_v1.py` copies, `test_engine.py`, `test_cloud_loop.py`, and `deploy_closeout.py` differ from those hashes because of the startup fix and the path overrides above.
