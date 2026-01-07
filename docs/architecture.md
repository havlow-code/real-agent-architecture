# Architecture

## System Overview

The Autonomous Business AI Agent is built as a modular, event-driven system with clear separation of concerns. The architecture enables autonomous decision-making, RAG-grounded responses, and graceful error handling.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                      │
│                    /webhook/lead, /agent/status                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestrator                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Intake  │→│  Load    │→│ Decision │→│ Retrieve │        │
│  │          │  │ Context  │  │  Engine  │  │   RAG    │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                    │                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Finalize │←│  Memory  │←│  Tools   │←│ Compose  │        │
│  │          │  │  Update  │  │          │  │          │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────────────────────────────────────────────────────────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Decision   │ │     RAG      │ │    Tools     │ │   Memory     │
│    Engine    │ │   Pipeline   │ │              │ │              │
├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│ · Analyze    │ │ · Chunking   │ │ · CRM        │ │ · Factual    │
│ · Decide     │ │ · Embeddings │ │ · Calendar   │ │   (SQLite)   │
│ · Confidence │ │ · Retrieval  │ │ · Email      │ │ · Semantic   │
│ · Escalate   │ │ · Re-ranking │ │ · Retry      │ │   (Chroma)   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │   LLM Provider   │
               │   Abstraction    │
               ├──────────────────┤
               │ · OpenAI         │
               │ · Anthropic      │
               │ · Google         │
               └──────────────────┘
```

## Component Descriptions

### 1. API Layer (`api/`)
- **FastAPI**: Lightweight, async-capable REST API
- **Endpoints**:
  - `POST /webhook/lead`: Main entry point for inbound leads
  - `GET /agent/status/{lead_id}`: Query lead status and history
  - `GET /health`: Health check
- **Middleware**: CORS, request logging, error handling

### 2. LangGraph Orchestrator (`agent/orchestrator.py`)
- **State Machine**: Explicit state transitions through graph
- **Nodes**: Discrete processing steps (9 nodes)
- **Conditional Edges**: Dynamic routing based on state
- **Persistence**: State can be checkpointed for long-running workflows

#### Node Flow:
1. **intake_webhook**: Entry point, logs start
2. **load_lead_context**: Loads CRM data + conversation history
3. **decide_action**: **CORE AUTONOMY** - decides next action
4. **retrieve_rag**: Conditional RAG retrieval
5. **compose_response**: LLM-generated response with grounding
6. **execute_tools**: Tool calls with retry logic
7. **update_memory**: Persists to both SQL and vector store
8. **handle_escalation**: Conditional escalation to human
9. **finalize**: Cleanup and return

### 3. Decision Engine (`agent/decision_engine.py`)
**This is the CORE of autonomy.**

- **Input**: Query, context, history, retrieved sources
- **Output**: Decision enum (RETRIEVE, REASON_ONLY, USE_TOOL, CLARIFY, ESCALATE)
- **Process**:
  1. Build decision prompt with full context
  2. LLM evaluates situation and decides action
  3. Parse structured decision output
  4. Calculate confidence score
  5. Determine if escalation needed

**NOT rule-based**: Uses LLM reasoning, not hardcoded rules.

### 4. RAG Pipeline (`rag/`)

#### 4.1 Document Chunking (`rag/chunker.py`)
- **Strategy**: Fixed token-size chunks with overlap
- **Size**: 600 tokens per chunk
- **Overlap**: 100 tokens
- **Rationale**: Balances context vs. precision
- **Metadata**: Doc type, file path, updated date

#### 4.2 Embeddings (`rag/embeddings.py`)
- **Provider**: Abstracted (OpenAI default)
- **Model**: `text-embedding-3-small` (1536 dimensions)
- **Caching**: File-based cache to avoid redundant API calls
- **Batch Processing**: Embeds multiple texts in single API call

#### 4.3 Vector Store (`memory/semantic.py`)
- **Database**: ChromaDB (persistent local store)
- **Collections**:
  - `knowledge_base`: SOPs, FAQs, pricing, policies
  - `conversation_history`: Past interactions
- **Metadata Filtering**: By doc type, updated date, category
- **Distance Metric**: Cosine similarity

#### 4.4 Retriever (`rag/retriever.py`)
- **Query**: Generates query embedding
- **Retrieval**: Top-k (default 8) by cosine similarity
- **Filtering**: Optional metadata filters
- **Output**: Structured Evidence objects

#### 4.5 Re-ranker (`rag/reranker.py`)
- **Hybrid Scoring**:
  - 60% cosine similarity
  - 20% recency (exponential decay)
  - 20% source quality (doc type hierarchy)
- **Conflict Detection**: Identifies contradictory sources
- **Filtering**: Removes low-quality sources below threshold

### 5. Tools (`tools/`)
All tools implement base `Tool` class with structured `ToolResult`.

#### 5.1 CRM Tool (`tools/crm.py`)
- **Backend**: SQLite (mock, swappable with HubSpot/Salesforce)
- **Operations**:
  - Upsert lead
  - Qualify lead (BANT scoring)
  - Update status
  - Schedule follow-up
- **Error Handling**: Retry on transient DB errors

#### 5.2 Calendar Tool (`tools/calendar.py`)
- **Backend**: Mock (swappable with Google Calendar/Calendly)
- **Operations**:
  - Book meeting
  - Check availability
  - Cancel meeting
- **Error Handling**: 10% simulated failure rate, retry enabled

#### 5.3 Email Tool (`tools/email.py`)
- **Backend**: Mock (swappable with SendGrid/SMTP)
- **Operations**:
  - Send email
  - Send follow-up (template-based)
- **Logging**: All emails logged for verification

### 6. Memory Systems (`memory/`)

#### 6.1 Factual Memory (`memory/factual.py`)
- **Backend**: SQLite
- **Schema**:
  - `leads`: Contact info, status, qualification score
  - `notes`: Timestamped notes
  - `interactions`: Full conversation history
  - `escalation_events`: Escalation tracking
- **Purpose**: Structured transactional data

#### 6.2 Semantic Memory (`memory/semantic.py`)
- **Backend**: ChromaDB
- **Purpose**: Vector embeddings for similarity search
- **Uses**:
  - Knowledge base retrieval
  - Conversation history search
  - Context enrichment

### 7. LLM Provider Abstraction (`integrations/llm_provider.py`)
- **Supported Providers**:
  - OpenAI (GPT-4)
  - Anthropic (Claude)
  - Google (Gemini)
- **Interface**: Unified `generate()` and `generate_with_messages()` methods
- **Configuration**: Provider selected via environment variable
- **Error Handling**: Provider-specific exception handling

### 8. Observability (`observability/logger.py`)
- **Structured Logging**: JSON format
- **Trace IDs**: UUID for request correlation
- **Events Logged**:
  - Decision made
  - Retrieval performed
  - Tool called/result
  - Confidence calculated
  - Escalation triggered
  - Response composed
  - Memory updated
  - Errors
- **Outputs**: File + console

### 9. Background Jobs (`jobs/scheduler.py`)
- **Scheduler**: APScheduler
- **Jobs**:
  - Follow-up checks (every 30 min)
  - Future: Lead scoring refresh, stale lead cleanup
- **Error Handling**: Job failures logged, don't crash scheduler

## Data Flow

### Example: Pricing Inquiry

1. **Webhook receives**: "What's your enterprise pricing?"
2. **Load context**: Fetch lead from CRM (or create)
3. **Decision engine**:
   - Analyzes query: "pricing" keyword detected
   - Decision: RETRIEVE (needs factual lookup)
   - Confidence: 0.85
4. **RAG retrieval**:
   - Query embedding generated
   - Top 8 chunks retrieved from knowledge_base
   - Re-ranked by quality/recency
   - Filtered to top 3 high-confidence sources
5. **Compose response**:
   - LLM prompt includes retrieved pricing info
   - Response grounded in sources
   - Cites "service_pricing.md"
6. **Execute tools**:
   - CRM updated: status → "contacted"
   - Email sent with response
7. **Update memory**:
   - Interaction logged to SQL
   - Conversation turn added to vector store
8. **Return**: Response with confidence 0.85

### Example: Escalation

1. **Webhook receives**: "I want a full refund for the last 6 months"
2. **Load context**: Existing customer, been with us 6 months
3. **Decision engine**:
   - Analyzes query: Sensitive issue, potential dispute
   - Decision: ESCALATE
   - Confidence: 0.35 (below threshold)
4. **Handle escalation**:
   - Escalation event created in DB
   - CRM status → "escalated"
   - Human-friendly response generated
5. **Return**: "I want to ensure you get the best assistance. A team member will reach out shortly."

## Deployment Architecture

### Development
```
Single machine:
- FastAPI process
- SQLite database
- ChromaDB local storage
- Background scheduler
```

### Production (Recommended)
```
Load Balancer
│
├─ FastAPI (Kubernetes pods, N replicas)
│  └─ Connects to:
│     ├─ PostgreSQL (managed, RDS)
│     ├─ Pinecone/Weaviate (vector store)
│     └─ Redis (session state, caching)
│
├─ Background Workers (Celery/K8s CronJobs)
│
└─ Monitoring (DataDog, Prometheus, Grafana)
```

## Security Considerations

1. **API Keys**: Environment variables, never committed
2. **Database**: Encrypted at rest
3. **HTTPS**: TLS 1.3 for all API traffic
4. **Input Validation**: Pydantic schemas
5. **Rate Limiting**: Per-IP rate limits (production)
6. **Secrets Management**: AWS Secrets Manager / HashiCorp Vault (production)

## Performance Characteristics

### Latency (PoC environment)
- Simple query (no retrieval): ~500ms
- With retrieval: ~2-3s (depends on embedding API)
- With tool execution: +500ms per tool

### Throughput (PoC)
- ~10 concurrent requests (single process)
- Can handle 100-500 leads/day

### Production targets
- <1s p50 latency
- <3s p99 latency
- 1000+ concurrent requests
- 10k+ leads/day

## Extensibility

### Adding New Tools
1. Subclass `Tool`
2. Implement `execute()` method returning `ToolResult`
3. Register in `agent/nodes.py:execute_tools()`

### Adding New Doc Types
1. Add markdown files to `knowledge_base/{category}/`
2. Run `python scripts/ingest_knowledge.py`
3. Update re-ranker quality scores if needed

### Swapping LLM Provider
1. Update `LLM_PROVIDER` in `.env`
2. Set appropriate API key
3. No code changes needed

### Scaling Vector Store
1. Replace `SemanticMemory` backend
2. Implement same interface
3. Update connection in initialization
