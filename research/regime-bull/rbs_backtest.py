"""REGIME_BULL_SURVIVE_V1 backtest. Implements PARAMS.md (sha256 in PARAMS.lock). No parameter is tuned."""
import json, numpy as np, pandas as pd
from load import load

FEE=0.0010; SLIP=0.0005; COST=FEE+SLIP; COST_STRESS=0.0040+SLIP
IS=('2018-03-05','2022-12-31'); OOS=('2023-01-01','2026-09-30')
VARS=['a_SMA200','b_SMA200_VOLTARGET','c_CROSS50_200_EXIT20','d_VOLTARGET_DDBRAKE']
NSEEDS=1000

def prep(sym):
    d=load(sym); c=d.close.values; o=d.open.values
    r=np.empty(len(d)); r[:-1]=o[1:]/o[:-1]-1; r[-1]=c[-1]/o[-1]-1
    return d.index, o, c, r

def indicators(c):
    s=pd.Series(c)
    sma200=s.rolling(200).mean().values; sma50=s.rolling(50).mean().values
    lr=np.log(s).diff()
    vol=(lr.rolling(60).std()*np.sqrt(365)).values
    return sma200,sma50,vol

def simulate(var, c, r, cost=COST):
    """returns dict of arrays aligned to days; position decided from info up to close(t-1), executed at open(t)."""
    N=len(c); sma200,sma50,vol=indicators(c)
    w=np.zeros(N); turn=np.zeros(N); net=np.zeros(N); gross=np.zeros(N); pre=np.zeros(N)
    E=1.0; cur=0.0; peak=1.0; brake=False; seen_off=False
    pos=0; stopped=False
    t0=200
    for t in range(t0,N):
        p=t-1
        regime=c[p]>sma200[p]
        tgt=cur
        if var=='a_SMA200':
            tgt=1.0 if regime else 0.0
        elif var in ('b_SMA200_VOLTARGET','d_VOLTARGET_DDBRAKE'):
            sized=min(1.0,0.40/vol[p])
            allowed=True
            if var.startswith('d'):
                if brake:
                    if not regime: seen_off=True
                    if seen_off and regime:
                        brake=False; peak=E; allowed=True
                    else:
                        allowed=False
                else:
                    if E<=0.75*peak:
                        brake=True; seen_off=False; allowed=False
                    else:
                        peak=max(peak,E)
            if not allowed or not regime: tgt=0.0
            else:
                if cur==0.0: tgt=sized
                elif abs(sized-cur)>=0.10: tgt=sized
                else: tgt=cur
        elif var=='c_CROSS50_200_EXIT20':
            trend=sma50[p]>sma200[p]
            lo=c[p-20:p].min(); hi=c[p-20:p].max()   # closes t-21..t-2
            if not trend: pos=0; stopped=False
            else:
                if pos==1:
                    if c[p]<lo: pos=0; stopped=True
                elif stopped:
                    if c[p]>hi: pos=1; stopped=False
                else: pos=1
            tgt=float(pos)
        pre[t]=cur
        tn=abs(tgt-cur); turn[t]=tn
        wt=tgt; w[t]=wt
        g=wt*r[t]; gross[t]=g
        n=g-cost*tn; net[t]=n
        E*=(1+n)
        cur=wt*(1+r[t])/(1+wt*r[t]) if wt>0 else 0.0
    return dict(w=w,turn=turn,net=net,gross=gross,pre=pre)

# ---------- metrics ----------
def mdd_info(ret):
    eq=np.cumprod(1+ret); eq=np.concatenate([[1.0],eq]); pk=np.maximum.accumulate(eq); dd=eq/pk-1
    # longest underwater run (days)
    uw=0; best=0
    for x in dd[1:]:
        if x<0: uw+=1; best=max(best,uw)
        else: uw=0
    return eq,dd,dd.min(),best
def metrics(ret):
    n=len(ret); eq,dd,mdd,uw=mdd_info(ret)
    yrs=n/365.0; tot=eq[-1]-1
    cagr=eq[-1]**(1/yrs)-1 if eq[-1]>0 else -1.0
    calmar=cagr/max(abs(mdd),1e-9)
    sd=ret.std(ddof=1)*np.sqrt(365); sharpe=(ret.mean()*365)/sd if sd>0 else 0
    return dict(days=n,total_return=tot,cagr=cagr,max_dd=mdd,calmar=calmar,sharpe=sharpe,longest_underwater_days=uw)

def bh_ret(r, cost=COST):
    x=r.copy(); x[0]=(1+x[0])*(1-cost)-1; return x

def zigzag(c, idx):
    piv=[]; mode=None; lo=hi=(0,c[0])
    for t in range(len(c)):
        p=c[t]
        if p>hi[1]: hi=(t,p)
        if p<lo[1]: lo=(t,p)
        if mode in (None,'up') and p<=hi[1]*0.8:
            if mode is None and lo[0]<hi[0]: piv.append((lo[0],'T'))
            piv.append((hi[0],'P')); mode='down'; lo=(t,p); hi=(t,p)
        elif mode in (None,'down') and p>=lo[1]*1.2:
            if mode is None and hi[0]<lo[0]: piv.append((hi[0],'P'))
            piv.append((lo[0],'T')); mode='up'; hi=(t,p); lo=(t,p)
    legs=[]
    for (a,ka),(b,kb) in zip(piv[:-1],piv[1:]):
        legs.append((a,b,'up' if ka=='T' else 'down'))
    # unfinished final leg
    la,lk=piv[-1]
    if lk=='T':
        j=la+int(np.argmax(c[la:])); legs.append((la,j,'up_unfinished'))
    else:
        j=la+int(np.argmin(c[la:])); legs.append((la,j,'down_unfinished'))
    out=[]
    for a,b,k in legs:
        chg=c[b]/c[a]-1
        if k.startswith('up') and chg>=0.50: out.append(dict(kind='bull',start=a,end=b,chg=chg,finished=(k=='up')))
        if k.startswith('down') and chg<=-0.30: out.append(dict(kind='bear',start=a,end=b,chg=chg,finished=(k=='down')))
    return out

def window_mask(idx,win):
    return np.asarray((idx>=pd.Timestamp(win[0]))&(idx<=pd.Timestamp(win[1])))

def phase_days(leg,N):
    m=np.zeros(N,bool); m[leg['start']+1:leg['end']+1]=True; return m

def phase_table(idx,legs,kind,strat,bh,mask):
    rows=[]
    for L in legs:
        if L['kind']!=kind: continue
        m=phase_days(L,len(idx))&mask
        if m.sum()==0: continue
        sr=np.prod(1+strat[m])-1; br=np.prod(1+bh[m])-1
        eq=np.concatenate([[1.0],np.cumprod(1+strat[m])]); sdd=(eq/np.maximum.accumulate(eq)-1).min()
        eb=np.concatenate([[1.0],np.cumprod(1+bh[m])]); bdd=(eb/np.maximum.accumulate(eb)-1).min()
        rows.append(dict(start=str(idx[L['start']].date()),end=str(idx[L['end']].date()),days_in_window=int(m.sum()),
            asset_leg_change=L['chg'],strat_ret=sr,bh_ret=br,capture=(sr/br if kind=='bull' else None),strat_maxdd=sdd,bh_maxdd=bdd,finished=L['finished']))
    return rows

def bull_capture(legs,strat,bh,mask,N):
    m=np.zeros(N,bool)
    for L in legs:
        if L['kind']=='bull': m|=phase_days(L,N)
    m&=mask
    if m.sum()==0: return None,0
    return float(np.log1p(strat[m]).sum()/np.log1p(bh[m]).sum()), int(m.sum())

def shifted_turn(wvec, rvec):
    """turnover of a post-trade weight vector given asset returns (weights drift between days); first day charged from flat."""
    drift=np.zeros(len(wvec))
    wl=wvec[:-1]; rl=rvec[:-1]
    drift[1:]=np.where(wl>0, wl*(1+rl)/(1+wl*rl), 0.0)
    return np.abs(wvec-drift)

def null_calmars(wv, rv, nseeds=NSEEDS, seed0=20261027):
    n=len(wv); out=[]
    for s in range(nseeds):
        rng=np.random.default_rng(seed0+s)
        k=int(rng.integers(30,n-30+1))
        w2=np.roll(wv,k)
        net=w2*rv-COST*shifted_turn(w2,rv)
        out.append(metrics(net)['calmar'])
    return np.array(out)

def evaluate_asset(sym, sel_var=None, full=False):
    idx,o,c,r=prep(sym)
    N=len(c); t0=200
    sims={v:simulate(v,c,r) for v in VARS}
    sims_stress={v:simulate(v,c,r,COST_STRESS) for v in VARS}
    legs=zigzag(c,idx)
    started=np.zeros(N,bool); started[t0:]=True
    res=dict(symbol=sym,first_date=str(idx[0].date()),last_date=str(idx[-1].date()),n_days=N,first_tradable=str(idx[t0].date()),
             legs=[dict(kind=L['kind'],start=str(idx[L['start']].date()),end=str(idx[L['end']].date()),chg=L['chg'],finished=L['finished']) for L in legs],variants={})
    for name,win in (('IS',IS),('OOS',OOS),('FULL',(IS[0],OOS[1]))):
        m=window_mask(idx,win)&started
        bh=bh_ret(r[m]); bh_full=np.zeros(N); bh_full[m]=bh
        res.setdefault('bh',{})[name]=metrics(bh)
        bhs=bh_ret(r[m],COST_STRESS); res.setdefault('bh_stress',{})[name]=metrics(bhs)
        for v in VARS:
            s=sims[v]; net=s['net'][m]
            mt=metrics(net)
            mt['gross_cagr']=metrics(s['gross'][m])['cagr']
            mt['annual_cost']=float((COST*s['turn'][m]).sum()/(m.sum()/365.0))
            mt['avg_exposure']=float(s['w'][m].mean())
            mt['entries']=int(((s['w'][m][1:]>0)&(s['w'][m][:-1]==0)).sum()+(1 if s['w'][m][0]>0 else 0))
            mt['annual_turnover']=float(s['turn'][m].sum()/(m.sum()/365.0))
            mt['stress_cagr']=metrics(sims_stress[v]['net'][m])['cagr']
            sfull=np.zeros(N); sfull[m]=net
            cap,nd=bull_capture(legs,sfull,bh_full,m,N)
            mt['bull_capture']=cap; mt['bull_days']=nd
            mt['bull_table']=phase_table(idx,legs,'bull',sfull,bh_full,m)
            mt['bear_table']=phase_table(idx,legs,'bear',sfull,bh_full,m)
            res['variants'].setdefault(v,{})[name]=mt
    return res, dict(idx=idx,o=o,c=c,r=r,sims=sims,legs=legs,started=started)

if __name__=='__main__':
    out={}
    btc,bctx=evaluate_asset('BTCUSDT')
    eth,ectx=evaluate_asset('ETHUSDT')
    # data integrity
    for sym,ctx in (('BTCUSDT',bctx),('ETHUSDT',ectx)):
        d=load(sym); full=pd.date_range(d.index[0],d.index[-1])
        out.setdefault('integrity',{})[sym]=dict(rows=len(d),missing_days=int(len(full.difference(d.index))),nonpositive=int((d[['open','high','low','close']]<=0).sum().sum()),
              max_abs_daily_close_move=float(d.close.pct_change().abs().max()))
    # ---- fee gate + selection on BTC IS ----
    sel=None; gate={}
    for v in VARS:
        mt=btc['variants'][v]['IS']
        gate[v]=dict(gross_cagr=mt['gross_cagr'],annual_cost=mt['annual_cost'],ratio=(mt['gross_cagr']/mt['annual_cost'] if mt['annual_cost']>0 else float('inf')),
                     passes=bool(mt['gross_cagr']>=2*mt['annual_cost']),is_calmar=mt['calmar'],entries=mt['entries'])
    cands=[v for v in VARS if gate[v]['passes']]
    if cands:
        sel=sorted(cands,key=lambda v:(-gate[v]['is_calmar'],gate[v]['entries']))[0]
    out['gate']=gate; out['selected']=sel
    out['btc']=btc; out['eth']=eth
    # ---- OOS judging ----
    if sel:
        judged={}
        for sym,res,ctx in (('BTCUSDT',btc,bctx),('ETHUSDT',eth,ectx)):
            idx=ctx['idx']; m=window_mask(idx,OOS)&ctx['started']
            s=ctx['sims'][sel]; mt=res['variants'][sel]['OOS']; bh=res['bh']['OOS']
            wv=s['w'][m]; rv=ctx['r'][m]
            nul=null_calmars(wv,rv)
            # sanity: recompute strategy net from weights with shifted_turn(k=0) approx
            net_re=wv*rv-COST*shifted_turn(wv,rv)
            c1=bool(mt['max_dd']>=-0.35 and mt['max_dd']>bh['max_dd'])
            c2=bool(mt['bull_capture'] is not None and mt['bull_capture']>=0.50)
            c3a=mt['cagr']>=0.70*bh['cagr']; c3b=mt['calmar']>bh['calmar']; c3=bool(c3a or c3b)
            p95=float(np.percentile(nul,95)); p9875=float(np.percentile(nul,98.75))
            pct=float((nul<mt['calmar']).mean()*100)
            c4='PASS' if mt['calmar']>p9875 else ('WARN' if mt['calmar']>p95 else 'FAIL')
            judged[sym]=dict(c1=c1,c2=c2,c3=c3,c3_cagr_ratio=mt['cagr']/bh['cagr'] if bh['cagr']!=0 else None,c3_cagr_ok=bool(c3a),c3_calmar_ok=bool(c3b),
                c4=c4,null_p50=float(np.percentile(nul,50)),null_p95=p95,null_p9875=p9875,null_max=float(nul.max()),strat_calmar=mt['calmar'],strat_percentile=pct,
                null_n=len(nul),recompute_cagr_check=metrics(net_re)['cagr'],reported_cagr=mt['cagr'])
            if sym=='BTCUSDT': np.save('null_btc_calmar.npy',nul)
            else: np.save('null_eth_calmar.npy',nul)
        out['judged']=judged
    json.dump(out,open('results.json','w'),indent=1,default=float)
    np.savez('sims.npz',**{f'btc_{v}_{k}':bctx['sims'][v][k] for v in VARS for k in ('w','net','turn')},
                       **{f'eth_{v}_{k}':ectx['sims'][v][k] for v in VARS for k in ('w','net','turn')})
    print(json.dumps(dict(integrity=out['integrity'],gate=gate,selected=sel,judged=out.get('judged')),indent=1,default=float))
