import json, lib, numpy as np
lib.check_lock('.')
D = lib.load(); end = len(D.C)
mf4 = lambda: lib.SC.make_strat(D, 'F0_MF4')
out = {}
for name, st, fee in (('D1_MF4_RECENT', '2024-10-01', 0.0004), ('D2_MF4_FULL', '2022-10-03', 0.0004), ('D4_MF4_RECENT_FEE05', '2024-10-01', 0.0005)):
    out[name] = lib.extract(D, mf4(), lib.idx(D, st), end, fee=fee)
s0 = lib.idx(D, '2022-10-03')
p = lib.match_p(D, mf4, s0, end, len(out['D2_MF4_FULL']))
z = []
for seed in range(20): z += lib.extract(D, lib.Rnd(mf4(), p, 1000+seed), s0, end)
out['D3_ZERO_EDGE'] = z
for k, v in out.items(): print(k, lib.summ(v))
print('p', p)
json.dump(out, open('trades.json', 'w'))
