# -*- coding: utf-8 -*-
"""본 측정 모델의 직접 적합 결과 산출.

K=70 통합 응답 jsonl(Defensive RL 세 시드)을 입력으로 받아 method.html 식 (6)의
모수 θ̂(응시자 강건성)·b̂(시나리오 난이도)·γ̂(severity 다이얼)·â(변별력)·û
(회피불가 하한)를 fit_map으로 추정하고, 본문 Results 절에 박을 figure 네 종을
산출한다.

산출 figure:
  (a) 응시자별 θ̂과 95% CI (Defensive RL 세 시드의 강건성 자릿수와 순위)
  (b) (G × c) b̂ heatmap (시나리오 난이도 매트릭스)
  (c) 생성기별 γ̂ (severity 다이얼 강도)
  (d) 생성기별 û (회피불가 하한)

D4 외부 비교점 sanity check로 본 추정 b̂의 c별 단조성 ρ와 ACARL 원고 §6.5의
cross-defender Spearman ρ(cut-in 0.53, rear-end 0.55)를 자릿수 일치 수준에서 비교한다.

usage:
    python3 analysis/highway_grid/fit_irt_main.py \\
        --jsonl analysis/highway_grid/responses_def_rl_combined.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import fit_map, b_item_grid  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-grid-validation"))
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


ACARL_RHO = {"acarl_cutin": 0.53, "acarl_rearend": 0.55}


def panel_theta(ax, av_list, theta, se_theta) -> None:
    x = np.arange(len(av_list))
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E"]
    ci_half = 1.96 * se_theta
    ax.bar(x, theta, color=colors[:len(av_list)], alpha=0.8,
           edgecolor="white", linewidth=0.5)
    ax.errorbar(x, theta, yerr=ci_half, fmt="none",
                ecolor="#333", capsize=4, linewidth=1.0)
    ax.axhline(0, color="#888", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(av_list, rotation=0)
    ax.set_ylabel(r"$\hat{\theta}$ (robustness)")
    ax.set_title(r"(a) AV robustness $\hat{\theta}$ with 95% CI")


def panel_b_heatmap(ax, g_list, c_list, b_mat) -> None:
    im = ax.imshow(b_mat, aspect="auto", cmap="RdYlBu_r",
                   vmin=-3, vmax=3, origin="lower")
    ax.set_xticks(np.arange(len(c_list)))
    ax.set_xticklabels([f"{c:.0f}" for c in c_list])
    ax.set_yticks(np.arange(len(g_list)))
    ax.set_yticklabels(g_list)
    ax.set_xlabel("severity c")
    ax.set_ylabel("generator G")
    ax.set_title(r"(b) Scenario difficulty $\hat{b}(G, c)$")
    for i in range(b_mat.shape[0]):
        for j in range(b_mat.shape[1]):
            ax.text(j, i, f"{b_mat[i, j]:.2f}", ha="center", va="center",
                    color="#222", fontsize=7)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=r"$\hat{b}$")


def panel_gamma(ax, g_list, gamma) -> None:
    x = np.arange(len(g_list))
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E", "#D04A4A"]
    ax.bar(x, gamma, color=colors[:len(g_list)], alpha=0.8,
           edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="#888", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(g_list, rotation=15, ha="right")
    ax.set_ylabel(r"$\hat{\gamma}_G$")
    ax.set_title(r"(c) Severity dial strength $\hat{\gamma}_G$")


def panel_u(ax, g_list, u) -> None:
    x = np.arange(len(g_list))
    colors = ["#5B8DEF", "#FFB454", "#5DAA7E", "#D04A4A"]
    ax.bar(x, u, color=colors[:len(g_list)], alpha=0.8,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(g_list, rotation=15, ha="right")
    ax.set_ylabel(r"$\hat{u}_G$")
    ax.set_ylim(0, 1)
    ax.set_title(r"(d) Unavoidable lower bound $\hat{u}_G$")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", required=True)
    p.add_argument("--out-prefix",
                   default="analysis/highway_grid/figures/irt_main")
    args = p.parse_args()

    rows = load_responses(Path(args.jsonl))
    print(f">> 응답 {len(rows)} 건 로드", flush=True)
    resp = build_resp_dict(rows)
    print(f">> 격자: AV={resp['n_av']}, G={resp['n_g']}, c={resp['n_sev']}, K={resp['K']}",
          flush=True)
    print(f">> AV list: {resp['av_list']}")
    print(f">> G list:  {resp['g_list']}")
    print(f">> c list:  {list(resp['c_list'])}")

    print("\n>> fit_map 호출 (use_prior=True, fix_u=None) ...", flush=True)
    f = fit_map(resp, fix_u=None, use_prior=True, seed=20260605)
    theta, beta, gamma, a, u = f["theta"], f["beta"], f["gamma"], f["a"], f["u"]
    se_theta = f["se_theta"]

    print("\n>> 추정 결과")
    print(f"   converged: {f['converged']}")
    print(f"   θ̂ (응시자 강건성):")
    for av_id, t, se in zip(resp["av_list"], theta, se_theta):
        print(f"      {av_id:<14} θ̂ = {t:>7.3f} ± {1.96*se:>5.3f} (95% CI)")
    print(f"   β̂ (생성기 baseline 난이도):")
    for g_id, b in zip(resp["g_list"], beta):
        print(f"      {g_id:<14} β̂ = {b:>7.3f}")
    print(f"   γ̂ (severity 다이얼):")
    for g_id, g in zip(resp["g_list"], gamma):
        print(f"      {g_id:<14} γ̂ = {g:>7.3f}")
    print(f"   â (변별력):")
    for g_id, ai in zip(resp["g_list"], a):
        print(f"      {g_id:<14} â = {ai:>7.3f}")
    print(f"   û (회피불가 하한):")
    for g_id, ui in zip(resp["g_list"], u):
        print(f"      {g_id:<14} û = {ui:>7.3f}")

    b_mat = b_item_grid(beta, gamma, resp["C"])
    print(f"\n>> b̂ 매트릭스 (G × c):")
    print("   " + "G".ljust(14) + " ".join(f"c={c:>3.0f}" for c in resp["c_list"]))
    for g_id, row in zip(resp["g_list"], b_mat):
        print(f"   {g_id:<14}" + " ".join(f"{v:>6.2f}" for v in row))

    print(f"\n>> D4 외부 비교점 sanity check")
    print(f"   ACARL 원고 §6.5 cross-defender Spearman ρ vs 본 b̂의 c별 단조성 ρ")
    for gi, g_id in enumerate(resp["g_list"]):
        rho_b, _ = stats.spearmanr(resp["c_list"], b_mat[gi])
        if g_id in ACARL_RHO:
            print(f"   {g_id:<14} ACARL ρ={ACARL_RHO[g_id]:>5.2f}  본 b̂ ρ={rho_b:>5.2f}  "
                  f"자릿수 일치={'예' if abs(ACARL_RHO[g_id] - rho_b) < 0.5 else '아니오'}")
        else:
            print(f"   {g_id:<14} (ACARL 비교 없음, 본 b̂ ρ={rho_b:>5.2f})")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    panel_theta(axes[0, 0], resp["av_list"], theta, se_theta)
    panel_b_heatmap(axes[0, 1], resp["g_list"], list(resp["c_list"]), b_mat)
    panel_gamma(axes[1, 0], resp["g_list"], gamma)
    panel_u(axes[1, 1], resp["g_list"], u)
    fig.suptitle(r"AAAI measurement model fit: $\hat{\theta}$, $\hat{b}$, $\hat{\gamma}$, $\hat{u}$  "
                 r"(K=70 combined, Defensive RL 3 seeds)", fontsize=11)
    fig.tight_layout()
    out_path = Path(args.out_prefix)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".pdf"))
    fig.savefig(out_path.with_suffix(".png"))
    plt.close(fig)
    print(f"\n>> figure saved: {out_path.with_suffix('.pdf')}")
    print(f"                  {out_path.with_suffix('.png')}")

    summary = {
        "n_av": resp["n_av"], "n_g": resp["n_g"], "n_sev": resp["n_sev"], "K": resp["K"],
        "av_list": resp["av_list"], "g_list": resp["g_list"],
        "c_list": list(resp["c_list"]),
        "theta_hat": theta.tolist(),
        "se_theta": se_theta.tolist(),
        "beta_hat": beta.tolist(),
        "gamma_hat": gamma.tolist(),
        "a_hat": a.tolist(),
        "u_hat": u.tolist() if u is not None else None,
        "b_matrix": b_mat.tolist(),
        "converged": bool(f["converged"]),
        "scale_s": f.get("scale_s", None),
    }
    summary_path = out_path.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f">> 추정값 → {summary_path}")


if __name__ == "__main__":
    main()
