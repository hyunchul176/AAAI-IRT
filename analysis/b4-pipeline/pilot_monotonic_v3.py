# -*- coding: utf-8 -*-
"""단조성 pilot 3차: AV=3 × G=4 × c 5 × K=20 = 1200 cells.

라운드 14 K=30 재pilot 후속. (sac, lc) c=0(sigma_scale 2.0) 조건에서 26.67%
충돌이 통계 검증된 신호임을 확인했고 SEVERITY_MAP['lc']을 가설 2 방향으로
반전(c=0→0.3, c=4→2.0)했다. pilot 3차는 그 반전 매핑 위에서 (AV, G) 쌍별
단조성 ρ ≥ 0.7 합격 여부 확인.

라운드 15 재실행: 1차 시도(K=10)는 sac×lc 35셀 완료 후 CARLA UE4가 컨테이너 안에서
망가져 이후 셀이 전부 load_world 30초 timeout으로 흘러간 흐름. 원인은 셀 사이 CARLA
메모리 누수. 재실행에서는 (1) K=10→20 통계력 보강, (2) 매 RESTART_EVERY 셀마다
CARLA를 컨테이너 안에서 안전 재시작해 누수를 끊는다.

설계:
- AV=3 SafeBench tree (SAC·basic·behavior). PlanT는 FREA tree라 별도 분기.
  behavior는 라운드 14의 None-safety 패치 적용 대상.
- G=4 SafeBench tree (LC·idm_attack·mobil_attack·ordinary).
- c 5수준 × K=20.
- 총 3 × 4 × 5 × 20 = 1200 cells, 셀당 ~1분, ETA ~20시간.

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
K_REPS = 20

# 라운드 15 2차: CARLA 메모리 누수 끊는 단계. K=20 1차 시도에서 RESTART_EVERY=100은
# 부족함이 확인됐다 : 누수가 셀 약 80~90 지점에서 발현되어 sac × lc·idm 모두 c=4
# 후반 구간에서 timeout cascade. 50 셀마다 안전 재시작으로 줄여 발현 전에 끊는다.
# 1200 셀 / 50 = 24 회 × 18초 = 432초 (7분) 추가 비용.
RESTART_EVERY = 50
CARLA_BOOT_WAIT_SEC = 18

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


def restart_carla(container: str) -> None:
    """sb-pilot 컨테이너 안 CarlaUE4를 안전 재시작. SafeBench upstream의 셀 사이
    메모리 누수 현상에 대응(라운드 15 진단). 죽이고 18초 부팅 대기.
    """
    print(f">>> [carla-restart] killing CarlaUE4 in {container}", flush=True)
    subprocess.run(
        ["docker", "exec", container, "bash", "-c",
         "pkill -9 -f CarlaUE4 2>/dev/null; sleep 2; pkill -9 -f Carla 2>/dev/null; sleep 1"],
        check=False, timeout=30,
    )
    subprocess.run(
        ["docker", "exec", "-d", container, "bash", "-c",
         "cd /home/safebench/carla && "
         "./CarlaUE4.sh -RenderOffScreen -nosound -carla-rpc-port=2000 "
         "> /tmp/carla.log 2>&1"],
        check=False, timeout=10,
    )
    print(f">>> [carla-restart] booting (sleep {CARLA_BOOT_WAIT_SEC}s)", flush=True)
    time.sleep(CARLA_BOOT_WAIT_SEC)


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
        # 라운드 15: 매 RESTART_EVERY 셀마다 CARLA 안전 재시작. 1셀은 깨끗한 상태이니 건너뜀.
        if not args.dry_run and i > 1 and (i - 1) % RESTART_EVERY == 0:
            restart_carla(args.container)
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
