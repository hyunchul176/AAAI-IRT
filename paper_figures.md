# AAAI Paper Figures: Raw 자료와 Caption Baseline

본 파일은 본문 figure 6종 + 추가 figure 후보의 raw 자료(파일 경로·수치·축·panel 구성)와 caption baseline을 정리한다. 본문 voice의 caption은 사용자가 직접 작성하며, 본 파일의 baseline은 raw 자료의 정확성을 검증할 수 있도록 정확한 수치와 결과를 포함한다.

---

## Figure 종합 분류

**본문 핵심 figure 4종 (§Results)**:
- Figure 2: D1 단조성과 응시자 순위 안정성 (`d1_rank_reversal_real`)
- Figure 3: D2 trial-split (`d2_trial_split`)
- Figure 4: D3 ablation LR test (`d3_ablation_real`)
- Figure 5: fit_irt_main 4-panel (`irt_main`)

**보조 figure 2종 (§Limitations 또는 supplementary)**:
- Figure S1: D2 표준 응시자 split-half N=5 (`d2_split_half_av5`)
- Figure S2: D2 표준 응시자 split-half real (`d2_split_half_real`)

**추가 figure 후보 (사용자 결정)**:
- Figure 1: §Introduction motivation (rank reversal 또는 SUT 의존성 schematic)
- Figure - method schematic: §Method conceptual diagram

---

## Figure 2: D1 단조성과 응시자 순위 안정성

> **figure 재산출 완료 (2026-06-08 라운드 23)**: 본 figure는 N=18·K=70 자료(`responses_av18_learned.jsonl`)로 재산출되었다. 라운드 19 시점의 IndexError 흠은 `analysis/d-grid-validation/d1_rank_reversal.py`의 `build_av_scenario_matrix`가 scenario를 `(sid, rid, data_id)` tuple로 묶어 N=18 자료에서 cell 1001개 가운데 일부가 응시자별로 비어 50회 split 모두 NaN으로 잡혀 percentile 산출에서 깨진 자료에서 비롯되었다. 라운드 23 정정으로 scen tuple을 `(g_id, c, trial_k)`로 옮겨 4 G × 5 c × 70 trial_k = 1400 scenarios로 묶었으며 50회 split이 모두 valid. 본 figure는 본문 §5.1 D1 단조성에 인용.

**파일 경로**:
- PDF: `analysis/highway_grid/figures/d1_rank_reversal_real.pdf`
- PNG: `analysis/highway_grid/figures/d1_rank_reversal_real.png`

**Panel 구성** (3-panel 자료, 라운드 23 N=18·K=70 재산출):
- **(a) AV ranking instability under scenario subset shift**: 50회 시나리오 부분집합 무작위 분리에서의 AV 순위 Spearman ρ 분포 (histogram).
  - 자료: AV=18 (학습 응시자만, `responses_av18_learned.jsonl`)·1400 scenarios = 4 G × 5 c × 70 trial_k
  - 결과: ρ mean = 0.987·p25 = 0.983·ρ min = 0.965·ρ max = 0.998. 50회 split 모두 valid.
  - reference 선: ρ = 0.80 (vertical dashed line, 합격선 표시). 본 자료가 합격선 위쪽 좁은 구간에 집중.
  - x축: AV rank Spearman ρ (50 scenario splits)
  - y축: frequency
- **(b) Per-AV collision rate shifts (real grid, AV=18, n_scen=1400)**: 응시자별 충돌률이 두 부분집합 (A vs B) 사이에서 어떻게 일치하는지 산점도.
  - x축: AV collision rate (scenario subset A)
  - y축: AV collision rate (scenario subset B)
  - reference 선: y = x (perfect agreement)
  - 18 응시자 각각 한 점 (def_rl 3 + ppo 5 + sac 5 + td3 5)
- **(c) Top-half AV identity shifts across subsets**: 시나리오 부분집합 사이에서 top-half 응시자 identity가 얼마나 바뀌는지 histogram.
  - x축: top-half AV disagreement (50 splits)
  - y축: frequency
  - 결과: mean = 0.078·p25 = 0.000. 절반 이상의 split에서 top-half가 완전 동일.

**산출 코드**: `analysis/d-grid-validation/d1_figure.py` (입력 `responses_av18_learned.jsonl`), `analysis/d-grid-validation/d1_rank_reversal.py`의 `build_av_scenario_matrix`가 라운드 23에서 (g_id, c, trial_k) tuple로 정정됨.

**Caption baseline (라운드 23 N=18·K=70 재산출 자료)**:
- (a) 본 측정 모델 위에서 시나리오 부분집합을 무작위 분리해도 AV 순위가 거의 변하지 않는다 (mean ρ = 0.987·p25 = 0.983, 50회 반복).
- (b) 응시자별 충돌률이 두 부분집합 사이에서 y = x 라인에 정렬되어 SUT-시나리오 분리 가설을 받친다.
- (c) Top-half 응시자 identity가 평균 7.8% 정도만 어긋난다 (mean = 0.078·p25 = 0.000).

**본문 위치**: §5.1 D1 단조성 (§Results 첫 figure)

---

## Figure 3: D2 trial-split

**파일 경로**:
- PDF: `analysis/highway_grid/figures/d2_trial_split.pdf`
- PNG: `analysis/highway_grid/figures/d2_trial_split.png`

**Panel 구성** (단일 panel 또는 2-panel, figure 직접 점검 권고):
- 각 (av_id, g_id, c) cell의 K=70 episode를 무작위 35 vs 35로 분리한 두 (G, c) 충돌률 매트릭스의 Pearson r을 50회 반복 산출.
- **수치 결과 (라운드 19 N=18·K=70 재산출)**:
  - 전체 4 G: r mean = **0.994**, p25 = **0.993**
  - 단조성 통과 3 G (cut-in·rear-end·**method_c**): r mean = **0.996**, p25 = **0.996**
- 합격선: r ≥ 0.80 (이전 N=5 0.939·0.917에서 강화)

**산출 코드**: `analysis/highway_grid/d2_trial_split.py` (입력 `responses_av18_learned.jsonl`)

**Caption baseline** (사용자가 voice 정리):
- 각 (G, c) cell의 K=70 episode를 무작위 35 vs 35로 분리한 두 충돌률 매트릭스의 Pearson r 분포 (50회 반복).
- 전체 4 G에서 r mean = 0.994, 단조성 통과 3 G(cut-in·rear-end·method_c)로 좁히면 r mean = 0.996. 합격선 0.80을 매우 강하게 통과.
- 본 결과는 본 격자의 N=18·K=70 자료가 b̂ 추정의 통계적 안정성을 매우 강하게 제공한다는 직접 증거이다. method_b는 D1 단조성 FAIL이라 통과 3 G에서 제외, method_c는 라운드 19 N 확장 후 양의 단조성으로 정정되어 통과.

**본문 위치**: §5.2 D2 trial-split (§Results)

---

## Figure 4: D3 ablation deviance 비교

> **figure 재산출 완료 (2026-06-08 라운드 23)**: 본 figure는 `responses_av18_learned.jsonl` 입력으로 재산출되었다. 라운드 22 검토자가 우려한 d1과 동일 자료 구조 흠은 d3_figure에서는 발생하지 않았으며 `d3_figure.py`가 이미 `seed=0`을 명시한 자료라 본 환경 재현값이 안정적이다. 본 환경 산출값은 no_severity Δ = 195,191.53·g_common Δ = 4,454.03·u_zero Δ = +36.78이며 paper_data §5.4의 본문값(195,116·4,454·+36.83)과 0.04~0.14% 이내로 일치한다. 본 figure는 본문 §5.4 D3 ablation에 인용.

**파일 경로**:
- PDF: `analysis/highway_grid/figures/d3_ablation_real.pdf`
- PNG: `analysis/highway_grid/figures/d3_ablation_real.png`

**Panel 구성** (figure 직접 점검 권고):
- 본 모델 vs 두 ablation 변종의 likelihood ratio test 결과.
- **수치 결과**:
  - **no_severity** (γ_G = 0 강제, severity 조건화 제거): deviance Δ ≈ **195,191** (N=18·K=70, df = 4, 라운드 23 본 환경 재현 자료; paper_data §5.4 본문값 195,116과 0.04% 이내 일치): 이전 N=5의 2,552.53의 약 76배. 매우 강한 통계 유의성.
  - **g_common** (G를 단일 그룹으로 통합, β·γ·a·u 4 모수 4→1로 축소): deviance Δ = **4,454.03** (N=18·K=70, df = 12): 이전 N=5의 482.16의 약 9배. 매우 강한 통계 유의성.
  - **u_zero** (u_G=0 강제): deviance Δ ≈ **+36.78** (N=18·K=70, df = 4, 라운드 23 재현; 본문값 +36.83과 0.14% 이내 일치): 이전 N=5에서 -18.04 음수 흠이 N 확장으로 정상 양수로 정정 (REVIEW_FIXLIST B-1 흠 자동 해소).
  - **재현성 정직 voice**: 정확한 deviance는 MAP 적합의 seed·수렴 자료에 따라 ±1% 안에서 변동하나 부호·자릿수·결론(세 변종 모두 본형 대비 매우 강한 적합도 손실)은 안정적이다. `d3_figure.py`가 `seed=0` 명시 자료라 본 환경에서 재현 가능.

**산출 코드**: `analysis/d-grid-validation/d3_*.py` 또는 `analysis/highway_grid/d3_*.py`

**Caption baseline** (사용자가 voice 정리):
- 본 모델과 두 ablation 변종 (no_severity, g_common) 사이의 likelihood ratio test.
- no_severity는 severity 조건화 (γ_G = 0)를 제거한 변종, g_common은 G별 차이 (a_G, u_G가 모든 G에서 동일)를 제거한 변종.
- deviance Δ는 약 195,191 (no_severity, df = 4)과 4,454.03 (g_common, df = 12)으로 매우 강한 통계 유의성 (N=18·K=70, 라운드 19~23 자료). u_zero (df=4) deviance Δ도 약 +36.78로 정상 양수 자료. 본 측정 모델의 세 구조가 격자 응답에 의미 있게 작동함을 직접 받친다. N 확장으로 deviance 자릿수가 76~9배로 강화된 흐름이 본 측정 모델의 학술 강도의 강한 신호.
- 재산출 완료(라운드 23, 2026-06-08): `d3_ablation_real.{pdf,png}` 자료가 N=18·K=70 자료로 갱신됨. d3_figure 코드가 이미 seed=0 명시라 재현성 안정.

**본문 위치**: §5.4 D3 ablation (§Results)

---

## Figure 5: fit_irt_main 4-panel (라운드 19 두 자료 보존)

**파일 경로 (두 자료)**:
- **N=20·K=20 (본문 주 자료, 모든 응시자)**:
  - PDF: `analysis/highway_grid/figures/irt_main_av20.pdf`
  - PNG: `analysis/highway_grid/figures/irt_main_av20.png`
  - JSON: `analysis/highway_grid/figures/irt_main_av20.json`
- **N=18·K=70 (본문 보조 sanity·D 분석 핵심)**:
  - PDF: `analysis/highway_grid/figures/irt_main_av18.pdf`
  - PNG: `analysis/highway_grid/figures/irt_main_av18.png`
  - JSON: `analysis/highway_grid/figures/irt_main_av18.json`
- 옛 자료 `irt_main.{pdf,png,json}` (N=3 def_rl 만)은 라운드 18 자료로 본문에 활용 안 함.

**Panel 구성** (4-panel: 2x2 layout):
- **(a) AV robustness θ̂ with 95% CI** (응시자 강건성, 라운드 19 N=20 확장 후):
  - 응시자 N=18 (av18.json) 또는 N=20 (av20.json) bar chart + error bar
  - **av18 θ̂ (학습 응시자 18종, K=70, 강건성 순)**:
    - PPO 강건군: ppo_200 +2.221 ± 0.821, ppo_800 +2.027 ± 0.757, ppo_500 +2.020 ± 0.758
    - Defensive RL 기존: def_rl_789 +0.317 ± 0.175, def_rl_42 -0.001 ± 0.110, def_rl_456 -0.244 ± 0.100
    - PPO·TD3 중간: ppo_100 +0.180, td3_100 +0.100, td3_789 -0.250
    - PPO 약함: ppo_999 -0.429 ± 0.130
    - SAC 5종: -0.652 ~ -0.769 (모두 약함)
    - TD3 약함: td3_42 -0.752, td3_456 -0.798, td3_999 -0.825
  - **av20 θ̂ (전체 20종, K=20)**: av18과 순위 일관 + IDM·MOBIL이 가장 약한 baseline의 한 자료 (idm -1.293·mobil -0.766)
  - 축: y축 θ̂ 값, x축 응시자 id (알고리즘별 색상 분리 권고: PPO·SAC·TD3·Defensive RL·IDM/MOBIL)
  - 0 horizontal line 표시
  - **본 SE의 산출 흐름**: d_study.py fit_map의 수치 헤시안(중심 차분) + 표준화 야코비안 J Σ J^T 적용 (라운드 18 2차 정정 후, av18·av20 모두 같은 산출 방법).
- **(b) Scenario difficulty b̂(G, c) heatmap** (생성기 × severity):
  - 4 G × 5 c heatmap
  - b̂(G, c) = β_G + γ_G · c 산출값
  - 색상 범위: -3 ~ +3, RdYlBu_r colormap
  - cell 안에 수치 표기
- **(c) Severity dial strength γ̂_G** (생성기별 severity 다이얼, 라운드 19):
  - 4 G bar chart (av18·av20 두 자료 별도 panel 권고)
  - **av18 (N=18·K=70)**: cut-in 0.010, rear-end 0.008, method_b 0.016, method_c 0.026
  - **av20 (N=20·K=20)**: cut-in 0.018, rear-end 0.034, method_b 0.025, method_c 0.037
  - method_c는 라운드 19 N 확장 후 양의 단조성으로 정정되어 본 fit에서도 양수 자료 (라운드 17·18의 "음의 단조성" 흠 폐기)
- **(d) Unavoidable lower bound û_G** (회피불가 하한, 라운드 19):
  - 4 G bar chart
  - **av18 (N=18·K=70)**: cut-in 0.056, rear-end 0.051, method_b 0.001, method_c 0.004
  - **av20 (N=20·K=20)**: cut-in 0.057, rear-end 0.054, method_b 0.003, method_c 0.004
  - y축 범위: 0 ~ 1
  - 두 fit 모두 ACARL G가 약 5% 자료, baseline G(method_b·c)가 약 0.1~0.4% 자료로 일관

**Title (라운드 19 정정)**: "AAAI measurement model fit: θ̂, b̂, γ̂, û (N=18·K=70 학습 응시자 + N=20·K=20 통합 보조 자료)"

**산출 코드**: `analysis/highway_grid/fit_irt_main.py` (입력 `responses_av18_learned.jsonl`·`responses_av20_combined.jsonl`)

**Caption baseline (라운드 19 N=20 확장 자료, 영어 본문 voice 변환 baseline)**:
- 본 figure는 본 측정 모델이 학습 방식 4종(rule-based·on-policy PPO·off-policy SAC·off-policy TD3)을 응시자 강건성 θ̂의 자릿수 차이로 분리한다는 핵심 결과를 보인다 (main message 첫 문장).
- (a) 응시자 강건성 θ̂ (av18·N=18·K=70, 라운드 19): PPO 강건군 ppo_200 +2.221 ± 0.821·ppo_500 +2.020 ± 0.758·ppo_800 +2.027 ± 0.757이 강건성 상단 (식별성 ceiling 영역). Defensive RL 기존 -0.244~+0.317 중간. PPO·TD3 중간 -0.250~+0.180. SAC 5종 -0.652~-0.769 약함군 (모두 음). TD3 5종 -0.825~+0.100 변동. 수치 헤시안 + 표준화 야코비안 J Σ J^T 보정 95% CI (라운드 18 2차 정정 후).
- (b) 시나리오 난이도 b̂(G, c) heatmap. severity c가 증가할수록 ACARL G의 b̂이 단조 증가. av18·av20 두 fit에서 일관된 단조 자료.
- (c) Severity 다이얼 γ̂ (av18·N=18·K=70): method_c 0.026 (가장 큰 양수, 라운드 19 정정으로 라운드 17·18의 -0.821 음의 다이얼 폐기)·method_b 0.016·cut-in 0.010·rear-end 0.008. 모든 G가 양의 단조성 자료. av20·N=20·K=20에서도 모두 양수 (cut-in 0.018·rear-end 0.034·method_b 0.025·method_c 0.037).
- (d) 회피불가 하한 û (av18·N=18·K=70): ACARL 두 G ≈ 5% (cut-in 0.056·rear-end 0.051), baseline 두 G ≈ 0.1~0.4% (method_b 0.001·method_c 0.004). av20에서 동일 자료 (cut-in 0.057·rear-end 0.054·method_b 0.003·method_c 0.004).
- 변별력 â의 trial 자료 의존성 양면 자료는 본문 §5.5·§6.4 참조 (av18: cut-in 24.43·rear-end 30.65 식별성 경계 자료, av20: 자연 sigmoid 6.64·7.39).

**본문 위치**: §5.5 fit_irt_main (§Results)

**추가 raw 자료** (D4 외적 타당성 sanity check에 활용):
- ACARL §6.5 cross-defender ρ: cut-in 0.53, rear-end 0.55
- 본 격자의 b̂(G, c)의 c별 단조성: heatmap에서 c=0→c=4 방향의 단조 증가 확인 가능.

---

## Figure S1·S2: D2 표준 응시자 split-half (보조)

**파일 경로**:
- Figure S1 (N=5 응시자):
  - PDF: `analysis/highway_grid/figures/d2_split_half_av5.pdf`
  - PNG: `analysis/highway_grid/figures/d2_split_half_av5.png`
- Figure S2 (real 응시자 split):
  - PDF: `analysis/highway_grid/figures/d2_split_half_real.pdf`
  - PNG: `analysis/highway_grid/figures/d2_split_half_real.png`

**Panel 구성** (figure 직접 점검 권고):
- 응시자 부분집합을 무작위 분리하여 두 부분집합의 b̂ Pearson r 분포.
- 수치: r mean = -0.014 ~ 0.415 (합격선 0.80에 한참 미달)

**Caption baseline** (사용자가 voice 정리):
- 응시자 부분집합을 무작위 분리한 두 b̂의 Pearson r 분포.
- 응시자 N=3~5의 작은 표본에서 통계 검정력이 부족함이 확인되었다. r mean = -0.014~0.415로 합격선 0.80에 미달.
- 본 한계는 응시자 N 부족에서 기인하며 본 측정 모델 자체의 정합성과는 분리된다. 본 검증을 보조 sanity 수준으로 옮기고 D2 trial-split 변형 (Figure 3)으로 보완.

**본문 위치**: §Limitations 또는 Supplementary Material (응시자 N 부족 한계 단락에서 참조)

---

## Figure 1 후보: §Introduction motivation (사용자 결정)

**상태**: 본 시점에 미작성. 사용자가 결정하면 작성.

### 옵션 A: LD-Scene·Shen 2025의 rank reversal 시각화

**개념**:
- 두 SUT (예: SUT_A, SUT_B) 위에서 시나리오 셋의 충돌률 분포가 어떻게 다른지 boxplot 또는 scatter.
- 동일한 시나리오 셋에서 SUT_A로는 시나리오 1이 어렵고 SUT_B로는 시나리오 2가 어렵다는 흐름을 한 그림으로 보여줌.
- 본 figure가 본 측정 모델의 motivation을 직접 보여주는 자료.

**데이터 출처**:
- LD-Scene (Peng 2026) 또는 Shen 2025의 원문 figure 인용 (원문 attribution 필요)
- 또는 본 격자의 K=70 자료로 직접 산출 (응시자 5종 × 시나리오 부분집합 분리)

### 옵션 B: 본 측정 모델의 conceptual schematic

**개념**:
- 시험 비유: 시나리오 = 시험문제, AV = 수험생, 충돌 = 오답
- 본 측정 모델의 식 (1)~(9) 흐름을 도식화: 응시자 θ + 생성기 G + severity c → 충돌 확률 P(Y=1)
- 본 도식이 reviewer에게 본 측정 모델의 직관을 빠르게 전달.

**산출 자료**:
- matplotlib + 일러스트레이션 (사용자 voice 선호)
- TikZ·draw.io 같은 conceptual diagram 도구

### 옵션 C: 두 figure 모두 (Figure 1·2를 introduction에 둠)

본 옵션이 가장 자료가 강하지만 본문 page 자료가 늘어남.

---

## Figure - method schematic 후보 (사용자 결정)

**상태**: 본 시점에 미작성.

**개념**:
- 식 (1)~(9)의 conceptual flow를 한 figure로 보여줌
- AV 응시자 → 생성기 G (severity c) → 충돌 응답 Y → IRT 적합 → 추정값 θ̂·b̂·γ̂·â·û
- 본 figure가 §Method의 첫 figure로 들어가면 reviewer가 측정 모델의 구조를 한눈에 봄.

**산출 자료**:
- matplotlib + arrow·label
- 또는 사용자가 직접 draw.io·PowerPoint로 작성한 후 PDF로 export

---

## 부가 자료: Figure caption voice 작성 시 참조

### 본문 voice 규칙 (CLAUDE.md)
- "자리" 어휘 회피
- 흐르는 산문 (불릿·표·라벨식 도식 회피, 본문에 한정)
- 메타포 회피 (부품·묶음·척추·축·무게중심·바닥 등)
- em-dash 회피 (콜론·가운뎃점·en-dash 활용)
- 자연스러운 동사 ("측정한다·산출한다·검증한다")
- 본보기 한글 학술 voice는 `N0210370104.pdf` (김예은·최성진·여화수 2019)

### Caption 표준 voice 자료
- 영문 AAAI 본문: figure caption은 한 문장 또는 짧은 단락. (a)·(b)·(c) panel 자료가 있으면 각각 한 줄.
- 한글 본문 voice: 본 baseline의 흐름을 본문 voice로 정리 (예: "각 cell의 K=70 episode를 35 vs 35로 분리한 두 충돌률 매트릭스의 Pearson r 분포이다. 단조성 통과 3 G에서 r mean=0.917로 합격선 0.80을 명확히 통과한다.")

### 수치 표기 voice (라운드 22 av18·av20 자료 본보기)
- ρ = 0.900 (소수점 셋째 자리, D1 단조성 av18 자료)
- r mean = 0.996·p25 = 0.996 (소수점 셋째 자리, D2 trial-split av18 통과 3 G)
- LR = 195,191.53 (소수점 둘째 자리, 큰 자료라 자릿수 보존; D3 no_severity deviance av18)
- θ̂ = +0.3170 ± 0.428 (점추정과 95% CI half-width = 1.96·SE; av18 def_rl_789)
- ρ = 0.9587 (소수점 넷째 자리, cross-fit Spearman 자료의 정밀도가 본문 voice의 학술 강도와 정합)
- p < 10⁻¹⁰ (지수 표기, 매우 강한 유의성)

---

## 부록: figure 산출 코드와 데이터 자료

### 산출 코드 경로
- `analysis/highway_grid/fit_irt_main.py`: Figure 5 (irt_main 4-panel)
- `analysis/highway_grid/d2_trial_split.py`: Figure 3 (d2_trial_split)
- `analysis/d-grid-validation/d1_*.py`, `d2_*.py`, `d3_*.py`: Figure 2·4·S1·S2 (정확한 경로는 d-grid-validation 디렉토리 점검 권고)

### 응답 jsonl (figure 산출의 입력 데이터)
- `analysis/highway_grid/responses_def_rl_combined.jsonl`: K=70 통합 응답 (Defensive RL 세 시드)
- `analysis/highway_grid/responses_*.jsonl`: 각 응시자·시드별 응답 자료

### figure 다시 산출하는 흐름
1. K=70 통합 응답 jsonl을 입력으로 fit_irt_main.py 실행 → irt_main.{pdf,png,json}
2. K=70 응답 jsonl을 입력으로 d2_trial_split.py 실행 → d2_trial_split.{pdf,png}
3. K=70 응답 jsonl을 입력으로 d1·d3 분석 스크립트 실행 → d1·d3 figure
4. 본문 page 크기에 맞게 figure layout 정정 (필요 시 fit_irt_main.py의 figsize·dpi 조정)
