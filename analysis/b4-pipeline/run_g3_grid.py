# -*- coding: utf-8 -*-
"""
즉시 B 단계 G=3 격자 실행 orchestrator (decisions.html 격자 후보 결정의 두 단계 진입).

격자: AV 6명 × G 3종 × severity 5수준 × 셀당 반복 K=20 = 1,800 cells
    AV (즉시 사용 가능, 학습 없이):
        - SafeBench SAC   (도커 동봉)
        - SafeBench basic (규칙 기반)
        - SafeBench behavior (규칙 기반)
        - FREA PlanT      (Drive에서 다운로드)
        - FREA expert     (PlanT 데이터 수집용 AutoPilot teacher)
        - FREA expert_disturb (AutoPilot에 throttle/steer/brake 노이즈)
    G (즉시 사용 가능):
        - LC       (SafeBench 적대 생성기, model_id 1 fallback)
        - fppo_adv (FREA 적대 생성기, Drive CBV ckpt)
        - ordinary (SafeBench 비적대 baseline)
    severity: SafeBench scenario는 severity 변수를 노출하지 않으므로
        해당 정책의 hyperparameter(attack budget, perturbation magnitude 등)
        5수준으로 매핑한다 (생성기·severity 결정). 우선 c 값을 SafeBench yaml override로 주입.
    K=20: 한 (AV, G, c) 셀을 시드를 달리해 20회 반복.

이 orchestrator는 위 1,800 cells을 SafeBench eval mode로 자동 순환 실행한다.
한 라운드 = 한 (AV, G, c) 조합 × 20 trials. SafeBench의 --num_scenario 1과
다양한 --seed로 K=20을 보장한다. 결과 records.pkl을 host로 docker cp 후
analysis/b4-pipeline/sb_to_response.py의 collect_grid_responses로 JSONL.

본 격자(G=4) 확장은 PPO·DDPG·TD3·AdvSim·AdvTraj·NF 자체 학습이 완료된
뒤 별도 orchestrator로(학습 진행 상태는 별도 추적).

사용:
    python3 analysis/b4-pipeline/run_g3_grid.py --container sb-grid --dry-run
    python3 analysis/b4-pipeline/run_g3_grid.py --container sb-grid --commit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


# ===== 격자 정의 (격자 후보 결정의 즉시 격자) =====
AV_LIST = ["sac", "basic", "behavior", "plant", "expert", "expert_disturb"]
G_LIST  = ["lc", "fppo_adv", "ordinary"]
C_LEVELS = [0.0, 1.0, 2.0, 3.0, 4.0]
K_REPS = 20


@dataclass(frozen=True)
class Cell:
    av_id: str
    g_id: str
    c: float
    trial_k: int

    @property
    def seed(self) -> int:
        # decisions.html 시드·시간·환경 결정: deterministic seed across processes.
        # Python's built-in hash() is salted per process (PEP 456), so we use a
        # stable hashlib digest of a canonical string and take the low 31 bits.
        key = f"{self.av_id}|{self.g_id}|{self.c:.6f}|{self.trial_k}".encode("utf-8")
        digest = hashlib.blake2b(key, digest_size=8).digest()
        return int.from_bytes(digest, "little") % (2 ** 31)

    @property
    def exp_name(self) -> str:
        return f"g3_{self.av_id}_{self.g_id}_c{self.c:.1f}_k{self.trial_k:02d}"


def iter_cells() -> Iterable[Cell]:
    for av in AV_LIST:
        for g in G_LIST:
            for c in C_LEVELS:
                for k in range(K_REPS):
                    yield Cell(av_id=av, g_id=g, c=c, trial_k=k)


# ===== SafeBench/FREA 실행 명령 =====
# AV·G cfg는 두 트리에 나뉘어 있다:
#   SafeBench tree: external/SafeBench/safebench/{agent,scenario}/config/
#   FREA tree    : external/FREA/frea/{agent,scenario}/config/
# B 단계 첫 작업 검토 결과(2026-06-03) FREA 측 cfg(plant/expert/expert_disturb/
# fppo_adv)는 SafeBench scripts/run.py가 곧장 못 읽으므로 FREA 컨테이너 또는
# FREA cfg가 stage된 SafeBench 컨테이너에서 별도 실행해야 한다. 격자 진입 시
# 두 그룹으로 나눠 각각의 cwd·entrypoint로 보낸다.
AGENT_CFG = {
    "sac":            ("safebench", "sac.yaml"),
    "basic":          ("safebench", "basic.yaml"),
    "behavior":       ("safebench", "behavior.yaml"),
    "plant":          ("frea",      "plant.yaml"),
    "expert":         ("frea",      "expert.yaml"),
    "expert_disturb": ("frea",      "expert_disturb.yaml"),
}
SCENARIO_CFG = {
    "lc":       ("safebench", "LC.yaml"),
    "fppo_adv": ("frea",      "fppo_adv_eval.yaml"),
    "ordinary": ("safebench", "ordinary.yaml"),
}


def safebench_cmd(cell: Cell, port: int = 2000, tm_port: int = 8000) -> str:
    """한 셀을 컨테이너 내부에서 평가하는 명령. AV·G가 같은 트리(safebench
    또는 frea)에 있을 때 그 트리의 entrypoint로 실행한다. 두 트리가 섞이면
    별도 stage가 필요하므로 ValueError로 알려 본 격자 실행 전에 처리한다.
    """
    av_tree, av_cfg = AGENT_CFG[cell.av_id]
    g_tree, g_cfg   = SCENARIO_CFG[cell.g_id]
    if av_tree != g_tree:
        raise ValueError(
            f"AV({cell.av_id}@{av_tree}) and G({cell.g_id}@{g_tree}) live in "
            f"different repos; orchestrate after staging or run via FREA tree"
        )
    if av_tree == "safebench":
        cwd, entry = "/home/safebench/SafeBench", "scripts/run.py"
    else:
        cwd, entry = "/home/safebench/FREA", "scripts/run.py"
    return (
        "SDL_VIDEODRIVER=dummy "
        f"cd {cwd} && "
        f"python {entry} "
        f"--agent_cfg {av_cfg} --scenario_cfg {g_cfg} "
        "--mode eval --num_scenario 1 "
        f"--seed {cell.seed} "
        f"--port {port} --tm_port {tm_port} "
        f"--exp_name {cell.exp_name}"
    )


# ===== orchestrator =====
def run_one_cell(cell: Cell, container: str, port: int, tm_port: int,
                 dry_run: bool, log_dir: Path) -> dict:
    cmd_inside = safebench_cmd(cell, port=port, tm_port=tm_port)
    docker_cmd = ["docker", "exec", container, "bash", "-lc",
                  f"export PYTHONPATH=/home/safebench/carla/PythonAPI/carla/dist/"
                  f"carla-0.9.13-py3.8-linux-x86_64.egg:"
                  f"/home/safebench/carla/PythonAPI/carla/agents:"
                  f"/home/safebench/carla/PythonAPI/carla:"
                  f"/home/safebench/carla/PythonAPI && {cmd_inside}"]
    log_path = log_dir / f"{cell.exp_name}.log"
    if dry_run:
        return dict(cell=asdict(cell), cmd=docker_cmd, dry_run=True)
    t0 = time.time()
    with open(log_path, "w") as f:
        # 시드·시간·환경 결정의 셀당 timeout 권고 60초의 2배(120초)를 wall-clock 상한으로 둠
        # (rollout 자체는 60초로 종료되고, 추가 60초는 docker exec·env init).
        p = subprocess.run(docker_cmd, stdout=f, stderr=subprocess.STDOUT,
                           timeout=120)
    return dict(cell=asdict(cell), rc=p.returncode, wall_sec=time.time() - t0,
                log=str(log_path))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-grid",
                   help="SafeBench eval container name (must be running with port 2000)")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--tm_port", type=int, default=8000)
    p.add_argument("--log-dir", default="analysis/b4-pipeline/g3_logs")
    p.add_argument("--dry-run", action="store_true",
                   help="Print docker commands without running")
    p.add_argument("--limit", type=int, default=None,
                   help="Run only the first N cells (smoke test)")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_cells())
    if args.limit:
        cells = cells[:args.limit]
    print(f">>> {len(cells)} cells to run (AV={len(AV_LIST)} × G={len(G_LIST)} × "
          f"c={len(C_LEVELS)} × K={K_REPS})")
    t0 = time.time()
    results = []
    for i, cell in enumerate(cells, 1):
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        out = run_one_cell(cell, args.container, args.port, args.tm_port,
                           args.dry_run, log_dir)
        results.append(out)
    summary_path = log_dir / "run_summary.json"
    summary_path.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    print(f">>> wall-clock {time.time() - t0:.0f}s, summary -> {summary_path}")


if __name__ == "__main__":
    main()
