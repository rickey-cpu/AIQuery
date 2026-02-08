# Hướng Dẫn Tối Ưu Hóa Câu Lệnh SQL Cho Báo Cáo (SQL Optimization Guide)

Tài liệu này tổng hợp các nguyên tắc và kỹ thuật tối ưu hóa câu lệnh SQL, đặc biệt tập trung vào các truy vấn tổng hợp (aggregation) phục vụ báo cáo. Nội dung được tổng hợp từ các thực hành tốt nhất (best practices) và quy chuẩn của dự án AIQuery.

## 1. Nguyên Tắc Cốt Lõi (Core Principles)

Dựa trên phân tích hiệu năng và video tham khảo "SQL Query Optimization", dưới đây là các nguyên tắc bất di bất dịch:

### 1.1. Chỉ Chọn Cột Cần Thiết (No `SELECT *`)
- **Vấn đề**: `SELECT *` lấy tất cả dữ liệu, làm tăng I/O, bộ nhớ và băng thông mạng. Nó cũng cản trở việc sử dụng "Covering Index".
- **Giải pháp**: Luôn liệt kê rõ ràng các cột cần thiết trong mệnh đề `SELECT`.
- **Ví dụ**:
  ```sql
  -- Tệ
  SELECT * FROM orders WHERE status = 'completed';
  
  -- Tốt
  SELECT id, order_date, total_amount FROM orders WHERE status = 'completed';
  ```

### 1.2. Sử dụng `LIMIT` cho mục đích xem trước
- **Khuyên dùng**: Khi chỉ cần kiểm tra dữ liệu hoặc lấy mẫu, luôn dùng `LIMIT` để tránh quét toàn bộ bảng không cần thiết.

### 1.3. Tránh `SELECT DISTINCT` nếu có thể
- **Vấn đề**: `DISTINCT` yêu cầu database engine phải sắp xếp (sort) và loại bỏ trùng lặp trên toàn bộ tập kết quả, tiêu tốn nhiều tài nguyên CPU và bộ nhớ tạm.
- **Giải pháp**: 
  - Sử dụng `GROUP BY` nếu đang thực hiện aggregation.
  - Sử dụng `EXISTS` nếu chỉ kiểm tra sự tồn tại.

### 1.4. Tận dụng Wildcard Hiệu Quả trong `LIKE`
- **Quy tắc**: Index chỉ hoạt động khi wildcard (`%`) nằm ở **cuối** chuỗi.
- **Ví dụ**:
  - `LIKE 'MacBook%'` -> **Sử dụng Index** (Range scan).
  - `LIKE '%Book'` -> **Không dùng Index** (Full table scan).

---

## 2. Tối Ưu Hóa Truy Vấn Tổng Hợp (Aggregation Optimization)

Các báo cáo thường xử lý lượng dữ liệu lớn. Việc tối ưu hóa ở giai đoạn này là quan trọng nhất.

### 2.1. Lọc Dữ Liệu Sớm Nhất Có Thể (Filter Early)
- **Nguyên tắc**: Giảm kích thước tập dữ liệu *trước khi* thực hiện JOIN hoặc GROUP BY.
- **Kỹ thuật**: 
  - Đặt điều kiện lọc trong `WHERE` thay vì `HAVING`. Mệnh đề `HAVING` lọc dữ liệu *sau khi* đã tổng hợp, trong khi `WHERE` lọc *trước khi* tổng hợp.
  
  ```sql
  -- Tệ: Tổng hợp hết rồi mới lọc
  SELECT user_id, SUM(amount) 
  FROM transactions 
  GROUP BY user_id 
  HAVING created_at >= '2023-01-01'; -- Sai logic (thường lỗi cú pháp) hoặc chậm
  
  -- Tốt: Lọc trước khi tổng hợp
  SELECT user_id, SUM(amount) 
  FROM transactions 
  WHERE created_at >= '2023-01-01'
  GROUP BY user_id;
  ```

### 2.2. SARGable Queries (Search ARGument ABLE)
- **Nguyên tắc**: Không bao giờ thực hiện phép toán hoặc hàm lên cột trong mệnh đề `WHERE` hoặc `JOIN`, vì điều này vô hiệu hóa Index.
- **Ví dụ**:
  ```sql
  -- Tệ (Index scan/Full scan):
  WHERE YEAR(order_date) = 2023
  
  -- Tốt (Index seek):
  WHERE order_date >= '2023-01-01' AND order_date < '2024-01-01'
  ```

### 2.3. Sử dụng CTE thay vì Subquery phức tạp
- **Lợi ích**: Common Table Expressions (CTE) giúp code dễ đọc, dễ bảo trì và trong nhiều trường hợp giúp database engine tối ưu hóa execution plan tốt hơn so với nested subqueries chồng chéo.
- **Áp dụng**: Sử dụng CTE để định nghĩa các bước logic rõ ràng (ví dụ: `WITH SalesData AS (...)`, `CustomerStats AS (...)`).

### 2.4. Tính Toán Gần Đúng (Approximate Aggregation)
- **Quy tắc**: Với các báo cáo dashboard thời gian thực trên dữ liệu cực lớn, cân nhắc sử dụng `COUNT(1)` thay vì `COUNT(DISTINCT column)` nếu sai số nhỏ chấp nhận được (hoặc sử dụng HyperLogLog nếu DB hỗ trợ). Đối với hầu hết các DB hiện đại, `COUNT(*)` được tối ưu hóa tốt hơn `COUNT(col)`.

---

## 3. Chiến Lược Indexing & Join

### 3.1. Index cho `GROUP BY` và `ORDER BY`
- Khi truy vấn có `GROUP BY column_A`, hãy đảm bảo `column_A` được đánh index (hoặc là phần đầu của composite index). Điều này cho phép DB thực hiện "Stream Aggregate" (không cần sort) thay vì "Hash Aggregate".

### 3.2. Covering Index
- **Khái niệm**: Index chứa tất cả các cột cần thiết cho truy vấn (cả cột trong SELECT và WHERE/JOIN).
- **Lợi ích**: Truy vấn chỉ cần đọc Index mà không cần truy xuất bảng gốc (Table Access), tăng tốc độ đáng kể.

### 3.3. Join Order & Types
- **Nguyên tắc dự án**:
  - Sử dụng chuẩn `JOIN` syntax (không dùng implicit join trong WHERE).
  - Ưu tiên `Pre-Aggregation` trước khi Join: Nếu bảng giao dịch (Fact) rất lớn và bảng danh mục (Dimension) nhỏ, hãy `GROUP BY` bảng Fact trước, sau đó mới `JOIN` với bảng Dimension để lấy tên/mô tả.

---

## 4. Quy Chuẩn Dự Án (Project Rules)

Áp dụng cho mọi Agent và Developer trong dự án AIQuery (tham khảo từ `sql_writer.py`):

1.  **NO `SELECT *`**: Luôn chỉ định cột.
2.  **SARGable**: Tránh hàm trên cột điều kiện.
3.  **EXISTS > IN**: Ưu tiên `EXISTS` cho subquery kiểm tra sự tồn tại.
4.  **UNION ALL > UNION**: Sử dụng `UNION ALL` nếu không cần loại bỏ trùng lặp (nhanh hơn vì không cần sort).
5.  **Window Functions**: Sử dụng `ROW_NUMBER()`, `RANK()`, `LEAD/LAG` cho các bài toán phân tích phức tạp thay vì self-join.
6.  **NULL Handling**: Luôn xử lý NULL bằng `COALESCE()` hoặc `IFNULL()` trong các phép tính toán học.
7.  **Order by Limit**: Luôn kèm `ORDER BY` khi dùng `LIMIT` để đảm bảo kết quả nhất quán.

---

> **Ghi chú**: Tài liệu này cần được cập nhật định kỳ dựa trên feedback từ hệ thống giám sát hiệu năng truy vấn của dự án.
