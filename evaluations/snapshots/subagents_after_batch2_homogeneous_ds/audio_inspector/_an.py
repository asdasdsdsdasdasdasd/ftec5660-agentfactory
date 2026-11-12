import os, sys, numpy as np
f = sys.argv[1]
try:
    import av
except Exception:
    os.system('pip install -q av 2>&1 | tail -1')
    import av
cont = av.open(f)
stream = cont.streams.audio[0]
sr = stream.rate
frames=[]
for frame in cont.decode(stream):
    arr = frame.to_ndarray()
    if arr.ndim>1: arr = arr.mean(axis=0)
    frames.append(arr.astype('float32'))
cont.close()
sig = np.concatenate(frames) if frames else np.zeros(1,dtype='float32')
sig = sig/(np.max(np.abs(sig))+1e-9)
win = int(sr)
n = len(sig)//win
rms=[]
for i in range(n):
    seg = sig[i*win:(i+1)*win]
    rms.append(float(np.sqrt(np.mean(seg**2))))
rms=np.array(rms)
print('TOTAL_SEC', round(len(sig)/sr,1))
print('MEAN_RMS', round(float(np.mean(rms)),4))
print('MAX_RMS', round(float(np.max(rms)),4))
step=30
for i in range(0, n, step):
    print('BIN', i, round(float(np.mean(rms[i:i+step])),4))
