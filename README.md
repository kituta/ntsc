# ntsc.py
https://github.com/zhuker/ntsc が素です。
https://github.com/discus0434/ntsc を参考にGemini、claude.aiを使い自分好みに改変したものです。

https://note.com/ktt_mee/n/nc1b7fca4ddea

ffmpegのPATH設定をする。

ntsc.bat、ntsc.py、ntsc_filter.py、ringPattern.npyを同じフォルダに入れる。
ntsc.batを編集で開き、py -3.14 ntsc_filter.py | ^ の ntsc_filter.py に ntsc_filter.py の絶対パスを指定する。
動画ファイルをntsc.batにドラッグアンドドロップする。

ntsc_filter.py で設定を行う。ログファイルのオンオフ、設定のランダム化も可。（ランダム・カモカ）
ntsc.bat を編集で開き、サーチモードを 0 にするとファイル末尾につく乱数は消えます。
