# EN309 G6: Couette viscometer PIV

Ensemble-correlation PIV of a glycerine/water Couette cell (inner cylinder rotating, outer fixed),
fit to the exact Couette solution. See `analysis/HANDOFF.md` for setup, method and results.

Raw TIFF frames are not in the repo. Pipeline (from this folder):
```
python analysis/run_blocks.py                      # piv_gpu.py (CuPy) on 4 blocks per run
python analysis/analyse.py analysis/out --blocks   # per-block fits, mean ± SD of ω_eff
python analysis/collapse.py analysis/out           # averaged-field fit, linearity, u/Ω collapse
python analysis/make_workbook.py                   # analysis/G6_EN309_results.xlsx
```
`analysis/piv.py` is the CPU version (about 5x slower, same output).
