import zipfile, glob, pandas as pd, io
def load(sym):
    frames=[]
    for f in sorted(glob.glob(f'data/{sym}-1d-*.zip')):
        with zipfile.ZipFile(f) as z:
            raw=z.read(z.namelist()[0])
        df=pd.read_csv(io.BytesIO(raw),header=None,usecols=[0,1,2,3,4,5])
        df.columns=['t','open','high','low','close','vol']
        if df['t'].iloc[0] > 1e14: df['t']=df['t']//1000   # microseconds (2025+)
        frames.append(df)
    d=pd.concat(frames)
    d['date']=pd.to_datetime(d['t'],unit='ms').dt.normalize()
    d=d.drop_duplicates('date').set_index('date').sort_index().drop(columns='t')
    return d.astype(float)
if __name__=='__main__':
    for s in ['BTCUSDT','ETHUSDT']:
        d=load(s); idx=pd.date_range(d.index[0],d.index[-1])
        print(s,d.index[0].date(),d.index[-1].date(),len(d),'missing',len(idx.difference(d.index)),
              'maxdailyret',d.close.pct_change().abs().max(), 'nonpos',(d[['open','high','low','close']]<=0).sum().sum())
        print(idx.difference(d.index)[:20])
