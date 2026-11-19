# Phân tích kết quả train raw vs clean

## 1. Chênh lệch mAP50 và độ ổn định giữa các seed

Kết quả trung bình trên 2 seed:

- Raw: mAP50 = 0.7258, độ lệch chuẩn = 0.0002.
- Clean: mAP50 = 0.7187, độ lệch chuẩn = 0.0095.
- Chênh lệch clean − raw = -0.0071.

Clean có mAP50 thấp hơn raw 0.0071. Chênh lệch này lớn hơn độ lệch chuẩn của raw nhưng nhỏ hơn độ lệch chuẩn của clean. Tuy nhiên, mỗi phương án chỉ chạy 2 seed nên chưa đủ cơ sở để kết luận khác biệt có ý nghĩa thống kê hoặc khẳng định quá trình làm sạch khiến chất lượng mô hình giảm. Kết quả còn phụ thuộc vào seed và các yếu tố của lần huấn luyện.

## 2. Số ảnh raw thực sự được sử dụng khi train

Raw có 224 ảnh đầu vào được quét. Log Ultralytics ghi:

- `216 images`
- `19 backgrounds`
- `11 corrupt`

Trong đó, 11 ảnh được đánh dấu corrupt và bỏ qua. Các nguyên nhân được log ghi nhận gồm ảnh không đọc được hoặc bị truncated, tọa độ không hợp lệ, class ID ngoài phạm vi 0–3 và class ID âm.

Không nên cộng trực tiếp ba con số trên để suy ra tổng ảnh: các nhóm thống kê của log không nhất thiết loại trừ lẫn nhau. 19 background là ảnh không có đối tượng được gán nhãn hợp lệ; chúng không đồng nghĩa với ảnh corrupt và vẫn có thể được dùng làm mẫu nền khi train.

Với clean, log ghi nhận 193 ảnh, 7 background và 0 corrupt. Như vậy không có ảnh nào trong tập clean bị Ultralytics đánh dấu corrupt.

## 3. Nguy cơ rò rỉ dữ liệu giữa raw và test

Báo cáo QC phát hiện 11 trường hợp `LEAK_TEST` trong raw. Đây là các ảnh bị phát hiện trùng với ảnh thuộc tập test. Vì vậy, kết quả đánh giá raw có nguy cơ bị thổi phồng do dữ liệu train và test không độc lập hoàn toàn.

Pipeline intake đã loại các trường hợp này khỏi tập clean.

Chưa thể định lượng mAP50 bị thổi phồng bao nhiêu chỉ từ 11 cảnh báo. Muốn đo mức ảnh hưởng cần huấn luyện thêm một baseline raw đã loại 11 ảnh rò rỉ, giữ nguyên cấu hình, seed, validation và test, rồi so sánh với raw ban đầu. Thí nghiệm hiện tại chưa thực hiện phép đối chứng đó.

## 4. So sánh AP50 theo lớp

AP50 trung bình trên 2 seed:

| Lớp | Raw | Clean | Clean − Raw |
|---|---:|---:|---:|
| car | 0.7375 | 0.7498 | +0.0123 |
| person | 0.8221 | 0.8255 | +0.0034 |
| truck | 0.6485 | 0.5993 | -0.0492 |
| bus | 0.6949 | 0.7003 | +0.0054 |

Car có mức tăng AP50 lớn nhất (+0.0123). Truck giảm nhiều nhất (-0.0492).

Các loại cảnh báo nhãn trong QC gồm `POSSIBLE_MISSING`, `POSSIBLE_LOOSE_BOX`, `POSSIBLE_FALSE_POS` và `POSSIBLE_WRONG_CLASS`. Tuy nhiên, file `02_error_list_v1.csv` không ghi class ID tương ứng cho từng cảnh báo. Do đó chưa đủ bằng chứng để quy mức tăng hoặc giảm AP50 của từng lớp cho một loại lỗi nhãn cụ thể.

## 5. Lỗi còn lại trong clean và giới hạn của kết quả

Review queue có 138 ảnh, trong khi ngân sách mô phỏng chỉ là 80 ảnh. Như vậy số ảnh cần duyệt vượt ngân sách 58 ảnh.

Sau khi mô phỏng duyệt 80 ảnh, gate vẫn ghi nhận 53/193 ảnh còn cảnh báo chưa được duyệt, tương đương 27.46%. Tỷ lệ này vượt ngưỡng Hold 10%, nên quyết định pipeline vẫn là **Hold**.

Clean là tập dữ liệu đã qua các bước intake, QC và autofix theo cấu hình hiện tại, không đồng nghĩa mọi nhãn đều chính xác hoặc đã được con người xác minh. Việc còn 53 ảnh cảnh báo chưa được duyệt và review queue vượt ngân sách cho thấy chưa đủ cơ sở coi clean là dữ liệu sạch hoàn toàn hoặc phát hành. Cần tiếp tục kiểm tra, xử lý cảnh báo và chạy lại pipeline cùng gate.
