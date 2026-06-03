# -*- coding: utf-8 -*-
"""D3 ablation: 네 변종의 적합 비교.

method.html 식 (6) P = u + (1-u)·σ(a·(β + γ_G·c − θ))에서 세 구조를 하나씩
검증한다. 각 변종은 d_study.py의 fit_map을 호출하지만 resp 또는 fix_u 인자로
변종 의도를 강제한다.

변종 4종 (검토자 라운드 11·12 정정 후):
- full       : 모든 모수 자유, γ_G가 G별
- no_severity: 응답에서 cc를 0으로 강제 → γ_G·c=0, σ(β−θ) 정적 IRT
- g_common   : 응답의 G를 모두 0으로 모음 → γ_G가 사실상 공통 한 값으로
               통합(G별 β·γ·a가 하나로 흡수). G별 반응성 차이 무시.
               (참고: 측정학 표준 metric invariance가 아니라 G별 severity
               반응 차이의 통계적 유의성 검정 자리.)
- u_zero     : u=0으로 fix → 회피불가 하한 무시 (현행 평가 관행)

각 변종에서 log-likelihood + split-half b̂ r p25 + θ̂ CI 폭을 보고. 본문은
full vs 변종의 차이가 의미 있는지(LRT χ², df = 모수 차이)를 본다.

usage:
    python3 analysis/d-grid-validation/d3_ablation.py \\
        analysis/b4-pipeline/responses.jsonl
    python3 analysis/d-grid-validation/d3_ablation.py --sanity
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import (  # noqa: E402
    fit_map,
    split_half_metrics,
    draw_true_params,
    simulate_responses,
    _neg_logpost,
)
# d2_split_half의 build_resp_dict 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d2_split_half import load_responses, build_resp_dict  # noqa: E402


def _resp_no_severity(resp: dict) -> dict:
    """cc를 0으로 강제. γ_G·c=0 → severity 효과 무시."""
    out = dict(resp)
    out["cc"] = np.zeros_like(resp["cc"])
    out["C"] = np.zeros_like(resp["C"])
    return out


def _resp_g_common(resp: dict) -> dict:
    """G를 모두 0으로 모음 + n_g=1 + item_id 재계산. G별 자유 모수가 한 자리로
    흡수되어 G별 반응성 차이 무시.
    """
    out = dict(resp)
    out["G"] = np.zeros_like(resp["G"])
    out["n_g"] = 1
    out["item_id"] = resp["L"]  # G=0이므로 L 그대로
    return out


VARIANTS = ["full", "no_severity", "g_common", "u_zero"]


def fit_variant(resp: dict, variant: str, seed: int = 0) -> dict:
    n_g = resp["n_g"]
    if variant == "full":
        return fit_map(resp, fix_u=None, use_prior=True, seed=seed)
    if variant == "no_severity":
        return fit_map(_resp_no_severity(resp), fix_u=None, use_prior=True, seed=seed)
    if variant == "g_common":
        return fit_map(_resp_g_common(resp), fix_u=None, use_prior=True, seed=seed)
    if variant == "u_zero":
        return fit_map(resp, fix_u=np.zeros(n_g), use_prior=True, seed=seed)
    raise ValueError(f"unknown variant: {variant}")


def neg_loglik(resp: dict, f: dict) -> float:
    """변종 적합값에서 자유 모수 벡터를 다시 만들어 _neg_logpost로 -loglik 계산.
    use_prior=False로 호출해 prior 항 제거(순수 likelihood 차이).
    """
    n_av, n_g = resp["n_av"], resp["n_g"]
    theta = f["theta"]; beta = f["beta"]; gamma = f["gamma"]; a = f["a"]; u = f["u"]
    if u is None:
        x = np.concatenate([theta, beta, np.log(np.clip(a, 1e-6, None)), gamma])
        fix_u = np.zeros(n_g)  # u_zero 변종
    else:
        from scipy.special import logit
        u_logit = logit(np.clip(u, 1e-6, 1 - 1e-6))
        x = np.concatenate([theta, beta, np.log(np.clip(a, 1e-6, None)), gamma, u_logit])
        fix_u = None
    return float(_neg_logpost(x, resp["y"], resp["I"], resp["G"], resp["cc"], resp["K"],
                              n_av, n_g, fix_u, False))


def run_d3(resp: dict, n_splits: int = 20, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for variant in VARIANTS:
        # 변종별 resp 변형
        if variant == "no_severity":
            resp_v = _resp_no_severity(resp)
        elif variant == "g_common":
            resp_v = _resp_g_common(resp)
        else:
            resp_v = resp
        f = fit_variant(resp, variant, seed=int(rng.integers(1e9)))
        nll = neg_loglik(resp_v, f)
        # split-half r (변종 resp 기준)
        rs = []
        try:
            for _ in range(n_splits):
                # u_zero는 fix_u=zeros, 다른 변종은 None
                fix_u_split = np.zeros(resp_v["n_g"]) if variant == "u_zero" else None
                r, _, _ = split_half_metrics(resp_v, fix_u_split, rng, use_prior=True)
                rs.append(r)
            rs_arr = np.array(rs)
            p25 = float(np.percentile(rs_arr, 25))
            r_mean = float(rs_arr.mean())
        except Exception as e:
            p25 = float("nan")
            r_mean = float("nan")
            print(f"   warning: {variant} split-half 실패: {e}")
        se = f.get("se_theta", np.array([]))
        ci_width = float(np.nanmean(2 * 1.96 * se)) if se.size else float("nan")
        out[variant] = dict(
            neg_loglik=nll,
            split_r_mean=r_mean,
            split_r_p25=p25,
            theta_ci_width=ci_width,
            converged=f.get("converged", False),
        )
    # LRT 차이 (full vs 각 변종)
    full_nll = out["full"]["neg_loglik"]
    for v in VARIANTS:
        if v == "full":
            continue
        out[v]["lr_stat_vs_full"] = 2 * (out[v]["neg_loglik"] - full_nll)
    return out


def run_jsonl(jsonl_path: Path) -> None:
    rows = load_responses(jsonl_path)
    print(f">> loaded {len(rows)} response rows")
    resp = build_resp_dict(rows)
    print(f">> grid: AV={resp['n_av']} × G={resp['n_g']} × c={resp['n_sev']} × K={resp['K']}")
    out = run_d3(resp, n_splits=20)
    print(">> D3 ablation 결과:")
    for v, d in out.items():
        print(f"   [{v}]")
        for k, val in d.items():
            print(f"       {k}: {val}")


def run_sanity() -> None:
    print(">> sanity check (synthetic): AV=6 × G=3 × c=5 × K=10")
    rng = np.random.default_rng(42)
    true = draw_true_params(n_av=6, n_g=3, rng=rng)
    resp = simulate_responses(true, n_sev=5, K=10, sev_placement="uniform", rng=rng)
    out = run_d3(resp, n_splits=10)
    for v, d in out.items():
        print(f"   [{v}]")
        for k, val in d.items():
            print(f"       {k}: {val}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="?", default=None)
    p.add_argument("--sanity", action="store_true")
    args = p.parse_args()
    if args.sanity:
        run_sanity()
    elif args.jsonl:
        run_jsonl(Path(args.jsonl))
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
