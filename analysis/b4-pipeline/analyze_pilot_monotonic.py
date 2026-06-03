# -*- coding: utf-8 -*-
"""단조성 pilot 결과 분석.

100 cells pilot(`pilot_mono_summary.json`)에서 (ego, c) 쌍별 충돌률 평균과
표준오차를 계산하고, (ego, G=fppo_adv) 쌍별 Spearman 순위 상관 ρ로
단조성을 검정한다. 합격선은 생성기·severity 결정의 ρ ≥ 0.7, 보조 기준은
bootstrap 5 percentile ≥ 0.5.

usage:
    python3 analysis/b4-pipeline/analyze_pilot_monotonic.py \
        analysis/b4-pipeline/pilot_mono_logs/pilot_mono_summary.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict

from scipy import stats


def summarize(path: str) -> dict:
    """pilot v1 (fppo_adv 한 G만, key=(ego, c)) + v2 ((ego, G, c) 3차원) 둘 다
    지원한다. v1 결과에는 cell.g_id가 'fppo_adv'로 고정되어 있고 v2 결과는
    여러 G를 갖는다. 출력은 (ego, g, c) 3차원 dict로 통일.
    """
    d = json.load(open(path))
    by_ego_g_c: dict[tuple[str, str, float], list[float]] = defaultdict(list)
    fails: list[dict] = []
    for r in d["results"]:
        c = r["cell"]
        ego = c["ego"]
        g_id = c.get("g_id", "fppo_adv")  # v1은 cell에 g_id 없음 → fppo_adv
        cval = c["c_value"]
        cr = r.get("collision_rate")
        if cr is None:
            fails.append(c)
            continue
        by_ego_g_c[(ego, g_id, cval)].append(float(cr))
    return dict(by_ego_g_c=by_ego_g_c, n_fails=len(fails),
                wall_sec=d.get("wall_sec"), total=d.get("n_cells"))


def spearman_monotonic(by_c: dict[float, list[float]]) -> tuple[float, float, list[tuple[float, float]]]:
    """ego별 (c_value, individual_trial_rate) 쌍 위에서 Spearman ρ를 계산.

    합격선 ρ ≥ 0.7 (생성기·severity 결정의 1차 합격). 같은 c에 여러 trial이
    있으니 c가 동률인 점이 많지만 그 자체로는 ρ가 잘 정의됨.
    """
    xs, ys = [], []
    for c, rates in sorted(by_c.items()):
        for r in rates:
            xs.append(c)
            ys.append(r)
    if len(xs) < 5:
        return float("nan"), float("nan"), []
    rho, p = stats.spearmanr(xs, ys)
    return float(rho), float(p), list(zip(xs, ys))


def bootstrap_p5(xs: list[float], ys: list[float], n_boot: int = 2000, seed: int = 0) -> float:
    """ρ의 5 percentile (편측 95% 하한 신뢰선)을 bootstrap으로 추정.
    pilot 표본이 작아 점추정 하나만으로는 분산이 가려진다.
    """
    import random
    random.seed(seed)
    n = len(xs)
    rhos = []
    for _ in range(n_boot):
        idx = [random.randint(0, n - 1) for _ in range(n)]
        bx = [xs[i] for i in idx]
        by = [ys[i] for i in idx]
        if len(set(bx)) < 2 or len(set(by)) < 2:
            continue
        r, _ = stats.spearmanr(bx, by)
        if not math.isnan(r):
            rhos.append(float(r))
    rhos.sort()
    return rhos[int(0.05 * len(rhos))] if rhos else float("nan")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    s = summarize(path)
    print(f">> pilot summary: {s['total']} cells, wall {s['wall_sec']:.0f}s, "
          f"{s['n_fails']} failed")
    print()

    # (ego, g) 쌍별로 c × rates 그룹
    by_eg: dict[tuple[str, str], dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (ego, g, c), rates in s["by_ego_g_c"].items():
        by_eg[(ego, g)][c] = rates

    n_pass = 0
    n_total = len(by_eg)
    for (ego, g) in sorted(by_eg):
        print(f"=== (ego={ego}, G={g}) ===")
        by_c = by_eg[(ego, g)]
        for c in sorted(by_c):
            rates = by_c[c]
            mean = sum(rates) / len(rates)
            sd = math.sqrt(sum((x - mean) ** 2 for x in rates) / len(rates)) if len(rates) > 1 else 0.0
            print(f"  c={c}: n={len(rates):2d} mean={mean:.3f} sd={sd:.3f}  raw={rates}")
        rho, p, pairs = spearman_monotonic(by_c)
        xs = [x for x, _ in pairs]
        ys = [y for _, y in pairs]
        p5 = bootstrap_p5(xs, ys) if pairs else float("nan")
        print(f"  Spearman ρ = {rho:.3f} (p={p:.3f}), bootstrap 5%-low = {p5:.3f}")
        flag = "PASS" if rho >= 0.7 else "FAIL"
        flag_low = "PASS" if p5 >= 0.5 else "FAIL"
        passed = (rho >= 0.7)
        if passed:
            n_pass += 1
        print(f"  → ρ ≥ 0.7: {flag},  bootstrap p5 ≥ 0.5: {flag_low}")
        print()

    print(f">> 합격 (ego, G) 쌍: {n_pass}/{n_total}")
    # 본 격자 진입 두 종 합격 조건은 G 단위에서 본다(같은 G가 어느 ego에서도
    # 합격하면 그 G는 1 종 합격으로 카운트). 검토자 라운드 10 권고.
    g_pass: dict[str, bool] = defaultdict(bool)
    for (ego, g) in sorted(by_eg):
        by_c = by_eg[(ego, g)]
        rho, _, _ = spearman_monotonic(by_c)
        if rho >= 0.7:
            g_pass[g] = True
    n_g_pass = sum(1 for v in g_pass.values() if v)
    print(f">> 합격 G 종 수: {n_g_pass} (본 격자 진입 조건: ≥ 2)")


if __name__ == "__main__":
    main()
