"""GPU (CuPy) version of piv.py; same algorithm and output format.

usage: python piv_gpu.py <run_dir> <prefix> <out.npz> [first] [last] [step] [dt]
"""
import sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cupy as cp
from cupyx.scipy.ndimage import gaussian_filter
from PIL import Image
from scipy.ndimage import gaussian_filter as gf_cpu

run, prefix, out = sys.argv[1:4]
first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
last = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
step = int(sys.argv[6]) if len(sys.argv) > 6 else 4
dt = int(sys.argv[7]) if len(sys.argv) > 7 else 2

W, OV = 64, 32


def load(i):
    return cp.asarray(np.array(Image.open(f"{run}/{prefix}_{i:06d}.tif"), np.float32))


bg = cp.mean(cp.stack([load(i) for i in range(first, last, max(1, (last - first) // 200))]), 0)
H, Wd = bg.shape
ys = np.arange(0, H - W + 1, OV)
xs = np.arange(0, Wd - W + 1, OV)
win = cp.asarray(np.outer(np.hanning(W), np.hanning(W)).astype(np.float32))


def windows(a):
    a = gaussian_filter(a - bg, 1.0)
    a = cp.where(a < 0, 0, a)
    blk = cp.lib.stride_tricks.sliding_window_view(a, (W, W))[::OV, ::OV][: len(ys), : len(xs)]
    blk = blk - blk.mean(axis=(2, 3), keepdims=True)
    blk = blk / (blk.std(axis=(2, 3), keepdims=True) + 1e-6)
    return blk * win


corr = cp.zeros((len(ys), len(xs), W, W), cp.float32)
npairs = 0
cache = {}  # frame -> windows, so each image is decoded and windowed once even when step < dt
pool = ThreadPoolExecutor(8)
raw = {}
AHEAD = 24  # frames decoded ahead of use (bounds memory)


def fetch(j):
    return np.array(Image.open(f"{run}/{prefix}_{j:06d}.tif"), np.float32)


def get(j):
    for k in range(j, min(j + AHEAD, last)):
        if k not in raw and k not in cache:
            raw[k] = pool.submit(fetch, k)
    if j not in cache:
        cache[j] = windows(cp.asarray(raw.pop(j).result()))
    return cache[j]


for i in range(first, last - dt, step):
    A, B = get(i), get(i + dt)
    c = cp.fft.irfft2(cp.conj(cp.fft.rfft2(A)) * cp.fft.rfft2(B), s=(W, W))
    corr += cp.fft.fftshift(c, axes=(2, 3))
    npairs += 1
    for j in [k for k in cache if k < i + step]:
        del cache[j]
corr = (corr / npairs).astype(cp.float64).get()


def subpix(c):
    c = gf_cpu(c, 1.0)
    j, i = np.unravel_index(np.argmax(c), c.shape)
    if not (0 < j < W - 1 and 0 < i < W - 1):
        return np.nan, np.nan, 0.0
    cc = np.log(np.clip(c[j - 1:j + 2, i - 1:i + 2], 1e-9, None))
    dy = 0.5 * (cc[0, 1] - cc[2, 1]) / (cc[0, 1] - 2 * cc[1, 1] + cc[2, 1])
    dx = 0.5 * (cc[1, 0] - cc[1, 2]) / (cc[1, 0] - 2 * cc[1, 1] + cc[1, 2])
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
