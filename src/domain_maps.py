import logging
logger = logging.getLogger(__name__)

def get_vessel_type(type_code: float) -> str:
    try:
        code = int(type_code)
    except:
        logger.info(f"Vessel Type: {type_code} not available!!")
        return "Unknown"

    if code == 0:
        return "Not available"

    if 20 <= code <= 29:
        return "Wing in Ground (WIG)"

    if code == 30:
        return "Fishing"
    if code == 31:
        return "Towing"
    if code == 32:
        return "Towing (length >200m or breadth >25m)"
    if code == 33:
        return "Dredging or underwater operations"
    if code == 34:
        return "Diving operations"
    if code == 35:
        return "Military operations"
    if code == 36:
        return "Sailing"
    if code == 37:
        return "Pleasure craft"
    if 38 <= code <= 39:
        return "Reserved"

    if 40 <= code <= 49:
        return "High-speed craft"

    if code == 50:
        return "Pilot vessel"
    if code == 51:
        return "Search and Rescue"
    if code == 52:
        return "Tug"
    if code == 53:
        return "Port tender"
    if code == 54:
        return "Anti-pollution vessel"
    if code == 55:
        return "Law enforcement vessel"
    if 56 <= code <= 57:
        return "Spare (reserved for future use)"
    if code == 58:
        return "Medical transport"
    if code == 59:
        return "Non-combatant ship"

    if 60 <= code <= 69:
        return "Passenger ship"

    if 70 <= code <= 79:
        return "Cargo ship"

    if 80 <= code <= 89:
        return "Tanker"

    if 90 <= code <= 99:
        return "Other / special vessel"

    return f"Unknown ({code})"


def get_nav_status(status_code: float) -> str:
    try:
        code = int(status_code)
    except:
        return "Unknown"

    mapping = {
        0: "Under way using engine",
        1: "At anchor",
        2: "Not under command",
        3: "Restricted manoeuverability",
        4: "Constrained by draught",
        5: "Moored",
        6: "Aground",
        7: "Engaged in fishing",
        8: "Under way sailing",
        14: "AIS-SART"
    }

    return mapping.get(code, f"Other ({code})")
