# -*- coding: utf-8 -*-
"""IDM 기반 단순 적대 시나리오 정책.

plan §4·§13의 셋째 기여(표준적·단순 생성기 위 SUT-불변 측정)를 회복하기
위한 모듈. SafeBench의 `adv_behavior_single` 시나리오 정의(`update_behavior`가
`convert_actions: speed = action[0]*5 + 5`로 background actor target_speed
조절)와 함께 작동한다.

우리 c 다이얼은 action[0] 한 스칼라 변수로 매핑된다. c=0.0(부드러운 진입)부터
c=4.0(빠른 진입)까지 background actor가 ego 진로에 단조 강하게 진입한다.
Wang·Ma·Lai 2024의 공격성 파라미터와 같은 역할이고, RL 학습이 봉인한
hyperparameter와 달리 c가 코드 수준에서 명시되어 단조성이 보장된다.

학습 없음(`type='unlearnable'`). REINFORCE·NF처럼 ckpt 로드도 없다.
"""
from __future__ import annotations

from safebench.scenario.scenario_policy.base_policy import BasePolicy


class IDMAttackPolicy(BasePolicy):
    name = "idm_attack"
    type = "unlearnable"

    def __init__(self, scenario_config, logger):
        self.logger = logger
        self.num_scenario = scenario_config["num_scenario"]
        # AAAI-IRT: c 다이얼을 yaml에서 직접 받을 수도 있고, severity_injectors의
        # SEVERITY_MAP['idm_attack']에서 monkey-patch로 주입할 수도 있다. 후자
        # 방식은 다른 정책(LC·NF)과 인터페이스 일관성을 가지므로 그대로 둔다.
        # 여기서는 default 1.0(중간 c=2.0과 같음)을 보존.
        self._aaai_action_value = 1.0
        # 학습된 정책의 inference-time 분기와 일관되도록 placeholder.
        self.continue_episode = 0
        self.mode = "eval"

    def train(self, replay_buffer):
        # type='unlearnable'이라 학습 단계 없음. 일관성 위해 pass.
        pass

    def set_mode(self, mode):
        self.mode = mode

    def get_action(self, state, infos, deterministic=False):
        """매 step 호출. background actor target_speed를 결정짓는 1차원 action을
        num_scenario 만큼 list로 돌려준다. severity_injectors가 모듈 외부에서
        `_aaai_action_value`를 주입한 값에 따라 c별로 다른 속도가 나온다.
        """
        return [[self._aaai_action_value] for _ in range(self.num_scenario)]

    def get_init_action(self, state, deterministic=False):
        """adv_behavior_single 시나리오 정의는 init_action을 사용하지 않는다.
        get_action만으로 매 step target_speed를 결정한다.
        """
        return [None] * self.num_scenario, None

    def load_model(self, scenario_configs=None):
        # 학습 ckpt 없음. graceful skip(train_scenario 흐름에서 호출되는 경로 +
        # eval 흐름에서 호출되는 경로 둘 다).
        return None

    def save_model(self, episode):
        # 학습 없으므로 저장도 없음.
        pass
