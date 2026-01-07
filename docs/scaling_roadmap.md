# Scaling Roadmap

## Current State (PoC)

### Capacity
- **Leads**: 100-500/month
- **Concurrent conversations**: <10
- **Documents**: <1,000 in knowledge base
- **Response time**: 2-3 seconds

### Infrastructure
- Single-machine deployment
- SQLite for CRM data
- ChromaDB local file storage
- Mock tool integrations
- No horizontal scaling

### Limitations
- Single point of failure
- Limited throughput
- Local storage only
- Manual scaling required

## Phase 1: Small Production (Months 1-3)

### Target Capacity
- **Leads**: 1,000-5,000/month
- **Concurrent conversations**: 50
- **Documents**: <10,000
- **Response time**: <1 second (p50), <3 seconds (p99)

### Infrastructure Changes

#### 1. Database Migration
- **From**: SQLite
- **To**: PostgreSQL (managed RDS)
- **Why**: Better concurrency, backups, scalability
- **Migration**: Use Alembic migrations

```bash
# Update settings
DATABASE_URL=postgresql://user:pass@host:5432/agent_db

# Run migrations
alembic upgrade head
```

#### 2. Vector Store Upgrade
- **From**: ChromaDB (local files)
- **To**: Pinecone or Weaviate (managed)
- **Why**: Higher throughput, managed backups
- **Migration**: Re-index all documents

```python
# Pinecone setup
import pinecone
pinecone.init(api_key="...", environment="us-west1-gcp")
index = pinecone.Index("autonomous-agent")
```

#### 3. Horizontal Scaling
- **Deploy**: 3-5 FastAPI instances behind load balancer
- **Load Balancer**: AWS ALB or GCP Load Balancer
- **Orchestration**: Docker Compose or basic K8s

```yaml
# docker-compose.yml
services:
  api:
    image: autonomous-agent:latest
    replicas: 3
    environment:
      - DATABASE_URL=postgresql://...
      - PINECONE_API_KEY=...
```

#### 4. Tool Integrations (Real APIs)
- **CRM**: Integrate with HubSpot/Salesforce
- **Calendar**: Google Calendar API
- **Email**: SendGrid

```python
# HubSpot integration
from hubspot import HubSpot
client = HubSpot(access_token=settings.hubspot_api_key)
contact = client.crm.contacts.basic_api.create(...)
```

#### 5. Caching Layer
- **Add**: Redis for session state and caching
- **Cache**: Embeddings, frequent queries, rate limits

```python
import redis
cache = redis.Redis(host='localhost', port=6379)
```

#### 6. Monitoring
- **Metrics**: Prometheus + Grafana
- **Logging**: Centralized (AWS CloudWatch / GCP Logging)
- **Alerts**: PagerDuty for critical issues

### Estimated Costs (Monthly)
- PostgreSQL (RDS): $50-150
- Pinecone: $70 (1M vectors)
- API hosting: $100-200 (3 instances)
- Redis: $20-50
- **Total**: ~$300-500/month

## Phase 2: Medium Scale (Months 4-12)

### Target Capacity
- **Leads**: 10,000-50,000/month
- **Concurrent conversations**: 200-500
- **Documents**: <100,000
- **Response time**: <500ms (p50), <2 seconds (p99)

### Infrastructure Changes

#### 1. Kubernetes Deployment
- **Orchestration**: Full Kubernetes cluster
- **Auto-scaling**: HPA based on CPU/memory
- **Multi-region**: Deploy to 2+ regions

```yaml
# k8s deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autonomous-agent
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: api
        image: autonomous-agent:v1.2.0
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
```

#### 2. Advanced Caching
- **L1**: In-memory (LRU cache)
- **L2**: Redis cluster
- **Cache**: Embeddings, RAG results, LLM responses

#### 3. Background Job Queue
- **Replace**: APScheduler
- **With**: Celery + Redis/RabbitMQ
- **Why**: Distributed task processing

```python
from celery import Celery
app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def send_followup(lead_id):
    # Async followup task
    pass
```

#### 4. Observability Upgrades
- **APM**: DataDog or New Relic
- **Tracing**: OpenTelemetry for distributed tracing
- **Dashboards**: Real-time metrics

#### 5. LLM Optimization
- **Add**: LLM caching (semantic caching)
- **Add**: Prompt caching for repeated context
- **Consider**: Self-hosted LLMs for cost reduction

```python
# Semantic caching
cache_key = hash(prompt + context)
if cached_response := llm_cache.get(cache_key):
    return cached_response
```

#### 6. Database Optimization
- **Read replicas**: 2-3 replicas for read scaling
- **Connection pooling**: PgBouncer
- **Query optimization**: Indexing, query analysis

### Estimated Costs (Monthly)
- K8s cluster: $500-1,000
- PostgreSQL (larger): $200-400
- Pinecone (10M vectors): $500
- Redis cluster: $100
- Monitoring/APM: $200
- **Total**: ~$2,000-3,000/month

## Phase 3: Large Scale (Year 2+)

### Target Capacity
- **Leads**: 100,000+/month
- **Concurrent conversations**: 1,000+
- **Documents**: 1M+
- **Response time**: <300ms (p50), <1 second (p99)

### Infrastructure Changes

#### 1. Multi-Region Active-Active
- **Regions**: 3+ (US, EU, APAC)
- **Routing**: Global load balancer with latency-based routing
- **Data**: Region-local PostgreSQL with global replication

#### 2. Advanced RAG
- **Hybrid search**: Dense + sparse (BM25) retrieval
- **Query understanding**: Query rewriting, expansion
- **Personalization**: User-specific embeddings
- **Update strategy**: Incremental indexing

```python
# Hybrid search
from hybrid_search import HybridRetriever
retriever = HybridRetriever(
    dense_index=pinecone_index,
    sparse_index=elasticsearch
)
results = retriever.retrieve(query, alpha=0.7)
```

#### 3. LLM Infrastructure
- **Option A**: Self-hosted LLMs (vLLM, TGI)
  - Pros: Cost savings at scale, control
  - Cons: Ops complexity
- **Option B**: Reserved capacity with providers
  - Pros: Simpler, managed
  - Cons: Higher cost

#### 4. Advanced Decision Engine
- **Add**: Reinforcement learning from human feedback (RLHF)
- **Add**: A/B testing framework
- **Add**: Outcome tracking and loop closure

```python
# Track decision outcomes
def log_decision_outcome(decision_id, outcome):
    # Did escalation turn out correct?
    # Did retrieval help?
    # Update decision model
    pass
```

#### 5. Feature Store
- **Add**: Feature store for ML features
- **Cache**: Lead scoring, intent classification
- **Real-time**: Feature updates

#### 6. Data Pipeline
- **ETL**: Daily batch jobs for analytics
- **Data warehouse**: Snowflake/BigQuery
- **BI**: Looker/Tableau dashboards

### Estimated Costs (Monthly)
- Multi-region K8s: $3,000-5,000
- Database cluster: $1,000-2,000
- Vector stores: $1,500
- Monitoring: $500
- LLM costs: $2,000-5,000
- **Total**: ~$10,000-15,000/month

## Migration Checklist

### Phase 1 (Small Production)
- [ ] Set up PostgreSQL
- [ ] Migrate CRM data from SQLite
- [ ] Configure Pinecone/Weaviate
- [ ] Re-index knowledge base
- [ ] Integrate real CRM API
- [ ] Integrate real Calendar API
- [ ] Integrate real Email service
- [ ] Set up Redis
- [ ] Deploy to Docker Compose / K8s
- [ ] Configure load balancer
- [ ] Set up monitoring (Prometheus)
- [ ] Test at 2x expected load

### Phase 2 (Medium Scale)
- [ ] Migrate to Kubernetes
- [ ] Configure auto-scaling
- [ ] Set up multi-region
- [ ] Implement Celery task queue
- [ ] Add advanced caching (L1+L2)
- [ ] Integrate APM (DataDog)
- [ ] Set up distributed tracing
- [ ] Configure read replicas
- [ ] Implement circuit breakers
- [ ] Load test at 5x expected load

### Phase 3 (Large Scale)
- [ ] Multi-region active-active
- [ ] Hybrid search implementation
- [ ] RLHF for decision engine
- [ ] Feature store setup
- [ ] Data warehouse pipeline
- [ ] Self-hosted LLM evaluation
- [ ] Advanced monitoring (anomaly detection)
- [ ] Chaos engineering tests

## Performance Optimization Tips

### 1. Reduce Latency
- Cache embeddings aggressively
- Use async I/O everywhere
- Minimize LLM calls (cache responses)
- Use streaming for long responses
- Parallel tool execution

### 2. Increase Throughput
- Horizontal scaling (more replicas)
- Connection pooling
- Batch operations where possible
- Asynchronous task processing

### 3. Reduce Costs
- Cache LLM responses (semantic similarity)
- Use cheaper models for simple tasks
- Compress embeddings (quantization)
- Reserved capacity for predictable load
- Auto-scale down during off-peak

### 4. Improve Quality
- A/B test prompt variations
- Track and learn from escalations
- Fine-tune decision thresholds based on metrics
- Implement feedback loops

## Key Metrics to Track

### Business Metrics
- Lead volume (daily/monthly)
- Conversion rate (lead → customer)
- Escalation rate
- Time to first response
- Customer satisfaction (CSAT)

### Technical Metrics
- API latency (p50, p95, p99)
- Error rate
- Throughput (requests/second)
- Database query time
- Cache hit rate
- LLM API latency
- Tool execution success rate

### Cost Metrics
- Cost per lead handled
- LLM API costs
- Infrastructure costs
- Cost per customer acquired

### Quality Metrics
- Decision accuracy
- Retrieval relevance
- Response quality (human eval)
- Escalation precision (% of escalations that were necessary)

## Rollback Plan

Each phase should have rollback plan:

1. **Database migrations**: Reversible with Alembic down migrations
2. **Vector store**: Keep old index during transition
3. **API changes**: Blue-green deployment
4. **Feature flags**: Kill switch for new features

## Timeline Summary

| Phase | Timeline | Capacity | Monthly Cost |
|-------|----------|----------|--------------|
| PoC | Current | 100-500 leads | $50 |
| Phase 1 | Months 1-3 | 1k-5k leads | $300-500 |
| Phase 2 | Months 4-12 | 10k-50k leads | $2k-3k |
| Phase 3 | Year 2+ | 100k+ leads | $10k-15k |
