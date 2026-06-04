#!/bin/bash
# DDPG·PPO·TD3 직렬 학습 orchestrator (라운드 12 후속, pgrep 자기 매치 정정)
#
# pilot v2 orchestrator의 pgrep 자기 매치 bug를 host pgrep으로 진단 후, 이
# 스크립트는 docker exec 안 pgrep만 쓴다. host docker exec 명령 라인은
# 컨테이너 안 process가 아니라 컨테이너 pgrep에 매치되지 않으므로 안전.
#
# 각 학습 train_episode=2000, 셀당 ~10초, ETA ~5.5h × 3 = ~16h.
# pilot v2가 이미 끝났다는 전제로 곧장 학습 진행 (DDPG는 이미 직접 시작된
# 자리이므로 polling 후 PPO·TD3 직렬).
#
# usage:
#   nohup bash analysis/b4-pipeline/train_agents_serial.sh > \
#       analysis/b4-pipeline/train_agents_serial.log 2>&1 &

set -uo pipefail

CONTAINER=sb-pilot
PYTHONPATH_CONTAINER='/home/safebench/carla/PythonAPI/carla/dist/carla-0.9.13-py3.8-linux-x86_64.egg:/home/safebench/carla/PythonAPI/carla/agents:/home/safebench/carla/PythonAPI/carla:/home/safebench/carla/PythonAPI'

wait_agent_done() {
    local agent="$1"
    echo ">> $(date +%H:%M:%S) waiting for ${agent} train to finish..."
    sleep 120
    while true; do
        local running
        running=$(docker exec "${CONTAINER}" bash -lc \
            "pgrep -f 'scripts/run.py.*${agent}.yaml' || true" 2>/dev/null \
            | grep -cE '^[0-9]+$' || true)
        if [[ "${running}" -eq 0 ]]; then
            echo ">> $(date +%H:%M:%S) ${agent} train finished"
            break
        fi
        sleep 120
    done
    docker exec "${CONTAINER}" tail -5 "/tmp/train_${agent}.log" 2>/dev/null || true
}

start_agent() {
    local agent="$1"
    local exp="train_${agent}_seed0"
    echo ">> $(date +%H:%M:%S) starting ${agent} train"
    docker exec "${CONTAINER}" bash -lc "rm -rf /home/safebench/SafeBench/log/${exp}"
    docker exec -d "${CONTAINER}" bash -c "
        export PYTHONPATH=${PYTHONPATH_CONTAINER}
        export SDL_VIDEODRIVER=dummy
        cd /home/safebench/SafeBench
        python scripts/run.py \
            --agent_cfg ${agent}.yaml --scenario_cfg ordinary.yaml \
            --mode train_agent --num_scenario 1 \
            --seed 0 --exp_name ${exp} \
            > /tmp/train_${agent}.log 2>&1
    "
    sleep 30
}

# === main ===
echo ">> $(date +%H:%M:%S) DDPG·PPO·TD3 직렬 학습 orchestrator 시작 (v2)"

# DDPG는 이미 직접 시작된 자리. polling만.
wait_agent_done ddpg

# 라운드 14 권고: DDPG 학습 후 (sac, lc) c=0 K=30 재pilot으로 LC 다이얼 신호 vs
# 잡음 진단. 5분 작업이라 PPO 시작 전 끼움.
echo ">> $(date +%H:%M:%S) DDPG 후 (sac, lc) c=0 K=30 재pilot 시작"
cd /home/hyunchul/AAAI && python3 analysis/b4-pipeline/pilot_recheck_lc_c0.py \
    --container "${CONTAINER}" > analysis/b4-pipeline/pilot_recheck.log 2>&1 || true
echo ">> $(date +%H:%M:%S) 재pilot 완료. log: analysis/b4-pipeline/pilot_recheck.log"

start_agent ppo
wait_agent_done ppo

start_agent td3
wait_agent_done td3

echo ">> $(date +%H:%M:%S) 모든 학습 완료. ckpt 자리:"
docker exec "${CONTAINER}" bash -lc '
for a in ddpg ppo td3; do
  echo "=== $a ==="
  ls /home/safebench/SafeBench/safebench/agent/model_ckpt/${a}/ 2>/dev/null | head -3
done'
