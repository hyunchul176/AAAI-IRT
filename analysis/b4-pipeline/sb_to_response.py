# -*- coding: utf-8 -*-
"""
B4 응답 기록 어댑터 (decisions.html D-08).

SafeBench `safebench/carla_runner.py`가 한 rollout을 끝내면 자체 logger
(`safebench/util/logger.py`의 `Logger`)에 출력을 쌓고, eval 모드에서는
`scenario_data_loader`가 만든 (route_id, scenario_id) 단위로 결과 dict를
남긴다. 이 어댑터는 그 출력에서 다음 다섯을 추출해 측정 모델 식 (6)의
응답 한 행으로 변환한다.

    (i)   y = 충돌 여부 0/1
    (ii)  t_collision = 충돌 시점 (없으면 None), 종류 (ego가 가해/피해)
    (iii) ego_traj, bg_traj = 시계열 위치·속도·heading
    (iv)  meta = 생성기 모수·route·날씨·step 수
    (v)   u_label = RSS 라벨러(rss_labeler.rss_label)로 부여한 회피불가 하한

응답 한 행은 dict 또는 dataclass로 누적되어 격자 응답표
(`analysis/d-study/response_table.{jsonl,parquet}` 또는 본 격자 대응 파일)
에 append된다. 이 응답표가 곧 측정 모델 MAP+Laplace 적합의 입력이다.

B 단계 첫 작업에서 확인할 것 (D-08 잔여 위험 노트):
- SafeBench 기본 logger가 ego 중심 지표(yaw, acceleration 등)는 저장하나
  background 차량 시계열 궤적의 자동 저장은 보장되지 않는다. 어댑터 첫
  점검으로 background trajectory hook을 `carla_runner.py`에 추가해야 할
  가능성이 있다(rss_label에 background 궤적이 필요).
- SafeBench rollout 단위는 default `num_scenario=2`라 셀 1개 = rollout 1개로
  매핑하려면 `scripts/run.py --num_scenario 1`로 강제하거나 wrapper에서
  data_ids별로 분리해 셀 단위 응답을 만든다(bev_wrapper도 같은 결정).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CellResponse:
    """한 셀 (AV π, 생성기 G, severity c, trial k)의 응답 한 행."""
    av_id: str
    g_id: str
    c: float
    trial_k: int
    y: int                          # 0 무충돌, 1 충돌
    t_collision: Optional[float]    # 충돌 시점 (sim time, sec). 없으면 None
    collision_type: Optional[str]   # 'ego_at_fault' | 'bg_at_fault' | 'unavoidable' | None
    u_label: Optional[float]        # rss_label 후처리. 0~1, RSS 위반 정도
    ego_traj: Optional[list] = field(default=None)   # (T, [x,y,vx,vy,heading])
    bg_traj: Optional[dict] = field(default=None)    # {bg_id: (T, [...])}
    meta: dict = field(default_factory=dict)         # route_id·town·weather·step 등


def extract_rollout_response(rollout_log: dict, cell_meta: dict) -> CellResponse:
    """SafeBench carla_runner.py 한 rollout 출력 → CellResponse 한 건.

    Args:
        rollout_log: SafeBench Logger가 dump한 dict. 키 후보:
            - 'collision' (bool 또는 dict)
            - 'collision_time' (sec) / 'collision_actor' (carla.Actor id)
            - 'ego_history' (list of state)
            - 'bg_history' (dict of actor_id -> list of state)
              -> background trajectory hook 추가 후에만 채워짐
            - 'scenario_config' (yaml에서 풀린 메타)
        cell_meta: 셀 식별자 dict {'av_id','g_id','c','trial_k'}

    Returns:
        CellResponse. u_label은 별도로 rss_labeler.rss_label로 채운다.
    """
    raise NotImplementedError("B 단계 첫 작업에서 SafeBench Logger 키 스펙 확인 후 채움")


def label_avoidability(resp: CellResponse, rss_params: dict) -> CellResponse:
    """rss_labeler를 호출해 resp.u_label 채움. ego·bg 궤적이 필요."""
    from .rss_labeler import rss_label
    if resp.ego_traj is None:
        raise ValueError("ego_traj가 비어 있음: SafeBench logger에서 ego_history 확인")
    if resp.bg_traj is None:
        raise ValueError("bg_traj가 비어 있음: background trajectory hook 추가 필요")
    if resp.y == 0:
        resp.u_label = 0.0   # 충돌 안 났으면 회피불가 라벨 무관
        return resp
    resp.u_label = rss_label(resp.ego_traj, resp.bg_traj, resp.t_collision, rss_params)
    return resp


def append_response(resp: CellResponse, table_path: Path) -> None:
    """응답표(JSONL)에 한 행 append. parquet 변환은 격자 끝나고 별도."""
    raise NotImplementedError("dataclass → dict → json.dumps 한 줄, append 모드로 write")


def collect_grid_responses(
    grid: dict, sb_log_dir: Path, output_path: Path, rss_params: dict
) -> None:
    """한 격자 (AV × G × severity × K)의 모든 rollout 출력을 응답표로 모음.

    흐름:
        1. sb_log_dir 아래의 SafeBench 결과 dict를 셀별로 로드
        2. 각 rollout을 extract_rollout_response로 변환
        3. label_avoidability로 u_label 채움
        4. append_response로 output_path에 누적
        5. 격자 끝에 보고서 출력 (실패 셀 비율 등, D-10)
    """
    raise NotImplementedError("B 단계 첫 작업: SafeBench 출력 디렉토리 구조 확인 후 채움")
