# EN309 G6: Couette viscometer PIV, session handoff (2026-10-14)

## Experiment
Objective: find the viscosity of a fluid using concentric-cylinder Couette flow, PIV and torque from a load cell.

| Item | Value | Source |
|---|---|---|
| Fluid | 88 : 12 glycerine : water (assumed wt%) | user |
| Seeding | 10 µm hollow spheres, about the same density as water | user |
| Temperature | about 24 °C | user |
| Reference viscosity | **126 mPa·s** (Cheng 2008 correlation; 145 at 22 °C, 111 at 26 °C) | computed |
| Inner (rotating) radius R1 | 6.0 mm, length 60 mm | Inner_cylinder.step / .stl |
| Outer (fixed) bore R2 | 11.0 mm (outer OD 32 mm, part height 72.5 mm) | Outer_cylinder.step / .stl |
| Camera | Phantom VEO 710L, 1280×800, 16-bit TIFF, 100 fps | .chd / folder names |
| Run 1 | `1_100fps_2pt14rpm`: 2.14 rpm, 4001 frames | |
| Run 2 | `2_100fps_4pt3rpm`: 4.3 rpm, 2501 frames | |
| Scale | 161.9 px per grid square, assumed 1 mm, so 6.18 µm/px and a 7.9 × 4.9 mm field of view | scale_000177.tif, FFT of grid |
| Note | slight leaks during the runs | user |

Image orientation: the rotating inner cylinder is just above the top edge of the frame. The fixed outer wall is near the bottom, where the speed falls to 0.

## Method (scripts in this folder)
1. `piv.py`: ensemble-correlation PIV. 64 px windows on a 32 px grid, frame separation dt = 3 frames, about 800 pairs per run.
   - The temporal-mean background is subtracted and both images and correlation planes get a Gaussian blur (σ = 1).
   - This matters: the camera's fixed-pattern noise produced a spike at zero displacement that ruined run 2 (see `out/diag2.png`).
2. `analyse.py`:
   - Fits the rotation centre so the vectors are perpendicular to the radius, then converts to u_θ(r).
   - Fits the Couette solution u = A·r + B/r, with A = −ωR1²/(R2²−R1²) and B = ωR1²R2²/(R2²−R1²).
   - Free parameters are ω_eff and a radial shift that pins u = 0 at R2.
   - The radius from the curvature fit alone is about 1.4 mm out, which is within the curvature uncertainty.
   - Writes `out/results.json` and `out/couette_profiles.png`.

Commands (from `G6_EN309/`, Python with numpy, scipy, pillow, matplotlib, openpyxl):
```
python analysis/piv.py 1_100fps_2pt14rpm 1 analysis/out/run1.npz 0 4000 5 3
python analysis/piv.py 2_100fps_4pt3rpm 2 analysis/out/run2.npz 0 2500 3 3
python analysis/analyse.py analysis/out
```
Each PIV run takes about 1–2 minutes.

## Results so far
| | Run 1 | Run 2 |
|---|---|---|
| Set ω | 0.224 rad/s (2.14 rpm) | 0.450 rad/s (4.3 rpm) |
| Fitted ω_eff | 0.155 rad/s (1.48 rpm) | 0.359 rad/s (3.43 rpm) |
| ω_eff / ω_set | 0.69 | 0.80 |
| Inner-wall speed, set → fitted | 1.34 → 0.93 mm/s | 2.70 → 2.15 mm/s |
| Couette fit R² / RMSE | 0.995 / 0.019 mm/s | 0.984 / 0.065 mm/s |
| Vectors used | 936 | 929 |

- The profile shape matches circular Couette flow well in both runs.
- The measured speed is 20–30 % below the set rpm. Possible causes:
  - the actual motor speed is lower than the label
  - 3-D or end effects: fluid level falling from the leaks, or the laser sheet not at mid-height
  - PIV bias against the velocity gradient, plus about 1 mm of extrapolation to the unseen inner wall
  - the scale image may not have been taken through the fluid and wall, so refraction can change the scale
- The streaks are wavy, which points to vibration or wobble of the inner cylinder (stepper motor?).
- Re = ρωR1(R2−R1)/μ ≈ 1230 × 1.34e-3 × 5e-3 / 0.126 ≈ 0.07, so the flow is laminar and far below the Taylor instability.

## Important: viscosity
A Newtonian Couette velocity profile does not depend on μ, so PIV alone can't give viscosity. Viscosity needs the load-cell torque:

**μ = T (R2² − R1²) / (4π L ω R1² R2²)**, where L is the wetted length.

- The leaks reduce L.
- There is no torque data in the folder yet. Get the load-cell readings and wetted fluid height from the group.
- Expected torque at μ = 0.126 Pa·s for L = 60 mm: about 1.1 µN·m at 2.14 rpm and 2.2 µN·m at 4.3 rpm. That's very small, so check the load cell's resolution.

## Remaining TODO
1. Run PIV on 4 time blocks per run to get error bars on ω_eff and check for drift caused by the leaks. This was the step in progress.
2. Confirm the grid square is 1 mm, and whether the scale image was taken through the filled cell.
3. Get the torque readings and wetted length, then compute μ and compare with 126 mPa·s.
4. Build the results workbook in the `en309_exp1` style: parameters, binned profiles, fit summary, and blue input cells for torque that compute μ.
