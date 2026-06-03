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
    "lc": {},          # 예: {0.0: {"sigma_scale": 0.3}, 1.0: {"sigma_scale": 0.6}, ...}
    "nf": {},          # 예: {0.0: {"flow_sigma": 0.5}, ...}
    "advsim": {},      # parameters 인덱스(data_id) 통제, 별도 매핑 필요 없음
    "advtraj": {},     # 같음
    "ordinary": {0.0: {}},   # severity 무관, c=0만 인정
    "fppo_adv": {},    # FREA PPO sample noise scale
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
    """NF flow_sample sigma 직접 매핑.

    NormalizingFlow.flow_sample(state, sample_number=1000, sigma=1.0)이 명시
    sigma 인자를 받는다. 호출자가 어디서 sigma를 어떻게 넘기는지 SafeBench의
    호출 사슬을 따라가야 정확한 monkey-patch가 가능하다(현재 NF는 SafeBench
    eval 흐름에서 어떻게 호출되는지 추가 점검 필요). 우선 인터페이스만 둔다.
    """
    mapping = SEVERITY_MAP["nf"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"NF severity mapping for c={c_value} not yet calibrated by pilot"
        )
    flow_sigma = mapping["flow_sigma"]
    from safebench.scenario.scenario_policy import normalizing_flow_policy as nf

    orig_flow_sample = nf.NormalizingFlow.flow_sample

    def patched_flow_sample(self, state, sample_number=1000, sigma=1.0):
        return orig_flow_sample(self, state, sample_number=sample_number, sigma=flow_sigma)

    nf.NormalizingFlow.flow_sample = patched_flow_sample


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
    """FREA fppo_adv는 PPO.get_action에서 self.policy.get_action으로 sample한다.
    sample noise scale을 monkey-patch로 곱해 c 단계를 만든다(NF처럼 명시 인자
    없음). 정확한 진입점은 FREA의 PPO.policy 객체 구조 점검이 필요하므로
    인터페이스만 잡아 둔다.
    """
    mapping = SEVERITY_MAP["fppo_adv"].get(c_value)
    if mapping is None:
        raise NotImplementedError(
            f"FREA fppo_adv severity mapping for c={c_value} not yet calibrated by pilot"
        )
    # 실제 hook은 FREA의 PPO.policy.get_action 분포 구조 점검 후 채운다. mapping
    # 표가 채워졌다는 것은 pilot이 진입점을 확인했다는 뜻이므로 그 시점에 여기서
    # 실제 monkey-patch를 적용한다.
    raise NotImplementedError(
        "fppo_adv hook awaiting FREA PPO sample-distribution inspection; "
        f"SEVERITY_MAP['fppo_adv'][{c_value}]={mapping} is set but no patch wired"
    )


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
