"""adv_behavior_attach: BehaviorAgent를 background actor에 attach한 시나리오 정의.

plan §4의 "IDM/MOBIL 기반 + 공격성 다른 몇 종" 권고에서 MOBIL 본격 자리.
adv_behavior_single이 background actor를 target_speed로만 조절했다면 이 자리는
CARLA `agents.navigation.behavior_agent.BehaviorAgent`를 actor에 attach해 매
step `run_step()`이 만든 control(throttle·steer·brake)을 적용한다. behavior_type
(cautious·normal·aggressive)을 c 다이얼로 받아 BehaviorAgent의 7개 변수(max_speed
·min_proximity_threshold·braking_distance 등)가 단조 변경되도록 한다.

이번 turn은 sid=8 NoSignalJunctionCrossingRoute 한 클래스만(우리 본 격자에서
실제로 사용되는 자리). 나머지 클래스는 본격 진입 후 확장.
"""

from .junction_crossing_route import NoSignalJunctionCrossingRouteAttach
