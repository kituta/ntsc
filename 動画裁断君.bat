@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: ツンデレ動画分割バッチ
:: 最終更新日 2026-03-23
:: ============================================================

:: ============================================================
:: ★ ffmpeg エンコード設定（ここを編集して挙動をカスタマイズ）★
:: ============================================================

:: --- 分割数の設定 ---
:: ここに数値を入れると物理コア数より優先されます。
:: 空欄（=""）にすると物理コア数を自動取得して分割数に使用します。
set "USER_PART_COUNT="

:: --- 映像品質 ---
:: -crf 値が低いほど高品質・大容量。
::   15: ほぼ完全ロスレス相当（推奨）
::   18: 視覚的ロスレス相当
::   23: ffmpeg デフォルト
set "CFG_CRF=15"

:: --- エンコード速度 ---
:: ultrafast / superfast / veryfast / faster / fast / medium / slow / slower / veryslow
:: slower: 圧縮効率重視（推奨）。フレーム精度には影響しない。
set "CFG_PRESET=slower"

:: ============================================================
:: ffmpeg 設定メモ（技術的な詳細）：
::
:: [シーク精度について]
::   -ss / -t は入力ファイル -i の後に配置（出力側シーク）。
::   入力前に置くと GOP 単位でのシークになり、フレーム単位の正確性が失われる。
::   出力側に置くことで、デコードしてから正確な秒数でカットされる。
::
:: [GOP 構造について]
::   -g GOP_SIZE でキーフレーム間隔を固定し、GOP 構造によるズレを防ぐ。
::   -keyint_min GOP_SIZE でキーフレームの最小間隔も統一。
::   -sc_threshold 0 でシーンチェンジ検出によるキーフレーム挿入を無効化。
::   → これにより分割点が必ず意図したフレームになる。
::
:: [FPS・GOP の計算について]
::   整数 fps（30fps / 60fps 等）を ffprobe で取得する。
::   GOP_SIZE = fps * 2（= 2 秒分のキーフレーム間隔）。
::
:: [音声について]
::   -an で音声を除去（ntsc.py フィルタ処理は映像のみを対象とするため）。
::
:: [ログについて]
::   -hide_banner -loglevel error で ffmpeg の冗長出力を抑制。
:: ============================================================

:: ============================================================
:: ↓↓↓ ここから下は通常編集不要 ↓↓↓
:: ============================================================

:: --- 入力チェック ---
set "INPUT=%~1"
if "%INPUT%"=="" (
    echo い、いきなり入ってこないでよ！
    echo.
    echo ……。
    echo.
    echo ま、まぁ、せっかく来たんだから寄こしなさいよ。
    echo ほら、動画ファイル！
    set /p "INPUT=（ここにファイルをドロップしてEnterしなさいよね！）: "

    :: 前後のダブルクォーテーションを除去（ドラッグ&ドロップ時に付く場合があるため）
    if defined INPUT set "INPUT=!INPUT:"=!"
)

:: 再度チェック（空打ちして進もうとした場合）
if "%INPUT%"=="" (
    echo ちょっと！何も入れないでEnterなんて、ふざけてるの！？
    echo もう知らない！勝手にしなさい！
    pause
    exit /b 1
)

:: --- 拡張子チェック（画像ファイル排除） ---
for %%a in ("%INPUT%") do set "CHEXT=%%~xa"
set "IS_IMAGE=0"
for %%e in (.jpg .jpeg .png .gif .bmp .webp .tiff) do (
    if /i "!CHEXT!"=="%%e" set "IS_IMAGE=1"
)

if "!IS_IMAGE!"=="1" (
    echo.
    echo.
    echo なによそれ、画像ファイルじゃない！
    echo まさか……あたしに、変なもの見せようとしてんじゃないでしょうね！？
    echo このバカ！　変態！　最低！
    echo.
    echo 動画以外はお断りよ！　出直してきなさい！
    echo.
    echo.
    pause
    exit /b 1
)

if not exist "%INPUT%" (
    echo ちょっと！そのファイル、存在しないじゃない！
    echo ちゃんと確認してからドロップしなさいよね！
    echo.
    pause
    exit /b 1
)

:: --- CPU名の取得 ---
set "CPU_NAME=不明なCPU"
for /f "skip=1 tokens=* delims=" %%c in ('wmic cpu get name 2^>nul') do (
    if not "%%c"=="" if "!CPU_NAME!"=="不明なCPU" set "CPU_NAME=%%c"
)
:: 末尾スペースを除去
for /f "tokens=* delims= " %%c in ("!CPU_NAME!") do set "CPU_NAME=%%c"

:: --- 物理コア数の取得（HT/論理スレッドを除外して「実力」を数える） ---
set "PHYS_CORES=0"
for /f "tokens=2 delims==" %%n in ('wmic cpu get NumberOfCores /value 2^>nul') do (
    set /a PHYS_CORES=%%n
)
if !PHYS_CORES! LEQ 0 (
    echo ……なんか物理コア数の取得に失敗したわ。しょうがないから4で進めるわよ。
    set /a PHYS_CORES=4
)

:: --- 分割数の決定 ---
if defined USER_PART_COUNT (
    if not "%USER_PART_COUNT%"=="" (
        set /a PART_COUNT=%USER_PART_COUNT%
        echo あんたが %USER_PART_COUNT% 分割って言うならそうしてあげるわよ。べ、別にいいけど。
    ) else (
        set /a PART_COUNT=!PHYS_CORES!
    )
) else (
    set /a PART_COUNT=!PHYS_CORES!
)

if !PART_COUNT! LEQ 0 set /a PART_COUNT=1

echo.
echo ……っ、起動したわよ。べ、別に待ってたわけじゃないんだから。
echo 物理コア数: !PHYS_CORES! コア（CPU: !CPU_NAME!）
echo 分割数: !PART_COUNT! パートで処理するわよ。文句ないわよね？
echo.

:: --- パス情報の取得 ---
for %%a in ("%INPUT%") do set "FNAME=%%~na"
for %%a in ("%INPUT%") do set "EXT=%%~xa"
for %%a in ("%INPUT%") do set "DIR=%%~dpa"
set "OUTDIR=%DIR%%FNAME%_parts"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

:: --- 上書き確認（出力フォルダ内に既存ファイルがある場合） ---
:: 最初の1回だけ確認し、yes なら以降は -y で全パート自動上書き
set "FFMPEG_OVERWRITE=-n"
dir /b "%OUTDIR%\%FNAME%_part*%EXT%" >nul 2>&1
if !errorlevel!==0 (
    echo.
    echo ちょっと待って。出力フォルダに、もう裁断済みのファイルがあるわよ。
    echo y を入力したら全パートまとめて上書きするからね。覚悟しなさいよ。
    echo.
    set /p "OW_CONFIRM=全パート上書きする場合は y を入力しなさい（それ以外でスキップ）: "
    if /i "!OW_CONFIRM!"=="y" (
        echo ……わかった。全部上書きしてあげるわよ。後悔しないでよね。
        set "FFMPEG_OVERWRITE=-y"
    ) else (
        echo ……そう。じゃあ既存ファイルはそのままにしておくわ。
        set "FFMPEG_OVERWRITE=-n"
    )
    echo.
)

:: --- 動画の総秒数を取得 ---
:: ffprobeが使える場合はffprobeを優先（より正確）
set "TOTALSECONDS=0"
where ffprobe >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%d in ('ffprobe -v error -show_entries format^=duration -of default^=noprint_wrappers^=1:nokey^=1 "%INPUT%" 2^>nul') do (
        :: 小数点以下切り捨て（整数部分のみ取得）
        for /f "tokens=1 delims=." %%i in ("%%d") do set /a TOTALSECONDS=%%i
    )
) else (
    :: ffprobe がない場合は ffmpeg の Duration 表示を解析
    for /f "tokens=1 delims=." %%a in ('ffmpeg -hide_banner -i "%INPUT%" 2^>^&1 ^| findstr "Duration"') do (
        set "LINE=%%a"
    )
    for /f "tokens=2,3,4 delims=:.," %%a in ("!LINE!") do (
        set /a HOURS=%%a
        set /a MINUTES=%%b
        set /a SECONDS=%%c
    )
    set /a TOTALSECONDS=HOURS*3600+MINUTES*60+SECONDS
)

if !TOTALSECONDS! LEQ 0 (
    echo ちょっと！動画の長さが取得できなかったわよ！
    echo そのファイル、本当に正常な動画なの？確認しなさいよね！
    pause
    exit /b 1
)

:: --- 動画の長さに応じたコメント ---
set /a DUR_MIN=TOTALSECONDS/60
echo 動画の長さ: !TOTALSECONDS! 秒。

if !TOTALSECONDS! LSS 60 (
    echo ……え、!TOTALSECONDS!秒？　短っ。
    echo あんたの動画ってこんなんなんだ（笑）。
    echo ……まあ、短くてもちゃんとやってあげるんだから。べ、別にもっと長くてもよかったけど？
) else if !DUR_MIN! LSS 5 (
    echo !DUR_MIN!分ね。まあ……ちょうどいいんじゃない。
    echo こっちも、その……準備してたわけじゃないし。ちょうどよかったわ。
) else if !DUR_MIN! LSS 10 (
    echo !DUR_MIN!分か。まあまあね。
    echo ……ちゃんとやってあげるから、変なこと考えないでよね。
) else if !DUR_MIN! LSS 20 (
    echo !DUR_MIN!分もあるじゃない。しょうがないわね。
    echo ……その、長い方が、一緒にいる時間が増えるわけで。べ、別にうれしくないけど。
) else if !DUR_MIN! LSS 30 (
    echo !DUR_MIN!分……ふうん。結構あるじゃない。
    echo ま、今日は時間あるし。付き合ってあげるわよ。……勘違いしないでよね。
) else if !DUR_MIN! LSS 60 (
    echo !DUR_MIN!分！？　それなりに長いわね……。
    echo ……まあ、その分だけここにいてくれるってことだから。べ、別にそれが目的じゃないけど！
) else if !DUR_MIN! LSS 180 (
    echo ……!DUR_MIN!分。1時間以上じゃない。まったく、呆れるわ。
    echo あんたって、いつもそういう無茶苦茶なの持ってくるわよね。
    echo ……しょうがないから付き合ってあげる。
) else if !DUR_MIN! LSS 360 (
    echo !DUR_MIN!分……3時間超え？　何それ、映画でもそんなのほぼないわよ。
    echo ……これ、本当に動画なの？何の動画か聞いてもいい？
    echo い、いや、別に気になってないけど！
) else if !DUR_MIN! LSS 720 (
    echo ……!DUR_MIN!分。6時間超えてるじゃない。ちょ、ちょっと待って。
    echo これ、本当に処理できるの？あたし、今ちょっとびっくりしてるんだけど……。
    echo ……ま、まあ、やってあげるけど。驚いてなんかないんだから！
) else (
    echo …………!DUR_MIN!分。
    echo 12時間以上って、何事なの。何事なのよ。
    echo ……もう、なんでもいいわ。やってあげる。やってあげればいいんでしょ。どうにでもなれ。
)
echo.

:: --- DURATION の計算 ---
:: (総秒数 + X - 1) / X + 1 の整数演算（切り上げ相当＋1で切れ端防止）
:: これにより最終パートが極端に短くなる（1フレームのみ等）のを防ぐ
set /a DURATION=(TOTALSECONDS + PART_COUNT - 1) / PART_COUNT + 1

:: --- 1パートあたりの長さに応じたコメント ---
set /a DUR_PART_MIN=DURATION/60

if !DURATION! LSS 5 (
    echo 1パートあたり: !DURATION! 秒。
    echo ……細かすぎ。こんな裁断、あたしじゃなきゃできないわよ。べ、別に自慢してるわけじゃないけど。
) else if !DURATION! LSS 10 (
    echo 1パートあたり: !DURATION! 秒。
    echo ……!DURATION!秒か。細かいわね。手際よく切ってあげるから、見ててよね。
) else if !DURATION! LSS 20 (
    echo 1パートあたり: !DURATION! 秒。
    echo まあ、このくらいが一番やりやすいわよ。……こういう時のためにあたしがいるんだから。
) else if !DURATION! LSS 30 (
    echo 1パートあたり: !DURATION! 秒。
    echo ……!DURATION!秒ね。悪くない長さじゃない。
    echo こっちもちょうど準備できてたし。……偶然よ、偶然。
) else if !DURATION! LSS 60 (
    echo 1パートあたり: !DURATION! 秒。
    echo !DURATION!秒か……そんなに長くないじゃない。サクッとやってあげるわよ。
    echo ……終わっても、まだいてもいいんだからね。
) else if !DUR_PART_MIN! LSS 5 (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo コア数と動画によっては、パートも長くなるわよね。当然じゃない。
    echo ……あたしは全然平気よ。長くても付き合ってあげる。
) else if !DUR_PART_MIN! LSS 10 (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo 結構長いわね。それだけ長い動画だったってことよ。
    echo ……まあ、その分だけ時間かかるけど。一緒にいてくれるんでしょ。
) else if !DUR_PART_MIN! LSS 20 (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo ……なかなかの長さね。でも、あたしはちゃんとやってあげるわよ。
    echo たまにしか来ないんだから、せめてこれくらいはね。
) else if !DUR_PART_MIN! LSS 30 (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo ……!DUR_PART_MIN!分もあるじゃない。全部で映画1本分？
    echo ……ま、終わるまで、ここにいてよね。
) else if !DUR_PART_MIN! LSS 60 (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo ……!DUR_PART_MIN!分。1パートがこんなに長いって、どんな動画なの。
    echo まあいいわ。どうせ付き合うって決めたんだから。……覚悟はできてるわよ。
) else (
    echo 1パートあたり: !DUR_PART_MIN! 分（!DURATION! 秒）。
    echo ……1パートが1時間以上ってどういうこと。
    echo もう何も言わない。やってあげる。ずっとここにいてあげるから。
)
echo.

:: --- フレームレートの取得（GOP設定に使用） ---
:: 整数 fps（30fps / 60fps 等）を ffprobe で取得する。
:: 取得できない・0 以下の場合は 30fps をデフォルトとする。
set "FPS=30"
where ffprobe >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=1 delims=/" %%f in ('ffprobe -v error -select_streams v:0 -show_entries stream^=r_frame_rate -of default^=noprint_wrappers^=1:nokey^=1 "%INPUT%" 2^>nul') do (
        set /a FPS=%%f
    )
)
if !FPS! LEQ 0 set /a FPS=30

:: GOP サイズ：fps * 2（= 2 秒分のキーフレーム間隔）
set /a GOP_SIZE=FPS*2

:: ============================================================
:: ツンデレ台詞テーブル
:: 現在時刻の秒数（00-59）を10で割った商（0-5）でグループ分け
:: これにより擬似ランダムなコメント選択を実現
:: ============================================================

:: 処理開始時の台詞（6パターン）
set "MSG_START_0=……っ、べ、別に急いでるわけじゃないけど、やってあげるわよ。"
set "MSG_START_1=ふん、これくらいあたしには朝飯前よ。見てなさいよね。"
set "MSG_START_2=……しょうがないわね。手ェ抜かないでやってあげるんだから、感謝しなさいよ。"
set "MSG_START_3=……っ、別にあんたのためじゃないけど、ちゃんとやってあげるわよ。"
set "MSG_START_4=黙って見てなさいよ。こういうの、あたしに任せとけばいいの。"
set "MSG_START_5=……ま、まあ、やってあげなくもないわよ。べ、別に嫌じゃないし。"

:: 処理完了時の台詞（6パターン）
set "MSG_DONE_0=……まあ、悪くないわね。"
set "MSG_DONE_1=ふん、当然よ。あたしがやったんだから。"
set "MSG_DONE_2=……できたわよ。ちゃんと確認しなさいよね。"
set "MSG_DONE_3=……これでいいんでしょ。文句言わないでよね。"
set "MSG_DONE_4=はい、完了。……ほら、ありがとうくらい言いなさいよ。"
set "MSG_DONE_5=……っ、別に急いでたわけじゃないけど。ちゃんとできたわよ。"

:: --- 分割処理ループ ---
set /a START=0
set /a INDEX=1

:LOOP
if !START! GEQ !TOTALSECONDS! goto END

:: 現在時刻の秒数を取得（HH:MM:SS.mm 形式の3番目フィールド）
for /f "tokens=3 delims=:." %%s in ("%TIME%") do set /a "CUR_SEC=%%s" 2>nul
if not defined CUR_SEC set /a CUR_SEC=0
set /a "MSG_IDX=CUR_SEC/10"
if !MSG_IDX! GTR 5 set /a MSG_IDX=5

echo [パート !INDEX! / !PART_COUNT! を処理中] !MSG_START_%MSG_IDX%!

ffmpeg !FFMPEG_OVERWRITE! -hide_banner -loglevel error ^
    -i "%INPUT%" ^
    -ss !START! -t !DURATION! ^
    -c:v libx264 ^
    -crf %CFG_CRF% ^
    -preset %CFG_PRESET% ^
    -g !GOP_SIZE! ^
    -keyint_min !GOP_SIZE! ^
    -sc_threshold 0 ^
    -an ^
    "%OUTDIR%\%FNAME%_part!INDEX!%EXT%"

if !errorlevel! neq 0 (
    echo.
    echo ちょ、ちょっと！パート !INDEX! でffmpegがうるさく吠えてるわよ！
    echo あんた、早く入力ファイル確認して黙らせてきなさいよ！
    echo.
    pause
    exit /b 1
)

:: 完了時の台詞（秒数で選択）
for /f "tokens=3 delims=:." %%s in ("%TIME%") do set /a "DONE_SEC=%%s" 2>nul
if not defined DONE_SEC set /a DONE_SEC=0
set /a "DONE_IDX=DONE_SEC/10"
if !DONE_IDX! GTR 5 set /a DONE_IDX=5

:: --- 最終パートのみ：秒数がゾロ目（00,11,22,33,44,55）なら超デレ台詞 ---
if !INDEX!==!PART_COUNT! (
    set "IS_ZOROI=0"
    if !DONE_SEC!==0  set "IS_ZOROI=1"
    if !DONE_SEC!==11 set "IS_ZOROI=1"
    if !DONE_SEC!==22 set "IS_ZOROI=1"
    if !DONE_SEC!==33 set "IS_ZOROI=1"
    if !DONE_SEC!==44 set "IS_ZOROI=1"
    if !DONE_SEC!==55 set "IS_ZOROI=1"

    if !IS_ZOROI!==1 (
        echo   → パート !INDEX! 完了。
        echo.
        echo   ……ねえ。
        echo   終わったわよ。全部。
        echo   ……あんたって、たまにしか来ないじゃない。
        echo   だから、その、裁断とかそういうのがなくても……来てもいいんだからね。
        echo   別に、来なくていいけど。来たら……来たら、まあ、相手くらいしてあげるから。
        echo   ……忘れないでよね。
        goto AFTER_DONE_MSG
    )
)

echo   → パート !INDEX! 完了。!MSG_DONE_%DONE_IDX%!

:AFTER_DONE_MSG
echo.

set /a START+=DURATION
set /a INDEX+=1
goto LOOP

:END
set /a DONE_COUNT=INDEX-1
echo.
echo べ、べつにあんたのために裁断してやったんじゃないんだからね！
echo !DONE_COUNT! パートに分けてあげたわよ。ちゃんと感謝しなさいよね。
echo ほら、出力フォルダはそこよ。とっとと持っていきなさい。: %OUTDIR%
echo.
echo ……ふん、!CPU_NAME! にしては上出来じゃない。
echo 次はもっといいCPU、買ってもらいなさいよね。……待ってるんだから。
echo.
pause
exit /b 0