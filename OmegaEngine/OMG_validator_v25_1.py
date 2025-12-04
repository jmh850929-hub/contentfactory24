import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent

INPUT_SCHEMA_FILE = BASE_DIR / "OMG_input_schema_v25_1.json"
OUTPUT_SCHEMA_FILE = BASE_DIR / "OMG_output_schema_v25_1.json"
FLAVOR_SPEC_FILE = BASE_DIR / "OMG_flavor_spec_v25_1.json"

FLAVOR_DIR = BASE_DIR / "flavors"
OUTPUT_DIR = BASE_DIR / "output"
INPUT_QUEUE_FILE = BASE_DIR / "input" / "OMG_content_queue.jsonl"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_print(msg: str) -> None:
    print(msg)


def check_required_fields(obj: Dict[str, Any], required: List[str]) -> List[str]:
    missing = [k for k in required if k not in obj]
    return missing


def validate_input_queue(schema: Dict[str, Any]) -> bool:
    required = schema.get("required_fields", [])
    ok = True

    if not INPUT_QUEUE_FILE.exists():
        safe_print(f"[INPUT] SKIP: {INPUT_QUEUE_FILE} not found.")
        return False

    safe_print(f"[INPUT] Checking queue file: {INPUT_QUEUE_FILE}")
    with INPUT_QUEUE_FILE.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                safe_print(f"[INPUT][ERROR] Line {line_no}: invalid JSON ({e})")
                ok = False
                continue

            missing = check_required_fields(obj, required)
            if missing:
                safe_print(
                    f"[INPUT][ERROR] Line {line_no}: missing required fields: {missing}"
                )
                ok = False

    if ok:
        safe_print("[INPUT] OK: all lines valid against schema.")
    return ok


def validate_flavors(spec: Dict[str, Any]) -> bool:
    required = spec.get("required_fields", [])
    ok = True

    if not FLAVOR_DIR.exists():
        safe_print(f"[FLAVOR] SKIP: {FLAVOR_DIR} not found.")
        return False

    safe_print(f"[FLAVOR] Checking flavor files in: {FLAVOR_DIR}")
    for path in FLAVOR_DIR.glob("*.json"):
        data = load_json(path)
        missing = check_required_fields(data, required)
        if missing:
            safe_print(
                f"[FLAVOR][ERROR] {path.name}: missing required fields: {missing}"
            )
            ok = False
            continue

        if not isinstance(data["intro"], list):
            safe_print(f"[FLAVOR][ERROR] {path.name}: intro must be a list.")
            ok = False

        if not isinstance(data["sections"], dict):
            safe_print(f"[FLAVOR][ERROR] {path.name}: sections must be an object.")
            ok = False

        if not isinstance(data["notice"], list):
            safe_print(f"[FLAVOR][ERROR] {path.name}: notice must be a list.")
            ok = False

        if not isinstance(data["outro"], list):
            safe_print(f"[FLAVOR][ERROR] {path.name}: outro must be a list.")
            ok = False

    if ok:
        safe_print("[FLAVOR] OK: all flavor files valid.")
    return ok


def validate_output(schema: Dict[str, Any]) -> bool:
    required = schema.get("required_fields", [])
    ok = True

    if not OUTPUT_DIR.exists():
        safe_print(f"[OUTPUT] SKIP: {OUTPUT_DIR} not found.")
        return False

    safe_print(f"[OUTPUT] Checking output JSON in: {OUTPUT_DIR}")
    for path in OUTPUT_DIR.glob("*.json"):
        data = load_json(path)
        missing = check_required_fields(data, required)
        if missing:
            safe_print(
                f"[OUTPUT][ERROR] {path.name}: missing required fields: {missing}"
            )
            ok = False
            continue

        if not isinstance(data.get("intro", []), list):
            safe_print(f"[OUTPUT][ERROR] {path.name}: intro must be a list.")
            ok = False

        sections = data.get("sections", [])
        if not isinstance(sections, list) or not sections:
            safe_print(f"[OUTPUT][ERROR] {path.name}: sections must be non-empty list.")
            ok = False
        else:
            for i, sec in enumerate(sections, start=1):
                if not isinstance(sec, dict):
                    safe_print(
                        f"[OUTPUT][ERROR] {path.name}: section {i} is not an object."
                    )
                    ok = False
                    continue
                for key in ("index", "heading", "body"):
                    if key not in sec:
                        safe_print(
                            f"[OUTPUT][ERROR] {path.name}: section {i} missing '{key}'."
                        )
                        ok = False

        if not isinstance(data.get("summary", ""), str):
            safe_print(f"[OUTPUT][ERROR] {path.name}: summary must be a string.")
            ok = False

    if ok:
        safe_print("[OUTPUT] OK: all output JSON valid.")
    return ok


def main() -> None:
    safe_print("=== OmegaEngine v2.5.1 Validator ===")

    input_schema = load_json(INPUT_SCHEMA_FILE)
    output_schema = load_json(OUTPUT_SCHEMA_FILE)
    flavor_spec = load_json(FLAVOR_SPEC_FILE)

    ok_input = validate_input_queue(input_schema)
    ok_flavor = validate_flavors(flavor_spec)
    ok_output = validate_output(output_schema)

    safe_print("----------------------------------")
    if ok_input and ok_flavor and ok_output:
        safe_print("[RESULT] ALL CHECKS PASSED ✅")
    else:
        safe_print("[RESULT] SOME CHECKS FAILED ❌  (See logs above.)")


if __name__ == "__main__":
    main()
