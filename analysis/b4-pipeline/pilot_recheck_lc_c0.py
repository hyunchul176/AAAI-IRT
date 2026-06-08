# -*- coding: utf-8 -*-
"""(sac, lc) c=0의 K=30 재pilot : 신호 vs 잡음 검증.

라운드 14 검토자 권고: pilot v2에서 c=0에서만 3/10 충돌, 나머지 0. 이항 K=10·p=0.05
일 때 우연 3건 이상 1.2% 확률이라 약하게 받쳐지지만 K=30·40으로 측정해 30% 충돌이
실제 신호인지(다이얼 작동), 아니면 잡음(우연)인지 가른다. 다이얼 약점 진단의 결정
단계.

설계: 1 ego(sac) × 1 G(lc) × c=0 × K=30 = 30 cells. Town02 한정 (sid=2, rid=0~3,
data_id=40~79 순환). c=0 한 조건만 ρ 검정 무의미 → 충돌률 30/30의 binomial CI로
0.30이 0.05(random) 또는 0.10(FREA Table 2)과 통계적으로 다른지만 본다.

usage:
    python3 analysis/b4-pipeline/pilot_recheck_lc_c0.py --container sb-pilot
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_monotonic_v2 import extract_collision_and_cleanup, run_cell  # noqa: E402
from pilot_monotonic_v2 import PilotCell  # noqa: E402


# LC catalog Town02 한정 (sid=2, rid=0~3, data_id=40~79)
ROUTE_DATA = [(0, 40), (1, 50), (2, 60), (3, 70)]
K_REPS = 30


def iter_cells() -> Iterable[PilotCell]:
    for k in range(K_REPS):
        rid, base = ROUTE_DATA[k % len(ROUTE_DATA)]
        data_id = base + (k // len(ROUTE_DATA))
        yield PilotCell(
            ego="sac", g_id="lc", c_value=0.0, trial_k=k,
            sid=2, rid=rid, data_id=data_id,
        )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-pilot")
    p.add_argument("--log-dir", default="analysis/b4-pipeline/pilot_recheck_lc_c0_logs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_cells())
    print(f">>> {len(cells)} cells (sac, lc, c=0, K={K_REPS})")
    results = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        r = run_cell(cell, args.container, args.dry_run, log_dir)
        if not args.dry_run and r.get("rc") == 0:
            r["collision_rate"] = extract_collision_and_cleanup(args.container, cell, log_dir)
        results.append(r)
    summary = log_dir / "pilot_recheck_summary.json"
    summary.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    # 통계 분석
    cr = [r.get("collision_rate") for r in results if r.get("collision_rate") is not None]
    n_ok = len(cr)
    n_collision = sum(int(x > 0) for x in cr)
    p_hat = n_collision / n_ok if n_ok else float("nan")
    print()
    print(f">>> wall {time.time() - t0:.0f}s")
    print(f">>> 작동 cells: {n_ok}/{len(cells)}, 충돌: {n_collision} ({p_hat:.2%})")
    if n_ok >= 10:
        # Wilson 95% CI (이항)
        from math import sqrt
        z = 1.96
        denom = 1 + z * z / n_ok
        center = (p_hat + z * z / (2 * n_ok)) / denom
        radius = z * sqrt(p_hat * (1 - p_hat) / n_ok + z * z / (4 * n_ok ** 2)) / denom
        ci_lo = center - radius
        ci_hi = center + radius
        print(f">>> Wilson 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
        print(f">>> p=0.05 random 잡음과 다름? {'예' if ci_lo > 0.05 else '아니오'}")
        print(f">>> p=0.10 FREA Table 2 자릿수와 다름? {'예' if ci_lo > 0.10 else '아니오'}")


if __name__ == "__main__":
    main()
