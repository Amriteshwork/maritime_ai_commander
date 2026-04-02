from langchain_core.tools import tool
from src.data_loader import DataLoader
from src.geospatial_utils import calculate_future_position
from src.anomaly_detector import detect_anomalies
from config import DATA_PATH
import json

# Initialize global loader for tools
loader = DataLoader(DATA_PATH)

@tool
def get_vessel_telemetry(vessel_name: str) -> str:
    """Fetches the latest known latitude, longitude, speed (SOG), and course (COG) for a given vessel."""
    history = loader.get_vessel_history(vessel_name)
    if history.empty: 
        return json.dumps({"error": f"Vessel '{vessel_name}' not found."})
    
    latest = history.iloc[-1]
    return json.dumps({
        "vessel": vessel_name,
        "lat": latest["LAT"], 
        "lon": latest["LON"],
        "sog": latest["SOG"], 
        "cog": latest["COG"]
    })

@tool
def predict_vessel_trajectory(lat: float, lon: float, speed_knots: float, course_degrees: float, minutes: int) -> str:
    """Predicts the future WGS-84 coordinates of a vessel based on current telemetry."""
    result = calculate_future_position(lat, lon, speed_knots, course_degrees, minutes)
    return json.dumps(result)

@tool
def assess_vessel_risk(vessel_name: str) -> str:
    """Runs a 3-point physics validation to detect spoofing, teleportation, or speed anomalies."""
    history = loader.get_vessel_history(vessel_name)
    if history.empty: 
        return json.dumps({"error": f"Vessel '{vessel_name}' not found."})
    
    result = detect_anomalies(history)
    return json.dumps(result)