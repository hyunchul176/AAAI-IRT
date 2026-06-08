# 검토 결과 · 리눅스 환경에서 확인·수정할 목록

> **시점 표시 (2026-06-07 라운드 19 추가)**: 본 문서는 2026-06-06 라운드 18 시점의 검토 자료다. 본 검토에서 잡은 일부 항목(A-1 SE 부풀림·B-1 u_zero deviance 음수)은 라운드 19 N=20 확장으로 자동 해소되었다. **현재 본 프로젝트의 최신 상태는 `paper_data.md` §5와 `decisions.html` 라운드 19 단락 기준이며, 본 REVIEW_FIXLIST는 정정 이력 reference로만 보존된다.** 새 검토 시 본 문서의 옛 수치를 그대로 활용하지 않는다.
>
> 작성: 2026-06-06. AAAI SUT-불변 측정 프로젝트의 분석·통계 정합성, 측정 모델 형식화,
> 본문 주장 대 데이터 정합성을 교차검증한 결과다. 본 파일 하나만 들고 가면 원 작업 환경에서
> 각 항목을 그대로 확인·수정할 수 있도록 위치·증거·재현 명령·수정안을 함께 적었다.
> 파일 경로는 모두 저장소 root(`AAAI/`) 기준 상대경로다.

---

## 먼저: 재현되어 손댈 필요 없는 부분

아래는 실제 데이터에서 정확히 재현되었다. 수정 대상이 아니다.

- D1 단조성 Spearman ρ: cut-in +0.821, rear-end +0.700, method_b +0.700, method_c −0.821
- D2 trial-split: 전체 4 G r mean 0.939 / p25 0.925, 단조성 통과 3 G r mean 0.917 / p25 0.895
- D3 LR 값(크기): no_severity 2552.53, g_common 482.16
- fit_irt_main 점추정값 θ̂·β̂·γ̂·â·û 및 b̂ 매트릭스 전부 `irt_main.json`과 일치
- 본문의 배수 표현: γ̂ 3.6배, Method B â 약 1/25, Method C γ̂ 1/2~1/8 모두 산술 일치

---

## A. 틀린 부분 (수정 필요)

### A-1. θ̂ 표준오차·신뢰구간이 약 2.6~4.2배 부풀려져 있다 (최우선)

- **위치**: `analysis/d-study/d_study.py`의 `fit_map`, 표준오차 산출부(약 172~178행). 영향받는 보고: `paper_data.md` §5.5·§6.3, `research/method.html` 운영 한계 박스, `irt_main.json`의 `se_theta`.
- **증상**: 표준오차를 `scipy` L-BFGS-B의 `res.hess_inv`(제한메모리 근사 역헤시안)에서 가져온다. 이 양은 공분산 추정에 신뢰할 수 없다고 알려져 있어, 보고된 95% CI가 실제보다 크게 넓다.
- **증거 (같은 최적점에서 수치 헤시안으로 재계산)**:

  | 응시자 | 보고된 95% CI half (코드) | 정확한 헤시안 기반 | 비율 |
  |--------|------|------|------|
  | def_rl_42 | ±1.808 | ±0.689 | 2.62× |
  | def_rl_456 | ±1.870 | ±0.674 | 2.77× |
  | def_rl_789 | ±3.776 | ±0.891 | 4.24× |

- **함의**: 본문은 이 넓은 CI를 "응시자 N=3의 작은 표본 효과"로 적었으나, 실제로는 표준오차 계산 방식의 수치 흠이 더 크게 작용했다. 정확한 헤시안을 쓰면 def_rl_789(+1.406 ± 0.89)가 음의 두 응시자와 분명히 분리되어 순위 주장이 강해진다. 즉 이 수정은 결과를 약화시키지 않고 강화한다.
- **수정안**: `fit_map`에서 `res.hess_inv` 대신 최적점의 수치 헤시안 역행렬로 표준오차를 산출한다. 예: `numdifftools.Hessian(neg_logpost)(res.x)`를 구해 `cov = inv(H)`, `se = sqrt(diag(cov)[:n_av])`. 이후 `irt_main.json`·`irt_main.png`·본문 CI 표를 모두 재산출.
- **추가 점검**: 표준화 변환(`se_theta = se_raw / s`)이 야코비안을 무시하므로, 헤시안을 표준화 후 좌표에서 직접 구하거나 delta method로 보정하면 더 정확하다(A-6 참조).

### A-2. paper_data.md §3.1 식 (1)의 부호가 method.html·코드와 반대다

- **위치**: `paper_data.md` §3.1, 식 (1) (약 113행).
- **증상**: 본문 raw 자료가 `P = u_G + (1−u_G)·σ(a_G·(θ_π − b(G,c)))`로 적혀 있다(θ−b). 그러나 `research/method.html` 식 (6)과 `d_study.py`의 적합 코드(`eta = a*(beta + gamma*c − theta)`)는 모두 `σ(a_G·(b(G,c) − θ_π))`(b−θ)를 쓴다.
- **함의**: 본문 형태대로면 강건성 θ가 클수록 충돌 확률이 올라가, 같은 단락의 "θ_π: 음수 = 약함" 정의와 정면으로 충돌한다. 이 파일에서 본문을 쓰면 그대로 옮겨붙을 오류다.
- **수정안**: §3.1 식 (1)을 `σ(a_G·(b(G,c) − θ_π))`로 바로잡는다(method.html·코드 기준).

### A-3. 총 episode 수 7,000은 실제 격자와 맞지 않는다

- **위치**: `paper_data.md` §0(12행), §1.4(55행), §4.5(207행) 등 "AV=5 × G=4 × c=5 × K=70 = 7,000 episode" 서술.
- **증상**: 실제 통합 파일은 5,000 episode다. IDM·MOBIL은 K=20(각 400), Defensive RL 세 시드만 K=70(각 1,400)으로 수집되었고, fit_irt_main이 쓰는 자료는 def_rl 세 시드의 4,200 episode다.
- **증거**: `responses_av5_combined.jsonl` 5,000줄(idm 400·mobil 400·def_rl 각 1400), `responses_def_rl_combined.jsonl` 4,200줄.
- **함의**: "5종 × K=70 = 7,000"은 다섯 응시자 전부 K=70일 때만 성립하므로 산술적으로도 내부 모순이다.
- **수정안**: "Defensive RL 3시드 K=70 + IDM·MOBIL K=20, IRT 적합은 def_rl 4,200 episode"로 정확히 적는다. 전체 격자 규모를 한 숫자로 쓰려면 5,000(통합)과 4,200(적합 사용분)을 구분해 명시.

### A-4. D3 g_common의 자유도 9는 코드 동작과 맞지 않는다

- **위치**: `paper_data.md` §5.4(256행). 관련 코드 `analysis/d-grid-validation/d3_ablation.py`의 `_resp_g_common`.
- **증상**: 본문은 g_common을 "a_G, u_G가 모든 G에서 동일(df=9)"로 적었다. 그러나 `_resp_g_common`은 G를 전부 0으로 모아 n_g=1로 적합하므로 β·γ·a·u 네 모수가 각각 4→1로 줄어 실제 자유도는 **12**다. 본문 말 설명(a·u만 공통)대로면 6이고, 어느 쪽도 9가 아니다.
- **참고**: no_severity의 df=4(γ 4개 무력화)는 맞다. LR 값 482.16 자체도 재현된다.
- **수정안**: g_common의 자유도를 코드 동작(β·γ·a·u 공통, df=12)에 맞추고, 말 설명도 "G별 모든 모수를 하나로 통합"으로 고친다. p값은 LR이 워낙 커서 결론(강한 유의)은 불변.

---

## B. 정합성 약점 (틀린 건 아니나 reviewer가 짚을 곳)

### B-1. D3의 "LR test"는 엄밀한 nested likelihood ratio test가 아니다

- **위치**: `analysis/d-grid-validation/d3_ablation.py`, `run_d3` / `neg_loglik_orig`. 보고: `paper_data.md` §5.4.
- **증상**: 변종을 prior가 붙은 MAP로 적합한 뒤 prior를 뺀 likelihood로 비교하고, no_severity·g_common은 변형된 데이터로 적합한다. 그 결과 본문에 보고하지 않은 **u_zero 변종은 LR = −18.04로 음수**가 나온다. 정상적인 nested LRT에서 LR은 음수가 될 수 없으므로, 이 프레임이 순수 LRT가 아님이 드러난다.
- **수정안**: (i) 변종을 ML(prior off)로 다시 적합해 정식 LRT로 만들거나, (ii) χ²·p값 표현을 낮춰 "deviance 비교" 또는 "예측 적합 비교"로 서술. no_severity·g_common의 큰 LR로 인해 결론은 유지되므로 표현 정정 위주.

### B-2. 사후 표준화가 N(0,1) prior와 이중으로 식별을 건다

- **위치**: `analysis/d-study/d_study.py`의 `fit_map`(약 167~171행).
- **증상**: θ에 N(0,1) prior를 주고도 적합 후 `θ=(θ−mean)/std`로 표본 평균 0·표준편차 1을 다시 강제한다. 응시자 3명의 표본 표준편차로 나누는 연산이라 척도가 인위적으로 고정된다.
- **함의**: eta는 보존되어 점추정 해석은 유지되나, 불확실성 정량화 근거가 약하다. A-1 수정과 함께 다룰 것.
- **수정안**: prior로 척도를 고정했으면 사후 하드 표준화를 제거하거나, 표준화 좌표에서 헤시안을 직접 구해 SE를 일관되게 산출.

### B-3. cut-in·rear-end의 â≈14.3은 사실상 계단함수다

- **위치**: `irt_main.json`의 `a_hat`. cut-in 14.297, rear-end 14.254.
- **증상**: 변별력이 14를 넘으면 ICC가 거의 step이 되어, 변별력 모수가 경계에 붙은 신호다. severity 기울기 γ가 작은 점(0.054)과 겹치면 이 두 생성기에서 충돌이 θ에 거의 임계적으로 갈린다.
- **수정안**: 적합 품질·식별성을 한 줄로 점검(예: a에 더 강한 사전정보, 또는 a 상한 점검)하고, 본문에 이 거동을 짧게 명시.

### B-4. 회피불가 하한 u를 자유 추정했다 (확정 사양과 어긋남)

- **위치**: `analysis/highway_grid/fit_irt_main.py`의 `fit_map(... fix_u=None ...)`. 확정 사양: `research/method.html` 확정 사양 2번. 본문: `paper_data.md` §3.1.
- **증상**: method.html은 u를 "데이터만으로 자유 추정하지 않고 RSS·귀책 라벨로 고정하거나 강한 사전정보로 준다"로 정했는데, 실제 적합은 `fix_u=None`으로 logit zu~N(−2,2) prior만 두고 자유 추정한다. paper_data.md §3.1은 "u_G ∈ [0,1] 강제"로만 적어 자유 추정 사실이 드러나지 않는다.
- **수정안**: 본문에 "u는 logit 약사전정보 하에 자유 추정"임을 한 줄 명시하거나, RSS 라벨 고정 방식으로 바꿔 사양과 일치시킨다.

---

## C. 재현 명령 (원 환경에서 그대로 실행)

저장소 root에서 실행. 의존성: numpy, scipy, matplotlib, numdifftools(SE 교차검증용).

```bash
# A-1 fit 재현 (점추정값 → irt_main.json과 일치 확인)
python3 analysis/highway_grid/fit_irt_main.py \
    --jsonl analysis/highway_grid/responses_def_rl_combined.jsonl \
    --out-prefix /tmp/irt_repro

# D2 trial-split 재현 (0.939/0.925, 0.917/0.895)
python3 analysis/highway_grid/d2_trial_split.py \
    --jsonl analysis/highway_grid/responses_def_rl_combined.jsonl

# D3 ablation 재현 (no_severity 2552.53, g_common 482.16, u_zero −18.04)
python3 analysis/d-grid-validation/d3_ablation.py \
    analysis/highway_grid/responses_def_rl_combined.jsonl
```

A-1의 표준오차 교차검증(수치 헤시안 대 L-BFGS-B)은 `fit_map` 호출 후 최적점 `res.x`에서
`numdifftools.Hessian(neg_logpost)(res.x)`를 구해 역행렬 대각의 제곱근을 비교하면 된다.

---

## D. 우선순위 요약

1. **A-1 (표준오차)**: 결과를 강화하는 방향. 가장 먼저.
2. **A-2 (식 (1) 부호)**: 본문 작성 전 반드시.
3. **A-3 (episode 수)**: 사실 오류, 전체 본문에 반복 등장.
4. **A-4 (g_common df)**: 수치 표 정정.
5. B-1~B-4: 표현·서술 정정 및 식별성 점검 (결론 불변, reviewer 방어용).
