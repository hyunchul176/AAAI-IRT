# -*- coding: utf-8 -*-
"""D4 외적 타당성: 추정 b̂이 외부 난이도 지표와 일치하는가.

섹션 C의 외부 난이도 지표(Wagner TTR, Yu complexity, Tulpule value function,
Kurian R_p)와 우리 추정 시나리오 난이도 b̂의 rank correlation을 보고한다.
검토자 라운드 9·10이 짚은 자리로, expert(AutoPilot teacher)는 격자 응시자에서
제외되었지만 external validity 비교점(reference policy)으로 D4에 들어간다.
척도 일치(scale linking)는 시도하지 않고 자릿수 일치 sanity check 수준에
한정한다.

설계:
1. 응답 JSONL의 (scenario_id, route_id) 단위 추정 b̂을 읽어 들임.
2. 외부 지표 매트릭스(시나리오별 Wagner·Yu·Tulpule·Kurian 점수)를 호스트의
   `pdfs/` 또는 별도 CSV에서 로드.
3. b̂ vs 각 외부 지표의 Spearman ρ + scatter plot 데이터 출력.
4. expert reference policy의 시나리오별 충돌률 분포를 b̂과 같은 자리에서
   비교(자릿수 일치).

본 격자 응답 + 외부 지표 데이터가 모두 있어야 호출. 지금은 인터페이스.

usage:
    python3 analysis/d-grid-validation/d4_external_validity.py \
        analysis/b4-pipeline/responses.jsonl \
        analysis/external_difficulty_indices.csv
"""
from __future__ import annotations

import sys
from pathlib import Path


EXTERNAL_INDICES = ["wagner_ttr", "yu_complexity", "tulpule_value", "kurian_rp"]


def run(jsonl_path: Path, indices_csv: Path | None = None) -> None:
    print(">> D4 외적 타당성 분석 진입점. 본 격자 응답이 모이면 호출.")
    print(">> 외부 난이도 지표(섹션 C):")
    for k in EXTERNAL_INDICES:
        print(f"   - {k}")
    print(">> expert reference policy 충돌률 분포도 비교 자리(검토자 라운드 10).")
    print(">> 척도 일치(scale linking)는 시도하지 않고 Spearman ρ + 자릿수 일치만 본다.")
    print(">> 본 격자 진입 전 인터페이스만 잡아 둔 단계.")
    # TODO: 응답에서 (sid, rid) 단위 b̂ 추정값 추출
    # TODO: 외부 지표 CSV 로드
    # TODO: b̂ vs 각 외부 지표 Spearman ρ + scatter 데이터
    # TODO: expert reference의 (sid, rid) 충돌률 분포 + b̂과 rank correlation
    # TODO: 결과 JSON + 본문 figure 데이터 출력


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run(Path(sys.argv[1]),
        Path(sys.argv[2]) if len(sys.argv) > 2 else None)
