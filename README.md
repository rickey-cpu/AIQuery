# AI Query Agent

> Natural Language to SQL conversion powered by LLM - Inspired by **Uber FINCH**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)

## 🚀 Features

- **Natural Language to SQL**: Ask questions in plain language, get SQL queries
- **Multi-Agent Architecture**: Supervisor → Intent → SQL Writer → Validation workflow
- **Semantic Layer**: Map business terms to SQL (e.g., "doanh thu" → `total_amount`)
- **RAG with ChromaDB**: Few-shot learning from SQL examples
- **Modern Dark UI**: Chat interface with real-time results

## 📁 Project Structure

```
AIQuery/
├── main.py                 # FastAPI entry point
├── config.py               # Configuration management
├── requirements.txt        # Dependencies
├── agents/                 # Multi-agent framework
│   ├── supervisor.py       # LangGraph orchestrator
│   ├── intent_agent.py     # Intent classification
│   ├── sql_writer.py       # Text-to-SQL conversion
│   └── validation_agent.py # SQL safety validation
├── rag/                    # RAG components
│   ├── vector_store.py     # ChromaDB integration
│   ├── schema_manager.py   # Schema metadata
│   └── semantic_layer.py   # Business term mappings
├── database/               # Database layer
│   └── connector.py        # SQLite connector
├── api/routes/             # API endpoints
│   ├── query.py            # Natural language queries
│   ├── schema.py           # Schema management
│   └── history.py          # Query history
└── frontend/               # Web UI
    ├── index.html
    ├── styles.css
    └── app.js
```

## 🛠️ Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys
```

## ▶️ Run

```bash
python main.py
```

Open http://localhost:8000 in your browser.

## 💡 Usage Examples

| Question | Generated SQL |
|----------|---------------|
| "Show all customers from Hanoi" | `SELECT * FROM customers WHERE city = 'Hanoi'` |
| "Total revenue by month" | `SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as revenue FROM orders GROUP BY month` |
| "Top 5 selling products" | `SELECT p.name, SUM(oi.quantity) as sold FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id ORDER BY sold DESC LIMIT 5` |

## 🔧 Configuration

Edit `.env` to configure:

- **LLM Provider**: OpenAI GPT-4, Google Gemini, or Ollama
- **Database**: SQLite (default), PostgreSQL, or MySQL

## 📚 Inspired By

- [Uber FINCH](https://www.uber.com/blog/finch/) - Conversational AI for finance teams
- [Uber QueryGPT](https://www.uber.com/blog/query-gpt/) - RAG-powered text-to-SQL

## 📄 License

MIT
