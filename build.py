#!/usr/bin/env python3
"""README.md → _site/index.html（頁籤版）。

README.md 是唯一來源（source of truth）；index.html 為自動產物，不進 git。
本機預覽：pip install markdown && python3 build.py（產出 _site/index.html）。
正式部署交給 GitHub Actions（.github/workflows/pages.yml），push 後自動建置。

頁籤規則：
- H1 與其後的引言（第一個 `## ` 之前）＝固定頁首，永遠可見。
- 以 `## 一、`「中文數字＋、」開頭的 h2 各自成一個頁籤；標籤名見 NUM_LABEL，
  沒對照到的編號會自動用章節標題前幾個字當標籤（新增「六、…」就自動長出新頁籤）。
- 不帶編號的 h2（如「✅ 行程已訂定」）與「〇、」歸入「總覽」頁籤（或併入前一個頁籤）。
- 頁首在更新戳記下方插入天氣追蹤區塊（data/weather.json，由 fetch_weather.py 每日產生；缺檔就不顯示）。
- 頁籤狀態寫入 URL hash（#門票快通），可直接分享特定頁籤；列印時自動攤平全部內容。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

try:
    import markdown
except ImportError:
    sys.exit("需要 markdown 套件：pip install markdown（或直接 push 交給 GitHub Actions 建置）")

SRC = "README.md"
WEATHER = os.path.join("data", "weather.json")  # fetch_weather.py 產生，每日自動更新
OUT_DIR = "_site"
OUT = os.path.join(OUT_DIR, "index.html")

TAB_OVERVIEW = "總覽"
NUM_LABEL = {
    "〇": TAB_OVERVIEW,
    "一": "門票快通",
    "二": "逐日行程",
    "三": "待辦",
    "四": "經驗整理",
    "五": "行前準備",
}

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
    --control-border: #858e98;
    --maxw: 880px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16181c;
      --surface: #1e2125;
      --surface-2: #262a2f;
      --text: #cfd3d9;
      --text-dim: #8f969f;
      --border: #343941;
      --accent: #d98a7d;
      --accent-soft: #271d1b;
      --warn: #c49b5c;
      --warn-soft: #262013;
      --control-border: #626c79;
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
  h2 { font-size: 1.32rem; margin: 28px 0 12px; padding-top: 4px; }
  h3 { font-size: 1.08rem; margin: 26px 0 10px; }
  h4 { font-size: 0.98rem; margin: 18px 0 8px; color: var(--text-dim); }
  .updated {
    margin: -8px 0 20px;
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  .updated code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.82rem;
    background: var(--surface-2);
    padding: 1px 6px;
    border-radius: 4px;
  }
  p { margin: 10px 0; }
  a { color: var(--accent); }
  ul, ol { padding-left: 1.4em; }
  li { margin: 5px 0; }
  hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
  strong { font-weight: 600; }
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
  .tabs {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    background: var(--bg);
    padding: 10px 0;
    margin: 0 0 6px;
    border-bottom: 1px solid var(--border);
  }
  .tabs::-webkit-scrollbar { display: none; }
  .tab {
    flex: 0 0 auto;
    font: inherit;
    font-size: 0.92rem;
    color: var(--text-dim);
    background: var(--surface);
    border: 1px solid var(--control-border);
    border-radius: 999px;
    padding: 6px 15px;
    cursor: pointer;
  }
  .tab:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .tab.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
    font-weight: 600;
  }
  .panel[hidden] { display: none; }
  .panel > h2:first-child { margin-top: 14px; }
  /* 頁首天氣區塊（data/weather.json → render_weather） */
  .wx {
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 10px;
    padding: 12px 14px 10px;
    margin: 0 0 22px;
  }
  .wx-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 4px 12px; margin-bottom: 10px; }
  .wx-head h2 { margin: 0; font-size: 1.05rem; padding: 0; }
  .wx-meta { font-size: 0.8rem; color: var(--text-dim); }
  .wx-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .wx-day { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 0.85rem; line-height: 1.5; }
  .wx-day .d { font-weight: 600; }
  .wx-day .tag { color: var(--text-dim); font-size: 0.76rem; }
  .wx-day .ico { font-size: 1.7rem; line-height: 1.2; margin: 4px 0 0; }
  .wx-day .t { font-size: 1.02rem; }
  .wx-day.na { color: var(--text-dim); }
  .wx .callout { margin: 10px 0 0; font-size: 0.88rem; }
  .wx-trend { margin-top: 10px; font-size: 0.8rem; }
  .wx-trend summary { cursor: pointer; color: var(--text-dim); }
  .wx-trend .table-scroll { margin: 8px 0 0; }
  .wx-trend table { min-width: 0; font-size: 0.78rem; }
  .wx-trend th, .wx-trend td { padding: 4px 8px; white-space: nowrap; }
  .wx-note { font-size: 0.76rem; color: var(--text-dim); margin: 8px 0 0; }
  @media (max-width: 560px) { .wx-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 480px) {
    body { font-size: 16px; }
    h1 { font-size: 1.45rem; }
    h2 { font-size: 1.2rem; }
    .wrap { padding: 18px 14px 64px; }
  }
  @media print {
    .tabs { display: none; }
    .panel[hidden] { display: block; }
  }
"""

JS = """
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.tab'));
  var panels = [].slice.call(document.querySelectorAll('.panel'));
  function show(id, writeHash) {
    panels.forEach(function (p) { p.hidden = (p.id !== id); });
    tabs.forEach(function (t) {
      var on = (t.dataset.t === id);
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    if (writeHash) {
      history.replaceState(null, '', '#' + encodeURIComponent(id.slice(2)));
    }
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      show(t.dataset.t, true);
      window.scrollTo(0, 0);
    });
  });
  var h = decodeURIComponent(location.hash.slice(1));
  var target = h && document.getElementById('p-' + h) ? 'p-' + h : panels[0].id;
  show(target, false);
})();
"""


def last_updated():
    """回傳 (日期字串, commit 短碼)；以 README.md 最後一次變更為準。

    GitHub Actions 的 checkout 需 fetch-depth: 0 才有完整歷史；
    取不到時退而用 HEAD 或 build 當下時間，確保永遠有值。
    """
    def git(args):
        try:
            out = subprocess.run(
                ["git", *args], capture_output=True, text=True, check=True
            ).stdout.strip()
            return out or None
        except Exception:
            return None

    iso = git(["log", "-1", "--format=%cI", "--", SRC]) or git(
        ["log", "-1", "--format=%cI"]
    )
    short = git(["log", "-1", "--format=%h", "--", SRC]) or git(
        ["log", "-1", "--format=%h"]
    )

    if iso:
        date = iso[:10]
    else:
        date = datetime.now().strftime("%Y-%m-%d")
    return date, short


def md_to_html(md_text):
    """Markdown 轉 HTML，套用共用後處理：表格橫向捲動、blockquote → callout。"""
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

    return re.sub(r"<blockquote>(.*?)</blockquote>", to_callout, body, flags=re.DOTALL)


def short_label(title):
    """NUM_LABEL 沒對照到的章節，從標題擷取短標籤。"""
    t = re.sub(r"^[〇一二三四五六七八九十]+、\s*", "", title)
    t = re.split(r"[（(＋+/／\s]", t)[0]
    return t[:6] or title[:6]


def split_tabs(md_text):
    """把 README 切成 (頁首 md, [(頁籤標籤, 該籤 md), ...])。"""
    chunks = re.split(r"(?m)^(?=##\s)", md_text)
    preamble, sections = chunks[0], chunks[1:]

    tabs = []  # [label, md]

    def add(label, md):
        if tabs and tabs[-1][0] == label:
            tabs[-1][1] += "\n" + md
        else:
            tabs.append([label, md])

    for sec in sections:
        sec = re.sub(r"\n-{3,}\s*$", "", sec.rstrip())  # 章節尾端的 --- 是舊分隔線，切籤後不需要
        title = sec.splitlines()[0][3:].strip()
        m = re.match(r"([〇一二三四五六七八九十]+)、", title)
        if m:
            label = NUM_LABEL.get(m.group(1)) or short_label(title)
            add(label, sec)
        else:
            add(tabs[-1][0] if tabs else TAB_OVERVIEW, sec)

    return preamble, tabs


# WMO weather code → (emoji, 台灣慣用描述)
WMO = {
    0: ("☀️", "晴"), 1: ("🌤️", "大致晴"), 2: ("⛅", "多雲時晴"), 3: ("☁️", "陰"),
    45: ("🌫️", "霧"), 48: ("🌫️", "霧"),
    51: ("🌦️", "毛毛雨"), 53: ("🌦️", "毛毛雨"), 55: ("🌧️", "毛毛雨"),
    56: ("🌧️", "凍雨"), 57: ("🌧️", "凍雨"),
    61: ("🌧️", "小雨"), 63: ("🌧️", "中雨"), 65: ("🌧️", "大雨"),
    66: ("🌧️", "凍雨"), 67: ("🌧️", "凍雨"),
    71: ("🌨️", "小雪"), 73: ("🌨️", "中雪"), 75: ("🌨️", "大雪"), 77: ("🌨️", "雪粒"),
    80: ("🌦️", "陣雨"), 81: ("🌧️", "陣雨"), 82: ("⛈️", "強陣雨"),
    85: ("🌨️", "陣雪"), 86: ("🌨️", "大陣雪"),
    95: ("⛈️", "雷雨"), 96: ("⛈️", "雷雨夾冰雹"), 99: ("⛈️", "雷雨夾冰雹"),
}
TRIP_TAG = {
    "2026-09-24": "抵達日・KIX 落地",
    "2026-09-25": "USJ Day 1",
    "2026-09-26": "USJ Day 2",
    "2026-09-27": "回程・KIX 傍晚起飛",
}
WEEKDAY = "一二三四五六日"


def _wmo(code):
    try:
        return WMO.get(int(code), ("🌡️", f"代碼 {code}"))
    except (TypeError, ValueError):
        return ("❔", "無資料")


def _md(date_str):
    """2026-09-24 → 9/24（四）"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}/{d.day}（{WEEKDAY[d.weekday()]}）"


def _num(v, nd=0):
    if v is None:
        return "–"
    return f"{v:.{nd}f}"


def render_weather():
    """data/weather.json → 頁首天氣區塊 HTML；沒有資料檔就回傳空字串。"""
    if not os.path.exists(WEATHER):
        return ""
    with open(WEATHER, encoding="utf-8") as f:
        data = json.load(f)
    snaps = data.get("snapshots") or {}
    if not snaps:
        return ""
    trip_start, trip_end = data.get("trip", ["2026-09-24", "2026-09-27"])
    d0 = datetime.strptime(trip_start, "%Y-%m-%d")
    trip_days = []
    while d0.strftime("%Y-%m-%d") <= trip_end:
        trip_days.append(d0.strftime("%Y-%m-%d"))
        d0 += timedelta(days=1)

    latest_key = max(snaps)
    latest = snaps[latest_key]["days"]
    countdown = (datetime.strptime(trip_start, "%Y-%m-%d") - datetime.strptime(latest_key, "%Y-%m-%d")).days
    if countdown > 0:
        cd = f"距出發還有 {countdown} 天"
    elif countdown == 0:
        cd = "今天出發"
    else:
        cd = "旅程進行中" if latest_key <= trip_end else "旅程已結束"

    cards, alerts = [], []
    for day in trip_days:
        v = latest.get(day)
        tag = TRIP_TAG.get(day, "")
        if not v:
            cards.append(
                f'<div class="wx-day na"><div class="d">{_md(day)}</div><div class="tag">{tag}</div>'
                f'<div class="ico">⏳</div><div>尚未進入 16 日預報範圍</div></div>'
            )
            continue
        ico, desc = _wmo(v.get("weather_code"))
        gust = v.get("wind_gusts_10m_max") or 0
        rain = v.get("precipitation_sum") or 0
        code = v.get("weather_code") or 0
        if gust >= 60 or rain >= 50 or int(code) in (82, 95, 96, 99):
            alerts.append(_md(day))
        cards.append(
            f'<div class="wx-day"><div class="d">{_md(day)}</div><div class="tag">{tag}</div>'
            f'<div class="ico">{ico}</div><div>{desc}</div>'
            f'<div class="t">{_num(v.get("temperature_2m_min"))}～{_num(v.get("temperature_2m_max"))}°C</div>'
            f'<div>降雨機率 {_num(v.get("precipitation_probability_max"))}%・雨量 {_num(rain, 1)} mm</div>'
            f'<div>風 {_num(v.get("wind_speed_10m_max"))} km/h・陣風 {_num(gust)}</div>'
            f'<div>紫外線指數 {_num(v.get("uv_index_max"), 1)}</div></div>'
        )

    alert_html = ""
    if alerts:
        alert_html = (
            '<div class="callout warn">⚠ 預報出現強風／大雨／雷雨訊號：' + "、".join(alerts)
            + "。留意颱風動態與航班／USJ 官方公告（颱風三情境見「門票快通」頁籤）。</div>"
        )

    # 預報變化：每個旅行日在歷次快照中的預報（最近的在上）
    trend_html = ""
    keys = sorted(snaps, reverse=True)[:10]
    if len(keys) >= 2:
        head = "".join(f"<th>{_md(d)}</th>" for d in trip_days)
        rows = []
        for k in keys:
            cells = []
            for d in trip_days:
                v = snaps[k]["days"].get(d)
                if not v:
                    cells.append("<td>–</td>")
                    continue
                ico, _ = _wmo(v.get("weather_code"))
                cells.append(
                    f'<td>{ico} {_num(v.get("temperature_2m_min"))}～{_num(v.get("temperature_2m_max"))}° '
                    f'雨 {_num(v.get("precipitation_probability_max"))}%</td>'
                )
            rows.append(f"<tr><td>{_md(k)} 預報</td>{''.join(cells)}</tr>")
        trend_html = (
            f'<details class="wx-trend"><summary>📈 預報變化（近 {len(keys)} 次快照，看趨勢穩不穩）</summary>'
            f'<div class="table-scroll"><table><thead><tr><th>快照日</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></details>'
        )
    else:
        trend_html = '<p class="wx-note">📈 從明天起每天累積一份快照，這裡會顯示旅行日預報的變化趨勢。</p>'

    loc = data.get("location", {}).get("name", "大阪")
    src = data.get("source", "Open-Meteo")
    fetched = snaps[latest_key].get("fetched_at", latest_key)[:16].replace("T", " ")
    return (
        '<section class="wx" aria-label="天氣追蹤">'
        f'<div class="wx-head"><h2>🌤 {loc} 天氣追蹤</h2>'
        f'<span class="wx-meta">預報日 {latest_key}・{cd}・每天 07:00（日本時間）自動更新</span></div>'
        f'<div class="wx-grid">{"".join(cards)}</div>'
        f"{alert_html}{trend_html}"
        f'<p class="wx-note">資料：{src}，抓取 {fetched} JST；超過一週的預報僅供參考，出發前 3 天內的最準。'
        '颱風動態：<a href="https://www.jma.go.jp/bosai/map.html#5/34.5/137/&elem=root&typhoon=all&contents=typhoon" target="_blank" rel="noopener">日本氣象廳</a>・'
        '<a href="https://www.cwa.gov.tw/V8/C/P/Typhoon/ty.html" target="_blank" rel="noopener">中央氣象署</a>・'
        '<a href="https://www.usj.co.jp/web/ja/jp/park/schedule" target="_blank" rel="noopener">USJ 營運公告</a></p>'
        "</section>"
    )


def build():
    with open(SRC, encoding="utf-8") as f:
        md_text = f.read()

    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = m.group(1).strip() if m else "九月旅遊計劃"

    preamble_md, tabs = split_tabs(md_text)
    header = md_to_html(preamble_md)

    # 在主標題下方插入「最後更新」一行（含 commit 短碼當版本號）
    date, short = last_updated()
    ver = f" · 版本 <code>{short}</code>" if short else ""
    stamp = f'<p class="updated">最後更新：{date}{ver}</p>'
    if "</h1>" in header:
        header = header.replace("</h1>", "</h1>\n" + stamp, 1)
    else:
        header = stamp + "\n" + header

    # 頁首最上方（更新戳記之後、引言之前）插入天氣追蹤區塊；沒有 data/weather.json 就略過
    wx = render_weather()
    if wx:
        header = header.replace(stamp, stamp + "\n" + wx, 1)

    nav = "\n".join(
        f'<button class="tab" role="tab" data-t="p-{label}" aria-selected="false">{label}</button>'
        for label, _ in tabs
    )
    panels = "\n".join(
        f'<section class="panel" id="p-{label}" role="tabpanel" hidden>\n{md_to_html(md)}\n</section>'
        for label, md in tabs
    )

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
        f"{header}\n"
        f'<nav class="tabs" role="tablist">\n{nav}\n</nav>\n'
        f"{panels}\n"
        "</div>\n"
        "<noscript><style>.panel[hidden] { display: block; } .tabs { display: none; }</style></noscript>\n"
        f"<script>{JS}</script>\n"
        "</body>\n</html>\n"
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    labels = "、".join(label for label, _ in tabs)
    print(f"wrote {OUT} ({len(page)} bytes)；頁籤：{labels}")


if __name__ == "__main__":
    build()
