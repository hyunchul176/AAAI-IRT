# 리눅스(계산) 환경 전달용 지시서 — K=70 통합 격자 분석 마무리

작성 2026-06-14. K=70 단일 격자(`analysis/highway_grid/responses_av20_k70.jsonl`, 20종·4 G·5 c·K=70 = 28,000 episode)는 완성됐고 데이터 정합성도 확인됐다(원고 환경에서 raw 재계산 검증 완료). 이 지시서는 통합 격자 분석을 본문용으로 확정하기 위한 마무리 작업이다. 네 가지를 해서 결과 요약 JSON 하나로 회신하면 된다.

## 결정된 방침 (D1 단조성 규칙)

생성기별 severity 단조성(D1)은 **그 생성기에서 정보가 있는 응시자 위에서만** 측정한다. 구체 규칙: 어떤 생성기 G에 대해, 해당 응시자의 충돌률이 c=0..4 전 구간에서 상수(전부 동일 = 분산 0, 즉 포화)이면 그 응시자는 G의 난이도 순서에 대한 정보(Fisher information)가 0이므로 단조성 ρ 산출에서 제외한다. 이 규칙은 네 생성기 모두에 동일하게 적용한다(특정 G만 겨냥하지 않음). rank-reversal·D2·fit 등 다른 분석은 20종 전부를 그대로 쓴다. 이 규칙은 IRT의 정보 가중과 정합하며, 본문에서 "단순 충돌률 평균은 포화 응시자에 같은 가중을 주어 단조성이 흔들릴 수 있고(전체 20종 rear-end ρ=0.667), 정보 있는 응시자로 한정하면 회복된다(ρ=0.700)"는 동기로 활용한다.

## Task 1 — D1 단조성 (위 규칙) 산출 + figure 재생성

각 생성기 G에 대해: (i) 포화 응시자(c 전 구간 상수) 식별·제외, (ii) 남은 응시자의 응시자평균 충돌률을 c=0..4에서 산출, (iii) c와의 Spearman ρ. 합격선 ρ≥0.7.

원고 환경에서 미리 재계산한 기대값(검증용 — 일치해야 함):

| G | 제외 응시자 | 유지 | ρ | 판정 |
|---|---|---|---|---|
| acarl_cutin | ppo_500 | 19 | +0.900 | PASS |
| acarl_rearend | mobil, ppo_100, ppo_800 | 17 | +0.700 | PASS |
| method_b | ppo_200 | 19 | +0.000 | FAIL |
| method_c | ppo_200, ppo_800 | 18 | +0.900 | PASS |

비교용으로 전체 20종 기준 ρ도 함께 보고한다(cut-in 0.900, rear-end **0.667**, method_b 0.000, method_c 0.900). rear-end의 0.667→0.700 대비가 본문 동기 단락에 쓰인다. 단조성 figure(severity별 충돌률 곡선 또는 ρ 막대)를 이 규칙으로 재생성해 `figures/..._k70`로 저장.

## Task 2 — D2 trial-split figure 재생성 (이번에 누락됨)

이번 재실행에서 d1·d3·fit figure는 갱신됐으나 **d2_trial_split figure가 통합 격자로 재생성되지 않았다.** 다음을 실행:

```bash
python3 analysis/highway_grid/d2_trial_split.py \
  --jsonl analysis/highway_grid/responses_av20_k70.jsonl \
  --pass-g acarl_cutin acarl_rearend method_c \
  --out analysis/highway_grid/figures/d2_trial_split_k70
```

(pass-G는 Task 1 결과 cut-in·rear-end·method_c.) r mean·p25를 전체 4 G와 pass 3 G에 대해 보고. 원고 환경 재계산값은 전체 r≈0.995, pass r≈0.988이니 비슷해야 한다.

## Task 3 — D3 deviance 정확값 보고

`d3_ablation_k70` figure는 생성됐으나 정확한 수치가 figure로는 안 읽힌다. 통합 격자(`responses_av20_k70.jsonl`)에 대한 세 변종의 deviance Δ와 df를 정확히 보고:
- no_severity (γ_G=0): Δ=?, df=?  (figure상 약 290,000)
- g_common (G 모수 통합): Δ=?, df=?  (figure상 df=9로 보이는데, 옛 문서는 df=12였음 — 어느 쪽이 맞는지 확정)
- u_zero (u_G=0): Δ=?, df=?
재현성 위해 seed 고정값(예: `--seed 0`)도 함께 명시.

## Task 4 — 결과 요약 JSON 회신

원고 환경이 문서를 정확히 갱신할 수 있게 아래를 한 JSON(`analysis/highway_grid/figures/results_summary_k70.json`)으로 덤프하고 그 내용을 회신:

- `d1_monotonicity`: G별 {rho_informative, rho_all20, excluded, n_kept, pass}
- `d1_rank_reversal`: {mean_rho, p25_rho, tophalf_disagreement_mean}  (figure값: 0.99, 0.99, 0.00 — 정확값 확인)
- `d2_trial_split`: {r_mean_all, p25_all, r_mean_pass, p25_pass}
- `d3_ablation`: 변종별 {deviance_delta, df}
- `fit`: irt_main_k70.json 그대로 (θ̂·SE·β̂·γ̂·â·û·converged) — 이미 있음, 경로만 확인
- 한 줄 메모: 본 수치가 기존 N=20·K=20 및 N=18·K=70 수치를 대체함

## 회신 후

원고 환경에서 `paper_data.md`·`paper_figures.md`·`AAAI_SUT_invariant_measurement_plan.md`를 위 JSON 기준으로 통합 K=70 단일 결과로 갱신한다(N=18/N=20 구분·두 fit·â=24·30 ceiling 한계·옛 D3 수치 모두 폐기).
