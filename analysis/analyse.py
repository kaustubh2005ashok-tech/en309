"""Couette-profile analysis of the PIV fields.

usage: python analyse.py <outdir>            fit run1.npz / run2.npz, write results.json + plot
       python analyse.py <outdir> --blocks   also fit run{1,2}_b{0..3}.npz -> blocks.json (mean ± SD, drift)
"""
import sys, json, glob
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PX_PER_MM = 161.9        # calibration grid (1 mm squares)
FPS = 100.0
R1, R2 = 6.0, 11.0       # mm, from Inner_/Outer_cylinder.step
RUNS = {"run1": 2.14, "run2": 4.3}   # rpm (folder names)


def couette(rt, w):
    A = -w * R1**2 / (R2**2 - R1**2)
    B = w * R1**2 * R2**2 / (R2**2 - R1**2)
    return A * rt + B / rt


def fit_run(d, rpm):
    X, Y = np.meshgrid(d["x"], d["y"])
    U = d["u"] * FPS / PX_PER_MM    # mm/s, image y points down
    V = d["v"] * FPS / PX_PER_MM
    x, y = X / PX_PER_MM, Y / PX_PER_MM
    sp = np.hypot(U, V)
    good = (d["pr"] > 1.05) & np.isfinite(sp)

    # 1) rotation centre: velocity must be perpendicular to the radius vector
    m = good & (sp > 0.25 * np.nanmax(sp[good]))
    def resid(c):
        rx, ry = x[m] - c[0], y[m] - c[1]
        return (U[m] * rx + V[m] * ry) / (sp[m] * np.hypot(rx, ry))
    c = least_squares(resid, [x.mean(), -8.0]).x
    r = np.hypot(x - c[0], y - c[1])
    ut = np.abs((-(y - c[1]) * U + (x - c[0]) * V) / r)   # azimuthal speed

    # 2) the wall positions are unknown in the image, so fit the radial offset too:
    #    r_true = r + s, with Couette u = A r + B/r and walls at R1 (u=w R1) and R2 (u=0)
    w_set = rpm * 2 * np.pi / 60
    rr, uu = r[good].ravel(), ut[good].ravel()
    fit = least_squares(lambda p: couette(rr + p[0], p[1]) - uu, [R2 - rr.max(), w_set],
                        loss="soft_l1", f_scale=0.05)
    s, w_fit = fit.x
    rt = rr + s
    pred = couette(rt, w_fit)
    ss_res = np.sum((uu - pred) ** 2)
    r2 = 1 - ss_res / np.sum((uu - uu.mean()) ** 2)
    rmse = np.sqrt(ss_res / len(uu))

    # free two-parameter fit u = A r + B/r on the same shifted radii
    G = np.c_[rt, 1 / rt]
    (A_f, B_f), *_ = np.linalg.lstsq(G, uu, rcond=None)

    # binned profile
    edges = np.linspace(rt.min(), rt.max(), 16)
    idx = np.digitize(rt, edges) - 1
    ok = [i for i in range(15) if np.sum(idx == i) > 3]
    rb = np.array([rt[idx == i].mean() for i in ok])
    ub = np.array([uu[idx == i].mean() for i in ok])
    eb = np.array([uu[idx == i].std() for i in ok])
    nb = np.array([int(np.sum(idx == i)) for i in ok])

    res = dict(rpm=rpm, omega_set=w_set, omega_fit=w_fit, centre_mm=list(c),
               shift_mm=s, r_min=float(rt.min()), r_max=float(rt.max()),
               r2=r2, rmse=rmse, A_free=A_f, B_free=B_f, nvec=int(len(uu)),
               npairs=int(d["npairs"]),
               u_wall_set=w_set * R1, u_wall_fit=w_fit * R1,
               bins=dict(r=rb.tolist(), u=ub.tolist(), sd=eb.tolist(), n=nb.tolist()))
    return res, (rt, uu)


if __name__ == "__main__":
    o = sys.argv[1]
    res = {}
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    for k, (run, rpm) in enumerate(RUNS.items()):
        res[run], (rt, uu) = fit_run(np.load(f"{o}/{run}.npz"), rpm)
        r_ = res[run]
        rb, ub, eb = (np.array(r_["bins"][q]) for q in ("r", "u", "sd"))
        w_set, w_fit, r2 = r_["omega_set"], r_["omega_fit"], r_["r2"]
        ax = axs[k]
        ax.plot(rt, uu, ".", ms=2, alpha=0.3, color="0.6", label="PIV vectors")
        ax.errorbar(rb, ub, eb, fmt="o", color="C0", ms=4, capsize=2, label="binned mean ± SD")
        rg = np.linspace(R1, R2, 200)
        ax.plot(rg, couette(rg, w_set), "k--", label=f"Couette, set ω ({rpm} rpm)")
        ax.plot(rg, couette(rg, w_fit), "C3-", label=f"Couette fit, ω = {w_fit*60/2/np.pi:.2f} rpm")
        ax.axvspan(rt.min(), rt.max(), color="C0", alpha=0.06)
        ax.set_xlim(R1, R2); ax.set_ylim(0, None)
        ax.set_xlabel("r [mm]"); ax.set_ylabel(r"$u_\theta$ [mm/s]")
        ax.set_title(f"Run {k+1}: {rpm} rpm   (R² = {r2:.3f})")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{o}/couette_profiles.png", dpi=150)
    json.dump(res, open(f"{o}/results.json", "w"), indent=1, default=float)
    for k, v in res.items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items() if a != "bins"})

    if "--blocks" in sys.argv:
        blocks = {}
        for run, rpm in RUNS.items():
            fits = []
            for f in sorted(glob.glob(f"{o}/{run}_b*.npz")):
                fits.append(fit_run(np.load(f), rpm)[0])
            w = np.array([f["omega_fit"] for f in fits])
            t = np.arange(len(w))
            slope = np.polyfit(t, w, 1)[0] if len(w) > 2 else float("nan")
            blocks[run] = dict(rpm=rpm, omega_set=2 * np.pi * rpm / 60,
                               omega_blocks=w.tolist(), shift_blocks=[f["shift_mm"] for f in fits],
                               r2_blocks=[f["r2"] for f in fits], rmse_blocks=[f["rmse"] for f in fits],
                               nvec_blocks=[f["nvec"] for f in fits],
                               omega_mean=float(w.mean()), omega_sd=float(w.std(ddof=1)),
                               drift_per_block=float(slope),
                               drift_total_pct=float(100 * slope * (len(w) - 1) / w.mean()))
            print(run, "ω blocks", np.round(w, 4), "mean", round(w.mean(), 4), "SD", round(w.std(ddof=1), 4),
                  "drift/total %", round(blocks[run]["drift_total_pct"], 1))
        json.dump(blocks, open(f"{o}/blocks.json", "w"), indent=1, default=float)
