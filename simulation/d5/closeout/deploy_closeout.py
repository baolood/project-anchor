#!/usr/bin/env python3
"""Install and request one start of the isolated closeout. Never auto-retry.

This module is safe to import. Only main() can make the explicitly authorized SSH
call; a durable exclusive local marker consumes that one attempt before SSH.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UpdateHostKeys=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
       '-o', 'ConnectionAttempts=1', '-o', 'ConnectTimeout=10', 'vultr-anchor', 'python3 -B -']
SERVICE = 'anchor-d5-closeout-20261012.service'
SCRIPT_NAMES = {
    'availability_fill_v1.py', 'backtest_kraken_prop_strategy.py',
    'research_kraken_prop_strategies.py', 'run_forward_round_v1.py',
    'track_kraken_prop_forward_observation.py', 'walk_forward_kraken_prop_strategies.py',
}
REMOTE = r'''
import base64, datetime, hashlib, io, json, os, subprocess, tarfile, time
from pathlib import Path
ROOT = Path('/var/lib/anchor-d5-closeout-20261012')
PRIVATE_ROOT = Path('/var/lib/private/anchor-d5-closeout-20261012')
UNIT = Path('/etc/systemd/system/anchor-d5-closeout-20261012.service')
OLD_ROOT = Path('/var/lib/anchor-native-dryrun-20261010').resolve(strict=True)
OLD_UNIT = Path('/etc/systemd/system/anchor-native-dryrun-20261010.service')
PATTERN = '[d]ry_run_loop_v1[.]sh|[c]loud_loop[.]py|[c]loseout_loop[.]py|[r]un_forward_round_v1[.]py|[t]rack_kraken_prop_forward_observation[.]py'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def checked(args, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=timeout)
def state(unit):
    raw = checked(['systemctl', 'show', unit, '--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,Result,NRestarts,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp,Restart,KillMode,RuntimeMaxUSec,User,StateDirectory']).stdout
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
def exclusive_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)
def sync_dir(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
def no_sim_process():
    found = subprocess.run(['pgrep', '-f', PATTERN], capture_output=True, text=True, timeout=10)
    assert found.returncode == 1, 'simulation process exists or lookup failed; no launch'
assert str(OLD_ROOT) == '/var/lib/private/anchor-native-dryrun-20261010', 'unexpected old root'
assert all(not p.exists() and not p.is_symlink() for p in [ROOT, PRIVATE_ROOT, UNIT]), 'destination exists; inspect instead of repeating installation'
old_state = state(OLD_UNIT.name)
assert old_state['ActiveState'] == 'inactive' and old_state['MainPID'] == '0', 'old service is not stopped'
no_sim_process()
baseline = PAYLOAD['baseline']
old_control = json.loads((OLD_ROOT / 'control.json').read_text())
assert old_control == baseline['control'], 'old control changed since frozen terminal evidence'
assert old_control['status'] == 'complete' and old_control['completed_rounds'] == 12 and old_control['slots_consumed'] == 12 and old_control['inflight'] is None
assert old_control['current_rel'] == 'runs/round-012'
old_generation = OLD_ROOT / old_control['current_rel']
assert all(sha(old_generation / rel) == digest for rel, digest in old_control['report_sha256'].items()), 'old reports changed'
assert sha(OLD_ROOT / 'cloud_loop.py') == baseline['wrapper_sha256']
assert sha(OLD_ROOT / 'manifest.json') == baseline['manifest_sha256']
assert sha(OLD_UNIT) == baseline['unit_sha256']
assert sha(OLD_ROOT / 'events.jsonl') == baseline['events_sha256']
protected_paths = PAYLOAD['protected_paths'] + [str(OLD_UNIT), str(OLD_ROOT / 'control.json'), str(OLD_ROOT / 'manifest.json'), str(OLD_ROOT / 'cloud_loop.py'), str(OLD_ROOT / 'events.jsonl')]
protected_before = {path: sha(path) for path in protected_paths}
receipt = PAYLOAD['receipt']
archive_bytes = base64.b64decode(PAYLOAD['archive'], validate=True)
assert hashlib.sha256(archive_bytes).hexdigest() == receipt['archive_sha256']
expected = receipt['files_sha256']
unit_bytes = PAYLOAD['unit'].encode()
assert hashlib.sha256(unit_bytes).hexdigest() == receipt['unit_sha256']
file_bytes = {}
with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(expected) and {m.name for m in members} == set(expected), 'archive members do not match receipt'
    for member in members:
        relative = Path(member.name)
        assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts and str(relative) == member.name
        assert member.size <= 8 * 1024 * 1024, 'oversized package file'
        raw = archive.extractfile(member).read()
        assert hashlib.sha256(raw).hexdigest() == expected[member.name]
        file_bytes[member.name] = raw
assert sum(map(len, file_bytes.values())) <= 64 * 1024 * 1024
manifest = json.loads(file_bytes['manifest.template.json'])
contract = json.loads(file_bytes['closeout-contract.template.json'])
control = json.loads(file_bytes['control.template.json'])
assert manifest['initial_report_sha256'] == old_control['report_sha256']
assert len(manifest['initial_round_ids']) == 12
assert control['current_rel'] == 'checkpoints/initial' and control['completed_rounds'] == 12 and control['slots_consumed'] == 12 and control['inflight'] is None and control['status'] == 'waiting'
assert control['report_sha256'] == old_control['report_sha256']
for rel, digest in old_control['report_sha256'].items():
    assert expected['checkpoints/initial/' + rel] == digest
assert contract['schema'] == 1 and contract['mode'] == 'closeout_only' and contract['max_additional_rounds'] == 43
assert not contract.get('started_at') and not contract.get('deadline_utc'), 'launch time must not be prefilled'
ROOT.mkdir(mode=0o700)
for relative, raw in file_bytes.items():
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)
assert all(sha(ROOT / rel) == digest for rel, digest in expected.items())
exclusive_json(ROOT / 'rollback-baseline.json', {'baseline': baseline, 'protected_before_sha256': protected_before, 'original_root_untouched': str(OLD_ROOT), 'archive_sha256': receipt['archive_sha256']})
with UNIT.open('xb') as handle:
    handle.write(unit_bytes)
    handle.flush()
    os.fsync(handle.fileno())
UNIT.chmod(0o644)
sync_dir(UNIT.parent)
verification = checked(['systemd-analyze', 'verify', str(UNIT)])
checked(['systemctl', 'daemon-reload'])
new_before = state(UNIT.name)
assert new_before['LoadState'] == 'loaded' and new_before['ActiveState'] == 'inactive' and new_before['MainPID'] == '0'
assert all(sha(path) == digest for path, digest in protected_before.items())
no_sim_process()
started = datetime.datetime.now(datetime.timezone.utc)
contract.update(started_at=started.isoformat(), deadline_utc=(started + datetime.timedelta(days=7)).isoformat())
exclusive_json(ROOT / 'closeout-contract.json', contract)
manifest['closeout_contract_sha256'] = sha(ROOT / 'closeout-contract.json')
exclusive_json(ROOT / 'manifest.json', manifest)
control.update(started_at=contract['started_at'], deadline_utc=contract['deadline_utc'], run_id=contract['run_id'], next_due=contract['started_at'])
exclusive_json(ROOT / 'control.json', control)
validation_result = checked(['/usr/bin/python3', '-B', str(ROOT / 'closeout_loop.py'), '--root', str(ROOT), '--validate-only'])
validation = json.loads(validation_result.stdout)
assert validation['completed_rounds'] == 12, 'validation did not confirm baseline'
exclusive_json(ROOT / 'start-request.json', {'at_utc': contract['started_at'], 'deadline_utc': contract['deadline_utc'], 'run_id': contract['run_id'], 'service': UNIT.name, 'archive_sha256': receipt['archive_sha256']})
sync_dir(ROOT)
checked(['systemctl', 'start', UNIT.name])
wait_until = time.monotonic() + 12
while time.monotonic() < wait_until:
    control = json.loads((ROOT / 'control.json').read_text())
    if control['completed_rounds'] > 12 or control['status'] in ('complete', 'failed'):
        break
    time.sleep(0.5)
old_after = state(OLD_UNIT.name)
protected_unchanged = all(sha(path) == digest for path, digest in protected_before.items())
baseline_unchanged = all(sha(old_generation / rel) == digest for rel, digest in old_control['report_sha256'].items())
result = {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'start_requested_once': True, 'run_id': contract['run_id'], 'started_at': contract['started_at'], 'deadline_utc': contract['deadline_utc'], 'root': str(ROOT), 'archive_sha256': receipt['archive_sha256'], 'source_receipt_files': len(expected), 'validation': validation, 'control': control, 'service_state': state(UNIT.name), 'old_service_before': old_state, 'old_service_after': old_after, 'protected_before_sha256': protected_before, 'existing_protected_hashes_unchanged': protected_unchanged, 'old_reports_unchanged': baseline_unchanged, 'unit_verify_output': (verification.stdout + verification.stderr).strip()}
exclusive_json(ROOT / 'deployment-receipt.json', result)
print(json.dumps(result))
assert protected_unchanged and baseline_unchanged and old_after['ActiveState'] == 'inactive' and old_after['MainPID'] == '0', 'post-launch preservation verification failed'
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def legacy_evidence_dir(base=BASE):
    """Sibling evidence directory. Override with D5_LEGACY_EVIDENCE_DIR.

    Staged copies replaced an admin home path with the placeholder
    ``<ADMIN_HOME>``. Do not restore that path; point this override at a
    reviewed evidence directory when the historical sibling layout is absent.
    """
    override = os.environ.get("D5_LEGACY_EVIDENCE_DIR", "").strip()
    if override:
        return Path(override)
    return base.parent / "dry-run-migration"


def build_payload(base=BASE):
    """Local-only complete checks; no connection and no marker yet."""
    legacy = legacy_evidence_dir(base)
    baseline = json.loads((legacy / 'terminal-evidence-20261011/snapshot.json').read_text())
    receipt = json.loads((base / 'package-receipt.json').read_text())
    archive = (base / 'cloud-package.tar.gz').read_bytes()
    unit = (base / SERVICE).read_text()
    assert sha(archive) == receipt['archive_sha256']
    assert sha(unit.encode()) == receipt['unit_sha256']
    required = {'closeout_loop.py', 'manifest.template.json', 'control.template.json', 'closeout-contract.template.json'}
    required |= {'bundle/scripts/' + name for name in SCRIPT_NAMES}
    required |= {'checkpoints/initial/' + rel for rel in baseline['control']['report_sha256']}
    assert set(receipt['files_sha256']) == required, 'receipt is not exact whitelist'
    protected = list(json.loads((legacy / 'cloud-preflight.json').read_text())['protected_unit_sha256'])
    assert all(p.startswith('/etc/systemd/system/project-anchor-') and Path(p).suffix in {'.service', '.timer'} for p in protected)
    return {'archive': base64.b64encode(archive).decode(), 'receipt': receipt, 'unit': unit,
            'baseline': baseline, 'protected_paths': protected}


def main():
    payload = build_payload()
    script = 'PAYLOAD = ' + repr(payload) + '\n' + REMOTE
    compile(script, 'remote-install-closeout', 'exec')
    marker = BASE / 'deploy-attempt.json'
    with marker.open('x') as handle:
        json.dump({'archive_sha256': payload['receipt']['archive_sha256'],
                   'service': SERVICE, 'attempt_consumed': True,
                   'retry_policy': 'never retry; inspect remote read-only after ambiguous result'}, handle)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(str(BASE), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        result = subprocess.run(SSH, input=script, text=True, capture_output=True, timeout=100)
    except subprocess.TimeoutExpired as exc:
        (BASE / 'deploy-timeout.json').write_text(json.dumps({'outcome': 'unknown; do not repeat start', 'timeout_seconds': exc.timeout}) + '\n')
        raise
    (BASE / 'deploy.stdout.txt').write_text(result.stdout)
    (BASE / 'deploy.stderr.txt').write_text(result.stderr)
    if result.returncode == 0:
        (BASE / 'deployment-receipt.json').write_text(json.dumps(json.loads(result.stdout), indent=2) + '\n')
    print('SSH_EXIT', result.returncode)
    print(result.stdout)
    print(result.stderr)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
