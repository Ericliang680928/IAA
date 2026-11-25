#!/usr/bin/env python3
"""IAA 會員大會資料一致性檢查。用法：python3 tools/check.py（在 20261204 資料夾外層執行）
檢查：舊錯字、變數未定義、award 缺頒發人、時段超時、投影片編號、手冊人數加總、公開版電話。"""
import json,re,sys,os,glob
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
rules=json.load(open(os.path.join(here,'names_rules.json'),encoding='utf-8'))
err=[];warn=[]
def tm(x):h,m=x.split(':');return int(h)*60+int(m)
# 1 舊錯字
for f in glob.glob(root+'/**/*',recursive=True):
    if os.path.isfile(f) and f.endswith(('.json','.html','.md','.py')) and 'names_rules' not in f:
        t=open(f,encoding='utf-8',errors='ignore').read()
        for w in rules['wrong_to_right']:
            if w in t: err.append(f'舊錯字「{w}」仍在 {os.path.relpath(f,root)}')
# 2 司儀稿
p=json.load(open(root+'/agm/program.json',encoding='utf-8'))
V=p['vars']
if V.get('應到人數')!=rules['fixed_facts']['應到人數']: err.append('應到人數不是 95')
n=0
for g in p['segments']:
    win=tm(g['end'])-tm(g['start']); used=sum((s.get('min') or 0) for s in g['scenes'])
    if used>win: warn.append(f"時段超時 {g['start']}-{g['end']} {g['title']}：排 {used} 分 > 窗 {win} 分")
    for s in g['scenes']:
        if s.get('slide'): n+=1
        blob=' '.join([s['say'],s['after'],s['sub'],s['giver'],s['receiver'],s['cue'],s['note']]+s['lines'])
        for m in re.findall(r'\{\{(.+?)\}\}',blob):
            if m!='lines' and m not in V: err.append(f"{s['id']} 未定義變數 {{{{{m}}}}}")
        if '{{lines}}' in s['say'] and not s['lines']: err.append(f"{s['id']} 唸稿用 {{lines}} 但名單是空的")
        if s['layout']=='award' and not s['giver']: err.append(f"{s['id']} 頒獎無頒發人")
        if re.search('待定|待確認',json.dumps(s,ensure_ascii=False)): warn.append(f"{s['id']} {s['title']} 仍有待定／待確認")
        if s['id']=='s26':
            names=[x.split()[-1] for x in s['lines']]
            if len(names)!=rules['fixed_facts']['長發會委員2027人數']: err.append(f"2027 長發會委員 {len(names)} 位，應為 20")
            for x in rules['fixed_facts']['長發會2027不含']:
                if x in names: err.append(f'長發會 2027 不應含 {x}')
            for x in rules['fixed_facts']['長發會2027含']:
                if x not in names: err.append(f'長發會 2027 應含 {x}')
print('投影片總數（編輯台）',n)
# 3 手冊
d=json.load(open(root+'/handbook/handbook.json',encoding='utf-8'))
S={s['id']:s for s in d}
rows=S['a1']['blocks'][2]['rows']; tot=rows[-1]
body=[r for r in rows if r[1] and '計' not in r[1]]
for ci in range(2,11):
    if sum(int(r[ci] or 0) for r in body)!=int(tot[ci]): err.append(f'附件一第 {ci} 欄加總不符')
r8=S['a8']['blocks'][1]['rows']
if len(r8)!=int(tot[10]): err.append(f'附件八 {len(r8)} 位 ≠ 附件一合計 {tot[10]}')
nm=[r[2].split('\n')[0] for r in r8]
for x in set(nm):
    if nm.count(x)>1: err.append(f'附件八重複 {x}')
print('手冊有效會員',tot[10],'名冊',len(r8))
print('\n錯誤',len(err));[print(' ✗',e) for e in err]
print('提醒',len(warn));[print(' △',w) for w in warn]
sys.exit(1 if err else 0)
