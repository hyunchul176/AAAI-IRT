# -*- coding: utf-8 -*-
"""D4 sanity: LC 생성기 자체의 위험도와 SAC의 약함을 분리.

라운드 15 항목 2(K=30 자릿수 비교 정직성) 정정의 핵심 작업. K=30 재pilot에서
(SAC, LC, c=4) cell의 26.67% 충돌이 검증됐지만 그 자릿수가 "SAC가 expert보다 약하다"는
결론으로 직접 이어지지 않는다: 응시자·시나리오·생성기 세 변수가 모두 다른
비교라 reviewer가 즉시 잡는다. 본 sanity는 그 흠을 두 갈래로 푼다.

1. **본 pilot v3 K=20 결과 안의 응시자 차이 분석**. AV=3(SAC·basic·behavior) ×
   LC × c=0~4 × K=20 = 300셀의 충돌률 분포를 추출해, 같은 LC 생성기·같은 c·같은
   시나리오 위에서 세 응시자가 자릿수가 어떻게 달라지는지 본문에 적을 자료로
   다듬는다. (SAC, LC, c=4) cell은 K=20에서 K=30 26.67%와 자릿수 일관성 검증
   항목이기도 하다.

2. **dummy ego + LC × c × K=20 보조 격자**. ego가 LC 행동에 반응하지 않는
   "방어 없는 baseline" 조건으로 LC 자체의 위험도 분리. dummy ego는 SafeBench
   `agent/dummy.py`의 DummyAgent로 throttle=0.2, steer=0(가벼운 직진 가속)인
   설정이라 standstill은 아니지만 LC 분포 변화에 무반응이라는 점에서 baseline
   역할에 정합. 약 100셀(c 5수준 × K=20) × 약 9.3초 = 약 16분.

본문 활용 위치: `research/method.html`의 "측정 모델 운영 측 한계" 박스 셋째
단락(외부 비교점의 자릿수 일치 sanity), `research/plan.html`의 "격자 운영 한계
노트" 셋째 li(외부 비교점과의 자릿수 비교의 한정), plan.md §12 셋째 항목.

usage:
    # pilot v3 K=20 결과만 분석 (baseline 격자 실행 안 함)
    python3 analysis/d-grid-validation/d4_lc_baseline_sanity.py --analyze-only

    # dummy baseline 격자만 실행 (pilot v3 끝난 후)
    python3 analysis/d-grid-validation/d4_lc_baseline_sanity.py --baseline-only \\
        --container sb-pilot

    # 둘 다: 본 분석 + baseline 실행 + 종합 sanity 보고
    python3 analysis/d-grid-validation/d4_lc_baseline_sanity.py --container sb-pilot
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from math import sqrt
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "b4-pipeline"))
from pilot_monotonic_v3 import (  # noqa: E402
    G_SCENARIO_CFG, PilotCell, restart_carla, run_cell,
    CARLA_BOOT_WAIT_SEC,
)


# K=30 재pilot 결과 (라운드 14, sigma_scale=2.0 = c=4 조건). 본문 자릿수 비교 anchor.
K30_C4_NCOLLISION = 8
K30_C4_NCELLS = 30
K30_C4_RATE = K30_C4_NCOLLISION / K30_C4_NCELLS  # 0.267
K30_C4_CI = (0.142, 0.444)  # Wilson 95%

# FREA Table 2 자릿수 (expert·fppo_adv·Town02 Scenario 9, raw paper §4.5)
FREA_TABLE2_RATE = 0.090


def iter_baseline_cells(k_reps: int = 20) -> Iterable[PilotCell]:
    """dummy ego + LC × c=0~4 × K=20 = 100 셀. PilotCell 그대로 재사용해
    pilot_monotonic_v3.run_cell·extract_collision_and_cleanup 흐름을 흐름 그대로
    탄다. .log 파일은 v3_dummy_lc_*.log 형식 (PilotCell.exp_name 자동 산출).
    """
    cfg = G_SCENARIO_CFG["lc"]
    route_data = cfg["route_first_data"]  # LC sid=2 rid=0~3 data_id 40~79
    for c in [0.0, 1.0, 2.0, 3.0, 4.0]:
        for k in range(k_reps):
            rid, base_did = route_data[k % len(route_data)]
            data_id = base_did + (k // len(route_data))
            yield PilotCell(
                ego="dummy", g_id="lc", c_value=c, trial_k=k,
                sid=2, rid=rid, data_id=data_id,
            )


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% binomial CI. 표본 비율 p와 표본 크기 n으로 구간 반환."""
    if n == 0:
        return (float("nan"), float("nan"))
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    rad = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - rad, center + rad)


# --- 분석 측 ----------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def extract_cr_from_log(log_path: Path) -> float | None:
    """pilot v3 .log에서 collision_rate 값 추출 (ANSI escape 제거 후 grep)."""
    try:
        txt = _ANSI.sub("", log_path.read_text())
    except Exception:
        return None
    m = re.search(r"collision_rate\s+([0-9.]+)", txt)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def analyze_pilot_v3_lc(pilot_log_dir: Path) -> dict:
    """본 pilot v3 K=20 결과에서 AV=3 × LC × c=0~4 자릿수 분석.

    같은 LC 생성기·같은 c·같은 시나리오 위에서 SAC·basic·behavior 세 응시자의
    충돌률을 나란히 비교해 "응시자 차이가 만드는 자릿수 변화"를 보고한다.
    (SAC, LC, c=4)는 K=30 재pilot 26.67%와 자릿수 일관성 검증 자리.
    """
    egos = ["sac", "basic", "behavior"]
    c_levels = [0.0, 1.0, 2.0, 3.0, 4.0]
    table: dict[str, dict[float, dict]] = {ego: {} for ego in egos}
    for ego in egos:
        for c in c_levels:
            rates: list[float] = []
            for fp in sorted(pilot_log_dir.glob(f"v3_{ego}_lc_c{c}_k*.log")):
                cr = extract_cr_from_log(fp)
                if cr is not None:
                    rates.append(cr)
            n = len(rates)
            n_col = sum(1 for r in rates if r > 0)
            p = n_col / n if n else float("nan")
            lo, hi = wilson(p, n) if n else (float("nan"), float("nan"))
            table[ego][c] = dict(K=n, n_collision=n_col, p_hat=p,
                                 ci_lo=lo, ci_hi=hi)
    return table


def analyze_baseline(baseline_log_dir: Path) -> dict[float, dict]:
    """dummy + LC × c=0~4 K=20 결과 분석. LC 자체의 위험도 (방어 없는 baseline).

    PilotCell.exp_name이 v3_ 접두라 .log 파일도 v3_dummy_lc_*.log 형식으로 저장됨.
    baseline_log_dir이 pilot v3 디렉토리와 별도여서 이름 충돌은 없음.
    """
    out: dict[float, dict] = {}
    for c in [0.0, 1.0, 2.0, 3.0, 4.0]:
        rates: list[float] = []
        for fp in sorted(baseline_log_dir.glob(f"v3_dummy_lc_c{c}_k*.log")):
            cr = extract_cr_from_log(fp)
            if cr is not None:
                rates.append(cr)
        n = len(rates)
        n_col = sum(1 for r in rates if r > 0)
        p = n_col / n if n else float("nan")
        lo, hi = wilson(p, n) if n else (float("nan"), float("nan"))
        out[c] = dict(K=n, n_collision=n_col, p_hat=p, ci_lo=lo, ci_hi=hi)
    return out


def print_table(title: str, table: dict) -> None:
    print(f"\n=== {title} ===")
    print(f"{'ego':<10} {'c':>4} {'K':>4} {'col':>4} {'p̂':>7} {'Wilson 95% CI':>22}")
    print("-" * 56)
    if all(isinstance(v, dict) and "K" in v for v in table.values()):
        # baseline (c 키)
        for c, row in sorted(table.items()):
            print(f"{'dummy':<10} {c:>4.1f} {row['K']:>4} {row['n_collision']:>4}"
                  f" {row['p_hat']:>7.3f}  [{row['ci_lo']:.3f}, {row['ci_hi']:.3f}]")
    else:
        # pilot v3 (ego × c 중첩)
        for ego, sub in table.items():
            for c, row in sorted(sub.items()):
                print(f"{ego:<10} {c:>4.1f} {row['K']:>4} {row['n_collision']:>4}"
                      f" {row['p_hat']:>7.3f}  [{row['ci_lo']:.3f}, {row['ci_hi']:.3f}]")


def sanity_report(pilot_table: dict, baseline_table: dict | None) -> None:
    """본문 항목 2 정직성 검증의 핵심 결과 정리.

    (1) (SAC, LC, c=4) K=20 vs K=30 자릿수 일관성
    (2) 같은 LC·c 위에서 SAC·basic·behavior 응시자 자릿수 비교
    (3) dummy baseline vs SAC: LC 자체의 위험도와 SAC의 약함 분리
    (4) FREA Table 2 자릿수와의 차이: 응시자·시나리오·생성기 세 변수 차이 명시
    """
    print("\n=== 항목 2 (K=30 정직성) 검증 보고 ===")
    # (1) K=20 c=4 vs K=30
    sac_c4 = pilot_table.get("sac", {}).get(4.0)
    if sac_c4 and sac_c4["K"] > 0:
        lo20, hi20 = sac_c4["ci_lo"], sac_c4["ci_hi"]
        overlap = (lo20 <= K30_C4_CI[1] and hi20 >= K30_C4_CI[0])
        print(f"\n(1) (SAC, LC, c=4) K=20 vs K=30 재pilot 자릿수 일관성")
        print(f"    K=20: {sac_c4['n_collision']}/{sac_c4['K']} = {sac_c4['p_hat']:.3f}, "
              f"95% CI [{lo20:.3f}, {hi20:.3f}]")
        print(f"    K=30: {K30_C4_NCOLLISION}/{K30_C4_NCELLS} = {K30_C4_RATE:.3f}, "
              f"95% CI [{K30_C4_CI[0]:.3f}, {K30_C4_CI[1]:.3f}]")
        print(f"    두 CI 자릿수 겹침: {'예' if overlap else '아니오'} "
              f"→ 본문 자릿수 일관 보고 {'가능' if overlap else '불가능, 별도 단락 필요'}")
    # (2) 응시자 차이 자릿수
    print(f"\n(2) 같은 LC·c 위 응시자 차이 자릿수 (응시자 차이가 만드는 자릿수 변화)")
    for c in [0.0, 4.0]:
        cells = [(ego, pilot_table.get(ego, {}).get(c)) for ego in ("sac", "basic", "behavior")]
        cells = [(ego, r) for ego, r in cells if r and r["K"] > 0]
        if not cells:
            continue
        print(f"    c={c}: ", end="")
        for ego, r in cells:
            print(f"{ego}={r['p_hat']:.3f} (K={r['K']}, CI [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}])  ", end="")
        print()
    # (3) dummy baseline vs SAC
    if baseline_table:
        print(f"\n(3) dummy baseline (LC 자체의 위험도) vs SAC")
        for c in [0.0, 4.0]:
            base = baseline_table.get(c)
            sac = pilot_table.get("sac", {}).get(c)
            if base and sac and base["K"] > 0 and sac["K"] > 0:
                print(f"    c={c}: dummy={base['p_hat']:.3f} (K={base['K']})  "
                      f"sac={sac['p_hat']:.3f} (K={sac['K']})  "
                      f"→ SAC의 약함 = sac - dummy = {sac['p_hat']-base['p_hat']:+.3f}")
        print("    해석: dummy 충돌률은 LC가 가하는 위협 자체 + ego가 LC에 무반응한 결과,")
        print("          sac - dummy 자릿수가 SAC가 LC 위협을 회피하지 못한 자릿수를 알린다.")
    else:
        print(f"\n(3) dummy baseline 미실행 (--baseline-only 또는 --container 인자 필요)")
    # (4) FREA Table 2 비교 한계
    print(f"\n(4) FREA Table 2 자릿수 ({FREA_TABLE2_RATE:.3f}, expert·fppo_adv·Town02 Scenario 9)와의 비교 한계")
    print(f"    응시자 차이 (SAC vs AutoPilot expert)·생성기 차이 (patched LC vs fppo_adv)·")
    print(f"    시나리오 차이 (sid=2 vs Scenario 9) 세 변수가 모두 다르므로, 자릿수 비교는")
    print(f"    'SAC가 expert보다 약하다'는 결론으로 직접 이어지지 않는다. 본문 한정:")
    print(f"    '이 격자 조건에서 충돌이 random보다 통계적으로 크다'까지로 적는다.")


# --- 실행 측 ---------------------------------------------------------


def run_baseline_grid(container: str, log_dir: Path, dry_run: bool = False) -> dict:
    """dummy + LC × c=0~4 × K=20 = 100 셀. pilot v3와 같은 run_cell 흐름.

    매 50셀마다 CARLA 안전 재시작 (pilot v3 라운드 15 2차와 같은 정책).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_baseline_cells(k_reps=20))
    print(f">>> {len(cells)} baseline cells (dummy × lc × c=5 × K=20)")
    results = []
    t0 = time.time()
    from pilot_monotonic_v3 import extract_collision_and_cleanup
    for i, cell in enumerate(cells, 1):
        # 매 50셀마다 안전 재시작 (라운드 15 2차 결정)
        if not dry_run and i > 1 and (i - 1) % 50 == 0:
            restart_carla(container)
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        r = run_cell(cell, container, dry_run, log_dir)
        if not dry_run and r.get("rc") == 0:
            r["collision_rate"] = extract_collision_and_cleanup(container, cell, log_dir)
        results.append(r)
    summary_path = log_dir / "d4_lc_baseline_summary.json"
    summary_path.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    print(f">>> wall-clock {time.time() - t0:.0f}s, summary → {summary_path}")
    return dict(n_cells=len(cells), summary=str(summary_path))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-pilot")
    p.add_argument("--pilot-log-dir",
                   default="analysis/b4-pipeline/pilot_mono_v3_logs",
                   help="pilot v3 K=20 결과 디렉토리")
    p.add_argument("--baseline-log-dir",
                   default="analysis/d-grid-validation/d4_lc_baseline_logs",
                   help="dummy baseline 격자 결과 디렉토리")
    p.add_argument("--analyze-only", action="store_true",
                   help="baseline 실행 없이 pilot v3 결과만 분석")
    p.add_argument("--baseline-only", action="store_true",
                   help="baseline 격자만 실행 (분석 보고는 건너뜀)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    pilot_dir = Path(args.pilot_log_dir)
    base_dir = Path(args.baseline_log_dir)

    # 1. baseline 격자 실행
    if not args.analyze_only:
        if not pilot_dir.exists() and not args.baseline_only:
            print(f"!! pilot v3 log dir not found: {pilot_dir}. pilot v3 K=20이 끝난 뒤 "
                  f"--analyze-only 또는 그냥 다시 굴리세요.", file=sys.stderr)
        run_baseline_grid(args.container, base_dir, args.dry_run)
    # 2. 분석 보고
    if not args.baseline_only:
        if not pilot_dir.exists():
            print(f"!! pilot v3 log dir not found: {pilot_dir}, "
                  f"분석 건너뜀.", file=sys.stderr)
            return
        pilot_table = analyze_pilot_v3_lc(pilot_dir)
        print_table("본 pilot v3 K=20: AV=3 × LC × c=0~4", pilot_table)
        baseline_table = None
        if base_dir.exists():
            baseline_table = analyze_baseline(base_dir)
            if any(v["K"] > 0 for v in baseline_table.values()):
                print_table("D4 sanity baseline: dummy × LC × c=0~4 × K=20", baseline_table)
        sanity_report(pilot_table, baseline_table)


if __name__ == "__main__":
    main()
