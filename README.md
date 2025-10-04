# LIC Receipt Processing Pipeline with Apache Airflow

An automated document processing system that extracts, validates, and processes LIC (Life Insurance Corporation) premium receipts using Apache Airflow orchestration and FastAPI. The system validates premium payments against financial years and ensures document authenticity through intelligent PDF parsing.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Airflow DAG Workflow](#airflow-dag-workflow)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

This project automates the processing of LIC premium receipts through a multi-stage pipeline:

1. **Upload**: FastAPI endpoint receives PDF receipts and metadata
2. **Extraction**: Automated text extraction from PDF documents
3. **Validation**: Document type verification and financial year validation
4. **Processing**: Data structuring and storage
5. **Cleanup**: Automated file management

The system uses Apache Airflow for workflow orchestration, ensuring reliable, monitored, and scalable document processing.

## Architecture

### Components

```
┌─────────────────┐
│   FastAPI App   │ ← Upload endpoint (Port 8000)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Input Directory│ ← PDF + metadata.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Airflow Scheduler│ ← Monitors DAGs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Airflow Worker  │ ← Executes tasks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │ ← Stores task metadata
└─────────────────┘
```

### Airflow Architecture in Docker

**Scheduler**: Monitors DAGs and schedules tasks based on dependencies and timing.

**Executor (CeleryExecutor)**: Distributes tasks across multiple workers using Redis as message broker.

**Worker(s)**: Execute individual task instances in parallel.

**Webserver**: Provides UI for monitoring and managing workflows (Port 8080).

**Metadata Database (PostgreSQL)**: Stores DAG states, task instances, execution logs, and configuration.

**Message Broker (Redis)**: Queues tasks for distributed execution.

## Features

- **PDF Text Extraction**: Intelligent parsing of LIC receipt PDFs using PyPDF2
- **Document Classification**: Automatic identification of LIC receipts vs other documents
- **Premium Amount Extraction**: Regex-based extraction of monetary values
- **Date Parsing**: Flexible date extraction supporting multiple formats
- **Financial Year Validation**: Ensures premiums fall within specified FY periods
- **RESTful API**: FastAPI endpoints for file upload and status monitoring
- **Workflow Orchestration**: Apache Airflow DAG for automated processing
- **XCom Communication**: Inter-task data sharing for workflow continuity
- **Docker Containerization**: Complete multi-container setup with docker-compose
- **Health Checks**: Service monitoring and automatic recovery
- **Persistent Storage**: Volume mapping for logs, data, and DAGs

## Technology Stack

**Backend Framework**
- FastAPI 0.109.2
- Uvicorn (ASGI server)

**Workflow Orchestration**
- Apache Airflow 2.10.5
- CeleryExecutor for distributed task execution

**Data Processing**
- PyPDF2 3.0.1 - PDF parsing
- pdfplumber 0.10.3 - Alternative PDF extraction
- pandas 2.0.3 - Data manipulation
- python-dateutil 2.8.2 - Date parsing

**Infrastructure**
- Docker & Docker Compose
- PostgreSQL 13 - Metadata database
- Redis 7.2 - Message broker

**Python Version**: 3.8+

## Project Structure

```
lic-receipt-processing/
├── docker-compose.yml          # Multi-container orchestration
├── Dockerfile.fastapi          # FastAPI app container
├── requirements.txt            # Python dependencies
│
├── dags/
│   ├── lic_processing_dag.py  # Main Airflow DAG
│   ├── input/                 # Upload directory
│   │   ├── lic_receipt.pdf   # Uploaded PDF (runtime)
│   │   └── metadata.json     # Upload metadata (runtime)
│   └── utils/
│       ├── __init__.py
│       └── pdf_extractor.py  # PDF extraction utilities
│
├── fastapi_app/
│   ├── main.py               # FastAPI application
│   └── models.py             # Pydantic models
│
├── logs/                     # Airflow logs
├── plugins/                  # Airflow plugins
├── config/                   # Airflow configuration
└── data/                     # Processed data storage
```

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- At least 4GB RAM
- 10GB free disk space
- Ports available: 8080 (Airflow), 8000 (FastAPI), 5432 (PostgreSQL), 6379 (Redis)

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/lic-receipt-processing.git
cd lic-receipt-processing
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
# Airflow
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=admin

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=adya
POSTGRES_DB=airflow
```

### 3. Initialize Directory Structure

```bash
mkdir -p ./dags ./logs ./plugins ./config ./data ./input
chmod -R 777 ./logs
```

### 4. Build and Start Services

```bash
# Build Docker images
docker-compose build

# Initialize Airflow database
docker-compose up airflow-init

# Start all services
docker-compose up -d
```

### 5. Verify Services

```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs -f airflow-scheduler
```

### 6. Access Web Interfaces

- **Airflow UI**: http://localhost:8080 (admin/admin)
- **FastAPI Docs**: http://localhost:8000/docs
- **Flower (Celery monitoring)**: http://localhost:5555

## Usage

### Step 1: Upload LIC Receipt

**Using cURL:**

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@/path/to/lic_receipt.pdf" \
  -F "financial_year=2023-24"
```

**Using Python:**

```python
import requests

url = "http://localhost:8000/upload"
files = {"file": open("lic_receipt.pdf", "rb")}
data = {"financial_year": "2023-24"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Response:**

```json
{
  "message": "File uploaded successfully",
  "filename": "lic_receipt.pdf",
  "financial_year": "2023-24",
  "status": "success"
}
```

### Step 2: Trigger Airflow DAG

**Via Airflow UI:**
1. Navigate to http://localhost:8080
2. Find `lic_receipt_processing` DAG
3. Click the "Play" button to trigger

**Via CLI:**

```bash
docker-compose exec airflow-scheduler \
  airflow dags trigger lic_receipt_processing
```

### Step 3: Monitor Processing

**Check Upload Status:**

```bash
curl http://localhost:8000/status
```

**Monitor DAG Execution:**
- View real-time progress in Airflow UI
- Check task logs for detailed output
- Use Graph View to visualize workflow

### Step 4: View Results

Check Airflow task logs for extraction results:

```bash
docker-compose logs airflow-worker | grep "EXTRACTION RESULTS"
```

## API Documentation

### Endpoints

#### POST `/upload`

Upload LIC receipt PDF with financial year metadata.

**Parameters:**
- `file` (file): PDF file of LIC receipt
- `financial_year` (string): Format YYYY-YY (e.g., "2023-24")

**Response:** `UploadResponse`

#### GET `/status`

Check if files are ready for processing.

**Response:**
```json
{
  "pdf_file_exists": true,
  "metadata_exists": true,
  "ready_for_processing": true,
  "timestamp": "2025-01-15T10:30:00",
  "metadata": {
    "financial_year": "2023-24",
    "upload_timestamp": "2025-01-15T10:30:00"
  }
}
```

#### GET `/health`

Health check endpoint.

#### DELETE `/clear`

Clear uploaded files from input directory.

#### GET `/`

API information endpoint.

## Airflow DAG Workflow

### DAG: `lic_receipt_processing`

**Schedule**: Manual trigger (on-demand)  
**Tags**: `lic`, `receipt`, `processing`

### Task Pipeline

```
check_files_exist
       ↓
extract_pdf_data
       ↓
validate_document
       ↓
validate_financial_year
       ↓
cleanup_processed_files
```

### Task Details

1. **check_files_exist**
   - Verifies PDF and metadata.json presence
   - Returns boolean for downstream tasks

2. **extract_pdf_data**
   - Extracts text from PDF using PyPDF2
   - Identifies document type
   - Extracts premium amount and submission date
   - Pushes data to XCom

3. **validate_document**
   - Verifies document is a LIC receipt
   - Checks for minimum 3 LIC-related keywords
   - Pushes validation result to XCom

4. **validate_financial_year**
   - Loads metadata for FY comparison
   - Validates submission date falls within FY period
   - Indian FY: April 1st to March 31st
   - Logs validation results

5. **cleanup_processed_files**
   - Optional file cleanup
   - Logs file paths for manual review

### XCom Keys

- `extracted_data`: Complete extraction results
- `is_valid_document`: Boolean validation status

## Configuration

### Airflow Configuration

Key settings in `docker-compose.yml`:

```yaml
AIRFLOW__CORE__EXECUTOR: CeleryExecutor
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
```

### Volume Mappings

```yaml
volumes:
  - ./dags:/opt/airflow/dags
  - ./logs:/opt/airflow/logs
  - ./plugins:/opt/airflow/plugins
  - ./input:/opt/airflow/dags/input
  - ./data:/opt/airflow/data
```

### Executor Selection

**LocalExecutor**: Single-machine parallel execution
- Use for: Development, testing, small workloads
- Configuration: Change executor in environment variables

**CeleryExecutor** (Current): Distributed execution
- Use for: Production, high availability, horizontal scaling
- Requires: Redis/RabbitMQ message broker

## Troubleshooting

### Common Issues

**Issue: Airflow webserver not accessible**
```bash
# Check service status
docker-compose ps airflow-webserver

# View logs
docker-compose logs airflow-webserver

# Restart service
docker-compose restart airflow-webserver
```

**Issue: Import errors in DAG**
```bash
# Verify utils module is in correct location
ls -la dags/utils/

# Check Python path in worker
docker-compose exec airflow-worker python -c "import sys; print(sys.path)"
```

**Issue: Files not found**
```bash
# Verify volume mounting
docker-compose exec airflow-worker ls -la /opt/airflow/dags/input/

# Check file permissions
docker-compose exec airflow-worker ls -l /opt/airflow/dags/input/
```

**Issue: Database connection errors**
```bash
# Check PostgreSQL health
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U postgres -d airflow -c "SELECT 1;"
```

### Logs Location

- **Airflow Task Logs**: `./logs/dag_id/task_id/`
- **Scheduler Logs**: `docker-compose logs airflow-scheduler`
- **Worker Logs**: `docker-compose logs airflow-worker`
- **FastAPI Logs**: `docker-compose logs fastapi-app`

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart airflow-scheduler

# Full reset (WARNING: Deletes data)
docker-compose down -v
docker-compose up -d
```

## Data Persistence

### Stored Information

- **DAG History**: Task states, execution times, success/failure
- **Logs**: Complete execution logs with timestamps
- **Metadata**: File upload information and validation results
- **XCom Values**: Inter-task communication data

### Volume Management

```bash
# Backup volumes
docker run --rm -v lic_postgres-db-volume:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/airflow_backup.tar.gz /data

# Restore volumes
docker run --rm -v lic_postgres-db-volume:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/airflow_backup.tar.gz -C /
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Follow PEP 8 style guidelines
4. Add tests for new functionality
5. Update documentation as needed
6. Commit changes (`git commit -m 'Add NewFeature'`)
7. Push to branch (`git push origin feature/NewFeature`)
8. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Check code style
flake8 dags/ fastapi_app/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Apache Airflow community for workflow orchestration
- FastAPI for modern Python web framework
- PyPDF2 for PDF processing capabilities

---

**Note**: This is a demonstration project for learning Airflow and document processing. Always validate extracted data against official sources before using in production systems.
