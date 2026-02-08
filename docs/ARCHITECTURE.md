# AI Query Agent - Kiến Trúc Hệ Thống

> Natural Language to SQL Agent inspired by **Uber FINCH**

## Tổng Quan

AI Query Agent là hệ thống chuyển đổi câu hỏi ngôn ngữ tự nhiên thành SQL queries, sử dụng kiến trúc multi-agent và RAG (Retrieval-Augmented Generation).

## Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   Web UI    │  │   Slack     │  │Google Sheet │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        API LAYER                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FastAPI Server (main.py)                                │    │
│  │  - POST /api/query              → Process query          │    │
│  │  - POST /api/query/with-context → Query + Agent Context  │    │
│  │  - GET  /api/tools/*            → Direct tool access     │    │
│  │  - GET  /api/schema             → Database schema        │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     AGENT FRAMEWORK                              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              SUPERVISOR AGENT (LangGraph)                │    │
│  │  Orchestrates workflow: Intent → SQL → Validate → Exec   │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                    │                    │            │
│  ┌────────▼────────┐  ┌───────▼───────┐  ┌────────▼────────┐   │
│  │  INTENT AGENT   │  │  SQL WRITER   │  │ VALIDATION AGENT│   │
│  │  - 6 intents    │  │  - Toolset    │  │  - SQL safety   │   │
│  │  - Routing      │  │  - Context    │  │  - LIMIT add    │   │
│  └─────────────────┘  └───────────────┘  └─────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                  SQL AGENT TOOLSET                         │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────┐ │  │
│  │  │Column Finder│ │Value Finder │ │Table Rules │ │Exec SQL│ │  │
│  │  └─────────────┘ └─────────────┘ └────────────┘ └────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                       RAG LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Vector Store│  │Schema Manager│ │    Semantic Layer       │  │
│  │  (ChromaDB) │  │ (Metadata)  │  │ (Term → SQL mapping)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    DATABASE LAYER                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              DATABASE CONNECTOR                          │    │
│  │  Supports: MySQL | PostgreSQL | SQL Server | SQLite      │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              SEARCH CONNECTOR                            │    │
│  │  Supports: Elasticsearch | OpenSearch                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Luồng Xử Lý Query

```
User Question: "Show total revenue by month in Hanoi"
                    │
                    ▼
┌─────────────────────────────────────┐
│ 1. INTENT AGENT                     │
│    - Intent: data_retrieval         │
│    - Sub: ad_hoc_query              │
│    - Query type: aggregate          │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│ 2. SQL WRITER + TOOLSET             │
│                                     │
│    Column Finder("revenue")         │
│    → orders.total_amount            │
│                                     │
│    Value Finder("Hanoi")            │
│    → city = 'Hanoi'                 │
│                                     │
│    Table Rules("orders")            │
│    → JOIN customers, example SQL    │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│ 3. AGENT CONTEXT                    │
│    tables: [orders, customers]      │
│    columns: [total_amount, city]    │
│    values: [Hanoi]                  │
│    rules: [JOIN hints]              │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│ 4. SQL GENERATION                   │
│    SELECT strftime('%Y-%m', o.date) │
│           SUM(o.total_amount)       │
│    FROM orders o                    │
│    JOIN customers c ON ...          │
│    WHERE c.city = 'Hanoi'           │
│    GROUP BY month                   │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│ 5. VALIDATION AGENT                 │
│    ✓ Only SELECT                    │
│    ✓ No dangerous patterns          │
│    + Add LIMIT if needed            │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│ 6. EXECUTE & RETURN                 │
│    → SQL + Results + Explanation    │
└─────────────────────────────────────┘
```

## Cấu Trúc Source Code

```
AIQuery/
├── main.py                 # FastAPI entry point
├── config.py               # Configuration management
├── requirements.txt        # Dependencies
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md     # This file
│   ├── API.md              # API documentation
│   └── DEPLOYMENT.md       # Deployment guide
│
├── agents/                 # Multi-agent framework
│   ├── __init__.py
│   ├── supervisor.py       # LangGraph orchestrator
│   ├── intent_agent.py     # Intent classification (6 types)
│   ├── sql_writer.py       # Text-to-SQL with toolset
│   ├── validation_agent.py # SQL safety validation
│   └── tools/              # SQL Agent Toolset
│       ├── column_finder.py
│       ├── value_finder.py
│       ├── table_rules.py
│       └── execute_sql.py
│
├── rag/                    # RAG components
│   ├── vector_store.py     # ChromaDB for few-shot
│   ├── schema_manager.py   # Schema metadata
│   └── semantic_layer.py   # Business term mappings
│
├── database/               # Database connectors
│   ├── __init__.py
│   ├── connector.py        # Base connector
│   └── sources/            # Multi-database support
│       ├── mysql.py
│       ├── postgresql.py
│       ├── sqlserver.py
│       └── elasticsearch.py
│
├── api/                    # FastAPI routes
│   └── routes/
│       ├── query.py        # Query endpoints
│       ├── schema.py       # Schema endpoints
│       └── history.py      # History endpoints
│
└── frontend/               # Web UI
    ├── index.html
    ├── styles.css
    └── app.js
```

## Các Thành Phần Chính

### 1. Supervisor Agent
- **File**: `agents/supervisor.py`
- **Công nghệ**: LangGraph
- **Chức năng**: Điều phối workflow giữa các agent

### 2. Intent Agent
- **File**: `agents/intent_agent.py`
- **6 Intent Types**:
  - `data_retrieval`: Ad-hoc queries
  - `report_generation`: Báo cáo định sẵn
  - `insight_generation`: Phân tích xu hướng
  - `query_assistance`: Hỗ trợ SQL
  - `allocation_explainability`: Giải thích phân bổ chi phí
  - `knowledge_base`: Tra cứu policy

### 3. SQL Writer Agent
- **File**: `agents/sql_writer.py`
- **Features**:
  - Toolset integration
  - Agent Context building
  - Few-shot learning từ Vector Store
  - Semantic Layer mapping

### 4. SQL Agent Toolset
| Tool | File | Chức năng |
|------|------|-----------|
| Column Finder | `tools/column_finder.py` | Tìm column theo business term |
| Value Finder | `tools/value_finder.py` | Map alias → actual value |
| Table Rules | `tools/table_rules.py` | Lấy rules, JOIN hints |
| Execute SQL | `tools/execute_sql.py` | Thực thi SQL an toàn |

### 5. RAG Layer
| Component | File | Chức năng |
|-----------|------|-----------|
| Vector Store | `rag/vector_store.py` | ChromaDB cho few-shot learning |
| Schema Manager | `rag/schema_manager.py` | Metadata về tables/columns |
| Semantic Layer | `rag/semantic_layer.py` | Map business term → SQL |

### 6. Database Connectors
| Database | File | Status |
|----------|------|--------|
| SQLite | `database/connector.py` | ✅ Implemented |
| MySQL | `database/sources/mysql.py` | ✅ Implemented |
| PostgreSQL | `database/sources/postgresql.py` | ✅ Implemented |
| SQL Server | `database/sources/sqlserver.py` | ✅ Implemented |
| Elasticsearch | `database/sources/elasticsearch.py` | ✅ Implemented |

## Tham Khảo

- [Uber FINCH Blog](https://www.uber.com/blog/finch/)
- [Uber QueryGPT](https://www.uber.com/blog/query-gpt/)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
