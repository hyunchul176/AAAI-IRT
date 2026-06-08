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
               반응 차이의 통계적 유의성 검정.)
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
    """G를 모두 0으로 모음 + n_g=1 + item_id 재계산. G별 자유 모수가 하나로
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


def _expand_to_orig(f: dict, orig_n_g: int, variant: str) -> dict:
    """변종 fit 모수를 원본 n_g 차원으로 펼친다.

    g_common 변종은 n_g=1로 fit한 결과라 β·γ·a·u가 길이 1. 원본 n_g 차원에
    같은 값으로 펼쳐 원본 데이터의 G 인덱스에 적용한다. 다른 변종은 이미 원본
    차원이라 그대로.
    """
    if variant != "g_common":
        return f
    return dict(
        theta=f["theta"],
        beta=np.full(orig_n_g, float(f["beta"][0])),
        gamma=np.full(orig_n_g, float(f["gamma"][0])),
        a=np.full(orig_n_g, float(f["a"][0])),
        u=(np.full(orig_n_g, float(f["u"][0])) if f["u"] is not None else None),
        converged=f.get("converged", False),
        se_theta=f.get("se_theta", np.array([])),
    )


def neg_loglik_orig(orig_resp: dict, f: dict, variant: str) -> float:
    """변종 fit 모수를 원본 resp 위에 적용한 -loglik.

    LR test의 정합은 같은 데이터 위에서 두 모델의 likelihood를 비교하는 흐름.
    d3 변종은 데이터를 변형해 fit한 결과지만, 학습된 모수를 원본 데이터 위에
    적용한 likelihood가 진짜 비교 anchor다(변종 가정이 원본 데이터를 얼마나
    못 적합하는가의 자릿수). _neg_logpost를 use_prior=False로 호출해 prior 항
    제거(순수 likelihood 차이만).
    """
    n_av = orig_resp["n_av"]
    orig_n_g = orig_resp["n_g"]
    f_exp = _expand_to_orig(f, orig_n_g, variant)
    theta = f_exp["theta"]; beta = f_exp["beta"]
    gamma = f_exp["gamma"]; a = f_exp["a"]; u = f_exp["u"]
    if u is None:
        x = np.concatenate([theta, beta,
                            np.log(np.clip(gamma, 1e-9, None)),
                            np.log(np.clip(a, 1e-9, None))])
        fix_u = np.zeros(orig_n_g)
    else:
        from scipy.special import logit
        u_logit = logit(np.clip(u, 1e-6, 1 - 1e-6))
        x = np.concatenate([theta, beta,
                            np.log(np.clip(gamma, 1e-9, None)),
                            np.log(np.clip(a, 1e-9, None)),
                            u_logit])
        fix_u = None
    return float(_neg_logpost(x, orig_resp["y"], orig_resp["I"], orig_resp["G"],
                              orig_resp["cc"], orig_resp["K"],
                              n_av, orig_n_g, fix_u, False))


# 옛 인터페이스 호환(외부에서 import한 코드가 있을 수 있음 : variant=full로 호출).
def neg_loglik(resp: dict, f: dict) -> float:
    """호환용. variant 인자 없이 부르면 full로 가정(모수 차원 변환 안 함).
    LR test 정합한 흐름은 neg_loglik_orig(orig_resp, f, variant)에 있다.
    """
    return neg_loglik_orig(resp, f, "full")


def run_d3(resp: dict, n_splits: int = 20, seed: int = 0) -> dict:
    """변종 4종을 같은 응답 위에서 비교. 변종 fit은 변형 데이터로, 평가는 원본
    데이터 위에서. LR test 정합 조건: 변종 fit 모수를 원본 데이터에 적용한 NLL이
    full NLL보다 크거나 같아야 한다(양의 LR).
    """
    rng = np.random.default_rng(seed)
    out = {}
    for variant in VARIANTS:
        # 변종 fit
        f = fit_variant(resp, variant, seed=int(rng.integers(1e9)))
        # 평가는 원본 resp 위에서 (LR test 정합)
        nll = neg_loglik_orig(resp, f, variant)
        # split-half r : 변종 가정 위 안정성. 변종 변형 데이터에서 두 절반 fit한 b̂의
        # Pearson r. 본문 해석: "변종 가정이 데이터를 단순화했을 때 안정성이 어떻게
        # 떨어지는가." full은 원본 데이터 위에서 측정.
        if variant == "no_severity":
            resp_v = _resp_no_severity(resp)
        elif variant == "g_common":
            resp_v = _resp_g_common(resp)
        else:
            resp_v = resp
        rs = []
        try:
            for _ in range(n_splits):
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
    # LR 통계 (full vs 각 변종). 같은 원본 데이터 위에서 측정한 NLL 차이.
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
