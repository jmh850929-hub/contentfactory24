CAPS Scheduler v1.5 — 신호등(Light Tower) 시스템 안내

1. SafeGuard → Scheduler 상태 전달 구조
   - SafeGuard 실행 후 SGD_state.json 생성
   - Scheduler가 해당 파일을 읽어 traffic_light 결정

2. traffic_light 규칙
   GREEN  = SafeGuard OK (failures=0)
   YELLOW = 경고 또는 실패 1회
   RED    = 연속 실패 2회 이상

3. Scheduler가 기록하는 정보
   - SCH_status_light.json
       .safe_guard.state
       .safe_guard.failures
       .safe_guard.warnings
       .scheduler.last_run
       .scheduler.next_run
       .traffic_light

4. 실행 방법
   CMD:
   cd C:\A1-M2\Scheduler\Scheduler1.5
   python SCH_scheduler_v1_5.py

5. 필수 파일
   SCH_scheduler_v1_5.py
   SCH_settings.json
   SCH_status_light.json
