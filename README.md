# Server Community - SOS Flood App

Đây là mã nguồn cho **Community Node** (Máy chủ cộng đồng) của hệ thống bản đồ cứu trợ thiên tai SOS. Community Node đóng vai trò như một máy chủ vệ tinh, giúp giảm tải cho máy chủ chính (Official Server) bằng cách cache dữ liệu và phục vụ người dùng tại địa phương hoặc khu vực lân cận với tốc độ nhanh hơn.

## 🚀 Giới thiệu

Server Community hoạt động theo cơ chế:
1.  **Proxy & Cache**: Nhận request từ người dùng, kiểm tra cache (Redis). Nếu có, trả về ngay lập tức. Nếu không, chuyển tiếp (forward) request đến máy chủ chính (Registry), sau đó lưu kết quả vào cache để phục vụ các request sau.
2.  **Self-Registration**: Tự động đăng ký thông tin của node (tên, liên hệ, URL) lên máy chủ chính để người dùng có thể tìm thấy trong danh sách máy chủ.
3.  **Phân tán tải**: Giúp hệ thống vẫn hoạt động ổn định ngay cả khi lượng truy cập tăng đột biến.

## 🛠 Yêu cầu hệ thống

*   **Docker** và **Docker Compose** (Khuyên dùng)
*   Hoặc **Python 3.9+** và **Redis** nếu chạy trực tiếp.

## 📦 Cài đặt & Chạy (Docker) - Khuyên dùng

Đây là cách đơn giản và nhanh nhất để khởi chạy một Community Node.

### 1. Clone repository
```bash
git clone <repository-url>
cd server-community
```

### 2. Cấu hình môi trường
Bạn có thể chỉnh sửa file `docker-compose.yml` hoặc tạo file `.env` để cấu hình các biến môi trường sau:

| Biến | Mặc định | Mô tả |
| :--- | :--- | :--- |
| `REGISTRY_URL` | `http://localhost:8001` | Địa chỉ của máy chủ chính (Official Server). |
| `MY_URL` | `http://localhost:8003` | Địa chỉ công khai của node này (để máy chủ chính ping kiểm tra). |
| `NODE_NAME` | `Community Node` | Tên hiển thị của node này trên bản đồ. |
| `CONTACT_NAME` | (Trống) | Tên người quản trị node. |
| `CONTACT_ZALO` | (Trống) | Số Zalo hỗ trợ. |
| `CONTACT_PHONE`| (Trống) | Số điện thoại hỗ trợ. |
| `CONTACT_EMAIL`| (Trống) | Email liên hệ. |
| `CONTACT_FB` | (Trống) | Link Facebook hỗ trợ. |

**Ví dụ cấu hình trong `docker-compose.yml`:**
```yaml
environment:
  - REGISTRY_URL=https://sg1.sos.info.vn hoặc https://hk1.sos.info.vn
  - MY_URL=http://my-community-node.com
  - NODE_NAME=Node Hà Nội 1
  - CONTACT_NAME=Nguyễn Văn A
  - CONTACT_ZALO=0987654321
```

### 3. Khởi chạy
Chạy lệnh sau để build và start server:

```bash
docker-compose up -d --build
```

Server sẽ hoạt động tại cổng **8003**.
*   API: `http://localhost:8003`
*   Redis: Chạy nội bộ trong container `redis-community`.

### 4. Kiểm tra hoạt động
Truy cập `http://localhost:8003/` trên trình duyệt. Bạn sẽ thấy thông báo:
```json
{
  "message": "SOS.INFO.VN - Community Node",
  "status": "running",
  "name": "Node Hà Nội 1"
}
```

## 🔧 Cài đặt & Chạy (Thủ công / Local)

Nếu bạn muốn chạy trực tiếp trên máy (để phát triển):

### 1. Cài đặt Redis
Đảm bảo bạn đã cài đặt và đang chạy Redis server tại `localhost:6379`.

### 2. Cài đặt thư viện Python
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` hoặc set trực tiếp trong terminal:
```bash
export REGISTRY_URL="http://localhost:8001"
export MY_URL="http://localhost:8003"
export REDIS_URL="redis://localhost:6379"
```

### 4. Chạy Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

## 📡 Danh sách API

Server Community cung cấp các API tương tự như Server Read nhưng đi qua lớp Cache:

*   **GET /api/requests**: Lấy danh sách yêu cầu cứu trợ (có phân trang, lọc).
*   **GET /api/news**: Lấy tin tức.
*   **GET /api/phones**: Lấy danh sách số điện thoại khẩn cấp.
*   **GET /api/rescue_points**: Lấy danh sách điểm cứu trợ.
*   **GET /api/map/tiles/{z}/{x}/{y}**: Proxy bản đồ (nếu có).
*   **GET /api/speedtest**: Kiểm tra tốc độ kết nối (Redis ping, Hot/Cold latency).

## 🤝 Đóng góp
Mọi đóng góp để cải thiện hiệu năng cache hoặc tối ưu hóa quy trình đồng bộ đều được hoan nghênh. Vui lòng tạo Pull Request trên GitHub.
