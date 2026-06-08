# AAAI 논문 연구 정리: AV 적대 평가의 SUT-불변 측정

*이 문서는 지금까지의 연구 상태와 초안을 한곳에 정리한 참고 문서다. 작업 지시나 할 일 목록은 포함하지 않는다. 본문(Intro 초안 등)에는 국문 학술 문체 규칙을 적용했다: 서론은 소절 없이 단일 흐름, 끝에 RQ 번호, em-dash 금지, 직역체·명사 나열 회피, 기술용어는 영어 병기.*

---

## 0. 한 줄 포지셔닝

LLM 평가에서 검증된 측정이론(IRT)을, 평가의 SUT 의존성이 알려진 문제인 자율주행 적대 평가에 처음으로 가져온다. 시나리오·생성기의 난이도와 AV의 강건성을 하나의 공통 척도 위에 올리고, severity 조건화와 avoidability 가중이라는 주행 고유의 구조로 다룬다.

---

## 1. 연구 개요 (확정)

적대적 주행 시나리오로 AV를 평가할 때, 충돌률 기반 비교가 어떤 SUT(AV/planner)로 측정했느냐에 따라 흔들리는 문제를 푼다. 측정이론(Item Response Theory, IRT 계열)을 가져와 시나리오·생성기 난이도와 AV 강건성을 SUT-불변(누가 측정하든 안 흔들리는) 공통 척도에 올린다.

이 논문의 주인공은 **측정 모델**(흔들리지 않는 평가를 만드는 방법)이다. 생성기는 그 모델을 검증하기 위한 재료(조연)다.

설명용 비유:
- 시험문제 = 시나리오 / 생성기
- 수험생 = AV 정책
- 오답 = 충돌
- 문제 난이도 = 시나리오의 진짜 위험도
- 수험생 실력 = AV의 진짜 강건성

타깃 학회는 AAAI 메인 트랙이다. 따라서 셀링포인트는 시뮬레이터·실험이 아니라 방법론/이론 신규성이어야 한다. 측정에 관한 얘기라 저충실도 시뮬레이터(예: highway-env)를 써도 reviewer가 시뮬레이터를 트집 잡기 어렵다는 것이 이 주제의 장점이다. 컴퓨팅 자원 제약은 없다(클라우드).

---

## 2. 신규성 (두 겹)

- **얕은 겹**: IRT/측정이론을 AV 적대 평가에 처음 적용. 이것만으로는 "응용 논문"으로 분류될 위험이 있다(AAAI 메인엔 경계선).
- **깊은 겹 (메인 트랙급으로 끌어올리는 핵심)**: 시험용 IRT가 가정하는 것(문항 고정, 1회 응시, 1차원 능력)이 AV 적대 평가에선 모두 성립하지 않는다. 이를 새 측정 모델로 형식화한다.
  1. **reactivity(반응성)**: 시나리오/생성기가 AV 행동에 반응(closed-loop). 시험 문항은 가만히 있다.
  2. **severity-conditioning(severity 조건화)**: 같은 생성기로 난이도를 연속 조절(c_level 같은 dial). 강건성 곡선을 모델링한다.
  3. **avoidability-weighting(avoidability 가중)**: 충돌엔 회피가능(시스템 결함)과 회피불가(누구도 못 피함)가 섞여 있다. 회피가능 충돌만 강건성에 반영한다.

---

## 3. 현재 작업 결정 (working decisions, 아직 최종 확정 전)

- **깊은 겹의 무게중심**: severity 조건화를 주축으로, avoidability 가중을 보조로, reactivity를 전제(틀)로 배치한다. 셋을 다 형식화하되 무게중심은 severity. 근거: c_level 경험이 있어 자연스럽고, 시험 IRT에 가장 분명히 없는 구조라는 점.
- **차원성 경계**: 단순 1차원 IRT는 SUT×시나리오 교차역전(Shen)에 취약하므로, 불변성 주장을 하나의 생성기 severity sweep(= 일관된 시나리오 family) 안으로 한정한다. family 사이의 다차원성은 본 연구의 경계로 명시한다(필요 시 MIRT).

---

## 4. 생성기 방침 (확정, 2026-06-06 라운드 17 정정)

**옛 결정(2026-06-02)**: ACARL은 재활용하지 않고, 새로 일부러 단순하게 만든다(IDM/MOBIL 기반 + 공격성 다른 몇 종 + severity 조절 가능한 1종). 측정 모델이 주인공이라 생성기는 평범·표준적인 것이 좋고, ACARL은 별도 심사 중(AAP)이라 재활용 시 생성기 논문처럼 메시지가 흐려질 위험을 회피하는 결정.

**2026-06-04 라운드 16 정정**: SafeBench의 IDM·MOBIL 단순 표준 생성기 직접 구현 시도(라운드 12) + CARLA + SafeBench 격자 환경(라운드 13~15)이 단조성 검정 미통과와 CARLA 학습 흠으로 매몰 비용 처리되었다. 본 시점의 격자는 highway-env + ACARL 인프라로 이전되었으며, 적대 생성기는 ACARL의 cut-in·rear-end 두 시나리오 type 정책(Method A)과 baseline 두 종(Method B Naive, Method C Rule-based AuthSim 구조) 네 종으로 구성된다. ACARL은 별도 출판(AAP 타겟)을 위해 arXiv에 preprint를 게재한 후 본 AAAI 논문에서 인용하며, 본 측정 모델의 SUT-불변성은 ACARL과 baseline 두 종을 포함한 적대 생성기 가족 위에서 검증된다는 흐름으로 본문 메시지를 정리한다.

**Contribution 좁힘과 부분 철회 (라운드 16 단조성 결과 + K=70 통합 + 라운드 17 추정값 정정)**: K=20 본 격자에서 acarl_cutin만 단조성 합격선 ρ ≥ 0.7을 통과(ρ=0.821, 응시자 5종 기준; ρ=0.900, Defensive RL 세 시드 기준)하여 contribution을 단일 시나리오 type(cut-in)으로 좁히는 결정을 한 차례 적었다. 그 후 K=50 보강 격자(3,000 episode)를 굴리고 K=20 + K=50을 통합한 자료(cell당 70 episode)로 다시 점검한 결과 세 생성기가 합격선을 통과하였다: acarl_cutin ρ=0.821, acarl_rearend ρ=0.700, method_b ρ=0.700. 본 통합 결과는 K=20·K=50 단독으로는 통과 G가 바뀌는 자료(K=20 acarl_cutin만 통과, K=50 acarl_rearend만 통과)가 K=70에서 안정되는 흐름이며, ACARL 원고 §6.2의 rear-end ρ=0.260 ± 0.484 큰 분산이 K 보강으로 안정된 결과이다. 본 결과에 따라 plan §13 셋째 기여를 "본 격자에서 검증된 표준 단순 생성기 묶음(ACARL cut-in·rear-end + baseline Method B Naive) 위에서 척도가 안정"으로 본문에 적되, Method C(Rule-based AuthSim 구조)는 단조 방향이 반대로 작동하는 흠을 본문 한계로 정직히 기술한다. K 의존성(K=20·K=50 단독 자릿수 변동, K=70 통합 안정)도 본문 Limitations에 명시한다. §11 6번 단락의 차원성 방어 순서는 본 결과에서도 정합한 흐름으로 유지된다.

**2026-06-06 라운드 17 추정값 정정 (Method C γ̂ 음수 표현 불가 → 작은 γ̂ + raw ρ 부호 결합 진단)**: fit_irt_main의 직접 적합 결과 Method C의 γ̂ = 0.025(다른 G 0.054~0.196의 약 1/2~1/8 수준), 변별력 â = 7.941(ACARL cut-in·rear-end 14.297·14.254의 약 절반), raw 단조성 ρ = -0.821이 산출되었다. 본 측정 모델이 γ_G = exp(lg) 양수 강제로 적합되어 음수 다이얼을 직접 음의 γ̂로 표현하지 못하므로, Method C의 음의 다이얼 진단은 "fit 결과의 작은 γ̂ + raw 데이터의 음의 단조성 ρ"의 결합 신호로 본문에 풀어 적는다. 본 진단 능력이 본 측정 모델의 contribution voice의 한 갈래로 활용되며, 본 voice는 "본 측정 모델이 단조성 가정에 정합한 G(γ̂가 큰 양수·â가 강한 자료)와 단조성 가정을 깨는 G(γ̂가 작은 양수·â가 약한 자료)를 추정값의 자릿수 차이로 분리하고, raw 단조성 ρ가 음수인 G는 본 모델의 양수 강제 제약 안에서 작은 γ̂와 raw ρ의 부호 결합으로 본 격자의 학술 범위 밖으로 진단된다"로 §Results의 한 단락에 박힌다. 또한 Method B의 변별력 â = 0.561이 ACARL 두 G의 약 1/25 수준으로 매우 낮은 자료가 발견되어, 본 G가 단조성 ρ = 0.700으로 통과했지만 응시자 분리에서 약한 자료를 보인다는 점도 본문 §Limitations에 정직히 적는다. 응시자 θ̂의 95% CI가 ±1.808~3.776로 매우 넓은 자료(N=3의 작은 표본 효과)도 본문 §Limitations에 함께 명시된다.

**2026-06-06 라운드 17 정정 (CARLA 이전 시도 종결, highway-env G 4종 유지)**: 라운드 16의 highway-env G 4종 구성을 CARLA Town04로 옮기는 재시도(v1·v2·v3)가 모두 fast crash로 수렴하여 종결되었다. cross-check에서 highway-env의 동일 ACARL이 ρ=+0.496·충돌 4%로 정상 작동함이 확인되어 본 격자의 G 4종을 highway-env에 그대로 유지한다. 자세한 시도 흐름·본질 진단·본문 voice는 §12 6번 항목과 `research/decisions.html` #d06·#d07의 라운드 17 단락에 박혀 있다.

- 자원 제약이 없으므로 실험 규모(더 많은 AV × 생성기 × severity 격자)를 키워 empirical power를 높일 수 있다.

---

## 5. 경쟁/관련 논문 정리

### 5.1 Yang et al. 2024: "Quantitative Representation of Scenario Difficulty ... Adversarial Policy Search" (arXiv 2408.14000) (가장 가까운 경쟁, 무력화됨)

- 한 것: environment agent를 SAC로 학습, 학습 단계별로 에이전트를 뽑아 난이도(0~1)를 연속 조절하는 transformer 모델. 난이도 기준 = average reward per episode.
- 결정적 한계(= 우리 차별점): 그들의 난이도는 정의상 단일 고정 ego에 종속(식 θ\*=argmax F(πA,πE,Sc)에서 πA 고정; 실험 ego 하나). 난이도 ground-truth가 "학습을 얼마나 오래 했나(training step)"라는 순환적 정의. SUT-불변성을 보장하지 않고 오히려 SUT 종속의 전형.
- 관계: 그들=한 AV에 대해 난이도 조절 적대 에이전트 생성. 우리=여러 AV에 걸쳐 난이도·강건성을 불변 척도에 올려 측정. 다른 문제. 위협이 아니라 baseline/item 공급원으로 쓸 수 있다. Related work에서 정면으로 구분한다.

### 5.2 Fan et al. 2026: PMCT (Transportation Research Part C)

- 핵심: 기존 정량 안전지표(TTC/PET/DRAC 등)는 신뢰성에 형식적 보장이 없다(희귀사건이라 실패율 불확실). PAC 검증 + DRL로 증명가능한 충돌시간(PMCT) 제안.
- 쓰임: 주장 4(stakes), 기존 지표가 provable하지 않다는 권위 인용.
- 혼동 주의: PMCT는 자기 지표가 policy-agnostic이라 주장(TeraSim 실험, NADE로 인간행동 포괄). 하지만 이건 실시간 충돌시간 지표 층위이지, 생성기·시나리오 비교 층위가 아니다. ability/difficulty를 같은 척도에 안 올린다. Related work에서 한 줄 구분.
- 계보: Shuo Feng 그룹(Tsinghua). Feng Nature 2023(Dense RL), Feng Nat Comm 2021(intelligent driving test)의 다음 발걸음으로 포지셔닝 가능. PMCT의 PAC 신뢰구간 기법은 우리 신뢰구간 부분에 영감 가능.

### 5.3 Peng et al. 2026: LD-Scene (Transportation Research Part C)

- 핵심: LLM + latent diffusion으로 자연어 제어 가능한 적대 시나리오 생성(최신 SOTA). severity(weak/medium/strong) 제어, nuScenes.
- 주장 1·2 입증: Table 1의 우수성 지표가 Adv-Ego Coll(%) (LD-Scene 40.75%로 baseline 압도). severity 축이 TTC 기반.
- 주장 3 정량 입증 (Table 4, transferability): 같은 생성기를 4개 ego planner로 평가 → Adv-Ego 충돌률 Lane-Graph 40.75% / PDM-Closed 41.36% / IL 62.88% / IL-Multi 60.94%. 같은 생성기인데 ego 바꾸면 약 41%→63%로 출렁. 저자는 transferability(긍정)로 해석하지만 우리 관점에선 SUT 의존성의 직접 증거. 남의 SOTA 논문 자신의 데이터라 반박이 어렵다.
- avoidability 동기 (4.9절): 저자가 ego planner 잘못이 아닌 충돌(급가속 추돌, 멈춘 ego에 정면충돌)을 인정. future work로 세밀한 충돌 분류와 귀책(attribution) 분석을 꼽음.
- 경쟁 아님: LD-Scene은 생성기, 우리는 측정. 동기 3기둥을 자기 데이터로 보여주는 논문이자 실험 재료.

### 5.4 Liao et al. 2025: ADS testing 서베이 (Information and Software Technology)

- 핵심: 100명 설문 + 105편 리뷰, 7개 demand.
- 쓰임: 주장 4(stakes)의 가장 강한 근거. Demand 3 "더 포괄적인 평가 기준"이 정확히 우리 문제의식.
  - 참가자 30.14%가 "포괄적 평가 기준 부재"를 demand로 꼽음(특히 system-level·E2E).
  - 실무자 발언: 충돌률이 낮은 ADS는 너무 보수적으로 운전(잦은 급제동)해서일 수 있고 이는 추돌을 유발 → 좋은 지표가 좋은 주행을 뜻하지 않는다.
  - system-level testing은 어디가 틀렸는지 짚기 어렵다(poor interpretability).
- 한계: 충돌률의 SUT 의존성(어떤 AV로 쟀느냐로 순위 바뀜)은 직접 안 다룬다. 그 구체적 주장은 Ponn/Qiu/Shen + 71.5% + LD-Scene Table 4 담당.

---

## 6. 업로드 3편 정밀 분석 (이번 세션 정독)

### 6.1 Ponn et al. 2020: 주장 3의 개념적 정의를 통째로 줌 (가장 직접적)

- criticality vs. challenging/complexity 구분이 핵심.
  - criticality = concrete scenario에서 ego의 성능 평가. 실행 후에만 측정 가능, 같은 concrete scenario라도 AV 함수가 다르면 결과가 달라진다(정의상 SUT-의존).
  - challenging/complex = scenario 자체 평가. 실행 전 결정, AV 성능과 무관.
- 초록 한 문장이 사실상 우리 동기 문장: 기존 지표는 대개 criticality 기반인데 test vehicle 행동에 의존하므로 좋은 테스트케이스를 사전에 고르는 데 부적합.
- 가장 강한 인용거리: highD 차량 1034 사례. 선행연구가 critical로 꼽았는데 Ponn의 SUT-독립 복잡도로 재면 0.37(중간)에 불과. 이유: 속도 ~20km/h, 회피 공간 충분. 시나리오 자체는 안 어려운데 그 시나리오를 주행한 인간 운전자의 대응이 나빠서 critical이 됨.
- 검증(Table I): 복잡도 최저/평균/최고 그룹에서 AV 유발 사고 2/13/22건, 임계 TTC 미만 2/7/9건. SUT-독립 속성이 SUT-의존 결과를 확률적으로 끌어올린다는, 우리 측정모델과 같은 구조.

과장 금지 / 공정 인용:
- Ponn은 우리 대안 해법이기도 하다. 그들의 SUT-독립 달성 방식은 결과를 안 보고 전문가 가중 Layer-4 속성(주변차 수·동역학·예측가능성·time-gap·occlusion 등 13개)으로 난이도를 정의하는 것. 측정모델이 아니라 hand-crafted open-loop 점수.
- Ponn 스스로 이 지표가 ego 행동과 완전히 독립은 아니라고 인정하고, 시나리오를 최고복잡도 순간에서 시작시켜 우회한다. 이 자백을 related work에서 쓸 수 있다(속성기반조차 완전한 SUT-불변을 못 줬다).

### 6.2 Qiu et al. 2026: 난이도가 SUT 성능으로 조작적 정의됨 (단, 조심해서)

- 난이도 ground-truth = 10개 참가팀의 서로 다른 알고리즘이 각 시나리오에서 받은 평균 점수. 즉 난이도 = 한 SUT 집단의 실패 정도로 조작적 정의. 91.3%는 물리기반 복잡도가 이 대회 알고리즘들에게 어려웠던 것과 일치한 비율.
- 복잡도 계산 자체가 고정 EV(독점 Lattice 플래너) 궤적에 의존(gravity model이 v_ego, a_ego 가·감속 분기, EV 속도변화, 상대거리 사용). EV를 바꾸면 점수가 바뀐다. 그런데 논문은 "고정 EV 알고리즘 하에서는 복잡도 차이가 시나리오 고유 구조에서만 나온다"고 못박는다(SUT 상대성의 자백). 난이도를 한 SUT 궤적으로 계산하고 다른 SUT 집단 성능으로 검증한다는 점에서 이중으로 SUT에 엮였다.
- 오분류 사례 Y_Test4: SDCMP "medium"(18.668) vs OnSite "easy"(93.64). 고정-EV 물리로 본 난이도와 알고리즘 성능으로 본 난이도의 불일치 = 둘 다 SUT 상대적이라는 직접 증거.

과장 금지:
- 8.7% 불일치(=100−91.3)를 전부 SUT 의존성으로 읽으면 안 된다. 임계값 효과, "medium" 범주가 원래 TPR 최저(저자도 인정), 측정노이즈가 섞임. 강한 인용은 개념적 포인트(난이도를 SUT 성능으로 정의했고 EV를 고정해야만 안정적)이지 8.7%라는 수치가 아니다.
- Qiu도 Ponn과 함께 baseline/대안 해법군(고정-EV 상호작용 복잡도).

### 6.3 Shen et al. 2025: 시나리오 고정·SUT만 변경 시 충돌률 출렁을 통제실험으로 증명 (가장 강한 정량 근거)

- 시나리오 유형·긴급도(THW, TTC)를 SUT 간 매칭(Table 4: Braking THW≈1.4s, Cut-in TTC≈1.22s, Merging TTC≈2.32s, L0~L4 거의 동일). 시나리오 난이도를 상수로 고정.
- 충돌률은 SUT(자동화 수준)만으로 12.6%(AMD) → 24.3%(L2) → 21.4%(L3) → 14.1%(L4). 매칭된 시나리오에서 거의 2배 차이(L2→L4 감소 10.2%, OR 0.51, p<0.001).
- 시나리오별 SUT 순위 역전(Fig 6a): Braking L2≈L3 ≫ L4(L4 9%), Merging L4 우위, Cut-in에선 L4가 오히려 최악. 단일 충돌률로는 SUT 순위는 물론 시나리오 난이도 순위조차 SUT에 따라 역전된다.
- 주장 4도 받침: L3는 충돌률 낮은데(21.4%) 중상 확률 최고(21.6%) → safety benefit이 L2(90%)≈L3(89%)로 같아짐. 충돌률과 부상심각도의 해리.

과장 금지 / 공정 인용:
- 시뮬레이터(SCANeR) + SAE 규격 rule-based AV stand-in 실험(산업 알고리즘 아님, 센서 무결 가정, 표본 편향). "통제된 시뮬레이터 증거"로 인용.
- Cut-in의 L4 역전 상당부분은 인간 운전자의 과신 → 낮은 개입률 + 긴 반응시간(1.03s) 때문(human-in-the-loop 고유 교란). 우리 SUT는 사람 개입 없는 AV 정책이므로 이 교란은 약하게 붙는다(오히려 더 깨끗함). 다만 capability만으로도 큰 격차(Braking L2 24% vs L4 9%)는 유효.

### 6.4 전략적 재구성: 세 논문 = SUT 의존성에 대한 세 가지 임시방편

세 편은 위협이 아니라 related work의 척추다. 셋 다 같은 병(난이도/비교가 어느 AV로 쟀느냐에 흔들림)을 앓고 각각 다르게 임시봉합한다.

| 논문 | SUT-불변을 얻는 방식 | 한계(우리 진입점) |
|---|---|---|
| Ponn | 결과를 버리고 전문가 가중 Layer-4 속성으로 난이도 정의(SUT 자체를 제거) | 결과정보 폐기 + 전문가 가중치 임의성, "완전 독립 아님" 자백 |
| Qiu | EV 하나를 고정하고 상호작용 복잡도를 "고유"라 선언 | "고유"가 고정 EV에 의존, ground-truth가 SUT집단 성능(순환) |
| Shen | 시나리오·긴급도를 SUT 간 매칭(통제실험) | 매칭은 비싸고 안 확장됨(모든 SUT를 동일 trigger로 재실행), 그래도 SUT×시나리오 역전 잔존 |
| 우리(IRT) | 다수 AV×시나리오 결과에서 item난이도·person능력을 동시 추정, 모수는 구성상 SUT-불변(specific objectivity) | (해당 없음) |

novelty pitch: 세 봉합이 다 부분적이다. Ponn은 결과를 버리고, Qiu는 SUT 하나에 묶이고, Shen은 매칭 재실행이 필요하다. 측정이론은 결과를 버리지 않고, 단일 SUT에 묶이지 않고, 매칭 없이 교차설계에서 불변 난이도와 능력을 분리 추정한다.

핵심 우위: IRT의 item 난이도는 보정표본의 능력분포에 불변이다(모형이 맞는 한). 즉 Qiu(고정 EV 의존)·생충돌률(AV 의존)과 달리 어떤 AV들로 재든 난이도 추정이 안 흔들린다. Ponn의 속성난이도도 표본불변이지만 결과 비검증·전문가가중·SUT누수가 있다. 따라서 IRT는 Ponn만큼(또는 그 이상) SUT-불변이면서 결과기반이고 불확실성까지 정량화한다.

---

## 7. 동기: 완성된 주장 3 (다섯 각도) + 펀치라인

주장 3(충돌·난이도의 SUT 의존성)을 다섯 각도가 받친다.
1. 개념적 정의: criticality는 SUT-의존 (Ponn, 명시적)
2. 통제실험: 시나리오·긴급도 고정, SUT만 바꿔도 충돌률 12.6→24.3% (Shen)
3. 순환적 난이도: 난이도를 SUT 성능으로 정의·고정 EV 필요 (Qiu)
4. 분산분해 defender 71.5% (본 저자 ACARL)
5. SOTA 생성기 자기 표의 전이성: ego 바꾸면 약 41→63% (LD-Scene Table 4)

동기 펀치라인 초안: 최신 SOTA 생성기는 ego를 바꾸면 충돌률이 약 41→63%로 달라지고(LD-Scene), 시나리오·긴급도를 통제한 실험조차 SUT만으로 충돌률이 2배 출렁이며(Shen), 난이도를 정량화하려는 시도는 한 SUT를 고정해야만 안정적이다(Qiu). 단일 SUT 충돌률은 생성기·시나리오의 불변 척도가 될 수 없으며, 이는 측정이론이 처음부터 풀려고 만들어진 문제다.

---

## 8. 동기 논증 6개 주장 + 근거 매핑

| # | 주장 | 받치는 근거 | 상태 |
|---|------|------------|------|
| 1 | 적대 시나리오 생성이 AV 테스트 핵심 도구가 됐고 폭증 | 서베이들 + LD-Scene 등 최신 생성 논문 | 확보 |
| 2 | 거의 보편적으로 충돌(률·빈도·근접)을 우수성 지표로 씀 | LD-Scene Table 1 (Adv-Ego Coll이 첫 지표) | 확보 |
| 3 | (심장) 충돌 기반 비교·난이도가 SUT에 흔들린다 | Ponn(개념) + Shen(통제실험) + Qiu(순환) + 71.5% + LD-Scene Table 4 | 확보 (다섯 각도) |
| 4 | (stakes) 흔들림이 해롭다 (regression 무효, 충돌률이 보수주행·boundary 못 잡음·provable 안 함) | Liao 2025 Demand 3 + Fan 2026 PMCT + Shen(충돌률·부상 해리) | 확보 |
| 5 | IRT는 SUT-불변 비교를 위해 설계됐고 LLM/분류기 평가서 검증됨 | agent psychometrics(2026), PSN-IRT, Fluid Benchmarking, β³-IRT | 확보 (정확 cite 정리 필요) |
| 6 | 시험용 IRT는 AV에 그대로 안 맞음 → 새 모델 필요 | 논증 (2절 깊은 겹) | 논증 |

---

## 9. 서론(Introduction) 초안 [국문 학술 문체, 단일 흐름]

적대적 시나리오 생성은 자율주행차(AV)의 안전성을 평가하는 핵심 도구로 정착하였다. 실제 도로 주행 데이터만으로는 충돌로 이어지는 위험 상황이 드물게 나타나므로, 최적화·강화학습·생성 모델로 위험 상황을 의도적으로 만들어내는 방법이 빠르게 늘고 있다 (Ding et al., 2023; Peng et al., 2026). 이때 생성기의 우수성과 시나리오의 난이도는 거의 예외 없이 충돌과 관련된 양으로 측정된다. 충돌률, 충돌 빈도, 근접도(TTC, THW)가 대표적이며, 최신 연구들도 adversarial collision rate를 첫 번째 우수성 지표로 보고한다 (Peng et al., 2026).

그러나 충돌을 기준으로 한 비교에는 근본적인 문제가 있다. 같은 시나리오나 생성기라도 어떤 AV로 측정하느냐에 따라 충돌률이 크게 달라진다. 충돌률은 시나리오의 난이도가 아니라, 시나리오와 평가 대상 시스템(System Under Test, SUT)이 만나서 만들어내는 결과를 측정한다. 생성기 A가 B보다 더 어렵다는 결론이 특정 AV에서만 성립하고 다른 AV에서는 뒤집힌다면, 그 비교는 생성기에 대한 안정적인 척도가 될 수 없다. 측정값이 어떤 AV로 쟀느냐에 따라 달라지는 이 문제를 이하에서 SUT 의존성이라 부른다.

SUT 의존성은 한두 사례의 예외가 아니라 서로 다른 연구에서 반복적으로 확인된다. Ponn et al. (2020)은 충돌과 위기를 기준으로 한 criticality가 정의상 test vehicle의 행동에 따라 달라지므로, 좋은 테스트 시나리오를 사전에 고르는 데 부적합하다고 지적한다. 같은 concrete 시나리오라도 평가하는 AV가 다르면 criticality 결과가 달라지기 때문이다. 실제로 선행 연구가 critical로 분류한 highD 시나리오 하나를 행동과 무관한 복잡도로 다시 평가하면 중간 수준에 불과하다. 시나리오 자체가 어려운 것이 아니라, 그 시나리오를 주행한 운전자의 대응이 나빴을 뿐이다. Shen et al. (2025)은 이를 통제된 실험으로 보여준다. 이들은 시나리오 유형과 긴급도(THW, TTC)를 자동화 수준 사이에서 거의 동일하게 맞춘 뒤 충돌률을 비교했는데, 시나리오 난이도를 사실상 상수로 고정했는데도 충돌률은 SUT만으로 12.6%에서 24.3%까지 약 두 배 차이가 났다. 더 나아가 시나리오 유형에 따라 SUT 사이의 순위마저 뒤집혔다. 어떤 시나리오에서 가장 안전하던 시스템이 다른 시나리오에서는 가장 위험했다.

난이도를 SUT와 무관하게 매기려는 최근 시도조차 같은 한계를 드러낸다. Qiu et al. (2026)은 알고리즘과 독립적인 시나리오 난이도를 주장하지만, 이를 얻는 방법은 하나의 EV 플래너를 고정하고 그 플래너의 궤적에서 복잡도를 계산하는 것이다. 게다가 이들이 사용한 난이도의 ground truth는 대회 참가 알고리즘들의 평균 성능이다. 결국 난이도가 한 SUT를 기준으로 정의되고, 또 다른 SUT 집단의 성능으로 검증된다. 한편 본 저자의 선행 연구에서는 충돌 결과의 분산이 어떤 요인에서 오는지 살펴보면 defender(AV) 정체성이 분산의 71.5%를 차지한다 (저자, 2026, under review). 최신 SOTA 생성기인 LD-Scene 역시 자신의 transferability 표에서 ego planner를 바꾸면 충돌률이 약 41%에서 63%로 달라진다 (Peng et al., 2026). 개념적 정의, 통제 실험, 정량 분석, 그리고 SOTA 생성기 자신의 결과가 모두 같은 곳을 가리킨다. 단일 SUT 충돌률은 생성기와 시나리오의 불변 척도가 될 수 없다.

이 의존성은 단순한 측정상의 불편이 아니라 실제 해를 낳는다. 첫째, AV를 업데이트할 때마다 같은 생성기의 난이도가 달라지면 버전 사이의 regression 테스트가 무효가 된다. 둘째, 충돌률이 낮다고 해서 좋은 주행을 뜻하지는 않는다. 지나치게 보수적으로 운전해 잦은 급제동을 일으키는 AV는 충돌률이 낮아도 추돌을 유발할 수 있다 (Liao et al., 2025). 셋째, 충돌률이나 근접도 같은 지표는 희귀 사건에 기반하므로 신뢰성에 대한 형식적 보장을 주지 못한다 (Fan et al., 2026). Shen et al. (2025)에서도 충돌률이 더 낮은 L3 시스템이 오히려 더 심각한 탑승자 부상을 낳아, 충돌률과 안전이 같은 방향으로 움직이지 않음이 드러난다.

이 문제를 다루려면 측정값이 누가 측정하든 흔들리지 않아야 한다. 교육 평가(educational testing)에서 출발한 문항반응이론(Item Response Theory, IRT)은 바로 이 목적을 위해 설계되었다. 서로 다른 응시자로 측정해도 문항 난이도가 흔들리지 않고, 서로 다른 문항으로 측정해도 응시자 능력이 흔들리지 않는 측정(specific objectivity)이 그것이다. IRT는 최근 대규모 언어 모델과 분류기 평가에서도 SUT-불변 비교 도구로 검증되었다 (ref needed: agent psychometrics, 2026; Fluid Benchmarking). 그러나 AV의 적대적 평가에는 아직 적용된 바 없다. 본 연구는 IRT 계열의 측정 모델을 AV 적대 평가에 처음으로 가져와, 시나리오와 생성기의 난이도, 그리고 AV의 강건성을 하나의 공통 척도 위에 올린다.

다만 교육 평가용 IRT를 그대로 가져올 수는 없다. 시험 문항이 가만히 있는 것과 달리, AV 적대 평가에는 시험 IRT가 가정하지 않는 세 가지 구조가 있다. (i) **반응성(reactivity)**: 시나리오와 생성기가 AV의 행동에 반응한다(closed-loop). 따라서 하나의 시나리오는 고정된 자극이 아니라 정책에 따라 달라지는 응답 과정이며, 난이도는 이 과정을 만들어내는 생성기의 속성으로 정의되어야 한다. (ii) **severity 조건화(severity-conditioning)**: 같은 생성기로 위험도를 연속적으로 조절할 수 있다(예: severity dial c_level). 하나의 난이도 값 대신, severity에 따라 달라지는 강건성 곡선을 모델링해야 한다. (iii) **avoidability 가중(avoidability-weighting)**: 충돌에는 시스템이 피할 수 있었던 것과 누구도 피할 수 없는 것이 섞여 있다. 회피 가능한 충돌만 강건성에 반영해야 한다. LD-Scene의 저자들도 ego planner의 잘못이 아닌 충돌을 인정하며, 충돌의 귀책(attribution) 분석을 향후 과제로 꼽는다 (Peng et al., 2026). 본 연구의 핵심 신규성은 이 세 구조를 측정 모델로 형식화하는 데 있다. 한편 SUT와 시나리오 사이에는 비단조 상호작용이 나타날 수 있으므로 (Shen et al., 2025), 본 연구는 하나의 생성기에서 severity를 변화시켜 얻은 일관된 시나리오 family 안에서 척도의 불변성을 먼저 확립하고, family 사이의 다차원성은 본 연구의 경계로 명시한다.

본 연구의 기여는 다음과 같다. 첫째, AV 적대 평가의 SUT 의존성 문제를 개념·통제실험·정량·SOTA의 네 각도로 정리하고, 측정 이론의 언어로 정식화한다. 둘째, 반응성·severity 조건화·avoidability 가중을 반영한 IRT 계열 측정 모델을 제안하여, 시나리오와 생성기의 난이도, AV의 강건성을 SUT-불변 공통 척도 위에 올린다. 셋째, 표준적이고 단순한 생성기 묶음(IDM/MOBIL 기반)과 다수의 AV 정책 위에서, 제안한 척도의 순위 안정성이 단일 충돌률 순위의 불안정성(순위 역전)보다 우월함을 보이고, 목표 신뢰도에 필요한 AV와 시나리오의 수를 추정하는 decision study를 제시한다.

연구 질문은 다음과 같다.

RQ1. 단일 충돌률에 기반한 난이도·강건성 순위는 어떤 AV로 측정하느냐에 따라 얼마나 불안정한가?

RQ2. 제안한 측정 모델은 SUT-불변 난이도·강건성 추정을 제공하는가? 추정된 모수는 보정에 사용한 AV 집단에 얼마나 둔감한가?

RQ3. 반응성·severity 조건화·avoidability 가중을 반영했을 때, 단순 IRT에 비해 모델 적합도와 순위 안정성이 얼마나 개선되는가?

---

## 10. 문제정의(Problem Formulation) 골격

서론과 분리해 본문에 짧게 둘 형식 정의(영어 표기, 본문에서 1단락 내외).

- AV 정책 집단 Π = {π}, 각 π는 잠재 강건성 θ_π를 가진다. (family 간 비교에서는 θ_π를 벡터로 두는 MIRT로 일반화.)
- 생성기 G와 severity c ∈ [0, c_max]가 시나리오 item s = (G, c)를 만든다. item은 난이도 b(G, c)를 가지며, b는 c에 대해 단조 증가한다고 가정한다(severity-conditioning).
- 반응성: s의 실현 궤적은 π에 따라 달라진다. 따라서 item을 고정 자극이 아니라 π에 반응하는 응답 과정으로 두고, 난이도는 G(와 c)의 속성으로 식별한다.
- 응답: 충돌 결과 Y_{π,s} ∈ {0,1}. avoidability 가중 w_{π,s} ∈ [0,1]로, 회피 가능한 충돌만 θ_π 추정에 기여하도록 한다.
- 측정 모델: P(Y_{π,s}=1) = f(θ_π, b(G,c)), crossed Π×S 설계에서 {θ_π}와 {b(G,c)}를 공통 척도 위에서 동시 식별. 핵심 성질은 specific objectivity, 즉 b는 보정 표본의 능력 분포에, θ는 사용한 item 집합에 둔감하다.
- 대비 기준: 단일 AV 충돌률 r_s = mean_π Y_{π,s}는 b와 θ를 한데 섞어버린다. 본 연구의 척도는 이 둘을 분리한다.

---

## 11. 예상 reviewer 반박과 방어 (배치 위치 포함)

방어 순서: ① 한계 인정 → ② 기여는 원리 수준 → ③ 한계를 현실적 대표성으로 재해석 → ④ 향후 검증.

1. "IRT는 기성품이다. 응용 논문 아닌가." → 시험 IRT의 세 가정(고정 문항·1회 응시·1차원 능력)이 AV 적대 평가에서 모두 성립하지 않는다. 우리는 반응성·severity·avoidability를 반영한 새 측정 모델을 형식화한다. 신규성은 적용이 아니라 모델에 있다. 배치: 서론(세 구조 단락) + Method.

2. "SUT 의존성은 LD-Scene 한 표 아닌가." → 개념적 정의(Ponn), 긴급도를 맞춘 통제 실험에서 약 2배 차이와 순위 역전(Shen), 순환적 난이도(Qiu), 분산의 71.5%(본 저자), SOTA 자기 표(LD-Scene)까지 다섯 각도가 동일 결론을 가리킨다. 배치: 서론 동기 + Related Work.

3. "결과(충돌)를 쓰면 다시 SUT 의존 아닌가." (Ponn이 미리 깔아둔 반박) → ① 개별 응답 P(Y|s,π)는 SUT 의존이 맞다. ② 그러나 잠재 모수 b, θ는 crossed 설계에서 식별·분리 가능하다(specific objectivity). 단일 AV 충돌률은 난이도와 능력을 섞지만, IRT는 person을 모형에 넣어 분리한다. ③ 따라서 우리는 결과 정보를 버리는 Ponn 방식을 subsumption 하면서 불확실성까지 정량화한다. 배치: Method(식별성) + Related Work(vs Ponn).

4. Yang et al. (2024)와의 구분. → 그들의 난이도는 단일 고정 ego에 종속되고 training step으로 정의되는 순환 구조다. 우리는 여러 AV에 걸쳐 불변 척도 위에서 측정한다. 그들의 생성기는 위협이 아니라 우리 item 공급원·baseline으로 쓸 수 있다. 배치: Related Work.

5. PMCT (Fan et al., 2026)와의 구분. → PMCT의 policy-agnostic 주장은 실시간 안전 지표(TTC류) 층위이지, 생성기·시나리오 비교 층위가 아니다. 난이도와 능력을 같은 척도에 올리지 않는다. 배치: Related Work 한 줄.

6. 차원성·교차 상호작용. → Shen의 순위 역전은 비단조 교차이며 단순 1차원 IRT의 일차원성 가정에 부담을 준다(2PL이 discrimination 차이로 일부는 흡수하나 큰 체계적 역전은 다차원을 시사). ① 한계 인정 ② 불변성 주장을 일관된 시나리오 family로 한정 ③ Shen의 역전 상당부분은 human takeover 교란이라 closed-loop AV 정책 평가인 우리에겐 약하게 붙는다 ④ family 간 다차원성은 MIRT로 향후 확대. 배치: Method(가정) + Limitations, 단 Method에서 선제.

7. "저충실도 시뮬레이터(highway-env)로 충분한가." → ① 충실도 한계 인정 ② 기여는 측정 모델·식별성의 원리 수준이라 시뮬레이터에 무관하다 ③ 오히려 표준적이고 단순한 생성기(IDM/MOBIL)를 일부러 써서, 결과가 특수한 생성기의 산물이 아니라 어떤 생성기 묶음을 줘도 척도가 안정적임을 보인다. 자원 제약이 없어 AV×시나리오×severity 격자를 키워 empirical power를 확보한다 ④ 고충실도 시뮬레이터·실차 데이터는 향후 검증. 배치: 서론 위치선정 + Experiment + Limitations.

8. "왜 ACARL 재활용이나 SOTA 생성기가 아니라 새 단순 생성기인가." → 이 논문의 주인공은 측정 모델이다. 평범한 표준 생성기 묶음이라야 척도의 SUT-불변성이 생성기 특수성에 오염되지 않음을 보일 수 있다. ACARL은 별도 심사 중이고, 재활용하면 생성기 논문처럼 보여 메시지가 흐려진다. 배치: Experiment design.

---

## 12. 운영 한계 (라운드 16 환경 이전 후 재구성, 2026-06-06 라운드 17·18 추가 정정, 2026-06-07 라운드 19 N=20 확장 후 정정)

§11이 다룬 여덟 항목은 측정 모델 자체에 대한 학술적 반박과 방어다. 이와 별개로, 격자를 실제로 운용하는 과정에서 따라오는 운영 한계가 있으며, 본 절은 라운드 16 결정으로 격자 환경이 CARLA + SafeBench에서 highway-env + ACARL로 이전된 후 본 환경에서 따라오는 한계 다섯 가지로 재구성되었다. 라운드 17에서 CARLA 재학습 시도(v1·v2·v3)가 모두 실패하여 본문 핵심이 highway-env에 그대로 유지되었고, CARLA 시도와 본 진단은 본 §의 6번 항목(시뮬레이터 충실도 자료의 본질적 자료)에 한 단락으로 추가되었다. reviewer가 같은 항목을 다시 지적하지 못하도록 본문 Limitations에 정직히 기술할 내용을 정리한다. 자세한 결정 이력과 데이터 근거는 `research/decisions.html` #d06·#d07의 라운드 16·17 단락에 있고, 측정 모델 한계는 `research/method.html`의 "측정 모델 운영 한계" 박스, 격자 운영 한계는 `research/plan.html`의 "격자 운영에서 따라오는 한계"에 본문 voice로 기술했다. 라운드 1~15의 SafeBench·CARLA 의존 한계(behavior None-safety 보강, LC σ 다이얼의 mu 위치, K=30 자릿수 비교 정직성, CARLA 메모리 누수, MOBIL 구현 명명, SafeBench RL 가족 시드 분산)는 매몰 비용 처리되어 결정 트레일에 보존만 되며 본 본문에는 등장하지 않는다.

1. **시뮬레이터 충실도의 한계와 측정 원리의 일반화**. 본 격자가 사용하는 highway-env(1.10.2)는 2D bicycle dynamics 기반의 단순 시뮬레이터로 sensor 모델·세부 동역학·도로 형상의 다양성이 CARLA 같은 고충실도 시뮬레이터에 비해 제한적이다. 자율주행 평가의 일반적인 reviewer 기대(고충실도 시뮬레이션)와 거리가 있는 흠이지만 본 연구의 기여는 측정 모델의 원리 자체에 있으며 plan §7과 §11 7번이 이 정합을 명시한다. AuthSim(T-ITS 2025)·ACARL(AAP) 같은 자율주행 평가 자료가 같은 highway-env에서 실험된 사례가 있다는 점도 함께 명시한다. 본 측정 모델의 일반화 가능성을 CARLA·실차 데이터에서 검증하는 작업은 향후 연구 과제로 남긴다. 배치: Method(범위·가정·경계) + Limitations(향후 검증).

2. **응시자 집단의 학습 시드 의존성과 정규 분포 가정**. 본 형식 (8)은 응시자 강건성 θ_π ∼ N(0, σ_θ²)의 정규 분포를 가정한다. 본 격자의 응시자 집단은 highway-env 표준 controller 두 종(IDM, MOBIL)과 ACARL이 학습한 Defensive RL 시드 셋(seeds 42·456·789)으로 구성된다. ACARL 원고 §5.3에서 보고된 Defensive RL 5-seed의 학습 결과는 시드별로 크게 갈리며 seed 1024는 70% baseline 충돌률을 보이고 seed 123은 0% baseline 충돌률을 보였다. 본 격자는 학습 성공한 시드만 응시자에 포함시켜 정규 분포 가정에서 멀리 벗어난 양극단을 배제한다. 응시자 N=3~5는 표준 D2 split-half 검정(응시자 부분집합 split)의 통계 검정력 측면에서 부족한 자료이며 K=70 통합 자료의 D2 응시자 split r mean은 -0.014~0.415로 합격선 0.80에 미달한다. 본 한계를 두 갈래로 다룬다. 첫째는 D2 trial-split 변형으로 각 cell의 K=70 episode를 무작위 35 vs 35로 분리하여 (G, c) 충돌률 매트릭스의 Pearson r을 산출하며 본 변형 결과는 합격선을 명확히 통과(전체 4 G에서 r mean=0.939, 단조성 통과 3 G에서 r mean=0.917)하여 b̂ 추정의 trial 표본 안정성을 직접 보인다. 둘째는 본문 메시지 좁힘으로 응시자 split-half를 보조 sanity 수준으로 옮기고 본 측정 모델의 정합성 검증을 단조성 ρ(K=70 통합)·D2 trial-split·D3 ablation 세 항목으로 모은다. 향후 응시자 집단을 확장하려면 다른 학습 방식의 자율주행 정책(예: TransFuser, MILE, World on Rails)을 도입하여 N=6~8까지 늘리는 자료가 필요하다. 배치: Experiment design(응시자 집단) + Method(D2 검정 형식) + Limitations(향후 검증).

3. **적대 생성기의 학습 분포 의존성과 c_level 다이얼의 한계**. ACARL의 적대 생성기는 c_level ∈ [0, 0.8]을 reward 함수의 THW target 매핑 THW*(c_level) = 3.0 - 2.5·c_level을 통해 학습한 정책이므로 본 측정 모델의 단조 가정이 학습 분포 안에서만 보장된다. ACARL 원고 §6.2는 c_level=0.8에서 측정 median THW가 1.652s로 target THW*=1.0s를 초과하여 c_level=0.0~0.6에서 유지된 단조 곡선이 c_level=0.8에서 깨지는 자료를 보고하며, 본 자료는 학습 분포의 가장자리에서 SSM 페널티가 강해져 정책이 target에 도달하지 못한 결과이다. 본 측정 모델은 c=0~3 구간을 주된 단조 검정 범위로 두고 c=4에 대해서는 별도 sanity 진단을 함께 보고한다. 배치: Method(γ_G·c 단조 가정 + 데이터 검증) + Limitations.

4. **적대 시나리오 type의 한정**. ACARL의 적대 생성기는 cut-in과 rear-end 두 시나리오 type만 학습되어 있고, brake_check·sideswipe·junction crossing 같은 다른 적대 시나리오는 본 격자에서 평가되지 않는다. 본 한정은 plan §13 셋째 기여(다양한 표준 단순 생성기 묶음 위에서 척도 안정)의 적용 범위를 두 시나리오 type으로 좁히는 흠이며, 본문은 이 한정을 명시하고 다른 시나리오 type 확장은 향후 연구 과제로 둔다. ACARL의 다른 baseline(Method B Naive, Method C Rule-based) 두 종이 cut-in/rear-end 구조를 공유하므로 본 격자의 G=4 구성도 두 시나리오 type 안에 머문다. 배치: Experiment design(생성기 정의) + Limitations(향후 확장).

5. **외부 비교점은 자릿수 일치 sanity check 수준에서만 사용**. ACARL 원고 §6.5의 multi-defender robustness 분석에서 보고된 cross-defender Spearman ρ(cut-in 0.53, rear-end 0.55)와 본 측정 모델의 추정 b̂의 단조성·rank correlation은 자릿수 일치 sanity check 수준에서만 비교한다. 척도 일치(scale linking)는 ACARL의 ρ 자료가 본 측정 모델의 latent trait 추정과 다른 통계량이므로 불가능하며, 본문은 이 차이를 별도 단락으로 명시한다(라운드 9·10 결정의 흐름 연속). 배치: Method(외부 비교점 단락) + Experiment(D4 외적 타당성).

6. **CARLA 이전 시도의 본질적 한계와 RL 정책의 환경 우회 (2026-06-06 라운드 17)**. 라운드 16에서 격자를 highway-env로 이전한 후에도 시뮬레이터 충실도에 대한 reviewer 우려가 잠재해 있다는 판단으로 본 라운드에서 환경 충실도 강화를 위해 격자를 다시 CARLA Town04로 옮기는 재시도를 검토하였다. 본 재시도가 세 차례(v1·v2·v3) 학습에서 모두 fast crash로 수렴하여 종결되었다. v1은 ACARL Phase 1을 CARLA에서 1M step 학습한 결과로 충돌율 100%·THW 0.45초·c_level controllability ρ ≈ 0을 산출하였고, v2는 reward 함수의 proximity_bonus·near_miss·thw_error 가중치를 강화한 295K step 학습, v3는 NPC의 LineOfSightSensor가 forward-only인 흠을 보완하기 위해 CruiseControl.tick에 ego threat-aware override를 추가한 880K step 학습이었으나 모두 같은 fast crash로 수렴하였다. cross-check(evaluate_5seed_final.py로 highway-env method A 5-seed)에서 ρ=+0.496 ± 0.172·충돌 4%·THW 2.57초가 확인되어 본 흠이 reward·NPC 인지가 아니라 CARLA의 3D physics·관성이 RL 정책의 환경 우회 학습을 가능케 하는 본질적 원인이라는 진단이 명확해졌다. 본문 §Limitations에 본 시도와 진단을 한 단락으로 정직히 명시하고, 본 측정 모델이 환경 우회 현상을 γ̂≈0으로 진단할 가능성은 본 격자에서 검증되지 않은 추측이므로 본 논문의 새 contribution이 아닌 후속 연구의 가설로만 §Future Work에 적는다. 본 학습을 80만 step에서 종결한 사유는 컴퓨팅 예산 안에서 hyperparameter·entropy regularizer 조정 공간을 충분히 탐색하지 못한 한계로, 본 우회 행동이 추가 탐색으로 우회될 가능성은 본 격자에서 검증되지 않은 채로 남는다. 본 시도에서 작성된 CARLA 코드(ACARL repository `<anonymized-acarl-repo>`)는 그대로 보존되어 future work의 출발점으로 활용된다. 배치: Limitations(시뮬레이터 충실도와 RL 정책의 환경 우회 현상) + Future Work(본 측정 모델의 환경 우회 진단 능력의 후속 검증 가설).

7. **분석·통계 정합성 적대 점검 정정 (2026-06-06 라운드 18)**. REVIEW_FIXLIST.md의 적대 점검에서 분석 코드와 본문 사이 4 흠과 4 약점이 잡혀 본 라운드에서 모두 정정하였다. 핵심 정정은 응시자 θ̂ 표준오차의 산출 흐름이다. 라운드 17까지 `analysis/d-study/d_study.py`의 fit_map은 L-BFGS-B의 `res.hess_inv` (제한메모리 근사 역헤시안)를 SE로 활용하여 ±1.808~3.776의 부풀려진 95% CI를 산출하였다. 라운드 18 1차 정정에서 `_numerical_hessian` 함수(중심 차분)를 추가하여 정확한 헤시안 기반 SE ±0.690~0.892를 산출하였다. 라운드 18 2차 정정에서 표준화 변환 θ' = (θ − m)/s의 야코비안 J = (I − 11ᵀ/n_av)/s를 적용한 J Σ J^T 공분산으로 sum-to-zero 제약과 sample 상관을 반영하여 ±0.262~0.567로 추가 정정. def_rl_789(+1.406 ± 0.567)가 음의 두 응시자(-0.836·-0.569)와 95% CI 수준에서 매우 명확히 분리되어 본 측정 모델의 응시자 순위 추정의 학술 anchor가 강하게 보장된다. 부수 정정: 식 (1) 부호 σ(a·(b−θ)) 정합, episode 수 5,000 통합·4,200 적합 명시, D3 g_common df=12 정정·deviance 비교 voice, 사후 표준화·u 자유 추정·â≈14.3 계단함수 신호의 §Limitations 명시. 배치: Method(SE 산출 방법) + Results(정정된 CI) + Limitations(잔여 본질 한계).

8. **응시자 N=20 확장과 Method C 음의 단조성 가짜 흠 정정 (2026-06-07 라운드 19)**. 라운드 19 깊은 검토자가 본 격자의 핵심 흠으로 잡은 "응시자 가족이 본질적으로 Defensive RL 세 시드의 same-family 시드 분산에 의존"을 해소하기 위해 N=3 → N=20으로 확장하였다. 추가 응시자 15종: PPO 새 seed 5종(100·200·500·800·999, 약 33분/seed × 5), SAC 5 seed(42·100·456·789·999, 약 58분/seed × 5), TD3 5 seed(42·100·456·789·999, 약 42분/seed × 5). 학습 11시간 + 격자 응답 산출 6시간 12분(21,000 추가 episode). 본 확장으로 다음 핵심 발견이 산출되었다. (1) Method C의 음의 단조성 ρ=-0.821이 N=3·5의 작은 표본 흠으로 만든 가짜 음의 단조성이었음. N=18·K=70에서 ρ=+0.900 양의 단조성으로 정정. 라운드 17·18의 Method C 진단 contribution voice 폐기. (2) Method B의 단조성 ρ=0.700(N=5)이 N=18에서 ρ=0.000으로 떨어져 본 G의 본질적 baseline 흠 드러남. (3) 응시자 θ̂이 학습 방식 4종(PPO·SAC·TD3·Defensive RL)을 자릿수 차이로 명확히 분리: PPO 강건군 +2.0~+2.2, SAC 약함군 -0.77~-0.65, TD3 변동 -0.83~+0.30. (4) D2 trial-split r=0.996(이전 0.917에서 강화), D3 deviance no_severity Δ=195,116(이전 2,552의 76배). (5) 변별력 â의 trial 자료 의존성 발견: N=20·K=20에서 cut-in â=6.6·rear-end â=7.4(자연 sigmoid)이 N=18·K=70에서 24.4·30.7(강한 계단함수 신호)로 자릿수 더 커지는 자료. 본 자료는 본 측정 모델의 식별성 경계 신호이기도 한 양면 발견. 배치: Method(트레이드오프) + Results(N=20·K=20과 N=18·K=70 두 자료) + Limitations(N=20이 Rasch family 권고 N≥30~50 미달·식별성 경계).

---

## 13. 참고문헌 / 검증 상태

- 이번 세션 정독(원문 확인): Ponn et al. 2020 (EVER); Qiu et al. 2026 (TR Part C); Shen et al. 2025 (Accident Analysis and Prevention).
- 이전 세션 정독: Fan et al. 2026 PMCT (TR Part C); Liao et al. 2025 (Information and Software Technology); Peng et al. 2026 LD-Scene (TR Part C).
- 무력화된 경쟁: Yang et al. 2024 (arXiv 2408.14000).
- (ref needed) IRT-for-AI 평가: agent psychometrics (2026), PSN-IRT, Fluid Benchmarking, β³-IRT. 정확한 서지 정보 정리 필요.
- 본 저자 ACARL (under review, AAP). 분산분해 defender 71.5%.
- 주의: LD-Scene 수치(약 41→63%, Table 4)와 ACARL 71.5%는 이전 핸드오프에 기록된 값이며 이번 세션에서 원문 재대조는 하지 않았다. 최종 제출 전 원 표와 대조 필요.

---

## 14. 현재 미결 상태 (아직 확정하지 않은 항목)

- 깊은 겹을 severity만으로 갈지, avoidability까지 포함할지, 셋을 어디까지 형식화할지의 최종 확정.
- 차원성 처리: family 한정 수준 vs MIRT 채택 범위.
- 서론의 Figure 1 구성(같은 생성기, AV를 바꾸면 난이도·강건성 순위가 역전되는 그림).
- 방법 수식의 구체화 수준(2PL/graded-response → severity 조건화 b(G,c) → avoidability 가중 → 식별성).
- 실험 설계 세부는 라운드 16에서 재구성: 응시자는 highway-env 표준 controller 두 종(IDM, MOBIL) + ACARL이 학습한 Defensive RL 세 시드(seeds 42·456·789) 다섯 종, 생성기는 G=4(ACARL cut-in + ACARL rear-end + Method B Naive + Method C Rule-based), severity 격자 c={0,1,2,3,4}에 ACARL c_level=0.2c 매핑, 반복 K=20(본 격자)·K=50(통계 검정력 보강 격자). 미결은 D1·D2·D3·D4 본 분석의 부분 자료 선정(idm·mobil을 baseline으로 분리할지, 응시자 셋만 본 분석에 둘지)과 K=50 결과 후 D2 split-half 검정의 통계 검정력 보강 항목.
- 단조성 ρ 합격선(0.7) 결과는 라운드 16 K=20 본 격자에서 한 생성기(acarl_cutin, ρ=0.900)만 통과하였다. K=50 보강 격자(3,000 episode) 후 K=70 통합에서 세 생성기(acarl_cutin ρ=0.821, acarl_rearend ρ=0.700, method_b ρ=0.700)가 통과하여 §4의 contribution 좁힘 결정은 부분 철회되었다. 본 정정 후 D1·D2 trial-split·D3 ablation·fit_irt_main 본 분석이 모두 highway-env K=70 자료로 통과한 상태로, 본 시점의 미결은 본 figure를 본문 §Results에 어떻게 배치할지(figure 4종을 한 페이지에 묶을지 분리할지)와 ACARL self-citation 단락의 본문 위치(서론 위치선정 vs §Related Work)이다.
- **2026-06-06 라운드 17 추가**: CARLA 이전 시도(v1·v2·v3) 종결에 따라 본문 핵심이 highway-env 격자로 그대로 유지된다. 본 시도와 진단은 §12 6번 항목에 추가되어 본문 §Limitations·Future Work에 한 단락으로 명시될 흐름이다. 본 측정 모델이 환경 우회 현상을 γ̂≈0으로 진단할 가능성은 본 격자에서 검증되지 않은 추측이므로 §Future Work의 후속 연구 가설로만 박는 흐름으로 결정되었다. 미결은 ACARL repository에 보존된 CARLA 코드(carla_traffic.py·adversarial_carla_env.py 수정, defensive_carla_env.py·grid_carla_env.py·run_aaai_grid_carla.py 등)를 본문에서 언급할지의 결정이다.
- (ref needed) 항목들의 정확한 서지 확정과 LD-Scene/ACARL 수치 원문 대조.
