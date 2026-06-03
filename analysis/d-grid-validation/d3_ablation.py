# -*- coding: utf-8 -*-
"""D3 ablation: 세 구조 하나씩 빼 적합 비교.

method.html 식 (6) P = u + (1-u)·σ(a·(β + γ_G·c − θ))의 세 구조:
- severity 조건화 (γ_G·c 항)
- G별 반응성 차이 (γ_G가 G에 따라 다름 vs 공통 γ)
- 회피불가 하한 u (avoidability)

검토자 라운드 11이 짚은 자리로, 처음 작성한 4 변종 중 no_severity_c(γc 항
제거)와 no_reactivity(γ·c 둘 다 제거)가 수식상 같은 변종이었다(γc 항이
곧 γ·c 곱이고 한쪽을 0으로 박는 게 같은 결과). 의미 있게 다른 세 변종으로
정정한다.

usage:
    python3 analysis/d-grid-validation/d3_ablation.py \
        analysis/b4-pipeline/responses.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path


VARIANTS = [
    ("full",       "P = u + (1-u)·σ(a·(β + γ_G·c − θ)), γ_G가 G별 자유 모수"),
    ("no_severity","γ_G·c 항 제거 → σ(β−θ) 정적 IRT, severity 효과 무시"),
    ("g_common",   "γ_G가 모든 G에서 같다고 가정(γ_G ≡ γ_common), G별 반응성 차이 무시"),
    ("u_zero",     "u=0 고정, 회피불가 하한 무시 (현행 평가 관행)"),
]


def run(jsonl_path: Path) -> None:
    print(">> D3 ablation 분석 진입점. 본 격자 응답이 모이면 호출.")
    print(">> 변종 4종 비교 (검토자 라운드 11 정정 후, 의미 있게 다른 변종):")
    for name, desc in VARIANTS:
        print(f"   - {name}: {desc}")
    print(">> 각 변종을 같은 응답에 적합 → log-likelihood·split-half r·θ̂ CI 폭 보고.")
    print(">> 본 격자 진입 전 인터페이스만 잡아 둔 단계.")
    # TODO: fit_map(variant=name)으로 4종 적합
    # TODO: 각 변종에서 split-half r p25 + θ̂ CI 폭 계산
    # TODO: full vs 변종 log-likelihood 차이 + LRT(χ² with df 차이) + 시각화


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run(Path(sys.argv[1]))
