def compute_adaptive_threshold(similarities: list) -> float:
    """
    유사도 분포 기반 자동 threshold 계산

    규칙:
    1) 평균이 높으면 threshold ↑
    2) 분산이 낮아 uniform하면 threshold ↑ (구분 가능)
    3) 분산이 높으면 threshold ↓ (요약값이 섞인 DB)
    4) 안정 범위: 0.45~0.75
    """

    if not similarities:
        return 0.5

    avg = sum(similarities) / len(similarities)
    var = sum((s - avg)**2 for s in similarities) / len(similarities)

    # 기본 threshold = 평균 - 분산 보정
    th = avg - (var * 0.5)

    # 안정 범위 내로 클램프
    th = max(0.45, min(0.75, th))

    return round(th, 4)
