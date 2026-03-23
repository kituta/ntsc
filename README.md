# ntsc.py
https://github.com/zhuker/ntsc が素です。<br>
https://github.com/discus0434/ntsc を参考にGemini、claude.aiを使い自分好みに改変したものです。

https://note.com/ktt_mee/n/nc1b7fca4ddea

【使い方】<br>
ffmpegのPATH設定をする。<br>
ntsc.bat、ntsc.py、ntsc_filter.py、ringPattern.npyを同じフォルダに入れる。<br>
ntsc.batを編集で開き、py -3.14 ntsc_filter.py | ^ の ntsc_filter.py に ntsc_filter.py の絶対パスを指定する。<br>
動画ファイルをntsc.batにドラッグアンドドロップする。<br>
<br>
ntsc_filter.py でフィルターの詳細設定を行う。ログファイルのオンオフ、設定のランダム化も可。（ランダム・カモカ）<br>
ntsc.bat を編集で開き、サーチモードを 0 にするとファイル末尾につく乱数は消えます。<br>
<br>
動画裁断君.batは、ntsc.pyを並列処理するために動画を分割するbatです。<br>
動画裁断君.batに動画をドラッグアンドドロップすると、入力動画と同じ階層に作られた新しいフォルダ内に分割した動画を生成する。<br>
分割した動画をntsc.batに順番にドラッグ・アンド・ドロップし、ntsc.pyを複数同時に処理できる。<br>
結合は、ChatGPTに任せる。処理後の動画をすべて選択しパスのコピーを行い、ChatGPTに「これらのパスの動画を、ffmpegで結合するコマンドを作る。」と指示する。エンコード方法は好み。そして、結合した動画と裁断前の動画のパスを貼り「〈結合した動画のパス〉に、〈裁断前の動画のパス〉の音声を結合する。」と指示する。<br>
