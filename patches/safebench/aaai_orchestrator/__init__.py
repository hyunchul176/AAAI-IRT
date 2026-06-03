"""SafeBench orchestrator patches for the AAAI-IRT response grid.

이 패키지는 SafeBench 컨테이너 안에 docker cp되어 한 셀(AV, G, scenario_id,
route_id, data_id, c, k) 단위로 SafeBench eval을 호출한다. yaml override·
severity injection을 한 자리에 모아 SafeBench upstream을 건드리지 않는다.

구성:
- yaml_override: 셀별 scenario yaml을 tmp 파일로 만들어 scenario_id·route_id를
  강제한다(scenario_utils.py의 filter는 yaml의 두 필드만 보므로).
- severity_injectors: 정책별 c → hyperparameter 매핑을 적용한다(인터페이스만
  지금 작성, 실제 매핑은 단조성 pilot이 결정).
- run_one_cell: 한 셀당 한 SafeBench eval을 띄우는 entrypoint.
"""
