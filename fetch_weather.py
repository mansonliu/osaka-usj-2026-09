#!/usr/bin/env python3
"""每日抓大阪環球影城的天氣預報，累積存到 data/weather.json（給 build.py 渲染頁首天氣區塊）。

- 資料來源：Open-Meteo（免金鑰）16 日預報，座標＝USJ（大阪市此花區）。
- 每次執行存一個「快照」（以 JST 日期為 key），同一天重跑會覆蓋當天快照；
  歷次快照都保留，網頁可顯示「旅行日預報怎麼變」。
- 旅程結束（TRIP_END 之後）就不再更新，直接結束。
- 只用標準函式庫，GitHub Actions 與本機都能直接跑：python3 fetch_weather.py
"""
import json
import os
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


def main():
    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    if today > TRIP_END:
        print(f"旅程已於 {TRIP_END} 結束，不再更新天氣（今天 {today}）。")
        return 0

    with urllib.request.urlopen(URL, timeout=30) as r:
        raw = json.load(r)
    d = raw["daily"]
    days = {}
    for i, date in enumerate(d["time"]):
        days[date] = {k: d[k][i] for k in DAILY_VARS}

    data = {"location": LOCATION, "trip": [TRIP_START, TRIP_END], "snapshots": {}}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    data["location"] = LOCATION
    data["trip"] = [TRIP_START, TRIP_END]
    data["source"] = "Open-Meteo（best_match 模型，16 日預報）"
    data.setdefault("snapshots", {})[today] = {
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M+09:00"),
        "days": days,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    covered = [x for x in days if TRIP_START <= x <= TRIP_END]
    print(f"wrote {OUT}：快照 {today}（共 {len(data['snapshots'])} 份），"
          f"預報涵蓋 {d['time'][0]}～{d['time'][-1]}，旅行日已涵蓋 {len(covered)}/4 天")
    for x in covered:
        v = days[x]
        print(f"  {x}  code={v['weather_code']}  {v['temperature_2m_min']}～{v['temperature_2m_max']}°C  "
              f"降雨機率 {v['precipitation_probability_max']}%  雨量 {v['precipitation_sum']}mm  "
              f"風 {v['wind_speed_10m_max']} km/h（陣風 {v['wind_gusts_10m_max']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
