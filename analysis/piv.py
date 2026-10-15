"""Ensemble-correlation PIV for the EN309 Couette-cell runs.

usage: python piv.py <run_dir> <prefix> <out.npz> [first] [last] [step] [dt]
"""
import sys
import numpy as np
from PIL import Image
from numpy.fft import rfft2, irfft2
from scipy.ndimage import gaussian_filter

run, prefix, out = sys.argv[1:4]
first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
last = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
step = int(sys.argv[6]) if len(sys.argv) > 6 else 4
dt = int(sys.argv[7]) if len(sys.argv) > 7 else 2   # frame separation of each pair

W, OV = 64, 32  # interrogation window and spacing (px)


def load(i):
    return np.array(Image.open(f"{run}/{prefix}_{i:06d}.tif"), np.float32)


# background = temporal mean over a sample of frames (removes camera fixed-pattern noise)
bg = np.mean(np.stack([load(i) for i in range(first, last, max(1, (last - first) // 200))]), 0)

H, Wd = bg.shape
ys = np.arange(0, H - W + 1, OV)
xs = np.arange(0, Wd - W + 1, OV)
win = np.outer(np.hanning(W), np.hanning(W)).astype(np.float32)


def windows(a):
    a = gaussian_filter(a - bg, 1.0)
    a[a < 0] = 0
    blk = np.lib.stride_tricks.sliding_window_view(a, (W, W))[::OV, ::OV][: len(ys), : len(xs)]
    blk = blk - blk.mean(axis=(2, 3), keepdims=True)
    blk = blk / (blk.std(axis=(2, 3), keepdims=True) + 1e-6)
    return blk * win


corr = np.zeros((len(ys), len(xs), W, W), np.float64)
npairs = 0
for i in range(first, last - dt, step):
    A, B = windows(load(i)), windows(load(i + dt))
    c = irfft2(np.conj(rfft2(A)) * rfft2(B), s=(W, W))
    corr += np.fft.fftshift(c, axes=(2, 3))
    npairs += 1
corr /= npairs


def subpix(c):
    c = gaussian_filter(c, 1.0)
    j, i = np.unravel_index(np.argmax(c), c.shape)
    if not (0 < j < W - 1 and 0 < i < W - 1):
        return np.nan, np.nan, 0.0
    cc = np.log(np.clip(c[j - 1:j + 2, i - 1:i + 2], 1e-9, None))
    dy = 0.5 * (cc[0, 1] - cc[2, 1]) / (cc[0, 1] - 2 * cc[1, 1] + cc[2, 1])
    dx = 0.5 * (cc[1, 0] - cc[1, 2]) / (cc[1, 0] - 2 * cc[1, 1] + cc[1, 2])
    # peak ratio: main peak vs. second peak outside a 5x5 neighbourhood
    m = c.copy()
    m[max(j - 2, 0):j + 3, max(i - 2, 0):i + 3] = -np.inf
    pr = c[j, i] / max(m.max(), 1e-9)
    return i + dx - W // 2, j + dy - W // 2, pr


U = np.full((len(ys), len(xs)), np.nan)
V = np.full_like(U, np.nan)
PR = np.zeros_like(U)
for a in range(len(ys)):
    for b in range(len(xs)):
        U[a, b], V[a, b], PR[a, b] = subpix(corr[a, b])

np.savez(out, x=xs + W / 2, y=ys + W / 2, u=U / dt, v=V / dt, pr=PR, npairs=npairs, dt=dt)
print(out, "pairs", npairs, "median |u| px/frame", np.nanmedian(np.hypot(U, V)) / dt,
      "median PR", np.median(PR))
