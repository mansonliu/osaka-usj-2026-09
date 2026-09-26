#!/usr/bin/env python3
"""每日抓大阪環球影城的天氣預報，累積存到 data/weather.json（給 build.py 渲染頁首天氣區塊）。

- 資料來源：Open-Meteo（免金鑰）16 日預報，座標＝USJ（大阪市此花區）。
- 每次執行存一個「快照」（以 JST 日期為 key），同一天重跑會覆蓋當天快照；
  歷次快照都保留，網頁可顯示「旅行日預報怎麼變」。
- 旅行日過完之後，另從日本氣象廳抓大阪氣象台的當日實測值存到 "actuals"，網頁拿來和「前一天的預報」對照。
- 旅程結束（TRIP_END）後不再存預報快照；隔天（補完最後一天的實測）之後就完全不再更新。
- 只用標準函式庫，GitHub Actions 與本機都能直接跑：python3 fetch_weather.py
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = os.path.join("data", "weather.json")
LOCATION = {"name": "大阪・環球影城（此花區）", "lat": 34.6654, "lon": 135.4323}
TRIP_START = "2026-09-24"
TRIP_END = "2026-09-27"
JST = timezone(timedelta(hours=9))
DAILY_VARS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "uv_index_max",
]
URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LOCATION['lat']}&longitude={LOCATION['lon']}"
    f"&daily={','.join(DAILY_VARS)}&timezone=Asia%2FTokyo&forecast_days=16"
)
# 實測：日本氣象廳「過去の気象データ」大阪（大阪管区気象台，中央區，離 USJ 約 8 公里）日值
JMA_STATION = "日本氣象廳 大阪氣象台（中央區）實測"
JMA_URL = ("https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
           "?prec_no=62&block_no=47772&year={y}&month={m}&day=&view=")


def _jma_num(v):
    """氣象廳的數值可能帶品質記號（ ) ] # 等），去掉後轉數字；「--」＝該現象未發生（如無降雨）記 0；沒有值回傳 None。"""
    if (v or "").strip().startswith("--"):
        return 0.0
    m = re.search(r"-?\d+(\.\d+)?", v or "")
    return float(m.group(0)) if m else None


def fetch_actuals(today):
    """回傳 {日期: 實測值}，只收旅行日中「今天以前」已過完的日子。"""
    out = {}
    months = sorted({(int(d[:4]), int(d[5:7])) for d in (TRIP_START, TRIP_END)})
    for y, m in months:
        req = urllib.request.Request(JMA_URL.format(y=y, m=m), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = r.read().decode("utf-8", "ignore")
        for row in re.findall(r'<tr class="mtx"[^>]*>(.*?)</tr>', page, re.S):
            c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
                 for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
            if len(c) != 21 or not c[0].isdigit():
                continue
            date = f"{y:04d}-{m:02d}-{int(c[0]):02d}"
            if not (TRIP_START <= date <= TRIP_END) or date >= today or _jma_num(c[7]) is None:
                continue
            out[date] = {
                "precipitation_sum": _jma_num(c[3]),
                "precipitation_max_1h": _jma_num(c[4]),
                "temperature_2m_max": _jma_num(c[7]),
                "temperature_2m_min": _jma_num(c[8]),
                "wind_speed_max_ms": _jma_num(c[12]),
                "wind_gust_max_ms": _jma_num(c[14]),
                "sunshine_h": _jma_num(c[16]),
                "weather_day": c[19],
                "weather_night": c[20],
            }
    return out


def main():
    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    day_after_end = (datetime.strptime(TRIP_END, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    if today > day_after_end:
        print(f"旅程已於 {TRIP_END} 結束、實測也已補完，不再更新天氣（今天 {today}）。")
        return 0

    data = {"location": LOCATION, "trip": [TRIP_START, TRIP_END], "snapshots": {}}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    data["location"] = LOCATION
    data["trip"] = [TRIP_START, TRIP_END]
    data["source"] = "Open-Meteo（best_match 模型，16 日預報）"

    # 已過完的旅行日：補氣象廳實測。抓不到不影響預報快照，下次執行再補。
    try:
        acts = fetch_actuals(today)
        if acts:
            data.setdefault("actuals", {}).update(acts)
            data["actuals_source"] = JMA_STATION
        print(f"實測：{', '.join(sorted(acts)) or '（尚無已過完的旅行日）'}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ 氣象廳實測抓取失敗，略過：{e}")

    days = {}
    if today <= TRIP_END:
        with urllib.request.urlopen(URL, timeout=30) as r:
            raw = json.load(r)
        d = raw["daily"]
        for i, date in enumerate(d["time"]):
            days[date] = {k: d[k][i] for k in DAILY_VARS}
        data.setdefault("snapshots", {})[today] = {
            "fetched_at": now.strftime("%Y-%m-%dT%H:%M+09:00"),
            "days": days,
        }

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    if not days:
        print(f"wrote {OUT}：旅程已結束，只補實測、不存預報快照")
        return 0
    covered = [x for x in days if TRIP_START <= x <= TRIP_END]
    print(f"wrote {OUT}：快照 {today}（共 {len(data['snapshots'])} 份），"
          f"預報涵蓋 {min(days)}～{max(days)}，旅行日已涵蓋 {len(covered)}/4 天")
    for x in covered:
        v = days[x]
        print(f"  {x}  code={v['weather_code']}  {v['temperature_2m_min']}～{v['temperature_2m_max']}°C  "
              f"降雨機率 {v['precipitation_probability_max']}%  雨量 {v['precipitation_sum']}mm  "
              f"風 {v['wind_speed_10m_max']} km/h（陣風 {v['wind_gusts_10m_max']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
