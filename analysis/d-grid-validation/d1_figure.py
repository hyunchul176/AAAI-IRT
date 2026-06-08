# -*- coding: utf-8 -*-
"""D1 본문 figure: 단일 충돌률 기반 AV 순위의 시나리오 부분집합 의존성.

본문 핵심 figure 가운데 하나. plan §13 첫째 기여(SUT-불변 측정)의 가장 직접적인
"문제 재현" 증거. method.html 식 (7) 충돌률 r_s가 "난이도 × 잰 사람"을 섞어
시나리오 집합에 따라 흔들린다는 사실을 시각화한 결과. D2 figure(우리 측정 모델이
그 흔들림을 해소)와 대비점으로 본문에 박힌다.

세 panel:

(a) AV 순위 Spearman ρ 분포 (50회 시나리오 split). 시나리오 부분집합을 두 갈래로
    무작위 split한 뒤 각 갈래에서 AV별 평균 충돌률로 응시자 순위를 매기고, 두
    순위의 ρ를 50회 모은 분포. ρ가 1.0에서 떨어질수록 시나리오 의존성이 크다.
(b) 한 split의 AV별 평균 충돌률 (cr_A vs cr_B) scatter. 응시자 충돌률 자체가
    시나리오 부분집합에 어떻게 흔들리는지 직접 보임. 점들이 y=x에서 벗어나는
    정도가 SUT 의존성의 크기.
(c) Top-half disagreement 분포 (50회 split). 두 갈래에서 상위 절반 응시자 명단이
    얼마나 다른지 비율. 0이면 두 갈래에서 같은 응시자가 항상 상위 절반, 0.5이면
    절반이 뒤바뀌는 사례 (Shen 2025의 순위 역전 현상).

D2 figure와 panel 구조를 일치시켜 본문에서 RQ1(문제 재현) → RQ2(우리 모델 해소)
대비가 한눈에 보이도록 했다.

usage:
    python3 analysis/d-grid-validation/d1_figure.py
    python3 analysis/d-grid-validation/d1_figure.py --jsonl <responses.jsonl>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d1_rank_reversal import (  # noqa: E402
    build_av_scenario_matrix, load_responses,
)


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


# RQ1 본문 자릿수 anchor: Spearman ρ가 1.0에서 떨어진 정도가 SUT 의존성의 크기.
# Shen 2025·LD-Scene Table 4가 보인 자릿수와 자릿수 일치 비교가 본문 흐름.
STABLE_LINE = 0.80  # 비교 anchor: ρ 0.8 위가 비교적 안정, 아래가 흔들리는 영역


def synthesize_av_scenario(n_av: int, n_scen: int, sut_dep: float = 0.0,
                           seed: int = 42) -> np.ndarray:
    """합성 AV × scenario 충돌률 매트릭스.

    SUT 의존성을 (AV, scenario) 쌍 위에 효과적 강건성 흔들림으로 명시한다.
    sut_dep가 클수록 응시자가 시나리오에 따라 다른 실력을 보이는 신호 : Shen
    2025·LD-Scene이 보인 순위 역전 현상을 합성에서 재현하는 흐름.

        θ_eff(i, j) = θ_base(i) + ε_{ij},  ε_{ij} ~ N(0, sut_dep)

    sut_dep=0이면 1차원 IRT 가정 그대로(응시자 i의 실력이 시나리오 j와 무관).
    sut_dep가 커질수록 시나리오 부분집합 split에서 AV 순위가 흔들린다.
    """
    rng = np.random.default_rng(seed)
    theta_base = rng.normal(0, 0.5, n_av)
    b = rng.normal(0, 1.0, n_scen)
    eps = rng.normal(0, sut_dep, (n_av, n_scen)) if sut_dep > 0 else np.zeros((n_av, n_scen))
    M = np.zeros((n_av, n_scen))
    for i in range(n_av):
        for j in range(n_scen):
            theta_eff = theta_base[i] + eps[i, j]
            p = 1 / (1 + np.exp(-(b[j] - theta_eff)))
            M[i, j] = float(rng.binomial(20, p) / 20.0)
    return M


def collect_rank_metrics(M: np.ndarray, n_splits: int = 50,
                        seed: int = 0) -> dict:
    """50회 시나리오 split → 순위 일치 메트릭 모음."""
    rng = np.random.default_rng(seed)
    n_av, n_scen = M.shape
    rhos: list[float] = []
    tops: list[float] = []
    scatter_pair = None
    for s in range(n_splits):
        perm = rng.permutation(n_scen)
        half_a = perm[: n_scen // 2]; half_b = perm[n_scen // 2:]
        cr_a = np.nanmean(M[:, half_a], axis=1)
        cr_b = np.nanmean(M[:, half_b], axis=1)
        if np.isnan(cr_a).any() or np.isnan(cr_b).any():
            continue
        rho, _ = stats.spearmanr(cr_a, cr_b)
        rhos.append(float(rho))
        # top-half disagreement
        rank_a = np.argsort(-cr_a)[: n_av // 2]
        rank_b = np.argsort(-cr_b)[: n_av // 2]
        disagree = 1.0 - len(set(rank_a.tolist()) & set(rank_b.tolist())) / max(len(rank_a), 1)
        tops.append(float(disagree))
        if s == 0:
            scatter_pair = (cr_a.copy(), cr_b.copy())
    return dict(rhos=np.array(rhos), tops=np.array(tops), scatter=scatter_pair)


def panel_a_rho(ax, results: dict) -> None:
    """50회 시나리오 split의 Spearman ρ 분포. 격자 셋 겹쳐."""
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E"]
    labels = []
    for (key, res), color in zip(results.items(), colors):
        rhos = res["rhos"]
        p25 = np.percentile(rhos, 25)
        ax.hist(rhos, bins=20, alpha=0.55, color=color, edgecolor="white",
                linewidth=0.5,
                label=f"{key}  (mean = {rhos.mean():.2f}, p25 = {p25:.2f})")
        labels.append(key)
    ax.axvline(STABLE_LINE, color="#888", linestyle="--", linewidth=1.0,
               label=fr"reference $\rho = {STABLE_LINE}$")
    ax.set_xlim(-0.1, 1.05)
    ax.set_xlabel(r"AV rank Spearman $\rho$  (50 scenario splits)")
    ax.set_ylabel("frequency")
    ax.set_title("(a) AV ranking instability under scenario subset shift")
    ax.legend(loc="upper left", frameon=False)


def panel_b_scatter(ax, scatter_a: np.ndarray, scatter_b: np.ndarray) -> None:
    """한 split의 AV별 평균 충돌률 cr_A vs cr_B scatter. y=x 이탈이 SUT 의존성."""
    ax.scatter(scatter_a, scatter_b, s=42, alpha=0.75, color="#5B8DEF",
               edgecolor="white", linewidth=0.5)
    lo = min(scatter_a.min(), scatter_b.min()) - 0.05
    hi = max(scatter_a.max(), scatter_b.max()) + 0.05
    ax.plot([lo, hi], [lo, hi], color="#888", linestyle=":", linewidth=1.0,
            label="y = x")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(r"AV collision rate (scenario subset A)")
    ax.set_ylabel(r"AV collision rate (scenario subset B)")
    ax.set_title(r"(b) Per-AV collision rate shifts across scenario subsets")
    ax.legend(loc="upper left", frameon=False)
    ax.set_aspect("equal", "box")


def panel_c_top_disagree(ax, results: dict) -> None:
    """Top-half disagreement 분포 (응시자 상위 절반이 두 갈래 다른 비율)."""
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E"]
    for (key, res), color in zip(results.items(), colors):
        tops = res["tops"]
        ax.hist(tops, bins=15, alpha=0.55, color=color, edgecolor="white",
                linewidth=0.5,
                label=f"{key}  (mean = {tops.mean():.2f})")
    ax.set_xlim(-0.02, 0.62)
    ax.set_xlabel("top-half AV disagreement  (50 splits)")
    ax.set_ylabel("frequency")
    ax.set_title("(c) Top-half AV identity shifts across subsets")
    ax.legend(loc="upper right", frameon=False)


def build_figure(results: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    panel_a_rho(axes[0], results)
    # 두 번째 panel은 가장 흔들림 큰 격자(ρ p25가 가장 낮은 항목)에서 scatter
    worst_key = min(results, key=lambda k: np.percentile(results[k]["rhos"], 25))
    sp = results[worst_key]["scatter"]
    panel_b_scatter(axes[1], sp[0], sp[1])
    axes[1].set_title(rf"(b) Per-AV collision rate shifts ({worst_key})")
    panel_c_top_disagree(axes[2], results)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".pdf"))
    fig.savefig(out_path.with_suffix(".png"))
    plt.close(fig)
    print(f">>> figure saved: {out_path.with_suffix('.pdf')}")
    print(f"                  {out_path.with_suffix('.png')}")


def run_synthetic(out_path: Path, n_splits: int = 50) -> None:
    """합성 격자 셋에서 noise 값을 달리 둬 SUT 의존성 자릿수 차이를 보임.

    - "no SUT bias": noise=0. 시나리오 의존 흔들림 없음 → ρ ≈ 1.0
    - "moderate SUT bias": noise=0.5. 일부 시나리오에서 응시자 실력 흔들림
    - "strong SUT bias": noise=1.0. 시나리오 부분집합에 따라 순위 뒤집힘
    """
    settings = [
        ("no SUT dependency", 0.0),
        ("moderate (sut_dep=1.0)", 1.0),
        ("strong (sut_dep=2.0)", 2.0),
    ]
    results = {}
    for label, sd in settings:
        print(f">>> synthetic {label}")
        M = synthesize_av_scenario(n_av=6, n_scen=40, sut_dep=sd, seed=42)
        res = collect_rank_metrics(M, n_splits=n_splits, seed=0)
        results[label] = res
        print(f"    ρ mean = {res['rhos'].mean():.3f}, p25 = {np.percentile(res['rhos'], 25):.3f}")
        print(f"    top-half disagree mean = {res['tops'].mean():.3f}")
    build_figure(results, out_path)


def run_real(jsonl_path: Path, out_path: Path, n_splits: int = 50) -> None:
    rows = load_responses(jsonl_path)
    print(f">>> 본 격자 응답 {len(rows)} rows")
    M, av_list, scen_list = build_av_scenario_matrix(rows)
    print(f">>> AV × scenario: {M.shape[0]} × {M.shape[1]}, AV={av_list}")
    res = collect_rank_metrics(M, n_splits=n_splits, seed=0)
    print(f"    ρ mean = {res['rhos'].mean():.3f}, p25 = {np.percentile(res['rhos'], 25):.3f}")
    print(f"    top-half disagree mean = {res['tops'].mean():.3f}")
    results = {f"real grid (AV={M.shape[0]}, n_scen={M.shape[1]})": res}
    build_figure(results, out_path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", default=None)
    p.add_argument("--out", default="analysis/d-grid-validation/figures/d1_rank_reversal")
    p.add_argument("--n-splits", type=int, default=50)
    args = p.parse_args()
    out_path = Path(args.out)
    if args.jsonl:
        run_real(Path(args.jsonl), out_path, args.n_splits)
    else:
        run_synthetic(out_path, args.n_splits)


if __name__ == "__main__":
    main()
