# -*- coding: utf-8 -*-
"""
RSS 라벨러 후처리 (decisions.html 응답표 변환 결정 + A4 결정).

한 충돌 셀에 회피불가 하한 u(0~1)를 부여한다. 우리 측정 모델 식 (6)의
P(충돌) = u + (1 − u)·σ(a·(β + γc − θ)) 우변에서 u가 곧 이 라벨이다.

RSS (Shalev-Shwartz et al. 2017) §3의 안전거리·적정대응 정의:

    종방향 (앞차가 reaction time ρ 동안 a_max,brake로 제동한다고 가정):
        d_long_min = v_rear·ρ + 0.5·a_max,acc·ρ²
                   + (v_rear + a_max,acc·ρ)² / (2·a_min,brake)
                   − v_front² / (2·a_max,brake)

    횡방향 (반응 시간 ρ 안에 양쪽이 양 옆으로 가속 후 감속):
        d_lat_min = (v_lat,1 + v_lat,2 + a_max,lat·ρ)·ρ

ego가 충돌 직전에 위 두 안전거리 중 하나라도 어겼으면 ego가 RSS 위반 →
회피 가능 (u → 0). 둘 다 지켰는데도 충돌이면 무과실 → u → 1.

soft 라벨링 (A4 결정):
    u = 1 − max(0, min(1, max(d_long_min − d_long, d_lat_min − d_lat) / scale))
    또는 RSS 위반량을 logistic으로 [0,1]에 매핑.

파라미터 (응답표 변환 결정):
    RSS 원문 (Shalev-Shwartz 2017) §3 default + Liu(2021)·Xu(2021) 실주행
    보정값을 민감도로 같이 보고. Khan(2026)은 종방향만 적용한 전례라
    횡방향·교차 시나리오는 RSS 원문을 직접 따라간다.

대안 중심값 (A4 결정에 따라 함께 보고):
    - LFR (FREA, frea/feasibility/HJ_Reachability.py): HJ-Reachability 기반
      회피가능 영역. RSS와 다른 위상 정보.
    - over-critical: ego가 RSS의 가장 엄격한 변종을 어겼을 때만 회피 가능
      (덜 엄격, u가 1에 더 쏠림).
"""
from __future__ import annotations

from typing import Optional

import numpy as np


# RSS 원문 기본 파라미터 (Shalev-Shwartz et al. 2017 §3)
RSS_PARAMS_ORIGINAL = dict(
    rho=0.5,           # 반응 시간 (sec)
    a_max_acc=3.0,     # 종방향 최대 가속도 (m/s²)
    a_max_brake=8.0,   # 종방향 최대 제동 (m/s²)
    a_min_brake=4.0,   # 종방향 최소 (legally required) 제동 (m/s²)
    a_max_lat=1.0,     # 횡방향 최대 가속도 (m/s²)
)

# Liu(2021)·Xu(2021) 실주행 보정값 (sec-d 카드 참조, 실측 후 갱신)
RSS_PARAMS_LIU_XU = dict(
    rho=0.7,
    a_max_acc=2.5,
    a_max_brake=7.0,
    a_min_brake=3.5,
    a_max_lat=0.8,
)


def _d_long_min(v_rear: float, v_front: float, p: dict) -> float:
    """RSS 종방향 최소 안전거리."""
    rho = p["rho"]
    return max(
        0.0,
        v_rear * rho
        + 0.5 * p["a_max_acc"] * rho ** 2
        + (v_rear + p["a_max_acc"] * rho) ** 2 / (2 * p["a_min_brake"])
        - v_front ** 2 / (2 * p["a_max_brake"]),
    )


def _d_lat_min(v_lat_1: float, v_lat_2: float, p: dict) -> float:
    """RSS 횡방향 최소 안전거리."""
    rho = p["rho"]
    return max(0.0, (v_lat_1 + v_lat_2 + p["a_max_lat"] * rho) * rho)


def rss_label(
    ego_traj: np.ndarray,
    bg_traj: dict,
    collision_t: Optional[float],
    params: Optional[dict] = None,
    soft_scale: float = 2.0,
) -> float:
    """한 충돌 셀에 RSS 회피불가 하한 u를 부여.

    Args:
        ego_traj: (T, [x, y, vx, vy, heading]) numpy array. 충돌 직전까지.
        bg_traj : {bg_actor_id: (T, [x,y,vx,vy,heading])} dict.
                  rss_label은 충돌 상대 actor 한 명만 따져도 충분.
        collision_t: 충돌 시점 (sec). t 이전 마지막 step의 상대 위치로 RSS.
        params : RSS 파라미터 dict. None이면 RSS_PARAMS_ORIGINAL.
        soft_scale: 위반량을 0~1로 매핑하는 scale (m).

    Returns:
        u in [0, 1]. 1에 가까울수록 무과실(회피 불가).

    Notes:
        - bg_traj가 비어 있으면 RSS 계산 불가 → ValueError. SafeBench의
          background trajectory hook이 필요(응답표 변환 결정의 잔여 위험 노트).
        - 충돌 상대 actor 결정 로직: collision_t 직전 가장 가까운 bg actor.
        - 종·횡 두 위반량 중 큰 쪽 (=ego가 더 명확히 어긴 쪽)을 기준.
    """
    if params is None:
        params = RSS_PARAMS_ORIGINAL
    if collision_t is None:
        return 0.0
    raise NotImplementedError(
        "B 단계 첫 작업: SafeBench 궤적 포맷 확인 후 (i) 충돌 상대 actor 식별, "
        "(ii) 충돌 직전 step에서 종·횡 위반량 계산, (iii) soft 매핑 채움"
    )


def rss_label_alternative(
    ego_traj: np.ndarray,
    bg_traj: dict,
    collision_t: Optional[float],
    method: str = "lfr",
) -> float:
    """A4 결정의 대안 중심값. 'lfr'는 FREA HJ-Reachability,
    'over_critical'은 가장 엄격한 RSS 변종. 민감도 분석용.
    """
    if method == "lfr":
        raise NotImplementedError(
            "FREA frea/feasibility/HJ_Reachability.py의 학습된 모델 추론 호출"
        )
    if method == "over_critical":
        params_strict = dict(RSS_PARAMS_ORIGINAL)
        params_strict["rho"] = 0.3   # 더 짧은 반응 시간 → 더 엄격
        params_strict["a_max_brake"] = 10.0
        return rss_label(ego_traj, bg_traj, collision_t, params_strict)
    raise ValueError(f"unknown alternative method: {method}")
