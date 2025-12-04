import json
import time
from flask import Flask, request, jsonify

app = Flask(__name__)


# -------------------------------------------------
# 1) 자연어 → CAPS 명령 토큰 매핑
# -------------------------------------------------
def parse_command(text):
    """
    자연어 명령을 CAPS 내부 토큰으로 변환하는 단순 매퍼.
    Slack Slash Command는 form-data(text)로 온다.
    """
    text = text.lower().strip()

    if "포스팅" in text or "게시물" in text:
        return "MAKE_POST"
    if "점검" in text or "상태" in text:
        return "CHECK_STATUS"
    if "동기화" in text or "싱크" in text:
        return "FORCE_SYNC"

    return "UNKNOWN"


# -------------------------------------------------
# 2) CAPS Core 실행 계획 생성
# -------------------------------------------------
def generate_execution_plan(command_token, user_text):
    """
    AutoSync가 읽는 계획 JSON을 구성.
    """
    plan = {
        "timestamp": int(time.time()),
        "command": command_token,
        "raw_text": user_text,
        "priority": "normal",
        "source": "slack",
        "autosync_trigger": True
    }
    return plan


# -------------------------------------------------
# 3) AutoSync 트리거 파일 저장
# -------------------------------------------------
def write_autosync_trigger(plan):
    """
    AutoSync가 감지하는 trigger 파일을 생성한다.
    """
    with open("caps_action_trigger.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)


# -------------------------------------------------
# 4) Slack → Webhook 엔드포인트
#    Slack Slash Command는 JSON이 아니라 form-data로 text를 전달함
# -------------------------------------------------
@app.route("/slack", methods=["POST"])
def slack_receive():
    # Slack Slash Command → Content-Type: application/x-www-form-urlencoded
    user_text = request.form.get("text", "")

    command_token = parse_command(user_text)

    # 실행 계획 생성
    plan = generate_execution_plan(command_token, user_text)

    # AutoSync 트리거
    write_autosync_trigger(plan)

    # Slack에게 응답
    return jsonify({
        "status": "ok",
        "received": user_text,
        "token": command_token,
        "message": "AlphaServer v1.1 명령 처리 완료"
    })


# -------------------------------------------------
# 5) 서버 실행
# -------------------------------------------------
if __name__ == "__main__":
    print("AlphaServer v1.1 started")
    app.run(host="0.0.0.0", port=8080)
