# -*- coding: utf-8 -*-
"""D2 trial-split 변형 분석.

표준 D2 split-half 검정은 응시자 부분집합을 무작위 분리하여 b̂ 추정의 응시자 표본
의존성을 검증한다. 본 격자의 응시자 수(N=3~5)는 split의 자유도가 작아 표준 검정의
통계 검정력이 부족한 상태로 진단되었다. 본 trial-split 변형은 각 (av_id, g_id, c)
cell의 K episode를 무작위 35 vs 35로 분리하여 두 부분집합 각각에서 (g_id, c) 단위
충돌률을 산출하고 두 충돌률 매트릭스의 Pearson r을 비교한다. 본 변형은 b(G, c)
추정의 trial 표본 의존성을 검증하는 자료이며, 응시자 표본불변성(specific objectivity)
의 직접 검증과는 다른 통계량이지만 응시자 N이 작은 격자에서 b̂의 표본 안정성을
가늠하는 보조 자료로 사용한다.

usage:
    python3 analysis/highway_grid/d2_trial_split.py \\
        --jsonl analysis/highway_grid/responses_def_rl_combined.jsonl \\
        --n-splits 50
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats


PASS_LINE = 0.80

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


def load_cells(jsonl_path: Path) -> dict:
    """{(av_id, g_id, c): [y_0, y_1, ..., y_{K-1}]} 구조로 응답 로드."""
    cells = defaultdict(list)
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "error" in r:
                continue
            cells[(r["av_id"], r["g_id"], float(r["c"]))].append(int(r["y"]))
    return cells


def one_trial_split(cells: dict, rng: np.random.Generator,
                    pass_g: list | None = None) -> tuple[float, np.ndarray, np.ndarray]:
    """한 split: cell당 K episode를 무작위 절반으로 분리하여 두 b̂ 매트릭스 산출.

    pass_g가 주어지면 단조성 통과 G만 사용(method_c 같은 음의 단조 G 제외).
    """
    av_ids = sorted({k[0] for k in cells})
    g_ids = sorted({k[1] for k in cells}) if pass_g is None else pass_g
    c_values = sorted({k[2] for k in cells})

    # b̂ 매트릭스 두 종: shape (G, c)
    b_a = np.zeros((len(g_ids), len(c_values)))
    b_b = np.zeros((len(g_ids), len(c_values)))
    for gi, g in enumerate(g_ids):
        for ci, c in enumerate(c_values):
            # 응시자 평균 충돌률 (각 응시자의 K_per_av를 split)
            rates_a = []
            rates_b = []
            for av in av_ids:
                ys = cells.get((av, g, c), [])
                if not ys:
                    continue
                ys_arr = np.array(ys)
                idx = rng.permutation(len(ys_arr))
                half = len(ys_arr) // 2
                rates_a.append(ys_arr[idx[:half]].mean())
                rates_b.append(ys_arr[idx[half:half * 2]].mean())
            b_a[gi, ci] = np.mean(rates_a) if rates_a else 0.0
            b_b[gi, ci] = np.mean(rates_b) if rates_b else 0.0
    r = stats.pearsonr(b_a.flatten(), b_b.flatten())[0]
    return float(r), b_a, b_b


def collect_rs(cells: dict, n_splits: int, seed: int,
               pass_g: list | None = None) -> tuple[np.ndarray, tuple]:
    rng = np.random.default_rng(seed)
    rs = []
    scatter_pair = None
    for s in range(n_splits):
        r, b_a, b_b = one_trial_split(cells, rng, pass_g=pass_g)
        rs.append(r)
        if s == 0:
            scatter_pair = (b_a.flatten(), b_b.flatten())
    return np.array(rs), scatter_pair


def build_figure(results: dict, scatter: tuple, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))

    # Panel (a): r 분포
    ax = axes[0]
    colors = ["#5B8DEF", "#FFB454"]
    for (key, rs), color in zip(results.items(), colors):
        p25 = np.percentile(rs, 25)
        ax.hist(rs, bins=20, alpha=0.55, color=color, edgecolor="white",
                linewidth=0.5,
                label=f"{key}  (mean = {rs.mean():.2f}, p25 = {p25:.2f})")
    ax.axvline(PASS_LINE, color="#D04A4A", linestyle="--", linewidth=1.2,
               label=fr"pass criterion $\rho \geq {PASS_LINE}$")
    ax.set_xlim(0.0, 1.05)
    ax.set_xlabel(r"trial-split $\hat{b}$ Pearson $r$")
    ax.set_ylabel("frequency")
    ax.set_title(r"(a) Trial-split $\hat{b}$ stability")
    ax.legend(loc="upper left", frameon=False)

    # Panel (b): b̂ scatter
    ax = axes[1]
    sa, sb = scatter
    ax.scatter(sa, sb, s=42, alpha=0.7, color="#5B8DEF",
               edgecolor="white", linewidth=0.5)
    lo = min(sa.min(), sb.min()) - 0.05
    hi = max(sa.max(), sb.max()) + 0.05
    ax.plot([lo, hi], [lo, hi], color="#888", linestyle=":", linewidth=1.0,
            label="y = x")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(r"$\hat{b}$ (trial subset A)")
    ax.set_ylabel(r"$\hat{b}$ (trial subset B)")
    ax.set_title(r"(b) Per-(G,c) collision rate agreement")
    ax.legend(loc="upper left", frameon=False)
    ax.set_aspect("equal", "box")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".pdf"))
    fig.savefig(out_path.with_suffix(".png"))
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", required=True)
    p.add_argument("--out", default="analysis/highway_grid/figures/d2_trial_split")
    p.add_argument("--n-splits", type=int, default=50)
    p.add_argument("--pass-g", nargs="+", default=None,
                   help="단조성 통과 G만 사용 (예: acarl_cutin acarl_rearend method_b)")
    args = p.parse_args()

    cells = load_cells(Path(args.jsonl))
    av_ids = sorted({k[0] for k in cells})
    g_ids = sorted({k[1] for k in cells})
    c_values = sorted({k[2] for k in cells})
    n_per_cell = len(cells[(av_ids[0], g_ids[0], c_values[0])])
    print(f">> 응시자 {len(av_ids)} ({av_ids}), G {len(g_ids)}, c {len(c_values)}, cell당 K={n_per_cell}")

    # 두 격자: 전체 G(method_c 포함) vs 단조성 통과 G만
    results = {}
    print(">> 전체 G(4종) trial-split:")
    rs_all, scatter_all = collect_rs(cells, args.n_splits, seed=0)
    print(f"    r mean = {rs_all.mean():.3f}, p25 = {np.percentile(rs_all, 25):.3f}")
    results[f"all 4 G"] = rs_all

    if args.pass_g:
        pass_g = args.pass_g
    else:
        pass_g = ["acarl_cutin", "acarl_rearend", "method_b"]
    print(f">> 단조성 통과 G({len(pass_g)}종) trial-split:")
    rs_pass, _ = collect_rs(cells, args.n_splits, seed=1, pass_g=pass_g)
    print(f"    r mean = {rs_pass.mean():.3f}, p25 = {np.percentile(rs_pass, 25):.3f}")
    results[f"monotone-pass {len(pass_g)} G"] = rs_pass

    build_figure(results, scatter_all, Path(args.out))
    print(f">> figure → {args.out}.{{pdf,png}}")


if __name__ == "__main__":
    main()
