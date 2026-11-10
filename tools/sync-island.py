#!/usr/bin/env python3
"""把「2027年 IAA 會務群島」Artifact 的 HTML 轉成網站上的 island/index.html。
用法：python3 tools/sync-island.py <artifact.html> <artifact版本代號>
- 加上 noindex（內部頁面，不讓搜尋引擎收錄）
- 寫入 island/.version，用來判斷下次要不要更新
- 內容沒變就不改檔，回傳碼 0；有更新回傳碼 10
"""
import sys, re, pathlib, datetime
src, ver = sys.argv[1], sys.argv[2]
root = pathlib.Path(__file__).resolve().parent.parent
out = root / "island" / "index.html"
verf = root / "island" / ".version"
html = pathlib.Path(src).read_text(encoding="utf-8")
if "<title>" not in html or "THREE" not in html:
    sys.exit("輸入檔看起來不是會務群島頁面，已停止")
meta = '<meta name="robots" content="noindex, nofollow">'
if meta not in html:
    html = re.sub(r"(<head[^>]*>)", r"\1\n" + meta, html, count=1, flags=re.I)
old = out.read_text(encoding="utf-8") if out.exists() else ""
if html == old and verf.exists() and verf.read_text().strip().split()[0] == ver:
    print("沒有變動"); sys.exit(0)
out.write_text(html, encoding="utf-8")
verf.write_text(ver + " " + datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ") + "\n")
print("已更新 island/index.html，來源版本", ver); sys.exit(10)
