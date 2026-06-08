# 라운드 19 정정 전파 점검 프롬프트 (실험 컴퓨터 인계용)

> 이 파일을 리눅스 실험 환경(저장소 root `<anonymized-repo-root>`)의 Claude Code 첫 대화에 그대로 붙여 넣는다.
> CLAUDE.md voice 규칙은 자동 로드된다. 아래 임무를 그 환경에서 수행한다.

---

## 임무 한 줄

라운드 19(응시자 N=3 → N=20 확장) 정정이 `paper_data.md` §1.4·§5와 fit JSON에는 반영됐지만, 같은 파일의 §4·§6.4·§6.5·§8과 `paper_figures.md`, 일부 오리엔테이션 문서에는 옛 N=3·5 수치가 남아 있다. **각 불일치를 실제 자료·스크립트로 재확인하고, 확인된 항목마다 구체적 정정안(어느 파일 어느 줄을 무엇으로)을 제시하라. 실제 편집은 사용자 승인 후에만 한다.** 지금 단계에서 파일을 고치지 마라.

이 점검은 Windows 환경 Claude가 1차로 찾아낸 결과를 인계한 것이다. Windows 쪽에서 직접 재현·확인한 항목과 아직 재현하지 못한 항목을 아래에 구분해 두었으니, 후자는 이 환경에서 반드시 다시 돌려 확인하라.

---

## 0. 먼저: 무엇이 ground truth인가

수치의 기준은 다음 산출물이다. 본문·figure raw 자료는 여기에 맞춰야 한다.

- `analysis/highway_grid/figures/irt_main_av18.json` — N=18·K=70 (학습 응시자만, D 분석 핵심)
- `analysis/highway_grid/figures/irt_main_av20.json` — N=20·K=20 (IDM·MOBIL 포함, 본문 주 자료)
- `analysis/highway_grid/figures/irt_main.json` — **N=3 옛 자료. 폐기 대상.** 본문·figure가 아직 이 값을 쓰면 그게 정정 대상이다.
- 응답 자료: `responses_av18_learned.jsonl`(25,200줄), `responses_av20_combined.jsonl`(26,000줄), `responses_def_rl_combined.jsonl`(4,200줄, N=3)
- 분석 스크립트: `analysis/highway_grid/analyze_monotonicity_jsonl.py`(D1), `analysis/highway_grid/d2_trial_split.py`(D2), `analysis/d-grid-validation/d3_ablation.py`(D3), `analysis/highway_grid/fit_irt_main.py`(추정값)

### Windows 쪽에서 이미 재현·확인한 항목 (그대로 신뢰 가능, 다만 환경 옮겼으니 한 번 더 확인 권장)

- **D1 단조성 (N=18)**: `analyze_monotonicity_jsonl.py --jsonl responses_av18_learned.jsonl` 실행 결과 cut-in ρ=0.900(PASS)·rear-end ρ=0.700(PASS)·method_b ρ=0.000(**FAIL**)·method_c ρ=0.900(**PASS**). `paper_data.md` §5.1 표와 일치 확인됨.
- **θ̂·생성기 추정값**: `irt_main_av18.json`·`irt_main_av20.json`의 모든 값이 `paper_data.md` §5.5 표와 소수점까지 일치. 표의 95% CI half-width = 1.96 × `se_theta`도 일치 확인됨.

### 아직 재현하지 못한 항목 (이 환경에서 반드시 다시 돌려 확인하라)

- **D2 trial-split (N=18)**: 본문 §5.2가 적은 r mean=0.996·p25=0.996. 아래 명령으로 재현해 확인.
- **D3 ablation (N=18)**: 본문 §5.4가 적은 no_severity Δ=195,116(df=4)·g_common Δ=4,454(df=12)·u_zero Δ=+36.83. 아래 명령으로 재현해 확인.

### 재현 명령 (저장소 root에서 실행, 의존성: numpy·scipy)

```bash
# D1 단조성 (이미 확인됨, 재확인용)
PYTHONIOENCODING=utf-8 python3 analysis/highway_grid/analyze_monotonicity_jsonl.py \
    --jsonl analysis/highway_grid/responses_av18_learned.jsonl

# D2 trial-split (재현 필요: 0.996/0.996 확인)
PYTHONIOENCODING=utf-8 python3 analysis/highway_grid/d2_trial_split.py \
    --jsonl analysis/highway_grid/responses_av18_learned.jsonl

# D3 ablation (재현 필요: 195,116 / 4,454 / +36.83 확인)
PYTHONIOENCODING=utf-8 python3 analysis/d-grid-validation/d3_ablation.py \
    analysis/highway_grid/responses_av18_learned.jsonl

# fit 재현 (av18 JSON과 일치 확인)
PYTHONIOENCODING=utf-8 python3 analysis/highway_grid/fit_irt_main.py \
    --jsonl analysis/highway_grid/responses_av18_learned.jsonl --out-prefix /tmp/irt_av18_repro

# JSON 값 직접 확인
python3 -c "import json; d=json.load(open('analysis/highway_grid/figures/irt_main_av18.json')); print('a_hat', d['a_hat']); print('gamma', d['gamma_hat']); print('u', d['u_hat'])"
```

스크립트 인자 형식이 위와 다르면(파일이 갱신됐을 수 있다) 각 스크립트의 `argparse` 정의를 먼저 확인하고 맞춰 실행하라. 재현 값이 본문 수치와 어긋나면, 그 자체가 새로운 정정 대상이니 보고에 포함하라.

---

## 1. 점검·정정안 제시 대상 (확인된 불일치)

각 항목에 대해 (i) ground truth로 재확인한 결과, (ii) 현재 파일에 적힌 옛 값, (iii) 제안하는 정정 내용을 보고하라. **편집은 승인 후.**

### 항목 A — `paper_data.md` §4 Experiment가 아직 N=5 격자

- §4.2 제목이 "응시자 가족 (N=5)"이고 IDM·MOBIL·Defensive RL 3종만 나열. §4.5 K 자료도 통합 5,000 episode 기준.
- §1.4·§5는 N=20(PPO 5·SAC 5·TD3 5 추가)으로 갱신됨. §4만 옛 격자를 설명해 본문 안에서 응시자 수가 어긋난다.
- 정정안 제시: §4.2~§4.5를 N=20 격자(20종 응시자, av20=26,000 + av18=25,200 episode 구성)로 다시 쓰되, 응시자 선택 근거·시드 학습 시간 등 라운드 19 plan §12·decisions 단락의 사실과 맞춘다. 어떤 문단을 어떻게 고칠지 초안을 제시.

### 항목 B — `paper_data.md` §6.4 변별력 수치가 N=3 값

- 현재 "Method B â=0.561", "cut-in·rear-end â≈14.3"으로 적힘. 이는 옛 `irt_main.json`(N=3) 값.
- ground truth: N=18 기준 method_b â=2.188, cut-in â=24.430, rear-end â=30.653 / N=20 기준 2.081, 6.639, 7.390.
- 정정안: §6.4를 §5.5가 쓰는 두 fit(av18/av20) 값으로 교체. §5.5는 이미 "K=70에서 â가 더 커진다"는 양면 진단을 정직하게 적고 있으니 §6.4도 그 틀에 맞춘다.

### 항목 C — `paper_data.md` §6.5가 폐기된 주장을 한계로 서술 (가장 시급)

- §6.5는 Method C 음의 단조성 ρ=−0.821을 현재 한계로 기술. 그러나 §5.6과 §1.4는 이 음의 단조성이 **N=3·5의 가짜였고 N=18에서 +0.900으로 정정·폐기**됐다고 명시. 같은 파일 안에서 정면 충돌.
- 정정안: §6.5를 §5.6과 정합하게 다시 쓴다. "음의 단조성 한계"가 아니라, §1.4가 정한 방향대로 "N 확장 후 부호가 정정된 발견 → 본 측정 모델의 응시자 다양성에 대한 강인성"으로 재서술하거나, γ_G 양수 강제 제약만 일반적 한계로 남기고 Method C 음의 단조성 언급은 제거. 어느 쪽이 §5.6과 가장 정합한지 초안 두 안으로 제시.

### 항목 D — `paper_data.md` §8 Conclusion이 전부 N=3·5 값

- 현재: D1 "cut-in 0.821·rear-end 0.700·method_b 0.700 통과", D2 "0.917", D3 "2552.53·482.16", contribution (3)에 "Method C 사례 진단 능력".
- ground truth: D1 cut-in 0.900·rear-end 0.700·method_c 0.900 통과(**method_b는 FAIL**), D2 0.996, D3 195,116·4,454. Method C 진단 능력 주장은 폐기됨.
- 정정안: §8을 §1.4(갱신된 3 contribution)와 §5 수치로 다시 쓴다.

### 항목 E — `paper_figures.md` Figure 3 (D2) 수치·통과 G가 옛값

- 현재 "r mean=0.939", "단조성 통과 3 G (cut-in·rear-end·method_b)"로 적힘.
- ground truth: r mean=0.996(재현 확인 후 확정), 통과 G는 cut-in·rear-end·**method_c**(method_b는 FAIL).
- 정정안: 수치와 통과 G 목록 교체.

### 항목 F — `paper_figures.md` Figure 5 (irt_main) 패널이 N=3 값

- 패널 (a) θ̂가 3종(def_rl_42/456/789, −0.836/−0.569/+1.406), (c) γ̂(0.054/0.196/0.194/0.025), (d) û(0.089/0.099/0.027/0.029) 모두 옛 `irt_main.json`(N=3). Title도 "Defensive RL 3 seeds".
- ground truth: av18/av20 JSON 값. (a)는 N=18 18종 θ̂ 또는 N=20 20종, (c)(d)는 두 fit 값으로 교체.
- 정정안: Figure 5 raw 자료 블록 전체를 av18/av20 기준으로 재작성. §5.5가 두 fit을 모두 보존하므로 figure raw도 두 fit 명시.

### 항목 G — `paper_figures.md` Figure 2 (D1) caption이 N=5

- 현재 "AV=5, n_scen=1000", 응시자 5종 나열(def_rl 3 + idm + mobil).
- 정정안: D1 source가 N=18(`responses_av18_learned.jsonl`)이므로 caption baseline을 N=18 기준으로 갱신.

### 항목 H — D1·D3 그림 파일이 N=5 시절 그대로 (재산출 필요)

- `figures/d1_rank_reversal_real.{pdf,png}` (6월 4일), `figures/d3_ablation_real.{pdf,png}` (6월 5일)이 N=5 산출물. D2·irt_main av18/av20은 6월 7일 라운드 19에 재산출됨.
- 정정안: D1·D3 산출 스크립트를 `responses_av18_learned.jsonl` 입력으로 재실행해 두 그림을 N=18 자료로 다시 그린다. 산출 스크립트 정확 경로(`analysis/d-grid-validation/` 또는 `analysis/highway_grid/`)를 먼저 확인하고, 입력 자료 인자가 av18을 받는지 점검. 재산출은 그림이라 가볍지만, 이것도 승인 후 실행.

### 항목 I — `SESSION_START_PROMPT.md`의 계단함수 "정정" 서술이 본문과 충돌

- SESSION_START_PROMPT는 cut-in·rear-end â 계단함수가 "N 확장으로 자연스러운 sigmoid로 정정"됐다고 적음(N=20·K=20의 6.6·7.4만 보고).
- 그러나 `paper_data.md` §5.5는 이를 "av20만 보고 적은 거짓 안도"로 철회하고, N=18·K=70에서 â=24.4·30.7로 **오히려 더 커진다**고 정직히 밝힘.
- 정정안: SESSION_START_PROMPT의 해당 줄을 §5.5의 양면 진단(trial 풍부할수록 식별성 경계 신호가 강해짐)에 맞춘다.

### 항목 J — `research/method.html` §243~§245의 시점 충돌

- §243·§244는 방법 형식화 본문인데 옛 N=3 값(â=14.3, Method B 0.561, Method C 음의 단조성 "진단 능력")을 현재 주장처럼 서술하고, §245에서야 라운드 19 정정을 덧붙인다. 한 페이지에서 옛 주장과 철회가 같이 읽혀 혼동.
- 정정안: §243·§244를 현재 추정값으로 갱신하거나, 최소한 문단 머리에 "아래 §245 라운드 19에서 정정됨"을 명시. (이건 결정 트레일이 아니라 방법 본문이므로 정정 가능.)

### 항목 K — `REVIEW_FIXLIST.md`·`HANDOFF.md`의 시점 표시

- REVIEW_FIXLIST(6월 6일, N=3 시점)의 일부 항목(B-1 u_zero 음수, A-1 SE 부풀림)은 N 확장으로 이미 해소. HANDOFF(6월 2일)는 라운드 19 이전.
- 정정안: 두 파일을 내용 수정 없이 보존하되, 헤더에 "라운드 19 이전 문서. 현재 상태는 paper_data.md §5 기준" 한 줄만 추가.

---

## 2. 절대 건드리지 말 것 (의도된 결정 트레일)

다음은 "시점별 정직한 기록"이라 옛 수치가 그대로 보존되어야 한다 (CLAUDE.md 규칙). 정정 대상이 아니다.

- `research/decisions.html`의 라운드 1~19 단락 전부
- `research/plan.html` §233·§234(라운드 18·19 정정 단락), §238~§240(라운드 16 결과 단락)
- `AAAI_SUT_invariant_measurement_plan.md` §4(라운드 16·17 정정 단락), §12 7·8번, §14의 라운드별 기록
- `research/method.html` §245(라운드 19 정정 단락 자체)

이들 단락의 옛 ρ·â 값은 그 시점의 결정 기록이므로 보존한다. 라운드 17 이후 voice 규칙("자리" 어휘·메타포·em-dash 회피)은 새로 쓰는 정정안에만 적용한다.

---

## 3. voice 규칙 (정정안 작성 시)

- 흐르는 산문. 본문·figure caption은 불릿·표·라벨식 도식·메타 설명 회피.
- em-dash(—) 금지. 콜론(:)·가운뎃점(·)·en-dash(–) 사용.
- 메타포 금지(부품·묶음·척추·사다리·축·무게중심·토대·바닥·손잡이). "자리" 어휘 회피. 한 단락 "자료" 8회 이상 금지.
- "도입" 대신 "서론". 자연스러운 동사("측정한다"). 통계·기술 용어는 처음 나올 때 쉬운 말로 풀기.
- 본보기 한글 학술 voice: `N0210370104.pdf`.

---

## 4. 보고 형식

각 항목(A~K)에 대해 다음을 보고하라.

1. 재확인 결과: ground truth 값 / 현재 파일 값 / 일치 여부
2. (D2·D3는) 재현 명령 출력 요약
3. 제안 정정: 파일·줄 범위 + "현재 → 제안" 텍스트
4. 주의점·판단 필요 사항(특히 항목 C·J처럼 두 안이 가능한 경우)

마지막에 정정 우선순위를 제안하라. Windows 쪽 1차 검토의 권고 순서는 C(폐기 주장 충돌) → D(결론) → E·F(figure raw) → H(그림 재산출) → A(§4 격자) → B·G·I·J·K 였다. 이 환경에서 재현 결과에 따라 조정해도 된다.

**다시 강조: 이 단계에서 파일을 편집하지 마라. 위 보고를 사용자가 본 뒤 승인하면 그때 정정한다.**
