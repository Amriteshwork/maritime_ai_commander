import os
import folium
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- LOCAL IMPORTS (Modular Architecture) ---
from src.data_loader import DataLoader
from src.nlp_processor import NLPProcessor
from src.geospatial_utils import calculate_future_position
from src.anomaly_detector import detect_anomalies
from src.domain_maps import get_vessel_type, get_nav_status

# --- SETUP & CONFIGURATION ---
base_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(base_dir, "data", "AIS_2020_12_30.csv")
static_dir = os.path.join(base_dir, "static")

# Ensure static directory exists for map files
os.makedirs(static_dir, exist_ok=True)

# Initialize Core Services
app = FastAPI(
    title="Maritime AI Commander", 
    description="NLP-driven interface for AIS tracking and predictive analytics.",
    version="2.0.0" # Version bump to signify "Senior" upgrade
)

# Mount static files to serve generated maps
app.mount("/static", StaticFiles(directory=static_dir), name="static")

print("⏳ Initializing System...")
loader = DataLoader(data_path)
nlp = NLPProcessor(loader.get_all_vessel_names())
print("✅ System Ready. Listening on Port 8000.")

# --- GLOBAL CONTEXT (Session Management) ---
# In production, replace this with Redis keyed by UserID
LAST_VESSEL_CONTEXT = None

class QueryRequest(BaseModel):
    query: str

# --- HELPER: VISUALIZATION (The "Bonus" Requirement) ---
def generate_map(vessel, lat, lon, pred_lat=None, pred_lon=None):
    """Generates a Leaflet map and returns the URL."""
    m = folium.Map(location=[lat, lon], zoom_start=10, tiles="CartoDB positron")
    
    # Current Position Marker
    folium.Marker(
        [lat, lon], 
        popup=f"<b>{vessel}</b><br>Current Position",
        icon=folium.Icon(color="blue", icon="ship", prefix="fa")
    ).add_to(m)

    # Prediction Marker (if applicable)
    if pred_lat and pred_lon:
        folium.Marker(
            [pred_lat, pred_lon],
            popup="Predicted Position",
            icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
        ).add_to(m)
        # Draw dotted line
        folium.PolyLine(
            locations=[[lat, lon], [pred_lat, pred_lon]],
            color="red", weight=2, dash_array="5, 5"
        ).add_to(m)

    filename = f"map_{vessel}_{datetime.now().strftime('%H%M%S')}.html"
    filepath = os.path.join(static_dir, filename)
    m.save(filepath)
    return f"/static/{filename}"

# --- MAIN ENDPOINT ---
@app.post("/query")
def process_query(request: QueryRequest):
    global LAST_VESSEL_CONTEXT
    
    print(f"\n📨 INCOMING QUERY: '{request.query}'")

    # 1. NLP PARSING (Linguistic Structure)
    # Uses spaCy dependency parser to extract intent, vessel, and time params
    parsed = nlp.parse_query(request.query, context_vessel=LAST_VESSEL_CONTEXT)
    
    intent = parsed["intent"]
    vessel = parsed["vessel"]
    minutes = parsed["minutes"]

    # 2. ERROR HANDLING & SUGGESTIONS
    if not vessel:
        # User didn't name a ship, and context was empty/unclear
        suggestions = nlp.get_suggestions(request.query)
        detail_msg = "Vessel not found."
        if suggestions:
            detail_msg += f" Did you mean: {', '.join(suggestions)}?"
        
        raise HTTPException(status_code=404, detail=detail_msg)

    # Update Context for next turn (e.g., "Where is it going?")
    LAST_VESSEL_CONTEXT = vessel

    # 3. DATA RETRIEVAL
    history = loader.get_vessel_history(vessel)
    if history.empty:
         raise HTTPException(status_code=404, detail=f"No AIS data found for '{vessel}'")

    latest = history.iloc[-1]
    
    # 4. INTENT EXECUTION
    response_text = ""
    metadata = {}
    map_url = None

    # Common Data Points
    lat, lon = float(latest['LAT']), float(latest['LON'])
    sog, cog = float(latest['SOG']), float(latest['COG'])
    
    if intent == "SHOW":
        # Enrich with Domain Mappings (Status Codes -> Strings)
        v_type = get_vessel_type(latest.get('VesselType', 0))
        status = get_nav_status(latest.get('Status', 0))
        
        # Calculate Data Freshness
        time_diff = (datetime.now() - latest['Timestamp']).total_seconds() / 3600
        freshness = f"({time_diff:.1f}h ago)" if time_diff < 24 else f"⚠️ OLD DATA ({time_diff/24:.1f} days ago)"

        response_text = (
            f"📍 {vessel} is a {v_type}.\n"
            f"Last seen {freshness} at {lat}, {lon}.\n"
            f"Status: {status} | Speed: {sog} kts | Heading: {cog}°"
        )
        
        map_url = generate_map(vessel, lat, lon)
        metadata = {"status": status, "type": v_type, "freshness_hours": round(time_diff, 1)}

    elif intent == "PREDICT":
        # Uses the 'minutes' extracted by NLP (defaults to 30 if unspecified)
        pred = calculate_future_position(lat, lon, sog, cog, minutes)
        
        response_text = (
            f"🔮 PREDICTION ({minutes} min horizon):\n"
            f"{vessel} will move to {pred['lat']}, {pred['lon']}.\n"
            f"Assumes constant speed of {sog} kts on course {cog}°."
        )
        
        map_url = generate_map(vessel, lat, lon, pred['lat'], pred['lon'])
        metadata = {"horizon_minutes": minutes, "predicted_coords": pred}

    elif intent == "VERIFY":
        # Advanced Anomaly Detection (Returns Dict, not String)
        scan_result = detect_anomalies(history)
        
        status_icon = "✅" if scan_result.get("is_clean", True) else "⚠️"
        summary = scan_result.get("summary", "Analysis complete.")
        
        response_text = f"{status_icon} SECURITY SCAN FOR {vessel}:\n{summary}"
        
        # Append specific warning details if they exist
        details = scan_result.get("details", {})
        if "speed_anomaly" in details:
            d = details['speed_anomaly']
            response_text += f"\n   - Speed Violation: {d['implied']}kts (Max Allowed: {d['max_allowed']}kts)"
        
        if "spoofing_risk" in details:
            d = details['spoofing_risk']
            response_text += f"\n   - Heading Mismatch: Rep {d['reported_cog']}° vs Act {d['actual_bearing']}°"

        map_url = generate_map(vessel, lat, lon)
        metadata = scan_result

    # 5. STANDARDIZED API RESPONSE
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "vessel": vessel,
            "intent": intent,
            "message": response_text,
            "map_url": map_url,
            "metadata": metadata
        }
    }

if __name__ == "__main__":
    import uvicorn
    # Run with reload=True for dev experience
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)