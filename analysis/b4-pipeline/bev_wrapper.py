# -*- coding: utf-8 -*-
"""
BEV wrapper (decisions.html 헤드리스·BEV 결정).

SafeBench는 이미 pygame 기반 BEV 렌더러를 갖고 있다:
- `safebench/gym_carla/envs/render.py:372` class BirdeyeRender
- `safebench/util/logger.py:328` Logger.add_frame(frame)
- `safebench/util/run_util.py` VideoRecorder.save (rollout 단위 mp4 저장)
- `safebench/carla_runner.py:271` self.logger.add_frame(pygame.surfarray.array3d(self.display).transpose(1, 0, 2))

이 wrapper는 위 메커니즘을 그대로 활용해 셀 단위 MP4를 만든다. 직접 그림
그리기(matplotlib 등)는 SafeBench에 이미 있는 것을 재구현하는 헛수고라 채택
하지 않는다(헤드리스·BEV 결정).

저장 모드 세 가지 (헤드리스·BEV 결정):
    'all'             : 모든 셀의 frame을 rollout 끝에 한 번 MP4로 저장
    'every_n'         : N번째 셀마다만 저장 (디스크 부담 줄임)
    'collisions_only' : 충돌이 발생한 셀에 한해서만 저장
    'off'             : BEV 저장 끔

저장은 rollout 끝에 한 번만 호출해 시드·시간·환경 결정의 셀 timeout을 BEV I/O가 깎지 않게
한다. SafeBench VideoRecorder.save가 default `num_scenario=2` 묶음 단위라
`num_scenario=1`로 강제하거나 data_ids별 frame_list 분리가 필요하다(헤드리스·BEV 결정).

헤드리스 운용: SafeBench README가 요구하는 대로
    SDL_VIDEODRIVER="dummy" python scripts/run.py ...
로 띄워야 pygame이 가상 SDL display에 그린다(carla_runner.py:15에서 pygame
가 무조건 import되고 line 154에서 init되므로 SDL display 없으면 실패).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


SAVE_MODES = ("all", "every_n", "collisions_only", "off")


class BEVCellRecorder:
    """SafeBench BirdeyeRender + Logger.add_frame + VideoRecorder.save를
    셀 단위로 wrapping. SafeBench carla_runner를 직접 patch하지 않고,
    어댑터가 셀 경계에서 begin_cell/end_cell을 호출하는 식으로 동작.
    """

    def __init__(
        self,
        outdir: Path,
        save_mode: str = "every_n",
        every_n: int = 10,
    ):
        if save_mode not in SAVE_MODES:
            raise ValueError(f"save_mode must be one of {SAVE_MODES}")
        self.outdir = Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.save_mode = save_mode
        self.every_n = every_n
        self._cell_counter = 0
        self._current_cell: Optional[dict] = None
        self._frames: list = []

    def begin_cell(self, cell_meta: dict) -> None:
        """셀 시작 시 호출. frame buffer 초기화. cell_meta는
        {av_id, g_id, c, trial_k}.
        """
        self._cell_counter += 1
        self._current_cell = cell_meta
        self._frames = []

    def add_frame(self, frame) -> None:
        """매 step 호출. SafeBench Logger.add_frame이 받는 형식과 같은
        (H, W, 3) numpy array를 받아 buffer에 누적. SafeBench carla_runner의
        line 271 호출과 같은 위치에 끼우는 식.
        """
        self._frames.append(frame)

    def end_cell(self, collision: bool) -> Optional[Path]:
        """rollout 끝 시점에 호출. 저장 모드 따라 MP4 만들거나 frame buffer
        만 비우고 None 반환. 반환 경로는 응답표 meta에 기록.
        """
        path = self._maybe_save(collision)
        self._current_cell = None
        self._frames = []
        return path

    def _maybe_save(self, collision: bool) -> Optional[Path]:
        if self.save_mode == "off" or not self._frames:
            return None
        if self.save_mode == "every_n" and (self._cell_counter % self.every_n) != 0:
            return None
        if self.save_mode == "collisions_only" and not collision:
            return None
        return self._write_mp4()

    def _write_mp4(self) -> Path:
        """SafeBench VideoRecorder.save를 num_scenario=1 모드로 호출하거나,
        직접 cv2 / imageio로 frames를 H.264 MP4로 인코딩.
        """
        cell = self._current_cell
        fname = f"av-{cell['av_id']}_g-{cell['g_id']}_c-{cell['c']:.2f}_k-{cell['trial_k']:03d}.mp4"
        outpath = self.outdir / fname
        raise NotImplementedError(
            "B 단계 첫 작업: VideoRecorder.save를 셀 단위로 호출하는 분기 또는 "
            "imageio.mimwrite로 H.264 인코딩 결정 후 채움"
        )
