# 🪐 Unified AI Workspace & Agent Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3+-blue.svg)](https://docs.docker.com/compose/)
[![Next.js](https://img.shields.io/badge/Next.js-v14+-black.svg)](https://nextjs.org/)

Một nền tảng doanh nghiệp hợp nhất (Unified Platform) tích hợp nhiều công cụ mã nguồn mở mạnh mẽ nhất hiện nay vào một giao diện duy nhất, được điều phối toàn diện bởi một **Central AI Agent (OpenClaw)**. Nền tảng tích hợp sẵn Single Sign-On (SSO) bảo mật, hệ thống RAG đồ thị thông tin công trình (BIM RAG), cổng chăm sóc khách hàng đa kênh (Chatwoot), và tự động hóa mạng xã hội (Postiz).

---

## 🚀 Tính Năng Nổi Bật: Triết Lý Thiết Kế "Central Agent"

Thay vì vận hành các dự án và công cụ riêng lẻ, hệ thống này **hợp nhất hoàn chỉnh** các nền tảng nghiệp vụ cốt lõi và đặt dưới sự kiểm soát của **một AI Agent trung tâm tập trung (Central AI Agent - OpenClaw)**:

*   **Hợp Nhất 1 Nền Tảng (1 Platform)**: Toàn bộ dịch vụ từ giao tiếp khách hàng (Chatwoot), quản lý chiến dịch MXH (Postiz), đến truy vấn dữ liệu kỹ thuật phức tạp (BIM RAG) được tích hợp trong một **App Shell (Next.js)** đồng nhất. Người dùng chỉ cần đăng nhập một lần duy nhất qua cổng **Keycloak SSO Gate**.
*   **Trí Tuệ Nhân Tạo Tập Trung (Central AI Agent - OpenClaw)**: Đóng vai trò là "bộ não" điều phối toàn bộ tài nguyên. Agent có thể:
    *   **Tự động phản hồi (Auto-Responder)**: Lắng nghe tin nhắn từ Chatwoot (qua webhook), suy luận qua LLM và tự động trả lời khách hàng.
    *   **Tự động hóa đăng tải (Smart Auto-Posting)**: Tạo ra các ý tưởng truyền thông từ dữ liệu nội bộ và đẩy trực tiếp vào lịch đăng bài của Postiz.
    *   **Tìm kiếm ngữ cảnh chéo (Cross-App Context)**: Sử dụng BIM RAG để trả lời các câu hỏi kỹ thuật phức tạp về mô hình tòa nhà và đưa câu trả lời trực tiếp lại cho khách hàng hoặc cập nhật lên mạng xã hội.

---

## 📐 Kiến Trúc Hệ Thống (Architecture)

```mermaid
graph TD
    User([Operator / Customer]) -->|Access via HTTPS| Cloudflare[Cloudflare Tunnel]
    Cloudflare -->|Secure Edge| Nginx[Nginx Reverse Proxy]
    
    subgraph Security Gate [Workspace SSO Gateway]
        Nginx -->|Check Session| OAuth2[OAuth2 Proxy]
        OAuth2 -->|Identify Provider| Keycloak[Keycloak Identity Provider]
    end

    subgraph Portal [Unified App Shell]
        Nginx -->|Route /| AppShell[Next.js App Shell]
    end

    subgraph Core Services [Platform Sub-Projects]
        Nginx -->|SAML Authenticated| Chatwoot[Chatwoot Omnichannel Chat]
        Nginx -->|OIDC Authenticated| Postiz[Postiz Social Media Scheduler]
        Nginx -->|Trusted-Proxy Auth| OpenClaw[OpenClaw AI Orchestrator]
        OpenClaw -->|Query API| BIM[BIM Ingest & RAG Service]
    end

    subgraph Storage & Workflows [Data & Engine Layers]
        Postiz -->|Queue Jobs| Temporal[Temporal Workflow Stack]
        Chatwoot -->|Events Webhook| OpenClaw
        OpenClaw -.->|Cross-App Automation| Postiz
        BIM -->|IFC Graph| Neo4j[(Neo4j Graph Database)]
        BIM -->|Vector Search| LightRAG[LightRAG Adapter]
    end

    classDef security fill:#f9f,stroke:#333,stroke-width:2px;
    classDef core fill:#bbf,stroke:#333,stroke-width:1px;
    classDef db fill:#fbf,stroke:#333,stroke-width:1px;
    class Security Gate security;
    class Core Services core;
    class Storage & Workflows db;
```

---

## 📦 Các Thành Phần Chi Tiết

### 1. Central AI Agent & Orchestrator (OpenClaw)
*   **Chức năng**: Hệ thống AI trung tâm chạy trên nền Node.js API, đóng vai trò nhận diện ý định (Intent Recognition), tự động hóa các luồng làm việc giữa các công cụ trong nền tảng.
*   **Tích hợp**: Xác thực qua Trusted-Proxy (Nginx chuyển tiếp header `X-Auth-Request-Email` từ Keycloak).

### 2. Unified App Shell (Next.js)
*   **Chức năng**: Giao diện cổng thông tin tập trung (Control Center) hiển thị trạng thái hoạt động (health status) của toàn hệ thống, cung cấp các nút chuyển đổi (toggle) cho các workflow tự động hóa chéo, tích hợp các View của các ứng dụng thành phần thông qua iframe bảo mật, và hỗ trợ tải lên/truy vấn mô hình BIM trực quan.

### 3. BIM RAG Stack (IFC -> Neo4j + LightRAG)
*   **Chức năng**: Pipeline phân tích file BIM (định dạng IFC), chuyển đổi cấu trúc tòa nhà thành đồ thị dữ liệu Neo4j kết hợp tìm kiếm ngữ cảnh LightRAG.
*   **Tác vụ của Agent**: Central AI Agent có thể truy cập cổng API này để trả lời các câu hỏi kỹ thuật về công trình (Ví dụ: *"Tường nào ở tầng 3 có khả năng chống cháy 2 giờ?"*).

### 4. Omnichannel Inbox (Chatwoot)
*   **Chức năng**: Quản lý tin nhắn đa kênh (Live chat website, Telegram, Facebook, Email, v.v.).
*   **Tích hợp SSO**: Cấu hình xác thực SAML cấp độ tài khoản trực tiếp qua Keycloak.

### 5. Social Scheduler (Postiz & Temporal)
*   **Chức năng**: Quản lý lịch đăng bài, tối ưu hóa thời gian đăng tải trên các nền tảng mạng xã hội lớn. Vận hành quy trình ngầm thông qua Temporal Workflow Engine (Postgres + Redis + Elasticsearch).
*   **Tích hợp SSO**: Cấu hình OpenID Connect (OIDC) client.

---

## 🔒 Single Sign-On (SSO) Flow

Để bảo vệ các hệ thống thành phần nhưng vẫn đảm bảo trải nghiệm mượt mà, dự án sử dụng mô hình SSO toàn diện:

1.  Người dùng truy cập vào bất cứ tên miền nào (`app.hiep265.shop`, `chat.hiep265.shop`, `post.hiep265.shop`, `openclaw.hiep265.shop`).
2.  **Nginx Reverse Proxy** kiểm tra phiên đăng nhập thông qua **oauth2-proxy**.
3.  Nếu chưa đăng nhập, người dùng được chuyển hướng tới cổng đăng nhập tập trung **Keycloak** (`realms/workspace`).
4.  Sau khi đăng nhập thành công, cookie dùng chung `.hiep265.shop` sẽ cho phép người dùng tự do truy cập tất cả các dịch vụ vệ tinh mà không cần đăng nhập lại.

> [!IMPORTANT]  
> Để biết thêm chi tiết về cấu hình tài khoản quản trị và các client Keycloak, vui lòng tham khảo [SSO.md](file:///home/ubuntu/managerapp/SSO.md).

---

## 🛠️ Hướng Dẫn Cài Đặt (Quick Start)

### Yêu Cầu Hệ Thống
*   Docker & Docker Compose (v2.x trở lên)
*   Domain được cấu hình DNS qua Cloudflare (nếu chạy môi trường production)

### Cài Đặt Các Bước

1.  **Clone dự án về máy**:
    ```bash
    git clone <your-repository-url>
    cd managerapp
    ```

2.  **Cấu hình môi trường**:
    Sao chép các file môi trường mẫu và cập nhật các thông số bảo mật, domain tương ứng của bạn:
    *   `chatwoot.env`
    *   `postiz.env`

3.  **Khởi động nền tảng bằng Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```

4.  **Thiết lập dữ liệu BIM demo**:
    Dự án đi kèm một script giúp thiết lập nhanh Graph DB và mô hình BIM văn phòng mẫu để kiểm thử RAG:
    ```bash
    ./scripts/setup-bim-demo.sh
    ```

5.  **Truy cập hệ thống**:
    *   **App Shell**: `https://app.hiep265.shop`
    *   **Keycloak Admin**: `https://app.hiep265.shop/admin/` (Tài khoản: `workspace-admin` / `b6a474783e5c0c5ef0f3202ab10aeb4dc0639287b004aa17`)

---

## 📝 Giấy Phép (License)

Dự án này được phân phối dưới giấy phép **MIT License**. Vui lòng xem file `LICENSE` để biết thêm chi tiết.
