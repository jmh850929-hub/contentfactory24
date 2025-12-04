# 파일명: deploybridge_core.py
# 목적: CAPS에서 Netlify Build Hook을 호출해 자동 배포를 실행하는 모듈

import requests
import json
import datetime

NETLIFY_BUILD_HOOK = "https://api.netlify.com/build_hooks/692d7279c2aea219056a09f1"

def trigger_deploy(source="CAPS-AutoSync"):
    """
    CAPS(WebRack)가 site_root를 생성한 후
    Netlify 자동 배포를 트리거하는 함수
    """
    payload = {
        "triggered_by": source,
        "timestamp": datetime.datetime.now().isoformat()
    }

    try:
        res = requests.post(
            NETLIFY_BUILD_HOOK,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        return {
            "status_code": res.status_code,
            "response": res.text
        }

    except Exception as e:
        return {
            "status_code": None,
            "error": str(e)
        }


# 테스트 실행용
if __name__ == "__main__":
    result = trigger_deploy("manual_test")
    print(result)
