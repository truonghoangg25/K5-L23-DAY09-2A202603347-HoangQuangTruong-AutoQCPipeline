"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.

Test: pytest tests/test_gate.py -q
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed = set(reviewed)

    n_images = len(stems)

    # ERROR luôn chặn, kể cả ảnh đã được review.
    n_errors = sum(1 for issue in issues if issue.severity == ERROR)

    # Đếm ảnh có cảnh báo, không đếm số issue.
    warn_images = {
        issue.image
        for issue in issues
        if issue.severity == WARN
        and issue.image in stems
        and issue.image not in reviewed
    }

    n_warn_images = len(warn_images)
    warn_ratio = round(n_warn_images / n_images, 4) if n_images else 0.0

    threshold = cfg["gate"]["warn_ratio_hold"]
    reasons = []

    if n_errors > 0:
        decision = "Rework"
        reasons.append(
            f"Còn {n_errors} lỗi bắt buộc (ERROR), cần sửa trước khi phát hành."
        )
    elif warn_ratio >= threshold:
        decision = "Hold"
        reasons.append(
            f"Có {n_warn_images}/{n_images} ảnh còn cảnh báo "
            f"({warn_ratio:.2%}), đạt/vượt ngưỡng Hold {threshold:.2%}."
        )
    else:
        decision = "Release"
        reasons.append(
            f"Còn {n_warn_images}/{n_images} ảnh có cảnh báo "
            f"({warn_ratio:.2%}), thấp hơn ngưỡng Hold {threshold:.2%}; "
            "không còn lỗi bắt buộc."
        )

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }
