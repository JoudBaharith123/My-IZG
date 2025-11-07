# Infrastructure Reference - Binder's Business

**Last Updated:** 2025-10-30 (Multi-VM Architecture)  
**Auto-Updated By:** Codex on every infrastructure change

---

## 🖥️ Virtual Machines Overview

| VM | IP Address | GPU | Purpose | Status |
|-----|------------|-----|---------|--------|
| **VM 1** | 149.36.0.182 | 2x RTX A4000 (15GB each) | Logistics AI Services | ✅ Operational |
| **VM 2** | 38.80.122.68 | 1x H100-80GB PCIe | Ruyah LLM + RAG + LoRA | ✅ Infrastructure Ready |

---

## 🔷 VM 1: Logistics AI Platform

### Basic Info

```yaml
Name: route-cv-ocr
IP: 149.36.0.182
SSH Key: D:/hyperstack
SSH Command: ssh -i "D:/hyperstack" ubuntu@149.36.0.182

Specifications:
  GPU: 2x NVIDIA RTX A4000 (15GB VRAM each)
  CPU: 32 cores
  RAM: 42 GB
  Storage:
    System: 97 GB (/dev/vda1)
    Data: 97 GB (/mnt/ephemeral)
  OS: Ubuntu 22.04 LTS
```

### Service Ports

| Service | Port | GPU | Status | Purpose |
|---------|------|-----|--------|---------|
| OSRM Engine | 5000 | - | ✅ Running | Routing calculations (legacy) |
| OSRM Proxy | 5010 | - | ✅ Running | Proxy → Legacy OSRM |
| Dynamic Routing | 8080 | - | ✅ Running | Route optimization (legacy) |
| Routing Proxy | 8090 | - | ✅ Running | Proxy → Legacy routing |
| Zone Calculator | 8081 | - | ✅ Running | Zone assignment |
| CV API | 8082 | GPU 0 | ✅ Running | Product detection |
| OCR API | 8083 | GPU 1 | ✅ Running | Document OCR |
| Prometheus | 9090 | - | ✅ Running | Monitoring |
| Grafana | 3000 | - | ⏳ Planned | Dashboards |

### GPU Allocation (VM 1)

#### GPU 0 (RTX A4000 #1)
```yaml
Service: CV API (04-cv-api)
Port: 8082
VRAM Allocated: 12 GB
CUDA Device: 0
Status: ✅ Active
Model: Product detection models
```

#### GPU 1 (RTX A4000 #2)
```yaml
Service: OCR API (05-ocr-api)
Port: 8083
VRAM Allocated: 8 GB
CUDA Device: 1
Status: ✅ Active
Model: Document OCR & classification
```

**⚠️ CRITICAL:** Never assign both GPUs to the same service. Each service gets exclusive GPU access.

### Directory Structure (VM 1)

```bash
/opt/logistics-ai-platform/              # Application root
├── services/
│   ├── 01-osrm-engine/                 # Port 5000
│   ├── 02-dynamic-routing/             # Port 8080
│   ├── 03-zone-calculator/             # Port 8081
│   ├── 04-cv-api/                      # Port 8082 (GPU 0)
│   └── 05-ocr-api/                     # Port 8083 (GPU 1)
├── config/                              # Configurations
├── scripts/                             # Automation
├── data/ → /mnt/ephemeral/data         # Data symlink
└── logs/                                # Logs

/mnt/ephemeral/data/                     # Data storage
├── uploads/                             # Input files
├── outputs/                             # Results
├── models/                              # ML models
├── cache/                               # Temporary
└── backups/                             # Backups
```

### Health Checks (VM 1)

```bash
# Comprehensive system check
ssh -i "D:/hyperstack" ubuntu@149.36.0.182 "sudo bash /opt/logistics-ai-platform/scripts/system-health-check.sh"

# Individual services
curl http://149.36.0.182:5010/health   # OSRM Proxy
curl http://149.36.0.182:8081/health   # Zone Calculator
curl http://149.36.0.182:8082/health   # CV API
curl http://149.36.0.182:8083/health   # OCR API
curl http://149.36.0.182:8090/health   # Routing Proxy
```

---

## 🔶 VM 2: Ruyah LLM Platform

### Basic Info

```yaml
Name: ruyah-llm-h100
IP: 38.80.122.68
SSH Key: D:/hyperstack (same as VM 1)
SSH Command: ssh -i "D:/hyperstack" ubuntu@38.80.122.68

Specifications:
  GPU: 1x NVIDIA H100 PCIe (81.5 GB VRAM)
  CPU: 28 cores (AMD EPYC 9554)
  RAM: 177 GB
  Storage:
    System: 100 GB (/dev/vda1)
    Ephemeral: 750 GB (/dev/vdb)
    Persistent: 2.0 TB (/dev/vdc) ✅
  OS: Ubuntu 22.04.5 LTS
  Python: 3.10.12
  CUDA: 12.2
  Driver: 535.183.06
```

### Service Ports (Phase 7 - To Be Deployed)

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| Ruyah LLM API | 8000 | ⏳ Planned | LLM inference |
| RAG API | 8001 | ⏳ Planned | Knowledge retrieval |
| LoRA Management | 8002 | ⏳ Planned | Fine-tuning management |
| Qdrant Vector DB | 6333 | ⏳ Planned | Vector database (localhost) |

### GPU Allocation (VM 2)

#### H100 PCIe (81.5 GB VRAM)
```yaml
Service: Ruyah LLM Inference
Port: 8000
VRAM Allocated: ~70 GB (for large LLM models)
CUDA Device: 0
Status: ⏳ Awaiting Phase 7 deployment
Models:
  - Primary: Llama or similar large language models
  - RAG: Embedding models for semantic search
  - LoRA: Fine-tuned adapters for domain-specific tasks
```

### Directory Structure (VM 2)

```bash
/opt/ruyah-llm/                          # Application code
├── services/
│   ├── llm-api/                         # Port 8000
│   ├── rag-api/                         # Port 8001
│   └── lora-management/                 # Port 8002
├── config/                              # Configurations
├── scripts/                             # Automation
└── logs/                                # Logs

/mnt/persistent/                         # 2 TB persistent storage
├── models/                              # LLM models (~500GB-1TB)
│   ├── base/                           # Base LLM models
│   └── embeddings/                     # Embedding models
├── lora/                                # LoRA adapters (~10-50GB)
│   ├── customer-service/
│   ├── logistics-domain/
│   └── arabic-dialect/
├── rag/                                 # RAG knowledge base (~100-300GB)
│   ├── vector-db/                      # Qdrant data
│   └── documents/                      # Source documents
├── datasets/                            # Training data (~100-200GB)
│   ├── fine-tuning/
│   └── evaluation/
├── backups/                             # Backups (~200-400GB)
└── logs/                                # System logs

/ephemeral/                              # 750 GB temporary cache
└── inference-cache/                     # Fast inference cache
```

### Health Checks (VM 2 - After Phase 7)

```bash
# Individual services (not yet deployed)
curl http://38.80.122.68:8000/health   # Ruyah LLM API
curl http://38.80.122.68:8001/health   # RAG API
curl http://38.80.122.68:8002/health   # LoRA Management

# GPU status
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "nvidia-smi"

# Storage status
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "df -h | grep -E 'persistent|ephemeral'"
```

---

## 🌐 Inter-VM Communication

### Network Map

```
VM 1 (149.36.0.182) ⟷ VM 2 (38.80.122.68)

VM 1 → VM 2:
  - Port 8000: Ruyah LLM Inference
  - Port 8001: RAG Knowledge Retrieval
  - Port 8002: LoRA Management

VM 2 → VM 1:
  - Port 5000: OSRM Engine
  - Port 5010: OSRM Proxy
  - Port 8080: Dynamic Routing
  - Port 8081: Zone Calculator
  - Port 8082: CV API
  - Port 8083: OCR API
  - Port 8090: Routing Proxy
```

### Use Cases for Cross-VM Integration

```yaml
Scenario 1: AI-Enhanced Routing
  Flow: VM1 Routing → VM2 LLM → VM1 Decision
  Purpose: Use LLM to analyze customer preferences and suggest optimal routes

Scenario 2: Document Intelligence
  Flow: VM1 OCR → VM2 RAG → VM1 Response
  Purpose: Extract text from documents and query knowledge base

Scenario 3: Customer Service Augmentation
  Flow: VM1 Customer Data → VM2 LLM + RAG → VM1 Response
  Purpose: Generate personalized customer communications using domain knowledge
```

### Firewall Configuration

**VM 1 Firewall:**
```bash
# Allows VM2 (38.80.122.68) to access all services
sudo ufw allow from 38.80.122.68 to any port 5000:8090
sudo ufw status verbose
```

**VM 2 Firewall:**
```bash
# Allows VM1 (149.36.0.182) to access LLM services
sudo ufw allow from 149.36.0.182 to any port 8000:8002
sudo ufw status verbose
```

---

## 🔐 Credentials & Secrets

### VM 1 Secrets

```bash
Location: /opt/logistics-ai-platform/config/secrets/.env.secret

Environment Variables:
  # Database
  POSTGRES_USER=logistics_admin
  POSTGRES_PASSWORD=[stored in .env.secret]
  POSTGRES_DB=logistics

  # API Keys
  GEMINI_API_KEY=[stored in .env.secret]
  API_MASTER_KEY=[stored in .env.secret]

  # External Services
  SLACK_WEBHOOK_URL=[stored in .env.secret]
```

### VM 2 Secrets (Phase 7)

```bash
Location: /opt/ruyah-llm/config/secrets/.env.secret

Environment Variables:
  # LLM Configuration
  HUGGINGFACE_TOKEN=[to be configured]
  OPENAI_API_KEY=[optional fallback]
  
  # Vector Database
  QDRANT_API_KEY=[to be generated]
  
  # Inter-VM Communication
  VM1_API_KEY=[shared secret with VM1]
```

---

## 🛠️ Quick Commands

### SSH Access

```bash
# VM 1 - Logistics AI
ssh -i "D:/hyperstack" ubuntu@149.36.0.182

# VM 2 - Ruyah LLM
ssh -i "D:/hyperstack" ubuntu@38.80.122.68
```

### GPU Monitoring

```bash
# VM 1 (2x RTX A4000)
ssh -i "D:/hyperstack" ubuntu@149.36.0.182 "nvidia-smi"
ssh -i "D:/hyperstack" ubuntu@149.36.0.182 "watch -n 1 nvidia-smi"

# VM 2 (1x H100)
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "nvidia-smi"
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "watch -n 1 nvidia-smi"
```

### Storage Monitoring

```bash
# VM 1 storage
ssh -i "D:/hyperstack" ubuntu@149.36.0.182 "df -h"

# VM 2 storage (detailed)
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "df -h | grep -E 'Filesystem|persistent|ephemeral|vda1'"
```

### Port Availability Check

```bash
# VM 1
ssh -i "D:/hyperstack" ubuntu@149.36.0.182 "sudo netstat -tulpn | grep -E '5000|5010|8080|8081|8082|8083|8090|9090|3000'"

# VM 2
ssh -i "D:/hyperstack" ubuntu@38.80.122.68 "sudo netstat -tulpn | grep -E '8000|8001|8002|6333'"
```

---

## 🌍 External Access (HTTPS)

### VM 1 (After Nginx Configuration)

```
https://149.36.0.182/osrm/      → OSRM Engine (5000)
https://149.36.0.182/routing/   → Dynamic Routing (8080)
https://149.36.0.182/zones/     → Zone Calculator (8081)
https://149.36.0.182/cv/        → CV API (8082)
https://149.36.0.182/ocr/       → OCR API (8083)
```

### VM 2 (Phase 7 - After Nginx Configuration)

```
https://38.80.122.68/llm/       → Ruyah LLM API (8000)
https://38.80.122.68/rag/       → RAG API (8001)
https://38.80.122.68/lora/      → LoRA Management (8002)
```

---

## 📊 Monitoring

### VM 1 Monitoring

```yaml
Prometheus:
  URL: http://149.36.0.182:9090
  Status: ✅ Running
  Purpose: Metrics collection for all VM1 services

Grafana:
  URL: http://149.36.0.182:3000
  Status: ⏳ Planned
  Purpose: Unified dashboards for VM1 services
```

### VM 2 Monitoring (Phase 8)

```yaml
Prometheus:
  URL: http://38.80.122.68:9090
  Status: ⏳ Planned
  Purpose: LLM inference metrics, GPU utilization

Grafana:
  URL: http://38.80.122.68:3000
  Status: ⏳ Planned
  Purpose: LLM performance dashboards
```

---

## 🔄 Service Dependencies

### VM 1 Dependencies

```
Foundation:
  01-osrm-engine (no dependencies)
    ↓
Dependent:
  02-dynamic-routing (requires OSRM)
  03-zone-calculator (requires OSRM)

Independent:
  04-cv-api (GPU 0, no dependencies)
  05-ocr-api (GPU 1, no dependencies)
```

### VM 2 Dependencies (Phase 7)

```
Foundation:
  Qdrant Vector DB (localhost:6333)
    ↓
Dependent:
  RAG API (8001) - requires Qdrant
    ↓
  Ruyah LLM API (8000) - can use RAG
  LoRA Management (8002) - independent
```

**Rule for VM 1:** Always start OSRM first, then others can start in any order.  
**Rule for VM 2:** Start Qdrant first, then RAG, then LLM and LoRA services.

---

## 📈 Deployment Status

```
Phase 0: Infrastructure Prep      ██████████ 100% ✅
Phase 1: VM 1 Foundation           ██████████ 100% ✅
Phase 2: SchemaValidator           ██████████ 100% ✅
Phase 3a: Proxy Layer              ██████████ 100% ✅
Phase 3b/3c: Migration             ░░░░░░░░░░   0% (Deferred)
Phase 4: GPU Services (VM1)        ██████████ 100% ✅
Phase 5: Integration & Testing     ██████████ 100% ✅
Phase 6: VM 2 Infrastructure       ██████████ 100% ✅
Phase 7: Ruyah LLM + RAG + LoRA    ░░░░░░░░░░   0% ← Next
Phase 8: Cross-VM Integration      ░░░░░░░░░░   0%
Phase 9: Monitoring & Ops          ░░░░░░░░░░   0%
```

**Overall Progress:** 60% complete (6 of 10 phases)

---

## 🚨 Emergency Procedures

### System Recovery

#### VM 1 Recovery
```bash
# Check VM status via Hyperstack dashboard
# SSH to VM and check services
ssh -i "D:/hyperstack" ubuntu@149.36.0.182

# Review logs
sudo tail -f /opt/logistics-ai-platform/logs/*.log

# Restart all services
sudo systemctl restart osrm-engine
sudo systemctl restart dynamic-routing
sudo systemctl restart zone-calculator
sudo systemctl restart cv-api
sudo systemctl restart ocr-api
```

#### VM 2 Recovery (After Phase 7)
```bash
# SSH to VM
ssh -i "D:/hyperstack" ubuntu@38.80.122.68

# Check GPU status
nvidia-smi

# Review logs
sudo tail -f /opt/ruyah-llm/logs/*.log

# Restart services
sudo systemctl restart qdrant
sudo systemctl restart rag-api
sudo systemctl restart ruyah-llm-api
sudo systemctl restart lora-management
```

### Rollback Procedures

#### VM 1 Rollback
```bash
ssh -i "D:/hyperstack" ubuntu@149.36.0.182
sudo bash /opt/logistics-ai-platform/scripts/maintenance/backup.sh manual
# Then restore from previous backup
```

#### VM 2 Rollback (After Phase 7)
```bash
ssh -i "D:/hyperstack" ubuntu@38.80.122.68
sudo bash /opt/ruyah-llm/scripts/maintenance/backup.sh manual
# Then restore from previous backup
```

---

## 📚 Documentation Index

### Core Documentation
1. **CLAUDE.md** - Project guidelines and quick reference
2. **PHASED_DEPLOYMENT_ROADMAP.md** - Complete deployment plan
3. **VM_PRODUCT_SPECIFICATION.md** - Detailed infrastructure spec
4. **VM_INVENTORY.md** - VM inventory and quick reference

### Phase Completion
1. **PHASE4_COMPLETE.md** - GPU services deployment (VM1)
2. **PHASE5_COMPLETE.md** - VM1 integration & testing
3. **PHASE6_COMPLETE.md** - VM2 infrastructure setup

### Configuration
1. **PORTS.md** - Port allocation reference (both VMs)
2. **FIREWALL_RULES.md** - Security configuration
3. **VM2_STORAGE_RECOMMENDATION.md** - VM2 storage analysis

---

## 📝 Changelog

### 2025-10-30 - Multi-VM Architecture Update
- Added VM 2 (Ruyah LLM Platform) with H100 GPU
- Documented inter-VM communication architecture
- Added cross-VM integration use cases
- Updated monitoring strategy for multi-VM setup
- Added Phase 7 service definitions for VM2
- Documented storage layout for 2TB persistent storage

### 2025-10-29 14:23:45
- Initial infrastructure documentation created
- All VM1 services documented with ports and status
- GPU allocation mapped for VM1
- SSH access verified

---

**END OF INFRASTRUCTURE REFERENCE**

*Codex will auto-update this file when infrastructure changes occur.*
