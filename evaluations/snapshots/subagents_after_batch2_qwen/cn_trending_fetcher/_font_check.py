import matplotlib.font_manager as fm
n=[f.name for f in fm.fontManager.ttflist]
keys=["CJK","WenQuanYi","Hei","Han","SimHei","YaHei","Gothic","Noto Sans CJK"]
c=sorted({x for x in n if any(k in x for k in keys)})
print("CJK_FONTS:", c[:10])