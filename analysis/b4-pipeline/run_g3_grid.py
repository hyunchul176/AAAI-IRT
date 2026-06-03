# -*- coding: utf-8 -*-
"""
즉시 B 단계 G=3 격자 실행 orchestrator (decisions.html 격자 후보 결정에 따른 두 단계 진입).

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
        5수준으로 매핑한다 (생성기·severity 결정).
    K=20: 한 (AV, G, c) 셀을 시드를 달리해 20회 반복.

셀 → SafeBench eval 매핑:
    한 셀은 한 (scenario_id, route_id, data_id) 인스턴스에 대응한다.
    SafeBench scripts/run.py는 yaml의 scenario_id·route_id 두 필드로만
    scenario_type json을 filter하므로, 셀별로 yaml override가 필요하다
    (patches/safebench/aaai_orchestrator/yaml_override.py가 처리).
    K=20 trial은 G별 (sid, rid, data_id) 카탈로그를 반복 인덱스로 가리킨다.
    severity는 patches/safebench/aaai_orchestrator/severity_injectors.py가
    정책별로 monkey-patch한다(단조성 pilot 후 매핑 표가 채워진다).

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


# ===== AV·G cfg 트리·yaml 매핑 =====
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
# 정책 타입(policy_type)은 severity_injectors가 정책별 monkey-patch 분기에 쓴다.
# (yaml의 policy_type 필드 값과 일치하도록 한다.)
SCENARIO_CFG = {
    "lc":       ("safebench", "LC.yaml",            "lc"),
    "fppo_adv": ("frea",      "fppo_adv_eval.yaml", "fppo_adv"),
    "ordinary": ("safebench", "ordinary.yaml",      "ordinary"),
}


# ===== G별 (sid, rid, data_id) 카탈로그 =====
# SafeBench scenario_type json을 읽어 G의 기본 scenario_id filter(yaml의 값)에
# 해당하는 (sid, rid, data_id) 목록을 펼친다. trial_k는 이 목록의 인덱스로
# 사용한다.
def _scenario_type_json_path(g_id: str, safebench_root: Path, frea_root: Path) -> Path:
    """G의 base yaml에서 scenario_type 파일명을 읽어 절대 경로를 만든다."""
    import yaml as _yaml
    tree, base_yaml, _policy = SCENARIO_CFG[g_id]
    if tree == "safebench":
        root, sub = safebench_root, "safebench/scenario/config"
    else:
        root, sub = frea_root, "frea/scenario/config"
    yaml_path = root / sub / base_yaml
    if not yaml_path.exists():
        raise FileNotFoundError(f"base scenario yaml missing: {yaml_path}")
    with open(yaml_path) as f:
        cfg = _yaml.safe_load(f)
    scenario_type_dir = cfg.get("scenario_type_dir", "")
    scenario_type_file = cfg.get("scenario_type", "")
    return root / scenario_type_dir / scenario_type_file


def build_g_catalog(g_id: str, safebench_root: Path, frea_root: Path) -> list[tuple[int, int, int]]:
    """한 G에 대해 base yaml의 scenario_id·route_id filter를 적용한 뒤 남는
    (sid, rid, data_id) 리스트를 돌려준다. trial_k는 이 리스트 인덱스로
    K_REPS 만큼 순환한다.

    fppo_adv는 FREA 트리에 별도 scenario_type 구조가 있을 가능성이 있어
    safebench_root와 frea_root를 둘 다 받아 둔다(현재는 SafeBench 동일 구조
    가정, FREA 점검 후 분기 추가).
    """
    import yaml as _yaml
    tree, base_yaml, _policy = SCENARIO_CFG[g_id]
    root = safebench_root if tree == "safebench" else frea_root
    sub = "safebench/scenario/config" if tree == "safebench" else "frea/scenario/config"
    with open(root / sub / base_yaml) as f:
        cfg = _yaml.safe_load(f)
    base_sid = cfg.get("scenario_id")
    base_rid = cfg.get("route_id")
    st_path = _scenario_type_json_path(g_id, safebench_root, frea_root)
    with open(st_path) as f:
        data_full = json.load(f)
    cat: list[tuple[int, int, int]] = []
    for item in data_full:
        if base_sid is not None and item["scenario_id"] != base_sid:
            continue
        if base_rid is not None and item["route_id"] != base_rid:
            continue
        cat.append((item["scenario_id"], item["route_id"], item["data_id"]))
    if not cat:
        raise RuntimeError(f"empty catalog for {g_id} (yaml={base_yaml})")
    return cat


@dataclass(frozen=True)
class Cell:
    av_id: str
    g_id: str
    c_idx: int
    c_value: float
    trial_k: int
    sid: int
    rid: int
    data_id: int

    @property
    def seed(self) -> int:
        # decisions.html 시드·시간·환경 결정: deterministic seed across processes.
        # Python's built-in hash() is salted per process (PEP 456), so we use a
        # stable hashlib digest of a canonical string and take the low 31 bits.
        key = (
            f"{self.av_id}|{self.g_id}|{self.c_value:.6f}|{self.trial_k}|"
            f"{self.sid}|{self.rid}|{self.data_id}"
        ).encode("utf-8")
        digest = hashlib.blake2b(key, digest_size=8).digest()
        return int.from_bytes(digest, "little") % (2 ** 31)

    @property
    def exp_name(self) -> str:
        return (
            f"g3_{self.av_id}_{self.g_id}_c{self.c_value:.1f}_k{self.trial_k:02d}"
            f"_s{self.sid}r{self.rid}d{self.data_id}"
        )


def iter_cells(safebench_root: Path, frea_root: Path) -> Iterable[Cell]:
    catalogs = {g: build_g_catalog(g, safebench_root, frea_root) for g in G_LIST}
    for av in AV_LIST:
        for g in G_LIST:
            cat = catalogs[g]
            for c_idx, c_value in enumerate(C_LEVELS):
                for k in range(K_REPS):
                    sid, rid, data_id = cat[k % len(cat)]
                    yield Cell(
                        av_id=av, g_id=g,
                        c_idx=c_idx, c_value=c_value, trial_k=k,
                        sid=sid, rid=rid, data_id=data_id,
                    )


# ===== SafeBench/FREA 실행 명령 =====
def safebench_cmd(cell: Cell, port: int = 2000, tm_port: int = 8000) -> str:
    """한 셀을 컨테이너 내부에서 평가하는 명령.

    AV·G가 같은 트리(safebench 또는 frea)에 있을 때 그 트리의 entrypoint로
    실행한다. 두 트리가 섞이면 별도 stage가 필요하므로 ValueError로 알려 본
    격자 실행 전에 처리한다. entrypoint는 SafeBench의 scripts/run.py가 아니라
    셀별 yaml override + severity injection을 처리하는
    patches/safebench/aaai_orchestrator/run_one_cell.py로 보낸다(컨테이너 안에
    /home/safebench/SafeBench/aaai_orchestrator/로 docker cp 되어 있다고 가정).
    """
    av_tree, av_cfg = AGENT_CFG[cell.av_id]
    g_tree, g_cfg, policy_type = SCENARIO_CFG[cell.g_id]
    if av_tree != g_tree:
        raise ValueError(
            f"AV({cell.av_id}@{av_tree}) and G({cell.g_id}@{g_tree}) live in "
            f"different repos; orchestrate after staging or run via FREA tree"
        )
    if av_tree == "safebench":
        sb_root = "/home/safebench/SafeBench"
    else:
        sb_root = "/home/safebench/FREA"

    parts = [
        "SDL_VIDEODRIVER=dummy",
        f"cd {sb_root} &&",
        "python aaai_orchestrator/run_one_cell.py",
        f"--safebench-root {sb_root}",
        f"--agent-cfg {av_cfg}",
        f"--scenario-cfg {g_cfg}",
        f"--policy-type {policy_type}",
        f"--sid {cell.sid}",
        f"--rid {cell.rid}",
        f"--data-id {cell.data_id}",
        f"--c-value {cell.c_value}",
        f"--seed {cell.seed}",
        f"--exp-name {cell.exp_name}",
        f"--port {port}",
        f"--tm-port {tm_port}",
        "--num-scenario 1",
    ]
    return " ".join(parts)


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
    p.add_argument("--safebench-root", default="external/SafeBench",
                   help="local path to SafeBench checkout (for reading scenario_type json)")
    p.add_argument("--frea-root", default="external/FREA",
                   help="local path to FREA checkout (for reading FREA scenario_type)")
    args = p.parse_args()

    safebench_root = Path(args.safebench_root).resolve()
    frea_root = Path(args.frea_root).resolve()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    # 직전 실행이 SIGKILL이나 docker 중단으로 끝났다면 atexit cleanup이
    # 호스트 yaml에는 영향을 주지 않지만 컨테이너 안 SafeBench config 디렉토리
    # 정리를 docker exec로 한 번 호출해 디렉토리 오염을 막는다. dry-run에서는
    # 컨테이너 호출이 없으므로 건너뛴다.
    if not args.dry_run:
        subprocess.run([
            "docker", "exec", args.container, "bash", "-lc",
            "rm -f /home/safebench/SafeBench/safebench/scenario/config/aaai_cell_*.yaml "
            "/home/safebench/FREA/frea/scenario/config/aaai_cell_*.yaml 2>/dev/null || true",
        ], check=False)
    cells = list(iter_cells(safebench_root, frea_root))
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
