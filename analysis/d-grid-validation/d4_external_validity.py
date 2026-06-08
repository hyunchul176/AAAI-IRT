# -*- coding: utf-8 -*-
"""D4 외적 타당성: 추정 b̂이 외부 난이도 지표와 일치하는가.

섹션 C의 외부 난이도 지표(Wagner TTR, Yu complexity, Tulpule value function,
Kurian R_p)와 우리 추정 시나리오 난이도 b̂(시나리오별 평균)의 Spearman ρ를
보고. expert reference policy의 충돌률 분포도 자릿수 일치로 비교(검토자 라운드
10·11이 짚은 단계: 척도 일치 scale linking은 시도하지 않고 rank correlation
sanity check 수준).

외부 지표는 CSV로 받는다. 헤더: scenario_id,route_id,data_id,wagner_ttr,
yu_complexity,tulpule_value,kurian_rp,expert_collision_rate. 일부 열은 비워도
되며 비어 있는 항목은 NaN으로 처리.

usage:
    python3 analysis/d-grid-validation/d4_external_validity.py \\
        analysis/b4-pipeline/responses.jsonl \\
        analysis/external_indices.csv
    python3 analysis/d-grid-validation/d4_external_validity.py --sanity
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "d-study"))
from d_study import fit_map, b_item_grid, simulate_responses, draw_true_params  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d2_split_half import load_responses, build_resp_dict  # noqa: E402


EXTERNAL_COLS = ["wagner_ttr", "yu_complexity", "tulpule_value", "kurian_rp", "expert_collision_rate"]


def load_external_csv(csv_path: Path) -> dict[tuple, dict]:
    """CSV → {(sid, rid, data_id): {지표명: 값 or NaN}}."""
    out: dict[tuple, dict] = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (int(row["scenario_id"]), int(row["route_id"]), int(row["data_id"]))
            out[key] = {col: float(row[col]) if row.get(col) not in (None, "") else float("nan")
                        for col in EXTERNAL_COLS}
    return out


def compute_b_per_scenario(resp: dict, f: dict) -> np.ndarray:
    """fit_map 결과 + resp의 C로 (G × n_sev) b 매트릭스. b_item_grid의 형식."""
    return b_item_grid(f["beta"], f["gamma"], resp["C"])


def run_d4(resp: dict, external: dict | None = None, seed: int = 0) -> dict:
    """우리 b̂(시나리오 난이도)을 시나리오별 평균 difficulty로 정리. 외부 지표가
    있으면 Spearman ρ + scatter pair. 없으면 b̂ 분포 통계만.
    """
    f = fit_map(resp, fix_u=None, use_prior=True, seed=seed)
    # b는 (G, sev) 매트릭스. G별 평균 difficulty를 G 인덱스에 대응시킨다.
    b_mat = compute_b_per_scenario(resp, f)
    b_per_g = b_mat.mean(axis=1)  # G별 평균
    out = dict(
        b_per_G=dict(zip(resp.get("g_list", list(range(resp["n_g"]))),
                         [float(x) for x in b_per_g])),
        b_min=float(b_mat.min()),
        b_max=float(b_mat.max()),
        converged=f.get("converged", False),
    )
    if external is None:
        out["external"] = "none provided"
        return out
    # 외부 지표 평균 (G 단위로 모음. CSV의 (sid, rid, data_id)가 G 매핑이 안
    # 명시되어 있어 우선 G별 평균 매핑만 본다. 본 격자 진입 후 정확한 매핑은
    # CSV에 g_id 열 추가).
    ext_per_g = {col: [] for col in EXTERNAL_COLS}
    for g_id, b_val in zip(resp.get("g_list", list(range(resp["n_g"]))), b_per_g):
        # 같은 g_id의 외부 지표 값들 평균
        vals_by_col = {col: [] for col in EXTERNAL_COLS}
        for key, ext in external.items():
            for col in EXTERNAL_COLS:
                if not np.isnan(ext[col]):
                    vals_by_col[col].append(ext[col])
        for col in EXTERNAL_COLS:
            ext_per_g[col].append(float(np.nanmean(vals_by_col[col])) if vals_by_col[col] else float("nan"))
    # Spearman ρ (b̂_per_G vs 각 외부 지표)
    out["spearman_vs_external"] = {}
    for col in EXTERNAL_COLS:
        vals = np.array(ext_per_g[col])
        if np.isnan(vals).any() or len(vals) < 3:
            out["spearman_vs_external"][col] = "insufficient"
            continue
        rho, p = stats.spearmanr(b_per_g, vals)
        out["spearman_vs_external"][col] = dict(rho=float(rho), p=float(p))
    return out


def run_jsonl(jsonl_path: Path, csv_path: Path | None) -> None:
    rows = load_responses(jsonl_path)
    print(f">> loaded {len(rows)} response rows")
    resp = build_resp_dict(rows)
    external = load_external_csv(csv_path) if csv_path else None
    if external:
        print(f">> loaded {len(external)} external index rows")
    out = run_d4(resp, external)
    print(">> D4 외적 타당성 결과:")
    for k, v in out.items():
        print(f"   {k}: {v}")


def run_sanity() -> None:
    print(">> sanity check (synthetic): AV=6 × G=3 × c=5 × K=10, 외부 지표 없음")
    rng = np.random.default_rng(42)
    true = draw_true_params(n_av=6, n_g=3, rng=rng)
    resp = simulate_responses(true, n_sev=5, K=10, sev_placement="uniform", rng=rng)
    out = run_d4(resp, external=None)
    for k, v in out.items():
        print(f"   {k}: {v}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="?", default=None)
    p.add_argument("external", nargs="?", default=None)
    p.add_argument("--sanity", action="store_true")
    args = p.parse_args()
    if args.sanity:
        run_sanity()
    elif args.jsonl:
        run_jsonl(Path(args.jsonl),
                  Path(args.external) if args.external else None)
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
