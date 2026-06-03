# -*- coding: utf-8 -*-
"""
B4 응답 기록 어댑터 (decisions.html 응답표 변환 결정).

SafeBench `scripts/run.py --mode eval` 실행이 끝나면
`log/exp/<exp_name>/eval_results/` 아래에 두 파일을 남긴다:

    results.pkl  — aggregate dict (collision_rate·distance_to_route·... 6 metric)
    records.pkl  — dict {cell_index: list of step dict}
                   step dict 키 (2026-06-03 실측 확인, exp_sac_lc_seed_0):
                     ego_velocity, ego_acceleration_x/y/z,
                     ego_x, ego_y, ego_z, ego_roll, ego_pitch, ego_yaw,
                     current_game_time, driven_distance, average_velocity,
                     lane_invasion, off_road, collision (py_trees Status enum),
                     run_red_light, run_stop, distance_to_route, route_complete

이 어댑터가 records.pkl을 읽어 우리 측정 모델 식 (6)의 응답 한 행 CellResponse로
변환한다. background 차량 시계열 궤적은 SafeBench 기본 logger에 없으므로
(응답표 변환 결정의 잔여 위험 노트 확인) `bg_traj` 필드는 None으로 두고, RSS 라벨러는
ego 단독으로는 회피불가 판정이 불가하니 u_label도 None으로 둔다. 본 격자
진입 전 SafeBench carla_runner에 background trajectory hook 추가가 필요하다.

사용:
    records = load_records("log/exp/exp_sac_lc_seed_0/eval_results/records.pkl")
    resp = extract_cell_response(records, cell_index=0,
                                  cell_meta={"av_id":"sac","g_id":"lc","c":0.0,"trial_k":0})
    collect_grid_responses(grid_log_dir, cell_meta_map, "responses.jsonl")

의존성: pickle.load가 SafeBench 모듈(safebench.*, carla)을 동적으로 import한다.
어댑터는 SafeBench 도커 컨테이너 안에서 실행하거나, 호스트에 SafeBench +
carla-0.9.13 egg를 PYTHONPATH로 잡고 실행한다.
"""
from __future__ import annotations

import json
import pickle
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
    collision_type: Optional[str]   # 'ego_at_fault' | 'bg_at_fault' | 'unavoidable' | 'unknown' | None
    u_label: Optional[float]        # rss_label 후처리. 0~1, RSS 위반 정도
    ego_traj: Optional[list] = field(default=None)   # (T, [x,y,vx,vy,heading])
    bg_traj: Optional[dict] = field(default=None)    # {bg_id: (T, [...])}, SafeBench hook 추가 후 채움
    meta: dict = field(default_factory=dict)         # cell_index·route·step·기타 진단 정보


def _status_is_collision(status) -> bool:
    """SafeBench의 'collision' 키 값이 py_trees.common.Status enum이고
    Status.FAILURE면 충돌, Status.RUNNING/SUCCESS는 무충돌로 본다.
    enum import 의존성 회피를 위해 str(value)로 비교한다."""
    if status is None:
        return False
    s = str(status)
    return "FAILURE" in s or "Failure" in s


def load_records(records_path) -> dict:
    """SafeBench records.pkl 로드. 의존성(safebench.*, carla)이 PYTHONPATH에 있어야 한다."""
    with open(records_path, "rb") as f:
        return pickle.load(f)


def extract_cell_response(records: dict, cell_index: int, cell_meta: dict) -> CellResponse:
    """records dict에서 한 셀(cell_index)을 CellResponse 한 행으로 변환.

    Args:
        records: load_records() 결과 (dict {int -> list of step dict})
        cell_index: SafeBench가 부여한 (route, scenario) 인덱스
        cell_meta: 우리 격자 셀 식별자 {'av_id','g_id','c','trial_k'}

    Returns:
        CellResponse. u_label은 별도로 rss_labeler.label_avoidability로 채운다.
    """
    if cell_index not in records:
        raise KeyError(f"cell_index {cell_index} not in records (available: "
                       f"{min(records)}~{max(records)} total {len(records)})")
    steps = records[cell_index]
    n_steps = len(steps)
    if n_steps == 0:
        return CellResponse(
            av_id=cell_meta["av_id"], g_id=cell_meta["g_id"],
            c=cell_meta["c"], trial_k=cell_meta["trial_k"],
            y=0, t_collision=None, collision_type=None, u_label=None,
            ego_traj=None, bg_traj=None,
            meta=dict(cell_index=cell_index, n_steps=0, empty=True),
        )

    # 충돌 검출: collision 키가 FAILURE로 전환되는 첫 step
    y = 0
    t_collision: Optional[float] = None
    for step in steps:
        if _status_is_collision(step.get("collision")):
            y = 1
            t_collision = float(step.get("current_game_time", 0.0))
            break

    # ego 시계열 (T, [x, y, velocity, yaw])
    ego_traj = [
        [
            float(s.get("ego_x", 0.0)),
            float(s.get("ego_y", 0.0)),
            float(s.get("ego_velocity", 0.0)),
            float(s.get("ego_yaw", 0.0)),
        ]
        for s in steps
    ]

    # background trajectory 추출. patches/safebench/route_scenario_patched.py가
    # 적용된 컨테이너의 records.pkl에는 step dict에 'bg_trajectories' 키가
    # 들어 있고 그 값은 {"actors": list, "error": str|None} dict다. actors의
    # 각 원소는 {id,type,kind('vehicle'|'walker'),role,x,y,velocity,yaw}.
    # 어댑터는 actor_id별 시계열로 묶고 actor 메타(kind 포함)는 meta에 적어
    # rss_labeler가 vehicle/walker를 구분할 수 있게 한다. patch가 안 들어간
    # 컨테이너의 결과는 None으로 둔다.
    bg_traj: Optional[dict] = None
    bg_actor_meta: dict = {}
    bg_error_steps: list = []
    if "bg_trajectories" in steps[0]:
        bg_traj = {}
        for i, s in enumerate(steps):
            entry = s.get("bg_trajectories") or {}
            actors = entry.get("actors", []) if isinstance(entry, dict) else entry
            if isinstance(entry, dict) and entry.get("error"):
                bg_error_steps.append((i, entry["error"]))
            for v in actors:
                vid = int(v.get("id", -1))
                if vid < 0:
                    continue
                bg_traj.setdefault(vid, []).append([
                    float(v.get("x", 0.0)),
                    float(v.get("y", 0.0)),
                    float(v.get("velocity", 0.0)),
                    float(v.get("yaw", 0.0)),
                ])
                if vid not in bg_actor_meta:
                    bg_actor_meta[vid] = dict(
                        type=v.get("type"),
                        kind=v.get("kind", "vehicle"),
                        role=v.get("role"),
                    )
        if not bg_traj:
            bg_traj = None  # patch는 들어갔지만 한 actor도 없었던 경우

    last = steps[-1]
    meta = dict(
        cell_index=cell_index,
        n_steps=n_steps,
        route_complete=float(last.get("route_complete", 0.0)),
        driven_distance=float(last.get("driven_distance", 0.0)),
        average_velocity=float(last.get("average_velocity", 0.0)),
        off_road=bool(any(s.get("off_road") for s in steps)),
        lane_invasion=bool(any(s.get("lane_invasion") for s in steps)),
        run_red_light=bool(any(s.get("run_red_light") for s in steps)),
        bg_actor_meta=bg_actor_meta,
        bg_error_steps=bg_error_steps[:5],   # 처음 5개만 (디버그용)
    )

    return CellResponse(
        av_id=cell_meta["av_id"],
        g_id=cell_meta["g_id"],
        c=float(cell_meta["c"]),
        trial_k=int(cell_meta["trial_k"]),
        y=y,
        t_collision=t_collision,
        collision_type="unknown" if y == 1 else None,
        u_label=None,
        ego_traj=ego_traj,
        bg_traj=bg_traj,
        meta=meta,
    )


def _resp_to_dict(resp: CellResponse) -> dict:
    """CellResponse → JSON-serializable dict (jsonl 한 줄)."""
    return dict(
        av_id=resp.av_id, g_id=resp.g_id, c=resp.c, trial_k=resp.trial_k,
        y=resp.y, t_collision=resp.t_collision, collision_type=resp.collision_type,
        u_label=resp.u_label,
        ego_traj=resp.ego_traj, bg_traj=resp.bg_traj,
        meta=resp.meta,
    )


def append_response(resp: CellResponse, table_path) -> None:
    """응답표(JSONL)에 한 행 append."""
    with open(table_path, "a") as f:
        f.write(json.dumps(_resp_to_dict(resp), ensure_ascii=False) + "\n")


def collect_grid_responses(
    grid_log_dir, cell_meta_map: dict, output_path, rss_params: Optional[dict] = None,
) -> dict:
    """한 격자 SafeBench eval 로그 디렉토리 → 응답표 JSONL.

    흐름:
      1. records.pkl 로드
      2. cell_meta_map의 각 cell_index에 대해 extract_cell_response 호출
      3. (rss_params and bg_traj available) → label_avoidability로 u_label 채움
      4. output_path(JSONL)에 한 행씩 append
      5. 보고서 dict 반환 (총 셀 수·결측·충돌률·평균 step 수)

    Args:
        grid_log_dir: SafeBench eval log dir (records.pkl·results.pkl 포함)
        cell_meta_map: dict {cell_index: cell_meta(dict)}
        output_path: 응답표 JSONL path (덮어쓰기)
        rss_params: rss_labeler 파라미터 dict. None이면 u_label은 None으로 남김.
    """
    grid_log_dir = Path(grid_log_dir)
    records = load_records(grid_log_dir / "records.pkl")
    output_path = Path(output_path)
    output_path.write_text("")  # 초기화

    stats = dict(n_total=len(cell_meta_map), n_missing=0, n_collision=0,
                 n_with_bg=0, n_labeled=0, mean_n_steps=0.0)
    sum_steps = 0

    for cell_index, cell_meta in cell_meta_map.items():
        if cell_index not in records:
            stats["n_missing"] += 1
            continue
        resp = extract_cell_response(records, cell_index, cell_meta)
        sum_steps += resp.meta.get("n_steps", 0)
        if resp.y == 1:
            stats["n_collision"] += 1
        # background traj hook이 추가된 뒤에만 RSS 라벨링 가능
        if resp.bg_traj is not None:
            stats["n_with_bg"] += 1
            if rss_params is not None and resp.y == 1:
                from .rss_labeler import rss_label
                resp.u_label = rss_label(resp.ego_traj, resp.bg_traj,
                                         resp.t_collision, rss_params)
                stats["n_labeled"] += 1
        append_response(resp, output_path)

    n_ok = stats["n_total"] - stats["n_missing"]
    stats["mean_n_steps"] = (sum_steps / n_ok) if n_ok > 0 else 0.0
    stats["collision_rate"] = (stats["n_collision"] / n_ok) if n_ok > 0 else 0.0
    return stats


if __name__ == "__main__":
    # 빠른 sanity: 직전 LC + SAC pilot 로그에서 한 셀을 변환해 출력
    import sys
    log_dir = sys.argv[1] if len(sys.argv) > 1 else \
        "log/exp/exp_sac_lc_seed_0/eval_results"
    records = load_records(Path(log_dir) / "records.pkl")
    print(f"records cells: {len(records)}  index range: "
          f"{min(records)}~{max(records)}")
    sample_idx = next(iter(records))
    resp = extract_cell_response(records, sample_idx,
                                 dict(av_id="sac", g_id="lc", c=0.0, trial_k=0))
    print(f"cell {sample_idx}: y={resp.y} n_steps={resp.meta['n_steps']} "
          f"route_complete={resp.meta['route_complete']:.2f} "
          f"driven={resp.meta['driven_distance']:.1f}m  "
          f"off_road={resp.meta['off_road']} lane_inv={resp.meta['lane_invasion']}")
    print(f"  ego_traj first/last: {resp.ego_traj[0]}  /  {resp.ego_traj[-1]}")
