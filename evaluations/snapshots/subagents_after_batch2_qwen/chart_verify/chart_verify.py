import json
import os
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    logic = []
    pngs = execute_shell_command('ls -1 *.png 2>/dev/null')
    logic.append('PNGs present: ' + pngs.strip().replace(chr(10), ', '))

    cands = [l.strip() for l in pngs.split(chr(10)) if l.strip()]
    target = None
    for c in cands:
        if c in query:
            target = c
            break
    if not target:
        for c in cands:
            if 'bar' in c.lower() or 'trend' in c.lower():
                target = c
                break
    if not target and cands:
        target = cands[0]

    info = {'target': target}
    if target and os.path.exists(target):
        info['size'] = os.path.getsize(target)
        b = open(target, 'rb').read(33)
        sig = b[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10])
        w = int.from_bytes(b[16:20], 'big')
        h = int.from_bytes(b[20:24], 'big')
        info['png_magic'] = sig
        info['w'] = w
        info['h'] = h
        logic.append('Chart ' + target + ' size=' + str(info['size']) + ' dims=' + str(w) + 'x' + str(h) + ' magic=' + str(sig))

    font_py = 'import matplotlib.font_manager as fm\nn=[f.name for f in fm.fontManager.ttflist]\nkeys=["CJK","WenQuanYi","Hei","Han","SimHei","YaHei","Gothic","Noto Sans CJK"]\nc=sorted({x for x in n if any(k in x for k in keys)})\nprint("CJK_FONTS:", c[:10])'
    with open('_font_check.py', 'w', encoding='utf-8') as f:
        f.write(font_py)
    font_chk = execute_shell_command('python _font_check.py 2>&1')
    logic.append('font check: ' + str(font_chk).strip()[:300])

    data_info = {}
    for f2 in ['trending_keywords.json', 'chart_items.json']:
        if os.path.exists(f2):
            try:
                d = json.load(open(f2, encoding='utf-8'))
                items = d.get('items', []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                data_info[f2] = {'rows': len(items), 'sample': [it.get('keyword') for it in items[:3]]}
            except Exception as e:
                data_info[f2] = {'error': str(e)}
    logic.append('data: ' + json.dumps(data_info, ensure_ascii=False)[:400])

    summary = call_llm(
        system='You are a QA summarizer. Assess whether a generated bar chart is valid and whether Chinese text can render (CJK font present).',
        messages=[{'role': 'user', 'content': 'Verification log:\n' + chr(10).join(logic) + '\n\nFile info: ' + json.dumps(info, ensure_ascii=False) + '\n\nWrite a SUMMARY (100-400 words): does the PNG exist and is valid, dimensions, row counts in data files, and whether a CJK-capable font is available so Chinese labels render (not tofu).'}],
        max_tokens=1200,
    )

    ok = bool(info.get('png_magic') and info.get('size', 0) > 10000)
    answer = ('Chart verified: ' + str(target) + ' valid PNG ' + str(info.get('w')) + 'x' + str(info.get('h')) + '; rows: ' + json.dumps({k: v.get('rows') for k, v in data_info.items()})) if ok else ('Chart verification problem. ' + json.dumps(info)[:300])
    return {'answer': answer, 'summary': summary}
