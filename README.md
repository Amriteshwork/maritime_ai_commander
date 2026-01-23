# AIS NLP Query Prototype

## Overview
A lightweight, production-ready prototype for querying maritime AIS data using natural language. 
Designed for the **Crimson Energy** interview task.

## Architecture Decisions (Senior Engineer Notes)
* **Modular Design:** Code is split into `src/` modules (Logic, NLP, Data) to ensure separation of concerns.
* **Zero-LLM Approach:** Used deterministic NLP (`spaCy`/Regex) instead of heavy LLMs to ensure **low latency (<50ms)** and **offline capability** suitable for maritime edge devices.
* **Geodesic Physics:** Implemented `geopy` (WGS-84 ellipsoid) rather than simple Euclidean math to ensure navigational accuracy over long distances.
* **Anomaly Detection:** Includes a physics-based verification engine to detect AIS spoofing (e.g., impossible speed jumps).

## Setup
1.  Install dependencies: `pip install -r requirements.txt`
2.  Run the API: `python main.py`
3.  Open Swagger UI: `http://localhost:8000/docs`

## Features
* **Fuzzy Matching:** Handles typos (e.g., "Show INS Kolkatta").
* **Stale Data Warnings:** Flags if AIS data is >1 hour old.
* **Fraud Detection:** Validates vessel physics to detect "teleporting" ships.

## Future Roadmap (Production)
* Migrate CSV storage to **PostGIS** for R-Tree spatial indexing.
* Integrate **Llama-3-8B** for complex multi-intent queries.