# -*- coding: utf-8 -*-
"""D1 순위 역전 재현: 시나리오 집합에 따라 AV 순위가 뒤집힘.

섹션 B의 LD-Scene·Shen이 보인 현상(같은 AV 집단이라도 시나리오 부분집합을
달리하면 충돌률 기반 AV 순위가 뒤집힘)을 우리 격자에서 재현한다. 본문 D2
표본불변성 결과의 대비점이다 ("문제 재현 → 우리 모델이 그 문제를 해소").

설계:
1. 응답 JSONL(`analysis/b4-pipeline/responses.jsonl`)에서 (AV, scenario_id,
   route_id) 단위로 충돌률 집계.
2. scenario 부분집합 두 갈래(예: 절반-절반 무작위 split 50회)에서 각각 AV
   순위 매김.
3. 두 갈래의 Spearman/Kendall τ 상관과 순위 뒤집힘 비율을 보고.

본 격자 응답이 모이면 호출. 지금은 인터페이스만 잡아 둔다.

usage:
    python3 analysis/d-grid-validation/d1_rank_reversal.py \
        analysis/b4-pipeline/responses.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path


def run(jsonl_path: Path) -> None:
    print(">> D1 순위 역전 재현 분석 진입점. 본 격자 응답이 모이면 호출.")
    print(">> 절차: 응답을 (AV, scenario) 집계 → scenario split 50회 →")
    print("        두 갈래 AV 순위 Spearman τ + 순위 뒤집힘 비율 보고.")
    print(">> 본 격자 진입 전 인터페이스만 잡아 둔 단계.")
    # TODO: AV별 충돌률 매트릭스 (AV × scenario) 구성
    # TODO: scenario_id 50회 split, 두 갈래 AV 순위 Spearman/Kendall 계산
    # TODO: 결과 JSON + 본문 figure 데이터 출력


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run(Path(sys.argv[1]))
