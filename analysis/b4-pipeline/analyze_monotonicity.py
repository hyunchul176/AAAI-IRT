# -*- coding: utf-8 -*-
"""단조성 검정: pilot v3 K=20 결과에서 (AV × G) 조합별 c→충돌률 단조성 산출.

각 시나리오 생성기 G(LC, IDM 공격, MOBIL 공격)에 대하여 위험도 c=0,1,2,3,4의
충돌률 곡선을 응시자(AV)별로 산출하고, Spearman 상관계수 ρ(c, 충돌률)와 합격선
ρ ≥ 0.7 통과 여부를 표로 정리한다. ordinary는 위험도 무관 baseline이므로 단조
검정에서 제외하고, baseline 비교를 위해 평균 충돌률만 보고한다.

본 격자 진입 조건: 두 개 이상의 생성기에서 단조성을 통과해야 한다. 이는 D2
표본불변성 검증에서 G 부분집합 분리가 의미를 갖기 위한 사전 조건이다.

usage:
    python3 analysis/b4-pipeline/analyze_monotonicity.py
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats


LOG_DIR = Path("/home/hyunchul/AAAI/analysis/b4-pipeline/pilot_mono_v3_logs")
EGOS = ["sac", "basic", "behavior"]
GENERATORS = ["lc", "idm_attack", "mobil_attack", "ordinary"]
C_LEVELS = [0.0, 1.0, 2.0, 3.0, 4.0]
PASS_LINE = 0.7

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def extract_collision_rate(log_path: Path) -> float | None:
    try:
        txt = _ANSI.sub("", log_path.read_text())
    except Exception:
        return None
    m = re.search(r"collision_rate\s+([0-9.]+)", txt)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def collect_rates() -> dict:
    """{(ego, g, c): [rate1, rate2, ...]} 구조로 충돌률 모음."""
    rates = defaultdict(list)
    for log_path in sorted(LOG_DIR.glob("v3_*.log")):
        name = log_path.stem
        parts = name.split("_")
        if len(parts) < 4 or parts[0] != "v3":
            continue
        ego = parts[1]
        if ego not in EGOS:
            continue
        if "lc" in parts:
            g = "lc"
        elif "idm" in parts:
            g = "idm_attack"
        elif "mobil" in parts:
            g = "mobil_attack"
        elif "ordinary" in parts:
            g = "ordinary"
        else:
            continue
        c_match = re.search(r"_c(\d\.\d)_", name)
        if not c_match:
            continue
        c = float(c_match.group(1))
        cr = extract_collision_rate(log_path)
        if cr is not None:
            rates[(ego, g, c)].append(cr)
    return rates


def main() -> None:
    rates = collect_rates()

    # 1. (AV × G × c) 평균 충돌률 표
    print("=" * 78)
    print("(AV × G × c) 평균 충돌률 (K=20)")
    print("=" * 78)
    print(f"{'AV':<10} {'G':<15} {'c=0':>8} {'c=1':>8} {'c=2':>8} {'c=3':>8} {'c=4':>8}")
    print("-" * 78)
    for ego in EGOS:
        for g in GENERATORS:
            row = [f"{ego:<10}", f"{g:<15}"]
            for c in C_LEVELS:
                vals = rates.get((ego, g, c), [])
                if vals:
                    avg = sum(vals) / len(vals)
                    row.append(f"{avg:>8.3f}")
                else:
                    row.append(f"{'--':>8}")
            print(" ".join(row))
        print()

    # 2. (AV × G) Spearman ρ + 합격 여부
    print("=" * 78)
    print("(AV × G) 단조성 Spearman ρ (ordinary 제외)")
    print("=" * 78)
    print(f"{'AV':<10} {'G':<15} {'ρ':>8} {'p-value':>10} {'합격':>8}")
    print("-" * 78)
    rho_table = {}
    for ego in EGOS:
        for g in ("lc", "idm_attack", "mobil_attack"):
            c_arr = []
            rate_arr = []
            for c in C_LEVELS:
                vals = rates.get((ego, g, c), [])
                if vals:
                    avg = sum(vals) / len(vals)
                    c_arr.append(c)
                    rate_arr.append(avg)
            if len(c_arr) >= 3:
                rho, p = stats.spearmanr(c_arr, rate_arr)
                rho_table[(ego, g)] = (rho, p)
                pass_str = "PASS" if rho >= PASS_LINE else "FAIL"
                print(f"{ego:<10} {g:<15} {rho:>8.3f} {p:>10.4f} {pass_str:>8}")
            else:
                print(f"{ego:<10} {g:<15} {'insufficient':>30}")
        print()

    # 3. G별 종합 단조성 (응시자 평균 충돌률의 c별 단조 ρ)
    print("=" * 78)
    print("G별 종합 단조성 (응시자 평균 충돌률의 c별 단조 ρ)")
    print("=" * 78)
    print(f"{'G':<15} {'ρ':>8} {'p-value':>10} {'합격':>8}")
    print("-" * 78)
    g_pass = {}
    for g in ("lc", "idm_attack", "mobil_attack"):
        c_arr = []
        rate_arr = []
        for c in C_LEVELS:
            ego_rates = []
            for ego in EGOS:
                vals = rates.get((ego, g, c), [])
                if vals:
                    ego_rates.append(sum(vals) / len(vals))
            if ego_rates:
                c_arr.append(c)
                rate_arr.append(sum(ego_rates) / len(ego_rates))
        if len(c_arr) >= 3:
            rho, p = stats.spearmanr(c_arr, rate_arr)
            g_pass[g] = (rho, p, rho >= PASS_LINE)
            pass_str = "PASS" if rho >= PASS_LINE else "FAIL"
            print(f"{g:<15} {rho:>8.3f} {p:>10.4f} {pass_str:>8}")

    # 4. 본 격자 진입 조건 점검
    print()
    print("=" * 78)
    print("본 격자 진입 조건 점검")
    print("=" * 78)
    n_pass = sum(1 for v in g_pass.values() if v[2])
    print(f"단조성 통과 생성기 수: {n_pass}/3")
    if n_pass >= 2:
        print(f">>> 본 격자 진입 조건 충족 (두 개 이상의 G 통과)")
        passed = [g for g, v in g_pass.items() if v[2]]
        print(f">>> 통과 생성기: {', '.join(passed)}")
        print(f">>> plan §13 셋째 기여(다양한 표준 단순 생성기 위에서 척도 안정)가 본문에서 유지됨")
    elif n_pass == 1:
        passed = [g for g, v in g_pass.items() if v[2]]
        print(f">>> 본 격자 진입 조건 미충족 (한 개의 G만 통과: {', '.join(passed)})")
        print(f">>> contribution을 '단일 생성기 안에서의 SUT-불변 측정 모델 형식화'로 좁히는 결정 검토")
    else:
        print(f">>> 본 격자 진입 조건 미충족 (모든 G가 단조성 검정 실패)")
        print(f">>> γ_G·c 항을 비단조 함수로 일반화하는 방향 또는 G 다이얼 재설계 검토")

    # 5. ordinary baseline 자릿수 (참고)
    print()
    print("=" * 78)
    print("ordinary baseline 평균 충돌률 (c와 무관, 참고용)")
    print("=" * 78)
    for ego in EGOS:
        all_vals = []
        for c in C_LEVELS:
            all_vals.extend(rates.get((ego, "ordinary", c), []))
        if all_vals:
            avg = sum(all_vals) / len(all_vals)
            print(f"  {ego:<10}: {avg:.3f}  (n={len(all_vals)})")


if __name__ == "__main__":
    main()
