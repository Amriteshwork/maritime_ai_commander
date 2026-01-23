from geopy.distance import geodesic
import pandas as pd
import math

# --- DOMAIN KNOWLEDGE MAP ---
# Mapping AIS VesselTypes to realistic max speeds (knots)
SPEED_LIMITS = {
    # Cargo/Tanker (70-89): Heavy, slow.
    range(70, 90): 25.0,
    # High Speed Craft (40-49): Very fast.
    range(40, 50): 45.0, 
    # Tugs/Fishing (30-39, 52): Operational vessels.
    range(30, 40): 20.0,
    range(52, 53): 18.0, 
    # Passenger (60-69): fast ferries vs cruise ships
    range(60, 70): 30.0
}

def get_max_speed(vessel_type):
    """Returns dynamic speed limit based on vessel class."""
    try:
        v_code = int(vessel_type)
        for r, limit in SPEED_LIMITS.items():
            if v_code in r:
                return limit
    except:
        pass
    return 30.0 # Default fallback

def detect_anomalies(history_df: pd.DataFrame) -> dict:
    """
    Analyzes vessel track for physical inconsistencies.
    Returns: Structured dictionary with status and logs.
    """
    if len(history_df) < 2:
        return {"status": "UNCERTAIN", "msg": "Insufficient history."}

    # Data Retrieval
    curr = history_df.iloc[-1]
    prev = history_df.iloc[-2]
    
    # 1. TIME CHECK (Duplicate detection)
    delta_hours = (curr['Timestamp'] - prev['Timestamp']).total_seconds() / 3600
    if delta_hours <= 0:
        return {"status": "ANOMALY", "msg": "Duplicate or unordered timestamps."}

    # 2. SPEED CHECK ("Teleportation")
    distance_nm = geodesic(
        (prev['LAT'], prev['LON']), 
        (curr['LAT'], curr['LON'])
    ).nautical
    
    implied_speed = distance_nm / delta_hours
    max_allowed = get_max_speed(curr.get('VesselType', 0))
    
    if implied_speed > max_allowed:
        return {
            "status": "ANOMALY",
            "msg": f"Impossible Speed: {implied_speed:.1f} kts (Limit: {max_allowed} kts)",
            "details": {"implied_speed": implied_speed, "dist": distance_nm}
        }

    # 3. SPOOFING CHECK (Heading vs Course)
    # If the ship reports heading North (0°) but moves East (90°), it's spoofing.
    reported_cog = curr.get('COG', 0)
    # Only check if the ship actually moved significant distance
    if distance_nm > 0.5:
        # Calculate actual bearing between two points
        lat1, lon1 = math.radians(prev['LAT']), math.radians(prev['LON'])
        lat2, lon2 = math.radians(curr['LAT']), math.radians(curr['LON'])
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        actual_bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
        
        diff = abs(reported_cog - actual_bearing)
        if diff > 180: diff = 360 - diff
        
        if diff > 45: # 45 degrees deviation threshold
            return {
                "status": "WARNING", 
                "msg": f"Heading Mismatch (Spoofing Risk). Rep: {reported_cog:.0f}°, Act: {actual_bearing:.0f}°"
            }

    return {"status": "CLEAN", "msg": "Movement consistent with physical laws."}