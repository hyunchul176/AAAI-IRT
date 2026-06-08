# AAAI 논문 작업: 새 환경 첫 대화 프롬프트

본 프롬프트의 내용을 새 컴퓨터 환경의 Claude 첫 대화에 그대로 붙여 넣으면 Claude가 본 프로젝트의 학술 흐름·voice 규칙·현재 상태를 한 번에 파악한다. Claude Code 환경과 Claude 웹(claude.ai) Projects 양쪽에서 모두 활용 가능하다.

---

## 프로젝트 정체성

본 프로젝트는 AAAI 메인 트랙 논문 "AV 적대 평가의 SUT-불변 측정: IRT 기반 공통 척도"의 연구 정리와 본문 작성 작업이다. Item Response Theory(IRT)를 자율주행 적대 평가에 처음 적용한 측정 모델을 제안하며, 시나리오 난이도와 AV(System Under Test) 강건성을 latent variable로 분리 추정하는 흐름이다.

- 타깃 학회: AAAI 메인 트랙 (방법론 신규성 중시)
- 본 연구의 빈 영역: 충돌률 같은 단일 지표가 SUT 의존성으로 시나리오 난이도 순위를 흐리는 문제를 IRT로 해소
- 본보기 한글 학술 voice: 김예은·최성진·여화수 2019 (대한교통학회지, `N0210370104.pdf`)

---

## 핵심 파일 위치

새 환경의 작업 디렉토리에 본 파일들이 옮겨져 있어야 한다. 디렉토리 root는 `AAAI/`(또는 사용자 지정 root)로 가정한다.

### 본문 작성용 raw 자료 (옵션 C로 정리됨)
- `paper_data.md`: AAAI 본문 outline + 각 단락에 박을 raw 자료 (§1 Introduction부터 §8 Conclusion·§A 부록)
- `paper_figures.md`: figure 6종 raw 자료 + caption baseline + 추가 figure 후보
- `paper_references.md`: 인용 reference 25개 + BibTeX 형식 + 인용 위치 매핑 + ref needed 15개 list

### 학술 voice·본보기
- `CLAUDE.md`: 학술 voice 규칙 (절대적). 본 규칙 위반 시 사용자 정정 누적.
- `N0210370104.pdf`: 본보기 한글 학술 스타일 (1차 reference)

### 연구 정리 사이트 (HTML)
- `research/index.html`: 연구 개요
- `research/method.html`: 측정 모델 식 (1)~(9) 형식화
- `research/plan.html`: 연구 계획 본문 voice
- `research/decisions.html`: 라운드 1~17 결정 트레일 (라운드별 학술 결정의 정직한 기록)
- `research/roadmap.html`: 수행 로드맵 (B1·B2·B3·B4 등 단계)

### 원본 계획·격자 자료
- `AAAI_SUT_invariant_measurement_plan.md`: 본 연구의 원본 계획 (§1 정체성부터 §14 미결 자료까지)
- `analysis/highway_grid/figures/`: figure 6종 (d1·d2·d3·irt_main + 보조 2종)
- `analysis/highway_grid/responses_*.jsonl`: K=70 통합 응답 자료

---

## 학술 voice 규칙 (CLAUDE.md 발췌)

본 규칙은 절대적이다. 사용자 누적 지적 항목이며 새 환경에서도 그대로 적용한다.

- **"자리" 어휘 금지**: "이 자리에서·결정 자리·흠 자리·본문 자리" 등 "자리"로 묶는 표현 회피. 대체: "이 경우·여기서·이 단계·이 부분·이 지점", 또는 그냥 X.
- **"자료" 어휘 과다 반복 회피**: 한 단락 8회 이상 사용 금지. 대체: 결과·진단·증거·현상·흠·결정·기록·코드 등 구체 명사.
- **흐르는 산문**: 불릿·표·배지·라벨식 도식·메타 설명 회피. 본문에 한정 (정리 문서는 outline·표 활용 가능).
- **메타포 금지**: 부품·묶음·척추·사다리·축·무게중심·주축·토대·바닥·손잡이.
- **em-dash 금지**: 콜론(:)·가운뎃점(·)·en-dash(–)로 대체.
- **"도입" 대신 "서론"** (한국어) 또는 "introduction" (영어).
- **인용은 abstract·Introduction에서 따오지 않음**: 본문(Results·Discussion·Conclusion)에서 발췌하고 2차 인용 여부 확인.
- **구어·과장 표현 금지**: "자백·자인·선구자·그냥 빼며·손으로 고른" 등 회피.
- **자연스러운 동사**: "위험도를 잰다"가 아니라 "측정한다". 어색한 합성어·명사 나열 회피.

---

## 본 시점의 진행 상태 (2026-06-06 기준)

### 완료된 작업
1. **방법론 형식화 완료**: method.html의 식 (1)~(9). IRT의 3PL model + severity 조건화 b(G,c) = β_G + γ_G·c + 회피불가 하한 u_G + 변별력 a_G.
2. **실험 격자 완료 (라운드 19 N=20 확장 후)**: highway-env 1.10.2 + ACARL infrastructure. 응시자 N=20: IDM·MOBIL (각 K=20), Defensive RL 3 시드 (42·456·789, K=70), PPO 새 5 시드 (100·200·500·800·999, K=70), SAC 5 시드 (42·100·456·789·999, K=70), TD3 5 시드 (42·100·456·789·999, K=70). 생성기 G 4종 (ACARL cut-in·rear-end·Method B·Method C) × severity c 5수준. 통합 응답 26,000 episode (`responses_av20_combined.jsonl`). fit 자료: N=20·K=20 통합 (`responses_av20_combined.jsonl`, 본문 주 자료) + N=18·K=70 학습 응시자만 (`responses_av18_learned.jsonl`, D 분석 핵심).
3. **분석 완료**:
   - D1 단조성 (N=18·K=70, 라운드 19 정정 후): cut-in ρ=0.900·rear-end ρ=0.700·method_c ρ=+0.900 (PASS 3종) / method_b ρ=0.000 (FAIL, N 확장으로 본 G의 단조성 흠 드러남). 이전 method_c ρ=-0.821 음의 단조성은 N=3·5의 작은 표본 흠으로 정정됨.
   - D2 trial-split: 단조성 통과 3 G에서 r mean=0.917, p25=0.895 (합격선 0.80 통과)
   - D3 ablation (deviance 비교, N=18·K=70 라운드 19): no_severity Δ=195,116 (df=4, 이전 2,552의 76배), g_common Δ=4,454 (df=12, 이전 482의 9배), u_zero Δ=+36.83 (정상 양수, 이전 -18.04 음수 흠 정정).
   - fit_irt_main 직접 적합: θ̂·β̂·γ̂·â·û 추정값 산출 (irt_main.json)
4. **결정 트레일 라운드 1~19 정리 완료**: decisions.html. 라운드 16(CARLA → highway-env 이전)·라운드 17(CARLA 재시도 종결)·라운드 18(REVIEW_FIXLIST 정정·야코비안 보정)·라운드 19(응시자 N=20 확장·Method C 음의 단조성 가짜 흠 정정).
5. **본문 작성용 raw 자료 정리 완료**: paper_data.md·paper_figures.md·paper_references.md 세 파일.
6. **검토자 1·2차 적대 검토 통과**: 본문 voice 정정 누적 약 50건 처리.

### 핵심 추정값 (fit_irt_main, irt_main.json)
- 응시자 강건성 θ̂ (N=18·K=70, 라운드 19 정정 후, 강건성 순):
  - **PPO 강건 (3종)**: ppo_200 +2.221 ± 0.821, ppo_800 +2.027 ± 0.757, ppo_500 +2.020 ± 0.758
  - **Defensive RL 기존**: def_rl_789 +0.317 ± 0.175, def_rl_42 -0.001 ± 0.110, def_rl_456 -0.244 ± 0.100
  - **PPO·TD3 중간**: ppo_100 +0.180, td3_100 +0.100, td3_789 -0.250
  - **PPO 약함**: ppo_999 -0.429 ± 0.130
  - **SAC 5종 (모두 약함)**: sac_42 -0.652, sac_456 -0.678, sac_100 -0.727, sac_999 -0.738, sac_789 -0.769
  - **TD3 약함**: td3_42 -0.752, td3_456 -0.798, td3_999 -0.825
  - PPO 강건군이 SAC 약함군과 ±0.7~3.0 자릿수 차이로 매우 명확히 분리. 학습 방식 4종(rule-based·on-policy PPO·off-policy SAC·off-policy TD3)의 강건성 분리가 본 측정 모델의 specific objectivity 검증의 강한 학술 anchor.
- 생성기 추정값 (두 fit 자료 분리):
  - **av18 (N=18·K=70 학습 응시자만, D 분석 핵심)**:
    - β̂: cut-in -0.907, rear-end -0.880, method_b -0.378, method_c -0.864
    - γ̂: cut-in 0.010, rear-end 0.008, method_b 0.016, method_c 0.026
    - â: cut-in 24.43, rear-end 30.65, method_b 2.19, method_c 3.38 (강한 계단함수 신호)
    - û: cut-in 0.056, rear-end 0.051, method_b 0.001, method_c 0.004
  - **av20 (N=20·K=20 통합, 본문 주 자료)**:
    - β̂: cut-in -1.266, rear-end -1.251, method_b -0.247, method_c -0.826
    - γ̂: cut-in 0.018, rear-end 0.034, method_b 0.025, method_c 0.037
    - â: cut-in 6.64, rear-end 7.39, method_b 2.08, method_c 2.51 (자연 sigmoid ICC)
    - û: cut-in 0.057, rear-end 0.054, method_b 0.003, method_c 0.004
  - 두 fit 자료의 양면: K=70 trial 풍부함이 변별력 모수의 식별성을 강화하지만 ICC가 step function에 가까워지는 식별성 경계 신호이기도 함. paper_data.md §5.5·§6.4의 양면 진단 voice 정합. 라운드 18 검토자가 잡은 "â≈14.3 계단함수 흠"이 라운드 19 av18에서 24~31로 자릿수 더 커진 자료를 §Limitations에 정직히 명시.

### 핵심 결정의 흐름
- 라운드 1~15: SafeBench + CARLA 인프라 (단조성 검정 미통과로 매몰 비용 처리)
- 라운드 16 (2026-06-04): highway-env + ACARL 인프라로 전면 이전
- 라운드 17 (2026-06-06): 시뮬레이터 충실도 강화를 위한 CARLA 재시도(v1·v2·v3) 종결. 본 진단(CARLA NPC의 forward-only LOS sensor + 3D physics 관성이 RL 정책의 환경 우회 학습을 가능케 함)으로 highway-env 본문 유지.
- 라운드 18 (2026-06-06): REVIEW_FIXLIST 적대 점검 정정 (4 흠·4 약점). θ̂ SE 수치 헤시안 + 표준화 야코비안 보정으로 ±0.262~0.567 산출. 식 (1) 부호·episode 수·D3 df 정정.
- 라운드 19 (2026-06-07): **응시자 N=3 → N=20 확장** (PPO 5 + SAC 5 + TD3 5 새 시드 학습 11시간 + 격자 응답 산출 6시간 12분). 핵심 발견: Method C의 음의 단조성 ρ=-0.821이 N=3·5 작은 표본 흠으로 만든 가짜 음의 단조성이었음이 N=18에서 +0.900 양의 단조성으로 정정. 라운드 17·18의 Method C 진단 contribution voice 폐기. PPO·SAC·TD3 학습 방식 분리가 본 측정 모델의 specific objectivity 검증의 강한 학술 anchor가 됨.

### 미결 작업
- 본문 voice 작성 (서론·관련 연구·방법·실험·결과·논의·결론 단락)
- Figure 1 (motivation) 결정과 산출
- ref needed 15개 자료 서지 확정 (paper_references.md §9 list 참조)
- ACARL self-citation 위치 결정 (서론 위치선정 vs §Related Work)

---

## 사용자 voice의 특수성

- 사용자는 측정통계 전문가가 아니라 자율주행 도메인 연구자이다. IRT·Wilson CI·REINFORCE·BehaviorAgent 같은 통계·기술 용어는 처음 등장할 때 한두 문장으로 쉬운 말이나 비유로 풀어 설명한다.
- 시험 비유를 일관되게 활용: 문항 = 시나리오, 수험생 = AV 정책, 오답 = 충돌, 문항 난이도 = 시나리오 위험도, 수험생 실력 = AV 강건성.
- 사용자의 학술 voice가 Claude의 기본 voice와 다르다는 점이 명시적으로 확인되었다. 본 voice 정정을 적극 수용하고, 본문 voice는 사용자가 직접 작성하며 Claude는 raw 자료의 정확성·완전성을 보장한다.
- 결정 트레일(decisions.html)의 voice와 본문(paper voice) voice는 분리되어 운영된다. 결정 트레일은 학술 결정의 정직한 시점별 기록이며 본문 voice의 정밀성과는 별개 표준이다.

---

## 협업 도구 역할

- **PDF 전문 정독**: 특정 논문의 표·수치·인용문 검증은 full text PDF를 `pdfs/`에 받아 직접 정독. abstract·Introduction에서 따오지 않음.
- **오픈웹·arXiv**: Claude가 직접 검색·정독.
- **leapspace** (ScienceDirect LLM): 코퍼스 전반 광역 조사 전용. 사용자가 직접 호출. Claude의 호출 대상 아님.

---

## 다음 진행 항목

본 새 환경에서 사용자가 우선 진행하려는 작업을 명확히 한다. 가능한 항목:

1. **본문 voice 작성** (Claude 웹 Projects 권고): paper_data.md를 outline으로 본문 단락 voice 작성. 사용자가 직접 voice 작성, Claude는 raw 자료의 정확성·완전성을 보장. 첫 단계로 §1 Introduction부터 시작 권고.

2. **Ref needed 자료 확정**: paper_references.md §9의 15개 자료(Qiu 2026·Shen 2025·Peng 2026 LD-Scene·AuthSim 2025·Wang·Ma·Lai 2026 등)의 정확한 서지 검색·확정. Google Scholar·arXiv·해당 저널 홈페이지 검색.

3. **Figure 1 (motivation) 산출**: paper_figures.md의 두 옵션(LD-Scene·Shen 2025 rank reversal 시각화 또는 측정 모델 conceptual schematic) 중 결정 후 산출.

4. **추가 분석**: 본 시점에 미진행한 분석 자료. 예: D2 응시자 N 확장(TransFuser·MILE·World on Rails 도입)·다른 적대 시나리오 type 평가(brake_check·sideswipe·junction crossing) 등.

5. **본 시점의 다른 자료**: 사용자 결정.

---

## 첫 대화 시 Claude가 사용자에게 묻는 자료

본 프롬프트를 새 환경에 붙여 넣은 후 Claude가 사용자에게 묻는 자료는 다음과 같다.

- 본 시점에서 우선 진행하려는 작업은 무엇인가? (위 다섯 항목 중 또는 다른 흐름)
- 본 raw 자료(paper_data.md·paper_figures.md·paper_references.md)를 attach 또는 참조할 자료가 준비되었는가?
- 본문 voice 작성을 진행하면 어느 섹션부터 시작하는가? (§1 Introduction 권고)

---

## 부록: 결정 트레일 라운드 1~17 한 줄 요약

| 라운드 | 날짜 | 핵심 결정 |
|--------|------|----------|
| 1~5 | 2026-06-02 | 시뮬레이터 CARLA + SafeBench 선택, 결정 트레일 보관 위치, 격자 합격선 |
| 6~10 | 2026-06-02~03 | 평가 대상 AV 선정, 시나리오 생성기 4종, severity 조절 |
| 11~15 | 2026-06-03~04 | SafeBench 단조성 미통과, behavior 패치, CARLA 메모리 누수, MOBIL 좁힘 |
| 16 | 2026-06-04 | highway-env + ACARL 전면 이전. K=20·K=50·K=70 통합. D2 trial-split 변형 |
| 17 | 2026-06-06 | CARLA 재시도(v1·v2·v3) 종결. highway-env 본문 복원. Method C 음의 단조성 진단 contribution 추가 |

자세한 단락은 `research/decisions.html` 참조.

---

본 프롬프트가 끝났다. 사용자가 이어서 첫 요청을 입력하면 Claude는 위 자료를 기준으로 작업을 시작한다.
