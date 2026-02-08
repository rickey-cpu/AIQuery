# AI Query Agent - API Documentation

## Base URL
```
http://localhost:8000/api
```

## Endpoints

### 1. Query Endpoints

#### POST /query
Xử lý câu hỏi ngôn ngữ tự nhiên và trả về SQL + kết quả.

**Request:**
```json
{
  "question": "Show all customers from Hanoi",
  "execute": true
}
```

**Response:**
```json
{
  "success": true,
  "question": "Show all customers from Hanoi",
  "sql": "SELECT * FROM customers WHERE city = 'Hanoi' LIMIT 100",
  "explanation": "Query to get all customers located in Hanoi",
  "data": {
    "columns": ["id", "name", "email", "city"],
    "rows": [...],
    "row_count": 25
  },
  "warnings": []
}
```

---

#### POST /query/with-context
Trả về SQL cùng với Agent Context (thông tin từ tools).

**Request:**
```json
{
  "question": "Total revenue by month"
}
```

**Response:**
```json
{
  "success": true,
  "question": "Total revenue by month",
  "sql": "SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as revenue FROM orders GROUP BY month",
  "explanation": "...",
  "agent_context": {
    "tables": [{"name": "orders", "description": "Customer orders"}],
    "columns": [{"table": "orders", "column": "total_amount", "data_type": "REAL"}],
    "values": [],
    "rules": [{"table": "orders", "example_queries": [...]}]
  },
  "data": {...}
}
```

---

#### POST /query/sql-only
Chỉ generate SQL, không execute.

**Response:**
```json
{
  "question": "...",
  "sql": "...",
  "explanation": "...",
  "tables_used": ["customers", "orders"],
  "confidence": 0.85
}
```

---

#### POST /query/execute
Execute SQL trực tiếp (cho advanced users).

**Query Parameter:** `sql`

---

### 2. Tool Endpoints

#### GET /tools/find-column/{term}
Truy cập Column Finder Tool.

**Example:** `/tools/find-column/revenue`

**Response:**
```json
{
  "term": "revenue",
  "matches": [
    {"table": "orders", "column": "total_amount", "data_type": "REAL", "score": 1.0}
  ]
}
```

---

#### GET /tools/find-value/{alias}
Truy cập Value Finder Tool.

**Example:** `/tools/find-value/HN`

**Response:**
```json
{
  "alias": "HN",
  "column": "city",
  "values": ["Hanoi"],
  "description": "Hanoi city",
  "found": true
}
```

---

#### GET /tools/table-rules/{table}
Lấy rules của một table.

**Example:** `/tools/table-rules/orders`

**Response:**
```json
{
  "table": "orders",
  "description": "Customer orders table",
  "required_columns": ["customer_id"],
  "join_hints": [{"target": "customers", "on": "orders.customer_id = customers.id"}],
  "example_queries": [...]
}
```

---

### 3. Schema Endpoints

#### GET /schema
Lấy schema của database.

#### GET /schema/tables
Danh sách tables.

#### GET /schema/semantic
Lấy semantic mappings.

#### POST /schema/semantic
Thêm semantic mapping mới.

---

### 4. History Endpoints

#### GET /history
Lấy query history.

#### POST /history/favorite
Đánh dấu query yêu thích.

---

## WebSocket

#### WS /query/stream
Streaming query results.

**Send:**
```json
{"question": "Show all customers"}
```

**Receive (multiple messages):**
```json
{"status": "processing", "step": "analyzing"}
{"status": "processing", "step": "generating_sql"}
{"status": "complete", "result": {...}}
```

---

## Error Responses

```json
{
  "detail": "Error message"
}
```

**Status Codes:**
- `400`: Invalid request
- `500`: Server error
- `503`: Database unavailable
