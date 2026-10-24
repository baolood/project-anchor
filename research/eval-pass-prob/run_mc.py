import json, lib, time
lib.check_lock('.')
T = json.load(open('trades.json'))
RULES = ['R_FIX_50','R_FIX_100','R_FIX_150','R_FIX_200','R_FIX_250','R_FIX_300','R_FLOORFRAC','R_SNAP','R_DAILYSHRINK150','R_FREQ2_100','R_FREQ2_200']
out = {}
for d in ['D1_MF4_RECENT','D3_ZERO_EDGE','D2_MF4_FULL','D4_MF4_RECENT_FEE05']:
    for r in RULES:
        t0 = time.time(); res = lib.mc(T[d], r); out[f'{d}|{r}'] = res
        u = res[1095]; s = res[60]
        print(f"{d:22s} {r:17s} 60d P/F/L/run {s['pass_']*100:5.1f}/{s['fail']*100:4.1f}/{s['locked']*100:5.1f}/{s['running']*100:5.1f} | ult P/F/L/run {u['pass_']*100:5.1f}/{u['fail']*100:4.1f}/{u['locked']*100:5.1f}/{u['running']*100:5.1f} | med days {res['med_days_resolved']} pass {res['med_days_pass']} trades {res['mean_trades']:.1f} ({time.time()-t0:.0f}s)", flush=True)
json.dump(out, open('mc_results.json', 'w'), indent=1)
