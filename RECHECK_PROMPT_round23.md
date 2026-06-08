# 라운드 23 마무리 점검 프롬프트 (그림 재산출·교차참조·표기 정합)

> 이 파일을 리눅스 실험 환경(저장소 root)의 Claude Code 첫 대화에 그대로 붙여 넣는다.
> CLAUDE.md voice 규칙은 자동 로드된다. 경로는 모두 저장소 root 기준 상대경로다.

---

## 임무 한 줄

라운드 19~22 정정으로 본문 raw 자료(`paper_data.md`·`paper_figures.md`)의 수치 정합성은 거의 정리되었다. 남은 마무리 항목은 네 가지다. **각 항목을 실제 자료·스크립트로 재확인하고 정정안을 제시하라. 텍스트 편집과 그림 교체(파일 덮어쓰기)는 사용자 승인 후에 한다.** 단, 그림 코드의 버그 진단과 재산출 실행 자체는 "정확한 숫자를 알아내기 위한 검증"이므로 scratch로 돌려 결과를 보고하는 데까지는 진행한다.

이 점검은 Windows 환경 Claude가 라운드 22 결과를 재검토한 뒤 인계한 것이다. Windows 쪽 재현 결과를 각 항목에 적어 두었으니, 이 환경에서 다시 돌려 대조하라.

---

## 0. ground truth (라운드 22 재검토에서 재현 확인됨)

다음은 Windows 환경에서 직접 재현해 본문과 일치를 확인한 값이다. 이 환경에서 한 번 더 대조하라.

- **D1 단조성 (N=18)**: cut-in 0.900·rear-end 0.700·method_b 0.000(FAIL)·method_c 0.900. `paper_data.md` §5.1과 일치.
- **D2 trial-split (N=18)**: 전체 4 G r=0.994·p25=0.993, 통과 3 G r=0.996·p25=0.996. §5.2와 일치.
- **θ̂·생성기 추정값**: av18·av20 JSON이 §5.5 두 표와 소수점까지 일치.
- **cross-fit 상관 (공통 18명)**: Spearman ρ=0.9587·Pearson r=0.9913. §5.5 라운드 22 주장과 일치.
- **D3 deviance (N=18)**: 부호·자릿수는 본문과 일치하나 **정확한 값이 MAP 적합 seed·수렴에 따라 흔들린다.** Windows 재현값은 no_severity 195,866·g_common 4,479·u_zero +62.3 (문서값 195,116·4,454·+36.83). 핵심 결론(u_zero 양수 → 옛 −18.04 음수 흠 해소)은 안정적이나 정확한 숫자는 재현마다 다르다. 항목 3에서 다룬다.

---

## 1. 남은 항목 (정정안 제시 대상)

### 항목 1 — D1·D3 그림 파일이 N=5 시절 그대로 (코드 버그 진단 + N=18 재산출) [최우선]

- `analysis/highway_grid/figures/d1_rank_reversal_real.{pdf,png}`(2026-06-04)·`d3_ablation_real.{pdf,png}`(2026-06-05)이 N=5 산출물. D2·irt_main av18/av20은 라운드 19에 재산출됐으나 이 두 그림만 남았다.
- 막힌 원인 (paper_figures.md Figure 2 주석에 기록됨): `analysis/d-grid-validation/d1_figure.py` 실행 시 빈 배열 quantile에서 `IndexError: index -1 is out of bounds for axis 0 with size 0`. `d3_figure.py`도 같은 자료 구조 흠 가능.
- 할 일:
  1. `d1_figure.py`·`d3_figure.py`의 입력 인자가 `responses_av18_learned.jsonl`(N=18)을 받는지 확인하고, IndexError를 진단한다(빈 배열이 어디서 생기는지: N=18 응시자 자료에서 특정 cell이 비어 quantile 계산이 깨지는지).
  2. 코드 흠을 정정한 뒤 N=18 입력으로 두 그림을 scratch 경로(`/tmp/d1_av18.png` 등)에 재산출해 결과 수치를 보고한다.
  3. **D1 rank reversal 패널 (Figure 2a)의 수치**: 현재 caption baseline(paper_figures.md)에 mean ρ=0.99·p25=1.00으로 적혀 있으나 이는 N=5 값이고 N=18로 재계산되지 않았다. 재산출 후 N=18 값으로 확정해 caption과 §5.1 본문을 맞춘다.
  4. 그림 파일 덮어쓰기(`figures/` 교체)는 승인 후.

### 항목 2 — `paper_data.md` §3.1 교차참조 오류

- §3.1의 u_G 자유 추정 식별성 단락(라운드 21 보강) 끝이 "본 한계를 §6.5에 정직 명시"로 적혀 있다. 그러나 §6.5는 γ_G 양수 강제 제약 단락이고, 여기서 말하는 변별력 â의 ceiling 식별성 한계(â=24~31)는 §6.4에 있다.
- 정정안: 해당 교차참조를 "§6.5" → "§6.4"로 바꾼다. (같은 문장이 이미 §5.5·§6.4를 인용하고 있으니 §6.4가 정합.)

### 항목 3 — D3 deviance의 seed 민감성 (그림과 본문 숫자 동기화)

- 위 0번에 적었듯 D3 deviance 정확값이 재현마다 흔들린다(예: no_severity 195,116 vs 195,866). 본문 §5.4·paper_figures Figure 4·그림 파일이 서로 다른 숫자를 들고 있으면 reviewer가 짚는다.
- 할 일:
  1. `d3_ablation.py`(또는 `d3_figure.py`)에서 deviance 산출의 random seed를 명시적으로 고정한다(`fit_variant(..., seed=0)` 등 이미 seed 인자가 있으면 그 값으로 통일).
  2. 고정 seed로 한 번 돌린 출력값을 정본으로 삼아 §5.4·Figure 4 caption·그림 이미지(항목 1의 d3 재산출)가 모두 같은 숫자를 쓰게 맞춘다.
  3. 본문에 "정확한 deviance는 적합 seed에 따라 ±1% 내에서 변동하나 부호·자릿수·결론은 불변"을 한 문장으로 정직 명시할지 사용자에게 제안한다.

### 항목 4 — `paper_figures.md` 표기 예시가 옛 값 (미용)

- 파일 끝 "수치 표기 voice" 예시에 LR=2552.53·θ̂=−0.836 ± 1.808 같은 옛(N=3·라운드 18 이전) 값이 형식 예시로 남아 있다. 주장이 아니라 표기 형식 예시일 뿐이나 혼동을 준다.
- 정정안: 예시 수치를 현재 값(예: deviance·θ̂ av18 기준)으로 교체.

---

## 2. 재현·진단 명령 (저장소 root, 의존성 numpy·scipy)

```bash
# D1·D3 그림 스크립트 인자·구조 확인
sed -n '1,40p' analysis/d-grid-validation/d1_figure.py
sed -n '1,40p' analysis/d-grid-validation/d3_figure.py

# D1 그림 재산출 시도 (IndexError 재현·진단)
PYTHONIOENCODING=utf-8 python3 analysis/d-grid-validation/d1_figure.py \
    --jsonl analysis/highway_grid/responses_av18_learned.jsonl   # 인자명은 argparse 확인 후 조정

# D3 deviance 정확값 재현 (seed 고정 확인)
PYTHONIOENCODING=utf-8 python3 - <<'PY'
from pathlib import Path
import importlib.util, sys
sys.path.insert(0, 'analysis/d-grid-validation')
import d3_ablation as m
rows = m.load_responses(Path('analysis/highway_grid/responses_av18_learned.jsonl'))
resp = m.build_resp_dict(rows)
full = m.fit_variant(resp, 'full', seed=0)
fnll = m.neg_loglik_orig(resp, full, 'full')
for v in ['no_severity','g_common','u_zero']:
    fv = m.fit_variant(resp, v, seed=0)
    print(v, '%.2f' % (2*(m.neg_loglik_orig(resp, fv, v) - fnll)))
PY
```

---

## 3. 절대 건드리지 말 것 (결정 트레일 보존)

`research/decisions.html`·`research/plan.html`(라운드 단락)·`AAAI_SUT_invariant_measurement_plan.md`(§4·§12·§14)·`research/method.html` §245의 라운드별 기록은 시점별 정직한 기록이라 옛 수치를 그대로 둔다. 이번 정정은 본문 raw 자료(paper_data·paper_figures)와 그림 파일·코드에 한정한다.

## 4. voice 규칙

흐르는 산문. em-dash(—) 금지(콜론·가운뎃점·en-dash 사용). 메타포 금지(부품·묶음·축·토대·바닥·손잡이). "자리" 어휘 회피. 한 단락 "자료" 8회 이상 금지. "도입" 대신 "서론". 통계·기술 용어는 처음 나올 때 쉬운 말로 풀기. 본보기: `N0210370104.pdf`.

## 5. 보고 형식

항목 1~4에 대해 (i) 재확인·진단 결과, (ii) 제안 정정(파일·줄 + 현재→제안), (iii) 그림은 scratch 재산출 결과 수치를 보고한다. 텍스트 편집·그림 교체는 보고 후 사용자 승인을 받고 진행한다.
