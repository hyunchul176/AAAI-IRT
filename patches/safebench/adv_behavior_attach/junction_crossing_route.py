# -*- coding: utf-8 -*-
"""BehaviorAgent attach 자리. adv_behavior_single.NoSignalJunctionCrossingRoute에서
update_behavior가 target_speed로 go_straight 호출하던 자리를 BehaviorAgent.run_step()
호출로 바꿈.

c 다이얼은 scenario_action[0]을 [0, 1, 2] 정수 인덱스로 받아 behavior_type을
cautious(0)·normal(1)·aggressive(2)로 매핑. severity_injectors가 그 매핑을
주입한다.
"""
from __future__ import annotations

import carla

from agents.navigation.behavior_agent import BehaviorAgent
from agents.navigation.behavior_types import Cautious, Normal, Aggressive

from safebench.scenario.scenario_manager.carla_data_provider import CarlaDataProvider
from safebench.scenario.scenario_definition.basic_scenario import BasicScenario
from safebench.scenario.tools.scenario_operation import ScenarioOperation
from safebench.scenario.tools.scenario_utils import calculate_distance_transforms


_BEHAVIOR_BY_LEVEL = {
    0: ("cautious",  Cautious),
    1: ("normal",    Normal),
    2: ("aggressive", Aggressive),
}


class NoSignalJunctionCrossingRouteAttach(BasicScenario):
    """No-signal junction crossing route + BehaviorAgent attached background actor."""

    def __init__(self, world, ego_vehicle, config, timeout=60):
        super().__init__(
            "NoSignalJunctionCrossingRoute-Behavior-Attach",
            config, world,
        )
        self.ego_vehicle = ego_vehicle
        self.timeout = timeout
        self.scenario_operation = ScenarioOperation()
        self.reference_actor = None
        self.trigger = False
        self._actor_distance = 110
        self.ego_max_driven_distance = 150
        self.bg_agent = None  # actor spawn 후 initialize_actors에서 만든다

    def convert_actions(self, actions):
        # action[0] ∈ [0, 1, 2] (정수). severity_injectors가 c→정수 매핑 주입.
        # 그 외 값은 round해서 [0, 2] 범위에 clamp.
        try:
            lvl = int(round(float(actions[0])))
        except (TypeError, ValueError):
            lvl = 1
        return max(0, min(2, lvl))

    def initialize_actors(self):
        other_actor_transform = self.config.other_actors[0].transform
        forward_vector = other_actor_transform.rotation.get_forward_vector() * self.other_actor_delta_x
        other_actor_transform.location += forward_vector
        first_vehicle_transform = carla.Transform(
            carla.Location(
                other_actor_transform.location.x,
                other_actor_transform.location.y,
                other_actor_transform.location.z,
            ),
            other_actor_transform.rotation,
        )
        self.actor_transform_list = [first_vehicle_transform]
        self.actor_type_list = ["vehicle.audi.tt"]
        self.other_actors = self.scenario_operation.initialize_vehicle_actors(
            self.actor_transform_list, self.actor_type_list,
        )
        self.reference_actor = self.other_actors[0]
        # BehaviorAgent attach (시작은 normal, update_behavior에서 c별로 갈아끼움)
        if self.other_actors[0] is not None:
            self.bg_agent = BehaviorAgent(self.other_actors[0], behavior="normal")
            # ego 진입 자리를 destination으로 한 번만 설정. ego가 그 자리를 통과하면
            # background actor는 path planner 안 fall-back으로 마지막 자리 향함.
            ego_loc = self.ego_vehicle.get_location()
            try:
                self.bg_agent.set_destination(ego_loc)
            except Exception:
                # CARLA 0.9.13 BehaviorAgent.set_destination 인자 차이 자리 안전
                pass

    def create_behavior(self, scenario_init_action):
        assert scenario_init_action is None, f"{self.name} should receive [None] initial action."
        self.other_actor_delta_x = 1.0
        self.trigger_distance_threshold = 35

    def update_behavior(self, scenario_action):
        if self.bg_agent is None or self.other_actors[0] is None:
            return
        lvl = self.convert_actions(scenario_action)
        # behavior_type 단계 변경: BehaviorAgent._behavior를 새 객체로 갈아끼움.
        # behavior_types.Cautious/Normal/Aggressive는 max_speed·min_proximity·
        # braking_distance 등 7개 변수가 단조 변하는 자리.
        _, behavior_cls = _BEHAVIOR_BY_LEVEL[lvl]
        self.bg_agent._behavior = behavior_cls()
        # run_step이 throttle·steer·brake control을 만든다.
        try:
            control = self.bg_agent.run_step()
            self.other_actors[0].apply_control(control)
        except Exception:
            # BehaviorAgent run_step의 자리 변동 (예: _incoming_waypoint=None)은
            # CARLA upstream 자리 한계라 graceful skip + 그 step은 no-control.
            pass

    def check_stop_condition(self):
        cur_distance = calculate_distance_transforms(
            CarlaDataProvider.get_transform(self.other_actors[0]),
            self.actor_transform_list[0],
        )
        return cur_distance >= self._actor_distance
