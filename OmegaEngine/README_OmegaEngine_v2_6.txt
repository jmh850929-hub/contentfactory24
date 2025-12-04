OmegaEngine v2.6 - Pre-GPT Layer

1. 역할
   - v2.5 엔진이 생성한 output JSON들을 읽어서
     GPT에 넘길 수 있는 페이로드(gpt_payload)를 만든다.
   - 실제 본문 작성은 여전히 v2.5 엔진이 담당하며,
     v2.6은 "output → GPT 입력" 사이의 전처리 레이어이다.

2. 입력
   - output 폴더의 *.json
     (구조는 OMG_output_schema_v25_1.json 을 따른다.)

3. 설정 파일
   - OMG_prompt_layer_v1.json
       .system_prompt          : GPT에게 줄 기본 역할 설명
       .user_prompt_template   : 사용자 프롬프트 템플릿
       .style                  : 톤/대상 등 메타 정보
   - OMG_pre_template_v26.json
       .title_prefix
       .section_join
       .summary_prefix         : draft_content 구성 규칙

4. 출력
   - gpt_payload 폴더 아래에
     {원본파일명}_gpt_payload.json 이 생성된다.
   - 구조:
       {
         "version": "2.6",
         "lang": "ko",
         "meta": {...},
         "system_prompt": "...",
         "user_prompt_template": "...",
         "style": {...},
         "draft_content": "제목 + 섹션 + 요약으로 구성된 텍스트",
         "summary": "원본 summary 필드"
       }

5. 실행 방법
   CMD:
     cd C:\A1-M2\OmegaEngine
     python OMG_main_engine_static_v26.py

6. 주의 사항
   - v2.6은 기존 v2.5 엔진을 대체하지 않는다.
     -> Scheduler / SafeGuard는 여전히 v2.5를 호출하여 본문을 생성한다.
     -> GPT 연동 단계(2.7)에서 v2.6 출력(gpt_payload)을 활용하게 된다.
   - gpt_payload는 사람이 확인 후 GPT에 넘길 수 있는 중간 산출물 역할이다.
