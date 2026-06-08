# -*- coding: utf-8 -*-
"""단조성 pilot 2차: LC·NF 자기 단위 다이얼 (학습 후).

라운드 9 정정에 따라 fppo_adv를 빼고 SafeBench의 두 적대 생성기(LC·NF)를
대상으로 단조성 pilot을 다시 돌린다. AdvSim·AdvTraj는 HardCodePolicy
(type='unlearnable')라 사용 불가(decisions.html #d07).

설계: 2 ego(SAC·behavior) × 2 G(LC·NF) × c 5수준 × K=10 = 200 cells.
- ego: SAC(동봉된 학습 ckpt) + behavior(CARLA BehaviorAgent, 규칙 기반).
  expert·expert_disturb는 라운드 9·10에서 격자 응시자 제외.
- G: LC(REINFORCE init-state, sigma_scale 다이얼) + NF(NormalizingFlow,
  flow_sigma=latent z 분산 다이얼).
- severity_injectors의 SEVERITY_MAP[lc/nf] 1차 후보를 monkey-patch로 적용.

LC·NF가 모두 학습 완료된 시점에 호출한다(`train_safebench_serial.sh`가
LC→NF 직렬 학습 자동 진행). 학습이 끝나기 전에 실행하면 fallback ckpt로
의미 없는 결과가 나온다.

usage:
    python3 analysis/b4-pipeline/pilot_monotonic_v2.py --container sb-pilot --dry-run
    python3 analysis/b4-pipeline/pilot_monotonic_v2.py --container sb-pilot
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


EGOS = ["sac", "behavior"]
GENERATORS = ["lc", "idm_attack"]
C_LEVELS = [0.0, 1.0, 2.0, 3.0, 4.0]
K_REPS = 10

# 라운드 12 정정 후 G 후보: LC + idm_attack(+ ordinary, baseline). NF는 yaml
# 누락 10개 필드로 학습 흐름 자체가 SafeBench upstream에서 한 번도 통과된 적
# 없어 라운드 12에서 포기. G별 시나리오 카탈로그는 sb-pilot 안 jsonl과 정합한
# 형태로 분리한다(host의 SafeBench와 docker 이미지의 SafeBench가 다른 commit
# 기반에서 빌드된 사실, IDM smoke test에서 확인).
G_SCENARIO_CFG = {
    "lc":         dict(yaml="LC.yaml",         sid=2, route_first_data=[(0, 40), (1, 50), (2, 60), (3, 70)]),
    "idm_attack": dict(yaml="idm_attack.yaml", sid=8, route_first_data=[(0, 280), (1, 290), (2, 300), (3, 310)]),
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
            f"v2_{self.ego}_{self.g_id}_c{self.c_value:.1f}_k{self.trial_k:02d}"
            f"_r{self.rid}d{self.data_id}"
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
    scenario_cfg = G_SCENARIO_CFG[cell.g_id]["yaml"]
    agent_cfg = f"{cell.ego}.yaml"
    cmd_inside = (
        "export SDL_VIDEODRIVER=dummy && "
        "cd /home/safebench/SafeBench && "
        "python aaai_orchestrator/run_one_cell.py "
        "--safebench-root /home/safebench/SafeBench --tree safebench "
        f"--agent-cfg {agent_cfg} --scenario-cfg {scenario_cfg} --policy-type {cell.g_id} "
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


def extract_collision_and_cleanup(container: str, cell: PilotCell, out_dir: Path) -> float | None:
    """SafeBench results.pkl에서 collision_rate를 읽고 host로 cp, 컨테이너 안
    원본 삭제(누적 평균 오염 회피)."""
    # SafeBench results.pkl 경로: log/<exp_name>/<exp_name>_<ego>_<g>_seed_0/eval_results/results.pkl
    remote = (
        f"/home/safebench/SafeBench/log/{cell.exp_name}/"
        f"{cell.exp_name}_{cell.ego}_{cell.g_id}_seed_0/eval_results"
    )
    p = subprocess.run(
        ["docker", "exec", container, "bash", "-lc",
         "PYTHONPATH=/home/safebench/carla/PythonAPI/carla/dist/"
         "carla-0.9.13-py3.8-linux-x86_64.egg "
         f"python -c \"import pickle; "
         f"d=pickle.load(open('{remote}/results.pkl','rb')); "
         f"print(d.get('collision_rate'))\""],
        capture_output=True, text=True, timeout=10,
    )
    out = p.stdout.strip()
    cell_dir = out_dir / cell.exp_name
    cell_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("results.pkl", "records.pkl"):
        subprocess.run(
            ["docker", "cp",
             f"{container}:{remote}/{fname}",
             str(cell_dir / fname)],
            capture_output=True,
        )
    subprocess.run(
        ["docker", "exec", container, "bash", "-lc",
         f"rm -rf /home/safebench/SafeBench/log/{cell.exp_name}"],
        capture_output=True,
    )
    try:
        return float(out)
    except ValueError:
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-pilot")
    p.add_argument("--log-dir", default="analysis/b4-pipeline/pilot_mono_v2_logs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_pilot_cells())
    print(f">>> {len(cells)} pilot v2 cells "
          f"(ego={len(EGOS)} × G={len(GENERATORS)} × c={len(C_LEVELS)} × K={K_REPS})")

    results = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        r = run_cell(cell, args.container, args.dry_run, log_dir)
        if not args.dry_run and r.get("rc") == 0:
            r["collision_rate"] = extract_collision_and_cleanup(args.container, cell, log_dir)
        results.append(r)

    summary_path = log_dir / "pilot_mono_v2_summary.json"
    summary_path.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    print(f">>> wall-clock {time.time() - t0:.0f}s, summary -> {summary_path}")


if __name__ == "__main__":
    main()
