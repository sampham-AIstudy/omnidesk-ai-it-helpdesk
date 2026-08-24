# Chiến lược Đánh giá Sản phẩm RAG

Tài liệu này mô tả chiến lược đánh giá hệ thống RAG (Retrieval-Augmented Generation) thông qua việc tổng hợp một chỉ số độ tin cậy (Confidence Score). Việc xây dựng hệ thống đo lường này giúp giám sát và đánh giá chất lượng RAG khi triển khai vào môi trường thực tế (production). Các biến số (X, Y, Z, T) bao phủ toàn bộ pipeline RAG: từ truy xuất (Retrieval), sinh ngôn ngữ (Generation), bối cảnh lịch sử (Context), cho đến đánh giá logic (Evaluation).

## 1. Công thức tính Confidence Score
Thay vì dùng Trung vị (Median) dễ bỏ qua các lỗi chí mạng (ví dụ LLM sinh nội dung mượt nhưng bịa đặt), chúng ta đưa tất cả về thang điểm `[0, 1]` và sử dụng **Trung bình cộng có trọng số (Weighted Average)** kết hợp với **Quy tắc Phủ quyết (Veto Rule)**.

* Công thức: $Confidence = w_1X + w_2Y + w_3Z + w_4T$ (với $w_1 + w_2 + w_3 + w_4 = 1$).
* **Phủ quyết:** Nếu $T < 0.3$ (LLM Judge đánh giá tệ), ép $Confidence = 0.3$ (để cảnh báo).

## 2. Cách thu thập và tính toán từng chỉ số (X, Y, Z, T)
Để công thức hoạt động, cả 4 biến số phải được chuẩn hóa về cùng một thang đo `[0, 1]`.

### X: Similarity của ChromaDB (Chất lượng Truy xuất)
ChromaDB thường trả về giá trị Distance (khoảng cách) chứ không trực tiếp trả về Similarity.
* **Thu thập:** Khi gọi hàm `collection.query()`, ChromaDB sẽ trả về mảng `distances`.
* **Tính toán:**
  * Nếu dùng Cosine Distance: $X = 1 - \text{distance}$
  * Nếu dùng L2 Distance (Euclidean), chuẩn hóa dựa trên khoảng cách tối đa trong không không gian vector: $X = \frac{1}{1 + \text{distance}}$
* **Chiến lược:** Nếu lấy top-k kết quả, X có thể là giá trị trung bình similarity của top 3 document, hoặc đơn giản là similarity của document cao điểm nhất.

### Y: Log prob của câu LLM sinh ra (Độ tự tin của Model)
Logprobs thể hiện xác suất mà LLM chọn mỗi token (từ).
* **Thu thập:** Bật tham số `logprobs=True` khi gọi API (OpenAI, vLLM, Ollama...).
* **Tính toán:** API trả về danh sách các giá trị âm. Tính trung bình cộng của các logprobs, sau đó chuyển đổi về xác suất (từ 0 đến 1) bằng hàm mũ (exponential):
  $$Y = \exp\left(\frac{1}{N} \sum_{i=1}^{N} \text{logprob}_i\right)$$
  *(Với $N$ là số lượng token. $Y$ càng gần 1 nếu LLM càng chắc chắn).*

### Z: Số ticket liên quan đã được xử lý (Độ tin cậy từ lịch sử)
* **Thu thập:** Đếm số lượng ticket/tài liệu tương đồng được query ra từ database.
* **Tính toán:** Sử dụng hàm Min-Max hoặc hàm bước (Step function) để chuẩn hóa. Ví dụ, nếu có từ 5 ticket trở lên là độ tin cậy lịch sử đã đạt tối đa:
  $$Z = \min\left(\frac{\text{Ticket Count}}{5}, 1.0\right)$$
  *(Có 0 ticket $\Rightarrow Z=0$; 2 ticket $\Rightarrow Z=0.4$; 5 hoặc 100 ticket $\Rightarrow Z=1.0$)*.

### T: LLM as a Judge (Chất lượng Câu trả lời)
Đây là chỉ số quan trọng nhất (nên chiếm trọng số cao nhất, ví dụ 40-50%).
* **Thu thập:** Chạy song song hoặc ngầm (asynchronous) một prompt gọi đến model mạnh hơn (Judge).
* **Tính toán:** Cung cấp: `Câu hỏi (Query)`, `Ngữ cảnh (Context từ Chroma)`, và `Câu trả lời (Answer)`.
* **Rubric gợi ý:** Yêu cầu Judge chấm điểm từ 0 đến 10 dựa trên 3 tiêu chí:
  1. **Groundedness:** Câu trả lời có dựa hoàn toàn vào Context không? (Tránh hallucination).
  2. **Answer Relevance:** Câu trả lời có đi đúng trọng tâm câu hỏi không?
  3. **Completeness:** Câu trả lời có đầy đủ thông tin không?
* **Chuyển điểm** từ 0-10 thành `[0, 1]` bằng cách chia cho 10.

## 3. Xác định Ngưỡng Đánh giá của Mô hình (Thresholding)
Sử dụng kỹ thuật Boundary Testing để tạo các tập test "chắc chắn sai" và "chắc chắn đúng", giúp hiệu chỉnh (calibrate) hệ thống.

### 3.1 Xác định Ngưỡng Dưới (Expected Failures)
Mục tiêu: Đảm bảo hệ thống không quá tự tin vào những câu trả lời sai hoặc không có cơ sở.
* **Phương pháp:** 
  * Hỏi những câu nằm ngoài vùng kiến thức (Out-of-Domain), câu hỏi lắt léo (hallucination).
  * **Đặc biệt:** Thêm các câu hỏi **mâu thuẫn** (đòi hỏi LLM phải tổng hợp thông tin đối lập từ nhiều ticket). Đây là lúc các hệ thống RAG dễ bị sập nhất.
* **Kiểm tra:**
  * Nếu trả lời sai nhưng **Confidence Score cao** $\Rightarrow$ **TỆ** (Cần điều chỉnh trọng số).
  * Nếu trả lời sai và **Confidence Score thấp** $\Rightarrow$ **TỐT** (Hoạt động đúng kỳ vọng).

### 3.2 Xác định Ngưỡng Trên (Expected Successes)
Mục tiêu: Đảm bảo hệ thống tự tin cao độ vào những câu trả lời hoàn toàn chính xác.
* **Phương pháp:** 
  * Đặt những câu hỏi cơ bản, có đáp án rõ ràng.
  * **Đặc biệt:** Đảm bảo câu hỏi có trích xuất nguyên văn hoặc thông tin trực tiếp từ 1-2 ticket đã được xử lý thành công gần đây.
* **Kiểm tra:**
  * Nếu trả lời đúng nhưng **Confidence Score thấp** $\Rightarrow$ **TỆ** (Có thể bị phạt sai ở một chỉ số nào đó).
  * Nếu trả lời đúng và **Confidence Score cao** $\Rightarrow$ **TỐT** (Hệ thống hoạt động chuẩn xác).

## 4. Các bước triển khai tiếp theo
1. **Thu thập dữ liệu Test**: Tạo ra 2 tập dataset cho Ngưỡng Trên và Ngưỡng Dưới theo gợi ý tại phần 3.
2. **Xây dựng Pipeline đánh giá**: 
   - Tích hợp ChromaDB distance $\Rightarrow$ X.
   - Trích xuất Logprob $\Rightarrow$ Y.
   - Query Ticket Count $\Rightarrow$ Z.
   - Setup LLM-as-a-judge $\Rightarrow$ T.
3. **Chạy thử nghiệm & Tinh chỉnh (Calibration)**: Chạy pipeline trên 2 tập dataset, phân tích phân phối của $w_1X + w_2Y + w_3Z + w_4T$ để chốt lại ngưỡng phân luồng (ví dụ: `< 0.4` $\Rightarrow$ Cần Human-in-the-loop, `> 0.8` $\Rightarrow$ Tự động trả lời).
