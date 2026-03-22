@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
set "SEARCH_MODE=1"
REM ランダム値探求モード。1がオン、0がオフ。
REM 出力動画ファイルの末尾に乱数値を付加する。
REM ntsc_filter.py のログファイル生成とランダムモードと併用して、
REM 好みのランダム値が出るまで短い動画ファイルで試す機能。

set "INPUT_VIDEO=%~1"
if "%SEARCH_MODE%"=="1" (
    set "OUTPUT_VIDEO=%~dpn1_ntsc_%RANDOM%.mp4"
) else (
    set "OUTPUT_VIDEO=%~dpn1_ntsc.mp4"
)

REM --- 解像度を個別に取得（WIDTH と HEIGHT を別々に ffprobe で取る）---
REM csv 形式で1行に "幅,高さ" が返るため tokens で分けて取得する
for /f "tokens=1,2 delims=," %%a in ('ffprobe -v error -select_streams v:0 -show_entries stream^=width^,height -of csv^=p^=0 "%INPUT_VIDEO%" 2^>nul') do (
    set "WIDTH=%%a"
    set "HEIGHT=%%b"
)

REM --- フレームレート取得 ---
for /f "delims=" %%f in ('ffprobe -v error -select_streams v:0 -show_entries stream^=r_frame_rate -of default^=nokey^=1:noprint_wrappers^=1 "%INPUT_VIDEO%" 2^>nul') do (
    set "FPS=%%f"
)

REM --- 取得結果の確認（デバッグ用。動作確認後は削除してよい）---
REM echo WIDTH=%WIDTH% HEIGHT=%HEIGHT% FPS=%FPS%

REM --- setlocal 配下では set した変数は子プロセスに自動継承される ---
REM --- そのため ntsc_filter.py は os.environ.get("WIDTH") で正しく読み取れる ---

ffmpeg -i "%INPUT_VIDEO%" -vf "setpts=PTS-STARTPTS" -f rawvideo -pix_fmt bgr24 - | ^
py -3.14 ntsc_filter.py | ^
ffmpeg -f rawvideo -pix_fmt bgr24 -s %WIDTH%x%HEIGHT% -r %FPS% -i - ^
-c:v libx264 -crf 15 -preset slower -pix_fmt yuv420p -fps_mode passthrough "%OUTPUT_VIDEO%"

echo 完了
pause