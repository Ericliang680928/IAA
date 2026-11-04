# 商務配對串聯

IAA 創新加速聯盟會現場配對系統，獨立運作（GitHub Pages + Supabase），不需要登入。

- `index.html`：配對系統（會友端、大螢幕、說明、主辦端）
- `rules.html`：給會友看的白話規則
- 資料庫：Supabase 的 `matching_*` 表與 `mm_*` 函式，建表 SQL 見 `setup.sql`
- 主辦端：頁面底部「主辦登入」，第一次使用時設定密碼
