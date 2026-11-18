"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.

Test: pytest tests/test_label_format.py -q
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    rules = cfg["label_format"]

    overflow_tol = rules["overflow_tol"]
    min_box_px = rules["min_box_px"]
    max_box_frac = rules["max_box_frac"]
    dup_box_iou = rules["dup_box_iou"]

    issues = []

    for path in ds.label_files():
        stem = path.stem
        previous_boxes = []

        for line_no, raw_line in ds.read_label_lines(stem) or []:
            # 1. Parse YOLO line
            try:
                class_id, cx, cy, w, h = parse_yolo_line(raw_line)
            except (ValueError, OverflowError):
                issues.append(Issue(
                    "label_format", ERROR, "BAD_FORMAT", stem,
                    "Dòng nhãn không đúng 5 cột số YOLO hợp lệ",
                    line=line_no,
                ))
                continue

            # 2. Check class ID
            if not 0 <= class_id < len(ds.classes):
                issues.append(Issue(
                    "label_format", ERROR, "BAD_CLASS_ID", stem,
                    f"Class ID {class_id} nằm ngoài phạm vi hợp lệ",
                    line=line_no,
                ))
                continue

            # 3. Check zero or negative dimensions
            if w <= 0 or h <= 0:
                issues.append(Issue(
                    "label_format", ERROR, "BOX_ZERO", stem,
                    f"Box có kích thước không hợp lệ: w={w}, h={h}",
                    line=line_no,
                ))
                continue

            box = (cx, cy, w, h)

            # 4. Check overflow beyond image boundaries
            left = cx - w / 2
            right = cx + w / 2
            top = cy - h / 2
            bottom = cy + h / 2

            overflow = max(
                0.0,
                -left,
                right - 1.0,
                -top,
                bottom - 1.0,
            )

            if overflow > overflow_tol:
                issues.append(Issue(
                    "label_format", ERROR, "BOX_OUT_OF_IMAGE", stem,
                    f"Box tràn khỏi ảnh {overflow:.6f}",
                    line=line_no,
                    extra={"overflow": overflow},
                ))

            # 5. Check duplicate boxes of the same class
            for old_class, old_box, old_line in previous_boxes:
                if old_class == class_id and iou_xywh(box, old_box) > dup_box_iou:
                    issues.append(Issue(
                        "label_format", ERROR, "DUP_BOX", stem,
                        f"Box trùng với dòng {old_line}",
                        line=line_no,
                        extra={"duplicate_of_line": old_line},
                    ))
                    break

            previous_boxes.append((class_id, box, line_no))

            # 6. Check tiny box using actual image dimensions
            size = ds.image_size(stem)

            if size is not None:
                image_w, image_h = size
                short_side_px = min(w * image_w, h * image_h)

                if short_side_px < min_box_px:
                    issues.append(Issue(
                        "label_format", WARN, "BOX_TINY", stem,
                        f"Cạnh ngắn {short_side_px:.2f}px < {min_box_px}px",
                        line=line_no,
                    ))

            # 7. Check huge box
            if w * h > max_box_frac:
                issues.append(Issue(
                    "label_format", WARN, "BOX_HUGE", stem,
                    f"Diện tích box {w * h:.4f} vượt {max_box_frac}",
                    line=line_no,
                ))

    return issues
