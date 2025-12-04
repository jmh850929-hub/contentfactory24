SafeGuard 1.2 (Static OmegaEngine 2.5 전용)
===========================================

역할:
- OMG_main_engine_static_v25.py 실행을 감싸는 래퍼
- 연속 실패 횟수 추적
- 일정 횟수 이상 실패 시 SAFE STATE 진입
- SAFE STATE 상태에서는 엔진 실행 차단 (auto_resume 설정에 따라 1회 시도 가능)

파일 구성:
- SGD_safe_guard_v1_2.py : 세이프가드 메인 스크립트
- SGD_config.json        : 설정 (엔진 경로, 실패 허용 횟수 등)
- SGD_state.json         : 상태 저장 (SAFE STATE 여부, 마지막 성공/실패 등)
- SGD_log.txt            : 로그 파일

사용 방법:
1) 이 세 파일을 C:\A1-M2\SafeGuard 폴더에 저장한다.
2) 명령 프롬프트에서:
   cd C:\A1-M2\SafeGuard
   python SGD_safe_guard_v1_2.py

3) Scheduler에서 기존:
   python OMG_main_engine_static_v25.py
   를
   python SGD_safe_guard_v1_2.py
   로 교체한다.

SAFE STATE 동작:
- StaticEngine이 연속으로 max_failures 번 실패하면
  SGD_state.json 의 safe_state 가 true 로 바뀌고,
  이후 실행 시 엔진을 차단한다.
- auto_resume=true 인 경우,
  SAFE STATE라도 1회 실행을 시도하고,
  성공하면 SAFE STATE 를 자동 해제한다.
