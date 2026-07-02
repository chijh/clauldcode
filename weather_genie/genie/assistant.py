"""Genie本体。ユーザーのテキスト質問から意図を読み取り、天気を答える."""

from __future__ import annotations

from datetime import date, timedelta

from .jma import DailyForecast, JmaError, TsukubaWeather, fetch_tsukuba_weather


class Genie:
    """つくば市の天気に答える対話アシスタント.

    予報データは初回アクセス時に取得し、以降はキャッシュを使う。
    再取得したい場合は refresh() を呼ぶ。
    """

    def __init__(self) -> None:
        self._weather: TsukubaWeather | None = None

    # ---- データ取得 --------------------------------------------------------
    def refresh(self) -> None:
        self._weather = fetch_tsukuba_weather()

    @property
    def weather(self) -> TsukubaWeather:
        if self._weather is None:
            self.refresh()
        assert self._weather is not None
        return self._weather

    # ---- 質問応答 ----------------------------------------------------------
    def answer(self, question: str) -> str:
        """質問文字列に対する回答テキストを返す."""
        q = question.strip()
        if not q:
            return "つくば市の天気について、何を知りたいですか？（例: 今日の天気 / 明日 / 週間 / 気温 / 雨）"

        try:
            weather = self.weather
        except JmaError as exc:
            return f"すみません、気象庁から天気を取得できませんでした。\n  → {exc}"

        # 週間予報
        if any(k in q for k in ("週間", "一週間", "週の", "これから", "今週")):
            return self._format_weekly(weather)

        # 対象日を判定
        target = self._resolve_day(q, weather)
        if target is None:
            return self._format_weekly(weather)

        # 観点（気温/降水）による絞り込み
        if any(k in q for k in ("気温", "温度", "何度", "暑", "寒")):
            return self._format_temp(target)
        if any(k in q for k in ("雨", "降水", "傘", "降る")):
            return self._format_pop(target)

        return self._format_day(target, header=True)

    # ---- 日付解決 ----------------------------------------------------------
    def _resolve_day(self, q: str, weather: TsukubaWeather) -> DailyForecast | None:
        today = date.today()
        wanted: date | None = None
        if "明後日" in q:
            wanted = today + timedelta(days=2)
        elif "明日" in q or "あした" in q or "あす" in q:
            wanted = today + timedelta(days=1)
        elif "今日" in q or "きょう" in q or "本日" in q:
            wanted = today

        if wanted is None:
            # 日付語が無ければ「今日」を既定にする
            wanted = today

        for day in weather.days:
            if day.date.date() == wanted:
                return day
        return None

    # ---- 整形 --------------------------------------------------------------
    def _format_day(self, day: DailyForecast, header: bool = False) -> str:
        lines: list[str] = []
        if header:
            lines.append(f"【つくば市 {day.label} の天気】")
        if day.weather:
            lines.append(f"天気: {day.weather}")
        temp = self._temp_line(day)
        if temp:
            lines.append(temp)
        if day.pops:
            pops = "  ".join(f"{span} {p}%" for span, p in day.pops)
            lines.append(f"降水確率: {pops}")
        if len(lines) <= (1 if header else 0):
            lines.append("この日の詳しい予報はまだ発表されていません。")
        return "\n".join(lines)

    def _format_temp(self, day: DailyForecast) -> str:
        temp = self._temp_line(day)
        if temp:
            return f"【つくば市 {day.label} の気温】\n{temp}"
        return f"{day.label} の気温情報はまだありません。"

    def _format_pop(self, day: DailyForecast) -> str:
        if day.pops:
            pops = "  ".join(f"{span} {p}%" for span, p in day.pops)
            advice = "傘があると安心です。" if self._max_pop(day) >= 50 else "傘は基本不要そうです。"
            return f"【つくば市 {day.label} の降水確率】\n{pops}\n{advice}"
        return f"{day.label} の降水確率情報はまだありません。"

    @staticmethod
    def _temp_line(day: DailyForecast) -> str | None:
        parts = []
        if day.temp_min is not None and day.temp_min != "":
            parts.append(f"最低 {day.temp_min}℃")
        if day.temp_max is not None and day.temp_max != "":
            parts.append(f"最高 {day.temp_max}℃")
        return "気温: " + " / ".join(parts) if parts else None

    @staticmethod
    def _max_pop(day: DailyForecast) -> int:
        vals = []
        for _, p in day.pops:
            try:
                vals.append(int(p))
            except (TypeError, ValueError):
                pass
        return max(vals) if vals else 0

    def _format_weekly(self, weather: TsukubaWeather) -> str:
        lines = ["【つくば市 週間予報】"]
        for day in weather.days:
            w = day.weather or "―"
            t = self._temp_line(day)
            t = t.replace("気温: ", "") if t else "―"
            pop = f"降水{self._max_pop(day)}%" if day.pops else ""
            lines.append(f"  {day.label}  {w}  {t}  {pop}".rstrip())
        return "\n".join(lines)

    # ---- 概況 --------------------------------------------------------------
    def overview(self) -> str:
        try:
            w = self.weather
        except JmaError as exc:
            return f"天気概況を取得できませんでした: {exc}"
        head = f"（{w.publishing_office} {w.report_datetime:%m月%d日 %H:%M} 発表）"
        return f"{head}\n{w.overview_text}" if w.overview_text else head
