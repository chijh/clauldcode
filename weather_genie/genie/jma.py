"""気象庁(JMA)公式APIから、つくば市を含む茨城県の天気予報を取得するモジュール.

APIキーは不要。以下の公開エンドポイントを利用する。
  - 予報:       https://www.jma.go.jp/bosai/forecast/data/forecast/{area}.json
  - 概況文:     https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area}.json

エリアコード:
  - 080000 : 茨城県（府県予報区）
  - 080020 : 茨城県南部（つくば市はここに属する）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from urllib.request import Request, urlopen

# 茨城県の予報区コードと、つくば市が属する細分区（県南部）コード。
PREFECTURE_CODE = "080000"
TSUKUBA_SUBAREA_CODE = "080020"

_FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
_OVERVIEW_URL = "https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{code}.json"

_USER_AGENT = "weather-genie/0.1 (+https://www.jma.go.jp/)"


class JmaError(RuntimeError):
    """JMA APIの取得・解析に失敗したときに送出する例外."""


@dataclass
class DailyForecast:
    """1日ぶんの予報."""

    date: datetime
    weather: str | None = None          # 例: "晴れ 時々 くもり"
    pops: list[tuple[str, str]] = field(default_factory=list)  # (時間帯, 降水確率%)
    temp_min: str | None = None         # 最低気温(℃)
    temp_max: str | None = None         # 最高気温(℃)

    @property
    def label(self) -> str:
        weekday = "月火水木金土日"[self.date.weekday()]
        return f"{self.date.month}月{self.date.day}日({weekday})"


def _fetch_json(url: str) -> object:
    """指定URLからJSONを取得して返す."""
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:  # ネットワーク・HTTPエラーをまとめて包む
        raise JmaError(f"JMA APIへの接続に失敗しました: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JmaError(f"JMA APIの応答を解析できませんでした: {exc}") from exc


def _pick_area(areas: list[dict], code: str) -> dict | None:
    """areas配列から指定コードのエリアを取り出す（無ければNone）."""
    for area in areas:
        if area.get("area", {}).get("code") == code:
            return area
    return areas[0] if areas else None


# 気温観測点の優先順位。つくば市は土浦(40341)が最寄り、次点で水戸(40201)。
_TEMP_POINT_PRIORITY = ("40341", "40201")


def _pick_temp_area(areas: list[dict]) -> dict | None:
    """気温の観測点を、つくば市に近い順で選ぶ（無ければ先頭）."""
    for code in _TEMP_POINT_PRIORITY:
        for area in areas:
            if area.get("area", {}).get("code") == code:
                return area
    for area in areas:
        if "つくば" in area.get("area", {}).get("name", ""):
            return area
    return areas[0] if areas else None


def _parse_dt(value: str) -> datetime:
    """JMAのISO8601文字列(例: 2026-07-02T11:00:00+09:00)をdatetimeに変換."""
    return datetime.fromisoformat(value)


class TsukubaWeather:
    """つくば市の天気予報をまとめて保持するオブジェクト."""

    def __init__(self, forecast: list, overview: dict):
        self.publishing_office: str = forecast[0].get("publishingOffice", "気象庁")
        self.report_datetime: datetime = _parse_dt(forecast[0]["reportDatetime"])
        self.overview_text: str = overview.get("text", "").strip()
        self.days: list[DailyForecast] = []
        self._build(forecast)

    # ---- 解析 --------------------------------------------------------------
    def _build(self, forecast: list) -> None:
        by_date: dict[str, DailyForecast] = {}

        def get_day(dt: datetime) -> DailyForecast:
            key = dt.strftime("%Y-%m-%d")
            if key not in by_date:
                by_date[key] = DailyForecast(date=dt)
            return by_date[key]

        # --- 短期予報 (forecast[0]) ---
        short = forecast[0]["timeSeries"]

        # timeSeries[0]: 天気文
        ts_weather = short[0]
        w_area = _pick_area(ts_weather["areas"], TSUKUBA_SUBAREA_CODE)
        if w_area:
            for t, text in zip(ts_weather["timeDefines"], w_area.get("weathers", [])):
                day = get_day(_parse_dt(t))
                # 全角スペースを半角に整える
                day.weather = " ".join(text.split())

        # timeSeries[1]: 降水確率
        if len(short) > 1:
            ts_pop = short[1]
            p_area = _pick_area(ts_pop["areas"], TSUKUBA_SUBAREA_CODE)
            if p_area:
                for t, pop in zip(ts_pop["timeDefines"], p_area.get("pops", [])):
                    dt = _parse_dt(t)
                    day = get_day(dt)
                    hour = dt.hour
                    span = f"{hour:02d}-{(hour + 6) % 24:02d}時"
                    day.pops.append((span, pop))

        # timeSeries[2]: 気温（地点別）
        # 茨城県南部の観測点は「水戸」と「土浦」。つくば市は土浦が最も近い。
        if len(short) > 2:
            ts_temp = short[2]
            t_area = _pick_temp_area(ts_temp["areas"])
            if t_area:
                temps = t_area.get("temps", [])
                for t, temp in zip(ts_temp["timeDefines"], temps):
                    dt = _parse_dt(t)
                    day = get_day(dt)
                    if temp == "":
                        continue
                    # JMAの慣例: 00:00頃=最低気温、09:00頃=最高気温（時刻で判定）
                    if dt.hour < 9:
                        day.temp_min = temp
                    else:
                        day.temp_max = temp

        # --- 週間予報 (forecast[1]) ---
        if len(forecast) > 1:
            self._merge_weekly(forecast[1], get_day)

        self.days = [by_date[k] for k in sorted(by_date)]

    def _merge_weekly(self, weekly: dict, get_day) -> None:
        series = weekly.get("timeSeries", [])
        # weekly[0]: 天気コード＆降水確率, weekly[1]: 気温
        if series:
            w = series[0]
            w_area = _pick_area(w["areas"], TSUKUBA_SUBAREA_CODE)
            if w_area:
                weather_codes = w_area.get("weatherCodes", [])
                pops = w_area.get("pops", [])
                for i, t in enumerate(w["timeDefines"]):
                    day = get_day(_parse_dt(t))
                    if day.weather is None and i < len(weather_codes):
                        day.weather = _WEATHER_CODE.get(weather_codes[i], "")
                    if not day.pops and i < len(pops) and pops[i] != "":
                        day.pops.append(("終日", pops[i]))
        if len(series) > 1:
            temp = series[1]
            # 気温は地点別。つくばに近い土浦→水戸→先頭 の優先で選ぶ。
            t_area = _pick_temp_area(temp["areas"])
            if t_area:
                mins = t_area.get("tempsMin", [])
                maxs = t_area.get("tempsMax", [])
                for i, t in enumerate(temp["timeDefines"]):
                    day = get_day(_parse_dt(t))
                    if day.temp_min is None and i < len(mins) and mins[i] != "":
                        day.temp_min = mins[i]
                    if day.temp_max is None and i < len(maxs) and maxs[i] != "":
                        day.temp_max = maxs[i]


# 週間予報で使われる天気コード → 日本語（主要なものだけ）。
_WEATHER_CODE = {
    "100": "晴れ", "101": "晴れ 時々 くもり", "102": "晴れ 一時 雨", "104": "晴れ 一時 雪",
    "110": "晴れ のち くもり", "111": "晴れ のち くもり", "112": "晴れ のち 雨",
    "200": "くもり", "201": "くもり 時々 晴れ", "202": "くもり 一時 雨", "204": "くもり 一時 雪",
    "210": "くもり のち 晴れ", "211": "くもり のち 晴れ", "212": "くもり のち 雨",
    "300": "雨", "301": "雨 時々 晴れ", "302": "雨 時々 止む", "303": "雨 時々 雪",
    "308": "雨 大雨", "311": "雨 のち 晴れ", "313": "雨 のち くもり",
    "400": "雪", "401": "雪 時々 晴れ", "402": "雪 時々 止む", "403": "雪 時々 雨",
    "411": "雪 のち 晴れ", "413": "雪 のち くもり", "414": "雪 のち 雨",
}


def fetch_tsukuba_weather() -> TsukubaWeather:
    """つくば市（茨城県南部）の最新の天気予報を取得する."""
    forecast = _fetch_json(_FORECAST_URL.format(code=PREFECTURE_CODE))
    overview = _fetch_json(_OVERVIEW_URL.format(code=PREFECTURE_CODE))
    if not isinstance(forecast, list) or not forecast:
        raise JmaError("予報データの形式が想定と異なります。")
    if not isinstance(overview, dict):
        overview = {}
    return TsukubaWeather(forecast, overview)
