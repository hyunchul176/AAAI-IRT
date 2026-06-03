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
    d = json.load(open(path))
    by_ego_c: dict[tuple[str, float], list[float]] = defaultdict(list)
    fails: list[dict] = []
    for r in d["results"]:
        c = r["cell"]
        ego = c["ego"]
        cval = c["c_value"]
        cr = r.get("collision_rate")
        if cr is None:
            fails.append(c)
            continue
        by_ego_c[(ego, cval)].append(float(cr))
    return dict(by_ego_c=by_ego_c, n_fails=len(fails),
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

    # ego별 그룹
    by_ego: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (ego, c), rates in s["by_ego_c"].items():
        by_ego[ego][c] = rates

    for ego in sorted(by_ego):
        print(f"=== ego = {ego} ===")
        by_c = by_ego[ego]
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
        print(f"  → ρ ≥ 0.7: {flag},  bootstrap p5 ≥ 0.5: {flag_low}")
        print()


if __name__ == "__main__":
    main()
