# 리눅스(계산) 환경 전달용 지시서 — 격자 K=70 통일 재실행

작성 2026-06-14. 이 문서는 원고 작업 환경에서 내린 결정을 계산 환경(학습·시뮬레이션·분석)에 전달하기 위한 자족형 지시서다. 이 파일 하나로 무엇을 다시 돌리고 무엇을 보고하면 되는지 끝나도록 적었다.

## 결정 (왜 다시 돌리나)

기존 격자는 규칙 기반 응시자(IDM·MOBIL)만 cell당 K=20, 학습 응시자 18종은 K=70으로 반복 수가 달랐다. 이 때문에 분석이 "N=20·K=20 주 분석"과 "N=18·K=70 보조 분석" 두 갈래로 나뉘었는데, 이 갈래는 설계 원칙이 아니라 자료 수집 이력의 흔적이라 논문 본문에서 정당화하기 약하다. 그래서 **전 응시자 20종을 cell당 K=70으로 통일**하기로 확정했다. 통일하면 두 갈래·K 차이·N=20/N=18 구분이 모두 사라지고 단일 격자(N=20·K=70)가 된다.

규칙 기반을 K=70으로 올리는 것이 의미 있는지는 확인됨: 매 반복의 시드가 `seed = f(av_id, g_id, c, trial_k)`로 trial_k마다 달라져 같은 cell도 반복마다 다른 시나리오가 된다. 실제로 IDM은 cut-in c=0~4에서 충돌률이 0.65·0.80·0.55·0.65·0.40으로 흩어진다(결정론 controller여도 시드로 변동 발생). 따라서 K=70은 추정 충돌률의 신뢰구간을 좁혀줄 뿐 헛돌지 않는다.

## ⚠ 주의 (반드시 지킬 것)

`run_aaai_grid.py`의 `AV_DEFINITIONS`에는 응시자가 **22개** 등록돼 있고, 거기엔 격자에서 **제외하기로 한 양극단 두 시드 `def_rl_123`(전 cell 충돌 0%)·`def_rl_1024`(baseline 70%)**가 포함돼 있다. 따라서 `--av`를 생략한 전체 재실행을 하면 이 두 제외 시드가 섞여 N=22가 된다. **전체 재실행 금지.** 아래처럼 규칙 기반 둘만 K=70으로 돌리고, 이미 정확한 학습 18종 파일(`responses_av18_learned.jsonl`)과 합쳐 N=20을 만든다.

## Step 1 — 규칙 기반 둘만 K=70으로 재실행 후 병합

저장소 루트에서 실행(ACARL_ROOT = `/home/hyunchul/ASG/ASG_2026` 접근 가능해야 함):

```bash
# (1) IDM·MOBIL만 K=70 (2 av × 4 G × 5 c × 70 = 2,800 episode)
python3 analysis/highway_grid/run_aaai_grid.py --K 70 --av idm mobil \
  --out analysis/highway_grid/responses_rulebased_k70.jsonl

# (2) 학습 18종 K=70(기존, 정확) + 규칙 기반 K=70(신규) 병합 → N=20·K=70 단일 격자
cat analysis/highway_grid/responses_av18_learned.jsonl \
    analysis/highway_grid/responses_rulebased_k70.jsonl \
  > analysis/highway_grid/responses_av20_k70.jsonl

# (3) 확인: 28,000줄(20 av × 4 G × 5 c × 70), av 20종, 모든 cell K=70
wc -l analysis/highway_grid/responses_av20_k70.jsonl
python3 -c "import json,collections as C; \
c=C.Counter(); av=set(); \
[ (av.add(d['av_id']), c.update([(d['av_id'],d['g_id'],round(float(d['c'])))])) \
  for d in map(json.loads, open('analysis/highway_grid/responses_av20_k70.jsonl')) ]; \
print('av:', len(av), '| Kset:', set(c.values()))"
# 기대: av: 20 | Kset: {70}
```

병합 대안(전체를 한 번에 새로 돌리고 싶을 때): `--av`에 20종을 **명시적으로 나열**해서 `def_rl_123`·`def_rl_1024`를 빼야 한다. 비용이 28,000 episode로 크고 제외 시드 누락 위험이 있으니 위 증분 방식을 권장한다.

## Step 2 — fit·D1~D4 재산출 (모두 통일 파일을 `--jsonl`로)

기존 av20/av18 두 fit은 폐기하고 단일 fit 하나만 산출한다.

```bash
# fit_irt_main (θ̂·b̂·β̂·γ̂·â·û) — 단일 N=20·K=70
python3 analysis/highway_grid/fit_irt_main.py \
  --jsonl analysis/highway_grid/responses_av20_k70.jsonl \
  --out-prefix analysis/highway_grid/figures/irt_main_k70

# D1 단조성 + 순위 역전 sanity
python3 analysis/d-grid-validation/d1_figure.py \
  --jsonl analysis/highway_grid/responses_av20_k70.jsonl

# D2 trial-split (K=70을 35 vs 35로 분리; --pass-g에 D1 통과 G만 나열)
python3 analysis/highway_grid/d2_trial_split.py \
  --jsonl analysis/highway_grid/responses_av20_k70.jsonl \
  --pass-g <D1 통과 생성기 나열, 예: acarl_cutin acarl_rearend method_c>

# D3 ablation (no_severity·g_common·u_zero deviance)
python3 analysis/d-grid-validation/d3_figure.py \
  --jsonl analysis/highway_grid/responses_av20_k70.jsonl
```

참고: 통일 후 모든 cell이 K=70이므로 예전의 "최소 K=20으로 자르는" 처리가 불필요하고, D2 trial-split도 응시자 20종 전부에 적용된다(예전엔 K=70인 18종만 가능했음).

## Step 3 — 원고 환경에 보고할 수치

아래만 정리해 원고 환경으로 회신하면 §5와 figure를 갱신한다.

1. **D1 단조성**: 생성기 4종(acarl_cutin·acarl_rearend·method_b·method_c)별 Spearman ρ와 합격(ρ≥0.7) 여부. 순위 역전 sanity의 ρ mean·p25.
2. **D2 trial-split**: r mean·p25 (전체 4 G, 그리고 단조성 통과 G 부분집합).
3. **D3 ablation**: deviance Δ — no_severity(df=4)·g_common(df=12)·u_zero(df=4).
4. **fit_irt_main**: 응시자 20종 θ̂과 95% CI(half-width), 생성기 4종 β̂·γ̂·â·û, converged 여부. (단일 fit 하나, av18/av20 구분 없음.)
5. 변경 사실 한 줄: 본 결과가 기존 N=20·K=20 및 N=18·K=70 수치를 대체함.

## 영향 (원고 환경 쪽 작업 — 참고)

- 기존 brief의 N=20/N=18 구분·K 통합(20→50→70) 서술은 폐기. §4.2·§4.5는 "스무 종을 각 cell에서 70회 평가" 한 줄로 단순화.
- §5 수치와 figure 5종(irt_main·d1·d2·d3)은 본 재산출 결과로 교체.
- 응시자 20종 구성은 그대로(규칙 기반 IDM·MOBIL + Defensive RL 3 + PPO 5 + SAC 5 + TD3 5), def_rl_123·1024 제외 유지.
