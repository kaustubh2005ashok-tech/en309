"""Averaged-field Couette fit, linearity check and v_theta/Omega collapse.  usage: python collapse.py <outdir>

Averages the PIV fields of the 4 time blocks of each run (all frames used), fits the exact Couette
solution and a straight line u = a + b r, then compares u/Omega across the two rotation rates.
"""
import sys, json, glob
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyse import fit_run, couette, R1, R2, RUNS

o = sys.argv[1]
out, series = {}, {}
for run, rpm in RUNS.items():
    ds = [np.load(f) for f in sorted(glob.glob(f"{o}/{run}_b*.npz"))]
    d = dict(x=ds[0]["x"], y=ds[0]["y"], u=np.mean([q["u"] for q in ds], 0), v=np.mean([q["v"] for q in ds], 0),
             pr=np.mean([q["pr"] for q in ds], 0), npairs=sum(int(q["npairs"]) for q in ds))
    res, (rt, uu) = fit_run(d, rpm)
    w_set, w = res["omega_set"], res["omega_fit"]
    # straight-line regression u = a + b r on the same vectors
    b, a = np.polyfit(rt, uu, 1)
    pl = a + b * rt
    r2_lin = 1 - np.sum((uu - pl) ** 2) / np.sum((uu - uu.mean()) ** 2)
    rmse_lin = np.sqrt(np.mean((uu - pl) ** 2))
    pc = couette(rt, w)
    r2_c = 1 - np.sum((uu - pc) ** 2) / np.sum((uu - uu.mean()) ** 2)
    rmse_c = np.sqrt(np.mean((uu - pc) ** 2))
    res.update(r2_couette=r2_c, rmse_couette=rmse_c, lin_slope=b, lin_intercept=a, r2_linear=r2_lin,
               rmse_linear=rmse_lin)
    out[run] = res
    series[run] = (rt, uu, np.array(res["bins"]["r"]), np.array(res["bins"]["u"]), np.array(res["bins"]["sd"]))
    print(run, f"npairs {d['npairs']}  w_set {w_set:.4f} w_eff {w:.4f} ratio {w/w_set:.3f} shift {res['shift_mm']:.2f} "
          f"| Couette R2 {r2_c:.4f} rmse {rmse_c:.4f} | linear R2 {r2_lin:.4f} rmse {rmse_lin:.4f}")

# shared-shift joint fit: same wall position for both runs, one omega each
data = {k: (series[k][0] - out[k]["shift_mm"], series[k][1]) for k in series}   # un-shifted radii
def resid(p):
    return np.concatenate([couette(data[k][0] + p[0], p[1 + i]) - data[k][1] for i, k in enumerate(data)])
j = least_squares(resid, [out["run1"]["shift_mm"], out["run1"]["omega_fit"], out["run2"]["omega_fit"]],
                  loss="soft_l1", f_scale=0.05)
out["joint"] = dict(shift_mm=j.x[0], omega_run1=j.x[1], omega_run2=j.x[2])
print("joint shared-shift fit:", out["joint"])

# ---- collapse figure: u/Omega vs r
col = {"run1": "#2a6fb0", "run2": "#d9822b"}
fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.8))
rg = np.linspace(R1, R2, 200)
for ax, key, lab in ((axs[0], "omega_set", "set Ω (nominal rpm)"), (axs[1], "omega_fit", "fitted ω_eff")):
    for run in RUNS:
        rt, uu, rb, ub, eb = series[run]
        Om = out[run][key]
        ax.plot(rt, uu / Om, ".", ms=2, alpha=0.18, color=col[run])
        ax.errorbar(rb, ub / Om, eb / Om, fmt="o", ms=5, capsize=2, color=col[run],
                    label=f"Run {run[-1]}: {RUNS[run]} rpm")
    ax.plot(rg, couette(rg, 1.0), "k--", lw=1.5, label="ideal Couette, u/Ω")
    ax.set_xlim(R1, R2); ax.set_ylim(0, None)
    ax.set_xlabel("r [mm]"); ax.set_ylabel(r"$u_\theta/\Omega$ [mm]")
    ax.set_title(f"Collapse using {lab}")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{o}/collapse.png", dpi=150)

# collapse metric (rms difference / mean u/Omega; a pointwise ratio blows up as u -> 0 at the wall): spread of u/Omega between runs on a common radius grid
for key in ("omega_set", "omega_fit"):
    rr = np.linspace(max(7.0, *(series[k][2].min() for k in series)), min(series[k][2].max() for k in series), 12)
    a1, a2 = (np.interp(rr, series[k][2], series[k][3]) / out[k][key] for k in ("run1", "run2"))
    out[f"collapse_{key}_rms_pct"] = float(100 * np.sqrt(np.mean((a1 - a2) ** 2)) / np.mean((a1 + a2) / 2))
    print("collapse rms difference", key, round(out[f"collapse_{key}_rms_pct"], 1), "%")
json.dump(out, open(f"{o}/collapse.json", "w"), indent=1, default=float)
