#!/bin/bash
# SafeBench 적대 생성기 직렬 학습 orchestrator
#
# LC 학습이 진행 중이면 완료 대기 후 NF 학습을 자동 시작한다. AdvSim·AdvTraj는
# HardCodePolicy(type='unlearnable')라 mode=train_scenario로 학습이 작동하지
# 않고 parameters JSON 생성 절차도 SafeBench README·docs 어디에도 없으므로
# 우리 격자에서 사용 불가(decisions.html #d07 라운드 10 갱신 참조).
#
# 학습 한 종당 ~1.5h, 둘 직렬 = ~3h. CARLA 인스턴스 한 자리(port 2000)를 공유
# 하므로 동시 학습은 못 한다.
#
# 학습 완료 감지: SafeBench가 마지막에 "Saving training results" + "Saving
# scenario policy {name} model" 메시지를 출력하고 process가 자연 종료된다.
# bash가 process 종료를 polling하는 가장 단순한 길로 둔다.
#
# usage:
#   bash analysis/b4-pipeline/train_safebench_serial.sh

set -euo pipefail

CONTAINER=sb-pilot
PYTHONPATH_CONTAINER='/home/safebench/carla/PythonAPI/carla/dist/carla-0.9.13-py3.8-linux-x86_64.egg:/home/safebench/carla/PythonAPI/carla/agents:/home/safebench/carla/PythonAPI/carla:/home/safebench/carla/PythonAPI'

wait_for_train() {
    local name="$1"
    local log="/tmp/train_${name}.log"
    echo ">> waiting for ${name} train to finish..."
    while true; do
        # SafeBench scripts/run.py가 살아 있나
        local running
        running=$(docker exec "${CONTAINER}" bash -lc "pgrep -f 'scripts/run.py.*train_scenario.*${name^^}' || pgrep -f 'scripts/run.py.*train_scenario.*${name}' || true")
        if [[ -z "${running}" ]]; then
            echo ">> ${name} train process not found (finished or never started)"
            break
        fi
        sleep 60
    done
    # 마지막 log tail
    echo ">> ${name} train last log:"
    docker exec "${CONTAINER}" bash -lc "tail -10 ${log}" || true
}

start_train() {
    local name="$1"          # lc | nf
    local scenario_cfg="$2"  # LC.yaml | nf.yaml
    local exp="train_${name}_seed0"
    local log="/tmp/train_${name}.log"
    echo ">> starting ${name} train (background)"
    docker exec "${CONTAINER}" bash -lc "rm -rf /home/safebench/SafeBench/log/${exp}"
    docker exec -d "${CONTAINER}" bash -c "
        export PYTHONPATH=${PYTHONPATH_CONTAINER}
        export SDL_VIDEODRIVER=dummy
        cd /home/safebench/SafeBench
        python scripts/run.py \
            --agent_cfg sac.yaml --scenario_cfg ${scenario_cfg} \
            --mode train_scenario --num_scenario 1 \
            --seed 0 --exp_name ${exp} \
            > ${log} 2>&1
    "
    sleep 30
    echo ">> ${name} train started, first 6 lines of log:"
    docker exec "${CONTAINER}" bash -lc "head -20 ${log} | tail -6" || true
}

# === main ===
echo ">> SafeBench 직렬 학습 orchestrator (LC → NF)"

# 1단계: LC 학습 (이미 진행 중이면 그대로 대기, 안 돌고 있으면 시작)
LC_RUNNING=$(docker exec "${CONTAINER}" bash -lc "pgrep -f 'scripts/run.py.*train_scenario.*LC' || true")
if [[ -z "${LC_RUNNING}" ]]; then
    start_train lc LC.yaml
else
    echo ">> LC train already running, skip start"
fi
wait_for_train lc

# 2단계: NF 학습 (LC 완료 후)
start_train nf nf.yaml
wait_for_train nf

echo ">> all done. ckpt 자리:"
docker exec "${CONTAINER}" bash -lc 'ls -la /home/safebench/SafeBench/safebench/scenario/scenario_data/model_ckpt/lc/ /home/safebench/SafeBench/safebench/scenario/scenario_data/model_ckpt/nf/ 2>/dev/null'
