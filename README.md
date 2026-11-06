# ⚓ Secure Marine Telemetry Ingestion Platform

An enterprise-grade, high-performance, asynchronous DevSecOps data ingestion pipeline designed to ingest streaming oceanographic and meteorological sensor metrics. This architecture combines a zero-trust **FastAPI API Gateway Layer** with an optimized **Polars Extraction Pipeline** and an immutable **PostgreSQL Storage Model** to achieve secure, parallelized data processing and metadata standardization compliant with global **CF-1.6 (Climate and Forecast)** specifications [1.11].

---

## 🏗️ Decoupled Architectural Data Flow

```mermaid
graph TD
    %% Define System Nodes
    Edge[Edge Nodes / Marine Sensor Arrays]
    Secrets[(GitHub Secrets / Env Memory)]
    Gateway[FastAPI API Gateway Ingress]
    Pydantic{Pydantic v2 Boundary Guard}
    Redis[(Redis 7 Asynchronous Message Buffer)]
    Celery[Celery Distributed Worker Array]
    Polars{Vectorized Polars Sorting Filter}
    DB_Valid[(PostgreSQL: telemetry_ingest Table)]
    DB_DLQ[(PostgreSQL: telemetry_dlq Immutable Table)]
    XML[datasets.xml Configuration Map]
    ERDDAP[ERDDAP Server Engine]
    Web[OPeNDAP / Web RESTful Services]
    Workstation[Hydrographic Workstations / Forecast Models]

    %% Define Structural Data Flow
    Edge -->|1. Transmits Telemetry Payload| Gateway
    Secrets -->|Injects JWT_SECRET_KEY| Gateway
    
    Gateway -->|2. Ingests Raw Request| Pydantic
    Pydantic -->|3a. Invalid Type/Schema Violation| DB_DLQ
    Pydantic -->|3b. Valid Clean Payload| Redis
    
    Redis -->|4. Holds Serialized JSON Queue String| Celery
    Celery -->|5. Assembles Records into DataFrame Matrix Chunks| Polars
    
    %% Spatial Filtering Decisions
    Polars -->|6a. Clean Coordinate Stream via psycopg3 Pool| DB_Valid
    Polars -->|6b. Out-of-Bounds Spatial Anomaly Registry| DB_DLQ
    
    %% Downstream Presentation
    DB_Valid -->|7. Relational Topology Mapping Loop| ERDDAP
    XML -->|Injects CF-1.6 Metadata Schema Attributes| ERDDAP
    ERDDAP -->|8. Generates Standardized NetCDF Matrix Profiles| Web
    Web -->|9. Streams In-Situ Visual Dashboard Graphs| Workstation

    %% Applied Custom Design Layout Styling
    classDef secure fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px,color:#000;
    classDef queue fill:#fce4ec,stroke:#f06292,stroke-width:2px,color:#000;
    classDef database fill:#efebe9,stroke:#8d6e63,stroke-width:2px,color:#000;
    classDef network fill:#fff3e0,stroke:#ffb74d,stroke-width:2px,color:#000;
    classDef filter fill:#f1f8e9,stroke:#8bc34a,stroke-width:2px,color:#000;

    class Gateway,Secrets secure;
    class Redis,Celery queue;
    class DB_Valid,DB_DLQ database;
    class Edge,Web,Workstation network;
    class Polars,Pydantic,XML,ERDDAP filter;
```

---

## 🧩 Ingestion Path & Core Component Stack

The platform's data ingestion machinery is completely decoupled to separate ingress network traffic from high-volume analytical computing operations:

1. **Ingress Cryptographic Guard (FastAPI & python-jose):** Acts as the system's front door. It intercepts inbound requests at the `/api/v1/telemetry/submit` entrypoint and runs an asymmetric validation check against the `Authorization: Bearer <JWT>` request header. Payloads lacking an authentic, cryptographically signed token are blocked before straining system memory.
2. **Zero-Trust Boundary Defense (Pydantic v2):** Enforces strict structural type safety on incoming JSON variables. Timestamps must strictly comply with ISO-8601 formatting, and metrics must map directly onto required numeric structures. 
3. **Global Exception Middleware Retention:** Instead of silently dropping malformed data types (such as text values injected into numeric metric floats), the gateway intercepts `RequestValidationError` exceptions via middleware [1.21, 1.28]. The un-parsable body is decoded verbatim and committed directly to the permanent database error ledger [1.11].
4. **High-Performance Vector Slicing (Polars):** Valid structural schemas pass to the Polars parsing layer, which filters out spatial coordinate bounds (Latitudes between -90 and 90; Longitudes between -180 and 180):
   * **Clean Records:** Sent straight to the primary `telemetry_ingest` table connection pool [1.11].
   * **Out-of-Bounds Records:** Automatically stamped with an explicit `Out of bounds spatial coordinates` classification tag and routed directly to the Dead Letter Queue (DLQ).
5. **Immutable Forensic Registry (PostgreSQL & init.sql):** The `telemetry_dlq` table acts as a write-locked, append-only ledger tracking all anomalies [1.11]. It binds spatial anomalies alongside type/schema structure violations into a single dashboard database trail, tracking unalterable insertion times (`inserted_at`) and exact Pydantic/Polars error summaries (`rejection_reason`).
6. **Metadata Standardizer (ERDDAP & datasets.xml):** Translates raw database rows into universally recognized hydrographic data. ERDDAP maps your PostgreSQL tables on boot and overlays strict **CF-1.6** attributes onto columns—mapping internal column strings to globally standardized measurements (e.g., `sea_surface_temperature` and `degrees_north`).

---

## 🔒 Production-Hardened Security Parameters

To maintain a zero-trust architecture, the platform enforces strict security guidelines to prevent credential leaks and runtime failures:

* **No Hardcoded Secrets:** All fallback plain-text strings are stripped entirely from configuration files (`docker-compose.yml` and `app/config.py`). The system forces credentials to be injected dynamically into protected virtual machine memory via environment variables (`${POSTGRES_PASSWORD}`).
* **Timezone Drift Protection:** Runtime token generation entirely bypasses deprecated, naive date methods like `utcnow()`. The platform enforces timezone-aware UTC stamps (`datetime.now(timezone.utc)`) to eliminate time synchronization blocks when services run across different cloud hosting environments.
* **Backward-Compatible Layering:** Custom proxy classes (`LegacyCompatibleDataFrame` and `LegacyCompatibleTuple`) wrap the modern Polars engines. This allows your legacy evaluation scripts to check truthiness conditions and execute row lookups natively without throwing Series ambiguity crashes.

---

## ⚙️ Cloud Laboratory Local Execution Guide

Follow these exact steps inside your **GitHub Codespace** to spin up the multi-container infrastructure and run an un-mocked, live integration test:

### 1. Initialize the Python Package Matrix
Install the pipeline requirements into your working cloud path environment:
```bash
pip install polars "psycopg[pool]" pydantic pydantic-settings celery redis pytest pytest-asyncio httpx "python-jose[cryptography]"
```

### 2. Boot Your Background Connected Service Infrastructure
Use Docker Compose to launch your localized database tables and gateway services securely:
```bash
docker compose up --build -d
```

### 3. Execute the Live End-to-End Test Suite
Trigger the live integration test. This script bypasses all testing mocks, fires a telemetry record over your virtual network, pushes it through the FastAPI gateway, writes the row to PostgreSQL, and queries the container directly to prove data persistence holds true [1.11]:
```bash
PYTHONPATH=. pytest tests/test_e2e_pipeline.py -v
```

---

## 🛡️ Automated DevSecOps Continuous Integration (CI/CD)

Whenever code modifications are pushed to your remote repository branch on GitHub, an automated pipeline (`devsecops.yml`) boots up a clean server runner to audit your codebase automatically using an extensive security gate:

* **Ruff:** Evaluates your application directories for code cleanliness and styling guidelines.
* **Mypy:** Checks your code layouts for strict type configuration anomalies.
* **Bandit:** Inspects your abstract syntax trees (AST) to ensure zero hardcoded secrets or cryptographic holes exist.
* **Trivy:** Runs a static dependency vulnerability scan across your final compiled Docker multi-stage container layers before deploying to the GitHub Container Registry (GHCR).
