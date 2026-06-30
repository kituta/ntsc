#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concat_videos.py
複数の動画ファイルをFFmpegのconcat demuxerで単純連結するスクリプト。
再エンコードなし（-c copy）で連結する。

使い方:
  複数の動画ファイルをこのスクリプトへドラッグアンドドロップして起動する。
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
CONCAT_SUFFIX = "_concat"   # 出力ファイル名に付加する識別子


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def print_separator(char: str = "─", width: int = 50) -> None:
    """区切り線を表示する。"""
    print(char * width)


def abort(message: str) -> None:
    """エラーメッセージを表示して終了する。"""
    print(f"\n[エラー] {message}")
    wait_and_exit(1)


def wait_and_exit(code: int = 0) -> None:
    """終了前にキー入力を待つ（コンソールが即閉じないようにする）。"""
    print("\n続けるには Enter キーを押してください...")
    input()
    sys.exit(code)


def check_ffmpeg() -> str:
    """
    ffmpegの実行ファイルがPATH上にあるか確認する。
    見つからなければ abort() で終了。
    見つかればコマンド名を返す。
    """
    cmd = "ffmpeg"
    if shutil.which(cmd) is None:
        abort("FFmpegがPATH上に見つかりません。FFmpegをインストールし、PATHを通してください。")
    return cmd


# ──────────────────────────────────────────────
# 並び替え
# ──────────────────────────────────────────────

SORT_MENU = {
    "1": ("ドラッグした順（デフォルト）", None),
    "2": ("ファイル名 昇順",             lambda p: p.name.lower()),
    "3": ("ファイル名 降順",             lambda p: p.name.lower()),
    "4": ("作成日時 昇順",               lambda p: p.stat().st_ctime),
    "5": ("作成日時 降順",               lambda p: p.stat().st_ctime),
    "6": ("更新日時 昇順",               lambda p: p.stat().st_mtime),
    "7": ("更新日時 降順",               lambda p: p.stat().st_mtime),
}

SORT_REVERSE = {"3", "5", "7"}   # 降順になる選択肢


def print_file_list(files: list[Path]) -> None:
    """連結順のファイル一覧を表示する。"""
    print_separator()
    print("連結順:")
    for i, f in enumerate(files, 1):
        print(f"  {i:2}. {f.name}")
    print_separator()


def choose_sort_order(original: list[Path]) -> list[Path]:
    """
    並び替えメニューを表示し、ユーザーが選んだ順序でソートしたリストを返す。
    初回は original のまま返す（メニューなしで確認画面へ）。
    """
    files = list(original)  # コピーして操作

    while True:
        print_file_list(files)

        # 確認
        answer = input("この順番で連結しますか？ (Y/N) > ").strip().upper()
        if answer == "Y":
            return files

        # 並び替えメニュー
        print("\n並び替え方法を選択してください:")
        for key, (label, _) in SORT_MENU.items():
            print(f"  {key}. {label}")

        choice = input("番号を入力してください > ").strip()
        if choice not in SORT_MENU:
            print("無効な入力です。もう一度選んでください。\n")
            continue

        label, key_func = SORT_MENU[choice]
        if key_func is None:
            # ドラッグした順（オリジナルに戻す）
            files = list(original)
        else:
            reverse = choice in SORT_REVERSE
            files = sorted(original, key=key_func, reverse=reverse)

        print(f"\n→ 並び替え: {label}\n")


# ──────────────────────────────────────────────
# 出力ファイル名生成
# ──────────────────────────────────────────────

def make_output_path(first_file: Path) -> Path:
    """
    出力ファイルのパスを生成する。
    同名ファイルが存在する場合は (2), (3) ... と連番を付ける。
    """
    stem = first_file.stem + CONCAT_SUFFIX
    suffix = first_file.suffix
    output_dir = first_file.parent

    candidate = output_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    # 連番付与
    n = 2
    while True:
        candidate = output_dir / f"{stem}({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


# ──────────────────────────────────────────────
# FFmpeg連結
# ──────────────────────────────────────────────

def build_concat_list(files: list[Path], list_path: Path) -> None:
    """
    FFmpeg concat demuxer 用のファイルリスト（list.txt）を生成する。
    パス内のシングルクォートをエスケープする。
    """
    with open(list_path, "w", encoding="utf-8") as f:
        for file in files:
            # Windowsのバックスラッシュをスラッシュに統一し、
            # シングルクォートをエスケープする
            safe_path = str(file.resolve()).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")


def run_ffmpeg(ffmpeg_cmd: str, list_path: Path, output_path: Path) -> None:
    """
    FFmpegを実行して動画を連結する。
    エラー終了した場合は abort() で終了。
    """
    cmd = [
        ffmpeg_cmd,
        "-f", "concat",       # concat demuxer を使用
        "-safe", "0",         # 絶対パスを許可
        "-i", str(list_path), # 入力リスト
        "-c", "copy",         # 再エンコードなし（ストリームコピー）
        str(output_path),
    ]

    print("\nFFmpegを実行中...")
    print_separator()

    result = subprocess.run(cmd)

    print_separator()

    if result.returncode != 0:
        # 出力途中のファイルが残っている場合は削除する
        if output_path.exists():
            output_path.unlink()
        abort(f"FFmpegがエラーコード {result.returncode} で終了しました。")


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def main() -> None:
    # ── 1. 引数チェック ──────────────────────────
    args = sys.argv[1:]  # スクリプト名を除いた引数

    if len(args) == 0:
        abort("動画ファイルをこのスクリプトへドラッグアンドドロップして起動してください。")

    if len(args) == 1:
        abort("連結には2個以上のファイルが必要です。ファイルが1個しか渡されませんでした。")

    # ── 2. パス検証 ──────────────────────────────
    files: list[Path] = []
    for arg in args:
        p = Path(arg)
        if not p.exists():
            abort(f"ファイルが見つかりません: {arg}")
        if not p.is_file():
            abort(f"ファイルではありません: {arg}")
        files.append(p)

    # ── 3. FFmpeg確認 ─────────────────────────────
    ffmpeg_cmd = check_ffmpeg()

    # ── 4. 並び替えと確認 ────────────────────────
    print(f"\n{len(files)} 個のファイルが渡されました。\n")
    sorted_files = choose_sort_order(files)

    # ── 5. 出力パス決定 ──────────────────────────
    output_path = make_output_path(sorted_files[0])
    print(f"\n出力ファイル: {output_path}")

    # ── 6. 一時ファイル（list.txt）作成 ──────────
    # 入力ファイルと同じディレクトリに一時ファイルを作る
    # （-safe 0 不要にもできるが、絶対パス方式を採用）
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".txt", prefix="ffmpeg_concat_")
    os.close(tmp_fd)
    list_path = Path(tmp_path_str)

    try:
        build_concat_list(sorted_files, list_path)

        # ── 7. FFmpeg実行 ─────────────────────────
        run_ffmpeg(ffmpeg_cmd, list_path, output_path)

    finally:
        # ── 8. 一時ファイル削除 ───────────────────
        if list_path.exists():
            list_path.unlink()

    # ── 9. 完了メッセージ ─────────────────────────
    print(f"\n✓ 連結完了: {output_path.name}")
    print(f"  保存先: {output_path.parent}")

    wait_and_exit(0)


if __name__ == "__main__":
    main()
