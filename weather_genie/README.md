# Genie 🧞 — つくば市 天気アシスタント

テキストで話しかけると、**つくば市（茨城県南部）の天気**を答えてくれるPython製の対話アシスタントです。
天気データは **気象庁（JMA）の公式API** から取得します（**APIキー不要・完全無料**）。
外部ライブラリも不要で、**Pythonの標準ライブラリだけ**で動きます。

## 必要環境

- Python 3.10 以上（`str | None` などの型表記を使用）

> このPCにはまだPythonがインストールされていないようです。
> [python.org](https://www.python.org/downloads/) から入れるか、`winget install Python.Python.3.12` でインストールできます。
> （Microsoft Store版のスタブだけだと動きません）

## 使い方

プロジェクトのルート（この README がある `weather_genie/`）で実行します。

### 対話モード

```bash
python main.py
```

```
あなた> 今日の天気
Genie> 【つくば市 7月2日(水) の天気】
       天気: くもり 時々 晴れ
       気温: 最低 24℃ / 最高 31℃
       降水確率: 00-06時 10%  06-12時 20%  12-18時 30%  18-24時 20%

あなた> 明日 雨降る？
あなた> 週間
あなた> quit
```

### ワンショット（1回だけ答えて終了）

```bash
python main.py 明日の天気
python main.py 週間予報
python main.py 今日の気温
```

## 答えられる質問の例

| 入力例 | 返す内容 |
| --- | --- |
| `今日の天気` / `本日` | 今日の天気・気温・降水確率 |
| `明日` / `あした` | 明日の予報 |
| `明後日` | 明後日の予報 |
| `週間` / `一週間` / `今週` | 向こう約1週間の予報一覧 |
| `気温` / `何度` / `暑い？` | 対象日の最低・最高気温 |
| `雨` / `傘いる？` / `降水` | 対象日の降水確率とひとことアドバイス |

日付語（今日/明日/明後日）を省略した場合は「今日」として扱います。

## 構成

```
weather_genie/
├── main.py              エントリポイント
├── README.md
└── genie/
    ├── __init__.py
    ├── jma.py           気象庁APIクライアント（取得・解析）
    ├── assistant.py     Genie本体（質問の意図解釈と回答生成）
    └── cli.py           コマンドライン対話UI
```

## 利用API

- 予報: `https://www.jma.go.jp/bosai/forecast/data/forecast/080000.json`
- 概況: `https://www.jma.go.jp/bosai/forecast/data/overview_forecast/080000.json`

`080000` は茨城県、つくば市は細分区 `080020`（茨城県南部）に属します。
出典: 気象庁ホームページ（<https://www.jma.go.jp/>）
