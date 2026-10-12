# Mritra: Enterprise-Grade AML Architecture Stack

Transitioning Mritra from a local datathon prototype to a Tier-1 financial network requires a shift from batch processing to real-time streaming, and from simulated security to hardware-enforced cryptography. Below is the comprehensive, unconstrained technology stack required to build the production system.

## 1. Infrastructure & Zero-Trust Execution

The physical and orchestration layer guarantees that neither the host cloud provider nor a compromised bank can inspect the Enclave's memory.

* **Trusted Execution Environments (TEEs):** **IBM Secure Execution** (for LinuxONE/s390x) or **AWS Nitro Enclaves** (x86/ARM). Replaces the `{"type": "simulated"}` attestation with hardware-backed cryptographic proof of the code's integrity.
* **Container Orchestration:** **Kubernetes (K8s)**. Replaces local Docker Compose to manage autoscaling, self-healing, and rolling deployments of the Bank and Enclave services.
* **Service Mesh:** **Istio** or **Envoy Proxy**. Manages the complex routing, load balancing, and strict mTLS enforcement across the multi-bank network without hardcoding logic into the application layer.

## 2. Real-Time Data & Streaming Engine

Batch processing with DuckDB and Pandas is replaced by an event-driven architecture that calculates behavioral features in milliseconds as transactions occur.

* **Message Broker (Event Bus):** **Apache Kafka** or **Redpanda**. Handles the massive firehose of global transactions, guaranteeing message ordering and fault-tolerant delivery.
* **Stateful Stream Processing:** **Apache Flink**. Replaces Python rolling-window loops. Flink maintains the state of the graph in memory, computing 7-day velocities, standard deviations, and dynamic ratios in real-time.
* **Enterprise Feature Store:** **Feast** or **Hopsworks**. Replaces the temporary Parquet feature files. It serves real-time features to the model for live inference and logs them for perfectly consistent offline model retraining.

## 3. Persistent Storage & State Management

Relational tables and Parquet files are replaced with systems natively designed for topology, scale, and immutability.

* **Distributed Graph Database:** **TigerGraph** or **Neo4j**. Stores the universal transaction topology, allowing sub-second querying of complex multi-hop cycles (e.g., 6-degree scatter-gather laundering patterns).
* **Cryptographic Ledger (Transparency Log):** **Amazon QLDB** (Quantum Ledger Database) or **CockroachDB**. Replaces the local SQLite `tlog.py`. Provides a distributed, mathematically immutable append-only ledger that regulators can continuously audit.
* **Data Lakehouse:** **Databricks** (Apache Iceberg/Delta Lake). Replaces static CSVs for storing petabytes of historical transaction data used for offline model research.

## 4. Advanced Machine Learning & AI

Static decision trees (Snap ML) are augmented or replaced by deep learning models capable of adapting to novel financial crime topologies.

* **Graph Neural Networks (GNNs):** **PyTorch Geometric (PyG)** or **Deep Graph Library (DGL)**. Used to train Temporal Graph Networks (TGNs) and Heterogeneous Graph Transformers (HGTs) that dynamically update account risk embeddings as new edges form.
* **Federated Learning Orchestrator:** **Flower (flwr)** or **PySyft**. Allows banks to collaboratively train the AML models without moving raw customer data across borders.
* **Explainable AI (XAI):** **GNNExplainer**. Extracts the precise sub-graph of transactions that caused the anomaly, providing human investigators with the exact causal chain.
* **Generative AI (SAR Generation):** **Llama 3** (fine-tuned) served via **vLLM**, augmented with **LangChain**. Automatically drafts Suspicious Activity Reports (SARs) by translating the flagged sub-graph and behavioral features into a regulatory-compliant narrative.
* **MLOps & CI/CD for ML:** **MLflow** or **Kubeflow**. Automates model registry, shadow deployments, A/B testing, and continuous retraining to fight concept drift.

## 5. Cryptography & Security

The mathematical enforcement layer that prevents malicious actors from poisoning the network.

* **Fully Homomorphic Encryption (FHE):** **Zama (Concrete)** or **TenSEAL**. Replaces standard TLS payloads for the most sensitive cross-bank queries. Allows the central Enclave to compute Jaccard similarities and reconcile ledgers directly on encrypted ciphertext.
* **Secrets & PKI Management:** **HashiCorp Vault**. Replaces the local `gen_bank_keys.py` script. Automatically provisions, rotates, and revokes the X25519 NaCl keys and RSA client certificates used for the two-way mTLS.

## 6. API & Frontend Integration

The interface layer where the machine learning outputs meet human compliance officers.

* **High-Performance RPC:** **gRPC (Protocol Buffers)**. Replaces standard REST/FastAPI for inter-service communication (Bank $\leftrightarrow$ Enclave) to minimize serialization latency and payload size.
* **Client-Facing API Gateway:** **GraphQL** or **FastAPI**. Serves the curated data to the UI.
* **Frontend Framework:** **React** (with Vite or Next.js) and **TypeScript**. (The stack your teammate is currently using).
* **Graph Visualization:** **Cytoscape.js** or **React Flow**. Renders the complex laundering sub-graphs interactively in the "Case View" dashboard, allowing investigators to visually explore the illicit networks.

This is the exact blueprint a modern fintech unicorn or consortium of Tier-1 banks would build to solve the problem you are tackling.