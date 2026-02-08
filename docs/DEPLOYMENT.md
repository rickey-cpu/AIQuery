# AI Query Agent - Deployment Guide

## Yêu Cầu Hệ Thống

- Python 3.11+
- Node.js 18+ (optional, for frontend build)
- One of: SQLite, MySQL, PostgreSQL, SQL Server, Elasticsearch

## Cài Đặt

### 1. Clone & Install Dependencies

```bash
git clone <repository>
cd AIQuery

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Database-specific Dependencies

```bash
# MySQL
pip install aiomysql

# PostgreSQL
pip install asyncpg

# SQL Server
pip install aioodbc pyodbc

# Elasticsearch
pip install elasticsearch[async]

# OpenSearch
pip install opensearch-py
```

### 3. Environment Configuration

```bash
copy .env.example .env
```

Edit `.env`:

```env
# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...

# Database (choose one)

# SQLite (default)
DB_TYPE=sqlite
DB_NAME=data/aiquery.db

# MySQL
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=aiquery
DB_USER=root
DB_PASSWORD=password

# PostgreSQL
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aiquery
DB_USER=postgres
DB_PASSWORD=password

# SQL Server
DB_TYPE=sqlserver
DB_HOST=localhost
DB_PORT=1433
DB_NAME=aiquery
DB_USER=sa
DB_PASSWORD=password
DB_DRIVER=ODBC Driver 17 for SQL Server

# Elasticsearch
DB_TYPE=elasticsearch
ES_HOSTS=http://localhost:9200
ES_USER=elastic
ES_PASSWORD=password
ES_USE_OPENSEARCH=false
```

## Chạy Ứng Dụng

### Development

```bash
python main.py
```

Server sẽ chạy tại: http://localhost:8000

### Production với Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t aiquery .
docker run -p 8000:8000 --env-file .env aiquery
```

## Kiểm Tra

### Health Check
```bash
curl http://localhost:8000/health
```

### Test Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all customers"}'
```

### Test Tools
```bash
curl http://localhost:8000/api/tools/find-column/revenue
curl http://localhost:8000/api/tools/find-value/HN
```

## Cấu Trúc Thư Mục Production

```
AIQuery/
├── .env                 # Environment variables
├── data/
│   ├── aiquery.db       # SQLite database (if used)
│   └── chroma/          # Vector store
├── logs/                # Application logs
└── ...source files
```

## Troubleshooting

### LLM Errors
- Kiểm tra API key đã set đúng
- Kiểm tra model name hợp lệ

### Database Errors
- Kiểm tra connection string
- Kiểm tra database server đang chạy
- Kiểm tra credentials

### ChromaDB Errors
- Xóa thư mục `data/chroma` và restart
