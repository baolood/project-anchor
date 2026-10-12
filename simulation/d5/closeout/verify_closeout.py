#!/usr/bin/env python3
"""Read-only SSH snapshot of this one simulation; write evidence locally only."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

from deploy_closeout import BASE, SERVICE, SSH

REMOTE = r'''
import base64, datetime, fcntl, hashlib, importlib.util, json, subprocess
from pathlib import Path
ALIAS = Path('/var/lib/anchor-d5-closeout-20261012')
ROOT = ALIAS.resolve(strict=True)
assert str(ROOT) == '/var/lib/private/anchor-d5-closeout-20261012', 'unexpected destination root'
UNIT = 'anchor-d5-closeout-20261012.service'
OLD_ROOT = Path('/var/lib/private/anchor-native-dryrun-20261010')
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path, limit=MAX_FILE_BYTES):
    assert path.is_file() and not path.is_symlink(), 'missing or symlink file: ' + str(path)
    assert path.stat().st_size <= limit, 'evidence size bound exceeded'
    return path.read_bytes()
def safe_file(relative):
    rel = Path(relative)
    assert not rel.is_absolute() and '..' not in rel.parts and str(rel) == relative
    current = ROOT
    for part in rel.parts:
        current = current / part
        assert not current.is_symlink(), 'symlink below run root'
    return current

def service_state(name):
    result = subprocess.run(['systemctl', 'show', name, '--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,Result,NRestarts,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp,Restart,KillMode,RuntimeMaxUSec,User,StateDirectory'], capture_output=True, text=True, check=True, timeout=15)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
def pids(pattern):
    result = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True, timeout=10)
    assert result.returncode in (0, 1), 'process lookup failed'
    return [int(pid) for pid in result.stdout.split()]

receipt = PAYLOAD['receipt']
source_hashes = {}
for relative, digest in receipt['files_sha256'].items():
    if relative.startswith('bundle/scripts/') or relative == 'closeout_loop.py':
        source_hashes[relative] = sha(read(safe_file(relative)))
        assert source_hashes[relative] == digest, 'deployed source changed'
unit_hash = sha(read(Path('/etc/systemd/system') / UNIT))
assert unit_hash == receipt['unit_sha256'], 'deployed unit changed'
manifest_raw = read(ROOT / 'manifest.json')
manifest = json.loads(manifest_raw)
contract_raw = read(ROOT / 'closeout-contract.json')
contract = json.loads(contract_raw)
assert sha(contract_raw) == manifest['closeout_contract_sha256']
rollback = json.loads(read(ROOT / 'rollback-baseline.json'))
protected_unchanged = all(sha(read(Path(path))) == digest for path, digest in rollback['protected_before_sha256'].items())
old_baseline = rollback['baseline']['control']
old_generation = OLD_ROOT / old_baseline['current_rel']
old_reports_unchanged = all(sha(read(old_generation / rel)) == digest for rel, digest in old_baseline['report_sha256'].items())
old_state = service_state('anchor-native-dryrun-20261010.service')

# A committed generation is immutable, so one captured control version pins all
# report reads. Detect a concurrent commit and return that fact without mixing it.
control_raw = read(ROOT / 'control.json')
control = json.loads(control_raw)
assert control['run_id'] == contract['run_id']
assert control['started_at'] == contract['started_at'] and control['deadline_utc'] == contract['deadline_utc']
current = control['current_rel']
assert current == 'checkpoints/initial' or (current.startswith('runs/round-') and current[11:].isdigit())
generation = safe_file(current)
reports = {}
aggregate_bytes = 0
assert len(control['report_sha256']) <= 128  # 18 baseline + 43 records + 43 candle files + summary.
for relative, digest in control['report_sha256'].items():
    assert relative.startswith('reports/kraken_prop/')
    path = safe_file(current + '/' + relative)
    raw = read(path)
    aggregate_bytes += len(raw)
    assert aggregate_bytes <= MAX_TOTAL_BYTES
    assert sha(raw) == digest, 'committed report changed'
    reports[relative] = base64.b64encode(raw).decode()
initial_log = read(ROOT / 'checkpoints/initial/reports/kraken_prop/dry-run-v1.jsonl')
current_log = read(generation / 'reports/kraken_prop/dry-run-v1.jsonl')
assert current_log.startswith(initial_log), 'original round history was rewritten'
for rid in manifest['initial_round_ids']:
    relative = 'reports/kraken_prop/rounds/round.' + rid + '.json'
    assert sha(read(generation / relative)) == manifest['initial_report_sha256'][relative]

validation = {'status': 'not_run', 'reason': 'round in flight or control already failed'}
if control['inflight'] is None and control['status'] != 'failed':
    spec = importlib.util.spec_from_file_location('closeout_readonly_validation', ROOT / 'closeout_loop.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate(ROOT)
        validation = {'status': 'PASS'}
    except Exception as error:
        validation = {'status': 'FAIL', 'error': str(error)}
state = service_state(UNIT)
wrapper_pids = pids('[c]loseout_loop[.]py')
legacy_pids = pids('[d]ry_run_loop_v1[.]sh|[c]loud_loop[.]py')
child_pids = pids('[r]un_forward_round_v1[.]py|[t]rack_kraken_prop_forward_observation[.]py')
main_pid = int(state['MainPID'])
unique_instance = not legacy_pids and ((state['ActiveState'] == 'active' and wrapper_pids == [main_pid] and main_pid > 0) or (state['ActiveState'] == 'inactive' and main_pid == 0 and not wrapper_pids and not child_pids))
lock_held = None
lock_path = ROOT / 'loop.lock'
if lock_path.is_file():
    with lock_path.open('r') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_held = True
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
            lock_held = False

events_raw = read(ROOT / 'events.jsonl', 2 * 1024 * 1024) if (ROOT / 'events.jsonl').is_file() else b''
events = [json.loads(line) for line in events_raw.splitlines() if line]
root_summary = None
root_summary_sha = None
for name in ('closeout-status.json', 'closeout-summary.json', 'closeout-final.json'):
    if (ROOT / name).is_file():
        raw = read(ROOT / name)
        root_summary = json.loads(raw)
        root_summary_sha = sha(raw)
        break
latest_b = json.loads(read(generation / 'reports/kraken_prop/sim-availability-v1-latest.json'))
latest_state = json.loads(read(generation / 'reports/kraken_prop/sim-state-v1.json'))
child_logs = {}
if current.startswith('runs/'):
    for name in ('child.stdout.log', 'child.stderr.log'):
        path = generation / name
        if path.is_file():
            raw = read(path, 256 * 1024)
            child_logs[name] = {'sha256': sha(raw), 'text': raw.decode(errors='replace')}
control_after = read(ROOT / 'control.json')
summary = {
    'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'root': str(ALIAS), 'resolved_root': str(ROOT), 'service': UNIT,
    'service_state': state, 'old_service_state': old_state,
    'wrapper_pids': wrapper_pids, 'legacy_wrapper_pids': legacy_pids,
    'child_pids': child_pids, 'single_instance_verified': unique_instance,
    'single_instance_lock_held': lock_held, 'validation': validation,
    'control_unchanged_during_read': control_after == control_raw,
    'existing_protected_hashes_unchanged': protected_unchanged,
    'old_reports_unchanged': old_reports_unchanged, 'original_history_unchanged': True,
    'source_sha256': source_hashes, 'unit_sha256': unit_hash,
    'contract_sha256': sha(contract_raw), 'manifest_sha256': sha(manifest_raw),
    'control_sha256': sha(control_raw), 'events_sha256': sha(events_raw),
    'closeout_summary_sha256': root_summary_sha,
    'run_id': contract['run_id'], 'started_at': contract['started_at'],
    'deadline_utc': contract['deadline_utc'],
    'completed_rounds': control['completed_rounds'], 'slots_consumed': control['slots_consumed'],
    'status': control['status'], 'next_due': control['next_due'],
    'wrapper_start_events': sum(e['event'] == 'wrapper_started' for e in events),
    'new_committed_rounds': sum(e['event'] == 'committed' for e in events),
    'report_count': len(reports), 'report_bytes': aggregate_bytes,
}
print(json.dumps({'summary': summary, 'control': control, 'contract': contract,
                  'manifest': manifest, 'events': events, 'reports': reports,
                  'closeout_summary': root_summary, 'latest_b': latest_b,
                  'latest_state': latest_state, 'child_logs': child_logs}))
'''


def main():
    receipt = json.loads((BASE / 'package-receipt.json').read_text())
    compile(REMOTE, 'remote-read-only-closeout-verification', 'exec')
    result = subprocess.run(SSH, input='PAYLOAD = ' + repr({'receipt': receipt}) + '\n' + REMOTE,
                            text=True, capture_output=True, timeout=60)
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        return result.returncode
    data = json.loads(result.stdout)
    summary = data['summary']
    stamp = summary['captured_at_utc'].replace(':', '').replace('+', '_')
    target = BASE / 'verified' / stamp
    target.mkdir(parents=True, exist_ok=False)
    for relative, encoded in data['reports'].items():
        rel = Path(relative)
        assert not rel.is_absolute() and '..' not in rel.parts and relative.startswith('reports/kraken_prop/')
        raw = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(raw).hexdigest() == data['control']['report_sha256'][relative]
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    data.pop('reports')
    (target / 'snapshot.json').write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'local_evidence_directory': str(target), 'summary': summary}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
