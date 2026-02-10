# AI Query Agent

> Hệ thống **Natural Language to SQL** theo kiến trúc multi-agent, lấy cảm hứng từ Uber FINCH.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)

## Tổng quan

AI Query Agent cho phép đặt câu hỏi bằng ngôn ngữ tự nhiên và nhận về:
- SQL query đã sinh
- giải thích logic
- dữ liệu thực thi (nếu bật execute)

Dự án hiện hỗ trợ:
- **Multi-agent orchestration** (Supervisor + các agent chuyên biệt)
- **Multi-database** (SQLite, MySQL, PostgreSQL, SQL Server, Elasticsearch, OpenSearch)
- **RAG + Semantic Layer** để tăng độ chính xác khi map business terms
- **Web UI (Vue 3 + Vite)** và REST API qua FastAPI
- **Agent management API** để quản lý nhiều agent/kết nối DB động

---

## Kiến trúc chính

### Backend (FastAPI)
- Entry point: `main.py`
- Routers:
  - `api/routes/query.py`: query NL2SQL, sql-only, stream, tools endpoint
  - `api/routes/agents.py`: CRUD agent + test DB connection
  - `api/routes/schema.py`: metadata/schema APIs
  - `api/routes/semantic.py`: semantic layer APIs
  - `api/routes/history.py`: query history APIs

### Agent layer
- `agents/supervisor.py`: điều phối workflow chính
- `agents/multi_db_supervisor.py`: routing query theo agent nhiều DB
- `agents/sql_writer.py`: sinh SQL
- `agents/validation_agent.py`: validate SQL an toàn
- `agents/report_agent.py`, `agents/insight_agent.py`, `agents/visualization_agent.py`: agent chuyên biệt
- `agents/tools/*`: column finder, value finder, table rules, execute SQL

### Data & knowledge layer
- `rag/vector_store.py`: vector store cho examples
- `rag/semantic_layer.py`: semantic mapping + context
- `rag/schema_manager.py`: schema metadata

### Frontend
- `frontend/` (Vue 3 + Vite)
- Build output (`frontend/dist`) sẽ được backend mount tại `/static`

---

## Cài đặt nhanh

### 1) Chuẩn bị môi trường

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2) Cấu hình biến môi trường

```bash
cp .env.example .env
```

Sau đó cập nhật các biến quan trọng trong `.env`:
- `LLM_PROVIDER` (`openai` | `gemini` | `ollama`)
- API key tương ứng (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, ...)
- `DB_TYPE` + thông tin kết nối DB
- `API_HOST`, `API_PORT`

### 3) (Tuỳ chọn) chạy frontend dev

```bash
cd frontend
npm install
npm run dev
```

### 4) Chạy backend

```bash
python main.py
```

Mặc định server chạy tại: `http://localhost:8000`

---

## Chạy ở chế độ fullstack (serve UI từ FastAPI)

```bash
cd frontend
npm install
npm run build
cd ..
python main.py
```

Khi có `frontend/dist`, FastAPI sẽ tự serve UI tại `/static/index.html` và route `/` sẽ redirect vào giao diện web.

---

## API chính

### Health
- `GET /health`
- `GET /api/health`

### Query
- `POST /api/query`
- `POST /api/query/sql-only`
- `POST /api/query/with-context`
- `POST /api/query/execute`
- `WS /api/query/stream`

### Agent management
- `GET /api/agents`
- `POST /api/agents`
- `GET /api/agents/{agent_id}`
- `PUT /api/agents/{agent_id}`
- `DELETE /api/agents/{agent_id}`
- `POST /api/agents/{agent_id}/test`

Chi tiết payload/response: xem `docs/API.md`.

---

## Cấu trúc thư mục (rút gọn)

```text
AIQuery/
├── main.py
├── config.py
├── requirements.txt
├── agents/
├── api/
│   └── routes/
├── database/
│   └── sources/
├── rag/
├── models/
├── services/
├── frontend/
├── docs/
└── tests/
```

---

## Tài liệu thêm

- `docs/ARCHITECTURE.md`: kiến trúc tổng thể
- `docs/API.md`: API reference
- `docs/DEPLOYMENT.md`: hướng dẫn triển khai
- `docs/SQL_OPTIMIZATION_GUIDE.md`: tối ưu SQL

---

## Ghi chú

- Dự án có sẵn script test trong thư mục `tests/`.
- Agent repository có thể dùng PostgreSQL/MySQL tuỳ cấu hình trong môi trường.

## License

MIT
