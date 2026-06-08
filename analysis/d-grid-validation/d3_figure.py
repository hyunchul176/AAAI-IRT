# -*- coding: utf-8 -*-
"""D3 본문 figure: 측정 모델 변종 ablation.

method.html 식 (6) P = u + (1-u)·σ(a·(β + γ_G·c − θ))의 세 구조(reactivity·
severity 조건화·avoidability 가중)를 하나씩 빼면 적합과 안정성이 어떻게 달라
지는지 본다. RQ3("세 구조가 vanilla IRT보다 적합·안정 개선") 본문 핵심 증거.

네 변종 (검토자 라운드 11·12 정정 후):
- full       : 모든 모수 자유. 본 측정 모델의 본형.
- no_severity: cc=0으로 강제. γ_G·c=0이 되어 σ(β−θ) 정적 IRT로 축소.
- g_common   : G를 모두 0으로 모음. G별 β·γ·a가 하나로 흡수되어 생성기 차이
               무시한 단일 IRT.
- u_zero     : u=0으로 fix. 회피불가 하한 무시 (현행 평가 관행).

세 panel:

(a) 변종별 LR statistic 2(NLL_v - NLL_full). 본형 대비 적합도 손실의 자릿수.
    df = 모수 차이라 χ² 임계값(p=0.05)을 reference로 둠.
(b) 변종별 split-half b̂ r 25 percentile. D2 합격선 ρ=0.80 위로 머무는 변종과
    떨어지는 변종을 가른다. 안정성 손실의 자릿수.
(c) 변종별 평균 θ posterior SE. 추정 정밀도 손실의 자릿수.

usage:
    python3 analysis/d-grid-validation/d3_figure.py
    python3 analysis/d-grid-validation/d3_figure.py --jsonl <responses.jsonl>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import (  # noqa: E402
    draw_true_params, simulate_responses,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d3_ablation import run_d3, VARIANTS  # noqa: E402
from d2_split_half import load_responses, build_resp_dict  # noqa: E402


plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.4,
})

PASS_LINE = 0.80   # D2 합격선


VARIANT_LABELS = {
    "full": "full\n(본 모델)",
    "no_severity": "no severity\n(γc 제거)",
    "g_common": "g_common\n(G 차이 무시)",
    "u_zero": "u_zero\n(회피불가 무시)",
}

VARIANT_LABELS_EN = {
    "full": "full\n(our model)",
    "no_severity": "no severity\n(remove γ·c)",
    "g_common": "g_common\n(merge G)",
    "u_zero": "u_zero\n(ignore u)",
}

# 변종별 모수 차이(df). LR χ² 자유도 산출 단계.
def variant_df(variant: str, n_av: int, n_g: int, n_sev: int) -> int:
    if variant == "full":
        return 0
    if variant == "no_severity":
        return n_g  # γ_G 항을 0 고정
    if variant == "g_common":
        return 4 * (n_g - 1)  # β·γ·a·u 각 G별 → 한 값 (df=12, u 포함)
    if variant == "u_zero":
        return n_g  # u_G 0 고정
    return 0


def panel_a_lrt(ax, result: dict, n_g: int) -> None:
    """LR statistic 막대 + χ² p=0.05 임계값 점선."""
    variants_no_full = [v for v in VARIANTS if v != "full"]
    lr = [result[v].get("lr_stat_vs_full", float("nan")) for v in variants_no_full]
    df = [variant_df(v, 0, n_g, 0) for v in variants_no_full]
    # χ² critical value (p=0.05) per df
    chi2_crit = [stats.chi2.ppf(0.95, max(d, 1)) for d in df]
    x = np.arange(len(variants_no_full))
    bars = ax.bar(x, lr, color=["#FFB454", "#5DAA7E", "#D04A4A"],
                  edgecolor="white", linewidth=0.5, alpha=0.8)
    # χ² 임계값 점선 (변종별 df 다르므로 점선 dot)
    ax.scatter(x, chi2_crit, marker="_", s=200, color="#444",
               linewidth=1.5, label=r"$\chi^2$ critical (p=0.05)")
    ax.set_xticks(x)
    ax.set_xticklabels([VARIANT_LABELS_EN[v] for v in variants_no_full])
    ax.set_ylabel(r"LR statistic  $2 \times (\mathrm{NLL}_v - \mathrm{NLL}_\mathrm{full})$")
    ax.set_title("(a) Likelihood ratio: variant vs full")
    ax.legend(loc="upper right", frameon=False)
    # 각 막대 위에 df 표기
    for xi, (lri, di) in enumerate(zip(lr, df)):
        if not np.isnan(lri):
            ax.text(xi, lri + max(lr) * 0.02 if max(lr) > 0 else 0.5,
                    f"df={di}", ha="center", va="bottom", fontsize=7, color="#444")


def panel_b_split_r(ax, result: dict) -> None:
    """변종별 split-half r p25. D2 합격선 표시."""
    p25 = [result[v].get("split_r_p25", float("nan")) for v in VARIANTS]
    r_mean = [result[v].get("split_r_mean", float("nan")) for v in VARIANTS]
    x = np.arange(len(VARIANTS))
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E", "#D04A4A"]
    ax.bar(x, p25, color=colors, edgecolor="white", linewidth=0.5, alpha=0.8,
           label="p25")
    # mean을 점으로
    ax.scatter(x, r_mean, marker="o", s=24, color="#222", zorder=5, label="mean")
    ax.axhline(PASS_LINE, color="#888", linestyle="--", linewidth=1.0,
               label=fr"pass criterion $\rho \geq {PASS_LINE}$")
    ax.set_xticks(x)
    ax.set_xticklabels([VARIANT_LABELS_EN[v] for v in VARIANTS])
    ax.set_ylabel(r"split-half $\hat{b}$ Pearson $r$")
    ax.set_ylim(0, 1.05)
    ax.set_title("(b) Sample invariance under variant ablation")
    ax.legend(loc="lower right", frameon=False)


def panel_c_se(ax, result: dict) -> None:
    """변종별 평균 SE(θ̂). 추정 정밀도 손실."""
    ci = [result[v].get("theta_ci_width", float("nan")) for v in VARIANTS]
    # CI width = 2 × 1.96 × SE이므로 SE로 환산
    se = [c / (2 * 1.96) if not np.isnan(c) else float("nan") for c in ci]
    x = np.arange(len(VARIANTS))
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E", "#D04A4A"]
    ax.bar(x, se, color=colors, edgecolor="white", linewidth=0.5, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([VARIANT_LABELS_EN[v] for v in VARIANTS])
    ax.set_ylabel(r"mean SE($\hat{\theta}$)")
    ax.set_title(r"(c) Robustness estimation precision (SE($\hat{\theta}$))")


def build_figure(result: dict, n_g: int, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    panel_a_lrt(axes[0], result, n_g)
    panel_b_split_r(axes[1], result)
    panel_c_se(axes[2], result)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".pdf"))
    fig.savefig(out_path.with_suffix(".png"))
    plt.close(fig)
    print(f">>> figure saved: {out_path.with_suffix('.pdf')}")
    print(f"                  {out_path.with_suffix('.png')}")


def run_synthetic(out_path: Path, n_splits: int = 30) -> None:
    """합성 응답으로 D3 ablation 적합 + figure 산출.

    AV=6 × G=3 × c=5 × K=20 합성 격자에서 fit_map의 변종별 적합을 돌리고,
    LR stat·split r p25·SE 자릿수를 figure로 그린다.
    """
    print(">>> synthetic AV=6 × G=3 × c=5 × K=20")
    rng = np.random.default_rng(42)
    true = draw_true_params(n_av=6, n_g=3, rng=rng)
    resp = simulate_responses(true, n_sev=5, K=20, sev_placement="uniform", rng=rng)
    result = run_d3(resp, n_splits=n_splits, seed=0)
    for v, d in result.items():
        print(f"   [{v}] r_p25={d.get('split_r_p25', float('nan')):.3f}  "
              f"SE_ci_width={d.get('theta_ci_width', float('nan')):.3f}  "
              f"LR vs full={d.get('lr_stat_vs_full', 0.0):.2f}")
    build_figure(result, n_g=resp["n_g"], out_path=out_path)


def run_real(jsonl_path: Path, out_path: Path, n_splits: int = 30) -> None:
    rows = load_responses(jsonl_path)
    resp = build_resp_dict(rows)
    print(f">>> 본 격자: AV={resp['n_av']} × G={resp['n_g']} × c={resp['n_sev']} × K={resp['K']}")
    result = run_d3(resp, n_splits=n_splits, seed=0)
    for v, d in result.items():
        print(f"   [{v}] r_p25={d.get('split_r_p25', float('nan')):.3f}  "
              f"SE_ci_width={d.get('theta_ci_width', float('nan')):.3f}  "
              f"LR vs full={d.get('lr_stat_vs_full', 0.0):.2f}")
    build_figure(result, n_g=resp["n_g"], out_path=out_path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", default=None)
    p.add_argument("--out", default="analysis/d-grid-validation/figures/d3_ablation")
    p.add_argument("--n-splits", type=int, default=30)
    args = p.parse_args()
    out_path = Path(args.out)
    if args.jsonl:
        run_real(Path(args.jsonl), out_path, args.n_splits)
    else:
        run_synthetic(out_path, args.n_splits)


if __name__ == "__main__":
    main()
