# -*- coding: utf-8 -*-
"""
D-study 결과 PNG 그림 생성.
입력: analysis/d-study/d_study_results.json
출력: research/assets/d-study/*.png (6 장)
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "analysis/d-study/d_study_results.json"
OUTDIR = ROOT / "research/assets/d-study"
OUTDIR.mkdir(parents=True, exist_ok=True)

with open(RESULTS) as f:
    R = json.load(f)

sweep = R["sweep"]
ablation = R["ablation"]
thresh = R["config"]["r_thresh"]

def cells(r):
    g = r["grid"]
    return g["n_av"] * g["n_g"] * g["n_sev"] * g["K"]

# 색·마커 약속
av_colors = {4: "#9a2f2f", 6: "#2f5d8a", 8: "#3f6b3f"}
sev_marker = {"uniform": "o", "adaptive": "^"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "figure.dpi": 130,
})

# ===== Fig 1 · 격자별 split r p25 (전체 162 점) =====
fig, ax = plt.subplots(figsize=(8, 5))
for r in sweep:
    g = r["grid"]
    ax.scatter(cells(r), r["split_r_p25"],
               s=28, alpha=0.75,
               c=av_colors[g["n_av"]],
               marker=sev_marker[r["sev_placement"]],
               edgecolors="none")
ax.axhline(thresh, ls="--", color="#444", lw=1, alpha=0.7)
ax.text(360, thresh + 0.005, f"pass threshold r = {thresh}", fontsize=9, color="#444")
ax.set_xscale("log")
ax.set_xlabel("grid size (cells = AV × G × severity × K)")
ax.set_ylabel("split-half b̂  Pearson r, 25 percentile")
ax.set_ylim(0.30, 1.00)
ax.set_title("Fig 1 · All 162 grid candidates pass r p25 ≥ 0.80")
# legend
from matplotlib.lines import Line2D
handles = [
    Line2D([0],[0], marker="o", color="w", markerfacecolor=av_colors[4], markersize=8, label="AV = 4"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor=av_colors[6], markersize=8, label="AV = 6"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor=av_colors[8], markersize=8, label="AV = 8"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor="#888", markersize=8, label="severity: uniform"),
    Line2D([0],[0], marker="^", color="w", markerfacecolor="#888", markersize=8, label="severity: adaptive"),
]
ax.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.9)
fig.tight_layout()
fig.savefig(OUTDIR / "fig1_p25_by_grid.png", bbox_inches="tight")
plt.close(fig)

# ===== Fig 2 · AV별 p25 boxplot =====
fig, ax = plt.subplots(figsize=(6, 4.2))
data = [[r["split_r_p25"] for r in sweep if r["grid"]["n_av"] == nav] for nav in [4, 6, 8]]
bp = ax.boxplot(data, labels=["AV = 4", "AV = 6", "AV = 8"], widths=0.5,
                patch_artist=True, medianprops=dict(color="#222", lw=1.5))
for patch, nav in zip(bp["boxes"], [4, 6, 8]):
    patch.set_facecolor(av_colors[nav])
    patch.set_alpha(0.65)
ax.axhline(thresh, ls="--", color="#444", lw=1, alpha=0.7)
ax.set_ylabel("split-half b̂  Pearson r, 25 percentile")
ax.set_ylim(0.78, 1.00)
ax.set_title("Fig 2 · r p25 distribution by AV count")
fig.tight_layout()
fig.savefig(OUTDIR / "fig2_p25_by_av.png", bbox_inches="tight")
plt.close(fig)

# ===== Fig 3 · ablation 막대 =====
# baseline: 합격 격자 중 ablation_target_grid에서 use_prior=True, K=10, adaptive
target = R["ablation_target_grid"]   # AV=4 G=3 sev=3 K=10
def find(use_prior, K, sev):
    cands = [r for r in sweep if r["grid"]["n_av"] == target["n_av"]
                                  and r["grid"]["n_g"] == target["n_g"]
                                  and r["grid"]["n_sev"] == target["n_sev"]
                                  and r["grid"]["K"] == K
                                  and r["sev_placement"] == sev
                                  and r["use_prior"] == use_prior]
    return cands[0] if cands else None

baseline = find(True, target["K"], "adaptive")
ab_prior_off = next(r for r in ablation if not r["use_prior"])
ab_half_k    = next(r for r in ablation if r["use_prior"] and r["grid"]["K"] < target["K"])

labels = [f"baseline\n(prior on, K={target['K']})",
          "prior OFF\n(K=K)",
          f"K/2  (K={ab_half_k['grid']['K']})\n(prior on)"]
values = [baseline["split_r_p25"], ab_prior_off["split_r_p25"], ab_half_k["split_r_p25"]]
colors = ["#3f6b3f", "#9a2f2f", "#8a6d1f"]

fig, ax = plt.subplots(figsize=(7, 4.2))
bars = ax.bar(range(3), values, color=colors, alpha=0.85, width=0.55)
ax.axhline(thresh, ls="--", color="#444", lw=1, alpha=0.7)
ax.text(2.45, thresh + 0.012, f"pass r = {thresh}", fontsize=9, color="#444", ha="right")
for i, v in enumerate(values):
    ax.text(i, v + 0.015, f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(range(3))
ax.set_xticklabels(labels)
ax.set_ylabel("split-half b̂  Pearson r, 25 percentile")
ax.set_ylim(0, 1.0)
ax.set_title(f"Fig 3 · Ablation at smallest grid (AV={target['n_av']}·G={target['n_g']}·sev={target['n_sev']})")
fig.tight_layout()
fig.savefig(OUTDIR / "fig3_ablation.png", bbox_inches="tight")
plt.close(fig)

# ===== Fig 4 · severity 배치 paired =====
fig, ax = plt.subplots(figsize=(6.5, 4.5))
pairs = {}
for r in sweep:
    g = r["grid"]
    key = (g["n_av"], g["n_g"], g["n_sev"], g["K"])
    pairs.setdefault(key, {})[r["sev_placement"]] = r["split_r_p25"]
u_vals, a_vals, colors_pt = [], [], []
for key, d in pairs.items():
    if "uniform" in d and "adaptive" in d:
        u_vals.append(d["uniform"])
        a_vals.append(d["adaptive"])
        colors_pt.append(av_colors[key[0]])
ax.scatter(u_vals, a_vals, c=colors_pt, alpha=0.75, s=30, edgecolors="none")
lo, hi = 0.78, 1.00
ax.plot([lo, hi], [lo, hi], ls="--", color="#444", lw=1, alpha=0.6, label="adaptive = uniform")
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
ax.set_xlabel("split r p25 (uniform severity)")
ax.set_ylabel("split r p25 (adaptive severity)")
ax.set_aspect("equal")
mean_diff = float(np.mean(np.array(a_vals) - np.array(u_vals)))
ax.set_title(f"Fig 4 · Adaptive vs uniform severity  (mean Δ = +{mean_diff:.3f})")
ax.legend(loc="lower right", fontsize=9)
fig.tight_layout()
fig.savefig(OUTDIR / "fig4_sev_placement.png", bbox_inches="tight")
plt.close(fig)

# ===== Fig 5 · MH DIF false-discovery rate vs AV (R-B 양적 증거) =====
fig, ax = plt.subplots(figsize=(6, 4.2))
data = [[r["split_mh_dif_rate"] for r in sweep if r["grid"]["n_av"] == nav] for nav in [4, 6, 8]]
bp = ax.boxplot(data, labels=["AV = 4", "AV = 6", "AV = 8"], widths=0.5,
                patch_artist=True, medianprops=dict(color="#222", lw=1.5))
for patch, nav in zip(bp["boxes"], [4, 6, 8]):
    patch.set_facecolor(av_colors[nav])
    patch.set_alpha(0.65)
ax.axhline(0.05, ls="--", color="#444", lw=1, alpha=0.7)
ax.text(3.4, 0.07, "nominal α = 0.05", fontsize=9, color="#444", ha="right")
ax.set_ylabel("Mantel-Haenszel DIF rate at α = 0.05")
ax.set_ylim(0, 1.0)
ax.set_title("Fig 5 · MH DIF false-discovery rate inflates at AV = 4 (R-B evidence)")
fig.tight_layout()
fig.savefig(OUTDIR / "fig5_mh_dif.png", bbox_inches="tight")
plt.close(fig)

# ===== Fig 6 · θ̂ CI 폭 vs cells (한계 노출) =====
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for r in sweep:
    g = r["grid"]
    ax.scatter(cells(r), r["theta_ci_width_mean"],
               s=28, alpha=0.7,
               c=av_colors[g["n_av"]],
               marker=sev_marker[r["sev_placement"]],
               edgecolors="none")
ax.set_xscale("log")
ax.set_xlabel("grid size (cells)")
ax.set_ylabel(r"mean $\theta$̂  95 percent Laplace CI width")
ax.set_title(r"Fig 6 · $\theta$̂  CI width far exceeds 0.5$\sigma$  (individual AV strength under-resolved)")
ax.legend(handles=handles, loc="upper right", fontsize=9, framealpha=0.9)
fig.tight_layout()
fig.savefig(OUTDIR / "fig6_theta_ci.png", bbox_inches="tight")
plt.close(fig)

print(">>> 6 figures saved to", OUTDIR)
for p in sorted(OUTDIR.glob("*.png")):
    print(f"  {p.name}  ({p.stat().st_size//1024} KB)")
