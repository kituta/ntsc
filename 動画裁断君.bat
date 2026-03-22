@echo off
setlocal enabledelayedexpansion

set "INPUT=%~1"

if "%INPUT%"=="" (
    echo い、いきなり入ってこないでよ！
    echo.
    echo なに？動画の裁断？
    echo それはここじゃなくて、batファイルに動画をドラッグ＆ドロップするの！
    echo.
    pause
    exit /b
)

:: "裁断する秒数を指定する。"
:: "最後の切れ端に極めて短い動画part（3秒未満）が生成されないようにしたほうが良いと思います。"
:: "極めて短い動画partが生成された場合の、実際の挙動は確認していません。"
set DURATION=60

:: "動画時間秒数 / CPUコア数 + 1（最後のpartを短くして切れ端対策）（小数点以下切り上げ）くらいの秒数が使いやすい"

for %%a in ("%INPUT%") do set "FNAME=%%~na"
for %%a in ("%INPUT%") do set "EXT=%%~xa"

for %%a in ("%INPUT%") do set "DIR=%%~dpa"
set "OUTDIR=%DIR%%FNAME%_parts"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

for /f "tokens=1 delims=." %%a in ('ffmpeg -i "%INPUT%" 2^>^&1 ^| findstr "Duration"') do (
    set "LINE=%%a"
)
for /f "tokens=2,3,4 delims=:.," %%a in ("!LINE!") do (
    set /a HOURS=%%a
    set /a MINUTES=%%b
    set /a SECONDS=%%c
)
set /a TOTALSECONDS=HOURS*3600+MINUTES*60+SECONDS

set /a START=0
set /a INDEX=1

:LOOP
if !START! GEQ %TOTALSECONDS% goto END

:: "ffmpeg出力。"
:: "正確性を重視するためCPUエンコード推奨。"
:: "-crf 18で視覚的ロスレスですが、気になるなら15程度まで下げても良いと思います。"
ffmpeg -i "%INPUT%" -ss !START! -t %DURATION% -c:v libx264 -crf 18 -preset slower -an "%OUTDIR%\%FNAME%_part!INDEX!%EXT%"

set /a START+=DURATION
set /a INDEX+=1
goto LOOP

:END
echo.
echo べ、べつにあんたのために裁断してやったんじゃないんだからね！
echo ほら、出力フォルダはそこよ。とっとと持っていきなさい。: %OUTDIR%
echo ・・・。
echo.
echo ・・・また、来なさいよね？
echo.
:: "最終更新日 2026-03-19"
pause
