# -*- coding: utf-8 -*-
"""단조성 검정 (highway-env 격자 jsonl 입력판).

`run_aaai_grid.py`가 산출한 응답 jsonl에서 (AV × G × c) 충돌률을 추출하고, 각
시나리오 생성기 G에 대해 위험도 c와 충돌률의 Spearman 상관계수 ρ를 산출한다.
합격선은 ρ ≥ 0.7이며 두 생성기 이상이 통과해야 본 격자 진입이 허용된다.

기존 `analysis/b4-pipeline/analyze_monotonicity.py`(SafeBench .log 입력 자료)를
jsonl 입력판으로 일반화한 자료이다.

usage:
    python3 analysis/highway_grid/analyze_monotonicity_jsonl.py \\
        --jsonl analysis/highway_grid/pilot_responses.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path

import numpy as np
from scipy import stats


PASS_LINE = 0.7


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    rad = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - rad, center + rad)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", required=True, help="응답 jsonl 경로")
    args = p.parse_args()

    rows = load_jsonl(Path(args.jsonl))
    print(f">> 응답 {len(rows)} 건 로드")

    # (av, g, c) → 충돌 list
    rates: dict = defaultdict(list)
    for r in rows:
        if "error" in r:
            continue
        rates[(r["av_id"], r["g_id"], float(r["c"]))].append(int(r["y"]))

    av_ids = sorted({k[0] for k in rates})
    g_ids = sorted({k[1] for k in rates})
    c_values = sorted({k[2] for k in rates})

    # 1. (AV × G × c) 평균 충돌률
    print("\n" + "=" * 78)
    print("(AV × G × c) 평균 충돌률")
    print("=" * 78)
    header = "AV          G                " + " ".join(f"c={c:>4.0f}" for c in c_values)
    print(header)
    print("-" * len(header))
    for av in av_ids:
        for g in g_ids:
            row = [f"{av:<11}", f"{g:<15}"]
            for c in c_values:
                ys = rates.get((av, g, c), [])
                if ys:
                    p_hat = sum(ys) / len(ys)
                    row.append(f"{p_hat:>5.2f}")
                else:
                    row.append(f"{'--':>5}")
            print(" ".join(row))
        print()

    # 2. (AV × G) 단조성 ρ
    print("=" * 78)
    print("(AV × G) 단조성 Spearman ρ")
    print("=" * 78)
    print(f"{'AV':<12} {'G':<15} {'n':>4} {'ρ':>8} {'p-value':>10} {'합격':>8}")
    print("-" * 60)
    for av in av_ids:
        for g in g_ids:
            cs, ps = [], []
            for c in c_values:
                ys = rates.get((av, g, c), [])
                if ys:
                    cs.append(c)
                    ps.append(sum(ys) / len(ys))
            if len(cs) >= 3 and len(set(ps)) > 1:
                rho, pv = stats.spearmanr(cs, ps)
                ok = "PASS" if rho >= PASS_LINE else "FAIL"
                print(f"{av:<12} {g:<15} {len(cs):>4} {rho:>8.3f} {pv:>10.4f} {ok:>8}")
            else:
                p_hat = float(np.mean(ps)) if ps else float("nan")
                note = f"constant (p={p_hat:.2f})" if len(set(ps)) == 1 else "insufficient"
                print(f"{av:<12} {g:<15} {len(cs):>4} {note:>30}")
        print()

    # 3. G별 종합 단조성 (응시자 평균 충돌률의 c별 단조 ρ)
    print("=" * 78)
    print("G별 종합 단조성 (응시자 평균 충돌률의 c별 단조 ρ)")
    print("=" * 78)
    print(f"{'G':<15} {'ρ':>8} {'p-value':>10} {'합격':>8}")
    print("-" * 50)
    g_pass: dict = {}
    for g in g_ids:
        cs, ps = [], []
        for c in c_values:
            ego_rates = []
            for av in av_ids:
                ys = rates.get((av, g, c), [])
                if ys:
                    ego_rates.append(sum(ys) / len(ys))
            if ego_rates:
                cs.append(c)
                ps.append(float(np.mean(ego_rates)))
        if len(cs) >= 3 and len(set(ps)) > 1:
            rho, pv = stats.spearmanr(cs, ps)
            g_pass[g] = (rho, pv, rho >= PASS_LINE)
            ok = "PASS" if rho >= PASS_LINE else "FAIL"
            print(f"{g:<15} {rho:>8.3f} {pv:>10.4f} {ok:>8}")
        else:
            print(f"{g:<15} {'insufficient or constant':>30}")
            g_pass[g] = (float("nan"), float("nan"), False)

    # 4. 본 격자 진입 조건
    print("\n" + "=" * 78)
    print("본 격자 진입 조건 점검")
    print("=" * 78)
    passed_gs = [g for g, v in g_pass.items() if v[2]]
    n_pass = len(passed_gs)
    print(f"단조성 통과 생성기 수: {n_pass}/{len(g_ids)}")
    if n_pass >= 2:
        print(f">>> 본 격자 진입 조건 충족 (두 생성기 이상 통과)")
        print(f">>> 통과 생성기: {', '.join(passed_gs)}")
        print(">>> plan §13 셋째 기여(다양한 표준 단순 생성기 위에서 척도 안정)가 본문에서 유지됨")
    elif n_pass == 1:
        print(f">>> 본 격자 진입 조건 미충족 (한 생성기만 통과: {passed_gs[0]})")
        print(">>> contribution을 단일 생성기 안 SUT-불변 측정 모델 형식화로 좁히는 결정 검토")
    else:
        print(">>> 본 격자 진입 조건 미충족 (모든 생성기 미통과)")
        print(">>> γ_G·c 항 비단조 일반화 또는 다이얼 재설계 검토 필요")


if __name__ == "__main__":
    main()
