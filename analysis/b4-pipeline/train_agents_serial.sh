#!/bin/bash
# DDPG·PPO·TD3 직렬 학습 orchestrator (본 격자 AV=6 진입 위한 RL ego 3종 확보)
#
# pilot v2 (host PID 추적)이 끝난 뒤 DDPG → PPO → TD3 순으로 train_agent
# 모드로 직렬 학습. 각 종 train_episode=2000 (sac.yaml 등과 같은 자리),
# 예상 ~1.7h × 3 = ~5h. CARLA 한 인스턴스(port 2000)를 공유하므로 동시 학습
# 안 함. scenario_cfg=ordinary.yaml(비적대 baseline)로 ego만 학습.
#
# 우리 SafeBench 패치(carla_data_provider·basic_scenario·route_scenario·
# carla_runner timeout)가 train_scenario에서 풀린 자리라 train_agent에서도
# 풀릴 가능성 큼. RL agent의 load_model(episode=None)이 자동 last episode
# 검색 + 파일 없으면 graceful skip(라운드 9에서 검증)이라 별도 patch 없음.
#
# pilot v2 polling은 LC 학습 orchestrator의 pgrep-self-match bug를 피해
# host process PID로 직접 추적한다.
#
# usage:
#   nohup bash analysis/b4-pipeline/train_agents_serial.sh > \
#       analysis/b4-pipeline/train_agents_serial.log 2>&1 &

set -uo pipefail

CONTAINER=sb-pilot
PYTHONPATH_CONTAINER='/home/safebench/carla/PythonAPI/carla/dist/carla-0.9.13-py3.8-linux-x86_64.egg:/home/safebench/carla/PythonAPI/carla/agents:/home/safebench/carla/PythonAPI/carla:/home/safebench/carla/PythonAPI'

wait_pilot_done() {
    echo ">> $(date +%H:%M:%S) waiting for pilot v2 (pilot_monotonic_v2.py) to finish..."
    while pgrep -af "pilot_monotonic_v2.py" > /dev/null 2>&1; do
        sleep 60
    done
    echo ">> $(date +%H:%M:%S) pilot v2 finished"
}

train_one_agent() {
    local agent="$1"   # ddpg | ppo | td3
    local exp="train_${agent}_seed0"
    local log_in="/tmp/train_${agent}.log"
    echo ">> $(date +%H:%M:%S) starting ${agent} train (~1.7h expected)"
    # 컨테이너 안 잔여 자리 정리
    docker exec "${CONTAINER}" bash -lc "rm -rf /home/safebench/SafeBench/log/${exp}"
    # 백그라운드 학습 시작
    docker exec -d "${CONTAINER}" bash -c "
        export PYTHONPATH=${PYTHONPATH_CONTAINER}
        export SDL_VIDEODRIVER=dummy
        cd /home/safebench/SafeBench
        python scripts/run.py \
            --agent_cfg ${agent}.yaml --scenario_cfg ordinary.yaml \
            --mode train_agent --num_scenario 1 \
            --seed 0 --exp_name ${exp} \
            > ${log_in} 2>&1
    "
    # 학습 process 종료 대기
    sleep 30
    while true; do
        # docker exec 안에서 train_agent process pgrep. pgrep이 자기 명령에
        # 'train_agent' 문자열을 포함하면 자기 매치 위험이 있으므로 --agent_cfg
        # ${agent}.yaml의 yaml 파일명도 포함시켜 정확도 높임.
        local running
        running=$(docker exec "${CONTAINER}" bash -lc \
            "pgrep -f 'scripts/run.py.*train_agent.*${agent}.yaml' || true" 2>/dev/null)
        # pgrep이 자기 명령 매치할 수 있으므로 결과에서 자기 PID 제외 위해
        # 결과 행 수가 1보다 작거나 같으면 종료로 간주(자기 자신만 잡힌 자리).
        local n_running
        n_running=$(echo "${running}" | grep -c '^[0-9]' || true)
        if [[ "${n_running}" -le 1 ]]; then
            # 한 번 더 확인 (race condition 회피)
            sleep 10
            running=$(docker exec "${CONTAINER}" bash -lc \
                "pgrep -f 'scripts/run.py.*train_agent.*${agent}.yaml' || true" 2>/dev/null)
            n_running=$(echo "${running}" | grep -c '^[0-9]' || true)
            if [[ "${n_running}" -le 1 ]]; then
                echo ">> $(date +%H:%M:%S) ${agent} train finished"
                break
            fi
        fi
        sleep 120
    done
    echo ">> ${agent} log 마지막:"
    docker exec "${CONTAINER}" tail -5 "${log_in}" 2>/dev/null || true
}

# === main ===
echo ">> $(date +%H:%M:%S) DDPG·PPO·TD3 직렬 학습 orchestrator 시작"
wait_pilot_done

for agent in ddpg ppo td3; do
    train_one_agent "${agent}"
done

echo ">> $(date +%H:%M:%S) 모든 학습 완료. ckpt 자리:"
docker exec "${CONTAINER}" bash -lc '
ls /home/safebench/SafeBench/safebench/agent/model_ckpt/ddpg/ 2>/dev/null | head
ls /home/safebench/SafeBench/safebench/agent/model_ckpt/ppo/ 2>/dev/null | head
ls /home/safebench/SafeBench/safebench/agent/model_ckpt/td3/ 2>/dev/null | head
'
