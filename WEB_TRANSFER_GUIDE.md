# Claude 웹 이전 가이드: AAAI 논문 본문 작성 단계

본 가이드는 본 프로젝트를 Claude 웹(claude.ai) 환경의 Projects 기능으로 이전하여 본문 voice 작성을 시작하는 흐름을 정리한다. Claude Code 환경(본 시점)에서 라운드 1~18 정정이 완료되어 본문 voice 작성 단계로 이전할 학술 강도에 도달한 상태이다.

---

## 1. 이전 흐름: 단계별

### Step 1: Claude.ai에서 새 Project 생성

claude.ai에 접속한 뒤 좌측 메뉴의 "Projects"에서 새 Project를 생성한다. Project 이름은 "AAAI SUT-Invariant Measurement (IRT)" 또는 유사한 학술 voice로 결정.

### Step 2: Project Instructions 설정

Project 설정의 "Custom Instructions" 또는 "Project Instructions" 항목에 `SESSION_START_PROMPT.md`의 전체 내용을 그대로 붙여 넣는다. 본 instruction이 Claude의 모든 응답에 자동 컨텍스트로 작용한다.

### Step 3: Project Knowledge에 파일 첨부

다음 파일들을 Project Knowledge에 attach한다(순서는 무관). 첨부는 파일 업로드 위치에서 직접 진행한다.

**필수 첨부 7파일**:
1. `paper_data.md`: AAAI 본문 outline + raw 자료 (본문 voice 작성의 핵심 reference)
2. `paper_figures.md`: figure 6종 raw 자료 + caption baseline
3. `paper_references.md`: 인용 reference 25개 + BibTeX + ref needed 15개 list
4. `CLAUDE.md`: voice 규칙 (절대적)
5. `N0210370104.pdf`: 본보기 한글 학술 스타일 (1차 reference)
6. `SESSION_START_PROMPT.md`: Project Instructions로도 활용한 본 파일을 Knowledge에도 첨부하면 참조 가능
7. `REVIEW_FIXLIST.md`: 분석 정합성 정정 reference (라운드 18 정정의 학술 anchor)

**보조 첨부 5파일** (본문 voice 작성 중 참조 가능):
8. `AAAI_SUT_invariant_measurement_plan.md`: 원본 계획 §1~§14
9. `research/method.html`: 측정 모델 식 (1)~(9) HTML voice 본보기
10. `research/decisions.html`: 라운드 1~18 결정 트레일
11. `research/plan.html`: 연구 계획 본문 voice 본보기
12. `analysis/highway_grid/figures/irt_main.json`: 추정값 raw (수치 검증)

**figure 첨부** (필요 시):
- `analysis/highway_grid/figures/d1_rank_reversal_real.{pdf,png}`: Figure 2
- `analysis/highway_grid/figures/d2_trial_split.{pdf,png}`: Figure 3
- `analysis/highway_grid/figures/d3_ablation_real.{pdf,png}`: Figure 4
- `analysis/highway_grid/figures/irt_main.{pdf,png}`: Figure 5

### Step 4: 첫 대화로 본문 voice 작성 시작

Project 안에서 새 chat을 시작하고 다음 같은 첫 요청을 입력한다.

```
SESSION_START_PROMPT.md의 흐름을 따라 본 프로젝트의 학술 voice를 파악했다. 
이제 본문 voice 작성을 §1 Introduction 첫 단락부터 시작한다. 

본 단락의 voice는 다음을 따른다.
- 본보기: N0210370104.pdf (한글 학술 voice 1차 reference)
- voice 규칙: CLAUDE.md 절대적
- raw 자료: paper_data.md §1.1·1.2·1.3·1.4

§1.1 motivation 첫 단락의 voice를 작성한다. raw 자료의 인용 (Peng 2026 LD-Scene·Shen 2025·Riedmaier 2020·ISO 34501)이 첫 단락의 학술 anchor가 되도록 흐름을 잡는다.

본문 voice는 사용자 voice 규칙에 정합한 흐름으로 작성하되, 내가(사용자) 정정·재작성하는 흐름을 적극 수용한다.
```

---

## 2. 본문 작성 우선순위 (검토자 권고)

라운드 19 깊은 검토자가 본문 voice 단계의 우선순위를 다음과 같이 권고한다.

### 우선순위 1: 본질적 흠의 보수적 좁힘 (학술 정직성)

**Contribution voice 좁힘**:
- §1.4 (2) "다수의 AV 정책 위에서 척도 보존" → "Defensive RL 세 시드의 학습 분산 위에서 척도 안정"
- §1.4 (3) "표준 단순 생성기 묶음 위에서 척도 안정" → "본 격자의 세 학습 흐름(ACARL Method A·Naive·Rule-based) 위에서 척도 안정"

본 좁힘이 학술 정직성을 강화하고 reviewer 변호의 강도를 높인다.

**Method B·계단함수 신호의 본문 voice 처리 (라운드 19 정정 자료)**:
- Method B 변별력 â를 §Results 본문에 정직히 적기 (단조성 통과 ≠ 변별력 강함). av18·N=18·K=70 fit에서 â=2.19, av20·N=20·K=20 fit에서 â=2.08. ACARL G 두 자료(cut-in 24.43·30.65, rear-end 30.65·7.39)의 1/12~1/14 수준.
- cut-in·rear-end â의 양면 자료를 §Results 부가 진단 단락으로 풀어 적기 (§Limitations 한 줄로 부족). av18 자료에서 cut-in â=24.43·rear-end â=30.65로 자릿수가 라운드 18 av20 자료(â≈14.3)에서 더 커진 자료, K=70 trial 풍부함이 변별력 식별성을 강화하지만 ICC가 계단함수에 접근하는 식별성 경계 신호를 §Limitations에 정직히 명시.

### 우선순위 2: Ref Needed 자료 확정 (본문 작성 전)

Motivation 핵심 3 reference 즉시 확정:
- **Shen 2025 (AAP)**: 정확한 저자 풀네임·논문 제목·DOI·페이지 (§1.1 첫 단락의 강한 정량 anchor)
- **Peng 2026 LD-Scene (TR-C)**: 정확한 서지 (rank reversal 발견의 학술 anchor)
- **Qiu 2026 (TR-C)**: 정확한 서지 (SUT 의존성의 직접 예)

본 3 reference 확정 흐름:
1. Google Scholar에서 "Shen 2025 autonomous vehicle scenario" 검색
2. arXiv 또는 해당 저널 홈페이지에서 정확한 DOI·페이지 확보
3. paper_references.md §1·§2의 BibTeX 정정

나머지 ref needed 12개는 본문 작성 중 인용이 등장하는 시점에 확정해도 됨.

### 우선순위 3: ACARL self-citation 처리 결정

paper_references.md §10에 두 옵션이 적혀 있다.
- 옵션 A: 서론 위치선정에서 ACARL을 본 측정 모델의 핵심 데이터 anchor로 명시 (학술 강도 명확)
- 옵션 B: §Related Work에서 ACARL을 자율주행 적대 시나리오 생성의 한 자료로 분류 (self-citation 의존성 분산)

**검토자 권고**: ACARL이 본 AAAI 제출 시점에 arXiv preprint 게재되지 않으면 self-citation의 학술 anchor가 검증 불가 상태이다. arXiv 게재 결정이 본문 voice 작성보다 선행되어야 reviewer 변호가 정합하다.

### 우선순위 4: Figure 1 (motivation) 산출 결정

paper_figures.md의 두 옵션 중 결정:
- 옵션 A: LD-Scene·Shen 2025 rank reversal 시각화 (motivation의 학술 anchor 강화)
- 옵션 B: 측정 모델 conceptual schematic (방법론 직관 강화)

검토자 권고는 옵션 A. §1 Introduction 첫 단락의 학술 anchor가 한 figure로 visual하게 받쳐지면 본 논문의 motivation 강도가 크게 올라간다.

---

## 3. 본 시점의 게재 가능성 (보수적 평가)

라운드 19 깊은 검토자의 보수 평가:

| 시나리오 | 게재 가능성 |
|---------|----------|
| 본 시점 그대로 본문 voice 작성 (라운드 18) | 약 25~35% |
| 검토자 권고 본질 흠 보수적 좁힘 후 | 약 30~40% |
| ACARL arXiv 게재 + N 확장 future work 실험 자료 | 약 40~50% |
| **N=20 응시자 확장 완료 (라운드 19, 본 시점)** | **약 45~60%** |
| + ACARL arXiv 게재 + Figure 1 motivation 산출 | 약 50~65% |

AAAI 메인 트랙의 매년 acceptance rate가 20~25%인 점을 고려하면 본 시점의 25~35% 자료가 평균보다 약간 높은 수준이며, 본질 흠 좁힘 후 30~40%가 borderline accept 자릿수에 가깝다.

---

## 4. 본 시점의 미결 자료 (사용자 결정 필요)

1. **ACARL arXiv 게재 시점**: 본 AAAI 제출보다 선행 또는 동시
2. **ACARL self-citation 본문 위치**: 서론 위치선정 vs §Related Work
3. **Figure 1 산출 결정**: rank reversal 시각화 vs method schematic
4. **응시자 N 확장 future work 실험**: 본 AAAI 제출 전 TransFuser·MILE 도입 시도 여부
5. **Contribution voice 좁힘 수준**: 검토자 권고대로 보수 좁힘 vs 본 시점 voice 유지
6. **AAAI double-blind anonymity 처리**: AAAI 메인 트랙은 double-blind review를 요구하므로 본 원고에서 저자명·소속·acknowledgement·식별 가능 self-citation의 처리 규약을 본문 작성 단계의 첫 결정 항목으로 명시한다. 구체로는 (a) ACARL self-citation 표기를 "Anonymous (under review)"로 일관 익명화 (AAAI-26 Review Process·Submission Instructions 공식 voice, paper_references.md ACARL2026 BibTeX의 `author = {{Anonymous}}`와 일관), (b) 저자 소속을 본문 어디에도 노출하지 않음(`[Affiliation, anonymized]` 또는 자동 익명화 placeholder로 처리), (c) acknowledgement·funding 단락을 camera-ready 단계로 유보, (d) supplementary material에 저자 식별 가능한 코드 repository URL 노출 회피(익명 mirror 또는 anonymous.4open.science 활용). 본 anonymity 규약을 paper_data.md·paper_references.md의 본문 작성 단계에서 일관 적용한다.

---

## 5. 새 환경에서 즉시 가능한 작업

Claude 웹 환경에서 Project 생성과 파일 첨부 후 다음 작업을 즉시 시작 가능하다.

### 즉시 1: §1 Introduction 첫 단락 voice 작성
- raw 자료: paper_data.md §1.1
- 인용: Shen 2025·Peng 2026·Riedmaier 2020·ISO 34501
- 본보기: N0210370104.pdf 서론 voice

### 즉시 2: §3 Method 본문 voice 작성
- raw 자료: paper_data.md §3.1·§3.2·§3.3 + method.html §s2~§s5
- 식 (1)~(9)의 본문 voice (수식은 LaTeX 형식)
- 본보기: method.html 본 voice

### 즉시 3: Ref needed 확정
- Google Scholar 검색
- paper_references.md §9의 15개 자료 서지 확정
- BibTeX 자료 정정

본 세 작업이 본문 voice 작성의 첫 1~2주 작업이다.

---

## 6. 본 시점 라운드 1~18 정리 자료 (정리·보존됨)

본 시점에서 정리·정정 완료된 자료는 다음과 같다. Claude 웹 이전 후 이 자료들은 변경 없이 활용된다.

- ✅ 측정 모델 형식화 (method.html 식 (1)~(9))
- ✅ 실험 격자 (highway-env, 응시자 N=20·G 4종·c 5수준·K=70 av18 fit + K=20 av20 통합 fit, 약 26,000 episode)
- ✅ 분석 결과 (D1·D2 trial-split·D3·fit_irt_main 모두 통과)
- ✅ 결정 트레일 라운드 1~18 (decisions.html)
- ✅ 본문 작성용 raw 자료 (paper_data·paper_figures·paper_references)
- ✅ figure 6종 산출 (irt_main 등)
- ✅ 라운드 17·18 정정 (CARLA 종결·SE 야코비안 보정·voice 정정)

미정정 잔여 (검토자 권고 미반영, 본문 voice 단계에서 사용자가 직접 처리):
- ⚠️ Contribution 2·3 voice 좁힘 (학술 정직성)
- ⚠️ ACARL self-citation 위치 결정·arXiv 게재
- ⚠️ Ref needed 15개 서지 확정
- ⚠️ Figure 1 산출

---

본 가이드를 따라 Claude 웹으로 이전하면 본문 voice 작성 단계가 막힘 없이 진행된다. 본 시점에서 추가로 정정·확정이 필요한 자료가 발견되면 Claude 웹의 첫 대화에서 사용자가 직접 알려 주는 흐름이 정합하다.
