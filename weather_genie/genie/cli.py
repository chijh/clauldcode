"""コマンドラインインターフェース（テキスト対話）."""

from __future__ import annotations

import argparse
import sys

from .assistant import Genie

_BANNER = r"""
==============================================
  Genie 🧞  つくば市 天気アシスタント
  データ: 気象庁 (JMA) 公式API
==============================================
話しかけてください（例: 今日の天気 / 明日 / 週間 / 気温 / 雨）
終了するには  quit / exit / bye  または Ctrl+C
"""

_QUIT_WORDS = {"quit", "exit", "bye", "終了", "さようなら", "おわり"}


def _run_interactive(genie: Genie) -> int:
    print(_BANNER)
    # 起動時に概況を表示（取得失敗しても対話は続行）
    print(genie.overview())
    print()
    while True:
        try:
            q = input("あなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGenie> またお越しください。さようなら！")
            return 0
        if q.lower() in _QUIT_WORDS or q in _QUIT_WORDS:
            print("Genie> またお越しください。さようなら！")
            return 0
        print("Genie> " + genie.answer(q).replace("\n", "\n       "))
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="genie",
        description="つくば市の天気を気象庁APIから取得して答えるテキストアシスタント。",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="質問を直接渡すと一度だけ回答して終了する（例: genie 明日の天気）。省略すると対話モード。",
    )
    args = parser.parse_args(argv)

    genie = Genie()

    if args.question:
        print(genie.answer(" ".join(args.question)))
        return 0

    return _run_interactive(genie)


if __name__ == "__main__":
    sys.exit(main())
