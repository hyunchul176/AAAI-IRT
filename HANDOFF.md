# HANDOFF · 새 기계(RTX 4080 리눅스)에서 이어가기

> 작성: 2026-06-02, Windows 노트북 세션 종료 시점.
> 새 기계에서 이 프로젝트 폴더로 이동해 Claude Code를 켜고 첫 메시지로
> **"HANDOFF.md와 research/roadmap.html 읽고 이어서 진행하자"** 라고 하면 된다.
> CLAUDE.md(voice·금지어 규칙)는 자동으로 로드된다.

## 프로젝트 한 줄

AAAI 메인 트랙 방법론 논문: 충돌률 기반 AV 적대 평가가 측정에 쓴 SUT에 따라 흔들리는 문제를,
IRT(문항반응이론)를 가져와 시나리오 난이도(b)와 AV 강건성(θ)을 하나의 SUT-불변 척도로 함께
측정한다. 주행 고유의 세 구조를 더한다: 반응성(reactivity, 난이도는 생성기 속성),
severity 조건화(난이도 조절 변수 c, 강건성 곡선과 c50), 회피가능성(회피불가 하한 u).
시험 비유를 일관되게 쓴다: 문항=시나리오, 수험생=AV, 오답=충돌.

## 산출물 지도

- `research/` · HTML 정리 사이트 (모든 페이지 다크모드 토글 있음)
  - `plan.html` 연구 계획 · `method.html` 측정 모델 형식화(식 1~9) · `roadmap.html` **수행 로드맵(진행 상태의 원본)**
  - `a1-identifiability.html` ~ `a4-labeler.html` · A 단계 결과 페이지 4장
  - `review/` · Literature Review 5섹션 30편 정독 카드 (index.html → sec-a~e.html)
  - `assets/a1/` · A 단계 그림들
- `analysis/a1-identifiability/` · A 단계 파이썬 코드와 결과 JSON
  (a1_recovery.py, a2_uncertainty.py, a3_covariates.py, a4_labeler.py)
- `pdfs/` · 논문 전문 PDF (+ `_xml/` Elsevier 전문 XML)
- `AAAI_SUT_invariant_measurement_plan.md` · 원본 계획 문서
- `_handoff/` · 이 인수인계용 사본들 (아래 "따로 옮길 것" 참조)

## 진행 상태 (2026-06-02 기준)

**Literature Review: 완료.** A(측정모델 IRT) 7편 · B(SUT 의존성 증거) 5편 ·
C(난이도 metric 선행) 5편 · D(회피가능성·귀책) 8편 · E(반응성·severity 생성) 5편.
모든 카드: 6파트 + 파트별 하이라이트 + 본문(abstract·서론 제외) 영어 인용 + PDF에서 추출한 figure.

**방법 형식화: 완료** (method.html). 전체 모델 식 (6):
P(충돌) = u(G,c) + (1−u)·σ(a_G(β_G + γ_G·c − θ_π)), θ~N(0,1).

**로드맵 A 단계(모델 확정): 4항목 모두 완료.** 핵심 결과:
- **A1 식별가능성**: u를 라벨로 고정하면 θ r=0.998, b r=0.999, a r=0.977, c50 r=0.996 복원.
  서로 겹치지 않는 두 AV 집단(강한 절반/약한 절반)으로 따로 보정해도 b̂ 일치 r=0.991(표본불변).
  같은 문항의 충돌률은 0.74 vs 0.44로 집단마다 다름(SUT 의존의 모의 재현).
  교훈: 격자는 충돌률이 중간 범위(~0.5대)에 걸쳐야 함. 천장(전부 충돌) 칸은 정보가 없음.
  u는 데이터만으로는 약식별(어려운 설계에서 r=−0.13, 쉬운 칸이 있으면 r=0.86).
- **A2 추정 절차**: MAP + Laplace 근사 + θ̂ 재표준화로 확정. Laplace 95% 구간이 자가 구현
  전처리 RWM MCMC와 일치(끝점 상관 ≥0.999, 5~18% 보수적). 40회 반복 coverage 95.2~96.3%.
  주의: 결합 중요도표본은 54차원에서 붕괴(ESS~10/20k) → 검증은 MCMC로.
  척도 자유(a↔θ·b 곱만 식별) 때문에 수렴 진단은 보고 양(표준화) 기준으로(원시 R̂ 1.08 vs 표준화 1.017).
- **A3 공변량(설명적 IRT)**: β=w·x+잔차 구조 검증. w 복원(0.92/−0.53/0.33 vs 참 0.90/−0.50/0.30),
  응답 없는 신규 생성기 난이도를 특징만으로 예측 r=0.951(RMSE 0.394, 잔차 하계 0.35에 근접).
  잔차를 빼면(LLTM) 보정 오차 2.2배 · 특징만으로 난이도를 정의하면 안 됨(섹션 C 교훈의 정식화).
- **A4 라벨러**: 오라벨 민감도(짝지은 비교). 피해는 θ*가 아니라 b*에 집중(라벨 틈을 난이도가 흡수).
  최악은 u=0 무시(현행 관행): θ* +43%, b* 4.2배. **방침: RSS를 사전 중심으로 한 soft 라벨링이 기본값**,
  LFR·over-critical 대안 중심 민감도 분석 + u=0 비교 보고.

**B1 시뮬레이터: CARLA (SafeBench + FREA 스택) 단독 확정.**
MetaDrive 보조 격자 안은 검토 후 채택하지 않음(논의·근거: research/decisions.html 시뮬레이터 선택 결정).
SafeBench(NeurIPS 2022, CARLA **0.9.13 권장**, 도커)가 적대 생성 4종 + RL ego 에이전트 제공,
FREA(CoRL 2024 Oral, github.com/CurryChen77/FREA)는 **SafeBench 포크**로
반응형 CBV + LFR 네트워크 구현 (LFR = soft 라벨 대안 중심값). RSS 라벨은 Khan 2026의 CARLA 전례.
유의: headless·도커 병렬, 버전은 SafeBench·FREA 권장 0.9.13.
사용자 호스트는 CARLA 0.9.16 native(~/carla_0916/)가 있으나 SafeBench와 3 minor 격차라
0.9.13을 도커로 별도 띄우는 것이 안전(SafeBench docker/run_docker.sh 제공).
합성 트랙(A·D-study 코드)과 2단 구성, 완전한 결정론 기대하지 않음(반복 변동은 반응성의 일부).

**실행 결정 트레일: research/decisions.html에 정식 기록 (동결).**
시뮬레이터 선택 (CARLA + SafeBench + FREA 단독) · 결정 트레일 보관 위치 · 격자 합격선 ·
표본불변성 검증 절차 (split-half) · 격자 후보 범위와 severity 배치 ·
평가 대상 AV 선정(SafeBench RL 4종 + 규칙 기반 2종 + PlanT 2종) ·
시나리오 생성기와 severity 조절 · 응답표 변환과 RSS 라벨링 ·
헤드리스 운용·2D BEV · 시드·시간·환경 통제 (Town·날씨·step).
잔여 위험은 응시자 수 부족 · split-half 검정력 부족 · 강건성 분산 부족 ·
severity 단조성 깨짐 · u 분포 쏠림 · 결과 파일 디스크 폭증 · GPU 인스턴스 수 일곱 가지.
검토자 에이전트 7 라운드 검토-정정
사이클을 거쳐 사실 오류·voice·환각·근거 없는 단정 약 50건이 본문에 박히기 전 잡혀 정정됨.
메모리에는 reference 한 줄만 두고 본문은 이 페이지에서 본다.

**D-study sweep: 완료** (`analysis/d-study/d_study.py sweep`, 32 코어 multiprocessing, 5h).
격자 후보 81개 × severity 배치 2종(uniform·adaptive) × 1000 trial × 50 split = 162 조합 평가.
결과: **162/162 모두 합격** (split r p25 ≥ 0.80, 응시자 수 부족 위험 자연 해소). AV별 평균 p25:
AV=4 0.881 · AV=6 0.908 · AV=8 0.927. severity 적응이 등간격보다 +0.006 평균 차이.
**Ablation 결정적**: 가장 작은 격자(AV=4·G=3·sev=3·K=10)에서 정보적 사전 끄면 0.81→0.37,
셀당 반복 K=5면 0.77로 둘 다 합격선 못 넘음(정보적 사전 + K≥10이 합격을 떠받침).
**MH DIF false-discovery rate가 AV별로 평탄(평균 0.74)하고 명목 α=0.05보다 자릿수가 한 자리 위**:
split-half 검정력 부족 위험의 양적 증거가 아니라 MH 진단의 한계. 검정력 답은 split r 자체로.
**θ̂ CI 폭 8~18 범위**(평균 12)로 격자 합격선 결정의 보조 합격선 0.5σ와 자릿수 다름: 시나리오 난이도는
안정적이나 개별 AV 강건성 정밀도는 본 격자에서 다시 평가.
**본 격자 권고 셋**: AV=6·G=3·sev=3·K=10 (540 cells, 작은 안전, θ̂ CI=9.2),
AV=6·G=4·sev=5·K=20 (2,400 cells, 중간), AV=8·G=4·sev=5·K=20 (3,200 cells, 큰).
θ̂ CI 더 줄이는 옵션: AV=6·G=5·sev=3·K=10 (900 cells, θ̂ CI=8.2).
결과 페이지: `research/d-study.html` (Fig 1~6 PNG 포함).

**B4 응답 기록 파이프라인: stub 작성** (`analysis/b4-pipeline/`).
sb_to_response.py (CellResponse dataclass + extract/append/collect 함수 시그니처),
bev_wrapper.py (BEVCellRecorder class, 4 저장 모드),
rss_labeler.py (RSS Shalev-Shwartz 2017 §3 종/횡 안전거리 + 대안 중심값 LFR·over_critical).
함수 본문은 NotImplementedError, B 단계 첫 작업에서 채움.

**사이트 구조 (GitHub Pages 임시 public + robots.txt 검색 차단)**:
URL <https://hyunchul176.github.io/AAAI-IRT/> → plan.html이 메인.
공개 6 페이지: plan(메인) · lit-review · roadmap · method · d-study 결과 · 정독 카드(review/).
로컬만(`.gitignore`): research/decisions.html · research/questions-log.html · research/index.html.
GitHub Education 승인되면 `gh api -X PATCH repos/hyunchul176/AAAI-IRT -f visibility=private`로
private 전환 + Pro plan에서 private Pages 호스팅.

## 다음 할 일

1. **(진행 중)** SafeBench 적대 생성기 자체 학습 (sb-pilot, LC→NF 직렬).
   `bash analysis/b4-pipeline/train_safebench_serial.sh`가 host 백그라운드(PID 2615889)에서
   LC 학습 완료를 polling 중. LC 약 26%·ETA 1:14. 완료 시 NF 학습 자동 시작.
   AdvSim·AdvTraj는 HardCodePolicy(`type='unlearnable'`) + parameters JSON 생성 절차 미공개
   → 격자에서 제외(`decisions.html` #d07 2026-06-03 갱신).
2. **단조성 pilot 2차**: LC·NF 학습 완료 후 `python3 analysis/b4-pipeline/pilot_monotonic_v2.py`로
   2 ego(SAC, behavior) × 2 G(LC, NF) × c 5수준 × K=10 = 200 cells 실행. `severity_injectors`의
   `SEVERITY_MAP['lc']` (sigma_scale 다이얼) + `SEVERITY_MAP['nf']` (flow_sigma=latent z 분산
   다이얼) 1차 후보를 monkey-patch로 검증. Spearman ρ ≥ 0.7 합격선·bootstrap 5%-low ≥ 0.5 보조.
   1차 가설 실패 시 가설 2(σ 반전)로 재시도. 두 가설 모두 실패하면 `method.html` 식 (6)의
   γ_G·c 비단조 일반화로 후퇴.
3. **본 격자 진입 조건**: 두 종 이상이 단조성 합격해야 split-half에서 G 부분집합 가르는
   표본불변성 검증이 의미를 갖는다(검토자 라운드 10). G=2 (LC+ordinary 또는 NF+ordinary) 한 종 합격은
   contribution이 "한 생성기 사례연구"로 좁아져 진입 보류.
4. **C 단계 격자 실행**: G=3 (LC+NF+ordinary) 단조성 합격 시 본 격자 실행. AV=6은 SAC + DDPG +
   PPO + TD3 + PlanT + behavior (라운드 9에서 expert·expert_disturb 제외). DDPG·PPO·TD3는
   학습 필요(load_model이 episode=None일 때 graceful 검색이라 patch 불필요).
5. **D 단계 검증**: D1(순위 역전 재현)·D2(표본불변 = 본문 핵심, `analysis/d-grid-validation/d2_split_half.py`)·
   D3(ablation)·D4(외적 타당성 = expert reference policy 충돌률 분포 비교).
5. **E 단계 원고**: AAAI 메인 트랙 형식.

## 작업 규칙 (CLAUDE.md가 원본, 자주 틀리는 것만 재강조)

- **voice**: 흐르는 산문, 통계 용어는 처음에 쉬운 말로, 시험 비유 일관 사용. em-dash(—) 금지.
- **금지어**(누적): 부품, 묶음, 척추, 사다리, 축, 무게중심, 주축, 토대, 바닥(→하한), 손잡이(→조절 변수),
  자백/자인, 선구자, 잰다(→측정한다), 배지·진행상태 라벨, "정독"을 상태 표현으로 쓰기.
  **HTML 수정 후 매번 grep으로 검증하는 습관**:
  `grep -cE "부품|묶음|척추|사다리|무게중심|주축|토대|바닥|손잡이|자백|자인|선구자|잰다|정독" <파일>` 과 `grep -c "—" <파일>`.
- **정독 카드**: `_handoff/skills/deep-review-card/` 스킬 절차를 따른다(6파트, 파트별 mark 1개,
  인용은 본문만, figure는 PDF 렌더 → 진단 크롭으로 잉크 경계 측정 → trim + 균일 테두리 → Read로 확인).
- **사실성**: 인용·수치 지어내지 않기, 미확인은 "확인 필요". 특정 논문은 full PDF로 검증.
  leapspace는 광역 서베이 전용.
- 모수 표기: 모델·코드·페이지 전반에서 method.html 표기(θ, β, γ, a, u, c, c50)를 따른다.

## 환경 메모 (리눅스에서 준비할 것)

- 파이썬: numpy·scipy·matplotlib (A 코드는 이것만 씀). 실행 시 `PYTHONIOENCODING=utf-8`.
  현재 리눅스에 python3.13.12 + numpy 1.26 / scipy 1.17 / matplotlib 3.10 ✓.
- PDF 도구: poppler-utils(pdftoppm, pdftotext, pdfinfo) ✓ 설치됨.
  **ImageMagick은 미설치**: 정독 카드 figure 크롭 전에 `sudo apt install imagemagick` 필요(사용자 비번 요).
- A 코드 실행 예: `PYTHONIOENCODING=utf-8 python3 analysis/a1-identifiability/a1_recovery.py`
  (그림은 research/assets/a1/에 저장됨).
- D-study sweep 재실행: `PYTHONIOENCODING=utf-8 python3 analysis/d-study/d_study.py sweep`
  (5h, 32 코어). 그림 재생성: `python3 analysis/d-study/make_figures.py`.
- Elsevier 전문/figure API: 키는 `~/.config/research_keys.env` (아래 참조).
  사용 예는 transcripts나 review 카드 작업 이력 참조 (X-ELS-APIKey 헤더, content/object/eid/...-grN_lrg.jpg).
- **B 단계 환경 (이미 잡힘)**: docker 29.3.0 ✓, nvidia-container-toolkit ✓, RTX 4080 16GB ✓,
  CARLA 0.9.16 native ~/carla_0916/ (참고용; SafeBench 도커가 0.9.13 별도로 띄움).
  SafeBench/FREA 코드는 `external/SafeBench/`·`external/FREA/`에 clone돼 있음(`.gitignore` 처리).
- **검토자 에이전트**: 정식 등록 `.claude/agents/research-reviewer.md` (model=opus, read-only tools).
  큰 결정·결과 페이지가 한 매듭 지을 때 호출하면 사실 오류·voice·환각·근거 없는 단정을
  찾아 줌. 직전 결정 페이지 + d-study 결과 작성에서 약 50건 잡힘. 다음 세션에서
  Agent({subagent_type: "research-reviewer", ...}) 호출 가능 (현재 세션에서는 호출 시점
  이전 등록이라 우회로 general-purpose에 동일 프롬프트 넘김).

## 이전 완료 상태 (2026-06-02 리눅스 이관)

1. `_handoff/skills/deep-review-card/` → `~/.claude/skills/deep-review-card/` ✓ 복사 완료.
2. `_handoff/memory/` 4개 파일(MEMORY.md 인덱스 + aaai-sut-research + writing-style-corrections + decisions-log)
   → `~/.claude/projects/-home-hyunchul-AAAI/memory/` ✓ 복사 완료.
3. **API 키** ✓ `~/.config/research_keys.env` (chmod 600)에 ELSEVIER_API_KEY·WILEY_TDM_TOKEN 등록.
   주의: 키는 이번 이관 과정에서 평문 노출되었으므로 Elsevier·Wiley 포털에서 재발급 권장.
4. `_handoff/transcripts/` 는 그대로 둠. 과거 맥락이 궁금할 때 grep으로 읽으면 됨.

## 새 기계 첫 메시지 (이대로 붙여 넣기)

```
이 프로젝트는 Windows 노트북에서 진행하다 이 리눅스 머신(RTX 4080)으로 옮겨온 것이다.
다음 순서로 시작하자.

1. 상태 파악: HANDOFF.md와 research/roadmap.html을 읽어라.
   (CLAUDE.md의 voice·금지어 규칙은 항상 적용한다.)

2. 인수인계 자산 설치:
   - _handoff/skills/deep-review-card/ 를 ~/.claude/skills/deep-review-card/ 로 복사해
     정독 카드 스킬을 등록해라.
   - _handoff/memory/ 의 파일들(MEMORY.md 인덱스 포함)을 너의 auto-memory 디렉토리에
     그대로 저장해 이전 메모리를 이어받아라.

3. 환경 점검 후 빠진 것을 보고해라:
   - python3 + numpy·scipy·matplotlib
   - poppler-utils (pdftoppm, pdftotext, pdfinfo)
   - ImageMagick (magick 또는 convert, 리눅스는 convert일 수 있음)
   - ~/.config/research_keys.env 존재 여부만 확인해라 (내용은 읽지 마라.
     없으면 내가 직접 넣어야 하니 알려만 줘.)
   - 동작 확인 삼아 PYTHONIOENCODING=utf-8 python3 analysis/a1-identifiability/a1_recovery.py
     를 한 번 돌려 research/assets/a1/ 에 그림이 생성되는지 확인해라.

4. 위가 끝나면 합의해 둔 다음 단계부터 이어간다:
   D-study(격자 규모 설계, 로드맵 C2 앞당김). AV 몇 대 × 생성기 몇 개 × severity 몇 수준 ×
   반복 몇 회면 목표 신뢰도가 나오는지를 A 단계 코드(Fisher 정보량 + 복원 실험)로 계산해,
   CARLA 격자의 계산 예산 근거를 만든다.
```

사용자가 손으로 할 일은 하나뿐: API 키 파일을 USB 등으로 옮겨
새 기계 `~/.config/research_keys.env` 에 두기 (chmod 600).
