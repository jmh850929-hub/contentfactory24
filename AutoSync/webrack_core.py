# webrack_core.py
# AutoSync 4.0 - WebRack site_root 업데이트

import os

def update_site_root():
    """
    site_root 디렉터리를 생성하고
    간단한 index.html 파일을 넣어 배포 준비하도록 한다.
    CAPS 본 버전에서는 WebRack이 실제 HTML을 생성함.
    """
    root = "site_root"
    os.makedirs(root, exist_ok=True)

    html = """
    <html>
    <head><title>CAPS AutoSync Test</title></head>
    <body>
        <h1>AutoSync WebRack Generated</h1>
    </body>
    </html>
    """

    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    return True
