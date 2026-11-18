# Báo cáo Day 09 — Hoàng Quang Trường, 2A202603347

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước
Pipeline kết luận **Hold**. Intake nhận 193/224 ảnh và loại 31/224 ảnh. Sau QC và mô phỏng duyệt 80 ảnh, còn 53/193 ảnh có cảnh báo chưa được người duyệt xử lý (27,46%), cao hơn ngưỡng Hold cố định 10%; thư mục export được tạo ở trạng thái bản nháp, chưa được phát hành.

## 2. Lỗi và phân việc
Số liệu dưới đây lấy từ `02_error_list_v1.csv`. Cột số liệu ghi **số dòng lỗi / số ảnh**; một ảnh có thể có nhiều dòng lỗi.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_CLASS_ID` | 6 dòng / 6 ảnh | máy | Loại dòng nhãn có class ID không hợp lệ |
| `BAD_CLASS_NAME` | 2 dòng / 1 ảnh | máy | Chuẩn hoá tên lớp theo cấu hình |
| `BAD_FORMAT` | 3 dòng / 3 ảnh | máy | Loại dòng nhãn sai định dạng |
| `BAD_SIZE` | 3 dòng / 3 ảnh | máy | Intake/autofix loại ảnh sai kích thước |
| `BOX_HUGE` | 3 dòng / 3 ảnh | người | Cảnh báo box quá lớn, cần xem nội dung ảnh |
| `BOX_OUT_OF_IMAGE` | 8 dòng / 8 ảnh | máy | Clip box về biên ảnh |
| `BOX_TINY` | 6 dòng / 4 ảnh | người | Box quá nhỏ cần người xác nhận |
| `BOX_ZERO` | 4 dòng / 4 ảnh | máy | Loại dòng box có diện tích bằng 0 |
| `CLASS_RARE` | 4 dòng / 1 ảnh | người | Cảnh báo lớp hiếm cần kiểm tra ngữ cảnh |
| `CORRUPT_IMAGE` | 2 dòng / 2 ảnh | máy | Intake loại ảnh hỏng |
| `DUP_BOX` | 7 dòng / 7 ảnh | máy | Loại box trùng trong cùng ảnh |
| `DUP_IMAGE_EXACT` | 8 dòng / 8 ảnh | máy | Intake loại ảnh trùng từng byte |
| `DUP_IMAGE_NEAR` | 7 dòng / 7 ảnh | máy | Intake loại ảnh bị đánh dấu trùng gần đúng |
| `EMPTY_LABEL` | 11 dòng / 11 ảnh | người | Cần phân biệt ảnh nền hợp lệ với ảnh thiếu nhãn |
| `LEAK_TEST` | 11 dòng / 11 ảnh | máy | Intake loại ảnh trùng với tập tham chiếu test |
| `MISSING_LABEL_FILE` | 6 dòng / 6 ảnh | người | Máy không tự tạo nhãn; chuyển người gán nhãn |
| `POSSIBLE_FALSE_POS` | 28 dòng / 26 ảnh | người | Cảnh báo ngữ nghĩa cần xác nhận |
| `POSSIBLE_LOOSE_BOX` | 43 dòng / 35 ảnh | người | Cần người xem box có bao quá rộng hay không |
| `POSSIBLE_MISSING` | 148 dòng / 84 ảnh | người | Cần người xác nhận vật thể có bị bỏ sót |
| `POSSIBLE_WRONG_CLASS` | 20 dòng / 19 ảnh | người | Cần người xác nhận nhãn lớp |

`05_review_queue.csv` có 138 ảnh; hàng đợi xếp theo điểm ưu tiên cộng dồn từ trọng số mã cảnh báo, confidence và các thao tác sửa cần chú ý. Ví dụ `img_0160` đứng đầu với priority 35.692 và hai mã `POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`. Với ngân sách 80 ảnh, mô phỏng đã duyệt 80/138 ảnh. Trong `06_review_log.csv`, bốn mã cảnh báo ngữ nghĩa có 113 lượt xuất hiện: `POSSIBLE_MISSING` 59, `POSSIBLE_LOOSE_BOX` 23, `POSSIBLE_WRONG_CLASS` 19 và `POSSIBLE_FALSE_POS` 12. Đây là số lượt mã trong log, không phải 113 ảnh khác nhau.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | 2 | 16 | Trùng gần: 1.00 / 0.50 → 1.00 / 0.83. Trùng exact: 1.00 / 1.00 → 1.00 / 1.00 | Ngưỡng 16 tăng recall trùng gần mà precision trên tập calibration vẫn là 1.00; ngưỡng 20 làm recall trùng exact giảm còn 0.33 nên không chọn. |
| `second_opinion.conf` | 0.25 | 0.25 | Không đổi so với khởi đầu. Tại 0.25: wrong class P/R 0.56/0.83; missing 0.50/1.00; loose box 0.29/0.40; false positive 0.31/1.00. | Giữ recall của cảnh báo missing ở 1.00 trên tập calibration; ngưỡng thấp hơn 0.10 có precision missing thấp hơn (0.40), còn các ngưỡng cao hơn làm recall một số loại cảnh báo giảm. |

Một điểm calibration có thể đánh lừa là pHash đo độ gần của hash, không xác nhận hai ảnh có thể thay thế nhau về nội dung. Intake loại 7 ảnh `DUP_IMAGE_NEAR`: khoảng cách pHash của các cặp lần lượt là 16, 0, 16, 0, 16, 10 và 6; trong đó 3 cặp ở đúng ngưỡng 16. Có thêm 8 ảnh `DUP_IMAGE_EXACT` được xác định trùng từng byte. Chưa kiểm tra trực quan các cặp ảnh nên không kết luận tất cả ảnh near-duplicate đều nên loại. Tổng intake loại 31/224 ảnh: 11 `LEAK_TEST`, 8 exact duplicate, 7 near duplicate, 3 `BAD_SIZE` và 2 `CORRUPT_IMAGE`. Calibration dùng 39 ảnh nên precision/recall có thể dao động và không đại diện chắc chắn cho toàn bộ dữ liệu.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
(a) Chạy kiểm tra với ngân sách duyệt bằng 0: `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`. Kết quả còn 6 lỗi bắt buộc, gate kết luận **Rework**, mã thoát **20** và không tạo thư mục `work/exp_nb`. Đây là bằng chứng pipeline không xuất dataset khi vẫn còn lỗi bắt buộc.

(b) Các cảnh báo ngữ nghĩa vẫn cần người đánh giá, không thể coi kết quả model là nhãn đúng: vòng QC3 còn 90 dòng `POSSIBLE_MISSING` trên 60 ảnh và 32 dòng `POSSIBLE_LOOSE_BOX` trên 26 ảnh. Ví dụ `img_0018` có IoU 0.4470 và `img_0020` có IoU 0.3987 ở cảnh báo loose box. Ngoài ra còn 10 dòng `POSSIBLE_WRONG_CLASS` trên 9 ảnh; pipeline chỉ đưa cảnh báo để xem xét, không tự xác nhận lớp đúng. Các số dòng và số ảnh khác nhau vì một ảnh có thể có nhiều cảnh báo.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa điền ở bước GitHub; sẽ cập nhật sau khi thực hiện phần train trên Colab theo đúng quy trình raw vs clean.

## 6. Quyết định và ghi chú AI
Chưa hoàn thiện ở bước này; sẽ chốt quyết định cuối sau phần Colab và bổ sung ghi chú sử dụng AI dựa trên prompt, cách kiểm chứng code và một trường hợp AI sai có thật.

*(Thưởng +2, tùy chọn)* CVAT: chưa thực hiện.
