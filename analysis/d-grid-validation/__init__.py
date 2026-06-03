"""D 단계 검증 모듈.

본 격자(CARLA + SafeBench/FREA)에서 수집한 응답 JSONL을 받아 D1·D2·D3·D4
분석을 수행한다. D-study 합성 격자 검증(`analysis/d-study/d_study.py`)의
공통 함수(fit_map, split_half_metrics, mh_chi2)를 재사용한다.

- d2_split_half: 표본불변성 검증 (split-half b̂ 상관, Spearman ρ).
- d1_rank_reversal: 충돌률로 AV 순위와 b̂ θ 순위 비교 (다음 turn에 작성).
- d3_ablation: 세 구조(반응성·severity·avoidability) 하나씩 빼 적합 비교.
- d4_external_validity: 추정 b̂가 섹션 C의 외부 난이도 지표와 일치 점검.
"""
