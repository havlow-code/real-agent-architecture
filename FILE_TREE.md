# Project File Tree

```
real-agent-architecture/
├── README.md                          # Main documentation with setup, architecture, usage
├── requirements.txt                   # Python dependencies
├── .env.example                      # Environment variable template
├── Dockerfile                        # Docker container definition
├── docker-compose.yml                # Docker Compose orchestration
├── main.py                           # Main entry point
│
├── config/                           # Configuration module
│   ├── __init__.py
│   └── settings.py                   # Pydantic settings with env validation
│
├── agent/                            # Core agent orchestration (LangGraph)
│   ├── __init__.py
│   ├── orchestrator.py               # LangGraph state machine
│   ├── decision_engine.py            # AUTONOMOUS DECISION-MAKING (core feature)
│   ├── state.py                      # State definition for graph
│   └── nodes.py                      # Graph nodes (intake, decide, retrieve, etc.)
│
├── rag/                              # RAG pipeline
│   ├── __init__.py
│   ├── chunker.py                    # Document chunking (600 tokens, 100 overlap)
│   ├── embeddings.py                 # Embedding generation with caching
│   ├── evidence.py                   # Evidence data structures
│   ├── retriever.py                  # Vector store retrieval (top-k=8)
│   └── reranker.py                   # Hybrid re-ranking (cosine+recency+quality)
│
├── tools/                            # Tool integrations with error handling
│   ├── __init__.py
│   ├── base.py                       # Tool abstraction + ToolResult
│   ├── crm.py                        # CRM operations (SQLite mock)
│   ├── calendar.py                   # Calendar booking (mock with retry)
│   └── email.py                      # Email sending (mock)
│
├── memory/                           # Cross-session memory systems
│   ├── __init__.py
│   ├── factual.py                    # SQL-based (SQLite: leads, interactions, notes)
│   └── semantic.py                   # Vector-based (ChromaDB: embeddings, history)
│
├── models/                           # Data models
│   ├── __init__.py
│   ├── lead.py                       # SQLAlchemy models (Lead, Note, Interaction, etc.)
│   └── schemas.py                    # Pydantic schemas for API
│
├── integrations/                     # External integrations
│   ├── __init__.py
│   └── llm_provider.py               # LLM abstraction (OpenAI/Claude/Gemini)
│
├── observability/                    # Logging and tracing
│   ├── __init__.py
│   └── logger.py                     # Structured JSON logging with trace IDs
│
├── api/                              # FastAPI application
│   ├── __init__.py
│   ├── app.py                        # FastAPI app definition
│   └── routes.py                     # API endpoints (/webhook/lead, /agent/status, /health)
│
├── jobs/                             # Background job scheduler
│   ├── __init__.py
│   └── scheduler.py                  # APScheduler for follow-ups
│
├── knowledge_base/                   # Documents for RAG (markdown)
│   ├── pricing/
│   │   └── service_pricing.md       # Pricing information (Starter, Pro, Enterprise)
│   ├── faqs/
│   │   └── general.md               # Frequently asked questions
│   ├── sops/
│   │   └── lead_qualification.md    # Standard operating procedure for BANT
│   └── policies/
│       └── refund_policy.md         # Refund and cancellation policy
│
├── docs/                             # Comprehensive documentation
│   ├── architecture.md               # System architecture and component design
│   ├── decision_logic.md             # How autonomous decision-making works
│   ├── rag_design.md                 # RAG pipeline details and tradeoffs
│   ├── risks_and_mitigations.md      # Known risks and how to mitigate
│   └── scaling_roadmap.md            # Path from PoC to production scale
│
├── scripts/                          # Utility scripts
│   └── ingest_knowledge.py           # Ingest knowledge base into vector store
│
├── examples/                         # Example runs and test scenarios
│   └── example_runs.md               # Detailed walkthroughs of 4 scenarios
│
└── data/                             # Runtime data (created on first run)
    ├── agent.db                      # SQLite database (CRM data)
    ├── chroma/                       # ChromaDB vector store persistence
    ├── logs/                         # Structured JSON logs
    └── embedding_cache/              # Cached embeddings
```

## File Count by Module

| Module | Files | Lines of Code (est.) |
|--------|-------|---------------------|
| agent/ | 5 | 800 |
| rag/ | 6 | 600 |
| tools/ | 5 | 500 |
| memory/ | 3 | 400 |
| models/ | 3 | 350 |
| integrations/ | 2 | 250 |
| observability/ | 2 | 200 |
| api/ | 3 | 150 |
| jobs/ | 2 | 100 |
| config/ | 2 | 100 |
| docs/ | 5 | ~3000 (markdown) |
| knowledge_base/ | 4 | ~1500 (markdown) |
| **Total** | **42 files** | **~8000 LOC** |

## Key Files for Understanding the System

**Start here**:
1. `README.md` - Overview, setup, usage
2. `docs/architecture.md` - System design
3. `docs/decision_logic.md` - Core autonomy feature
4. `examples/example_runs.md` - See it in action

**Core autonomy**:
- `agent/decision_engine.py` - Autonomous decision-making
- `agent/orchestrator.py` - LangGraph state machine
- `agent/nodes.py` - Processing nodes

**RAG implementation**:
- `rag/chunker.py` - Document chunking
- `rag/retriever.py` - Retrieval logic
- `rag/reranker.py` - Re-ranking and conflict detection

**Tool error handling**:
- `tools/base.py` - Tool abstraction with retry
- `tools/crm.py`, `tools/calendar.py`, `tools/email.py` - Implementations

**Cross-session memory**:
- `memory/factual.py` - SQL-based CRM data
- `memory/semantic.py` - Vector-based conversation history
