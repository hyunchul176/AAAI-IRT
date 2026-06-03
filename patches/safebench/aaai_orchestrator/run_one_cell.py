# -*- coding: utf-8 -*-
"""한 셀당 한 SafeBench eval entrypoint (SafeBench 컨테이너 안에서 실행).

호출 예 (orchestrator → docker exec):
    python aaai_orchestrator/run_one_cell.py \
        --agent-cfg sac.yaml --scenario-cfg LC.yaml \
        --sid 2 --rid 0 --data-id 5 --model-id 1 \
        --c-value 2.0 --policy-type lc \
        --seed 12345 --exp-name g3_sac_lc_c2.0_k0 \
        --port 2000 --tm-port 8000

이 entrypoint는:
1. base scenario yaml을 읽어 (sid, rid, model_id)를 강제한 tmp yaml을 만들고
2. severity_injectors.apply_severity로 c → policy hyperparameter 매핑을 SafeBench
   import 직전에 monkey-patch한 뒤
3. SafeBench scripts/run.py의 main 흐름(import + CarlaRunner)을 직접 호출한다.

scripts/run.py를 별도 프로세스로 띄우면 monkey-patch가 적용되지 않으므로 동일
프로세스에서 SafeBench 모듈을 직접 import해 실행한다.
"""
from __future__ import annotations

import argparse
import atexit
import os
import sys
import traceback
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--safebench-root", default="/home/safebench/SafeBench",
                   help="SafeBench 저장소 루트")
    p.add_argument("--agent-cfg", required=True, help="agent yaml 파일명 (예: sac.yaml)")
    p.add_argument("--scenario-cfg", required=True, help="원본 scenario yaml 파일명 (예: LC.yaml)")
    p.add_argument("--policy-type", required=True,
                   choices=["lc", "nf", "advsim", "advtraj", "ordinary", "fppo_adv"],
                   help="severity injector를 고르는 정책 타입")
    p.add_argument("--sid", type=int, required=True, help="scenario_id 강제값")
    p.add_argument("--rid", type=int, required=True, help="route_id 강제값")
    p.add_argument("--data-id", type=int, default=None,
                   help="HardCode 계열(AdvSim/AdvTraj) parameters 인덱스 강제값")
    p.add_argument("--model-id", type=int, default=None,
                   help="REINFORCE 계열(LC) model_id 강제값")
    p.add_argument("--c-value", type=float, required=True, help="severity 수준")
    p.add_argument("--seed", type=int, required=True, help="셀 시드")
    p.add_argument("--exp-name", required=True, help="SafeBench --exp_name")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--tm-port", type=int, default=8000)
    p.add_argument("--num-scenario", type=int, default=1,
                   help="셀당 한 rollout만 실행하도록 1로 강제")
    p.add_argument("--max-episode-step", type=int, default=300)
    p.add_argument("--fixed-delta-seconds", type=float, default=0.1)
    p.add_argument("--dry-run", action="store_true",
                   help="tmp yaml만 만들고 SafeBench 호출은 생략")
    return p


def main() -> int:
    args = _build_parser().parse_args()

    # SafeBench가 import할 수 있도록 PYTHONPATH/cwd 설정
    safebench_root = Path(args.safebench_root)
    if not safebench_root.exists():
        print(f"!! safebench root not found: {safebench_root}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(safebench_root))

    # 우리 패키지(__init__.py 가 한 단계 위) 가져오기
    pkg_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(pkg_root))
    from aaai_orchestrator.yaml_override import (
        make_cell_scenario_yaml, remove_cell_scenario_yaml,
    )

    # tmp scenario yaml 만들기
    tmp_scenario_yaml = make_cell_scenario_yaml(
        safebench_root=str(safebench_root),
        base_scenario_cfg=args.scenario_cfg,
        cell_tag=args.exp_name,
        scenario_id=args.sid,
        route_id=args.rid,
        model_id=args.model_id,
    )
    atexit.register(remove_cell_scenario_yaml, str(safebench_root), tmp_scenario_yaml)

    if args.dry_run:
        tmp_path = safebench_root / "safebench/scenario/config" / tmp_scenario_yaml
        print(f">> dry-run: wrote {tmp_path}")
        with open(tmp_path) as f:
            sys.stdout.write(f.read())
        return 0

    # severity 매핑은 단조성 pilot 후 SEVERITY_MAP을 채워야 실제 monkey-patch가
    # 작동한다. 비어 있으면 NotImplementedError가 즉시 던져진다(silent skip 금지).
    from aaai_orchestrator.severity_injectors import apply_severity
    apply_severity(args.policy_type, args.c_value)

    # 이제 SafeBench를 import해 한 셀 eval을 직접 띄운다(monkey-patch가
    # import 후에도 작동하도록 정책 클래스의 메서드를 갈아끼우는 방식이라
    # apply_severity는 import 전·후 어느 자리에서도 OK).
    os.chdir(str(safebench_root))
    sys.argv = [
        "scripts/run.py",
        "--agent_cfg", args.agent_cfg,
        "--scenario_cfg", tmp_scenario_yaml,
        "--mode", "eval",
        "--num_scenario", str(args.num_scenario),
        "--seed", str(args.seed),
        "--port", str(args.port),
        "--tm_port", str(args.tm_port),
        "--exp_name", args.exp_name,
        "--max_episode_step", str(args.max_episode_step),
        "--fixed_delta_seconds", str(args.fixed_delta_seconds),
        "--ROOT_DIR", str(safebench_root),
    ]
    try:
        import runpy
        runpy.run_path(str(safebench_root / "scripts/run.py"), run_name="__main__")
    except SystemExit as e:
        return int(e.code or 0)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
