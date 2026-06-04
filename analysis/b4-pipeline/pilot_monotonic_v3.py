# -*- coding: utf-8 -*-
"""단조성 pilot 3차: AV=3 × G=4 × c 5 × K=10 = 600 cells.

라운드 14 K=30 재pilot 후속. (sac, lc) c=0(sigma_scale 2.0) 자리에서 26.67%
충돌이 통계 검증된 신호임을 확인했고 SEVERITY_MAP['lc']을 가설 2 방향으로
반전(c=0→0.3, c=4→2.0)했다. pilot 3차는 그 반전 매핑 위에서 (AV, G) 쌍별
단조성 ρ ≥ 0.7 합격 자리 확인.

설계:
- AV=3 SafeBench tree (SAC·basic·behavior). PlanT는 FREA tree라 별도 분기.
  behavior는 라운드 14의 None-safety 패치 적용 자리.
- G=4 SafeBench tree (LC·idm_attack·mobil_attack·ordinary).
- c 5수준 × K=10.
- 총 3 × 4 × 5 × 10 = 600 cells, 셀당 ~10초, ETA ~1.7시간.

usage:
    python3 analysis/b4-pipeline/pilot_monotonic_v3.py --container sb-pilot --dry-run
    python3 analysis/b4-pipeline/pilot_monotonic_v3.py --container sb-pilot
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
from pilot_monotonic_v2 import extract_collision_and_cleanup  # noqa: E402


EGOS = ["sac", "basic", "behavior"]
GENERATORS = ["lc", "idm_attack", "mobil_attack", "ordinary"]
C_LEVELS = [0.0, 1.0, 2.0, 3.0, 4.0]
K_REPS = 10

# G별 (sid, rid, data_id) 카탈로그. sb-pilot 안 jsonl 기준으로 정렬.
G_SCENARIO_CFG = {
    # LC: adv_init_state.json sid=2 rid=0~3 data_id=40~79
    "lc": dict(yaml="LC.yaml", policy_type="lc", sid=2,
               route_first_data=[(0, 40), (1, 50), (2, 60), (3, 70)]),
    # idm·mobil: adv_behavior_single.json sid=8 rid=0~3 data_id=280~319
    "idm_attack":   dict(yaml="idm_attack.yaml",   policy_type="idm_attack",   sid=8,
                         route_first_data=[(0, 280), (1, 290), (2, 300), (3, 310)]),
    "mobil_attack": dict(yaml="mobil_attack.yaml", policy_type="mobil_attack", sid=8,
                         route_first_data=[(0, 280), (1, 290), (2, 300), (3, 310)]),
    # ordinary: scenario_id=0 (DummyPolicy, baseline). data_id 0~3.
    "ordinary": dict(yaml="ordinary.yaml", policy_type="ordinary", sid=0,
                     route_first_data=[(0, 0), (0, 1), (0, 2), (0, 3)]),
}


@dataclass(frozen=True)
class PilotCell:
    ego: str
    g_id: str
    c_value: float
    trial_k: int
    sid: int
    rid: int
    data_id: int

    @property
    def exp_name(self) -> str:
        return (
            f"v3_{self.ego}_{self.g_id}_c{self.c_value:.1f}_k{self.trial_k:02d}"
            f"_s{self.sid}r{self.rid}d{self.data_id}"
        )


def iter_pilot_cells() -> Iterable[PilotCell]:
    for ego in EGOS:
        for g in GENERATORS:
            cfg = G_SCENARIO_CFG[g]
            route_data = cfg["route_first_data"]
            for c in C_LEVELS:
                for k in range(K_REPS):
                    rid, base_did = route_data[k % len(route_data)]
                    data_id = base_did + (k // len(route_data))
                    yield PilotCell(
                        ego=ego, g_id=g, c_value=c, trial_k=k,
                        sid=cfg["sid"], rid=rid, data_id=data_id,
                    )


def run_cell(cell: PilotCell, container: str, dry_run: bool, log_dir: Path) -> dict:
    cfg = G_SCENARIO_CFG[cell.g_id]
    scenario_cfg = cfg["yaml"]
    policy_type = cfg["policy_type"]
    agent_cfg = f"{cell.ego}.yaml"
    cmd_inside = (
        "export SDL_VIDEODRIVER=dummy && "
        "cd /home/safebench/SafeBench && "
        "python aaai_orchestrator/run_one_cell.py "
        "--safebench-root /home/safebench/SafeBench --tree safebench "
        f"--agent-cfg {agent_cfg} --scenario-cfg {scenario_cfg} --policy-type {policy_type} "
        f"--sid {cell.sid} --rid {cell.rid} --data-id {cell.data_id} "
        f"--c-value {cell.c_value} --seed 0 "
        f"--exp-name {cell.exp_name} --port 2000 --tm-port 8000 --num-scenario 1"
    )
    pythonpath = (
        "/home/safebench/carla/PythonAPI/carla/dist/carla-0.9.13-py3.8-linux-x86_64.egg:"
        "/home/safebench/carla/PythonAPI/carla/agents:"
        "/home/safebench/carla/PythonAPI/carla:"
        "/home/safebench/carla/PythonAPI"
    )
    docker_cmd = [
        "docker", "exec", container, "bash", "-lc",
        f"export PYTHONPATH={pythonpath} && {cmd_inside}",
    ]
    log_path = log_dir / f"{cell.exp_name}.log"
    if dry_run:
        return dict(cell=asdict(cell), cmd=docker_cmd, dry_run=True)
    t0 = time.time()
    with open(log_path, "w") as f:
        p = subprocess.run(docker_cmd, stdout=f, stderr=subprocess.STDOUT, timeout=240)
    return dict(cell=asdict(cell), rc=p.returncode, wall_sec=time.time() - t0,
                log=str(log_path))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-pilot")
    p.add_argument("--log-dir", default="analysis/b4-pipeline/pilot_mono_v3_logs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_pilot_cells())
    print(f">>> {len(cells)} pilot v3 cells "
          f"(ego={len(EGOS)} × G={len(GENERATORS)} × c={len(C_LEVELS)} × K={K_REPS})")

    results = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        r = run_cell(cell, args.container, args.dry_run, log_dir)
        if not args.dry_run and r.get("rc") == 0:
            r["collision_rate"] = extract_collision_and_cleanup(args.container, cell, log_dir)
        results.append(r)

    summary_path = log_dir / "pilot_mono_v3_summary.json"
    summary_path.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    print(f">>> wall-clock {time.time() - t0:.0f}s, summary -> {summary_path}")


if __name__ == "__main__":
    main()
