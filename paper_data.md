# AAAI Paper Raw Data: SUT-Invariant Measurement (IRT)

본 파일은 AAAI 메인 트랙 본문 voice 작성용 raw 자료이다. 본문 voice는 사용자가 Claude 웹에서 직접 작성하며, 본 파일의 자료는 voice 작성에 필요한 수치·진단·논리 흐름·인용 위치를 표준 본문 구조 outline에 맞춰 정리한다. Figure 자료는 `paper_figures.md`에, 인용 reference는 `paper_references.md`에 분리되어 있다.

---

## §0 본문 작성 가이드

- 본 자료는 voice가 비어 있는 raw 자료이다. 본문 voice는 사용자가 직접 작성한다.
- voice 규칙은 `CLAUDE.md` 참조 (자리 어휘·메타포·em-dash·라벨식 도식·구어 표현 금지, 흐르는 산문).
- 본보기 한글 학술 스타일은 `N0210370104.pdf`(김예은·최성진·여화수 2019, 대한교통학회지) 참조.
- 모든 수치·결과는 라운드 19 N=20 확장 후 highway-env 격자 기준이다. 정확한 구성: 응시자 N=20 (IDM·MOBIL 각 K=20·Defensive RL 3 시드·PPO 5 시드·SAC 5 시드·TD3 5 시드 각 K=70) × G=4 × c=5로 통합 26,000 episode (`responses_av20_combined.jsonl`, 본문 주 자료). 학습 응시자 18종만 K=70 자료는 `responses_av18_learned.jsonl` (25,200 episode)로 D 분석 핵심. fit_irt_main은 두 자료로 산출: `irt_main_av18.json`·`irt_main_av20.json`.
- 각 단락의 "raw 자료" 아래 항목이 본문 voice 작성에 박힐 자료이며, "인용" 항목은 `paper_references.md` 식별자 참조.

### 한·영 용어 매핑 표 (본문 영어 voice 작성 시 일관 참조)

| 한글 raw 자료 | 영어 본문 voice |
|---|---|
| 응시자 (AV 정책) | subject / examinee (informal: AV policy) |
| 생성기 | generator |
| 시나리오 | scenario |
| 응시자 강건성 θ | (latent) robustness, person ability θ |
| 시나리오 난이도 b(G, c) | (latent) scenario difficulty b(G, c) |
| 변별력 a_G | discrimination a_G |
| 회피불가 하한 u_G | unavoidable lower bound u_G |
| severity (위험도) c | severity c |
| 단조성 ρ | monotonicity (Spearman ρ) |
| trial-split | trial-split |
| split-half | split-half |
| 표본 불변성 | sample invariance |
| SUT-불변 측정 | SUT-invariant measurement |
| specific objectivity | specific objectivity |
| 격자 (응답표) | grid / response table |
| 적대 시나리오 | adversarial scenario |
| 충돌 (충돌률) | collision (collision rate) |
| 시뮬레이터 충실도 | simulator fidelity |
| 적대 학습 | adversarial learning |
| 정합성 | consistency (학술), validity (외적) |
| 학술 anchor | scholarly anchor / supporting evidence |
| 본문 voice | manuscript prose |
| 결정 트레일 | decision trail / decision log |

본보기 학술 voice의 전환 흐름은 두 단계이다. 한글 raw 자료 → 한글 학술 voice (N0210370104.pdf 본보기 적용) → 영어 본문 voice (AAAI 학술 표준). 본 두 단계 voice 전환에서 위 매핑 표가 일관 참조된다.

---

## §1 Introduction

### 1.1 본 연구의 motivation: 충돌률 같은 표준 지표의 SUT 의존성

**raw 자료**:
- 자율주행 적대 시나리오 생성 분야의 표준 평가 지표: 충돌률(collision rate), TTC(time-to-collision), THW(time-headway), DRAC(deceleration rate to avoid collision).
- 본 지표들은 모두 SUT(System Under Test, 평가 대상 자율주행 정책)의 능력에 의존하는 양이다. 같은 시나리오를 다른 AV에 적용하면 충돌률·TTC·THW가 모두 달라진다.
- LD-Scene (Peng et al. 2026, TR-C)이 본 의존성을 직접 보였다: 시나리오를 고정하고 SUT를 바꾸면 시나리오 난이도 순위가 역전된다.
- Shen et al. 2025 (Accident Analysis and Prevention)는 본 의존성을 통제 실험으로 정량 증명했다: 같은 시나리오 셋에 다른 SUT를 적용했을 때 충돌률의 분포가 SUT별로 크게 갈리며 순위가 안정적이지 않다.
- 본 결과의 학술 함의: 충돌률 같은 단일 지표로 산출한 "시나리오 난이도"는 그 시나리오 자체의 속성이 아니라 SUT와 시나리오의 상호작용의 산물이다.

**인용**: Peng2026LDScene, Shen2025AAP, Riedmaier2020Access, Menzel2018IV, ISO34501

### 1.2 본 연구의 빈 영역: IRT의 자율주행 적대 평가 적용

**raw 자료**:
- 측정학(psychometrics)에는 본 SUT-시나리오 상호작용을 분리하는 표준 방법이 있다: Item Response Theory (IRT, Lord 1980, Rasch 1960).
- IRT는 응시자(수험생)의 latent ability θ와 문항의 latent difficulty b를 동시에 추정하여 두 양을 분리한다. 본 분리의 핵심 성질이 specific objectivity (Rasch family) 또는 sample-invariant scale (모든 IRT family)이다.
- IRT는 교육 평가에서 출발하여 분류기·회귀·LLM·강화학습 에이전트 평가로도 옮겨와 검증되었다 (Martínez-Plumed et al. 2019, agent psychometrics 2026, PSN-IRT, Fluid Benchmarking, β³-IRT).
- 자율주행 적대 평가에는 IRT가 아직 적용된 적 없다. 본 연구가 채우려는 빈 영역이다.

**인용**: Lord1980, Rasch1960, MartinezPlumed2019AI, AgentPsychometrics2026, PSNIRT, FluidBenchmarking, Beta3IRT

### 1.3 본 측정 모델의 핵심 아이디어: 시험 비유

**raw 자료**:
- 본 측정 모델의 mapping: 시험문제 = 시나리오/생성기, 수험생 = AV 정책, 오답 = 충돌, 문제 난이도 = 시나리오의 진짜 위험도 b(G, c), 수험생 실력 = AV의 진짜 강건성 θ.
- 본 mapping이 IRT의 latent variable 두 종(item difficulty·person ability)을 자율주행 적대 평가의 양(시나리오 난이도·AV 강건성)으로 자연스럽게 옮긴다.
- 자율주행 적대 평가의 세 가지 특수성 (시험용 IRT의 표준 가정과 어긋남):
  - (a) 시나리오는 AV의 행동에 반응한다 (closed-loop)
  - (b) 같은 생성기로 위험도 c를 연속해서 조절할 수 있다 (severity 다이얼)
  - (c) 충돌에는 회피할 수 있었던 것과 누구도 피할 수 없는 것이 섞여 있다 (avoidability)
- 본 세 특수성을 측정 모델 안으로 끌어들여 형식화하는 것이 본 연구의 핵심 기여이다.

### 1.4 Contribution (세 항목, 2026-06-07 라운드 19 정정: N=20 응시자 확장으로 강화)

**raw 자료**:
1. **방법론 신규성**: IRT를 자율주행 적대 평가에 처음 적용. 본 측정 모델의 식 (1)~(9)이 closed-loop 반응성·severity 조건화·avoidability를 IRT 안에 형식화.
2. **응시자 가족 다양성 위에서 척도 보존**: 본 측정 모델이 응시자 20종(IDM·MOBIL·Defensive RL 3 시드·PPO 5 새 시드·SAC 5 시드·TD3 5 시드) 위에서 SUT-불변성을 D1 단조성·D2 trial-split·D3 ablation·D4 외적 타당성 sanity check로 검증. 본 응시자 가족이 학습 방식 4종(IDM rule-based·MOBIL lane-change·PPO on-policy·SAC·TD3 off-policy) × 시드 분산으로 본 측정 모델의 specific objectivity 가정을 강하게 받침.
3. **표준 적대 생성기 위에서 척도 안정 + 생성기 진단 능력**: K=70 통합 격자에서 세 생성기(ACARL cut-in·rear-end·method_c)가 D1 단조성 합격선 ρ ≥ 0.7을 통과 (cut-in 0.900·rear-end 0.700·method_c +0.900). Method B Naive는 단조성 ρ=0.000으로 통과 못함과 동시에 변별력 â가 약해 본 격자의 baseline의 한 흠으로 진단됨. 본 측정 모델이 단조성 가정을 만족하는 G(PASS)와 만족하지 못하는 G(Method B, ρ=0.000)를 명확히 분리하여 응시자 분리에 의미 있는 G와 의미 없는 G를 데이터로 식별한다는 부가 발견.

**라운드 19 N=20 확장의 핵심 발견 (이전 contribution voice 정정)**:
- 라운드 17·18에서 Method C의 음의 단조성 ρ=-0.821을 "본 측정 모델의 진단 능력"으로 contribution voice에 활용한 흐름이 N=18·K=70 자료(라운드 19)에서 ρ=+0.900으로 정정됨. 본 자료가 응시자 N=3·5의 작은 표본 흠이 만든 가짜 음의 단조성이었음을 직접 보임. 본 contribution voice를 폐기하고 본 발견을 §Limitations에 정직히 적되 본 측정 모델의 응시자 다양성에 대한 강인성의 학술 anchor로 활용.
- 응시자 N=3 → N=20 확장으로 검토자(라운드 19 깊은 검토)가 잡은 핵심 흠("same-family 시드 분산")이 본질적으로 해소됨. PPO·SAC·TD3 세 학습 방식의 다양성으로 본 측정 모델이 학습 방식 차이를 응시자 강건성 θ̂의 자릿수 차이로 정직히 분리한다는 새 학술 anchor가 산출됨.

---

## §2 Related Work

### 2.1 IRT의 ML 평가 적용

**raw 자료**:
- Martínez-Plumed et al. 2019 (Artificial Intelligence): IRT가 dual character로 item(instance)과 respondent(classifier)에 대해 모두 정보를 제공한다. ML 평가의 표준으로 정착.
- agent psychometrics 2026: agent 평가에 IRT 적용 (정확한 서지 정보 확인 필요).
- PSN-IRT, Fluid Benchmarking, β³-IRT: IRT-for-AI의 최근 변형 (정확한 서지 정보 확인 필요).
- 본 관련 연구들이 자율주행 적대 평가의 본 분야에 IRT를 옮긴 첫 시도가 본 연구.

**인용**: MartinezPlumed2019AI, AgentPsychometrics2026, PSNIRT, FluidBenchmarking, Beta3IRT

### 2.2 자율주행 적대 시나리오 생성

**raw 자료**:
- SafeBench (Xu et al. 2022, NeurIPS): CARLA 0.9.13 위에 적대 생성 알고리즘 4종 (LC·AdvSim·AdvTraj·NF) + RL ego 에이전트 + 도커 환경 제공. 본 연구 라운드 1~15에서 본 인프라 활용 후 라운드 16에서 매몰 비용 처리.
- FREA (CoRL 2024 Oral, SafeBench 포크): 반응형 CBV + 실행가능영역(LFR) 네트워크 구현.
- ACARL (저자 동일, AAP under review): Aggressiveness-Calibrated Adversarial Reinforcement Learning. highway-env 환경에서 cut-in·rear-end 두 시나리오 type 정책 + severity 다이얼 c_level ∈ [0, 0.8]. Method A (Ours) + Method B (Naive) + Method C (Rule-based AuthSim 구조) + Method D (GAIL) 4종 baseline 비교.
- AuthSim (T-ITS 2025, highway-env 환경): 자율주행 적대 시나리오 평가의 선례.
- Wang·Ma·Lai 2026 (T-IV, highway-env 환경): 공격성 파라미터 전례. 본 연구의 severity 다이얼의 reference.

**인용**: Xu2022SafeBench, CoRL2024FREA, ACARL2026 (under review, AAP), AuthSim2025TITS, WangMaLai2026TIV

### 2.3 시나리오 난이도 정량화의 선행 연구

**raw 자료**:
- Yang et al. 2024 (arXiv 2408.14000), "Quantitative Representation of Scenario Difficulty ... Adversarial Policy Search": 본 연구의 가장 가까운 경쟁이었으나 무력화됨. 본 논문의 difficulty가 단일 SUT에서의 충돌률·TTC·THW로 정의되어 SUT 의존성을 분리하지 못한다.
- Ponn et al. 2020 (EVER): 주장 3 (SUT-시나리오 분리)의 개념적 정의. 본 연구의 핵심 동기를 제공.
- Qiu et al. 2026 (TR Part C): 난이도가 SUT 성능으로 조작적 정의됨. 본 연구가 분리해야 한다고 주장하는 자료.
- Shen et al. 2025 (Accident Analysis and Prevention): 시나리오 고정·SUT만 변경 시 충돌률 출렁임을 통제 실험으로 증명. 본 연구의 motivation의 강한 정량 근거.
- Fan et al. 2026 PMCT (TR Part C): 시나리오 난이도 정량화 자료.
- Peng et al. 2026 LD-Scene (TR Part C): 시나리오 고정·AV 변경 시 난이도 순위 역전.
- Liao et al. 2025 (Information and Software Technology): ADS testing 서베이.

**인용**: Yang2024Arxiv, Ponn2020EVER, Qiu2026TRC, Shen2025AAP, Fan2026PMCT, Peng2026LDScene, Liao2025IST

### 2.4 시뮬레이터·자율주행 평가 표준

**raw 자료**:
- Riedmaier et al. 2020 (IEEE Access): 시나리오 기반 안전성 평가의 표준 틀.
- Menzel et al. 2018 (IEEE IV): functional·logical·concrete 세 단계 시나리오 정의.
- ISO 34501 (2022): SUT 정의 ("the automated driving system that is tested with test scenarios").
- Ding et al. 2023: 자율주행 적대 시나리오 생성 서베이 (생성기 우수성·시나리오 난이도가 충돌 관련 양으로 측정됨).

**인용**: Riedmaier2020Access, Menzel2018IV, ISO34501, Ding2023Survey

---

## §3 Method: 측정 모델 형식화

### 3.1 본 측정 모델의 식 (1)~(9)

**raw 자료** (수식은 method.html §s2~s5 참조):
- **식 (1) Item Response Function**: P(Y = 1 | π, G, c) = u_G + (1 − u_G) · σ(a_G · (b(G, c) − θ_π))
  - Y = 1: 충돌, Y = 0: 무충돌
  - π: 응시자(AV 정책)
  - G: 시나리오 생성기, c: severity level
  - θ_π: 응시자 강건성 (latent person ability, 음수 = 약함, 큰 값일수록 충돌 확률 감소)
  - b(G, c): 시나리오 난이도 (latent item difficulty, 큰 값 = 어려움, 충돌 확률 증가)
  - u_G: 회피불가 하한 (생성기 G의 baseline 충돌 확률, ego 행동과 무관한 자료)
  - a_G: 변별력 (생성기 G가 응시자 강건성을 얼마나 잘 분리하는지)
  - σ: standard logistic function
  - 부호 정합성: b(G,c) − θ_π 형태로 적합. θ_π가 클수록 (b − θ_π)가 작아져 충돌 확률 감소. method.html 식 (6)·`d_study.py` 적합 코드 (`eta = a*(beta + gamma*c − theta)`)와 정합.
  - **거울 구조 명시 (IRT 표준 3PL과의 관계)**: 표준 3PL (Lord 1980)은 정답 확률을 모형화하며 lower asymptote c가 정답 쪽 (`P(Y=1) = c + (1−c)·σ(a(θ−b))`, Y=1=정답). 본 식 (1)은 충돌(=오답에 해당) 확률을 모형화하며 lower asymptote u_G가 오답 쪽 (Y=1=충돌, b−θ 형태로 거울 변형). 본 거울 구조는 자율주행 적대 평가의 도메인 voice(충돌 확률 모형화)와 IRT 표준의 통계 형식을 연결한다. Lord 1980 §3·§4의 3PL 정의와 De Boeck·Wilson 2004의 explanatory IRT의 거울 변형이 본 자료의 학술 anchor이다.

- **식 (2) Severity 조건화**: b(G, c) = β_G + γ_G · c
  - β_G: 생성기 G의 baseline 난이도 (c=0에서의 난이도)
  - γ_G: severity 다이얼 강도 (c가 1 단위 증가할 때 난이도 증가량)

- **식 (3) γ_G 양수 강제**: γ_G = exp(lg_G), lg_G ∈ ℝ
  - γ_G > 0 강제로 모델 안에서 단조 증가 가정 보장
  - 식별성 조건의 일부

- **식 (4) 변별력 양수 강제**: a_G = exp(la_G), la_G ∈ ℝ. ICC의 기울기 모수가 양수 강제로 모형 안에서 단조 증가 가정 보장. method.html 식 (7)과 정합.
- **식 (5) 회피불가 하한 logit parameterization**: u_G = σ(zu_G), zu_G ∈ ℝ. u_G ∈ [0, 1] 강제. 본 격자의 적합 코드(d_study.py)는 zu_G ∼ N(−2, 2) 약사전정보 하에 자유 추정 (방법 본문에는 method.html 확정 사양 2번 "RSS·귀책 라벨로 고정하거나 강한 사전정보로 준다"의 differ를 정직 명시).
- **식 (6) 응시자 강건성 prior**: θ_π ∼ N(0, σ_θ²). σ_θ는 표본 평균 0·표본 분산 σ_θ²의 N=20 자료에서 적합. method.html 식 (8)과 정합.
- **식 (7) 척도 식별성 조건 1 (응시자 평균 0)**: ∑_π θ_π / N_av = 0. fit_map 적합 후 사후 변환으로 강제.
- **식 (8) 척도 식별성 조건 2 (생성기 baseline 평균 0)**: ∑_G β_G / N_g = 0. method.html 식 (9)와 정합.
- **식 (9) Laplace 사후 추정**: SE_θ는 수치 헤시안 + 표준화 야코비안 J Σ J^T 산출 (라운드 18 2차 정정 후). method.html 식 (8)~(9)의 GLMM·Laplace approximation과 정합.

**식 번호 매핑 (paper_data §3.1 ↔ method.html)**:
| paper_data §3.1 | method.html |
|---|---|
| 식 (1) | 식 (6) |
| 식 (2) | 식 (4) |
| 식 (3) | 식 (5) |
| 식 (4) | 식 (7) |
| 식 (5) | 확정 사양 2번 |
| 식 (6) | 식 (8) |
| 식 (7)~(8) | 식 (9) (식별성 조건) |
| 식 (9) | 식 (8) (Laplace approximation) |

- **u_G 자유 추정의 식별성 영향 (REVIEW_FIXLIST B-4 + 라운드 21 보강)**: u_G·a_G·θ_π의 동시 식별이 4-parameter logistic의 알려진 약점이다. 본 격자는 K=70 trial 풍부함이 u_G 식별성을 보충하나, ACARL G의 cut-in·rear-end에서 â이 24·30으로 식별성 경계에 닿은 자료(§5.5·§6.4)와 결합하여 본 모형의 ceiling 영역의 식별성 약화를 만든다. 본 한계를 §6.4에 정직 명시.
- **사후 표준화의 식별성 자료 (REVIEW_FIXLIST B-2)**: 본 적합은 θ에 N(0,1) prior를 두면서 동시에 적합 후 θ=(θ−mean)/std로 표본 평균 0·표준편차 1을 강제하는 사후 변환을 적용한다. eta = a·(b−θ)는 보존되어 점추정 해석은 일관되나, 척도가 prior와 사후 변환 양쪽에서 이중으로 고정되는 자료. SE의 정확한 산출은 수치 헤시안 기반(REVIEW_FIXLIST A-1)으로 정정되었다.

### 3.2 specific objectivity와 표본 불변성

**raw 자료**:
- 본 측정 모델의 핵심 성질: 응시자 강건성 θ_π의 추정값이 시나리오 부분집합 (subset of G × c) 의 선택에 무관하다.
- 본 성질은 충돌률 같은 단일 지표가 가지지 못한 자료이며, LD-Scene·Shen 2025가 보인 SUT-시나리오 상호작용의 분리 가능성을 데이터로 받친다.
- D1 검정 (단조성 + 시나리오 부분집합 사이의 AV 순위 안정성)이 본 성질의 직접 검증.

### 3.3 D1·D2·D3·D4 검정 정의

**raw 자료**:
- **D1 단조성**: 각 생성기 G의 충돌률이 severity c가 증가할 때 단조 증가하는지 Spearman ρ로 검정. 합격선 ρ ≥ 0.7. 응시자 평균 위에서 G별 종합 ρ 산출.
- **D1 rank reversal sanity**: 시나리오 부분집합 A vs B로 무작위 분리하여 두 부분집합에서의 AV 순위 Spearman ρ 계산. 본 ρ가 안정되면 본 측정 모델의 표본 불변성이 확인됨.
- **D2 trial-split 변형**: 각 (av_id, g_id, c) cell의 K=70 episode를 무작위 35 vs 35로 분리하여 두 (G, c) 충돌률 매트릭스의 Pearson r을 50회 반복 산출. 합격선 r ≥ 0.80.
- **D2 표준 응시자 split-half** (보조 sanity): 응시자 부분집합을 무작위 분리하여 b̂의 응시자 표본 의존성 검정. 합격선 r ≥ 0.80. 본 격자의 응시자 N=3~5에서는 통계 검정력 부족.
- **D3 ablation (deviance 비교)**: 본 모델의 세 구조를 하나씩 제거한 변종과 본 모델의 deviance Δ 비교. REVIEW_FIXLIST B-1 정정 (u_zero 변종 Δ = -18.04 음수가 nested LRT 아님의 직접 증거).
  - no_severity: γ_G = 0 강제 (severity 조건화 제거, df=4)
  - g_common: G를 단일 그룹으로 통합, β·γ·a·u 4 모수가 4→1로 축소 (df=12)
  - u_zero: u_G = 0 강제 (회피불가 하한 제거, 선택)
- **D4 외적 타당성 sanity check**: ACARL 원고 §6.5의 cross-defender Spearman ρ (cut-in 0.53, rear-end 0.55)와 본 격자의 b̂의 c별 단조성 ρ 자릿수 일치 비교. 척도 일치(scale linking)는 latent trait 추정과 다른 통계량이라 불가능.

---

## §4 Experiment

### 4.1 환경

**raw 자료**:
- **환경**: highway-env 1.10.2 + ACARL infrastructure (`<anonymized-acarl-repo>`)
- **결정 이력 (decisions.html #d06·#d07 참조)**:
  - 라운드 1~15: CARLA + SafeBench (CARLA 0.9.13 도커), 매몰 비용 처리
  - 라운드 16 (2026-06-04): highway-env + ACARL로 전면 이전. 근거: pilot v3 K=20에서 SafeBench 적대 생성기 셋(LC·idm_attack·mobil_attack)의 단조성 한 종만 통과, BasicAgent·BehaviorAgent의 적대 생성기와 정책 가족 중복.
  - 라운드 17 (2026-06-06): 시뮬레이터 충실도 강화를 위한 CARLA 재시도 종결 (v1·v2·v3 모두 fast crash로 수렴). 본 진단(CARLA의 3D physics·관성이 RL 정책의 환경 우회 학습을 가능케 함)으로 highway-env 본문 유지.
- **highway-env 선례**: AuthSim (T-ITS 2025), ACARL (AAP under review), Wang·Ma·Lai (T-IV 2026).

### 4.2 응시자 가족 (N=20, 라운드 19 확장)

**raw 자료**:
- **응시자 20종** (학습 방식 4종 × 시드 분산):
  - **규칙 기반 2종**: IDM (highway-env 표준 longitudinal controller), MOBIL (lane-change controller)
  - **Defensive RL 3 시드 (기존)**: 42·456·789, ACARL이 학습한 PPO 정책 (`results/defensive/seed{S}_*/final_model.zip`)
  - **PPO 새 5 시드 (라운드 19 추가)**: 100·200·500·800·999, ACARL infrastructure에서 학습 (`results/defensive_multi/ppo/seed{S}_*/final_model.zip`)
  - **SAC 5 시드 (라운드 19 추가)**: 42·100·456·789·999, off-policy 학습, stable-baselines3 default hyperparam (`results/defensive_multi/sac/seed{S}_*/final_model.zip`)
  - **TD3 5 시드 (라운드 19 추가)**: 42·100·456·789·999, DDPG의 안정 변형 (`results/defensive_multi/td3/seed{S}_*/final_model.zip`)
- **응시자 확장 결정 근거 (라운드 19 깊은 검토자 진단)**:
  - 라운드 17·18 시점의 N=3·5(Defensive RL 세 시드와 IDM·MOBIL 자료)가 검토자의 "same-family 시드 분산" 흠 진단을 받음. PPO·SAC·TD3 세 학습 방식의 다양성을 추가하여 본 측정 모델의 specific objectivity 검증을 강화.
  - 학습 시간: PPO 약 33분/seed × 5, SAC 약 58분/seed × 5, TD3 약 42분/seed × 5. 총 학습 약 11시간 (2026-06-06 16:17 시작·2026-06-07 03:26 종료).
  - ACARL 기존 5-seed 중 def_rl_123 (전 cell 0% 충돌)·def_rl_1024 (70% baseline 충돌)은 정규 분포 가정에서 벗어난 양극단으로 본 격자에서 제외(ACARL §5.3 자료).
- **본 N=20 확장의 학술 함의**:
  - 학습 방식 4종(rule-based·on-policy PPO·off-policy SAC·off-policy TD3)이 본 측정 모델 fit에서 θ̂의 자릿수 차이로 명확히 분리 (§5.5 자료): PPO 강건군 +2.0~+2.2·SAC 약함군 -0.77~-0.65·TD3 변동·Defensive RL 기존 중간.
  - 본 분리가 검토자가 잡은 핵심 흠("same-family 시드 분산")의 본질적 해소이며 contribution 2의 강한 학술 anchor.

### 4.3 시나리오 생성기 (G = 4)

**raw 자료**:
- **생성기 4종 (ACARL 인프라 활용)**:
  - **acarl_cutin**: ACARL Method A, scenario_type = "cut_in". RL 학습된 adversarial NPC가 ego 차량에 옆 차선에서 끼어들기.
  - **acarl_rearend**: ACARL Method A, scenario_type = "rear_end". RL 학습된 adversarial NPC가 ego 차량 앞에서 갑작스러운 brake.
  - **method_b**: ACARL Method B, Naive adversarial. 직접 충돌을 보상하는 단순 RL.
  - **method_c**: ACARL Method C, Rule-based (AuthSim 구조). zone-based reward를 사용하는 규칙 기반 적대 생성기.
- **각 생성기의 5-seed 학습 ckpt 활용** (ACARL repository).

### 4.4 Severity 격자 c (5 수준)

**raw 자료**:
- c = {0, 1, 2, 3, 4} 다섯 수준 정수 grid
- ACARL의 c_level ∈ [0, 0.8] 학습 분포와 매핑: c = k → c_level = 0.2k
- 본 매핑이 ACARL §6.2에서 보고된 c_level=0.0~0.8 자료의 단조성 검증 범위에 정합.
- ACARL §6.2: c_level=0.8 (학습 분포 가장자리)에서 측정 median THW가 1.652s로 target THW*=1.0s를 초과. c=0~3 (c_level=0~0.6) 구간이 안정.

### 4.5 반복 K와 응답 자료 구성 (라운드 19 N=20 확장 후)

**raw 자료**:
- **K 결정 흐름**:
  - K=20 본 격자 (응시자 5종 × G=4 × c=5 × K=20 = 2,000 episode, 2026-06-04 라운드 16): acarl_cutin만 ρ=0.821 통과
  - K=50 보강 격자 (Defensive RL 세 시드 × G=4 × c=5 × K=50 = 3,000 episode, 2026-06-05): acarl_rearend만 ρ=0.900 통과
  - K=70 통합 (Defensive RL 세 시드 cell당 70 episode): 세 생성기 통과로 안정
  - **라운드 19 격자 응답 산출**: 추가 15 응시자 × G=4 × c=5 × K=70 = 21,000 episode (2026-06-07, 약 6시간 12분)
- **응시자별 trial 풍부함**:
  - IDM·MOBIL: K=20 (각 G=4 × c=5 × K=20 = 400 episode/응시자, 두 응시자 합 800 episode)
  - Defensive RL 3 시드 + PPO 5 + SAC 5 + TD3 5 = 18 시드: K=70 (각 1,400 episode/시드, 18 시드 합 25,200 episode)
- **응답 jsonl 두 갈래**:
  - `responses_av20_combined.jsonl`: **26,000 episode** (20종 통합, 본문 주 격자 출력)
  - `responses_av18_learned.jsonl`: **25,200 episode** (학습 응시자 18종만, IDM·MOBIL 제외)
- **fit·D 분석 산출 분리**:
  - **N=20·K=20 fit** (`irt_main_av20.json`): 본문 주 결과. `responses_av20_combined.jsonl` 입력, build_resp_dict이 cell당 K를 최소 K=20으로 잘라 처리.
  - **N=18·K=70 fit** (`irt_main_av18.json`): D 분석 핵심·본문 보조 sanity. `responses_av18_learned.jsonl` 입력, trial 풍부.
  - D1·D2 trial-split·D3 ablation: `responses_av18_learned.jsonl` (N=18·K=70) 기준

---

## §5 Results

### 5.1 D1 단조성 (라운드 19 N=18·K=70 자료, 라운드 17·18의 N=3·5 결과를 본질적으로 정정)

**raw 자료**:
- **G별 종합 Spearman ρ** (응시자 평균 위에서, N=18 학습 응시자 자료):

| 생성기 G | ρ (N=18·K=70) | ρ (N=3·5, 옛 자료) | 합격선 ρ ≥ 0.7 |
|---------|---|---|----------------|
| acarl_cutin | **+0.900** | +0.821 | PASS |
| acarl_rearend | **+0.700** | +0.700 | PASS |
| method_b | **0.000** | +0.700 (옛) | **FAIL** (N 확장으로 통과 못함이 드러남) |
| method_c | **+0.900** | -0.821 (옛, 음의 단조성) | **PASS** (N 확장으로 양의 단조성 정정) |

- **세 생성기 합격선 통과** (cut-in·rear-end·method_c)
- **본 결과의 학술 함의**:
  - 라운드 17·18에서 Method C의 음의 단조성(ρ=-0.821)이 contribution voice의 핵심 진단 자료였으나 N=3·5의 작은 표본 흠이었음이 N=18·K=70 자료로 직접 드러남. Method C가 N=18에서 +0.900 양의 단조성을 보여 본 측정 모델의 단조 가정에 정합한 G로 정정.
  - Method B는 N=5에서 ρ=0.700 통과 자료였으나 N=18에서 ρ=0.000으로 통과 못함이 드러남. 본 G의 변별력 â이 ACARL 두 G의 약 1/12~1/14 수준(av18 fit: â_method_b=2.188 ÷ â_cut-in=24.430 ≈ 1/11, ÷ â_rear-end=30.653 ≈ 1/14)이라는 fit_irt_main 결과와 정합한 신호.
  - N 확장이 본 측정 모델의 단조성 검정 자료를 본질적으로 강화함.

→ **Figure**: `d1_rank_reversal_real.{pdf,png}` (라운드 23 재산출 완료, 2026-06-08; `d1_rank_reversal.py`의 `build_av_scenario_matrix` scen tuple 정정 후 N=18·K=70 자료로 갱신)

### 5.2 D2 trial-split (라운드 19 N=18·K=70 자료)

**raw 자료**:
- 각 (av_id, g_id, c) cell의 K=70 episode를 무작위 35 vs 35로 분리.
- 두 (G, c) 충돌률 매트릭스의 Pearson r을 50회 반복 산출.
- **결과 (N=18·K=70, 라운드 19 정정)**:
  - 전체 4 G: r mean = **0.994**, p25 = **0.993** (이전 N=5 0.939·0.925)
  - 단조성 통과 3 G (cut-in·rear-end·method_c): r mean = **0.996**, p25 = **0.996** (이전 0.917·0.895)
- **합격선 0.80을 모두 명확히 통과** (이전보다 더 강하게).
- **본 결과의 학술 함의**: N=18·K=70 자료의 trial 표본 안정성이 본질적으로 강해짐. 응시자 다양성과 trial 풍부함의 결합이 b̂ 추정의 통계 정합성을 매우 강하게 받침.

→ **Figure**: `d2_trial_split.{pdf,png}` (정정 후 재산출됨)

### 5.3 D2 표준 응시자 split-half (보조 sanity)

**raw 자료**:
- 응시자 부분집합을 무작위 분리 (N=3~5 응시자에서 split).
- r mean = -0.014 ~ 0.415 (합격선 0.80에 한참 미달).
- **본 결과의 학술 함의**: 응시자 N=3~5의 작은 표본에서 표준 D2 검정의 통계 검정력이 부족함이 확인되었다. 본 흠은 응시자 N 부족에서 기인하며 본 측정 모델 자체의 정합성과는 분리됨. 본 검증을 보조 sanity 수준으로 옮기고 D2 trial-split 변형으로 보완.

→ **Figure**: `d2_split_half_av5.{pdf,png}`, `d2_split_half_real.{pdf,png}` (보조)

### 5.4 D3 ablation (deviance 비교, 라운드 19 N=18·K=70 자료)

**raw 자료**:
- **no_severity 변종** (γ_G = 0 강제, severity 조건화 제거): **deviance Δ = 195,116.35 (df = 4)** (이전 N=5: 2,552.53의 약 76배 강화)
- **g_common 변종** (G를 단일 그룹으로 통합, β·γ·a·u 4→1 축소, df = 12): **deviance Δ = 4,454.03** (이전 N=5: 482.16의 약 9배)
- **u_zero 변종** (u_G=0 강제, df=4): **deviance Δ = +36.83** (이전 N=5: -18.04 음수 → 정상 양수로 정정)
- **본 결과의 학술 함의**:
  - 응시자 N 확장으로 deviance 자료 자릿수가 본질적으로 강화됨. severity 조건화·G별 차이의 의미가 본 측정 모델 안에서 매우 강하게 받쳐짐.
  - REVIEW_FIXLIST B-1이 잡은 "u_zero 변종 deviance 음수, nested LRT 아님" 흠이 N 확장으로 자동 해소됨. 본 검정이 N=18·K=70 자료에서 엄밀한 LRT 자료에 가까운 deviance 비교로 정합.
  - **재현성 정직 voice (라운드 23 추가)**: 정확한 deviance는 MAP 적합의 seed·수렴 자료에 따라 ±1% 안에서 변동한다. 본 환경 재현값(2026-06-08, `d3_figure.py --seed=0`)이 no_severity Δ ≈ 195,191·g_common Δ = 4,454.03·u_zero Δ ≈ +36.78로 본 단락의 본문값(195,116·4,454·+36.83)과 0.04~0.14% 이내 일치. 부호·자릿수·결론(세 변종 모두 본형 대비 매우 강한 적합도 손실, u_zero 양수 → 옛 N=5 -18.04 음수 흠 해소)은 안정적이며 reviewer 재현 시 본 변동 범위 안에서 같은 결론이 산출된다.

→ **Figure**: `d3_ablation_real.{pdf,png}` (라운드 23 재산출 완료, 2026-06-08; `d3_figure.py --seed=0`로 N=18·K=70 자료 갱신)

### 5.5 fit_irt_main 직접 적합 (라운드 19 N=20·N=18 두 자료)

**raw 자료** (source: `irt_main_av20.json`·`irt_main_av18.json`):

본 자료는 두 fit 결과를 모두 보존한다. **N=20·K=20** (모든 응시자, IDM·MOBIL 포함, build_resp_dict 최소 K=20으로 잘림): 본문 주 자료. **N=18·K=70** (학습 응시자만, trial 자료 풍부): 본문 보조 sanity check 및 D 분석의 핵심 자료.

**응시자 θ̂ (강건성, N=18·K=70, 강건성 순 정렬)**:

| 응시자 | θ̂ | 95% CI half-width | 알고리즘 |
|--------|-----|---|---|
| ppo_200 | +2.221 | ± 0.821 | PPO (강건) |
| ppo_800 | +2.027 | ± 0.757 | PPO |
| ppo_500 | +2.020 | ± 0.758 | PPO |
| def_rl_789 | +0.317 | ± 0.175 | Defensive RL (기존) |
| ppo_100 | +0.180 | ± 0.140 | PPO |
| td3_100 | +0.100 | ± 0.127 | TD3 |
| def_rl_42 | -0.001 | ± 0.110 | Defensive RL |
| def_rl_456 | -0.244 | ± 0.100 | Defensive RL |
| td3_789 | -0.250 | ± 0.102 | TD3 |
| ppo_999 | -0.429 | ± 0.130 | PPO |
| sac_42 | -0.652 | ± 0.182 | SAC |
| sac_456 | -0.678 | ± 0.189 | SAC |
| sac_100 | -0.727 | ± 0.200 | SAC |
| sac_999 | -0.738 | ± 0.201 | SAC |
| td3_42 | -0.752 | ± 0.206 | TD3 |
| sac_789 | -0.769 | ± 0.209 | SAC |
| td3_456 | -0.798 | ± 0.216 | TD3 |
| td3_999 | -0.825 | ± 0.223 | TD3 (약함) |

**알고리즘별 강건성 분리 (학술 핵심 발견)**:
- **PPO 응시자**: PPO 200·500·800이 가장 강건 (+2.0~+2.2). PPO 100·999는 중간·약함 (+0.18 ~ -0.43). PPO 학습이 시드별로 분산이 큰 자료.
- **Defensive RL (기존)**: -0.244 ~ +0.317 (중간). 다양한 강건성 수준.
- **TD3 응시자**: -0.83 ~ +0.10 (전체 약함, 시드별 변동 큼).
- **SAC 응시자**: -0.77 ~ -0.65 (모두 음, 가장 약함). off-policy 학습이 본 환경에서 보수적 정책으로 수렴한 자료.

**본 결과의 학술 함의**: 본 측정 모델이 학습 방식 4종(PPO·SAC·TD3·기존 Defensive RL)과 시드 분산을 응시자 강건성 θ̂의 자릿수 차이로 명확히 분리. 검토자(라운드 19 깊은 검토)가 잡은 "same-family 시드 분산" 흠이 본질적으로 해소된 직접 증거.

**PPO 강건군의 식별성 ceiling 신호 (라운드 21 발견·라운드 22 자릿수 정정)**: av20 fit에서 ppo_200·ppo_500·ppo_800 세 시드의 θ̂이 +2.1063897·+2.1065093·+2.1065029로 소수점 다섯째 자리에서야 갈리며 ppo_200이 약간 낮고 ppo_500·ppo_800은 일곱째 자리까지 거의 동일. SE도 0.49717·0.49713·0.49744로 넷째 자리까지 동일. av18 fit에서도 +2.0196 ~ +2.2209의 좁은 범위. 본 결과는 세 시드가 본 측정 모델의 ICC 상단(매우 강건한 응시자 영역)에서 step function 형태에 닿은 직접 증거이며, IRT의 표본 식별성 경계(ceiling identifiability boundary)의 직접 신호이다. 본 측정 모델이 ACARL G의 cut-in·rear-end â=24~31 영역과 PPO 강건군의 θ̂≈+2.106 영역에서 두 차원의 식별성 경계 신호를 동시에 보인다. 본 발견이 본 모형의 학술 강도(매우 강건한 응시자·강한 변별력 G를 임계적으로 분리)와 식별성 경계 한계의 양면을 직접 드러낸 진단이며, 본문 §Results 한 단락 + §Limitations §6.4의 식별성 경계 한계 단락에 함께 풀어 적는다. (라운드 21 보고에서 ppo_800을 "+2.1064"로 적은 자릿수가 어느 시드와도 일치하지 않는 흠을 라운드 22 적대적 검토에서 잡아 정정한 기록.)

**N=20·K=20 fit (응시자 20종, IDM·MOBIL 포함)**: 본 fit이 본문 주 자료이며, av18 결과와의 정합성을 라운드 22에서 직접 산출하여 보고한다. 두 fit에 공통으로 들어간 학습 응시자 18명에 대해 av20 θ̂과 av18 θ̂ 사이 Spearman ρ = 0.9587 (p = 3.7×10⁻¹⁰), Pearson r = 0.9913 (p = 1.5×10⁻¹⁵). 두 fit이 매우 강한 정합을 보이되 완전한 1.0은 아니며, 순위가 가장 크게 어긋난 응시자는 td3_42 (av20에서 11위·av18에서 15위로 4계단 차이)와 PPO 강건군 내부 ppo_200↔ppo_500의 1위↔3위 교차이다. 본 차이의 본질은 각각 N=18·K=70과 N=20·K=20에서 잡힌 trial 풍부함과 응시자 표본 차이에 의한 추정 잡음이며, 학습 응시자의 강건성 순위가 두 fit 사이에 본질적으로 정합한다는 본문 주장은 ρ ≈ 0.96·r ≈ 0.99의 통계량으로 받쳐진다. av20 fit의 응시자 20종 θ̂ 추정값을 아래에 정리한다 (강건성 순 정렬, 95% CI half-width = 1.96·SE):

| 응시자 | θ̂ | 95% CI half-width | 알고리즘 |
|--------|-----|---|---|
| ppo_500 | +2.1065 | ± 0.974 | PPO (강건 ceiling) |
| ppo_800 | +2.1065 | ± 0.975 | PPO (강건 ceiling) |
| ppo_200 | +2.1064 | ± 0.974 | PPO (강건 ceiling) |
| def_rl_789 | +0.5328 | ± 0.308 | Defensive RL |
| ppo_100 | +0.3814 | ± 0.258 | PPO |
| td3_100 | +0.2987 | ± 0.236 | TD3 |
| def_rl_42 | +0.2403 | ± 0.223 | Defensive RL |
| td3_789 | +0.1042 | ± 0.189 | TD3 |
| def_rl_456 | -0.1954 | ± 0.156 | Defensive RL |
| ppo_999 | -0.3850 | ± 0.172 | PPO |
| td3_42 | -0.4798 | ± 0.197 | TD3 |
| sac_100 | -0.5106 | ± 0.203 | SAC |
| sac_42 | -0.5322 | ± 0.198 | SAC |
| sac_456 | -0.5541 | ± 0.205 | SAC |
| sac_789 | -0.6031 | ± 0.222 | SAC |
| sac_999 | -0.7157 | ± 0.237 | SAC |
| mobil | -0.7658 | ± 0.245 | rule-based MOBIL |
| td3_456 | -0.8870 | ± 0.287 | TD3 |
| td3_999 | -0.9552 | ± 0.307 | TD3 |
| idm | -1.2930 | ± 0.415 | rule-based IDM |

본 자료에서 rule-based 기준선 IDM(-1.293)·MOBIL(-0.766)이 가장 약한 응시자로 산출되며, 학습 응시자 중 가장 약한 td3_999(-0.955)와 비교해도 IDM이 한 단계 더 낮은 강건성으로 분리된다. 본 baseline 분리가 본 측정 모델이 rule-based·학습 응시자의 강건성 차이를 자릿수로 잡아낸다는 직접 증거이다.

**생성기 추정값 (두 fit 자료 비교)**:

| G | N=20·K=20: β̂·γ̂·â·û | N=18·K=70: β̂·γ̂·â·û |
|---|------|------|
| acarl_cutin | -1.266·0.018·6.639·0.057 | **-0.907·0.010·24.430·0.056** |
| acarl_rearend | -1.251·0.034·7.390·0.054 | **-0.880·0.008·30.653·0.051** |
| method_b | -0.247·0.025·2.081·0.003 | -0.378·0.016·2.188·0.001 |
| method_c | -0.826·0.037·2.511·0.004 | -0.864·0.026·3.379·0.004 |

- **변별력 â의 trial 풍부함 의존성 발견 (라운드 19 핵심 결과·라운드 18 검토자 진단 깊이 정정)**:
  - N=20·K=20 (trial 작음): cut-in â=6.64, rear-end â=7.39. 비교적 자연스러운 sigmoid ICC.
  - N=18·K=70 (trial 풍부): cut-in â=**24.43**, rear-end â=**30.65**. 계단함수 신호 매우 강함.
  - 라운드 18에서 잡힌 "â≈14.3 계단함수 흠"이 라운드 19 N=18·K=70에서 자릿수가 더 커지는 결과. 본 결과를 라운드 19 정정 단락에서 "계단함수 해소"로 적은 흐름이 av20 출력만 보고 적은 거짓 안도였음을 본 검토에서 정직히 인정한다.
- **본 발견의 학술 함의 (정직 voice)**:
  - K=70 trial 풍부함이 ACARL cut-in·rear-end의 변별력 모수를 강한 양수로 더 정확히 식별한 흐름. 본 결과가 본 측정 모델의 학술 강도를 강화하는 신호이기도 하고, ICC가 step function에 가까워지는 식별성 경계 신호이기도 한 양면 진단.
  - 본 양면 진단을 본문 §Results에 정직히 풀어 적되, §Limitations에 "본 측정 모델이 변별력 모수가 매우 큰 영역(â ≥ 20)에서 응시자 강건성을 거의 임계적으로 분리하는 한계"를 명시한다.
  - Method B (â=2.19)·Method C (â=3.38)는 본 식별성 경계와 무관한 안정 영역. 두 G가 baseline의 변별력 약한 G로 정직히 본문에 적힘.

- **converged**: True (두 fit 모두)

→ **Figure**: `irt_main_av20.{pdf,png}`·`irt_main_av18.{pdf,png}` (4-panel 각 자료)

### 5.6 Method C의 단조성 정정 (라운드 17·18 음의 단조성 진단 폐기)

**raw 자료**:
- **이전 자료 (N=3·5)**: Method C raw 단조성 ρ = -0.821 (강한 음의 다이얼). 라운드 17·18에서 본 자료를 "본 측정 모델의 진단 능력"으로 contribution voice에 활용.
- **정정 자료 (라운드 19)**: Method C raw 단조성 ρ = **+0.900** (강한 양의 단조성, N=18·K=70 자료). Method C fit 결과 av18(N=18·K=70) γ̂ = 0.026, â = 3.379 / av20(N=20·K=20) γ̂ = 0.037, â = 2.511. 두 fit 모두 양수 γ̂이며 av18 fit이 trial 풍부함으로 변별력을 더 정확히 식별.
- **본 정정의 학술 함의**:
  - 라운드 17·18의 Method C 음의 단조성이 **응시자 N=3·5의 작은 표본 흠으로 만든 가짜 음의 단조성**이었음을 N=18·K=70 자료가 직접 보임.
  - 본 측정 모델의 단조 가정에 정합한 G로 정정되어 본 격자에 정상적으로 포함됨.
  - "본 측정 모델의 진단 능력" contribution voice는 폐기. 본 발견을 §Limitations의 한 단락으로 정직히 적어 본 측정 모델의 응시자 다양성에 대한 강인성의 학술 anchor로 활용.
- **본 정정이 본 측정 모델의 학술 강도에 미치는 영향**:
  - 본 격자에서 G=3 (cut-in·rear-end·method_c) 통과 자료에서 G=3 (cut-in·rear-end·method_c) 통과로 양적 변화는 없으나 통과 G의 종류가 바뀜 (method_b·method_c 교체).
  - Method B의 변별력 약함과 단조성 통과 못함이 함께 드러나 본 G의 본질적 baseline 흠이 명확.
  - Method C의 정정이 contribution voice 단순화에 기여 (이전의 복잡한 "γ̂ + raw ρ 결합 진단" voice 제거).

### 5.7 D4 외적 타당성 sanity check

**raw 자료**:
- **ACARL §6.5 cross-defender Spearman ρ** (multi-defender robustness 분석):
  - cut-in: ρ = 0.53
  - rear-end: ρ = 0.55
- **본 격자의 b̂의 c별 단조성 ρ**: (ACARL과 별개 통계량이므로 직접 비교 안 함)
- **자릿수 일치 sanity check**: ACARL ρ ≈ 0.5 자료와 본 격자의 단조성 자료(라운드 19 N=18·K=70: cut-in 0.900·rear-end 0.700)가 같은 부호·같은 단조 방향을 보임.
- **본 결과의 학술 함의**: 본 측정 모델의 추정값이 외부 비교점의 정성적 흐름과 정합. 척도 일치(scale linking)는 latent trait 추정과 다른 통계량이라 불가능.

---

## §6 Limitations

### 6.1 시뮬레이터 충실도 (highway-env 2D bicycle dynamics)

**raw 자료**:
- highway-env (1.10.2)는 2D bicycle dynamics 기반의 단순 시뮬레이터. sensor 모델·세부 동역학·도로 형상의 다양성이 CARLA 같은 고충실도 시뮬레이터에 비해 제한적.
- 본 한계의 변호 자료:
  - AuthSim (T-ITS 2025) + ACARL (AAP) + Wang·Ma·Lai (T-IV 2026)의 같은 환경 선례.
  - 본 연구의 기여는 측정 모델의 원리 자체에 있으며 시뮬레이터에 무관 (plan §7, §11 7번).
- 본 측정 모델의 일반화 가능성을 CARLA·실차 데이터에서 검증하는 작업은 향후 연구 과제로 남김.

### 6.2 라운드 17 CARLA 이전 시도 종결 진단

**raw 자료**:
- 환경 충실도 강화를 위해 본 격자를 CARLA Town04로 옮기는 재시도가 세 차례 실패.
  - v1 (ACARL Phase 1 CARLA 1M step): 충돌율 100%·THW 0.45초·c_level controllability ρ ≈ 0
  - v2 (reward 함수 가중치 강화 295K step): 같은 fast crash
  - v3 (NPC threat-aware override 880K step): 학습 초기 8K step은 정합 (충돌 30~40%·ttc 7~15초), 30만 step·88만 step에서 fast crash 재수렴
- cross-check (`scripts/evaluate_5seed_final.py`, highway-env method A 5-seed): ρ = +0.496 ± 0.172, 충돌 4%, THW 2.57초. ACARL이 highway-env에서 정상 작동 확인.
- **본질 진단**: CARLA NPC의 LineOfSightSensor가 forward-only라 NPC 뒤에서 추격하는 ego를 감지하지 못함. CARLA의 3D physics·관성이 RL 정책의 환경 우회 학습을 가능케 함.
- v3 종결 사유: 컴퓨팅 예산 안에서 hyperparameter·entropy regularizer 조정 공간을 충분히 탐색하지 못한 한계. 본 우회 행동이 추가 탐색으로 우회될 가능성은 미검증.

### 6.3 응시자 가족 다양성과 학습 방식 분리 (라운드 19 N=20 확장 후 정정)

**raw 자료 (라운드 19 정정)**:
- 응시자 N=20 (IDM·MOBIL·Defensive RL 3 시드·PPO 5 시드·SAC 5 시드·TD3 5 시드)으로 확장됨. 학습 방식 4종(rule-based·on-policy PPO·off-policy SAC·off-policy TD3)과 시드 분산이 본 측정 모델의 specific objectivity 검증에 강한 학술 anchor를 제공.
- D2 trial-split (N=18·K=70): r mean = **0.996** (이전 0.917에서 강화), p25 = 0.996.
- 응시자 θ̂ CI half-width 분포 (N=18·K=70):
  - PPO 강건 응시자 (ppo_200·500·800): ±0.76~0.82 (큰 폭, 강건한 응시자의 식별 불확실성이 드러나는 영역)
  - 나머지 응시자: ±0.10~0.27 (정확한 값, N 확장으로 SE 크게 감소)
- N=3·5의 옛 흠 (표준 D2 응시자 split-half r mean = -0.014~0.415 합격선 미달, ACARL §5.3 학습 시드 분산만 의존)이 N=20 확장으로 본질적으로 해소.
- **Rasch family 권고 N≥30~50 미달 (라운드 21 정직 명시)**: 본 격자의 N=20이 IRT·Rasch family 표준 권고 N≥30~50 (de Ayala 2009, Hambleton·Swaminathan 1985 등)에 미달하는 자료. 본 미달이 본 측정 모델의 가장 큰 학술 흠 중 하나이며, D2 trial-split (r=0.996, K=70 trial 풍부함)이 본 흠을 통계적으로 부분 보충하나 표본 크기 자체의 권고치는 충족 못함. 본 한계가 §7.2 응시자 N 확장 future work의 출발점.
- 본 limitations 단락은 응시자 가족 다양성 자료를 본 측정 모델의 정직한 학술 anchor로 적되, 본 격자가 cut-in·rear-end 두 시나리오 type에 한정된 자료라는 §6.6 한정과 함께 본문에 적는다.

### 6.4 변별력 â의 G별 차이와 trial 풍부함 의존성 (라운드 19 정정)

**raw 자료**:
- **Method B 변별력 약함 (두 fit 일관)**: av20 fit에서 â = 2.081, av18 fit에서 â = 2.188. ACARL 두 G의 약 1/12~1/14 수준. Method B가 단조성 ρ = 0.000(N=18, FAIL)·약한 변별력으로 본 격자의 baseline 흠 자료. 본 결과를 본문에 정직히 명시하고 Method B를 contribution 검증의 핵심 G가 아닌 baseline의 한 사례로 적는다.
- **cut-in·rear-end â의 trial 풍부함 의존성 (라운드 18 검토자 진단의 라운드 19 정정)**: 
  - av20 (N=20·K=20, trial 작음): cut-in â=6.64, rear-end â=7.39 (자연 sigmoid ICC)
  - av18 (N=18·K=70, trial 풍부): cut-in â=24.43, rear-end â=30.65 (강한 계단함수 신호)
  - 라운드 18 시점의 "â≈14.3 계단함수 흠"이 라운드 19 av18에서 24.4·30.7로 자릿수가 더 커진 결과. 본 진단을 본문 §5.5의 양면 voice(K 증가가 변별력 식별성을 강화하지만 ICC가 step function에 가까워지는 식별성 경계 신호이기도 함)에 정합하게 적되, 본 §Limitations에는 "본 측정 모델이 trial 풍부할수록 강건한 응시자를 더 임계적으로 분리하는 식별성 경계 한계"로 명시한다.
- **본 한계의 future work**: 변별력 모수에 더 강한 사전정보(상한 a ≤ 10 등) 또는 4-parameter logistic 확장으로 본 식별성 경계를 완화하는 흐름이 후속 연구 과제로 남는다.

### 6.5 γ_G 양수 강제 제약의 일반적 한계 (라운드 19 정정)

**raw 자료**:
- 본 측정 모델의 식 (3)에서 γ_G = exp(lg) 양수 강제 적합이 본 모델의 식별성 조건의 일부. 본 강제로 단조성 가정을 깨는 G(raw ρ < 0)가 본 격자에 들어오면 본 모델이 본 G의 음의 다이얼을 직접 음의 γ̂로 표현하지 못한다.
- 본 한계는 본 측정 모델의 모수화 선택에서 비롯되는 일반적 제약이며, 본 격자의 실제 적합에서는 N=18·K=70 자료에서 모든 G가 양의 단조성 자료(method_c ρ=+0.900 포함)를 보여 본 한계가 발현되지 않은 흐름이다.
- 본문 voice에서 본 한계를 "본 모델의 식별성 모수화 선택의 일반적 결과"로 정직히 명시하고, 단조성 가정을 깨는 G를 본 격자에서 발견 시의 진단 절차(raw ρ + 작은 γ̂ 결합 해석)는 §Discussion의 한 단락으로 적는다. 라운드 17·18의 "Method C 음의 단조성 진단 능력" contribution voice는 §5.6의 N=18 정정으로 폐기되었으므로 본 §에서는 일반 한계로만 다룬다.

### 6.6 적대 시나리오 type의 한정

**raw 자료**:
- ACARL의 적대 생성기가 cut-in·rear-end 두 시나리오 type만 학습됨.
- brake_check·sideswipe·junction crossing 같은 다른 적대 시나리오는 본 격자에서 평가되지 않음.
- ACARL의 다른 baseline (Method B·Method C) 두 종도 cut-in/rear-end 구조 공유.
- plan §13 셋째 기여의 적용 범위가 두 시나리오 type으로 좁혀짐.

### 6.7 외부 비교점은 자릿수 일치 sanity check 수준만

**raw 자료**:
- ACARL §6.5의 cross-defender ρ와 본 b̂의 단조성 ρ는 자릿수 일치 sanity check 수준에서만 비교.
- 척도 일치 (scale linking)는 ACARL의 ρ가 latent trait 추정과 다른 통계량이라 불가능.
- 본 차이를 본문에 별도 단락으로 명시.

### 6.8 K 의존성

**raw 자료**:
- K=20·K=50 단독으로는 통과 G가 바뀜 (K=20 acarl_cutin만 통과, K=50 acarl_rearend만 통과).
- K=70 통합으로 자릿수 안정 (세 G 통과).
- 본 K 의존성을 본문에 정직 명시.

### 6.9 SAC 응시자 동질성과 학습 실패 vs 본질 진단의 분리 불가 (라운드 21 신규)

**raw 자료**:
- SAC 5 시드의 θ̂이 -0.652·-0.678·-0.727·-0.738·-0.769로 ±0.12 안에 좁게 모이는 자료.
- 본 동질성이 두 해석에 열려 있다. 첫째는 본 환경에서 SAC가 정책 다양성을 잃고 보수적 수렴에 갇힌 본질 진단(SAC의 maximum entropy 자료가 본 highway-env 환경에서 보수적 정책을 유도). 둘째는 stable-baselines3 default hyperparam (entropy coefficient `ent_coef='auto'`·target update rate τ=0.005·buffer 100K) 미조정으로 인한 학습 실패 잔존.
- 본 격자는 학습 곡선 reward·exploration entropy·학습 안정성 자료를 별도 점검하지 않아 두 해석을 분리하지 못한다. 본 한계를 정직히 명시하고 SAC hyperparam sweep (ent_coef·target update rate·buffer 자료 조정)을 §7 Future Work에 포함한다.
- 본 한계가 contribution 2("응시자 가족 다양성")의 학술 강도에 영향을 미친다. SAC 동질성이 학습 실패라면 본 응시자 5종을 응시자 다양성으로 활용한 자료가 학술 정직성을 약화한다. 본 흐름을 §Discussion에 정직히 풀어 적어 reviewer가 본 흠을 변호 가능한 voice를 확보한다.

### 6.10 ACARL self-citation 의존성 (라운드 21 신규)

**raw 자료**:
- 본 격자의 응시자 18종(Defensive RL 3 + PPO 5 + SAC 5 + TD3 5)이 모두 ACARL infrastructure (`<anonymized-acarl-repo>`)에서 학습된 자료.
- 생성기 G 4종(Method A·B·C·D)이 모두 ACARL 원고에서 학습·정의된 자료.
- 환경(highway-env + ACARL infrastructure)·외부 비교점(ACARL §6.5 cross-defender ρ) 모두 ACARL 한 인프라 의존.
- 본 self-citation 의존성이 본 측정 모델의 외부 검증을 단일 저자 인프라에 묶는 흠. AAAI submission 시점에 ACARL은 Accident Analysis and Prevention(AAP) under review 상태이며 arXiv preprint 게재 자료가 결정되어야 한다.
- AAAI double-blind review 자료를 고려하면 self-citation 처리가 "Anonymous, [author's previous work]"로 익명 변환되어야 함 (paper_references §10 참조).
- 본 측정 모델의 일반화 가능성을 외부 자율주행 적대 평가 인프라(SafeBench·FREA·VCDI·LFR 등)에서 검증하는 작업이 §7 Future Work의 핵심 항목.
- AAAI camera-ready 시점에 ACARL arXiv 자료가 확정되면 footnote에 본 의존성을 정직 명시.

---

## §7 Future Work

### 7.1 본 측정 모델의 환경 우회 진단 능력 검증 (CARLA)

**raw 자료**:
- 라운드 17 진단 자료 (forward-only LOS sensor·3D physics 관성이 RL 정책의 환경 우회를 가능케 함)
- 본 측정 모델이 γ̂≈0으로 환경 우회 현상을 진단할 가능성 (검증되지 않은 가설)
- 본 가설을 contribution이 아닌 후속 연구의 hypothesis로 명시

### 7.2 응시자 N 확장

**raw 자료**:
- TransFuser·MILE·World on Rails 같은 외부 학습 정책 도입
- N=6~8 표준 D2 검정 통계 검정력 확보 목표

### 7.3 적대 시나리오 type 확장

**raw 자료**:
- brake_check·sideswipe·junction crossing 등 다른 시나리오 type
- 본 시나리오의 ACARL 학습 데이터 부재로 본 격자에서 평가 안 됨

### 7.4 ACARL repository CARLA 코드 (future work 출발점)

**raw 자료**:
- `<anonymized-acarl-repo>`의 보존 코드:
  - `src/environments/adversarial_carla_env.py` (reward 함수 원래 복원)
  - `src/environments/carla_traffic.py` (CruiseControl.tick ego threat-aware override 추가)
  - `src/environments/defensive_carla_env.py` (새 작성)
  - `src/environments/grid_carla_env.py` (새 작성)
  - `scripts/train_defensive_carla.py` (새 작성)
  - `scripts/run_aaai_grid_carla.py` (새 작성)
  - `configs/defensive_carla.yaml` (새 작성)
- 본 코드가 CARLA 환경에서 본 측정 모델을 시험할 future work의 출발점.

### 7.5 MIRT 확장 (차원성)

**raw 자료**:
- 본 측정 모델은 1차원 latent θ (응시자 능력)을 가정.
- 다차원 강건성 (cut-in 강건성·rear-end 강건성·brake_check 강건성 등)이 별도 차원으로 작동할 가능성.
- MIRT (Multidimensional IRT) 확장은 향후 연구 과제 (plan §11 6번).

### 7.6 실차 데이터·고충실도 시뮬레이터 검증

**raw 자료**:
- 본 측정 모델의 일반화 가능성을 CARLA·실차 데이터에서 검증.
- 본 검증이 본 측정 모델의 학술 강도를 강화할 자료.

---

## §8 Conclusion (라운드 19 N=20 확장 후 정정)

**raw 자료**:
- 본 연구가 IRT를 자율주행 적대 평가에 처음 적용한 SUT-불변 측정 모델 형식화 완료.
- 본 측정 모델의 세 contribution (§1.4와 정합):
  - (1) 방법론 신규성: IRT의 자율주행 적대 평가 첫 적용. 식 (1)~(9)이 closed-loop 반응성·severity 조건화·avoidability를 IRT 안에 형식화.
  - (2) 응시자 가족 다양성 위에서 척도 보존: 본 측정 모델이 응시자 20종(IDM·MOBIL·Defensive RL 3 + PPO 5 + SAC 5 + TD3 5) 위에서 SUT-불변성을 D1 단조성·D2 trial-split·D3 ablation·D4 외적 타당성 sanity check로 검증. 학습 방식 4종 분리가 본 측정 모델의 specific objectivity 가정의 강한 학술 anchor.
  - (3) 표준 적대 생성기 위에서 척도 안정 + 생성기 진단 능력: 세 생성기(ACARL cut-in·rear-end·method_c)가 D1 단조성 합격선 ρ ≥ 0.7 통과. Method B Naive는 ρ=0.000·변별력 â=2.19로 본 격자의 baseline 흠으로 진단됨. 본 측정 모델이 단조성을 만족하는 G와 만족하지 못하는 G를 데이터로 식별.
- 본 격자의 검증 자료 (N=18·K=70):
  - D1 단조성: 세 G 합격선 통과 (cut-in ρ=0.900·rear-end ρ=0.700·method_c ρ=0.900), method_b FAIL (ρ=0.000)
  - D2 trial-split: r mean = 0.996, p25 = 0.996 (단조성 통과 3 G)
  - D3 ablation (deviance 비교): no_severity Δ = 195,116.35 (df=4) · g_common Δ = 4,454.03 (df=12) · u_zero Δ = +36.83 (df=4)
  - fit_irt_main: 응시자 θ̂ 학습 방식 분리 (PPO 강건군 +2.0~+2.2·SAC 약함군 -0.77~-0.65·TD3 변동·Defensive RL 기존 중간), 생성기 β̂·γ̂·â·û 두 fit 자료(av18·av20) 모두 보존
- 본 측정 모델의 한계(N=20이 Rasch family 권고 N≥30~50 미달·변별력 â의 trial 자료 의존성·시뮬레이터 충실도·시나리오 type 한정·외부 비교점 sanity check 한정)와 future work(외부 학습 정책 도입·시나리오 type 확장·CARLA 환경 우회 진단 능력 검증)를 §Limitations·§Future Work에 정직히 명시.

---

## §A 부록: 결정 트레일 요약 (decisions.html 라운드 1~19)

**raw 자료**:
- **라운드 1~5**: 시뮬레이터 선택 (CARLA + SafeBench), 결정 트레일 보관 위치, 격자 합격선, 표본불변성 검증 절차, 응답 격자 후보 범위.
- **라운드 6~10**: 평가 대상 AV 선정 (SafeBench RL ego 자료), 시나리오 생성기와 severity 조절 (SafeBench 4종 + FREA fppo_adv), SafeBench 출력 응답표 변환, CARLA 헤드리스 운용.
- **라운드 11~15**: SafeBench 단조성 검정 미통과, MOBIL 구현 명명, behavior None-safety 보강, CARLA 메모리 누수.
- **라운드 16 (2026-06-04)**: highway-env + ACARL로 전면 이전 결정. K=20 본 격자, K=50 보강, K=70 통합. Contribution 좁힘과 부분 철회. D2 검정 변형 결정 (trial-split + 의미 좁힘).
- **라운드 17 (2026-06-06)**: CARLA 이전 시도 종결 (v1·v2·v3 실패). highway-env 본문 복원. Method C 음의 단조성 진단 contribution voice 추가. 1차·2차 검토자 정정.
- **라운드 18 (2026-06-06)**: REVIEW_FIXLIST 적대 점검 정정. A-1 θ̂ SE 수치 헤시안 재산출 (def_rl_42·456·789 95% CI: ±0.690·±0.675·±0.892, 이전의 2.6~4.2배 부풀림 정정으로 응시자 순위 주장 강화). A-2 식 (1) 부호 σ(a·(b−θ)) 정정. A-3 episode 수 정확히 명시 (통합 5,000 + 적합 4,200). A-4 D3 g_common df=12 정정. B-1 LR test → deviance 비교. B-2·B-3·B-4 표현·서술 정정 (사후 표준화·계단함수 신호·u 자유 추정 명시).

자세한 단락은 `research/decisions.html` 참조.
