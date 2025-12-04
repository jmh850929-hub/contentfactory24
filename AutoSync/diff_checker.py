# diff_checker.py
# AutoSync 4.0 - 변경 감지 최소 모듈

def check_diff(structure_info):
    """
    구조 변화가 있는지 최소한의 수준으로만 감지.
    기본적으로 항상 "변경 있음" 처리하여 AutoSync 테스트가 가능하도록 구성.
    필요하면 고도화 가능.
    """
    # 여기서는 단순히 항상 diff 있다고 가정 (테스트 편의)
    return {"changed": True}
