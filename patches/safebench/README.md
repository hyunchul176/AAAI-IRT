# SafeBench patches for AAAI-IRT

이 디렉토리는 SafeBench upstream을 건드리지 않고 한 셀(AV, G, scenario_id,
route_id, data_id, c, k) 단위로 SafeBench eval을 호출할 수 있도록 모은 최소
패치를 담는다. 두 부분으로 나뉜다.

## Patch 1: `route_scenario.py` · background vehicle trajectories in records.pkl

응답표 변환 결정의 잔여 위험 노트("background trajectory hook may be required")를
해소한다. SafeBench `gym_carla/envs/carla_env.py`가 `vehicle.*`·`walker.*` actor를
이미 추적하지만 `records.pkl`에 적히는 step dict가 ego state만 들고 있어, 우리
RSS 라벨러가 회피불가 판정을 할 수 없다. 패치는 `RouteScenario`에 헬퍼
`_aaai_collect_bg_trajectories`를 더하고 `get_running_status`에 한 키
(`bg_trajectories`)를 더한다.

파일:
- `route_scenario_original.py`: SafeBench `safebench/safebench:latest` docker
  이미지(2026-06-03 pull) 안의 `safebench/scenario/scenario_definition/route_scenario.py`
  원본.
- `route_scenario_patched.py`: 위 파일에 한 메서드와 한 키만 추가.

적용(컨테이너에 idempotent하게 덮어쓰기):

```bash
docker cp patches/safebench/route_scenario_patched.py \
    <container>:/home/safebench/SafeBench/safebench/scenario/scenario_definition/route_scenario.py
```

적용 후 `records.pkl`의 모든 step dict에 `bg_trajectories` 키가 잡힌다.
`analysis/b4-pipeline/sb_to_response.py`가 그것을 `bg_traj`로 읽어
`analysis/b4-pipeline/rss_labeler.py`로 회피불가 라벨 u를 부여한다.

## Patch 2: `aaai_orchestrator/` · 셀 단위 yaml override + severity injection

응답 격자(1,800 cells)의 한 셀을 SafeBench eval 한 번에 1대1로 매핑한다.
SafeBench `scripts/run.py`는 yaml의 `scenario_id`·`route_id` 두 필드로만
scenario_type json을 filter하므로 셀별로 yaml override가 필요하다(생성기·
severity 결정의 2026-06-03 갱신 노트).

구성:
- `yaml_override.py`: base scenario yaml을 읽어 (scenario_id, route_id,
  model_id)를 셀에 맞게 덮어쓴 tmp yaml을 `safebench/scenario/config/`
  안에 만든다(scripts/run.py가 파일명만 받기 때문). cleanup은
  `run_one_cell.py`가 atexit으로 처리.
- `severity_injectors.py`: 정책별 c → hyperparameter monkey-patch.
  LC(REINFORCE sample sigma)·NF(flow_sample sigma)·HardCode(parameters 인덱스,
  data_id로 통제)·Ordinary(no-op)·FREA fppo_adv(PPO sample noise) 다섯 정책의
  진입점만 잡아 두었고, 실제 c → hyperparam 매핑 값은 단조성 pilot이
  채운다(`SEVERITY_MAP` 표).
- `run_one_cell.py`: 컨테이너 안에서 한 셀당 한 SafeBench eval을 띄우는
  entrypoint. 호출 예:

  ```bash
  python aaai_orchestrator/run_one_cell.py \
      --agent-cfg sac.yaml --scenario-cfg LC.yaml \
      --sid 2 --rid 0 --data-id 40 \
      --c-value 0.0 --policy-type lc \
      --seed 1234 --exp-name g3_sac_lc_c0.0_k00_s2r0d40
  ```

  내부적으로 yaml override → severity inject → `scripts/run.py` 본문을
  `runpy.run_path`로 동일 프로세스에서 실행한다(별도 프로세스로 띄우면
  monkey-patch가 적용되지 않는다).

적용(컨테이너에 패키지 통째로 복사):

```bash
docker cp patches/safebench/aaai_orchestrator \
    <container>:/home/safebench/SafeBench/aaai_orchestrator
```

FREA 트리도 같은 위치(`/home/safebench/FREA/aaai_orchestrator/`)에 두면
fppo_adv 셀이 그 트리에서 실행될 때 동일 entrypoint를 쓸 수 있다.

## 단조성 pilot 후 채워야 하는 자리

`severity_injectors.SEVERITY_MAP`이 현재 비어 있다. 단조성 pilot
(`analysis/b4-pipeline/run_g3_grid.py`로 1 AV × 1 G × 5 c × 5 k = 25 셀
smoke run)에서 c → hyperparam 매핑이 (AV, G) 쌍에서 충돌률 vs c의 Spearman
ρ ≥ 0.7을 만족하는지 확인한 뒤 그 매핑 표를 코드에 박는다(생성기·severity
결정의 합격 판정).

패치를 작게 유지해 upstream SafeBench 갱신 시 재적용이 쉽도록 했다.
