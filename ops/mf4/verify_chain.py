#!/usr/bin/env python3
"""Verify the MF4 forward stream hash chain. Read-only."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf4_host_watcher as W
p = sys.argv[1] if len(sys.argv) > 1 else W.EVENTS; prev = 'GENESIS'; n = 0
for line in open(p):
    ev = json.loads(line); n += 1
    assert ev['prev_hash'] == prev, ('prev_hash break', n); assert W.row_hash(ev) == ev['row_hash'], ('row_hash mismatch', n)
    prev = ev['row_hash']
print('OK', n, 'events, head', prev[:12])
