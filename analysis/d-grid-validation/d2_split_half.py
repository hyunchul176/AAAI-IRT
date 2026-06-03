# -*- coding: utf-8 -*-
"""D2 표본불변성 검증: b̂ split-half 상관 (specific objectivity 경험적 확인).

본 격자 응답 JSONL을 받아 무작위 AV split·scenario split 50회 r 분포의
25 percentile이 격자 합격선 결정의 0.80을 넘는지 보고한다. D-study sweep의
split_half_metrics와 동일 로직(`analysis/d-study/d_study.py:216`).

응답 JSONL 한 행:
    {"av_id": "sac", "g_id": "lc", "sid": 2, "rid": 0, "data_id": 40,
     "c_idx": 2, "c_value": 2.0, "trial_k": 0, "seed": 1234567,
     "collision": 0, "u_label": null, ...}

usage:
    python3 analysis/d-grid-validation/d2_split_half.py \
        analysis/b4-pipeline/g3_logs/responses.jsonl
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def load_responses(jsonl_path: Path) -> dict:
    """JSONL을 (AV, G, c_idx) 키 → list of (collision, u_label, trial_k)로 정리."""
    by_cell: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    av_set: set[str] = set()
    g_set: set[str] = set()
    c_set: set[int] = set()
    with open(jsonl_path) as f:
        for line in f:
            r = json.loads(line)
            av = r["av_id"]
            g = r["g_id"]
            c = r["c_idx"]
            av_set.add(av); g_set.add(g); c_set.add(c)
            by_cell[(av, g, c)].append(r)
    return dict(
        by_cell=by_cell,
        av_list=sorted(av_set),
        g_list=sorted(g_set),
        c_list=sorted(c_set),
    )


def build_response_tensor(loaded: dict) -> dict:
    """4D 응답 격자(AV × G × c × trial)를 dict 형식으로 빌드.

    `analysis/d-study/d_study.py`의 fit_map이 받는 형식과 호환되도록 한다.
    """
    av_list = loaded["av_list"]
    g_list = loaded["g_list"]
    c_list = loaded["c_list"]
    n_av, n_g, n_sev = len(av_list), len(g_list), len(c_list)
    # K는 셀별 trial 수 평균(셀이 불균등하면 가장 작은 셀에 맞춤)
    K_per_cell = [len(loaded["by_cell"][(av, g, c)])
                  for av in av_list for g in g_list for c in c_list]
    K = min(K_per_cell)
    print(f">> grid: AV={n_av} × G={n_g} × c={n_sev} × K={K} "
          f"({n_av*n_g*n_sev*K} cells)")
    y = np.zeros((n_av, n_g, n_sev, K), dtype=np.int8)
    u = np.full((n_av, n_g, n_sev, K), np.nan, dtype=np.float32)
    for i, av in enumerate(av_list):
        for j, g in enumerate(g_list):
            for s, c in enumerate(c_list):
                rs = loaded["by_cell"][(av, g, c)][:K]
                for k, r in enumerate(rs):
                    y[i, j, s, k] = int(r.get("collision", 0))
                    if r.get("u_label") is not None:
                        u[i, j, s, k] = float(r["u_label"])
    return dict(y=y, u=u, av_list=av_list, g_list=g_list, c_list=c_list, K=K)


def run(jsonl_path: Path) -> None:
    """D2 검증의 entrypoint. analysis/d-study/d_study.py의 split_half_metrics를
    호출해 무작위 50 split의 b̂ Pearson r 분포 25 percentile을 보고한다.
    실제 적합은 우리 IRT 모델(method.html 식 6)의 MAP + Laplace 추정으로
    수행되어야 하므로 본 격자 응답 + RSS 라벨 u가 모두 모인 후 이 모듈을
    호출한다.
    """
    loaded = load_responses(jsonl_path)
    grid = build_response_tensor(loaded)
    print(">> D2 split-half 검증은 IRT MAP fit + 50회 split이 필요하다.")
    print(">> 본 격자 응답이 모이면 analysis/d-study/d_study.py의 함수를")
    print("   재사용해 호출한다(fit_map → split_half_metrics).")
    print(">> 본 격자 진입 전 인터페이스만 잡아 둔 단계.")
    # TODO: from analysis.d_study.d_study import fit_map, split_half_metrics
    # TODO: split-half r 50회 + 25 percentile + bootstrap 5 percentile 보고


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    run(Path(sys.argv[1]))
