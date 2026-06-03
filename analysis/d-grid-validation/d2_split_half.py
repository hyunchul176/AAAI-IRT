# -*- coding: utf-8 -*-
"""D2 표본불변성 검증: b̂ split-half 상관 (specific objectivity 경험적 확인).

본 격자 응답 JSONL을 (AV, G, severity, trial)의 4차원 응답 격자로 변환한 뒤
`analysis/d-study/d_study.py`의 fit_map(MAP + Laplace 추정)과 split_half_metrics
(AV 부분집합 무작위 split 50회 b̂ Pearson r 분포)를 호출해 r 분포의 25 percentile이
격자 합격선 0.80을 넘는지 보고한다.

응답 JSONL 한 행 (analysis/b4-pipeline/sb_to_response.CellResponse를 dict로):
    {"av_id": "sac", "g_id": "lc", "c": 2.0, "trial_k": 0,
     "y": 0,  # 0=무충돌, 1=충돌 (한 trial)
     "u_label": 0.3,  # RSS 회피불가 라벨 (없으면 None, fit_map이 fix_u=None으로 추정)
     ...}

usage:
    python3 analysis/d-grid-validation/d2_split_half.py \\
        analysis/b4-pipeline/responses.jsonl                       # 본 격자 응답 분석
    python3 analysis/d-grid-validation/d2_split_half.py --sanity   # 합성 응답으로 sanity
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

# d_study.py와 같은 디렉토리 import. CWD가 repo root일 때 d-study 디렉토리는
# 하이픈이 있어 직접 import 불가 → sys.path에 명시.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import (  # noqa: E402
    fit_map,
    split_half_metrics,
    draw_true_params,
    simulate_responses,
    b_item_grid,
)


def load_responses(jsonl_path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_resp_dict(rows: list[dict]) -> dict:
    """본 격자 응답 행들을 모아 d_study.py의 fit_map이 받는 resp dict로 변환.

    한 (AV, G, c) 셀의 K trial을 모아 y_sum(0~K 정수)로 만든다. 한 trial 한 행이
    들어오는 형식을 가정한다(K=trial 수 = 셀당 행 수의 최소값).
    """
    by_cell: dict[tuple[str, str, float], list[int]] = defaultdict(list)
    for r in rows:
        key = (r["av_id"], r["g_id"], float(r["c"]))
        by_cell[key].append(int(r["y"]))

    av_set = sorted({k[0] for k in by_cell})
    g_set = sorted({k[1] for k in by_cell})
    c_set = sorted({k[2] for k in by_cell})
    av_idx = {av: i for i, av in enumerate(av_set)}
    g_idx = {g: i for i, g in enumerate(g_set)}
    c_idx = {c: i for i, c in enumerate(c_set)}

    n_av, n_g, n_sev = len(av_set), len(g_set), len(c_set)
    K = min(len(v) for v in by_cell.values())

    # y_sum, I, G, L, cc, item_id 평탄 array
    y_list, I_list, G_list, L_list = [], [], [], []
    for (av, g, c), ys in by_cell.items():
        i = av_idx[av]; j = g_idx[g]; l = c_idx[c]
        y_sum = int(sum(ys[:K]))  # K로 자름 (불균등 셀이 있으면 가장 작은 K로 맞춤)
        y_list.append(y_sum); I_list.append(i); G_list.append(j); L_list.append(l)

    y = np.array(y_list, dtype=np.int64)
    I_ = np.array(I_list, dtype=np.int64)
    G_ = np.array(G_list, dtype=np.int64)
    L_ = np.array(L_list, dtype=np.int64)
    C = np.array(c_set, dtype=np.float64)
    cc = C[L_]
    item_id = G_ * n_sev + L_

    return dict(
        y=y, I=I_, G=G_, L=L_, cc=cc, item_id=item_id,
        K=K, C=C, n_av=n_av, n_g=n_g, n_sev=n_sev,
        av_list=av_set, g_list=g_set, c_list=c_set,
    )


def run_d2(resp: dict, n_splits: int = 50, use_prior: bool = True,
           fix_u: np.ndarray | None = None, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    # main fit (전체 응답에서 한 번)
    main_fit = fit_map(resp, fix_u=fix_u, use_prior=use_prior,
                       seed=int(rng.integers(1e9)))
    # split-half 50회
    rs, mhs, deltas = [], [], []
    for _ in range(n_splits):
        r, mh, d = split_half_metrics(resp, fix_u, rng, use_prior)
        rs.append(r); mhs.append(mh); deltas.append(d)
    rs_arr = np.array(rs)
    p25 = float(np.percentile(rs_arr, 25))
    p5 = float(np.percentile(rs_arr, 5))
    se = main_fit.get("se_theta", np.array([]))
    ci_width = float(np.nanmean(2 * 1.96 * se)) if se.size else float("nan")
    return dict(
        n_av=resp["n_av"], n_g=resp["n_g"], n_sev=resp["n_sev"], K=resp["K"],
        split_r_mean=float(rs_arr.mean()),
        split_r_p25=p25,
        split_r_p5=p5,
        split_r_min=float(rs_arr.min()),
        split_mh_mean=float(np.mean(mhs)),
        theta_ci_width=ci_width,
        converged=main_fit.get("converged", False),
        pass_p25_080=(p25 >= 0.80),   # 격자 합격선 결정의 1차 합격
        pass_p5_080=(p5 >= 0.80),     # 보수 합격 (bootstrap 5 percentile)
    )


def run_jsonl(jsonl_path: Path) -> None:
    rows = load_responses(jsonl_path)
    print(f">> loaded {len(rows)} response rows from {jsonl_path}")
    resp = build_resp_dict(rows)
    print(f">> grid: AV={resp['n_av']} × G={resp['n_g']} × c={resp['n_sev']} × K={resp['K']}")
    print(f">> AV list: {resp['av_list']}")
    print(f">> G  list: {resp['g_list']}")
    print(f">> c  list: {resp['c_list']}")
    # u_label이 있으면 fix_u로 사용, 없으면 None으로 두어 fit_map이 추정.
    # 본 격자 첫 호출에서는 RSS 라벨러 미적용일 수 있으므로 None.
    out = run_d2(resp, n_splits=50, use_prior=True, fix_u=None, seed=0)
    print()
    print(">> D2 split-half 결과:")
    for k, v in out.items():
        print(f"   {k}: {v}")


def run_sanity() -> None:
    """합성 응답으로 fit_map + split_half_metrics 호출 검증.

    A1 합성 격자(AV=6 × G=2 × c=5 × K=10 = 600 cells)에서 d_study 흐름 그대로
    돌려 split r mean·p25를 본다. 합격선 위로 떨어지면 함수 사슬 살아 있음.
    """
    print(">> sanity check (synthetic): AV=6 × G=2 × c=5 × K=10")
    rng = np.random.default_rng(42)
    true = draw_true_params(n_av=6, n_g=2, rng=rng)
    resp = simulate_responses(true, n_sev=5, K=10,
                              sev_placement="uniform", rng=rng)
    out = run_d2(resp, n_splits=20, use_prior=True, fix_u=true["u"], seed=0)
    print()
    for k, v in out.items():
        print(f"   {k}: {v}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="?", default=None,
                   help="본 격자 응답 JSONL 경로")
    p.add_argument("--sanity", action="store_true",
                   help="합성 응답으로 함수 사슬 검증")
    args = p.parse_args()
    if args.sanity:
        run_sanity()
        return
    if not args.jsonl:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run_jsonl(Path(args.jsonl))


if __name__ == "__main__":
    main()
