# webrack_build.py
# Netlify Build Command용 CAPS WebRack Builder (정식 버전)
# ----------------------------------------------
# 기능:
# - site_root 디렉토리를 생성
# - 상상피아노 테스트 포스팅용 index.html 자동 생성
# - images 폴더 자동 생성
# - Netlify가 GitHub repo 기반으로 즉시 사이트 배포 가능

import os
from datetime import datetime

# -----------------------------
# 1) site_root 생성
# -----------------------------
ROOT = "site_root"
IMG_DIR = os.path.join(ROOT, "images")

os.makedirs(ROOT, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# -----------------------------
# 2) HTML 본문 생성
# -----------------------------
title = "상상피아노 – CAPS 자동 포스팅 테스트"
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

html = f"""
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            padding: 40px;
            line-height: 1.7;
        }}
        h1 {{
            color: #333;
            font-size: 28px;
        }}
        .timestamp {{
            color: #777;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .content {{
            padding: 20px;
            background: #fafafa;
            border: 1px solid #eee;
            border-radius: 10px;
        }}
        .footer {{
            margin-top: 40px;
            color: #aaa;
            font-size: 12px;
        }}
    </style>
</head>

<body>
    <h1>{title}</h1>
    <div class="timestamp">자동 생성 시각: {timestamp}</div>

    <div class="content">
        <p>이 페이지는 CAPS WebRack Builder(webrack_build.py)가 Netlify 빌드 과정에서 자동 생성한 테스트 포스팅입니다.</p>
        <p>정상적으로 보였다면 Netlify + GitHub 기반 자동 포스팅 구조가 완전히 작동하고 있는 것입니다.</p>
        <p>다음 단계에서는 실제 상상피아노 사진/문구/구성을 적용해 자동 포스팅으로 확장할 수 있습니다.</p>
    </div>

    <div class="footer">
        © CAPS 자동 포스팅 시스템 – AutoSync + WebRack + DeployBridge
    </div>
</body>
</html>
"""

# -----------------------------
# 3) index.html 생성
# -----------------------------
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)

print("✔ site_root/index.html 생성 완료")
print("✔ Netlify Build 용 WebRack Builder 실행 완료")
