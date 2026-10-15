"""Run piv_gpu.py on 4 time blocks per run (from G6_EN309/):  python analysis/run_blocks.py"""
import subprocess, sys
PY = sys.executable
jobs = [("1_100fps_2pt14rpm", "1", "run1", 0, 4000, 1000, 1, 3),
        ("2_100fps_4pt3rpm", "2", "run2", 0, 2500, 625, 1, 3)]
for d, p, name, f0, f1, blk, step, dt in jobs:
    for b in range((f1 - f0) // blk):
        lo, hi = f0 + b * blk, f0 + (b + 1) * blk
        subprocess.run([PY, "analysis/piv_gpu.py", d, p, f"analysis/out/{name}_b{b}.npz",
                        str(lo), str(hi), str(step), str(dt)], check=True)
