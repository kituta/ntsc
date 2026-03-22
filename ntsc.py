import math
import random
import os
from enum import Enum
from typing import List, Final, Optional
from pathlib import Path
# 現代風に高速化できる箇所はありますか？計算結果は素と絶対に同一になるようにしてください。コメントアウトは残してください。
import cv2
import numpy as np
import numpy
import scipy.signal
from scipy.signal import lfilter
from scipy.ndimage import shift

M_PI: Final[float] = math.pi
Int_MIN_VALUE = -2147483648
Int_MAX_VALUE = 2147483647

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
RING_PATTERN_PATH: Final[Path] = BASE_DIR / 'ringPattern.npy'

if RING_PATTERN_PATH.exists():
    RingPattern = np.load(str(RING_PATTERN_PATH))
else:
    RingPattern = np.ones(1024) 


def ringing(img2d, alpha=0.5, noiseSize=0, noiseValue=2, clip=True, seed=None):
    """
    https://bavc.github.io/avaa/artifacts/ringing.html
    """
    dft = cv2.dft(np.float32(img2d), flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)

    rows, cols = img2d.shape
    crow, ccol = rows // 2, cols // 2
    mask = np.zeros((rows, cols, 2), np.float32)

    maskH = min(crow, int(1 + alpha * crow))
    mask[:, ccol - maskH:ccol + maskH] = 1

    if noiseSize > 0:
        noise = np.ones((mask.shape[0], mask.shape[1], mask.shape[2]), dtype=np.float32) * noiseValue - noiseValue / 2.0
        start = int(ccol - ((1 - noiseSize) * ccol))
        stop = int(ccol + ((1 - noiseSize) * ccol))
        noise[:, start:stop, :] = 0
        rnd = np.random.RandomState(seed)
        mask = mask + rnd.rand(mask.shape[0], mask.shape[1], mask.shape[2]).astype(np.float32) * noise - noise / 2.0

    img_back = cv2.idft(np.fft.ifftshift(dft_shift * mask), flags=cv2.DFT_SCALE)
    if clip:
        _min, _max = img2d.min(), img2d.max()
        return np.clip(img_back[:, :, 0], _min, _max)
    else:
        return img_back[:, :, 0]


def ringing2(img2d, power=4, shift=0, clip=True):
    """
    https://bavc.github.io/avaa/artifacts/ringing.html
    :param img2d: 2d image
    :param power: int, ringing parrern poser (optimal 2 - 6)
    :return: 2d image
    """
    dft = cv2.dft(np.float32(img2d), flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)

    rows, cols = img2d.shape

    scalecols = int(cols * (1 + shift))
    mask = cv2.resize(RingPattern[np.newaxis, :], (scalecols, 1), interpolation=cv2.INTER_LINEAR)[0]

    mask = mask[(scalecols // 2) - (cols // 2):(scalecols // 2) + (cols // 2)]
    mask = mask ** power
    img_back = cv2.idft(np.fft.ifftshift(dft_shift * mask[None, :, None]), flags=cv2.DFT_SCALE)
    if clip:
        _min, _max = img2d.min(), img2d.max()
        return np.clip(img_back[:, :, 0], _min, _max)
    else:
        return img_back[:, :, 0]


def fmod(x: float, y: float) -> float:
    return x % y


class NumpyRandom:
    def __init__(self, seed=None):
        self.rng = numpy.random.default_rng(seed)

    def random(self) -> float:
        return float(self.rng.random())

    def nextFloat(self) -> float:
        return float(self.rng.random())

    def nextInt(self, _from: int = 0, until: int = Int_MAX_VALUE) -> int:
        return int(self.rng.integers(_from, until))

    def nextIntArray(self, size: int, _from: int = 0, until: int = Int_MAX_VALUE) -> numpy.ndarray:
        return self.rng.integers(_from, until, size=size, dtype=numpy.int32)

def bgr2yiq(bgrimg: numpy.ndarray) -> numpy.ndarray:
    img = bgrimg.astype(numpy.float32)
    b = img[..., 0]
    g = img[..., 1]
    r = img[..., 2]
    
    dY = 0.299 * r + 0.587 * g + 0.114 * b
    
    Y = (dY * 256).astype(numpy.int32)
    I = (256 * (0.596 * r - 0.274 * g - 0.322 * b)).astype(numpy.int32)
    Q = (256 * (0.211 * r - 0.523 * g + 0.312 * b)).astype(numpy.int32)
    return numpy.stack([Y, I, Q], axis=0)

def yiq2bgr(yiq: numpy.ndarray, dst_bgr: numpy.ndarray = None, field: int = 0) -> numpy.ndarray:
    c, h, w = yiq.shape
    dst_bgr = dst_bgr if dst_bgr is not None else numpy.zeros((h, w, c))
    
    Y, I, Q = yiq
    if field == 0:
        Y_f, I_f, Q_f = Y[::2], I[::2], Q[::2]
        sl = slice(None, None, 2)
    else:
        Y_f, I_f, Q_f = Y[1::2], I[1::2], Q[1::2]
        sl = slice(1, None, 2)

    r = ((1.000 * Y_f + 0.956 * I_f + 0.621 * Q_f) / 256).astype(numpy.int32)
    g = ((1.000 * Y_f + -0.272 * I_f + -0.647 * Q_f) / 256).astype(numpy.int32)
    b = ((1.000 * Y_f + -1.106 * I_f + 1.703 * Q_f) / 256).astype(numpy.int32)
    
    dst_bgr[sl, :, 0] = numpy.clip(b, 0, 255)
    dst_bgr[sl, :, 1] = numpy.clip(g, 0, 255)
    dst_bgr[sl, :, 2] = numpy.clip(r, 0, 255)
    
    return dst_bgr


class LowpassFilter:
    def __init__(self, rate: float, hz: float, value: float = 0.0):
        self.timeInterval: float = 1.0 / rate
        self.tau: float = 1 / (hz * 2.0 * M_PI)
        self.alpha: float = self.timeInterval / (self.tau + self.timeInterval)
        self.prev: float = value

    def lowpass(self, sample: float) -> float:
        stage1 = sample * self.alpha
        stage2 = self.prev - self.prev * self.alpha
        self.prev = stage1 + stage2
        return self.prev

    def highpass(self, sample: float) -> float:
        stage1 = sample * self.alpha
        stage2 = self.prev - self.prev * self.alpha
        self.prev = stage1 + stage2
        return sample - self.prev

    def lowpass_array(self, samples: numpy.ndarray) -> numpy.ndarray:
        if self.prev == 0.0:
            return lfilter([self.alpha], [1, -(1.0 - self.alpha)], samples)
        else:
            ic = scipy.signal.lfiltic([self.alpha], [1, -(1.0 - self.alpha)], [self.prev])
            return lfilter([self.alpha], [1, -(1.0 - self.alpha)], samples, zi=ic)[0]

    def highpass_array(self, samples: numpy.ndarray) -> numpy.ndarray:
        f = self.lowpass_array(samples)
        return samples - f


def composite_lowpass(yiq: numpy.ndarray, field: int, fieldno: int):
    _, height, width = yiq.shape
    fY, fI, fQ = yiq
    rate = Ntsc.NTSC_RATE

    for p in range(1, 3):
        cutoff = 1300000.0 if p == 1 else 600000.0
        delay = 2 if (p == 1) else 4
        P = fI if (p == 1) else fQ
        target_field = P[field::2]
        num_rows = target_field.shape[0]

        tau = 1 / (cutoff * 2.0 * M_PI)
        alpha = (1.0 / rate) / (tau + (1.0 / rate))
        b, a = [alpha], [1, -(1.0 - alpha)]

        zi = np.tile(scipy.signal.lfiltic(b, a, [0.0]), (num_rows, 1))
        
        f, _ = scipy.signal.lfilter(b, a, target_field, axis=-1, zi=zi)
        f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)
        f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)

        target_field[:, :width - delay] = f[:, delay:].astype(numpy.int32)

def composite_lowpass_tv(yiq: numpy.ndarray, field: int, fieldno: int):
    _, height, width = yiq.shape
    fY, fI, fQ = yiq
    rate = Ntsc.NTSC_RATE
    cutoff = 2600000.0
    delay = 1

    tau = 1 / (cutoff * 2.0 * M_PI)
    alpha = (1.0 / rate) / (tau + (1.0 / rate))
    b, a = [alpha], [1, -(1.0 - alpha)]

    for p in range(1, 3):
        P = fI if (p == 1) else fQ
        target_field = P[field::2]
        num_rows = target_field.shape[0]

        zi = np.tile(scipy.signal.lfiltic(b, a, [0.0]), (num_rows, 1))

        f, _ = scipy.signal.lfilter(b, a, target_field, axis=-1, zi=zi)
        f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)
        f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)

        target_field[:, :width - delay] = f[:, delay:].astype(np.int32)


def composite_preemphasis(yiq: numpy.ndarray, field: int, composite_preemphasis: float,
                          composite_preemphasis_cut: float):
    fY, fI, fQ = yiq
    target_field = fY[field::2]
    num_rows = target_field.shape[0]

    rate = Ntsc.NTSC_RATE
    tau = 1 / (composite_preemphasis_cut * 2.0 * M_PI)
    alpha = (1.0 / rate) / (tau + (1.0 / rate))
    b, a = [alpha], [1, -(1.0 - alpha)]

    zi = np.tile(scipy.signal.lfiltic(b, a, [16.0]), (num_rows, 1))

    f_lp, _ = scipy.signal.lfilter(b, a, target_field, axis=-1, zi=zi)
    filtered = target_field + (target_field - f_lp) * composite_preemphasis

    fY[field::2] = filtered.astype(np.int32)


class VHSSpeed(Enum):
    VHS_SP = (2400000.0, 320000.0, 9)
    VHS_LP = (1900000.0, 300000.0, 12)
    VHS_EP = (1400000.0, 280000.0, 14)

    def __init__(self, luma_cut: float, chroma_cut: float, chroma_delay: int):
        self.luma_cut = luma_cut
        self.chroma_cut = chroma_cut
        self.chroma_delay = chroma_delay


class Ntsc:
    NTSC_RATE = 315000000.00 / 88 * 4 
    
    _Umult = numpy.array([1, 0, -1, 0], dtype=numpy.int32)
    _Vmult = numpy.array([0, 1, 0, -1], dtype=numpy.int32)
    
    def __init__(self, precise=False, random=None):
        self.precise = precise
        self.random = random if random is not None else NumpyRandom(31374242)
        self._composite_preemphasis_cut = 1000000.0
        self._composite_preemphasis = 0.0 

        self._vhs_out_sharpen = 1.5 

        self._vhs_edge_wave = 0 

        self._vhs_head_switching = False 
        self._vhs_head_switching_point = 1.0 - (4.5 + 0.01) / 262.5 
        self._vhs_head_switching_phase = (1.0 - 0.01) / 262.5 
        self._vhs_head_switching_phase_noise = 1.0 / 500 / 262.5 

        self._color_bleed_before = True 
        self._color_bleed_horiz = 0 
        self._color_bleed_vert = 0 
        self._ringing = 1.0 
        self._enable_ringing2 = True
        self._ringing_power = 2
        self._ringing_shift = 0
        self._freq_noise_size = 0 
        self._freq_noise_amplitude = 2 
        self._composite_in_chroma_lowpass = True 
        self._composite_out_chroma_lowpass = True
        self._composite_out_chroma_lowpass_lite = True

        self._video_chroma_noise = 0 
        self._video_chroma_phase_noise = 0 
        self._video_chroma_loss = 0 
        self._video_noise = 2 
        self._subcarrier_amplitude = 50
        self._subcarrier_amplitude_back = 50
        self._emulating_vhs = False
        self._nocolor_subcarrier = False 
        self._vhs_chroma_vert_blend = True 
        self._vhs_svideo_out = False 

        self._output_ntsc = True 
        self._video_scanline_phase_shift = 180
        self._video_scanline_phase_shift_offset = 0 
        self._output_vhs_tape_speed = VHSSpeed.VHS_SP

    def rand(self) -> numpy.int32:
        return self.random.nextInt(_from=0)

    def rand_array(self, size: int) -> numpy.ndarray:
        return self.random.nextIntArray(size, 0, Int_MAX_VALUE)

    def video_noise(self, yiq: numpy.ndarray, field: int, video_noise: int):
        fY = yiq[0, field::2]
        fh, fw = fY.shape
        noise_mod = video_noise * 2 + 1
        
        if not self.precise:
            rnds = self.rand_array(fw * fh).reshape(fh, fw) % noise_mod - video_noise
            b, a = [0.5], [1, -0.5]
            noises = scipy.signal.lfilter(b, a, rnds.astype(np.float32), axis=-1)
            noises = np.hstack([np.zeros((fh, 1)), noises[:, :-1]])
            fY += noises.astype(np.int32)
        else:
            noise = 0
            for row in fY:
                rnds = self.rand_array(fw) % noise_mod - video_noise
                for x in range(0, fw):
                    row[x] += noise
                    noise += rnds[x]
                    noise = int(noise / 2)

    def video_chroma_noise(self, yiq: numpy.ndarray, field: int, video_chroma_noise: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq

        noise_mod = video_chroma_noise * 2 + 1
        U = fI[field::2]
        V = fQ[field::2]
        fh, fw = U.shape
        if not self.precise:
            lp = LowpassFilter(1, 1, 0)
            lp.alpha = 0.5
            rndsU = self.rand_array(fw * fh) % noise_mod - video_chroma_noise
            noisesU = shift(lp.lowpass_array(rndsU).astype(numpy.int32), 1)

            rndsV = self.rand_array(fw * fh) % noise_mod - video_chroma_noise
            noisesV = shift(lp.lowpass_array(rndsV).astype(numpy.int32), 1)

            U += noisesU.reshape(U.shape)
            V += noisesV.reshape(V.shape)
        else:
            noiseU = 0
            noiseV = 0
            for y in range(0, fh):
                for x in range(0, fw):
                    U[y][x] += noiseU
                    noiseU += self.rand() % noise_mod - video_chroma_noise
                    noiseU = int(noiseU / 2)

                    V[y][x] += noiseV
                    noiseV += self.rand() % noise_mod - video_chroma_noise
                    noiseV = int(noiseV / 2)

    def video_chroma_phase_noise(self, yiq: numpy.ndarray, field: int, video_chroma_phase_noise: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        noise_mod = video_chroma_phase_noise * 2 + 1
        U = fI[field::2]
        V = fQ[field::2]
        fh, fw = U.shape
        noise = 0
        for y in range(0, fh):
            noise += self.rand() % noise_mod - video_chroma_phase_noise
            noise = int(noise / 2)
            pi = noise * M_PI / 100
            sinpi = math.sin(pi)
            cospi = math.cos(pi)
            u = U[y] * cospi - V[y] * sinpi
            v = U[y] * sinpi + V[y] * cospi
            U[y, :] = u
            V[y, :] = v

    def vhs_head_switching(self, yiq: numpy.ndarray, field: int = 0):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        twidth = width + width // 10
        shy = 0
        noise = 0.0

        if self._vhs_head_switching_phase_noise != 0.0:
            x = numpy.int32(self.rand())
            x = numpy.int32(x * self.rand())
            x = numpy.int32(x * self.rand())
            x = numpy.int32(x * self.rand())
            x = x & 0x7FFFFFFF
            x %= 2000000000
            noise = (x / 1000000000.0 - 1.0) * self._vhs_head_switching_phase_noise * 0.8 # ここを 0.8 倍（20%カット）にすると、フレームごとの位置の跳ね返りがマイルドになります

        scanlines = 262.5 if self._output_ntsc else 312.5
        t = twidth * scanlines

        p_point = int(fmod(self._vhs_head_switching_point + noise, 1.0) * t)
        y = int(p_point // twidth * 2) + field

        p_phase = int(fmod(self._vhs_head_switching_phase + noise, 1.0) * t)
        x_orig = p_phase % twidth

        y -= (262 - 240) * 2 if self._output_ntsc else (312 - 288) * 2

        tx = x_orig
        ishif = (x_orig - twidth if x_orig >= twidth // 2 else x_orig) * 1.2 # 1.2を変えると振れ幅が変わる。
        shif = 0.0

        while y < height:
            if y >= 0:
                current_tx = tx if shy == 0 else 0
                int_shif = int(shif)

                if int_shif != 0:
                    x2 = int((current_tx + twidth + int_shif) % twidth)

                    for channel in [fY, fI, fQ]:
                        tmp = numpy.zeros(twidth, dtype=channel.dtype)
                        tmp[:width] = channel[y]
                        double_tmp = numpy.concatenate([tmp, tmp])

                        end_idx = x2 + (width - current_tx)
                        channel[y][current_tx:width] = double_tmp[x2 : int(end_idx)]

            shif = ishif if shy == 0 else shif * 7 / 8
            tx = 0
            y += 2
            shy += 1

    def _chroma_luma_xi(self, fieldno: int, y: int):
        if self._video_scanline_phase_shift == 90:
            return int(fieldno + self._video_scanline_phase_shift_offset + (y >> 1)) & 3
        elif self._video_scanline_phase_shift == 180:
            return int(((((fieldno + y) & 2) + self._video_scanline_phase_shift_offset) & 3))
        elif self._video_scanline_phase_shift == 270:
            return int(((fieldno + self._video_scanline_phase_shift_offset) & 3))
        else:
            return int(self._video_scanline_phase_shift_offset & 3)

    def chroma_into_luma(self, yiq: numpy.ndarray, field: int, fieldno: int, subcarrier_amplitude: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        
        y_indices = np.arange(field, height, 2)
        num_rows = len(y_indices)
        
        if self._video_scanline_phase_shift == 90:
            xi_arr = (fieldno + self._video_scanline_phase_shift_offset + (y_indices >> 1)) & 3
        elif self._video_scanline_phase_shift == 180:
            xi_arr = ((((fieldno + y_indices) & 2) + self._video_scanline_phase_shift_offset) & 3)
        elif self._video_scanline_phase_shift == 270:
            xi_arr = np.full(num_rows, (fieldno + self._video_scanline_phase_shift_offset) & 3)
        else:
            xi_arr = np.full(num_rows, self._video_scanline_phase_shift_offset & 3)

        umult_table = np.array([
            np.tile(Ntsc._Umult, (width // 4) + 2)[i : i + width] for i in range(4)
        ])
        vmult_table = np.array([
            np.tile(Ntsc._Vmult, (width // 4) + 2)[i : i + width] for i in range(4)
        ])

        umult_2d = umult_table[xi_arr]
        vmult_2d = vmult_table[xi_arr]

        chroma = fI[field::2] * subcarrier_amplitude * umult_2d
        chroma += fQ[field::2] * subcarrier_amplitude * vmult_2d
        
        fY[field::2] += (chroma // 50).astype(np.int32)
        fI[field::2] = 0
        fQ[field::2] = 0


    def chroma_from_luma(self, yiq: numpy.ndarray, field: int, fieldno: int, subcarrier_amplitude: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq

        Y_fields = fY[field::2]
        num_rows = Y_fields.shape[0]

        sum_vals = Y_fields[:, 0] + Y_fields[:, 1]

        y2 = np.pad(Y_fields[:, 2:], ((0, 0), (0, 2)))
        yd4 = np.pad(Y_fields[:, :-2], ((0, 0), (2, 0)))

        sums = y2 - yd4
        sums0 = np.column_stack([sum_vals, sums])

        acc = np.add.accumulate(sums0, axis=1)[:, 1:]
        acc4 = acc // 4
        chromas = y2 - acc4

        fY[field::2] = acc4

        y_indices = np.arange(field, height, 2)

        for i, y in enumerate(y_indices):
            chroma = chromas[i]
            xi = self._chroma_luma_xi(fieldno, y)

            x = (4 - xi) & 3
            chroma[x + 2::4] = -chroma[x + 2::4]
            chroma[x + 3::4] = -chroma[x + 3::4]

            chroma = (chroma * 50 / subcarrier_amplitude)

            cxi = -chroma[xi::2]
            cxi1 = -chroma[xi + 1::2]

            fI[y, ::2] = np.pad(cxi, (0, width // 2 - cxi.shape[0]))
            fQ[y, ::2] = np.pad(cxi1, (0, width // 2 - cxi1.shape[0]))

            fI[y, 1:width - 2:2] = (fI[y, :width - 2:2] + fI[y, 2::2]) >> 1
            fQ[y, 1:width - 2:2] = (fQ[y, :width - 2:2] + fQ[y, 2::2]) >> 1
            fI[y, width - 2:] = 0
            fQ[y, width - 2:] = 0

    def vhs_luma_lowpass(self, yiq: np.ndarray, field: int, luma_cut: float):
        fY = yiq[0, field::2]
        num_rows = fY.shape[0]

        rate = Ntsc.NTSC_RATE
        timeInterval = 1.0 / rate
        tau = 1 / (luma_cut * 2.0 * M_PI)
        alpha = timeInterval / (tau + timeInterval)
        b, a = [alpha], [1, -(1.0 - alpha)]

        zi_value = scipy.signal.lfiltic(b, a, [16.0])
        zi = np.tile(zi_value, (num_rows, 1))

        f0, _ = scipy.signal.lfilter(b, a, fY, axis=-1, zi=zi)
        f1, _ = scipy.signal.lfilter(b, a, f0, axis=-1, zi=zi)
        f2, _ = scipy.signal.lfilter(b, a, f1, axis=-1, zi=zi)

        f2_lp, _ = scipy.signal.lfilter(b, a, f2, axis=-1, zi=zi)
        f_hp = f2 - f2_lp
        
        yiq[0, field::2] = (f2 + f_hp * 1.6).astype(np.int32)

    def vhs_chroma_lowpass(self, yiq: np.ndarray, field: int, chroma_cut: float, chroma_delay: int):
        rate = Ntsc.NTSC_RATE
        tau = 1 / (chroma_cut * 2.0 * M_PI)
        alpha = (1.0 / rate) / (tau + (1.0 / rate))
        b, a = [alpha], [1, -(1.0 - alpha)]

        for i in [1, 2]:
            target_field = yiq[i, field::2]
            num_rows = target_field.shape[0]

            zi_value = scipy.signal.lfiltic(b, a, [0.0])
            zi = np.tile(zi_value, (num_rows, 1))

            f, _ = scipy.signal.lfilter(b, a, target_field, axis=-1, zi=zi)
            f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)
            f, _ = scipy.signal.lfilter(b, a, f, axis=-1, zi=zi)

            target_field[:, :-chroma_delay] = f[:, chroma_delay:]

    def vhs_chroma_vert_blend(self, yiq: numpy.ndarray, field: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        U2 = fI[field + 2::2, ]
        V2 = fQ[field + 2::2, ]
        delayU = numpy.pad(U2[:-1, ], [[1, 0], [0, 0]])
        delayV = numpy.pad(V2[:-1, ], [[1, 0], [0, 0]])
        fI[field + 2::2, ] = (delayU + U2 + 1) >> 1
        fQ[field + 2::2, ] = (delayV + V2 + 1) >> 1

    def vhs_sharpen(self, yiq: numpy.ndarray, field: int, luma_cut: float):
        fY = yiq[0]
        target_field = fY[field::2]
        num_rows = target_field.shape[0]

        rate = Ntsc.NTSC_RATE
        timeInterval = 1.0 / rate
        tau = 1 / ((luma_cut * 4) * 2.0 * M_PI)
        alpha = timeInterval / (tau + timeInterval)
        b, a = [alpha], [1, -(1.0 - alpha)]

        zi_value = scipy.signal.lfiltic(b, a, [0.0])
        zi = np.tile(zi_value, (num_rows, 1))

        ts, _ = scipy.signal.lfilter(b, a, target_field, axis=-1, zi=zi)
        ts, _ = scipy.signal.lfilter(b, a, ts, axis=-1, zi=zi)
        ts, _ = scipy.signal.lfilter(b, a, ts, axis=-1, zi=zi)

        fY[field::2] = (target_field + (target_field - ts) * self._vhs_out_sharpen * 2.0).astype(numpy.int32)

    def color_bleed(self, yiq: numpy.ndarray, field: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq

        field_ = fI[field::2]
        h, w = field_.shape
        fI[field::2] = numpy.pad(field_, ((self._color_bleed_vert, 0), (self._color_bleed_horiz, 0)))[0:h, 0:w]

        field_ = fQ[field::2]
        h, w = field_.shape
        fQ[field::2] = numpy.pad(field_, ((self._color_bleed_vert, 0), (self._color_bleed_horiz, 0)))[0:h, 0:w]

    def vhs_edge_wave(self, yiq: numpy.ndarray, field: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        rnds = self.random.nextIntArray(height // 2, 0, self._vhs_edge_wave)
        lp = LowpassFilter(Ntsc.NTSC_RATE, self._output_vhs_tape_speed.luma_cut,
                           0) 
        rnds = lp.lowpass_array(rnds).astype(numpy.int32)

        for y in range(len(rnds)):
            shift_val = rnds[y]
            if shift_val != 0:
                fY[field + y * 2, shift_val:] = fY[field + y * 2, :-shift_val]
                fI[field + y * 2, shift_val:] = fI[field + y * 2, :-shift_val]
                fQ[field + y * 2, shift_val:] = fQ[field + y * 2, :-shift_val]

    def vhs_chroma_loss(self, yiq: numpy.ndarray, field: int, video_chroma_loss: int):
        _, height, width = yiq.shape
        fY, fI, fQ = yiq
        for y in range(field, height, 2):
            U = fI[y]
            V = fQ[y]
            if self.rand() % 100000 < video_chroma_loss:
                U[:] = 0
                V[:] = 0

    def emulate_vhs(self, yiq: numpy.ndarray, field: int, fieldno: int):
        vhs_speed = self._output_vhs_tape_speed
        if self._vhs_edge_wave != 0:
            self.vhs_edge_wave(yiq, field)

        self.vhs_luma_lowpass(yiq, field, vhs_speed.luma_cut)

        self.vhs_chroma_lowpass(yiq, field, vhs_speed.chroma_cut, vhs_speed.chroma_delay)

        if self._vhs_chroma_vert_blend and self._output_ntsc:
            self.vhs_chroma_vert_blend(yiq, field)

        if True: 
            self.vhs_sharpen(yiq, field, vhs_speed.luma_cut)

        if not self._vhs_svideo_out:
            self.chroma_into_luma(yiq, field, fieldno, self._subcarrier_amplitude)
            self.chroma_from_luma(yiq, field, fieldno, self._subcarrier_amplitude)

    def composite_layer(self, dst: numpy.ndarray, src: numpy.ndarray, field: int, fieldno: int):
        assert dst.shape == src.shape, "dst and src images must be of same shape"
        yiq = bgr2yiq(src)
        
        _, height, _ = yiq.shape
        if height % 2 != 0:
            yiq = yiq[:, :-1, :]

        if self._color_bleed_before and (self._color_bleed_vert != 0 or self._color_bleed_horiz != 0):
            self.color_bleed(yiq, field)

        if self._composite_in_chroma_lowpass:
            composite_lowpass(yiq, field, fieldno)

        if self._ringing != 1.0:
            self.ringing(yiq, field)

        self.chroma_into_luma(yiq, field, fieldno, self._subcarrier_amplitude)

        if self._composite_preemphasis != 0.0 and self._composite_preemphasis_cut > 0:
            composite_preemphasis(yiq, field, self._composite_preemphasis, self._composite_preemphasis_cut)

        if self._video_noise != 0:
            self.video_noise(yiq, field, self._video_noise)

        if self._vhs_head_switching:
            self.vhs_head_switching(yiq, field)

        if not self._nocolor_subcarrier:
            self.chroma_from_luma(yiq, field, fieldno, self._subcarrier_amplitude_back)

        if self._video_chroma_noise != 0:
            self.video_chroma_noise(yiq, field, self._video_chroma_noise)

        if self._video_chroma_phase_noise != 0:
            self.video_chroma_phase_noise(yiq, field, self._video_chroma_phase_noise)

        if self._emulating_vhs:
            self.emulate_vhs(yiq, field, fieldno)

        if self._video_chroma_loss != 0:
            self.vhs_chroma_loss(yiq, field, self._video_chroma_loss)

        if self._composite_out_chroma_lowpass:
            if self._composite_out_chroma_lowpass_lite:
                composite_lowpass_tv(yiq, field, fieldno)
            else:
                composite_lowpass(yiq, field, fieldno)

        if not self._color_bleed_before and (self._color_bleed_vert != 0 or self._color_bleed_horiz != 0):
            self.color_bleed(yiq, field)

        Y, I, Q = yiq

        I[field::2] = self._blur_chroma(I[field::2])
        Q[field::2] = self._blur_chroma(Q[field::2])

        yiq2bgr(yiq, dst, field)

    def _blur_chroma(self, chroma: numpy.ndarray) -> numpy.ndarray:
        h, w = chroma.shape
        down2 = cv2.resize(chroma.astype(numpy.float32), (w // 2, h // 2), interpolation=cv2.INTER_LANCZOS4)
        return cv2.resize(down2, (w, h), interpolation=cv2.INTER_LANCZOS4).astype(numpy.int32)

    def ringing(self, yiq: numpy.ndarray, field: int):
        Y, I, Q = yiq
        sz = self._freq_noise_size
        amp = self._freq_noise_amplitude
        shift = self._ringing_shift
        if not self._enable_ringing2:
            Y[field::2] = ringing(Y[field::2], self._ringing, noiseSize=sz, noiseValue=amp, clip=False)
            I[field::2] = ringing(I[field::2], self._ringing, noiseSize=sz, noiseValue=amp, clip=False)
            Q[field::2] = ringing(Q[field::2], self._ringing, noiseSize=sz, noiseValue=amp, clip=False)
        else:
            Y[field::2] = ringing2(Y[field::2], power=self._ringing_power, shift=shift, clip=False)
            I[field::2] = ringing2(I[field::2], power=self._ringing_power, shift=shift, clip=False)
            Q[field::2] = ringing2(Q[field::2], power=self._ringing_power, shift=shift, clip=False)


def random_ntsc(seed=None) -> Ntsc:
    rnd = random.Random(seed)
    ntsc = Ntsc(random=NumpyRandom(seed))
    ntsc._composite_preemphasis = rnd.triangular(0, 8, 0)
    ntsc._vhs_out_sharpen = rnd.triangular(1, 5, 1.5)
    ntsc._composite_in_chroma_lowpass = rnd.random() < 0.8 
    ntsc._composite_out_chroma_lowpass = rnd.random() < 0.8 
    ntsc._composite_out_chroma_lowpass_lite = rnd.random() < 0.8 
    ntsc._video_chroma_noise = int(rnd.triangular(0, 16384, 2))
    ntsc._video_chroma_phase_noise = int(rnd.triangular(0, 50, 2))
    ntsc._video_chroma_loss = int(rnd.triangular(0, 50000, 10))
    ntsc._video_noise = int(rnd.triangular(0, 4200, 2))
    ntsc._emulating_vhs = rnd.random() < 0.2 
    ntsc._vhs_edge_wave = int(rnd.triangular(0, 5, 0))
    ntsc._video_scanline_phase_shift = rnd.choice([0, 90, 180, 270])
    ntsc._video_scanline_phase_shift_offset = rnd.randint(0, 3)
    ntsc._output_vhs_tape_speed = rnd.choice([VHSSpeed.VHS_SP, VHSSpeed.VHS_LP, VHSSpeed.VHS_EP])
    enable_ringing = rnd.random() < 0.8
    if enable_ringing:
        ntsc._ringing = rnd.uniform(0.3, 0.7)
        enable_freq_noise = rnd.random() < 0.8
        if enable_freq_noise:
            ntsc._freq_noise_size = rnd.uniform(0.5, 0.99)
            ntsc._freq_noise_amplitude = rnd.uniform(0.5, 2.0)
        ntsc._enable_ringing2 = rnd.random() < 0.5
        ntsc._ringing_power = rnd.randint(2, 7)
    ntsc._color_bleed_before = 1 == rnd.randint(0, 1)
    ntsc._color_bleed_horiz = int(rnd.triangular(0, 8, 0))
    ntsc._color_bleed_vert = int(rnd.triangular(0, 8, 0))
    return ntsc


def lowpassFilters(cutoff: float, reset: float, rate: float = Ntsc.NTSC_RATE) -> List[LowpassFilter]:
    return [LowpassFilter(rate, cutoff, reset) for x in range(0, 3)]