from geopy.distance import geodesic
from typing import Dict

import logging
logger = logging.getLogger(__name__)

def calculate_future_position(lat: float, lon: float, speed_knots: float, course_degrees: float, minutes: int)-> Dict[str, float]:
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
    try:
        if minutes < 0:
            raise ValueError("minutes cannot be negative")
        if speed_knots < 0:
            raise ValueError("speed_knots cannot be negative")

        # Normalize course (0–360)
        course_degrees = course_degrees % 360

        # Convert Knots to Kilometers per minute for geopy
        # 1 Knot = 1.852 km/h
        speed_kmh = speed_knots * 1.852
        distance_km = (speed_kmh / 60) * minutes

        origin = (lat, lon)
        destination = geodesic(kilometers=distance_km).destination(origin, course_degrees)

        return {
            "lat": round(destination.latitude, 5),
            "lon": round(destination.longitude, 5)
        }

    except Exception as e:
        logger.exception("Error calculating future position")
        raise