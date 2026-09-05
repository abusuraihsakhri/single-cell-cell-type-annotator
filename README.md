# Single Cell Cell Type Annotator

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Single Cell Cell Type Annotator** is an analytical platform implementing multi-agent evaluation workers for task payload assessment. It provides:

- Multi-worker consensus evaluation with urgency classification
- HMAC-SHA256 tamper-evident audit trail
- Zero-PHI outbound guard blocking sensitive identifiers
- FastAPI REST API with Prometheus metrics
- CLI for interactive and batch processing

---

## ⚙️ Key Capabilities

- **Multi-Worker Evaluation**: Three specialized workers (QC, Safety, Protocol Conformance) assess each task
- **Urgency Classification**: Automatic ROUTINE / ELEVATED / CRITICAL_STAT categorization
- **Cryptographic Audit Trail**: Chained HMAC-SHA256 signatures for tamper detection
- **PHI Protection**: Active pattern detection blocking SSNs, MRNs, emails, and patient identifiers
- **REST API**: FastAPI endpoints with OpenAPI 3.1 spec
- **Batch Processing**: CSV-based bulk task evaluation

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/single-cell-cell-type-annotator.git
cd single-cell-cell-type-annotator

# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

---

## 💻 CLI Usage

### 1. Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Interactive Chat
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail
```bash
python cli.py verify-audit
```

### 5. Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameters
| Flag | Description | Default |
|:-----|:------------|:--------|
| `--task-id` | Unique task identifier | TASK-2026-001 |
| `--target` | Target identifier | KEY-TARGET-01 |
| `--primary` | Primary metric (float) | 28.5 |
| `--secondary` | Secondary metric (float) | 14.2 |
| `--critical` | Critical flag | False |
| `--status` | Status descriptor | DISCORDANT |

---

## 🛡️ Security

### Audit Trail Secret Key
Set the `AUDIT_SECRET_KEY` environment variable in production:
```bash
export AUDIT_SECRET_KEY="your-secure-random-key"
```

**Warning:** Without this variable, an insecure default is used and a warning is emitted.

### Zero-PHI Guard
The system actively scans outbound data for:
- Medical Record Numbers (MRN)
- Social Security Numbers (SSN)
- Phone numbers and email addresses
- Patient names and dates of birth

---

## 🧪 Testing

```bash
# Run full test suite
pytest -v

# Run with coverage
pytest -v --cov=agents --cov=celltype_annotator

# Run simulation benchmark
python simulator.py --tasks 1000
```

---

## 🐳 Docker Deployment

```bash
# Build and run
docker compose up --build

# Or manually
docker build -t single-cell-cell-type-annotator .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret single-cell-cell-type-annotator
```

---

## 📁 Project Structure

```
├── agents/                    # Enterprise agent modules
│   ├── api.py                # FastAPI REST endpoints
│   ├── base.py               # Security, PHI guard, audit trail
│   ├── models.py             # Pydantic data models
│   ├── supervisor.py         # Main orchestrator
│   ├── workers.py            # Specialized evaluation workers
│   └── ...
├── celltype_annotator/       # Core annotation engine
│   ├── agents.py             # Sub-agent implementations
│   ├── engine.py             # Domain logic engine
│   └── models.py             # Data models
├── tests/                    # Test suite
├── web/                      # Web operations console
├── cli.py                    # Main CLI entry point
├── enrichment.py             # Enrichment feature engines
├── simulator.py              # High-throughput simulator
└── pyproject.toml            # Project configuration
```

---

## 📋 REST API Endpoints

| Method | Path | Description |
|:-------|:-----|:------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/audit` | Submit task for evaluation |
| POST | `/api/chat` | Supervisor chat query |
| GET | `/api/audit/logs` | Get audit trail |

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
