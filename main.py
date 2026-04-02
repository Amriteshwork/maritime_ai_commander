import os
import folium
import uvicorn
import pandas as pd
from datetime import datetime, timezone 
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import logger, DATA_PATH, STATIC_DIR

from src.data_loader import DataLoader
from src.nlp_processor import NLPProcessor
from src.geospatial_utils import calculate_future_position
from src.anomaly_detector import detect_anomalies
from src.domain_maps import get_vessel_type, get_nav_status


app = FastAPI(
    title="Maritime AI Commander", 
    description="NLP-driven interface for AIS tracking and predictive analytics.",
    version="2.1.1"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


logger.info("Initializing System...")
loader = DataLoader(DATA_PATH)
nlp = NLPProcessor(loader.get_all_vessel_names())
logger.info("System Ready. Listening on Port 8000.")

LAST_VESSEL_CONTEXT = None


class QueryRequest(BaseModel):
    query: str

class AgentRequest(BaseModel):
    query: str
    session_id: str = "default_session"

def generate_map(vessel, lat, lon, pred_lat=None, pred_lon=None):
    m = folium.Map(location=[lat, lon], zoom_start=10, tiles="CartoDB positron")

    folium.Marker(
        [lat, lon],
        popup=f"<b>{vessel}</b><br>Current Position",
        icon=folium.Icon(color="blue", icon="ship", prefix="fa")
    ).add_to(m)

    if pred_lat is not None and pred_lon is not None:
        folium.Marker(
            [pred_lat, pred_lon],
            popup="Predicted Position",
            icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
        ).add_to(m)

        folium.PolyLine(
            locations=[[lat, lon], [pred_lat, pred_lon]],
            weight=2,
            dash_array="5, 5"
        ).add_to(m)

    safe_vessel = vessel.replace(" ", "_").replace("/", "_")
    filename = f"map_{safe_vessel}_{datetime.now().strftime('%H%M%S')}.html"
    filepath = os.path.join(STATIC_DIR, filename)

    m.save(filepath)
    return f"/static/{filename}"    

@app.post("/agent/query")
def process_agentic_query(request: AgentRequest):
    """
    Handles queries using LangGraph, MCP, and RAG capabilities.
    Triggers traces in LangSmith automatically.
    """
    try:
        inputs = {"messages": [("user", request.query)]}
        # Configurable thread_id allows LangGraph to maintain conversational memory
        config = {"configurable": {"thread_id": request.session_id}}
        
        result = agent_app.invoke(inputs, config=config)
        final_message = result["messages"][-1].content
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "message": final_message,
                "orchestration_engine": "LangGraph + GPT"
            }
        }
    except Exception as e:
        logger.error(f"Agent error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def process_query(request: QueryRequest):
    global LAST_VESSEL_CONTEXT

    logger.info(f"\nINCOMING QUERY: '{request.query}'")

    parsed = nlp.parse_query(request.query, context_vessel=LAST_VESSEL_CONTEXT)

    intent = parsed.get("intent")
    vessel = parsed.get("vessel")
    minutes = parsed.get("minutes", 30)

    if not vessel:
        suggestions = nlp.get_suggestions(request.query)
        detail_msg = "Vessel not found."
        if suggestions:
            detail_msg += f" Did you mean: {', '.join(suggestions)}?"
        raise HTTPException(status_code=404, detail=detail_msg)

    LAST_VESSEL_CONTEXT = vessel

    history = loader.get_vessel_history(vessel)

    if history is None or history.empty:
        raise HTTPException(status_code=404, detail=f"No AIS data found for '{vessel}'")

    latest = history.iloc[-1]

    # Extraction
    try:
        lat = float(latest["LAT"])
        lon = float(latest["LON"])
        sog = float(latest["SOG"])
        cog = float(latest["COG"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corrupt AIS data: {e}")

    response_text = ""
    metadata = {}
    map_url = None

    if intent == "SHOW":
        v_type = get_vessel_type(latest.get("VesselType", 0))
        status = get_nav_status(latest.get("Status", 0))

        ts = latest["Timestamp"]

        # Ensure timestamp is datetime
        if not isinstance(ts, datetime):
            ts = pd.to_datetime(ts, utc=True)

        time_diff = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        freshness = (
            f"({time_diff:.1f}h ago)"
            if time_diff < 24
            else f"OLD DATA ({time_diff/24:.1f} days ago)"
        )

        response_text = (
            f"{vessel} is a {v_type}.\n"
            f"Last seen {freshness} at {lat}, {lon}.\n"
            f"Status: {status} | Speed: {sog} kts | Heading: {cog}°"
        )

        map_url = generate_map(vessel, lat, lon)
        metadata = {
            "status": status,
            "type": v_type,
            "freshness_hours": round(time_diff, 2)
        }

    elif intent == "PREDICT":
        pred = calculate_future_position(lat, lon, sog, cog, minutes)

        response_text = (
            f"PREDICTION ({minutes} min horizon):\n"
            f"{vessel} will move to {pred['lat']}, {pred['lon']}.\n"
            f"Assumes constant speed of {sog} kts on course {cog}°."
        )

        map_url = generate_map(vessel, lat, lon, pred["lat"], pred["lon"])
        metadata = {
            "horizon_minutes": minutes,
            "predicted_coords": pred
        }

    elif intent == "VERIFY":
        scan_result = detect_anomalies(history)

        status_icon = "✅" if scan_result.get("is_clean", True) else "⚠️"
        summary = scan_result.get("summary", "Analysis complete.")

        response_text = f"{status_icon} SECURITY SCAN FOR {vessel}:\n{summary}"

        for error in scan_result.get("details", {}).get("flags", []):
            response_text += f"\n   - {error}"

        map_url = generate_map(vessel, lat, lon)
        metadata = scan_result

    else:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "vessel": vessel,
            "intent": intent,
            "message": response_text,
            "map_url": map_url,
            "metadata": metadata
        }
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)