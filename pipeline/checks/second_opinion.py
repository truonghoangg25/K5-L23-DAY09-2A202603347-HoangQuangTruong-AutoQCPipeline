"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model lớn hơn."""

from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    rules = cfg["second_opinion"]

    conf_threshold = rules["conf"]
    min_area_px = rules["min_area_px"]
    fp_conf = rules["fp_conf"]
    iou_missing = rules["iou_missing"]
    iou_match = rules["iou_match"]
    iou_loose = rules["iou_loose"]

    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    issues = []

    for image_path in ds.image_files():
        stem = image_path.stem

        # Bỏ qua ảnh không có dự đoán hoặc không có file nhãn.
        if stem not in preds or not ds.label_path(stem).exists():
            continue

        size = ds.image_size(stem)
        if size is None:
            continue

        image_w, image_h = size
        labels = ds.valid_boxes(stem)
        image_preds = preds[stem]

        # Lọc dự đoán theo confidence và diện tích pixel.
        filtered_preds = []
        for pred in image_preds:
            cls, conf, cx, cy, w, h = pred

            if conf < conf_threshold:
                continue

            area_px = (w * image_w) * (h * image_h)
            if area_px < min_area_px:
                continue

            filtered_preds.append(pred)

        # Phân tích từng dự đoán theo đúng thứ tự ban đầu.
        for pred in filtered_preds:
            pred_cls, conf, cx, cy, w, h = pred
            pred_box = (cx, cy, w, h)

            # Các nhãn thuộc mọi lớp có IoU đủ lớn.
            candidates = []
            for label_cls, lcx, lcy, lw, lh in labels:
                iou = iou_xywh(pred_box, (lcx, lcy, lw, lh))
                if iou >= iou_missing:
                    candidates.append((label_cls, iou))

            # Không có nhãn nào khớp: có thể thiếu nhãn.
            if not candidates:
                issues.append(Issue(
                    "second_opinion",
                    WARN,
                    "POSSIBLE_MISSING",
                    stem,
                    "Model phát hiện vật thể chưa có nhãn tương ứng",
                    extra={"conf": conf},
                ))
                continue

            # Ưu tiên xét nhãn cùng lớp trước.
            same_class = [
                iou for label_cls, iou in candidates
                if label_cls == pred_cls
            ]

            if same_class:
                best_iou = max(same_class)

                if best_iou < iou_loose:
                    issues.append(Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_LOOSE_BOX",
                        stem,
                        "Box nhãn có thể lỏng hoặc lệch so với dự đoán",
                        extra={"conf": conf, "iou": best_iou},
                    ))

                # Có nhãn cùng lớp thì không xét nhãn khác lớp nữa.
                continue

            # Không có nhãn cùng lớp: xét IoU tốt nhất khác lớp.
            best_other_iou = max(iou for _, iou in candidates)

            if best_other_iou >= iou_match:
                issues.append(Issue(
                    "second_opinion",
                    WARN,
                    "POSSIBLE_WRONG_CLASS",
                    stem,
                    "Nhãn có thể bị gán sai lớp",
                    extra={"conf": conf, "iou": best_other_iou},
                ))

        # FALSE_POS: xét từng dòng nhãn hợp lệ.
        # Dùng line_no gốc do read_label_lines cung cấp.
        # Không lọc diện tích dự đoán ở bước này.
        for line_no, raw_line in ds.read_label_lines(stem) or []:
            try:
                label_cls, lcx, lcy, lw, lh = parse_yolo_line(raw_line)
            except (ValueError, OverflowError):
                continue

            if not 0 <= label_cls < len(ds.classes):
                continue

            label_box = (lcx, lcy, lw, lh)
            matched = False

            for pred in image_preds:
                pred_cls, pred_conf, pcx, pcy, pw, ph = pred

                if pred_conf < fp_conf:
                    continue

                pred_box = (pcx, pcy, pw, ph)

                if iou_xywh(label_box, pred_box) >= iou_missing:
                    matched = True
                    break

            if not matched:
                issues.append(Issue(
                    "second_opinion",
                    WARN,
                    "POSSIBLE_FALSE_POS",
                    stem,
                    "Box nhãn không khớp với dự đoán nào của model",
                    line=line_no,
                    extra={"iou": 0.0},
                ))

    return issues
