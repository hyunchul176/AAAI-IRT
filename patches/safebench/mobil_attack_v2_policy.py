# -*- coding: utf-8 -*-
"""MOBIL v2 (BehaviorAgent attach 본격) 정책.

adv_behavior_attach 시나리오 정의(`NoSignalJunctionCrossingRouteAttach`)와
짝. update_behavior가 scenario_action[0]을 정수 0~2(behavior_type 단계)로 받음.
0=cautious, 1=normal, 2=aggressive. severity_injectors._patch_mobil_attack_v2가
c→behavior_type 매핑을 인스턴스 attribute로 주입.
"""
from __future__ import annotations

from safebench.scenario.scenario_policy.base_policy import BasePolicy


class MOBILAttackPolicyV2(BasePolicy):
    name = "mobil_attack_v2"
    type = "unlearnable"

    def __init__(self, scenario_config, logger):
        self.logger = logger
        self.num_scenario = scenario_config["num_scenario"]
        # default normal (lvl=1)
        self._aaai_action_value = 1.0
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
