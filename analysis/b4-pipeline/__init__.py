"""B4 응답 기록 파이프라인 (decisions.html 응답표 변환·헤드리스·BEV 결정).

세 모듈로 구성:
- sb_to_response: SafeBench carla_runner.py 출력 → 측정 모델 응답표 어댑터
- bev_wrapper:    BirdeyeRender + VideoRecorder.save를 셀 단위로 wrapping
- rss_labeler:    RSS 후처리로 회피불가 라벨 u 부여 (A4·응답표 변환 결정)

B 단계 첫 작업에서 함수 본문을 채운다. 현재는 시그니처와 docstring만.
"""
