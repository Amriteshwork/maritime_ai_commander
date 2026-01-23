from geopy.distance import geodesic

def calculate_future_position(lat: float, lon: float, speed_knots: float, course_degrees: float, minutes: int):
    """
    Predicts future coordinates using WGS-84 ellipsoid geodesy.
    
    Args:
        lat, lon: Current coordinates
        speed_knots: Speed in nautical miles per hour
        course_degrees: Heading (0-360)
        minutes: Time horizon for prediction
    
    Returns:
        dict: {lat: float, lon: float}
    """
    # 1. Math: Convert Knots to Kilometers per minute for geopy
    # 1 Knot = 1.852 km/h
    speed_kmh = speed_knots * 1.852
    distance_km = (speed_kmh / 60) * minutes
    
    # 2. Physics: Calculate destination
    origin = (lat, lon)
    destination = geodesic(kilometers=distance_km).destination(origin, course_degrees)
    
    return {
        "lat": round(destination.latitude, 5),
        "lon": round(destination.longitude, 5)
    }