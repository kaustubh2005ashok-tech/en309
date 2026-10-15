"""Build G6_EN309_results.xlsx from out/collapse.json + out/blocks.json (run analyse.py --blocks, then collapse.py).

usage (from G6_EN309/):  python analysis/make_workbook.py
Blue cells are inputs; black cells are formulas. No torque data: the outer cylinder is fixed, so mu is not computed.
"""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

HERE = Path(__file__).parent
OUT = HERE / "out"
res = json.load(open(OUT / "collapse.json"))   # averaged-field fits, all frames
blk = json.load(open(OUT / "blocks.json"))

BLUE = Font(name="Arial", color="0000FF")
BLK = Font(name="Arial")
BOLD = Font(name="Arial", bold=True)
HDR = Font(name="Arial", bold=True, color="FFFFFF")
HFILL = PatternFill("solid", fgColor="1F3864")
INFILL = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = Workbook()


def header(ws, row, labels, col=1):
    for j, t in enumerate(labels):
        c = ws.cell(row, col + j, t)
        c.font, c.fill, c.border = HDR, HFILL, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def put(ws, ref, v, font=BLK, fmt=None, fill=None):
    c = ws[ref]
    c.value, c.font, c.border = v, font, BOX
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    return c


# ---------------------------------------------------------------- Parameters
ws = wb.active
ws.title = "Parameters"
ws["A1"].value, ws["A1"].font = "EN309 G6: Couette viscometer, PIV analysis", Font(name="Arial", bold=True, size=14)
header(ws, 3, ["Parameter", "Value", "Unit", "Source / note"])
params = [
    ("Fluid", "88:12 glycerine:water (wt%, assumed)", "", "user"),
    ("Temperature", 24, "°C", "approx."),
    ("Reference viscosity (not used)", 126, "mPa·s", "Cheng 2008, assumes wt%; mixing may have been by parts/volume. No torque, so μ is not computed"),
    ("Density", 1230, "kg/m³", "approx. for 88 wt% glycerine"),
    ("Inner (rotating) radius R1", 6.0, "mm", "Inner_cylinder.step"),
    ("Outer (fixed) radius R2", 11.0, "mm", "Outer_cylinder.step"),
    ("Inner cylinder length", 60.0, "mm", "Inner_cylinder.step"),
    ("Camera frame rate", 100, "fps", "Phantom VEO 710L"),
    ("Image scale", 161.9, "px/mm", "calibration grid, assumed 1 mm squares"),
    ("PIV window / grid", "64 px / 32 px", "", "ensemble correlation, dt = 3 frames"),
]
for i, (a, b, c, d) in enumerate(params, start=4):
    put(ws, f"A{i}", a)
    put(ws, f"B{i}", b, BLUE if not isinstance(b, str) else BLK)
    put(ws, f"C{i}", c)
    put(ws, f"D{i}", d)
# row map: B8 = R1, B9 = R2, B6 = reference viscosity
ws["A15"].value, ws["A15"].font = "Runs", BOLD
header(ws, 16, ["Run", "Set speed [rpm]", "Set ω [rad/s]", "Frames", "Blocks"])
for i, (k, n, nb) in enumerate([("Run 1", 4001, "4 × 1000 (step 3)"), ("Run 2", 2501, "4 × 625 (step 2)")], start=17):
    r = res[f"run{i-16}"]
    put(ws, f"A{i}", k)
    put(ws, f"B{i}", r["rpm"], BLUE, "0.00")
    put(ws, f"C{i}", f"=B{i}*2*PI()/60", BLK, "0.0000")
    put(ws, f"D{i}", n)
    put(ws, f"E{i}", nb)
ws["A20"].value = "Blue = input, black = formula. Slight leaks occurred during both runs."
ws["A20"].font = Font(name="Arial", italic=True)
for col, w in zip("ABCD", (30, 34, 14, 60)):
    ws.column_dimensions[col].width = w
ws.column_dimensions["E"].width = 20

# ---------------------------------------------------------------- Profiles
wp = wb.create_sheet("Profiles")
wp["A1"].value, wp["A1"].font = "Binned azimuthal velocity u_θ(r), averaged field of all frames", BOLD
col = 1
for run in ("run1", "run2"):
    b = res[run]["bins"]
    wp.cell(3, col, f"Run {run[-1]} ({res[run]['rpm']} rpm)").font = BOLD
    header(wp, 4, ["r [mm]", "u_θ [mm/s]", "SD [mm/s]", "N vectors", "Couette fit [mm/s]"], col)
    for i, (r_, u_, s_, n_) in enumerate(zip(b["r"], b["u"], b["sd"], b["n"]), start=5):
        L = lambda k: wp.cell(i, col + k).coordinate
        for k, v, f in ((0, r_, "0.000"), (1, u_, "0.0000"), (2, s_, "0.0000"), (3, n_, "0")):
            c = wp.cell(i, col + k, v)
            c.font, c.number_format, c.border = BLK, f, BOX
        # u = A r + B/r with ω = fitted ω_eff (Fit summary sheet)
        wcell = f"'Fit summary'!{'B' if run == 'run1' else 'C'}5"
        c = wp.cell(i, col + 4,
                    f"={wcell}*(Parameters!$B$8^2*Parameters!$B$9^2/{L(0)}-Parameters!$B$8^2*{L(0)})"
                    f"/(Parameters!$B$9^2-Parameters!$B$8^2)")
        c.font, c.number_format, c.border = BLK, "0.0000", BOX
    for k, w in enumerate((10, 13, 11, 11, 18)):
        wp.column_dimensions[wp.cell(1, col + k).column_letter].width = w
    col += 6

# ---------------------------------------------------------------- Fit summary
wf = wb.create_sheet("Fit summary")
wf["A1"].value, wf["A1"].font = "Couette fit u = A·r + B/r (ω_eff and radial shift fitted)", BOLD
header(wf, 3, ["Quantity", "Run 1", "Run 2", "Unit"])
put(wf, "A4", "Set ω"); put(wf, "D4", "rad/s")
put(wf, "A5", "Averaged-field fitted ω_eff"); put(wf, "D5", "rad/s")
put(wf, "A6", "Block-mean ω_eff (used for μ)", BOLD); put(wf, "D6", "rad/s")
put(wf, "A7", "Block SD of ω_eff"); put(wf, "D7", "rad/s")
put(wf, "A8", "SD / mean"); put(wf, "D8", "%")
put(wf, "A9", "ω_eff / ω_set"); put(wf, "D9", "–")
put(wf, "A10", "Drift over run (linear fit)"); put(wf, "D10", "% of mean")
put(wf, "A11", "Fitted ω_eff"); put(wf, "D11", "rpm")
put(wf, "A12", "Inner-wall speed, set"); put(wf, "D12", "mm/s")
put(wf, "A13", "Inner-wall speed, fitted"); put(wf, "D13", "mm/s")
put(wf, "A14", "Radial shift"); put(wf, "D14", "mm")
put(wf, "A15", "Couette fit R² (averaged field)"); put(wf, "D15", "–")
put(wf, "A16", "Couette fit RMSE (averaged field)"); put(wf, "D16", "mm/s")
put(wf, "A17", "Vectors used (averaged field)"); put(wf, "D17", "–")
for run, colL in (("run1", "B"), ("run2", "C")):
    r, bk = res[run], blk[run]
    put(wf, f"{colL}4", f"=Parameters!C{17 if run == 'run1' else 18}", BLK, "0.0000")
    put(wf, f"{colL}5", r["omega_fit"], BLK, "0.0000")
    put(wf, f"{colL}6", f"=AVERAGE({colL}22:{colL}25)", BOLD, "0.0000")
    put(wf, f"{colL}7", f"=STDEV({colL}22:{colL}25)", BLK, "0.0000")
    put(wf, f"{colL}8", f"={colL}7/{colL}6*100", BLK, "0.0")
    put(wf, f"{colL}9", f"={colL}6/{colL}4", BLK, "0.000")
    put(wf, f"{colL}10", f"=SLOPE({colL}22:{colL}25,$A$22:$A$25)*3/{colL}6*100", BLK, "0.0")
    put(wf, f"{colL}11", f"={colL}6*60/(2*PI())", BLK, "0.000")
    put(wf, f"{colL}12", f"={colL}4*Parameters!$B$8", BLK, "0.000")
    put(wf, f"{colL}13", f"={colL}6*Parameters!$B$8", BLK, "0.000")
    put(wf, f"{colL}14", r["shift_mm"], BLK, "0.000")
    put(wf, f"{colL}15", r["r2"], BLK, "0.0000")
    put(wf, f"{colL}16", r["rmse"], BLK, "0.0000")
    put(wf, f"{colL}17", r["nvec"], BLK, "0")
wf["A20"].value, wf["A20"].font = "Time-block fits (drift check: leaks)", BOLD
header(wf, 21, ["Block", "Run 1 ω_eff [rad/s]", "Run 2 ω_eff [rad/s]", "Run 1 R²", "Run 2 R²"])
for b in range(4):
    i = 22 + b
    put(wf, f"A{i}", b)
    put(wf, f"B{i}", blk["run1"]["omega_blocks"][b], BLK, "0.0000")
    put(wf, f"C{i}", blk["run2"]["omega_blocks"][b], BLK, "0.0000")
    put(wf, f"D{i}", blk["run1"]["r2_blocks"][b], BLK, "0.000")
    put(wf, f"E{i}", blk["run2"]["r2_blocks"][b], BLK, "0.000")
wf["A27"].value = ("Block 0..3 = successive quarters of each run. Run 1: 1000-frame blocks; "
                   "run 2: 625-frame blocks. Drift = slope × 3 blocks / mean.")
wf["A27"].font = Font(name="Arial", italic=True)
for col_, w in zip("ABCDE", (34, 20, 20, 12, 12)):
    wf.column_dimensions[col_].width = w

# ---------------------------------------------------------------- Linearity & collapse
wv = wb.create_sheet("Linearity & collapse")
wv["A1"].value, wv["A1"].font = "Couette fit, linear regression and u_θ/Ω collapse", Font(name="Arial", bold=True, size=13)
header(wv, 3, ["Quantity", "Run 1", "Run 2", "Unit"])
lin = [("Couette fit R²", "r2_couette", "0.0000", "–"), ("Couette fit RMSE", "rmse_couette", "0.0000", "mm/s"),
       ("Linear fit R² (u = a + b r)", "r2_linear", "0.0000", "–"), ("Linear fit RMSE", "rmse_linear", "0.0000", "mm/s"),
       ("Linear slope b", "lin_slope", "0.0000", "1/s"), ("Linear intercept a", "lin_intercept", "0.000", "mm/s")]
for i, (t, key, f, u) in enumerate(lin, start=4):
    put(wv, f"A{i}", t); put(wv, f"D{i}", u)
    put(wv, f"B{i}", res["run1"][key], BLK, f); put(wv, f"C{i}", res["run2"][key], BLK, f)
put(wv, "A10", "Linear RMSE / Couette RMSE"); put(wv, "D10", "–")
put(wv, "B10", "=B7/B5", BLK, "0.00"); put(wv, "C10", "=C7/C5", BLK, "0.00")
put(wv, "A11", "Set Ω"); put(wv, "D11", "rad/s")
put(wv, "A12", "Fitted ω_eff, own radial shift"); put(wv, "D12", "rad/s")
put(wv, "A13", "Fitted ω_eff, shared radial shift"); put(wv, "D13", "rad/s")
put(wv, "A14", "ω_eff / Ω_set (own shift)"); put(wv, "D14", "–")
for colL, run in (("B", "run1"), ("C", "run2")):
    put(wv, f"{colL}11", f"='Fit summary'!{colL}4", BLK, "0.0000")
    put(wv, f"{colL}12", res[run]["omega_fit"], BLK, "0.0000")
    put(wv, f"{colL}13", res["joint"]["omega_" + run], BLK, "0.0000")
    put(wv, f"{colL}14", f"={colL}12/{colL}11", BLK, "0.000")
put(wv, "A15", "Shared radial shift"); put(wv, "B15", res["joint"]["shift_mm"], BLK, "0.00"); put(wv, "D15", "mm")
put(wv, "A16", "Collapse rms spread, u/Ω_set"); put(wv, "B16", res["collapse_omega_set_rms_pct"], BLK, "0.0"); put(wv, "D16", "%")
put(wv, "A17", "Collapse rms spread, u/ω_eff"); put(wv, "B17", res["collapse_omega_fit_rms_pct"], BLK, "0.0"); put(wv, "D17", "%")
wv["A19"].value = ("Linear check: the gap is 5 mm against R1 = 6 mm (gap/R1 ≈ 0.8), so it is not a narrow gap and the exact profile "
                   "is curved; a straight line is a worse fit than the Couette form (higher RMSE). Collapse: spread is the rms difference "
                   "between the two runs' u/Ω on r = 7 to 11 mm divided by mean u/Ω.")
wv["A19"].font = Font(name="Arial", italic=True)
wv["A19"].alignment = Alignment(wrap_text=True, vertical="top")
wv.merge_cells("A19:D23")
for col_, w in zip("ABCD", (40, 14, 14, 10)):
    wv.column_dimensions[col_].width = w

# ---------------------------------------------------------------- Summary
wsu = wb.create_sheet("Summary", 0)
wsu["A1"].value, wsu["A1"].font = "EN309 G6 Couette PIV: summary of results", Font(name="Arial", bold=True, size=14)
header(wsu, 3, ["Result", "Run 1", "Run 2", "Unit"])
summ = [
    ("Set speed", "=Parameters!B17", "=Parameters!B18", "rpm", "0.00"),
    ("Set Ω", "='Fit summary'!B4", "='Fit summary'!C4", "rad/s", "0.0000"),
    ("ω_eff, block mean", "='Fit summary'!B6", "='Fit summary'!C6", "rad/s", "0.0000"),
    ("ω_eff, block SD", "='Fit summary'!B7", "='Fit summary'!C7", "rad/s", "0.0000"),
    ("ω_eff / Ω_set", "='Fit summary'!B9", "='Fit summary'!C9", "–", "0.000"),
    ("Drift over run", "='Fit summary'!B10", "='Fit summary'!C10", "% of mean", "0.0"),
    ("ω_eff, averaged field", "='Fit summary'!B5", "='Fit summary'!C5", "rad/s", "0.0000"),
    ("Radial shift to fit wall position", "='Fit summary'!B14", "='Fit summary'!C14", "mm", "0.00"),
    ("Couette fit R²", "='Linearity & collapse'!B4", "='Linearity & collapse'!C4", "–", "0.0000"),
    ("Couette fit RMSE", "='Linearity & collapse'!B5", "='Linearity & collapse'!C5", "mm/s", "0.0000"),
    ("Linear fit R²", "='Linearity & collapse'!B6", "='Linearity & collapse'!C6", "–", "0.0000"),
    ("Linear fit RMSE", "='Linearity & collapse'!B7", "='Linearity & collapse'!C7", "mm/s", "0.0000"),
    ("Collapse spread, u/Ω_set (both runs)", "='Linearity & collapse'!B16", None, "%", "0.0"),
    ("Collapse spread, u/ω_eff (both runs)", "='Linearity & collapse'!B17", None, "%", "0.0"),
]
for i, (t, b_, c_, u, f) in enumerate(summ, start=4):
    put(wsu, f"A{i}", t); put(wsu, f"B{i}", b_, BLK, f); put(wsu, f"C{i}", c_, BLK, f); put(wsu, f"D{i}", u)
wsu["A19"].value = ("Viscosity is not computed: the outer cylinder is fixed, so there is no torque reading. "
                    "The profile shape matches Couette flow, but the speed is below the set rpm in both runs.")
wsu["A19"].font = Font(name="Arial", italic=True)
wsu["A19"].alignment = Alignment(wrap_text=True, vertical="top")
wsu.merge_cells("A19:D21")
for col_, w in zip("ABCD", (40, 14, 14, 12)):
    wsu.column_dimensions[col_].width = w

# ---------------------------------------------------------------- Plot
wi = wb.create_sheet("Plot")
wi["A1"].value, wi["A1"].font = "u_θ(r)/Ω collapse of the two runs", BOLD
img = Image(str(OUT / "collapse.png"))
img.width, img.height = img.width * 0.6, img.height * 0.6
wi.add_image(img, "A3")

dest = HERE / "G6_EN309_results.xlsx"
wb.save(dest)
print("wrote", dest)
