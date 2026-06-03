# -*- coding: utf-8 -*-
"""D1 순위 역전 재현: 시나리오 집합에 따라 AV 순위가 뒤집힘.

섹션 B의 LD-Scene·Shen이 보인 현상(같은 AV 집단이라도 시나리오 부분집합을
달리하면 충돌률 기반 AV 순위가 뒤집힘)을 우리 격자에서 재현한다. 본문 D2
표본불변성 결과의 대비점이다 ("문제 재현 → 우리 모델이 그 문제를 해소").

설계:
1. 응답 JSONL → (AV, scenario_id, route_id, data_id) 단위 충돌률 매트릭스.
2. scenario_id·route_id를 두 갈래로 50회 무작위 split.
3. 각 갈래에서 AV별 평균 충돌률 → AV 순위 매김.
4. 두 갈래의 Spearman ρ·Kendall τ + 순위 뒤집힘 비율(top-k 순위가 두 갈래에서
   다른 비율).

usage:
    python3 analysis/d-grid-validation/d1_rank_reversal.py \\
        analysis/b4-pipeline/responses.jsonl
    python3 analysis/d-grid-validation/d1_rank_reversal.py --sanity
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats


def load_responses(jsonl_path: Path) -> list[dict]:
    with open(jsonl_path) as f:
        return [json.loads(line) for line in f if line.strip()]


def build_av_scenario_matrix(rows: list[dict]) -> tuple[np.ndarray, list[str], list[tuple]]:
    """행들을 (AV, scenario=(sid, rid, data_id)) 매트릭스로. 셀당 평균 충돌률.

    같은 셀에 K trial이 있으면 평균. 값이 없는 자리는 NaN으로 두고 split 시
    nanmean.
    """
    by_cell: dict[tuple[str, tuple], list[int]] = defaultdict(list)
    for r in rows:
        scen = (int(r.get("sid", 0)), int(r.get("rid", 0)), int(r.get("data_id", 0)))
        by_cell[(r["av_id"], scen)].append(int(r["y"]))
    av_list = sorted({k[0] for k in by_cell})
    scen_list = sorted({k[1] for k in by_cell})
    M = np.full((len(av_list), len(scen_list)), np.nan)
    for (av, scen), ys in by_cell.items():
        i = av_list.index(av)
        j = scen_list.index(scen)
        M[i, j] = float(np.mean(ys))
    return M, av_list, scen_list


def rank_reversal(M: np.ndarray, n_splits: int = 50, seed: int = 0) -> dict:
    """시나리오 부분집합 50회 split → 두 갈래 AV 순위 Spearman ρ·Kendall τ +
    상위 절반이 두 갈래에서 다른 AV 비율(top-half disagreement).
    """
    rng = np.random.default_rng(seed)
    n_av, n_scen = M.shape
    spearman_vals = []
    kendall_vals = []
    top_disagree = []
    for _ in range(n_splits):
        perm = rng.permutation(n_scen)
        half_a = perm[:n_scen // 2]
        half_b = perm[n_scen // 2:]
        cr_a = np.nanmean(M[:, half_a], axis=1)
        cr_b = np.nanmean(M[:, half_b], axis=1)
        if np.isnan(cr_a).any() or np.isnan(cr_b).any():
            continue
        rho, _ = stats.spearmanr(cr_a, cr_b)
        tau, _ = stats.kendalltau(cr_a, cr_b)
        # top-half 순위 안 들어간 AV 비율
        rank_a = np.argsort(-cr_a)[: n_av // 2]
        rank_b = np.argsort(-cr_b)[: n_av // 2]
        disagree = 1.0 - len(set(rank_a.tolist()) & set(rank_b.tolist())) / max(len(rank_a), 1)
        spearman_vals.append(float(rho))
        kendall_vals.append(float(tau))
        top_disagree.append(float(disagree))
    sp = np.array(spearman_vals)
    kt = np.array(kendall_vals)
    td = np.array(top_disagree)
    return dict(
        n_splits=len(spearman_vals),
        spearman_mean=float(sp.mean()) if sp.size else float("nan"),
        spearman_p25=float(np.percentile(sp, 25)) if sp.size else float("nan"),
        kendall_mean=float(kt.mean()) if kt.size else float("nan"),
        top_half_disagreement_mean=float(td.mean()) if td.size else float("nan"),
        rank_reversal_observed=(sp.mean() < 0.7) if sp.size else False,
    )


def run_jsonl(jsonl_path: Path) -> None:
    rows = load_responses(jsonl_path)
    print(f">> loaded {len(rows)} response rows")
    M, av_list, scen_list = build_av_scenario_matrix(rows)
    print(f">> AV × scenario: {M.shape[0]} × {M.shape[1]}")
    print(f">> AV list: {av_list}")
    out = rank_reversal(M, n_splits=50)
    print(">> D1 순위 역전 결과:")
    for k, v in out.items():
        print(f"   {k}: {v}")


def run_sanity() -> None:
    """합성 (AV × scenario) 충돌률 매트릭스에서 순위 역전 재현.
    강건성 분산이 작은 AV 집단에 시나리오 다양성이 큰 경우 ρ가 낮아짐."""
    print(">> sanity check: AV=6 × scenario=40, 강건성·시나리오 difficulty 둘 다 분산 있음")
    rng = np.random.default_rng(42)
    n_av, n_scen = 6, 40
    theta = rng.normal(0, 0.5, n_av)
    b = rng.normal(0, 1.0, n_scen)
    M = np.zeros((n_av, n_scen))
    for i in range(n_av):
        for j in range(n_scen):
            p = 1 / (1 + np.exp(-(b[j] - theta[i])))
            M[i, j] = float(rng.binomial(10, p) / 10.0)
    out = rank_reversal(M, n_splits=50)
    for k, v in out.items():
        print(f"   {k}: {v}")


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
