
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.font_manager as fm

# try to find a CJK-capable font, else fallback
titles = ["刘欢安葬于北京 曾与膀胱癌斗争多年", "男子失业断供房贷 法院暂不拍卖房产", "进博会把全球南方好物送到中国", "朴树哥哥否认朴树去世", "马化腾内部训话", "立陶宛设“台湾代表处”内幕曝光", "台湾青年：台湾从来不是一个国家", "A股放量冲高回落 反弹是否已结束", "油价13日起下调", "双11最猛的增长不在商品", "“商家扬言取消外卖”系引流套路", "山姆399元羽绒服断货供应商回应", "脑梗年轻化趋势引发广泛关注", "中国国民党举办纪念孙中山诞辰座谈会", "沪深两市主力资金净流出435.28亿", "爆款羽绒服工厂为何甘心躲在山姆后面", "泽连斯基：星链系统出现严重运行异常", "国产手机再迎双品牌战略", "APEC为什么选在大湾区举办", "无牌四轮车撞倒老人后逃逸"]
heats = [11609288, 10504518, 9504881, 8600372, 7781938, 7041389, 6371312, 5765002, 5216389, 4719984, 4270818, 3864396, 3496650, 3163900, 2862815, 2590382, 2343874, 2120825, 1919002, 1736385]
title = "今日头条热榜前20话题热度"

cjk_candidates = ['Noto Sans CJK SC','Noto Sans CJK JP','WenQuanYi Zen Hei','WenQuanYi Micro Hei','SimHei','Microsoft YaHei','Arial Unicode MS','Source Han Sans','Droid Sans Fallback']
avail = {f.name for f in fm.fontManager.ttflist}
chosen = None
for c in cjk_candidates:
    if c in avail:
        chosen = c; break
if chosen:
    plt.rcParams['font.sans-serif'] = [chosen]
plt.rcParams['axes.unicode_minus'] = False

# reverse so top item is at top of horizontal bar
rev_titles = titles[::-1]
rev_heats = heats[::-1]
fig, ax = plt.subplots(figsize=(12, 10))
bars = ax.barh(range(len(rev_titles)), rev_heats, color='#e74c3c')
ax.set_yticks(range(len(rev_titles)))
lbl = [ (t[:28] + '…') if len(t) > 28 else t for t in rev_titles ]
ax.set_yticklabels(lbl, fontsize=9)
ax.set_xlabel('Heat / 热度', fontsize=11)
ax.set_title(title, fontsize=15, fontweight='bold')
for b, h in zip(bars, rev_heats):
    ax.text(b.get_width(), b.get_y()+b.get_height()/2, f' {h:,.0f}', va='center', fontsize=8)
plt.tight_layout()
plt.savefig('trending_top20.png', dpi=150)
print('SAVED trending_top20.png')
