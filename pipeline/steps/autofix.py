"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN."""
from collections import defaultdict
from pathlib import Path

import yaml

from ..common import ERROR, parse_yolo_line


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}

REMOVE_CODES = {
    "LEAK_TEST",
    "CORRUPT_IMAGE",
    "BAD_SIZE",
}


def _format_number(value):
    """Ghi số gọn, tránh tạo chuỗi số thập phân không cần thiết."""
    return f"{value:.10g}"


def _clip_line(raw_line):
    """Cắt box YOLO về biên ảnh [0,1]. Trả None nếu box không còn diện tích."""
    class_id, cx, cy, w, h = parse_yolo_line(raw_line)

    left = max(0.0, cx - w / 2)
    right = min(1.0, cx + w / 2)
    top = max(0.0, cy - h / 2)
    bottom = min(1.0, cy + h / 2)

    new_w = right - left
    new_h = bottom - top

    if new_w <= 0 or new_h <= 0:
        return None

    new_cx = (left + right) / 2
    new_cy = (top + bottom) / 2

    return " ".join(_format_number(v) for v in (
        class_id, new_cx, new_cy, new_w, new_h
    ))


def _remove_image_and_label(ds, stem):
    """Xóa ảnh và nhãn tương ứng nếu tồn tại."""
    image_path = ds.image_path(stem)
    if image_path is not None:
        image_path.unlink(missing_ok=True)

    ds.label_path(stem).unlink(missing_ok=True)


def _rename_classes(ds, cfg, fixes):
    """Đưa names trong data.yaml về đúng thứ tự lớp của cấu hình."""
    yaml_path = ds.yaml_path

    if not yaml_path.exists():
        return

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    old_names = data.get("names", {})

    if isinstance(old_names, list):
        before = old_names
    elif isinstance(old_names, dict):
        before = {
            int(k): v for k, v in old_names.items()
        }
    else:
        before = old_names

    classes = list(cfg["classes"])

    if isinstance(old_names, dict):
        data["names"] = {i: name for i, name in enumerate(classes)}
    else:
        data["names"] = classes

    yaml_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    fixes.append({
        "image": "data.yaml",
        "line": None,
        "action": "rename_classes",
        "before": str(before),
        "after": str(classes),
    })


def fix(ds, issues, cfg):
    fixes = []

    # Chỉ nhận lỗi bắt buộc.
    errors = [issue for issue in issues if issue.severity == ERROR]

    # Xác định ảnh phải xóa trước để bỏ qua các issue khác của ảnh đó.
    remove_by_image = defaultdict(set)

    for issue in errors:
        if (
            issue.code in REMOVE_CODES
            or issue.code.startswith("DUP_IMAGE_")
        ):
            remove_by_image[issue.image].add(issue.code)

    removed_images = set(remove_by_image)

    # 1. Xóa ảnh trùng, rò rỉ, hỏng hoặc sai kích thước.
    for stem in sorted(removed_images):
        _remove_image_and_label(ds, stem)

        fixes.append({
            "image": stem,
            "line": None,
            "action": "remove_image",
            "before": ",".join(sorted(remove_by_image[stem])),
            "after": "",
        })

    # 2. Gom lỗi theo file nhãn và số dòng gốc.
    drop_lines = defaultdict(dict)
    clip_lines = defaultdict(dict)

    for issue in errors:
        stem = issue.image

        if stem in removed_images:
            continue

        if issue.code == "MISSING_LABEL_FILE":
            # Không tạo file nhãn. Ảnh cần được người gán nhãn.
            fixes.append({
                "image": stem,
                "line": issue.line,
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })
            continue

        if issue.code == "BAD_CLASS_NAME":
            continue

        if issue.line is None:
            continue

        if issue.code in DROP_CODES:
            drop_lines[stem][issue.line] = issue.code

        elif issue.code == "BOX_OUT_OF_IMAGE":
            clip_lines[stem][issue.line] = issue.code

    # 3. Xử lý file nhãn. Đọc file gốc một lần và ghi lại một lần.
    affected_stems = sorted(set(drop_lines) | set(clip_lines))

    for stem in affected_stems:
        label_path = ds.label_path(stem)

        # File có thể không còn tồn tại; bỏ qua an toàn.
        if not label_path.exists():
            continue

        original_lines = label_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        output_lines = []

        for line_no, raw_line in enumerate(original_lines, start=1):
            if line_no in drop_lines[stem]:
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": raw_line,
                    "after": "",
                })
                continue

            if line_no in clip_lines[stem]:
                try:
                    clipped = _clip_line(raw_line)
                except (ValueError, OverflowError):
                    clipped = None

                if clipped is None:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw_line,
                        "after": "",
                    })
                    continue

                if clipped != raw_line.strip():
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": raw_line,
                        "after": clipped,
                    })

                output_lines.append(clipped)
                continue

            output_lines.append(raw_line)

        label_path.write_text(
            "\n".join(output_lines) + ("\n" if output_lines else ""),
            encoding="utf-8",
        )

    # 4. Sửa tên lớp trong data.yaml nếu có lỗi.
    if any(issue.code == "BAD_CLASS_NAME" for issue in errors):
        _rename_classes(ds, cfg, fixes)

    return fixes
