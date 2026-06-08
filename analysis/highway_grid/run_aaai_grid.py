# -*- coding: utf-8 -*-
"""AAAI 격자 실행 : highway-env + ACARL 인프라 (라운드 16 결정).

본 스크립트는 결정 트레일 라운드 16의 격자 재설계를 직접 굴린다. 응시자(AV)는
IDM·MOBIL·Defensive RL 5-seed 일곱 종이며, 적대 생성기(G)는 ACARL cut-in·ACARL
rear-end·Method B(Naive)·Method C(Rule-based, AuthSim 구조) 네 종이다. 위험도 c는
{0, 1, 2, 3, 4} 다섯 수준이고 ACARL c_level ∈ [0, 0.8]에 c=k → c_level=0.2k로
매핑된다. 반복 K는 기본 20이며 총 격자 규모는 7 × 4 × 5 × 20 = 2,800 episode이다.

본 스크립트는 ACARL의 AdversarialNPCEvalEnv(`src/environments/npc_adapter.py`)와
evaluate_av_downstream.py의 응시자 호출 패턴을 활용하여 한 episode를 굴리고,
응답을 D1·D2·D3·D4 분석 코드의 입력 jsonl 형식으로 출력한다.

출력 jsonl 형식:
    {av_id, g_id, c, trial_k, y, ep_len, thw_mean, ttc_min, ego_speed}

usage:
    # 작은 단조성 pilot (K=5)
    python3 analysis/highway_grid/run_aaai_grid.py --pilot

    # 본 격자 (K=20)
    python3 analysis/highway_grid/run_aaai_grid.py --K 20

    # 단일 (av, g) 점검
    python3 analysis/highway_grid/run_aaai_grid.py --K 2 --av idm --g acarl_cutin
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import types
from pathlib import Path

import numpy as np


# ACARL 인프라 부분 ─────────────────────────────────────────────────────────────
ACARL_ROOT = Path("/home/hyunchul/ASG/ASG_2026")
if str(ACARL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACARL_ROOT))

# highway_env import (ACARL 환경 의존성)
import highway_env  # noqa: F401, E402

# Gymnasium compat patch (evaluate_av_downstream_5def.py L33-46 동일 흐름)
try:
    import gymnasium.wrappers.monitoring  # noqa: F401
except (ImportError, ModuleNotFoundError):
    import gymnasium.wrappers  # noqa: F401
    m = types.ModuleType("gymnasium.wrappers.monitoring")
    sys.modules["gymnasium.wrappers.monitoring"] = m
    try:
        from gymnasium.wrappers import RecordVideo as _RV
        vr = types.ModuleType("gymnasium.wrappers.monitoring.video_recorder")
        vr.VideoRecorder = _RV
        m.video_recorder = vr
    except ImportError:
        vr = types.ModuleType("gymnasium.wrappers.monitoring.video_recorder")
        m.video_recorder = vr
    sys.modules["gymnasium.wrappers.monitoring.video_recorder"] = m.video_recorder


# 격자 정의 ───────────────────────────────────────────────────────────────────
AV_DEFINITIONS = {
    "idm": {
        "av_policy": "idm",
        "model_path": None,
        "swap_to_idm_vehicle": False,
    },
    "mobil": {
        "av_policy": "idm",
        "model_path": None,
        "swap_to_idm_vehicle": True,
    },
    "def_rl_42": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive/seed42_20260411_235554/final_model.zip",
    },
    "def_rl_123": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive/seed123_20260411_235554/final_model.zip",
    },
    "def_rl_456": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive/seed456_20260420_184409/final_model.zip",
    },
    "def_rl_789": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive/seed789_20260411_235554/final_model.zip",
    },
    "def_rl_1024": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive/seed1024_20260420_191733/final_model.zip",
    },
    # === N=20 응시자 확장 (2026-06-07 라운드 19, 학습 방식 다양성 확보) ===
    # PPO 새 5 seed (기존 42·123·456·789·1024 외 추가 5 seed)
    "ppo_100": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/ppo/seed100_20260606_161734/final_model.zip",
        "algorithm": "PPO",
    },
    "ppo_200": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/ppo/seed200_20260606_165153/final_model.zip",
        "algorithm": "PPO",
    },
    "ppo_500": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/ppo/seed500_20260606_172454/final_model.zip",
        "algorithm": "PPO",
    },
    "ppo_800": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/ppo/seed800_20260606_175755/final_model.zip",
        "algorithm": "PPO",
    },
    "ppo_999": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/ppo/seed999_20260606_183115/final_model.zip",
        "algorithm": "PPO",
    },
    # SAC 5 seed (다른 학습 방식, off-policy)
    "sac_42": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/sac/seed42_20260606_190615/final_model.zip",
        "algorithm": "SAC",
    },
    "sac_100": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/sac/seed100_20260606_200456/final_model.zip",
        "algorithm": "SAC",
    },
    "sac_456": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/sac/seed456_20260606_210258/final_model.zip",
        "algorithm": "SAC",
    },
    "sac_789": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/sac/seed789_20260606_220142/final_model.zip",
        "algorithm": "SAC",
    },
    "sac_999": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/sac/seed999_20260606_225956/final_model.zip",
        "algorithm": "SAC",
    },
    # TD3 5 seed (DDPG 안정 변형, off-policy)
    "td3_42": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/td3/seed42_20260606_235759/final_model.zip",
        "algorithm": "TD3",
    },
    "td3_100": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/td3/seed100_20260607_004002/final_model.zip",
        "algorithm": "TD3",
    },
    "td3_456": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/td3/seed456_20260607_012101/final_model.zip",
        "algorithm": "TD3",
    },
    "td3_789": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/td3/seed789_20260607_020219/final_model.zip",
        "algorithm": "TD3",
    },
    "td3_999": {
        "av_policy": "external",
        "model_path": ACARL_ROOT / "results/defensive_multi/td3/seed999_20260607_024412/final_model.zip",
        "algorithm": "TD3",
    },
}

GEN_DEFINITIONS = {
    "acarl_cutin": {
        "adv_model_path": ACARL_ROOT / "results/phase1/seed42_20260408_163617/tb_logs/best_collision_model.zip",
        "scenario_type": "cut_in",
    },
    "acarl_rearend": {
        "adv_model_path": ACARL_ROOT / "results/phase1/seed42_20260408_163617/tb_logs/best_collision_model.zip",
        "scenario_type": "rear_end",
    },
    "method_b": {
        "adv_model_path": ACARL_ROOT / "results/phase2/naive_seed42_done/final_model.zip",
        "scenario_type": "rear_end",
    },
    "method_c": {
        "adv_model_path": ACARL_ROOT / "results/phase2/rule_seed42/tb_logs/best_collision_model.zip",
        "scenario_type": "rear_end",
    },
}

C_LEVELS = [0.0, 0.2, 0.4, 0.6, 0.8]    # c=0,1,2,3,4 → c_level
EVAL_SEED_BASE = 20000
MAX_STEPS = 200
_TTC_INF = 999.0


# 응시자 호출 자료 ──────────────────────────────────────────────────────────────
def _build_25d_obs(env) -> np.ndarray:
    """Defensive RL 응시자가 받는 25차원 ego-centric obs (evaluate_av_downstream_5def.py 동일)."""
    inner = env.unwrapped
    ego = inner.vehicle
    ex, ey = ego.position
    evx = ego.speed * math.cos(ego.heading)
    evy = ego.speed * math.sin(ego.heading)
    others = sorted(
        [(math.sqrt((v.position[0] - ex) ** 2 + (v.position[1] - ey) ** 2), v)
         for v in inner.road.vehicles if v is not ego],
        key=lambda x: x[0],
    )
    obs = np.zeros((5, 5), dtype=np.float32)
    obs[0] = [ex / 200, ey / 12, evx / 40, evy / 40, ego.heading / (2 * math.pi)]
    for i, (_, v) in enumerate(others[:4]):
        vx, vy = v.position
        obs[i + 1] = [
            (vx - ex) / 200, (vy - ey) / 12,
            (v.speed * math.cos(v.heading) - evx) / 40,
            (v.speed * math.sin(v.heading) - evy) / 40,
            v.heading / (2 * math.pi),
        ]
    return np.clip(obs.flatten(), -1, 1)


def _swap_ego_to_idm_vehicle(env) -> None:
    """MOBIL 응시자: ego를 IDMVehicle로 교체 (evaluate_av_downstream.py L106 동일)."""
    from highway_env.vehicle.behavior import IDMVehicle  # noqa: WPS433
    inner = env.unwrapped
    ego = inner.vehicle
    new_ego = IDMVehicle(
        road=inner.road,
        position=ego.position.copy(),
        heading=ego.heading,
        speed=ego.speed,
    )
    if ego in inner.road.vehicles:
        idx = inner.road.vehicles.index(ego)
        inner.road.vehicles[idx] = new_ego
    inner.vehicle = new_ego


def _load_av_models() -> dict:
    """Defensive RL 응시자 ckpt 로드. IDM·MOBIL은 모델이 없으므로 None.

    알고리즘별 분기 추가 (2026-06-07 라운드 19): PPO·SAC·TD3 분기로
    N=20 응시자 확장에 필요한 자료. av_def["algorithm"] 자료가 없으면
    기존 PPO로 로드 (기존 def_rl_42·123·456·789·1024 호환).
    """
    from stable_baselines3 import PPO, SAC, TD3  # noqa: WPS433
    ALGO_MAP = {"PPO": PPO, "SAC": SAC, "TD3": TD3}
    av_models: dict = {}
    for av_id, av_def in AV_DEFINITIONS.items():
        path = av_def["model_path"]
        if path is None:
            av_models[av_id] = None
            continue
        if not Path(path).exists():
            print(f"!! AV ckpt missing: {av_id}: {path}", file=sys.stderr)
            sys.exit(1)
        algo = av_def.get("algorithm", "PPO")
        algo_cls = ALGO_MAP.get(algo)
        if algo_cls is None:
            raise ValueError(f"Unknown algorithm '{algo}' for AV {av_id}")
        av_models[av_id] = algo_cls.load(str(path), device="cpu")
        print(f">> loaded AV: {av_id} ({algo}) ← {path}", flush=True)
    return av_models


# 한 episode 실행 ─────────────────────────────────────────────────────────────
def run_one_episode(av_id: str, g_id: str, c_idx: int, trial_k: int,
                    av_model) -> dict:
    """한 episode 굴리고 응답 dict 반환.

    응답 jsonl 한 줄은 D2 split-half(`load_responses`)의 입력 형식과 정합한다.
    """
    from src.environments.npc_adapter import AdversarialNPCEvalEnv  # noqa: WPS433
    av_def = AV_DEFINITIONS[av_id]
    gen_def = GEN_DEFINITIONS[g_id]
    c_level = C_LEVELS[c_idx]
    c_value = float(c_idx)

    env = AdversarialNPCEvalEnv(
        adversarial_model_path=str(gen_def["adv_model_path"]),
        av_policy=av_def["av_policy"],
        scenario_type=gen_def["scenario_type"],
        c_level=c_level,
        render_mode="none",
        vehicles_count=15,
        lanes_count=3,
        duration=MAX_STEPS,
    )

    seed = (EVAL_SEED_BASE + abs(hash((av_id, g_id, c_idx, trial_k))) % 100000)
    error_msg = None
    try:
        env.reset(seed=seed)
    except Exception as e:
        env.close()
        return {
            "av_id": av_id, "g_id": g_id, "c": c_value, "trial_k": trial_k,
            "y": 0, "ep_len": 0,
            "thw_mean": None, "ttc_min": None, "ego_speed": 0.0,
            "error": f"reset:{e}",
        }
    if av_def.get("swap_to_idm_vehicle"):
        try:
            _swap_ego_to_idm_vehicle(env)
        except Exception as e:
            error_msg = f"swap:{e}"

    collision = False
    thws: list = []
    ttc_min = _TTC_INF
    ego_speed_final = 0.0
    ep_len = 0
    info: dict = {}
    for _ in range(MAX_STEPS):
        ep_len += 1
        if av_def["av_policy"] == "external" and av_model is not None:
            obs25 = _build_25d_obs(env)
            action, _ = av_model.predict(obs25, deterministic=True)
        else:
            action = np.zeros(2, dtype=np.float32)
        try:
            _obs, _r, term, trunc, info = env.step(action)
        except Exception as e:
            error_msg = error_msg or f"step:{e}"
            break
        thw = info.get("thw", _TTC_INF)
        ttc = info.get("ttc", _TTC_INF)
        if 0 < thw < 100:
            thws.append(float(thw))
        if 0 < ttc < ttc_min:
            ttc_min = float(ttc)
        if info.get("collision"):
            collision = True
        if term or trunc:
            break
    ego_speed_final = float(info.get("ego_speed", 0.0))
    env.close()

    resp = {
        "av_id": av_id,
        "g_id": g_id,
        "c": c_value,
        "trial_k": trial_k,
        "y": int(collision),
        "ep_len": ep_len,
        "thw_mean": float(np.mean(thws)) if thws else None,
        "ttc_min": float(ttc_min) if ttc_min < _TTC_INF else None,
        "ego_speed": ego_speed_final,
    }
    if error_msg:
        resp["error"] = error_msg
    return resp


# 격자 실행 ────────────────────────────────────────────────────────────────────
def run_grid(K: int, out_path: Path,
             av_filter: list | None = None,
             g_filter: list | None = None) -> None:
    av_models = _load_av_models()

    av_ids = [a for a in AV_DEFINITIONS if (av_filter is None or a in av_filter)]
    g_ids = [g for g in GEN_DEFINITIONS if (g_filter is None or g in g_filter)]
    n_total = len(av_ids) * len(g_ids) * len(C_LEVELS) * K
    print(f">> 격자: AV={len(av_ids)} × G={len(g_ids)} × c={len(C_LEVELS)} × K={K} "
          f"= {n_total} episode", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    idx = 0
    with open(out_path, "w") as f:
        for av_id in av_ids:
            for g_id in g_ids:
                for c_idx in range(len(C_LEVELS)):
                    for k in range(K):
                        idx += 1
                        resp = run_one_episode(av_id, g_id, c_idx, k,
                                               av_models.get(av_id))
                        f.write(json.dumps(resp) + "\n")
                        f.flush()
                        if idx <= 5 or idx % 50 == 0 or idx == n_total:
                            wall = time.time() - t0
                            eta = wall / idx * (n_total - idx)
                            err = f" ERR:{resp['error']}" if "error" in resp else ""
                            print(f"  [{idx}/{n_total}] {av_id:>11} × {g_id:<15} "
                                  f"c={resp['c']:.0f} k={k:>2}  y={resp['y']}  "
                                  f"wall={wall:.0f}s ETA={eta:.0f}s{err}",
                                  flush=True)
    print(f">> 완료: {idx} episode, wall={time.time() - t0:.0f}s, 응답 → {out_path}",
          flush=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--K", type=int, default=20, help="cell당 episode 반복 수")
    p.add_argument("--out", default="analysis/highway_grid/responses.jsonl")
    p.add_argument("--pilot", action="store_true", help="작은 단조성 pilot (K=5)")
    p.add_argument("--av", nargs="+", default=None, help="응시자 부분집합")
    p.add_argument("--g", nargs="+", default=None, help="생성기 부분집합")
    args = p.parse_args()

    if args.pilot:
        K = 5
        out_path = Path("analysis/highway_grid/pilot_responses.jsonl")
    else:
        K = args.K
        out_path = Path(args.out)

    run_grid(K=K, out_path=out_path,
             av_filter=args.av, g_filter=args.g)


if __name__ == "__main__":
    main()
