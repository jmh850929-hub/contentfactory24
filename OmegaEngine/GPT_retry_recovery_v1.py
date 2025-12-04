"""
GPT_retry_recovery_v1.py
CAPS OmegaEngine - GPT 호출 재시도 + mock 폴백 레이어 v1
"""

import os
import time
from typing import Dict, Any, Tuple
import requests


def has_api_key(env_name: str) -> bool:
    return bool(os.environ.get(env_name, "").strip())


def call_gpt_api(
    api_base: str,
    model: str,
    api_key_env: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Tuple[bool, str]:

    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        return False, "API 키가 없습니다."

    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}: {resp.text}"
        data = resp.json()
        return True, data["choices"][0]["message"]["content"]

    except Exception as e:
        return False, str(e)


def build_mock_response(draft_content: str) -> str:
    """GPT API사용 불가 시 안전한 mock 응답"""
    return (
        "※ [MOCK 응답] 실제 GPT 대신 초안을 정리한 테스트 버전입니다.\n\n"
        "------ 초안 시작 ------\n"
        f"{draft_content.strip()}\n"
        "------ 초안 끝 ------\n"
    )


def call_with_retry(
    cfg: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    draft_content: str,
    max_retries: int = 2,
    retry_delay_sec: int = 3,
) -> str:

    mode = cfg.get("mode", "mock_first")
    api_base = cfg.get("api_base")
    model = cfg.get("model")
    api_key_env = cfg.get("api_key_env")
    max_tokens = cfg.get("max_tokens", 1200)
    temperature = cfg.get("temperature", 0.5)

    # mock-first 모드
    if mode == "mock_first":
        if not has_api_key(api_key_env):
            return build_mock_response(draft_content)

        # API키 있으면 실제 호출 시도
        for _ in range(max_retries + 1):
            ok, res = call_gpt_api(
                api_base, model, api_key_env,
                system_prompt, user_prompt,
                max_tokens, temperature
            )
            if ok:
                return res
            time.sleep(retry_delay_sec)

        return build_mock_response(draft_content)

    # api-only 모드
    if mode == "api_only":
        for _ in range(max_retries + 1):
            ok, res = call_gpt_api(
                api_base, model, api_key_env,
                system_prompt, user_prompt,
                max_tokens, temperature
            )
            if ok:
                return res
            time.sleep(retry_delay_sec)

        return build_mock_response(draft_content)

    # mode 이상하면 안전하게 mock
    return build_mock_response(draft_content)
