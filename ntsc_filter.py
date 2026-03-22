import sys
import os
import numpy as np
import random
from datetime import datetime
from ntsc import Ntsc, VHSSpeed

# ===== ログファイルとランダム化切り替え =====
WRITE_LOG = True
# Trueが残す。Falseが残さない。(True*/False)
# ログ内容は、入力/出力動画のフルパス、実行日、ntsc.py、パラメータ設定

RANDOM_MODE = False
# True にするとパラメータ値をランダムで上書きする。(True/False*)
# ==========================================

# =========== パラメータ手動設定 ===========
#  【A】映像信号（NTSC）関連のフィルター
#  アナログ放送や通信ケーブルで発生するノイズ・信号劣化の再現
# ==========================================
# 参考：https://github.com/zhuker/ntsc?tab=readme-ov-file#readme
# 参考：https://www.avartifactatlas.com/tags.html#video

# --- 信号・基本設定 ---
COMPOSITE_PRE_CUT = 1000000.0 # プリエンファシス（高域強調）の開始閾値
COMPOSITE_PRE     = 0.0       # 信号の強調度(0.0*-8.0) 
                              # 値を上げると信号が強調され、アナログ的な質感が強まる。

# --- 色のにじみ (Color Bleed) ---
# Y/C分離エラーなどによる色のズレや滲みを再現する。
BLEED_BEFORE      = True      # 劣化処理の前に滲ませるか(True*/False)
COLOR_BLEED_H     = 0         # 横方向のにじみ(0*-10) 3-5で「にじみ」が目立つ。
COLOR_BLEED_V     = 0         # 縦方向のにじみ(0*-10)

# --- リンギング (Ringing) ---
# 輪郭の横に発生する不要な振動（二重影）を再現する。
RINGING           = 1.0       # 輪郭の影(1.0* = 無し, 0.3-0.99 = 有り)
ENABLE_RINGING2   = True      # 第2リンギングの有効化(True*/False)
RINGING_POWER     = 2         # リンギングの強度(整数)(2*)
RINGING_SHIFT     = 0         # リンギングのズレ量(0*)

# --- 周波数ノイズ (Frequency Noise) ---
# 信号の乱れによるチリチリとした細かいノイズ。
FREQ_NOISE_SIZE   = 0.0       # ノイズの大きさ(0.0*-1.0) 0で無効
FREQ_NOISE_AMPLI  = 2.0       # ノイズの振幅(0.0-5.0, 0.5-2.0*付近が最適)

# --- ビデオノイズ (Video Noise) ---
# 輝度(Luma)と色(Chroma)それぞれのザラザラ感を調整する。
VIDEO_NOISE       = 2         # 輝度ノイズ(0-2*-4200) 砂嵐のようなザラザラ感。
VIDEO_CHROMA_NOISE= 0         # 色ノイズ(0*-16384) 色がついている部分のノイズ。
VIDEO_CHROMA_PHASE= 0         # 色の位相ノイズ(0*-50) 色が変わってしまう変色ノイズ。
VIDEO_CHROMA_LOSS = 0         # 色信号の欠損(0*-100,000) 色が部分的に抜ける現象。

# --- 信号フィルタリングと規格 ---
IN_CHROMA_LP      = True      # エンコード前の色信号低域通過(True*/False)
OUT_CHROMA_LP     = True      # デコード後の色信号低域通過(True*/False)
OUT_CHROMA_LP_LITE= True      # 軽量版色信号低域通過(True*/False)
OUTPUT_NTSC       = True      # NTSCカラーサブキャリアを再現するか(True*/False)
SCANLINE_PHASE    = 180       # 走査線の位相シフト量(180*)
SCANLINE_OFFSET   = 0         # 位相シフトのオフセット(0*-4)
SUBCARRIER_AMP    = 50        # サブキャリア振幅(50*)
SUBCARRIER_AMP_B  = 50        # 戻し時の振幅(50*)

# ==========================================
#  【B】VHS（磁気テープ）関連のフィルター
#  ビデオデッキでの録画・再生時に発生する特有の劣化の再現
# ==========================================

# --- VHSエミュレーション切り替え ---
USE_VHS_MODE      = False     # VHSモードを有効にするか(True/False*)
                              # Trueにすると以下のVHSエミュレーション設定の項目が反映される。

# --- VHSエミュレーション設定 ---
TAPE_SPEED        = "SP"      # テープ速度(SP*/LP/EP) 速度が遅いほど画質が低下。
VHS_SVIDEO_OUT    = False     # S-Video出力にするか(True/False*)
VHS_CHROMA_V_BLEND= True      # 垂直方向の色信号合成(True*/False) 
                              # VHS特有の色のボケを再現する。
VHS_OUT_SHARPEN   = 1.5       # 輪郭の鋭さ(1.0-1.5*-5.0) 
                              # ビデオデッキのシャープネス調整のような効果。
WAVE_STRENGTH     = 0         # 画面の揺らぎ(0*-10) 
                              # テープの伸びや回転ムラによる左右のうねり。VHSの物理的劣化の程度。

# --- ヘッド切り替えノイズ (画面最下部の乱れ) (ランダム化の対象外) ---
# テープ再生時にヘッドが切り替わる瞬間に発生するノイズ。
USE_HEAD_SWITCH   = False     # ノイズを出すか(True/False*) ※高さ486px以上推奨
HEAD_SWITCH_POINT = 1.0 - (4.5 + 0.01) / 262.5 # " 1.0 - (4.5 + 0.01) / 262.5 "*
HEAD_SWITCH_PHASE = (1.0 - 0.01) / 262.5       # " (1.0 - 0.01) / 262.5 "*
HEAD_SWITCH_NOISE = 1.0 / 500 / 262.5          # " 1.0 / 500 / 262.5 "*

# --- その他・デバッグ用 (ランダム化の対象外) ---
PRECISE_MODE      = False     # Trueにするとノイズ再現を厳密にするが低速になる。(True/False*)
NOCOLOR_SUBCARRIER= False     # 色をデコードせず搬送波を直接見る。(True/False*)
# ==========================================
# 【プリセット用エリア】
# ログファイルの設定やプリセットを以下に貼り付けると、上の基本設定を上書きする。
#  ; でパラメータを区切る。A = 0 ; B = 1 。
# ------------------------------------------

# ------------------------------------------

# ==============ランダム化部分==============
# RANDOM_MODE = True の時だけ動作し、手動パラメータ値を上書きする。
# ランダム値の範囲は、ntsc.pyと同一。
# ==========================================
if RANDOM_MODE:
    rnd = random.Random() 
    COMPOSITE_PRE      = rnd.triangular(0, 8, 0)
    VHS_OUT_SHARPEN    = rnd.triangular(1, 5, 1.5)
    IN_CHROMA_LP       = rnd.random() < 0.8
    OUT_CHROMA_LP      = rnd.random() < 0.8
    OUT_CHROMA_LP_LITE = rnd.random() < 0.8
    VIDEO_CHROMA_NOISE = int(rnd.triangular(0, 16384, 2))
    VIDEO_CHROMA_PHASE = int(rnd.triangular(0, 50, 2))
    VIDEO_CHROMA_LOSS  = int(rnd.triangular(0, 50000, 10))
    VIDEO_NOISE        = int(rnd.triangular(0, 4200, 2))
    USE_VHS_MODE       = rnd.random() < 0.2
    WAVE_STRENGTH      = int(rnd.triangular(0, 5, 0))
    SCANLINE_PHASE     = rnd.choice([0, 90, 180, 270])
    SCANLINE_OFFSET    = rnd.randint(0, 3)
    TAPE_SPEED         = rnd.choice(["SP", "LP", "EP"])
    enable_ringing = rnd.random() < 0.8
    if enable_ringing:
        RINGING           = rnd.uniform(0.3, 0.7)
        enable_freq_noise = rnd.random() < 0.8
        if enable_freq_noise:
            FREQ_NOISE_SIZE  = rnd.uniform(0.5, 0.99)
            FREQ_NOISE_AMPLI = rnd.uniform(0.5, 2.0)
        else:
            FREQ_NOISE_SIZE  = 0.0
        ENABLE_RINGING2   = rnd.random() < 0.5
        RINGING_POWER     = rnd.randint(2, 7)
    else:
        RINGING           = 1.0
        FREQ_NOISE_SIZE   = 0.0
    BLEED_BEFORE  = (1 == rnd.randint(0, 1))
    COLOR_BLEED_H = int(rnd.triangular(0, 8, 0))
    COLOR_BLEED_V = int(rnd.triangular(0, 8, 0))
    
    # ---ランダム値上書き設定 ---
    # 固定したいパラメータがある場合、ランダム化した値に上書きする。
    # 使い方： # を外す。行頭を COLOR_BLEED_H, COLOR_BLEED_V 等に合わせる。
    # ---------------------------
    #USE_VHS_MODE = True
    
# ==========================================

ntsc = Ntsc(precise=PRECISE_MODE)

# パラメータを実体に反映
ntsc._composite_preemphasis_cut = COMPOSITE_PRE_CUT
ntsc._composite_preemphasis = COMPOSITE_PRE
ntsc._vhs_out_sharpen = VHS_OUT_SHARPEN
ntsc._vhs_edge_wave = WAVE_STRENGTH
ntsc._vhs_head_switching = USE_HEAD_SWITCH
ntsc._vhs_head_switching_point = HEAD_SWITCH_POINT
ntsc._vhs_head_switching_phase = HEAD_SWITCH_PHASE
ntsc._vhs_head_switching_phase_noise = HEAD_SWITCH_NOISE
ntsc._color_bleed_before = BLEED_BEFORE
ntsc._color_bleed_horiz = COLOR_BLEED_H
ntsc._color_bleed_vert = COLOR_BLEED_V
ntsc._ringing = RINGING
ntsc._enable_ringing2 = ENABLE_RINGING2
ntsc._ringing_power = RINGING_POWER
ntsc._ringing_shift = RINGING_SHIFT
ntsc._freq_noise_size = FREQ_NOISE_SIZE
ntsc._freq_noise_amplitude = FREQ_NOISE_AMPLI
ntsc._composite_in_chroma_lowpass = IN_CHROMA_LP
ntsc._composite_out_chroma_lowpass = OUT_CHROMA_LP
ntsc._composite_out_chroma_lowpass_lite = OUT_CHROMA_LP_LITE
ntsc._video_chroma_noise = VIDEO_CHROMA_NOISE
ntsc._video_chroma_phase_noise = VIDEO_CHROMA_PHASE
ntsc._video_chroma_loss = VIDEO_CHROMA_LOSS
ntsc._video_noise = VIDEO_NOISE
ntsc._subcarrier_amplitude = SUBCARRIER_AMP
ntsc._subcarrier_amplitude_back = SUBCARRIER_AMP_B
ntsc._emulating_vhs = USE_VHS_MODE
ntsc._nocolor_subcarrier = NOCOLOR_SUBCARRIER
ntsc._vhs_chroma_vert_blend = VHS_CHROMA_V_BLEND
ntsc._vhs_svideo_out = VHS_SVIDEO_OUT
ntsc._output_ntsc = OUTPUT_NTSC
ntsc._video_scanline_phase_shift = SCANLINE_PHASE
ntsc._video_scanline_phase_shift_offset = SCANLINE_OFFSET

if TAPE_SPEED == "LP":
    ntsc._output_vhs_tape_speed = VHSSpeed.VHS_LP
elif TAPE_SPEED == "EP":
    ntsc._output_vhs_tape_speed = VHSSpeed.VHS_EP
else:
    ntsc._output_vhs_tape_speed = VHSSpeed.VHS_SP

# --- ファイル情報取得 ---
WIDTH  = int(os.environ.get("WIDTH", 640))
HEIGHT = int(os.environ.get("HEIGHT", 480)) # 640,480はファイル情報を取得できなかった場合に使用する。
input_video = os.environ.get("INPUT_VIDEO", "unknown_input")
output_video = os.environ.get("OUTPUT_VIDEO", "unknown_output")

frame_size = WIDTH * HEIGHT * 3
# --- 処理ループ ---
i = 0
buf = bytearray(frame_size)

while True:
    read_bytes = sys.stdin.buffer.readinto(buf)
    if read_bytes != frame_size:
        break

    frame = np.frombuffer(buf, np.uint8).reshape((HEIGHT, WIDTH, 3))
    out = frame.copy()

    # フィールド処理を重ねる
    ntsc.composite_layer(out, frame, field=0, fieldno=i)
    ntsc.composite_layer(out, frame, field=1, fieldno=i)

    sys.stdout.buffer.write(out.tobytes())
    i += 1

# --- ログ出力 ---
if WRITE_LOG:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    mode_label = "【ランダム生成】" if RANDOM_MODE else "【手動設定】"
    
    base_name = os.path.splitext(os.path.basename(output_video))[0]
    dir_path = os.path.dirname(output_video) or "."

    txt_name = f"{base_name} - {timestamp}.txt"
    txt_path = os.path.join(dir_path, txt_name)

    counter = 2
    while os.path.exists(txt_path):
        txt_name = f"{base_name} - {timestamp}_{counter}.txt"
        txt_path = os.path.join(dir_path, txt_name)
        counter += 1

    content = (
        f"入力動画：{input_video}\n"
        f"出力動画：{output_video}\n"
        f"実行日：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"generator=ntsc.py {mode_label}\n"
        f"\n"
        f"使用したパラメータ設定\n"
        f"COMPOSITE_PRE_CUT = {COMPOSITE_PRE_CUT} ; COMPOSITE_PRE = {COMPOSITE_PRE}\n"
        f"BLEED_BEFORE = {BLEED_BEFORE} ; COLOR_BLEED_H = {COLOR_BLEED_H} ; COLOR_BLEED_V = {COLOR_BLEED_V}\n"
        f"RINGING = {RINGING} ; ENABLE_RINGING2 = {ENABLE_RINGING2} ; RINGING_POWER = {RINGING_POWER} ; RINGING_SHIFT = {RINGING_SHIFT}\n"
        f"FREQ_NOISE_SIZE = {FREQ_NOISE_SIZE} ; FREQ_NOISE_AMPLI = {FREQ_NOISE_AMPLI}\n"
        f"VIDEO_NOISE = {VIDEO_NOISE} ; VIDEO_CHROMA_NOISE = {VIDEO_CHROMA_NOISE} ; VIDEO_CHROMA_PHASE = {VIDEO_CHROMA_PHASE} ; VIDEO_CHROMA_LOSS = {VIDEO_CHROMA_LOSS}\n"
        f"IN_CHROMA_LP = {IN_CHROMA_LP} ; OUT_CHROMA_LP = {OUT_CHROMA_LP} ; OUT_CHROMA_LP_LITE = {OUT_CHROMA_LP_LITE} ; OUTPUT_NTSC = {OUTPUT_NTSC}\n"
        f"SCANLINE_PHASE = {SCANLINE_PHASE} ; SCANLINE_OFFSET = {SCANLINE_OFFSET} ; SUBCARRIER_AMP = {SUBCARRIER_AMP} ; SUBCARRIER_AMP_B = {SUBCARRIER_AMP_B}\n"
        f"USE_VHS_MODE = {USE_VHS_MODE} ; TAPE_SPEED = '{TAPE_SPEED}' ; VHS_SVIDEO_OUT = {VHS_SVIDEO_OUT} ; VHS_CHROMA_V_BLEND = {VHS_CHROMA_V_BLEND}\n"
        f"VHS_OUT_SHARPEN = {VHS_OUT_SHARPEN} ; WAVE_STRENGTH = {WAVE_STRENGTH}\n"
        f"USE_HEAD_SWITCH = {USE_HEAD_SWITCH} ; HEAD_SWITCH_POINT = {HEAD_SWITCH_POINT} ; HEAD_SWITCH_PHASE = {HEAD_SWITCH_PHASE} ; HEAD_SWITCH_NOISE = {HEAD_SWITCH_NOISE}\n"
        f"PRECISE_MODE = {PRECISE_MODE} ; NOCOLOR_SUBCARRIER = {NOCOLOR_SUBCARRIER}\n"
    )

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)