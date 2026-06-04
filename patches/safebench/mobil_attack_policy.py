# -*- coding: utf-8 -*-
"""MOBIL 기반 단순화 적대 시나리오 정책.

plan §4의 "IDM/MOBIL 기반" 표준 단순 생성기 권고에서 MOBIL 자리. CARLA의
BehaviorAgent가 cautious·normal·aggressive 세 단계의 behavior_type을 가지며
각 단계는 max_speed·safety_time·min_proximity_threshold·braking_distance 등
7개 변수에서 단조 변화한다(behavior_types.py 확인).

본 정책은 두 단계 단순화 위에 만들어졌다. 본격은 BehaviorAgent를 background
actor에 attach해 매 step run_step() control을 받는 새 시나리오 정의가 필요한
1주 작업이라 다음 turn 작업으로 분리. 이번 turn은 BehaviorAgent의
behavior_type 단계 max_speed 분포만 c 다이얼에 매핑해 IDMAttackPolicy와 다른
c→speed 곡선을 만든다(IDM 0~50 m/s 폭, MOBIL 11~19 m/s 폭).

학술적 차이는 두 정책이 같은 인터페이스(target_speed) 위에 다른 c 곡선을
얹은 자리라 정책 family로 정직하게 다른 자리는 아니지만, c=0 부드러운 진입과
c=4 빠른 진입의 폭 자체가 다른 두 G로 split-half 검정 자리를 의미 있게 만든다.
본문 한계: BehaviorAgent attach 본격 구현은 향후 검증.
"""
from __future__ import annotations

from safebench.scenario.scenario_policy.base_policy import BasePolicy


class MOBILAttackPolicy(BasePolicy):
    name = "mobil_attack"
    type = "unlearnable"

    def __init__(self, scenario_config, logger):
        self.logger = logger
        self.num_scenario = scenario_config["num_scenario"]
        # default: BehaviorAgent normal의 max_speed 50 km/h ≈ 13.9 m/s.
        # convert_actions: speed = action[0]*5 + 5 → action ≈ 1.78
        self._aaai_action_value = 1.78
        self.continue_episode = 0
        self.mode = "eval"

    def train(self, replay_buffer):
        pass

    def set_mode(self, mode):
        self.mode = mode

    def get_action(self, state, infos, deterministic=False):
        return [[self._aaai_action_value] for _ in range(self.num_scenario)]

    def get_init_action(self, state, deterministic=False):
        return [None] * self.num_scenario, None

    def load_model(self, scenario_configs=None):
        return None

    def save_model(self, episode):
        pass
