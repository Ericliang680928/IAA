#!/usr/bin/env python3
"""由使用者手動排版的範本（範本/IAA手冊_版面範本_*.docx）匯出 Word 與 PDF。
用法: python3 export_handbook.py 範本.docx 輸出前綴 [--replace 舊=>新 ...]
- Word 版：沿用範本的目錄頁碼（使用者在 Word 看到的頁碼）。
- PDF 版：用 LibreOffice 排版，目錄頁碼改成 PDF 實際頁碼（兩者排版差 0~1 頁）。
"""
import sys, re, shutil, subprocess, os, tempfile
import docx
from docx.oxml.ns import qn

TOC = [("第四屆會長 上任感言", "第四屆會長 上任感言"), ("第三屆會長 卸任感言", "第三屆會長 卸任感言"),
       ("聯合會理事長 致詞", "聯合會理事長 致詞"), ("聯合會副理事長 致詞", "聯合會副理事長 致詞"),
       ("程序表", None), ("專題演講暨講師介紹", "專題演講暨講師介紹"), ("第四屆第一次會員大會議程", "第四屆第一次會員大會議程"),
       ("附件一：", "【附件一】"), ("附件二：", "【附件二】"), ("附件三：", "【附件三】"), ("附件四：", "【附件四】"),
       ("附件五：", "【附件五】"), ("附件六：", "【附件六】"), ("附件七：", "【附件七】"), ("附件八：", "【附件八】")]

def para_text(p): return ''.join(r.text for r in p.runs)

def replace_in_paragraph(p, old, new):
    full = para_text(p)
    if old not in full: return 0
    for r in p.runs:                       # 整段落落在單一 run：直接換，保留格式
        if old in r.text:
            r.text = r.text.replace(old, new); return 1
    # 跨 run：以第一個受影響 run 承接
    i = full.index(old); pos = 0; first = True
    for r in p.runs:
        s, e = pos, pos + len(r.text); pos = e
        if e <= i or s >= i + len(old): continue
        a, b = max(i, s) - s, min(i + len(old), e) - s
        r.text = r.text[:a] + (new if first else '') + r.text[b:]; first = False
    return 1

def all_paragraphs(d):
    for p in d.paragraphs: yield p
    def cells(tbls):
        for t in tbls:
            for row in t.rows:
                seen = set()
                for c in row.cells:
                    if id(c._tc) in seen: continue
                    seen.add(id(c._tc))
                    for p in c.paragraphs: yield p
                    yield from cells(c.tables)
    yield from cells(d.tables)

def toc_paragraphs(d):
    out = []
    for p in d.paragraphs[:40]:
        t = para_text(p)
        if '\t' in t and re.search(r'\t\d+$', t): out.append(p)
    return out

def set_toc_numbers(d, nums):
    ps = toc_paragraphs(d)
    assert len(ps) == len(nums), (len(ps), len(nums))
    for p, n in zip(ps, nums):
        runs = p.runs; k = None
        for i, r in enumerate(runs):
            if '\t' in r.text: k = i; break
        runs[k].text = runs[k].text.split('\t')[0] + '\t' + str(n)
        for r in runs[k + 1:]: r.text = ''

def pdf_pages(pdf):
    n = int(re.search(r'Pages:\s+(\d+)', subprocess.check_output(['pdfinfo', pdf]).decode()).group(1))
    return [subprocess.check_output(['pdftotext', '-f', str(i), '-l', str(i), '-layout', pdf, '-']).decode() for i in range(1, n + 1)]

def toc_from_pdf(pdf):
    pages = pdf_pages(pdf); res = []
    heads = []
    for t in pages:
        ls = [l.strip() for l in t.splitlines() if l.strip()]
        heads.append(' '.join(ls[:2]))
    for label, key in TOC:
        pg = None
        if key:
            for i, h in enumerate(heads[2:], 3):   # 封面、目錄之後
                if h.replace(' ', '').startswith(key.replace(' ', '')): pg = i; break
        res.append(pg)
    if res[4] is None and res[5]: res[4] = res[5] - 1          # 程序表是整頁圖片，沒有文字
    return [p - 2 if p else 0 for p in res]

def soffice(docx_path, outdir):
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', outdir, docx_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def main():
    tpl, prefix = sys.argv[1], sys.argv[2]
    public = '--public' in sys.argv
    reps = [a.split('=>', 1) for a in sys.argv[3:] if a != '--public']
    d = docx.Document(tpl)
    if public:                                    # 公開版：附件八行動電話一律「不公開」
        t = d.tables[-1]
        for row in t.rows[1:]:
            for p in row.cells[-1].paragraphs:
                if p.runs: p.runs[0].text = '不公開'; [setattr(r, 'text', '') for r in p.runs[1:]]
    for old, new in reps:
        n = sum(replace_in_paragraph(p, old, new) for p in all_paragraphs(d))
        print('replace', old, '->', new, ':', n)
    d.save(prefix + '.docx')                       # Word 版（範本頁碼）
    tmp = tempfile.mkdtemp(); shutil.copy(prefix + '.docx', tmp + '/b.docx')
    soffice(tmp + '/b.docx', tmp)
    for _ in range(2):                             # PDF 版：頁碼以 LibreOffice 排版為準
        nums = toc_from_pdf(tmp + '/b.pdf'); print('PDF 目錄頁碼', nums)
        dd = docx.Document(tmp + '/b.docx'); set_toc_numbers(dd, nums); dd.save(tmp + '/b.docx'); soffice(tmp + '/b.docx', tmp)
    shutil.copy(tmp + '/b.pdf', prefix + '.pdf')
    print('done', prefix)
main()
