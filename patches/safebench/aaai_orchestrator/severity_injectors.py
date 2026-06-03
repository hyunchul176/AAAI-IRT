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
    # LC(REINFORCE init-state policy)의 c 다이얼 후보. 검토자 라운드 10이 짚은
    # 자리로, 매 시나리오 시작 위치 한 번 결정에서 c 5수준을 만들 자리는
    # sample_action의 Gaussian σ에 곱하는 sigma_scale 한 자리 변수다. 가설
    # 1(sigma 작음 → 학습된 mu 근처 결정 → 공격력 증가)을 1차 후보로 박고,
    # 단조성 pilot 2차에서 ρ ≥ 0.7 미달이면 가설 2(sigma 큼 → mu 분포 tail의
    # 극단적 공격 위치 sample)로 반전 시도. method.html 식 (6) γ_G·c와 정합한
    # 자리는 sigma_scale 단일 변수 다이얼이지만 단조성 방향 자체는 가설.
    "lc": {
        0.0: {"sigma_scale": 2.0},
        1.0: {"sigma_scale": 1.5},
        2.0: {"sigma_scale": 1.0},
        3.0: {"sigma_scale": 0.7},
        4.0: {"sigma_scale": 0.5},
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

    def patched_get_init_action(self, state, infos, deterministic=False):
        processed_state = self.proceess_init_state(state)
        processed_state = CUDA(torch.from_numpy(processed_state))
        # AAAI-IRT patch (라운드 11): NF는 매 호출 다른 z를 sample하므로 같은
        # (sid, rid, data_id, seed) 셀이라도 매번 다른 action이 나와 cell-level
        # reproducibility가 깨진다. SafeBench의 set_seed가 process 시작 시
        # 한 번 호출되므로 그 자리 이후 매 호출 manual_seed로 결정성을 강제한다.
        # 같은 셀의 K=10 trial은 호출 횟수가 다르므로 자연스럽게 다른 z를 받는다.
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


_INJECTORS: dict[str, Callable[[float], None]] = {
    "lc": _patch_lc,
    "nf": _patch_nf,
    "advsim": _patch_hardcode,
    "advtraj": _patch_hardcode,
    "ordinary": _patch_dummy,
    "fppo_adv": _patch_fppo_adv,
}


def apply_severity(scenario_policy: str, c_value: float) -> None:
    """진입점. orchestrator(run_one_cell.py)가 SafeBench import 직전 또는 직후에
    한 번 호출한다. SafeBench 모듈을 monkey-patch하므로 같은 프로세스 안에서
    호출되어야 한다.
    """
    if scenario_policy not in _INJECTORS:
        raise ValueError(f"unknown scenario_policy: {scenario_policy}")
    _INJECTORS[scenario_policy](c_value)
