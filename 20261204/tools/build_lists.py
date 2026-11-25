#!/usr/bin/env python3
"""由 agm/program.json 產生「頒發名單」PDF（每位頒發人一份），新增或修改頒獎項目只要改司儀稿資料再重跑。
用法：python3 tools/build_lists.py 輸出資料夾   需要 google-chrome。"""
import json,re,os,subprocess,sys,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
out=sys.argv[1] if len(sys.argv)>1 else '.'
p=json.load(open(root+'/agm/program.json',encoding='utf-8')); V=p['vars']
css=open(here+'/award.css',encoding='utf-8').read()
def sub(t):
    for k,v in V.items(): t=t.replace('{{%s}}'%k,v)
    return t.replace('  ',' ')
n=0;items=[]
for g in p['segments']:
    for s in g['scenes']:
        if s.get('slide'): n+=1
        if s['layout']=='award' and 'giver' in s and s['giver']:
            items.append((n if s.get('slide') else None,g,s))
by=collections.OrderedDict()
for no,g,s in items:
    giver=sub(s['giver'])
    if '理事長' in giver: continue   # 理事長頒發者另行處理
    by.setdefault(giver,[]).append((no,g,s))
def rows(s):
    L=[sub(x) for x in s['lines']] or [sub(s['receiver']).replace(' 代表受獎','').replace(' 代表受聘','')]
    out=[]
    for x in L:
        m=re.match(r'^(\S+?社|\S*(?:會長|執行長|秘書長|財務長|總召|知識長|人資長|顧問|營運長))\s+(\S+)$',x)
        out.append(m.groups() if m else ('',x))
    return out
def sec(i,no,s):
    r=rows(s);half=(len(r)+1)//2
    cntp=len([x for x in r if x[1]!='空缺'])
    def one(k,x): return f'<div class="row"><span class="n">{k}</span>'+(f'<span class="r">{x[0]}</span>' if x[0] else '')+f'<span class="p">{x[1]}</span><span class="ck"></span></div>'
    L=''.join(one(k+1,x) for k,x in enumerate(r[:half]));R=''.join(one(k+1+half,x) for k,x in enumerate(r[half:]))
    rep=sub(s['receiver'])
    meta=f'<b>{rep}</b>' if '代表' in rep else '全員上台'
    if s['note']: meta+='　｜　'+sub(s['note'])
    return f'<div class="sec"><div class="sh"><span class="no">{i}</span><span class="st2">{sub(s["title"])}</span><span class="tag">{cntp} 人{'＋空缺' if cntp<len(r) else ''}　簡報第 {no} 張</span></div><div class="meta">{meta}</div><div class="grid"><div>{L}</div><div>{R}</div></div></div>'
for giver,its in by.items():
    total=sum(len([x for x in rows(s) if x[1]!='空缺']) for _,_,s in its)
    # 重複受獎者
    cnt=collections.Counter(x[1] for _,_,s in its for x in rows(s))
    dup=[k for k,v in cnt.items() if v>1]
    note=f'<div class="note"><b>核對提醒</b>　{"、".join(dup)} 出現在多個項目，可能領多份，請接待組備足。</div>' if dup else ''
    body=''.join(sec(i+1,no,s) for i,(no,g,s) in enumerate(its))
    html=f'<!doctype html><meta charset="utf-8"><style>{css}.pg{{height:auto}}.in{{position:static;padding:30px 44px 20px 46px}}.row{{height:25px}}.sec{{margin-top:9px}}</style><div class="pg"><div class="bar"><i></i></div><div class="in"><div class="eyebrow">IAA 創新加速聯盟會　頒發名單</div><h1>{giver}　頒發名單</h1><div class="sub">共 {len(its)} 批、{total} 人次　｜　資料來源：司儀稿編輯台（program.json）</div>{body}{note}</div></div>'
    h=f'{out}/{re.sub(r"[ /]","",giver)}_頒發名單.html'
    open(h,'w',encoding='utf-8').write(html)
    subprocess.run(['google-chrome','--headless','--no-sandbox','--disable-gpu','--no-pdf-header-footer','--print-to-pdf='+h[:-5]+'.pdf',h],capture_output=True)
    os.remove(h); print(giver,len(its),'批',total,'人次 →',h[:-5]+'.pdf')
