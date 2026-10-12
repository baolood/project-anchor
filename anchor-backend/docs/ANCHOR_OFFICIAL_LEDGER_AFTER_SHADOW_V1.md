# Ledger after the JEV forward shadow

This is an example only. It does not install a unit, and it does not change the sealed Official V2 ledger.

`project-anchor-jev-forward-shadow-v2.service` can start `anchor-official-ledger.service` when the shadow run succeeds:

[`systemd/project-anchor-jev-forward-shadow-v2.service.d/start-official-ledger.conf.example`](systemd/project-anchor-jev-forward-shadow-v2.service.d/start-official-ledger.conf.example)

```ini
[Unit]
OnSuccess=anchor-official-ledger.service
```

The drop-in adds one dependency. It does not set `User=`, `DynamicUser=`, `StateDirectory=`, and it does not `chmod` or `setfacl` the ledger StateDirectory. `OnSuccess=` can be set more than once, so this does not remove the mirror drop-in on the ledger unit.

## Overlap with the hourly timer

`anchor-official-ledger.service` is also started by its hourly timer, which fires at minute :10. If the shadow run succeeds in that same window, systemd starts the oneshot again. `Type=oneshot` means the process exits when it finishes; a second start runs it again. It does not keep a second long-running copy of a service that is already active, but it is not by itself a promise that the second run writes nothing.

The sealed entry point is `/var/lib/anchor-official-ledger-20261010/cloud_official_once.py`, with `affl-causal-successor/affl_v2` and the runner. That tree is manifest-pinned and is not in this checkout, so this change does not open or edit it.

The only `affl_v2` copy in git history is `affl-causal-successor/affl_v2/c6_protective_boundary.py` on `cursor/c6-protective-risk-boundary-7180`. That branch is not the live manifest. In `ProtectiveRiskBook.on_signal`, a flat book with choice `FLAT` returns an empty list, and an open book whose choice equals the open side also returns an empty list. Those calls commit no ledger row. That is the evidence in this repository that a run with no new signal does not append. It is not a line from `cloud_official_once.py`, which remains sealed.

Do not install this drop-in from the pull request. A later host change copies the example to `/etc/systemd/system/project-anchor-jev-forward-shadow-v2.service.d/start-official-ledger.conf` and runs `systemctl daemon-reload`. Confirm the StateDirectory is still mode `0700` afterward. Do not `chmod` or `setfacl` it.

Rollback is removing that drop-in file and running `systemctl daemon-reload`. Leave the ledger file and the StateDirectory in place.
