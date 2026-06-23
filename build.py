#!/usr/bin/env python3
"""README.md → _site/index.html。

README.md 是唯一來源（source of truth）；index.html 為自動產物，不進 git。
本機預覽：pip install markdown && python3 build.py（產出 _site/index.html）。
正式部署交給 GitHub Actions（.github/workflows/pages.yml），push 後自動建置。
"""
import os
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit("需要 markdown 套件：pip install markdown（或直接 push 交給 GitHub Actions 建置）")

SRC = "README.md"
OUT_DIR = "_site"
OUT = os.path.join(OUT_DIR, "index.html")

CSS = """
  :root {
    --bg: #ffffff;
    --surface: #f6f7f9;
    --surface-2: #eef0f3;
    --text: #1c1f24;
    --text-dim: #5a626c;
    --border: #d9dde2;
    --accent: #c0392b;
    --accent-soft: #fbeae8;
    --warn: #b9770e;
    --warn-soft: #fdf3e2;
    --maxw: 880px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #15171a;
      --surface: #1e2125;
      --surface-2: #262a2f;
      --text: #e6e8eb;
      --text-dim: #9aa1a9;
      --border: #343941;
      --accent: #ff7a6b;
      --accent-soft: #2a1d1b;
      --warn: #e0a64a;
      --warn-soft: #2a2114;
    }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei",
                 "PingFang TC", "Noto Sans TC", "Helvetica Neue", Arial, sans-serif;
    line-height: 1.7;
    font-size: 17px;
  }
  .wrap { max-width: var(--maxw); margin: 0 auto; padding: 24px 18px 80px; }
  h1 {
    font-size: 1.7rem;
    line-height: 1.3;
    margin: 0 0 18px;
    padding-bottom: 14px;
    border-bottom: 2px solid var(--accent);
  }
  h2 { font-size: 1.32rem; margin: 40px 0 12px; padding-top: 8px; }
  h3 { font-size: 1.08rem; margin: 26px 0 10px; }
  h4 { font-size: 0.98rem; margin: 18px 0 8px; color: var(--text-dim); }
  p { margin: 10px 0; }
  a { color: var(--accent); }
  ul, ol { padding-left: 1.4em; }
  li { margin: 5px 0; }
  hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
  strong { font-weight: 700; }
  blockquote { margin: 0; }
  .callout {
    border-left: 4px solid var(--accent);
    background: var(--accent-soft);
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 14px 0;
    font-size: 0.95rem;
  }
  .callout.warn { border-left-color: var(--warn); background: var(--warn-soft); }
  .callout p:first-child { margin-top: 0; }
  .callout p:last-child { margin-bottom: 0; }
  .table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 14px 0; }
  table {
    border-collapse: collapse;
    width: 100%;
    min-width: 520px;
    font-size: 0.9rem;
  }
  th, td {
    border-bottom: 1px solid var(--border);
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
  }
  thead th { background: var(--surface-2); border-bottom: 2px solid var(--border); white-space: nowrap; }
  tbody tr:nth-child(even) { background: var(--surface); }
  @media (max-width: 480px) {
    body { font-size: 16px; }
    h1 { font-size: 1.45rem; }
    h2 { font-size: 1.2rem; }
    .wrap { padding: 18px 14px 64px; }
  }
"""


def build():
    with open(SRC, encoding="utf-8") as f:
        md_text = f.read()

    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = m.group(1).strip() if m else "九月旅遊計劃"

    body = markdown.markdown(
        md_text,
        extensions=["tables", "sane_lists", "nl2br"],
    )

    # 表格包一層橫向捲動，手機上不會撐破版面
    body = re.sub(
        r"<table>.*?</table>",
        lambda mt: '<div class="table-scroll">' + mt.group(0) + "</div>",
        body,
        flags=re.DOTALL,
    )

    # blockquote 轉成 callout；含警示符號的用 warn 變體（橘）
    def to_callout(mt):
        inner = mt.group(1).strip()
        cls = "callout warn" if re.search(r"⚠|🔴|注意|提醒", inner) else "callout"
        return f'<div class="{cls}">{inner}</div>'

    body = re.sub(r"<blockquote>(.*?)</blockquote>", to_callout, body, flags=re.DOTALL)

    page = (
        "<!DOCTYPE html>\n"
        '<html lang="zh-Hant">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex, nofollow">\n'
        f"<title>{title}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body>\n"
        '<div class="wrap">\n'
        f"{body}\n"
        "</div>\n</body>\n</html>\n"
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    build()
