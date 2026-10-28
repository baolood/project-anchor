import json, numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rbs_backtest import *
R=json.load(open('results.json')); sel=R['selected']
info={}
ctxs={}
for sym,key in (('BTCUSDT','btc'),('ETHUSDT','eth')):
    res,ctx=evaluate_asset(sym); ctxs[key]=(res,ctx)
    idx=ctx['idx']; m=window_mask(idx,OOS)&ctx['started']
    rv=ctx['r'][m]
    for v in VARS:
        nul=null_calmars(ctx['sims'][v]['w'][m],rv)
        cal=res['variants'][v]['OOS']['calmar']
        info.setdefault(key,{})[v]=dict(calmar=cal,null_p95=float(np.percentile(nul,95)),null_p9875=float(np.percentile(nul,98.75)),pct=float((nul<cal).mean()*100))
json.dump(info,open('info_null_all_variants.json','w'),indent=1)
print(json.dumps(info,indent=1))

def eqdd(ret): 
    eq=np.cumprod(1+ret); pk=np.maximum.accumulate(np.maximum(eq,1)); return eq,eq/pk-1
def shade(ax,idx,legs,mask_dates=None):
    for L in legs:
        if L['kind']=='bull': ax.axvspan(idx[L['start']],idx[L['end']],color='green',alpha=0.08,lw=0)
        else: ax.axvspan(idx[L['start']],idx[L['end']],color='red',alpha=0.08,lw=0)
def chart(key,win,var_list,fname,title,logy=True):
    res,ctx=ctxs[key]; idx=ctx['idx']; m=window_mask(idx,win)&ctx['started']; di=idx[m]
    fig,(a1,a2)=plt.subplots(2,1,figsize=(12,8),sharex=True,gridspec_kw=dict(height_ratios=[2,1]))
    bh=bh_ret(ctx['r'][m]); e,d=eqdd(bh)
    a1.plot(di,e,'k',lw=1.6,label='Buy & hold'); a2.plot(di,d*100,'k',lw=1.2)
    cols=['tab:blue','tab:orange','tab:purple','tab:brown']
    for v,cl in zip(var_list,cols):
        e,d=eqdd(ctx['sims'][v]['net'][m]); lab=v+(' (SELECTED)' if v==sel else '')
        a1.plot(di,e,color=cl,lw=1.3,label=lab); a2.plot(di,d*100,color=cl,lw=1)
    shade(a1,idx,ctx['legs']); shade(a2,idx,ctx['legs'])
    a1.set_xlim(di[0],di[-1])
    if logy: a1.set_yscale('log')
    a1.set_ylabel('equity (start=1, log)' if logy else 'equity'); a2.set_ylabel('drawdown %'); a1.legend(loc='upper left'); a1.set_title(title+'  [green=bull phase, red=bear phase, ex-post]')
    a2.axhline(-35,color='r',ls=':',lw=1); a2.grid(alpha=.3); a1.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(fname,dpi=110); plt.close(fig)
chart('btc',(IS[0],OOS[1]),VARS,'chart_btc_full_all_variants.png','BTC full history 2018-03-05..2026-09-30, net of 15bp/side')
chart('btc',OOS,[sel],'chart_btc_oos_selected.png','BTC OOS 2023-01-01..2026-09-30: selected variant vs buy&hold')
chart('btc',OOS,VARS,'chart_btc_oos_all_variants_info.png','BTC OOS, all 4 variants (info only; only selected is judged)')
chart('eth',(IS[0],OOS[1]),VARS,'chart_eth_full_all_variants.png','ETH full history, net of 15bp/side')
chart('eth',OOS,[sel],'chart_eth_oos_selected.png','ETH OOS: selected variant vs buy&hold')
nb=np.load('null_btc_calmar.npy'); ne=np.load('null_eth_calmar.npy')
fig,ax=plt.subplots(1,2,figsize=(12,4))
for a,nul,k,t in ((ax[0],nb,'btc','BTC'),(ax[1],ne,'eth','ETH')):
    a.hist(nul,bins=50,color='gray'); a.axvline(R['judged'][t+'USDT']['strat_calmar'],color='r',label='selected variant Calmar')
    a.axvline(R['judged'][t+'USDT']['null_p95'],color='b',ls='--',label='null p95'); a.axvline(R['judged'][t+'USDT']['null_p9875'],color='navy',ls=':',label='null p98.75')
    a.set_title(f'{t} OOS Calmar: 1000 random-timing paths'); a.legend()
fig.tight_layout(); fig.savefig('chart_null_calmar.png',dpi=110)
