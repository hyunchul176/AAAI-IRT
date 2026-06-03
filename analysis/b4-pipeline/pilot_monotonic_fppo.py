# -*- coding: utf-8 -*-
"""단조성 pilot: fppo_adv의 c → episode 매핑이 충돌률 단조 증가를 만드는지 점검.

작은 격자: 1 AV(expert) × G(fppo_adv) × c 5수준 × K=5 = 25 cells.
SEVERITY_MAP['fppo_adv']의 c→episode (50·200·500·900·1250)이 충돌률 vs c의
Spearman ρ ≥ 0.7을 만족하면 합격(생성기·severity 결정 본문).

Town02 한정 catalog (fppo_adv ckpt가 expert_rule-based_seed0/Scenario9_Town02/
한 자리만 있어 다른 Town은 fallback). route_id ∈ {12,13,14,15,16,20,21} 일곱
종, 각 route에 data_id 10개. K=5 trial은 일곱 route 안에서 분산.

usage:
    python3 analysis/b4-pipeline/pilot_monotonic_fppo.py --container sb-pilot --dry-run
    python3 analysis/b4-pipeline/pilot_monotonic_fppo.py --container sb-pilot
"""
from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


# Town02 한정 (route_id, first_data_id). FREA Scenario9_Town05_Town02_10x.json
# 안에서 route_id가 Town02에 매핑되는 일곱 자리. data_id는 각 route 안 0번째.
TOWN02_ROUTES: list[tuple[int, int]] = [
    (12,  80), (13,  90), (14, 100), (15, 110), (16, 120),
    (20, 130), (21, 140),
]
EGOS = ["expert", "expert_disturb"]
C_LEVELS = [0.0, 1.0, 2.0, 3.0, 4.0]
K_REPS = 10


@dataclass(frozen=True)
class PilotCell:
    ego: str
    c_value: float
    trial_k: int
    sid: int
    rid: int
    data_id: int

    @property
    def exp_name(self) -> str:
        return f"pilotmono_{self.ego}_c{self.c_value:.1f}_k{self.trial_k:02d}_r{self.rid}d{self.data_id}"


def iter_pilot_cells() -> Iterable[PilotCell]:
    for ego in EGOS:
        for c in C_LEVELS:
            for k in range(K_REPS):
                rid, base_did = TOWN02_ROUTES[k % len(TOWN02_ROUTES)]
                # 같은 route 안에서 k에 따라 data_id를 약간 이동
                data_id = base_did + (k // len(TOWN02_ROUTES))
                yield PilotCell(
                    ego=ego, c_value=c, trial_k=k,
                    sid=9, rid=rid, data_id=data_id,
                )


def run_cell(cell: PilotCell, container: str, dry_run: bool, log_dir: Path) -> dict:
    agent_cfg = f"{cell.ego}.yaml"
    # `--frea-pretrain-ego`는 FREA의 ckpt 폴더 경로(expert_rule-based_seed0/...)를
    # 결정한다. 우리는 expert pretrain 환경에서 학습된 fppo_adv ckpt만 갖고
    # 있어 expert로 고정하고, ego 자체는 agent_cfg 파일로 분기한다
    # (expert / expert_disturb).
    cmd_inside = (
        "SDL_VIDEODRIVER=dummy "
        "cd /home/safebench/FREA && "
        "python aaai_orchestrator/run_one_cell.py "
        "--safebench-root /home/safebench/FREA --tree frea "
        f"--agent-cfg {agent_cfg} --scenario-cfg fppo_adv_eval.yaml --policy-type fppo_adv "
        "--frea-pretrain-ego expert "
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
    """FREA의 results.pkl에서 collision_rate를 읽고 host로 복사한 뒤 컨테이너 안
    원본을 제거한다(다음 셀의 누적 평가에 영향을 주지 않도록).

    FREA는 `log/eval/eval_cbv_pretrained_with_expert/expert_fppo_adv_rule-based_seed0/
    Scenario9_Town02/results.pkl`에 한 자리만 둔다(num_scenario=1이라 한 셀 한 행).
    한 셀 끝나면 results.pkl·records.pkl을 셀명으로 host에 보관한 뒤 컨테이너 안
    원본을 지운다.
    """
    # results.pkl 경로: FREA가 `eval_cbv_pretrained_with_<pretrain_ego>` 디렉토리
    # 아래에 `<agent_policy_name>_<scenario_policy_name>_<CBV_selection>_seed<seed>/
    # Scenario<sid>_<Town>/`로 둔다. pretrain_ego는 우리가 expert로 고정했으니
    # 부모는 항상 expert. agent_policy_name은 cell.ego(expert 또는 expert_disturb).
    remote_dir = (
        f"/home/safebench/FREA/log/eval/eval_cbv_pretrained_with_expert/"
        f"{cell.ego}_fppo_adv_rule-based_seed0/Scenario9_Town02"
    )
    p = subprocess.run(
        ["docker", "exec", container, "bash", "-lc",
         "PYTHONPATH=/home/safebench/carla/PythonAPI/carla/dist/"
         "carla-0.9.13-py3.8-linux-x86_64.egg "
         f"python -c \"import pickle; "
         f"d=pickle.load(open('{remote_dir}/results.pkl','rb')); "
         f"print(d.get('collision_rate'))\""],
        capture_output=True, text=True, timeout=10,
    )
    out = p.stdout.strip()
    cell_dir = out_dir / cell.exp_name
    cell_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("results.pkl", "records.pkl"):
        subprocess.run(
            ["docker", "cp",
             f"{container}:{remote_dir}/{fname}",
             str(cell_dir / fname)],
            capture_output=True,
        )
    subprocess.run(
        ["docker", "exec", container, "bash", "-lc",
         f"rm -rf {remote_dir}"],
        capture_output=True,
    )
    try:
        return float(out)
    except ValueError:
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--container", default="sb-pilot")
    p.add_argument("--log-dir", default="analysis/b4-pipeline/pilot_mono_logs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cells = list(iter_pilot_cells())
    print(f">>> {len(cells)} pilot cells (c={len(C_LEVELS)} × K={K_REPS})")

    results = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        print(f"  [{i}/{len(cells)}] {cell.exp_name}", flush=True)
        r = run_cell(cell, args.container, args.dry_run, log_dir)
        if not args.dry_run and r.get("rc") == 0:
            r["collision_rate"] = extract_collision_and_cleanup(args.container, cell, log_dir)
        results.append(r)

    summary_path = log_dir / "pilot_mono_summary.json"
    summary_path.write_text(json.dumps(dict(
        n_cells=len(cells), wall_sec=time.time() - t0, results=results,
    ), default=str, indent=2))
    print(f">>> wall-clock {time.time() - t0:.0f}s, summary -> {summary_path}")


if __name__ == "__main__":
    main()
