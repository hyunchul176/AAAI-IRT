# -*- coding: utf-8 -*-
"""D2 본문 figure: split-half b̂ 표본불변성 시각화.

본문 핵심 figure 가운데 하나. 같은 측정 모델 위에서 응시자 부분집합을 바꿔도
시나리오 난이도 추정 b̂이 같은 위치에 머문다는 specific objectivity의 경험적
시각화. plan §13 첫째 기여(SUT-불변 측정)의 가장 가까운 본문 증거다.

세 panel:

(a) split-half b̂ Pearson r 분포 (50회 split). 격자 크기 셋(AV=4·6·8)에서 r 분포
    히스토그램을 겹쳐 그려, AV가 늘수록 분포가 합격선 ρ ≥ 0.80 위로 좁아지는
    흐름을 본다.
(b) 한 무작위 split의 left·right b̂ scatter. 응시자 부분집합이 달라도 b̂이
    대각선 y=x 근처에 머무는 결과를 직접 보여 준다(specific objectivity).
(c) 표본 크기 K에 따른 평균 θ posterior SE(95% CI 폭). 식 (9)의 Fisher 정보
    합 ∝ 1/SE² 관계를 데이터로 받친다. D-study의 핵심 시각화.

본 격자 K=20 결과가 들어오면 합성 응답을 본 격자 응답으로 바꿔 같은 figure를
다시 산출한다. 본문 figure는 이 흐름의 결과.

usage:
    # 합성 응답으로 figure 미리 산출 (pilot v3 끝나기 전 작업)
    python3 analysis/d-grid-validation/d2_figure.py

    # 본 격자 응답 JSONL 들어오면
    python3 analysis/d-grid-validation/d2_figure.py --jsonl <responses.jsonl>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import (  # noqa: E402
    draw_true_params, simulate_responses, fit_map, split_half_metrics,
    b_item_grid,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d2_split_half import load_responses, build_resp_dict  # noqa: E402


# 본문 figure 규약 (AAAI single-column · 학술 figure 표준)
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

PASS_LINE = 0.80   # D2 합격선 (split r 25 percentile ≥ 0.80)


def collect_split_r(resp: dict, n_splits: int, fix_u=None, use_prior=True,
                    seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """split-half b̂ Pearson r 분포 + 한 split의 (b̂_a, b̂_b) 값 반환.

    50회 split마다 r 한 값을 모아 분포로 만든다. 첫 split의 b̂_a·b̂_b는 panel (b)
    scatter에 쓴다.
    """
    rng = np.random.default_rng(seed)
    rs: list[float] = []
    scatter_a, scatter_b = None, None
    for s in range(n_splits):
        r, _mh, _d = split_half_metrics(resp, fix_u, rng, use_prior)
        rs.append(r)
        if s == 0:
            # 같은 split에서 left·right b̂를 따로 fit해 scatter 자료 마련
            n_av = resp["n_av"]
            perm = np.random.default_rng(seed + 1).permutation(n_av)
            half_a, half_b = perm[:n_av // 2], perm[n_av // 2:]
            sub_a = _subset_resp(resp, half_a)
            sub_b = _subset_resp(resp, half_b)
            fa = fit_map(sub_a, fix_u=fix_u, use_prior=use_prior, seed=seed)
            fb = fit_map(sub_b, fix_u=fix_u, use_prior=use_prior, seed=seed + 1)
            scatter_a = b_item_grid(fa["beta"], fa["gamma"], resp["C"]).flatten()
            scatter_b = b_item_grid(fb["beta"], fb["gamma"], resp["C"]).flatten()
    return np.array(rs), (scatter_a, scatter_b)


def _subset_resp(resp: dict, av_idx: np.ndarray) -> dict:
    """응답 dict에서 응시자 부분집합만 남긴 dict 만들기."""
    keep_av = set(int(i) for i in av_idx)
    mask = np.array([int(i) in keep_av for i in resp["I"]], dtype=bool)
    # I_를 0~len(keep_av)-1로 재매핑
    old_to_new = {old: new for new, old in enumerate(sorted(keep_av))}
    new_I = np.array([old_to_new[int(i)] for i in resp["I"][mask]], dtype=np.int64)
    return dict(
        y=resp["y"][mask], I=new_I, G=resp["G"][mask], L=resp["L"][mask],
        cc=resp["cc"][mask], item_id=resp["item_id"][mask],
        K=resp["K"], C=resp["C"], n_av=len(keep_av),
        n_g=resp["n_g"], n_sev=resp["n_sev"],
    )


def panel_a_split_r(ax, results: dict) -> None:
    """50 splits: b̂ Pearson r distribution across AV subset splits."""
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E"]
    for (n_av, rs), color in zip(results.items(), colors):
        p25 = np.percentile(rs, 25)
        ax.hist(rs, bins=20, alpha=0.55, color=color, edgecolor="white",
                linewidth=0.5, label=f"N={n_av}  (p25 = {p25:.2f})")
    ax.axvline(PASS_LINE, color="#D04A4A", linestyle="--", linewidth=1.2,
               label=fr"pass criterion $\rho \geq {PASS_LINE}$")
    ax.set_xlim(0.4, 1.0)
    ax.set_xlabel(r"split-half $\hat{b}$ Pearson $r$")
    ax.set_ylabel("frequency (50 splits)")
    ax.set_title(r"(a) Sample invariance of $\hat{b}$ across AV subsets")
    ax.legend(loc="upper left", frameon=False)


def panel_b_scatter(ax, scatter_a: np.ndarray, scatter_b: np.ndarray) -> None:
    """One split: b̂ on AV subset A vs subset B. Points along y=x = specific objectivity."""
    ax.scatter(scatter_a, scatter_b, s=18, alpha=0.7, color="#5B8DEF",
               edgecolor="white", linewidth=0.4)
    lo = min(scatter_a.min(), scatter_b.min()) - 0.3
    hi = max(scatter_a.max(), scatter_b.max()) + 0.3
    ax.plot([lo, hi], [lo, hi], color="#888", linestyle=":",
            linewidth=1.0, label="y = x (specific objectivity)")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(r"$\hat{b}$  on AV subset A")
    ax.set_ylabel(r"$\hat{b}$  on AV subset B")
    ax.set_title(r"(b) Scenario difficulty $\hat{b}$ agreement across AV subsets")
    ax.legend(loc="upper left", frameon=False)
    ax.set_aspect("equal", "box")


def panel_c_K_sweep(ax) -> None:
    """K sweep: mean posterior SE(θ̂) vs trial repetitions K. Fisher info ∝ K, SE ∝ 1/√K."""
    K_list = [5, 10, 20, 30, 50]
    se_means: list[float] = []
    rng = np.random.default_rng(7)
    true = draw_true_params(n_av=6, n_g=4, rng=rng)
    for K in K_list:
        resp = simulate_responses(true, n_sev=5, K=K,
                                  sev_placement="uniform", rng=rng)
        f = fit_map(resp, fix_u=true["u"], use_prior=True, seed=0)
        se_means.append(float(np.nanmean(f["se_theta"])))
    se_arr = np.array(se_means)
    pred = se_arr[0] * np.sqrt(K_list[0]) / np.sqrt(K_list)
    ax.plot(K_list, se_arr, "o-", color="#5B8DEF", linewidth=1.6,
            markersize=6, label=r"observed mean SE($\hat{\theta}$)")
    ax.plot(K_list, pred, "--", color="#888", linewidth=1.0,
            label=r"prediction $\propto 1/\sqrt{K}$")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("trial repetitions K (per cell)")
    ax.set_ylabel(r"mean SE($\hat{\theta}$)")
    ax.set_title(r"(c) Decision study: K vs SE($\hat{\theta}$)")
    ax.legend(loc="upper right", frameon=False)
    ax.set_xticks(K_list)
    ax.set_xticklabels([str(k) for k in K_list])


def build_figure(results_by_N: dict, scatter_pair: tuple, out_path: Path) -> None:
    """세 panel 한 figure로 묶어 PDF·PNG로 저장."""
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    panel_a_split_r(axes[0], results_by_N)
    panel_b_scatter(axes[1], scatter_pair[0], scatter_pair[1])
    panel_c_K_sweep(axes[2])
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".pdf"))
    fig.savefig(out_path.with_suffix(".png"))
    plt.close(fig)
    print(f">>> figure saved: {out_path.with_suffix('.pdf')}")
    print(f"                  {out_path.with_suffix('.png')}")


def run_synthetic(out_path: Path, n_splits: int = 50) -> None:
    """본 격자 응답이 없을 때 합성 응답으로 figure 산출.

    AV 격자 셋(N=4·6·8) × G=4 × c=5 × K=20에서 split r 분포를 모은다.
    """
    rng_master = np.random.default_rng(42)
    results: dict[int, np.ndarray] = {}
    scatter_pair = None
    for n_av in (4, 6, 8):
        print(f">>> synthetic N={n_av}")
        true = draw_true_params(n_av=n_av, n_g=4,
                                rng=np.random.default_rng(rng_master.integers(1e9)))
        resp = simulate_responses(true, n_sev=5, K=20,
                                  sev_placement="uniform",
                                  rng=np.random.default_rng(rng_master.integers(1e9)))
        rs, sp = collect_split_r(resp, n_splits=n_splits, fix_u=true["u"],
                                 use_prior=True, seed=int(rng_master.integers(1e9)))
        results[n_av] = rs
        if n_av == 6:
            scatter_pair = sp  # 본문 figure (b)는 권고 격자 N=6 결과에서 추출
        print(f"    r mean = {rs.mean():.3f}, p25 = {np.percentile(rs, 25):.3f}, "
              f"min = {rs.min():.3f}")
    build_figure(results, scatter_pair, out_path)


def run_real(jsonl_path: Path, out_path: Path, n_splits: int = 50) -> None:
    """본 격자 응답 JSONL → figure. AV 격자 한 셋트만 (실제 격자 단일 입력)."""
    rows = load_responses(jsonl_path)
    resp = build_resp_dict(rows)
    n_av = resp["n_av"]
    print(f">>> 본 격자 응답 N={n_av} × G={resp['n_g']} × c={resp['n_sev']} × K={resp['K']}")
    rs, sp = collect_split_r(resp, n_splits=n_splits, fix_u=None,
                             use_prior=True, seed=0)
    print(f"    r mean = {rs.mean():.3f}, p25 = {np.percentile(rs, 25):.3f}, "
          f"min = {rs.min():.3f}")
    build_figure({n_av: rs}, sp, out_path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", default=None,
                   help="본 격자 응답 JSONL (없으면 합성 응답으로 산출)")
    p.add_argument("--out", default="analysis/d-grid-validation/figures/d2_split_half",
                   help="저장 경로 (확장자 자동, PDF + PNG 양쪽)")
    p.add_argument("--n-splits", type=int, default=50)
    args = p.parse_args()
    out_path = Path(args.out)
    if args.jsonl:
        run_real(Path(args.jsonl), out_path, args.n_splits)
    else:
        run_synthetic(out_path, args.n_splits)


if __name__ == "__main__":
    main()
