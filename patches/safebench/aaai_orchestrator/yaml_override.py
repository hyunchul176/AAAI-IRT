# -*- coding: utf-8 -*-
"""셀별 scenario yaml 동적 생성.

SafeBench의 `scenario/tools/scenario_utils.py`는 scenario_type json을 yaml의
`scenario_id`·`route_id` 두 필드로만 filter한다. 한 셀을 한 SafeBench eval에
1대1 매핑하려면 셀별로 (scenario_id, route_id)를 강제한 yaml이 필요하다.

scripts/run.py가 `osp.join(ROOT_DIR, 'safebench/scenario/config', scenario_cfg)`로
경로를 빌드하므로 tmp yaml은 그 디렉토리 안에 셀명으로 만든다. cleanup은
호출자 책임(run_one_cell.py가 atexit으로 처리).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml


SAFEBENCH_SCENARIO_CFG_DIR = "safebench/scenario/config"


def make_cell_scenario_yaml(
    *,
    safebench_root: str,
    base_scenario_cfg: str,
    cell_tag: str,
    scenario_id: Optional[int],
    route_id: Optional[int],
    model_id: Optional[int] = None,
) -> str:
    """base yaml을 읽어 (scenario_id, route_id, model_id)를 셀에 맞게 덮어쓴 새
    yaml을 safebench/scenario/config/aaai_cell_<tag>.yaml로 저장하고 그 파일명을
    돌려준다. scripts/run.py에 --scenario_cfg로 넘기는 값(파일명만)이 그대로
    돼야 하므로 SafeBench config 디렉토리 안에 두는 것이 가장 깔끔하다.

    Args:
      safebench_root: SafeBench 저장소 루트(예: /home/safebench/SafeBench).
      base_scenario_cfg: 원본 scenario yaml 파일명(예: "LC.yaml").
      cell_tag: 셀 식별자(파일명 충돌 방지용).
      scenario_id: 강제할 scenario_id(None이면 base 값 유지).
      route_id: 강제할 route_id.
      model_id: REINFORCE(LC·NF) 정책의 model_id를 셀별로 바꾸고 싶으면 지정.

    Returns:
      tmp yaml의 파일명(scenario_cfg 인자로 그대로 넘길 값).
    """
    base_path = Path(safebench_root) / SAFEBENCH_SCENARIO_CFG_DIR / base_scenario_cfg
    if not base_path.exists():
        raise FileNotFoundError(f"base scenario cfg not found: {base_path}")
    with open(base_path, "r") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)

    if scenario_id is not None:
        cfg["scenario_id"] = scenario_id
    if route_id is not None:
        cfg["route_id"] = route_id
    if model_id is not None and "model_id" in cfg:
        cfg["model_id"] = model_id

    tmp_name = f"aaai_cell_{cell_tag}.yaml"
    tmp_path = Path(safebench_root) / SAFEBENCH_SCENARIO_CFG_DIR / tmp_name
    with open(tmp_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return tmp_name


def remove_cell_scenario_yaml(safebench_root: str, tmp_name: str) -> None:
    """cleanup. atexit 또는 finally에서 호출한다."""
    tmp_path = Path(safebench_root) / SAFEBENCH_SCENARIO_CFG_DIR / tmp_name
    if tmp_path.exists():
        os.remove(tmp_path)


def make_cell_agent_yaml(
    *,
    safebench_root: str,
    base_agent_cfg: str,
    cell_tag: str,
    overrides: Optional[dict[str, Any]] = None,
) -> str:
    """agent yaml override(현 시점에는 사용 없음, 인터페이스만 갖춰 둠).

    AV planner cfg는 셀별로 바뀌지 않으므로 기본은 no-op. 향후 reward 변종이나
    학습 시드 변화를 셀별로 강제할 필요가 생기면 이 함수에서 처리한다.
    """
    base_path = Path(safebench_root) / "safebench/agent/config" / base_agent_cfg
    if not base_path.exists():
        raise FileNotFoundError(f"base agent cfg not found: {base_path}")
    if not overrides:
        return base_agent_cfg
    with open(base_path, "r") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    cfg.update(overrides)
    tmp_name = f"aaai_cell_{cell_tag}_agent.yaml"
    tmp_path = Path(safebench_root) / "safebench/agent/config" / tmp_name
    with open(tmp_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return tmp_name


def remove_cell_agent_yaml(safebench_root: str, tmp_name: str) -> None:
    tmp_path = Path(safebench_root) / "safebench/agent/config" / tmp_name
    if tmp_path.exists():
        os.remove(tmp_path)
