import numpy as np, av
p='focus_music.mp3'
c=av.open(p)
s=c.streams.audio[0]
s.codec_context.sample_rate=s.codec_context.sample_rate or s.average_rate
sr=s.codec_context.sample_rate
frames=[]
for f in c.decode(audio=0):
    arr=f.to_ndarray()
    if arr.ndim>1:
        arr=arr.mean(axis=0)
    frames.append(arr)
c.close()
a=np.concatenate(frames).astype(np.float32)
def rms(x):
    return float(np.sqrt(np.mean(x**2))) if x.size else 0.0
print('len',a.size,'sr',sr)
print('meanRMS',rms(a))
print('peak',float(np.max(np.abs(a))))
w=int(0.1*sr)
for ts in [1,5,60,540,900,1075]:
    i=int(ts*sr)
    seg=a[i:i+w]
    print(f'win@{ts}s',rms(seg))
