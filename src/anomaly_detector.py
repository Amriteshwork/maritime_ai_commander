from geopy.distance import geodesic
import pandas as pd
import math
import logging

logger = logging.getLogger(__name__)

# Mapping AIS VesselTypes to realistic max speeds (knots)
SPEED_LIMITS = {
    range(70, 90): 25.0, # Cargo/Tanker
    range(40, 50): 45.0, # High Speed Craft
    range(30, 40): 20.0, # Tugs/Fishing
    range(52, 53): 18.0, 
    range(60, 70): 30.0  # Passenger
}

def get_max_speed(vessel_type):
    try:
        v_code = int(vessel_type)
        for r, limit in SPEED_LIMITS.items():
            if v_code in r: return limit
    except: pass
    return 30.0

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculates bearing between two points."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d_lon = lon2 - lon1
    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(d_lon))
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def detect_anomalies(history_df: pd.DataFrame) -> dict:
    """
    Analyzes vessel track using 3-point logic (A -> B -> C).
    """
    # Require at least 3 points for "Smoothness" check
    if len(history_df) < 3:
        return {
            "is_clean": True, 
            "summary": "Insufficient history (need 3+ points).", 
            "details": {"flags": []}
        }

    # Get Last 3 Points: p1 (Oldest) -> p2 (Middle) -> p3 (Latest)
    p3 = history_df.iloc[-1]
    p2 = history_df.iloc[-2]
    p1 = history_df.iloc[-3]

    flags = []

    # SEGMENT 1 (A -> B)
    t1 = (p2['Timestamp'] - p1['Timestamp']).total_seconds() / 3600
    d1 = geodesic((p1['LAT'], p1['LON']), (p2['LAT'], p2['LON'])).nautical
    v1 = d1 / t1 if t1 > 0 else 0
    
    # SEGMENT 2 (B -> C)
    t2 = (p3['Timestamp'] - p2['Timestamp']).total_seconds() / 3600
    d2 = geodesic((p2['LAT'], p2['LON']), (p3['LAT'], p3['LON'])).nautical
    v2 = d2 / t2 if t2 > 0 else 0

    # CHECK A: Max Speed (Physics Limit)
    max_allowed = get_max_speed(p3.get('VesselType', 0))
    if v2 > max_allowed:
        flags.append(f"Speed Violation: {v2:.1f}kts (Max {max_allowed}kts)")

    # CHECK B: Acceleration (Smoothness)
    if abs(v2 - v1) > 15.0:
        flags.append(f"Unrealistic Acceleration: {v1:.1f}kts -> {v2:.1f}kts")

    # CHECK C: Trajectory (Turn Smoothness)
    if d1 > 0.5 and d2 > 0.5:
        b1 = calculate_bearing(p1['LAT'], p1['LON'], p2['LAT'], p2['LON'])
        b2 = calculate_bearing(p2['LAT'], p2['LON'], p3['LAT'], p3['LON'])
        
        turn = abs(b2 - b1)
        if turn > 180: turn = 360 - turn
        
        # If moving fast, sharp turns are impossible
        if v2 > 20.0 and turn > 60:
            flags.append(f"Impossible Turn: {turn:.0f}° at {v2:.1f}kts")

    # CHECK D: Spoofing (Heading vs Course)
    cog = p3.get('COG', 0)
    if d2 > 0.5:
        b_final = calculate_bearing(p2['LAT'], p2['LON'], p3['LAT'], p3['LON'])
        diff = abs(cog - b_final)
        if diff > 180: diff = 360 - diff
        if diff > 45:
            flags.append(f"Spoofing Risk: Heading {cog}° vs Course {b_final:.0f}°")

    # Return structure matching main.py expectations
    if not flags:
        return {
            "is_clean": True, 
            "summary": "✅ Movement smooth & consistent.",
            "details": {"flags": []}
        }
    
    return {
        "is_clean": False, 
        "summary": f"⚠️ Found {len(flags)} Anomalies", 
        "details": {"flags": flags}
    }