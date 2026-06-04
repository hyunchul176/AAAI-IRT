# -*- coding: utf-8 -*-
"""정책별 c(severity) → hyperparameter 매핑.

생성기·severity 결정에 따라 각 정책의 c는 자기 단위의 hyperparameter로
들어간다(LC는 sample sigma, NF는 flow_sample sigma, AdvSim·AdvTraj는 parameters
인덱스, ordinary는 무관). 단조성을 만족하는 c → hyperparam 매핑 자체는 단조성
pilot이 답해야 하므로(생성기·severity 결정의 본문에서 ρ ≥ 0.7 합격선) 이 파일은
인터페이스와 hook 자리만 잡고 실제 매핑 값은 SEVERITY_MAP에 표로 둔다.

사용:
    from aaai_orchestrator.severity_injectors import apply_severity
    apply_severity(scenario_policy="lc", c_value=2.0)
    # 이후 SafeBench가 자기 흐름대로 정책을 import·init·run하면
    # monkey-patch가 그 init/run에 자동으로 끼어든다.

지금은 LC·NF·HardCode·DummyPolicy·FREA fppo_adv 다섯 정책의 진입점만 정의하고
실제 c → hyperparam 곡선은 단조성 pilot 결과로 채운다(빈 dict).
"""
from __future__ import annotations

from typing import Callable


# c는 우리 격자에서 0.0..4.0 5수준이지만 정책별 자기 단위는 다르다.
# 단조성 pilot(생성기·severity 결정의 ρ ≥ 0.7 합격선)을 통과한 매핑이 여기에
# 들어간다. pilot 전에는 비워 두고, severity injector는 c_value가 매핑에 없으면
# 명시적으로 NotImplementedError를 던지도록 한다(silent fallback 금지).
SEVERITY_MAP: dict[str, dict[float, dict[str, float]]] = {
    # IDMAttackPolicy의 c 다이얼 (라운드 14 정정: 범위 확장).
    # adv_behavior_single.update_behavior의 convert_actions는 `speed = action[0]*5 + 5`로
    # 변환한다. action[0] 범위를 더 넓혀 background actor target_speed가 더 공격적인
    # 자리까지 펼쳐지도록 한다. pilot v2 (sac, idm_attack)에서 target_speed 5~25 m/s가
    # SAC ego·시나리오 8에 너무 약했다는 진단(라운드 13)에 따라 c=0→-1.0(0 m/s 정지),
    # c=4→9.0(50 m/s 고속) 자리로 폭을 두 배 키운다. 명시 변수 자리에 다이얼을 직접
    # 거는 길은 plan §4·§13 정합(검토자 라운드 14).
    "idm_attack": {
        0.0: {"action_value": -1.0},  # → speed = 0  m/s (정지)
        1.0: {"action_value":  1.5},  # → speed = 12.5 m/s
        2.0: {"action_value":  4.0},  # → speed = 25 m/s
        3.0: {"action_value":  6.5},  # → speed = 37.5 m/s
        4.0: {"action_value":  9.0},  # → speed = 50 m/s (고속 진입)
    },
    # MOBILAttackPolicy: BehaviorAgent behavior_type 단계(cautious 40 km/h ≈ 11
    # m/s / normal 50 ≈ 14 m/s / aggressive 70 ≈ 19 m/s)의 max_speed 분포를
    # c 5수준에 선형 보간. speed = action*5 + 5 변환이므로:
    # c=0 cautious 11 m/s → action 1.2 / c=2 normal 14 m/s → action 1.78 /
    # c=4 aggressive 19 m/s → action 2.8. IDM의 폭(0~50 m/s)과 다른 좁은
    # 폭(11~19)이라 두 G가 다른 c→speed 곡선 family로 작동.
    "mobil_attack": {
        0.0: {"action_value": 1.20},  # cautious
        1.0: {"action_value": 1.50},
        2.0: {"action_value": 1.80},  # normal
        3.0: {"action_value": 2.30},
        4.0: {"action_value": 2.80},  # aggressive
    },
    # MOBIL v2: BehaviorAgent attach 본격. update_behavior가 정수 0~2를 받아
    # behavior_type 단계를 갈아끼움(cautious·normal·aggressive). 단순화 MOBIL(11~19
    # m/s target_speed 폭)과 달리 throttle·steer·brake control 자체를 BehaviorAgent
    # 7개 변수(max_speed·min_proximity·braking_distance 등)에서 정합 결정한다.
    # c 5수준은 세 단계에 분배: c=0~1 cautious, c=2 normal, c=3~4 aggressive.
    "mobil_attack_v2": {
        0.0: {"action_value": 0.0},  # cautious
        1.0: {"action_value": 0.0},  # cautious
        2.0: {"action_value": 1.0},  # normal
        3.0: {"action_value": 2.0},  # aggressive
        4.0: {"action_value": 2.0},  # aggressive
    },
    # LC(REINFORCE init-state policy)의 c 다이얼. 라운드 14 검토 + K=30 재pilot
    # 결과(2026-06-04)로 가설 2(σ 큼 → mu 분포 tail의 다양·극단 공격 위치
    # sample → 공격력 증가)가 검증됨. (sac, lc) sigma_scale=2.0(옛 c=0) 자리에서
    # 30 cells 충돌률 26.67%, Wilson 95% CI [0.142, 0.444], random(p=0.05)과
    # FREA Table 2(p=0.10) 둘 다 통계적으로 다름. 따라서 라벨을 반전해
    # c=0→sigma_scale 0.3(거의 결정적, mu 그대로), c=4→sigma_scale 2.0(검증된
    # 공격 자리)으로 매핑하면 단조 곡선이 자연.
    "lc": {
        0.0: {"sigma_scale": 0.3},
        1.0: {"sigma_scale": 0.7},
        2.0: {"sigma_scale": 1.0},
        3.0: {"sigma_scale": 1.5},
        4.0: {"sigma_scale": 2.0},
    },
    # NF c 다이얼: get_init_action의 latent z 분산 σ. z=0(c=0.0)은 학습된 mode
    # 그대로, σ 키울수록 latent tail에서 sample. 가설 1을 1차 후보로 박고
    # 단조성 pilot 2차에서 검증.
    "nf": {
        0.0: {"flow_sigma": 0.0},
        1.0: {"flow_sigma": 0.25},
        2.0: {"flow_sigma": 0.5},
        3.0: {"flow_sigma": 1.0},
        4.0: {"flow_sigma": 2.0},
    },
    "advsim": {},      # parameters 인덱스(data_id) 통제, 별도 매핑 필요 없음
    "advtraj": {},     # 같음
    "ordinary": {0.0: {}},   # severity 무관, c=0만 인정
    # FREA fppo_adv는 학습 progress step 자체가 severity 다이얼이다. CBV_ckpt의
    # `model.fppo_adv.cbv.<episode>.torch` 파일 episode 인덱스를 c에 매핑한다.
    # 후보 5수준은 단조성 pilot이 합격 판정할 자리(생성기·severity 결정의
    # Spearman ρ ≥ 0.7).
    "fppo_adv": {
        0.0: {"episode":   50},
        1.0: {"episode":  200},
        2.0: {"episode":  500},
        3.0: {"episode":  900},
        4.0: {"episode": 1250},
    },
}


def _patch_lc(c_value: float) -> None:
    """LC(REINFORCE) sample sigma scaling.

    `reinforce_continuous.AutoregressiveModel.sample_action`이 sigma = softplus(.)
    후 mu + sigma*eps로 sample한다. severity는 그 sigma에 c-derived scale을 곱해
    sample 분포의 폭을 키우거나 줄인다. mu(공격 평균 위치)는 그대로 두고 sigma만
    조절하므로 c=낮음 → sample이 mu 근처로 모임, c=높음 → sample이 mu 주변으로
    퍼짐. 단조성은 pilot이 확인한다.
    """
    mapping = SEVERITY_MAP["lc"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"LC severity mapping for c={c_value} not yet calibrated by pilot"
        )
    sigma_scale = mapping["sigma_scale"]
    from safebench.scenario.scenario_policy import reinforce_continuous as rc

    orig_sample = rc.AutoregressiveModel.sample_action

    def patched_sample(self, normal_action, action_os):
        action, mu, sigma = orig_sample(self, normal_action, action_os)
        # mu는 그대로 두고 sigma만 scale → 같은 평균에서 분산만 변경
        scaled_sigma = sigma * sigma_scale
        eps = (action - mu) / (sigma + 1e-8)
        new_action = mu + scaled_sigma * eps
        return new_action, mu, scaled_sigma

    rc.AutoregressiveModel.sample_action = patched_sample


def _patch_nf(c_value: float) -> None:
    """NF의 c 다이얼: get_init_action의 latent z 분산 σ.

    SafeBench eval 흐름에서 NF는 `flow_sample`이 아니라 `get_init_action`을
    호출한다 (normalizing_flow_policy.py:221). 그 안 `mean = zeros(action_dim)`
    +`action = self.model.inverse(mean, condition)`. z=0이면 학습된 mode를
    그대로 받고, z를 N(0, σ²I)에서 sample하면 latent space의 다른 자리에서
    flow 역방향 결과를 받는다. σ가 곧 c 다이얼이다.

    가설 1 (검토자 라운드 10 정합): σ 키우면 latent tail에서 mode 밖 sample →
    더 다양한·극단적 공격 위치. 단조성 pilot 2차에서 ρ ≥ 0.7 미달이면 가설 2
    (σ 키우면 학습된 mode를 잃음 → 공격력 감소)로 반전 시도.
    """
    mapping = SEVERITY_MAP["nf"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"NF severity mapping for c={c_value} not yet calibrated by pilot"
        )
    flow_sigma = mapping["flow_sigma"]
    import torch
    from safebench.scenario.scenario_policy import normalizing_flow_policy as nf
    from safebench.util.torch_util import CUDA

    # 셀당 trial_k 카운터(같은 process 안 호출 순서 = trial_k). SafeBench가
    # data_loader를 한 자리만 남기도록 yaml override하면 한 process = 한 셀이
    # 되고, K 반복은 별도 process로 호출되어 _call_idx는 항상 0이 된다.
    # 두 자리 모두 결정성 강제.
    _aaai_call_idx = [0]

    def patched_get_init_action(self, state, infos, deterministic=False):
        # AAAI-IRT patch (라운드 12): 같은 (sid, rid, data_id, seed) 셀이 매
        # 호출 다른 z를 받지 않도록 manual_seed로 결정성 강제. trial_k는
        # severity_injectors가 알 자리가 없으므로 (cell seed + call index)
        # 조합으로 결정성 확보. SafeBench process 외부에서 trial_k별 새 seed로
        # 호출되는 자리(한 셀 한 process)에서는 _call_idx가 항상 0.
        seed = int(torch.initial_seed()) & 0xFFFFFFFF
        torch.manual_seed(seed + _aaai_call_idx[0] * 7919)
        _aaai_call_idx[0] += 1
        processed_state = self.proceess_init_state(state)
        processed_state = CUDA(torch.from_numpy(processed_state))
        self.model.eval()
        with torch.no_grad():
            # z=0 대신 z ~ N(0, flow_sigma²I) sample (학습된 base prior 정합).
            z = CUDA(torch.randn(self.action_dim)[None]) * flow_sigma
            condition = CUDA(torch.tensor(processed_state))[None]
            action = self.model.inverse(z, condition)
        action_list = []
        for a_i in range(self.action_dim):
            action_list.append(action.cpu().numpy()[0, a_i])
        return action_list

    nf.NormalizingFlow.get_init_action = patched_get_init_action


def _patch_hardcode(c_value: float) -> None:
    """AdvSim·AdvTraj severity는 scenario_type json의 parameters 인덱스로
    통제한다(advsim에는 0.json~9.json의 attack 파라미터 파일이 있다). 매핑은
    orchestrator가 data_id를 셀에 부여할 때 결정되므로 여기서는 no-op이다.
    """
    _ = c_value
    return  # data_id 매핑이 동등 역할


def _patch_dummy(c_value: float) -> None:
    """Ordinary는 비적대 baseline이라 severity와 무관. c=0만 의미 있고 다른
    c값은 같은 결과를 준다. orchestrator가 ordinary에 대해 c=0 한 수준만
    생성하도록 보장하면 이 hook은 사실상 호출되지 않는다.
    """
    if c_value != 0.0:
        raise ValueError(
            f"ordinary policy is non-adversarial baseline; only c=0 is meaningful, got c={c_value}"
        )


def _patch_fppo_adv(c_value: float) -> None:
    """FREA fppo_adv는 학습 progress가 곧 severity 다이얼이다. PPO.load_model이
    `model.fppo_adv.cbv.<episode>.torch` 파일을 episode 인자로 골라 로드하므로
    (frea/scenario/scenario_policy/rl/ppo.py:229-254), 우리 c 5수준은 episode
    인덱스 5개로 매핑한다(생성기·severity 결정).

    monkey-patch는 PPO.load_model을 wrap해 episode 인자를 강제로 매핑값으로
    바꾼다. carla_runner의 self.scenario_policy.load_model(map_name=...)
    호출이 그 wrap을 거치게 된다.
    """
    mapping = SEVERITY_MAP["fppo_adv"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"FREA fppo_adv severity mapping for c={c_value} not yet calibrated by pilot"
        )
    target_episode = mapping["episode"]
    from frea.scenario.scenario_policy.rl.ppo import PPO

    orig_load = PPO.load_model

    def patched_load(self, map_name, episode=None):
        return orig_load(self, map_name, episode=target_episode)

    PPO.load_model = patched_load


def _patch_idm_attack(c_value: float) -> None:
    """IDMAttackPolicy의 c 다이얼을 SEVERITY_MAP에서 받아 인스턴스 attribute에
    주입. policy.get_action이 매 step `[[self._aaai_action_value]]`을 돌려주고
    그 값이 adv_behavior_single.update_behavior의 convert_actions에서
    `speed = action[0]*5 + 5`로 변환된다.
    """
    mapping = SEVERITY_MAP["idm_attack"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"IDMAttackPolicy severity mapping for c={c_value} not yet calibrated"
        )
    action_value = mapping["action_value"]
    from safebench.scenario.scenario_policy import idm_attack as ia

    orig_init = ia.IDMAttackPolicy.__init__

    def patched_init(self, scenario_config, logger):
        orig_init(self, scenario_config, logger)
        self._aaai_action_value = action_value

    ia.IDMAttackPolicy.__init__ = patched_init


def _patch_mobil_attack(c_value: float) -> None:
    """MOBILAttackPolicy의 c 다이얼 주입. IDM과 같은 monkey-patch 패턴."""
    mapping = SEVERITY_MAP["mobil_attack"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"MOBILAttackPolicy severity mapping for c={c_value} not yet calibrated"
        )
    action_value = mapping["action_value"]
    from safebench.scenario.scenario_policy import mobil_attack as ma

    orig_init = ma.MOBILAttackPolicy.__init__

    def patched_init(self, scenario_config, logger):
        orig_init(self, scenario_config, logger)
        self._aaai_action_value = action_value

    ma.MOBILAttackPolicy.__init__ = patched_init


def _patch_mobil_attack_v2(c_value: float) -> None:
    """MOBILAttackPolicyV2의 c 다이얼 주입. behavior_type 단계 0~2."""
    mapping = SEVERITY_MAP["mobil_attack_v2"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"MOBILAttackPolicyV2 severity mapping for c={c_value} not yet calibrated"
        )
    action_value = mapping["action_value"]
    from safebench.scenario.scenario_policy import mobil_attack_v2 as mav2

    orig_init = mav2.MOBILAttackPolicyV2.__init__

    def patched_init(self, scenario_config, logger):
        orig_init(self, scenario_config, logger)
        self._aaai_action_value = action_value

    mav2.MOBILAttackPolicyV2.__init__ = patched_init


_INJECTORS: dict[str, Callable[[float], None]] = {
    "lc": _patch_lc,
    "nf": _patch_nf,
    "advsim": _patch_hardcode,
    "advtraj": _patch_hardcode,
    "ordinary": _patch_dummy,
    "fppo_adv": _patch_fppo_adv,
    "idm_attack": _patch_idm_attack,
    "mobil_attack": _patch_mobil_attack,
    "mobil_attack_v2": _patch_mobil_attack_v2,
}


def apply_severity(scenario_policy: str, c_value: float) -> None:
    """진입점. orchestrator(run_one_cell.py)가 SafeBench import 직전 또는 직후에
    한 번 호출한다. SafeBench 모듈을 monkey-patch하므로 같은 프로세스 안에서
    호출되어야 한다.
    """
    if scenario_policy not in _INJECTORS:
        raise ValueError(f"unknown scenario_policy: {scenario_policy}")
    _INJECTORS[scenario_policy](c_value)
