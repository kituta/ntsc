# ntsc.py
https://github.com/zhuker/ntsc が素です。<br>
https://github.com/discus0434/ntsc を参考にGemini、claude.aiを使い自分好みに改変したものです。

https://note.com/ktt_mee/n/nc1b7fca4ddea

【使い方】<br>
ffmpegのPATH設定をする。<br>
ntsc.bat、ntsc.py、ntsc_filter.py、ringPattern.npyを同じフォルダに入れる。<br>
動画ファイルをntsc.batにドラッグアンドドロップする。<br>
<br>
ntsc_filter.py でフィルターの詳細設定を行う。ログファイルのオンオフ、設定のランダム化も可。（ランダム・カモカ）<br>
ntsc.bat を編集で開き、サーチモードを 0 にするとファイル末尾につく乱数は消えます。<br>
<br>
動画裁断君.batは、ntsc.pyを並列処理するために動画を分割するbatです。<br>
動画裁断君.batに動画をドラッグアンドドロップすると、入力動画と同じ階層に作られた新しいフォルダ内に分割した動画を生成する。<br>
分割した動画をntsc.batに順番にドラッグ・アンド・ドロップし、ntsc.pyを複数同時に処理できる。<br>
<br>
結合は、加工後の複数の動画ファイルを複数選択し、concat_videos.py（もしくはconcat_videos.bat）にドラッグアンドドロップする。
