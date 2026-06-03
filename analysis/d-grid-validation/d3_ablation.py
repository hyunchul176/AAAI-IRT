# -*- coding: utf-8 -*-
"""D3 ablation: 세 구조 하나씩 빼 적합 비교.

method.html 식 (6) P = u + (1-u)·σ(a·(β + γc − θ))의 세 구조:
- 반응성 (severity 조건화 c, γ_G)
- severity 조건화 자체 (c 항)
- 회피불가 하한 u (avoidability)

각 구조를 빼고 적합한 모델과 전체 모델의 비교를 본문 D3에 보고. ablation은
같은 응답 격자 위에서 (a) γc 빼기, (b) σ 함수만 (c·γ 둘 다 빼기), (c) u=0
고정 세 가지 변종을 fit_map으로 적합해 log-likelihood·split-half r 차이를
본다.

usage:
    python3 analysis/d-grid-validation/d3_ablation.py \
        analysis/b4-pipeline/responses.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path


VARIANTS = [
    ("full", "P = u + (1-u)·σ(a·(β + γc − θ))"),
    ("no_severity_c", "γc 항 제거 (β·θ만, severity 무시)"),
    ("no_reactivity", "γ·c 둘 다 제거, σ(β−θ) 정적 IRT"),
    ("u_zero", "u=0 고정 (회피불가 하한 무시, 현행 평가 관행)"),
]


def run(jsonl_path: Path) -> None:
    print(">> D3 ablation 분석 진입점. 본 격자 응답이 모이면 호출.")
    print(">> 변종 4종 비교:")
    for name, desc in VARIANTS:
        print(f"   - {name}: {desc}")
    print(">> 각 변종을 같은 응답에 적합 → log-likelihood·split-half r·θ̂ CI 폭 보고.")
    print(">> 본 격자 진입 전 인터페이스만 잡아 둔 단계.")
    # TODO: fit_map(variant=name)으로 4종 적합
    # TODO: 각 변종에서 split-half r p25 + θ̂ CI 폭 계산
    # TODO: full vs 변종의 log-likelihood 차이 + 시각화 데이터 출력


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run(Path(sys.argv[1]))
