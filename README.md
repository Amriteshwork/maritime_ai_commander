# Maritime AI Commander

**An NLP-driven Microservice for AIS Tracking, Predictive Analytics, and Anomaly Detection.**

A FastAPI-based prototype that allows users to interact with maritime AIS (Automatic Identification System) data using natural language queries. The system supports vessel lookup, trajectory prediction, anomaly detection, and interactive geospatial visualization.

## Features
- **Natural Language Queries**
    - "Show the last known position of INS Kolkata"
    - "Predict where MSC Flaminia will be after 45 minutes"
    - "Check if Ever Given movement is consistent"
- **spaCy-based NLP Engine**
    - Custom vessel entity recognition
    - Intent detection (SHOW / PREDICT / VERIFY)
    - Context-aware follow-up queries
- **AIS Data Processing Pipeline**
    - Cleaning, normalization, de-duplication
    - UTC timestamp enforcement
    - Robust vessel filtering
- **Geospatial Visualization**
    - Folium-generated interactive maps
    - Current + predicted positions plotted
- **Trajectory Prediction**
    - Geodesic projection using speed (SOG), course (COG), and time horizon
- **Anomaly Detection**
    - Teleportation / impossible speed
    - Timestamp inconsistency
    - Spoofing risk (heading vs actual bearing)
- **REST API via FastAPI**

---
## Architecture Overview
``` bash
/maritime_ai_commander
│
├── main.py                 # Application Entry Point
├── requirements.txt        # Dependencies
├── README.md               # Documentation
├── docker-compose.yml
├── Dockerfile
│
├── data/
│   └── ais_sample_data.csv # Dataset
│
├── static/                 # Generated .html Leaflet maps
│
└── src/
    ├── __init__.py
    ├── logger_config.py    # Centralized Logging Setup
    ├── data_loader.py      # Robust CSV Loading & UTC Normalization
    ├── nlp_processor.py    # spaCy Logic (Entity Ruler + Matcher)
    ├── anomaly_detector.py # 3-Point Physics Validation Logic
    ├── geospatial_utils.py # WGS-84 Geodesic Calculations
    └── domain_maps.py      # ITU-R M.1371 Mappings
```
---
## NLP Design

The NLP system is implemented using spaCy with:   
- Entity recognition using a dynamically generated EntityRuler from known vessel names
- Intent recognition using spaCy’s Matcher
- Regex-based time extraction (e.g., "30 min", "2 hours")
- Context memory (resolves pronouns like "it", "she", "the vessel" across queries)

Implementation: `NLPProcessor` class in `nlp_processor.py`

| Intent  | Example Query                                       | Behavior                             |
| ------- | --------------------------------------------------- | ------------------------------------ |
| SHOW    | "Show last position of INS Kolkata"                 | Returns latest lat/lon, status, type |
| PREDICT | "Predict where Ever Given will be after 2 hours" | Projects future coordinates          |
| VERIFY  | "Check if MSC Flaminia movement is consistent"      | Runs anomaly detection on track      |

---
## Context-Aware State Management
Unlike stateless scripts that require repetitive inputs, this system maintains a **Session Context**. It intelligently resolves pronouns based on the conversation history.

* **Multi-Turn Conversation:**
    * *Turn 1:* "Where is **INS Kolkata**?" (System caches entity: `INS KOLKATA`)
    * *Turn 2:* "How fast is **it** moving?" (System resolves "it" -> `INS KOLKATA`)
    * *Turn 3:* "Predict **its** location in 30 mins." (System maintains focus on `INS KOLKATA`)
* **Technical Implementation:** Uses a global session state (extensible to Redis for production) to track the active subject, reducing user friction and mimicking natural human dialogue.
---
## Prediction Logic

Prediction uses geodesic navigation over WGS-84 ellipsoid:
- Converts speed from knots → km/h
- Computes travel distance based on time horizon
- Uses `geopy.geodesic().destination()` to calculate new coordinates
- Returns rounded `lat/lon`   
Implemented in `calculate_future_position()`   
    - geospatial_utils.py

---
## Anomaly Detection Logic
The system validates vessel movement using three checks:
- Timestamp validation
    - Detects duplicate or unordered timestamps
- Teleportation detection
    - Calculates implied speed between last two points
    - Compares with realistic max speed per vessel class
- Spoofing detection
    - Compares reported COG with actual bearing
    - Flags if deviation > 45°   

Implemented in `detect_anomalies()`
> anomaly_detector.py
---

## Data Handling
AIS data is processed using DataLoader:
- Loads CSV safely
- Normalizes column names
- Converts types robustly
- Enforces `UTC` timestamps
- Removes invalid coordinates
- Deduplicates by `MMSI + Timestamp`
- Cleans vessel names
> data_loader.py
---

## Vessel & Navigation Semantics
AIS codes are mapped to human-readable maritime labels:
- Vessel types (Fishing, Cargo, Tanker, Military, etc.)
- Navigational status (Under way, Anchored, Moored, etc.)
> domain_maps.py

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- pip

### 1. Clone the Repository
```bash
git clone https://github.com/Amriteshwork/maritime_ai_commander.git

cd maritime_ai_commander
```
### 2. Create and Activate Virtual Environment (Recommended)
On Linux / macOS
```bash
python3 -m venv venv

source venv/bin/activate
```
On Windows (PowerShell)
```bash
python -m venv venv

venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
You must also install the spaCy English model:
```bash
python -m spacy download en_core_web_sm
```
### 4. Check Dataset Location
The project expects this file to exist:
> data/ais_sample_data.csv   

If the file is missing, the app will fail with:
> `FileNotFoundError`: Data file not found

So ensure the folder structure looks like:
```bash
project-root/
├── main.py
├── data/
│   └── ais_sample_data.csv
```
### 5. Run the FastAPI Server
Start the API using uvicorn:
```bash
uvicorn main:app --reload
```
It should see output like:
```bash
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```
The system is now `LIVE`

## Using FastAPI Interactive Docs (Swagger UI)
Open your browser and go to:
> http://127.0.0.1:8000/docs

You will see an interactive UI where you can test the API without writing any code.   
**Example:**   
1. Click on POST /query
2. Click "Try it out"
3. Enter:
    ```bash
        {
            "query": "Show the last known position of INS Kolkata"
        }
    ```
4. Click Execute
You will receive a JSON response with:
- Vessel details
- Textual analysis
- Map URL
- Metadata

```json
    {
  "status": "success",
  "timestamp": "2026-01-25T12:49:18.177543+00:00",
  "data": {
    "vessel": "INS KOLKATA",
    "intent": "SHOW",
    "message": "INS KOLKATA is a Military operations.\nLast seen OLD DATA (3.1 days ago) at 12.95, 80.33.\nStatus: Under way using engine | Speed: 15.0 kts | Heading: 135.0°",
    "map_url": "/static/map_INS_KOLKATA_181918.html",
    "metadata": {
      "status": "Under way using engine",
      "type": "Military operations",
      "freshness_hours": 74.32
    }
  }
}
```
> **Example Response: Prediction**   
***Query**: "Where it will be in 2 hours?"*
```json
{
  "status": "success",
  "timestamp": "2026-01-25T12:49:53.903410+00:00",
  "data": {
    "vessel": "INS KOLKATA",
    "intent": "PREDICT",
    "message": "PREDICTION (120 min horizon):\nINS KOLKATA will move to 12.59463, 80.69156.\nAssumes constant speed of 15.0 kts on course 135.0°.",
    "map_url": "/static/map_INS_KOLKATA_181953.html",
    "metadata": {
      "horizon_minutes": 120,
      "predicted_coords": {
        "lat": 12.59463,
        "lon": 80.69156
      }
    }
  }
}
```
> **Example Response: Anomaly Detection**   
***Query**: "Verify Ever Given for anomalies?"*
```json
{
  "status": "success",
  "timestamp": "2026-01-25T12:47:19.938763+00:00",
  "data": {
    "vessel": "EVER GIVEN",
    "intent": "VERIFY",
    "message": "⚠️ SECURITY SCAN FOR EVER GIVEN:\n⚠️ Found 3 Anomalies\n   - Speed Violation: 714.8kts (Max 25.0kts)\n   - Unrealistic Acceleration: 3.6kts -> 714.8kts\n   - Spoofing Risk: Heading 180.0° vs Course 0°",
    "map_url": "/static/map_EVER_GIVEN_181719.html",
    "metadata": {
      "is_clean": false,
      "summary": "⚠️ Found 3 Anomalies",
      "details": {
        "flags": [
          "Speed Violation: 714.8kts (Max 25.0kts)",
          "Unrealistic Acceleration: 3.6kts -> 714.8kts",
          "Spoofing Risk: Heading 180.0° vs Course 0°"
        ]
      }
    }
  }
}
```
---
## Using curl from Terminal
You can also test directly from the command line.   
**Example 1 — Show vessel position**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show the last known position of INS Kolkata"}'
```
**Example 2 — Predict future position**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Predict where INS Kolkata will be after 30 minutes"}'
  ```
**Example 3 — Verify movement consistency**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Check if INS Kolkata movement is consistent"}'
```
## Docker Setup
Run the entire system in a container without installing Python dependencies locally.

**Build and Run**
```bash
docker-compose up --build
```
- Access the API The service will be available at http://localhost:8000
Maps: Maps generated inside the container will be synced to your local static/ folder

---
## Viewing the Generated Map
Each successful query generates a Folium HTML map. In the response we will see something like:
```bash
"map_url": "/static/map_INS_KOLKATA_153210.html"
```
Open it in browser:
```bash
http://127.0.0.1:8000/static/map_INS_KOLKATA_153210.html
```
- Blue marker -> current position
- Red marker -> predicted position (if prediction)
- Dashed line -> movement path
---
## References
The following external resources were used for understanding AIS domain concepts and implementing logic in this project:
- AIS Vessel Type Codes (NOAA / Marine Cadastre)   
https://coast.noaa.gov/data/marinecadastre/ais/VesselTypeCodes2018.pdf

- AIS Navigational Status Values (MarineTraffic Support)   
https://support.marinetraffic.com/en/articles/9552867-what-do-ais-navigational-status-values-mean

- U.S. Coast Guard AIS Guide   
https://www.navcen.uscg.gov/sites/default/files/pdf/AIS/AISGuide.pdf

- International Telecommunication Union (ITU)   
https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-5-201402-I!!PDF-E.pdf




