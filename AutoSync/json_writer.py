# json_writer.py
# AutoSync 4.0 - VersionDocs(JSON)

import json
from datetime import datetime

def write_json_version():
    version_info = {
        "type": "json_version_doc",
        "generated_at": datetime.now().isoformat()
    }

    with open("AS_version_doc.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)

    return True
