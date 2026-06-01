import folium
import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Major airport coordinates lookup (IATA → lat, lon, city name)
AIRPORT_COORDS = {
    "BOM": (19.0896, 72.8656, "Mumbai"),
    "DEL": (28.5562, 77.1000, "Delhi"),
    "BLR": (13.1986, 77.7066, "Bangalore"),
    "MAA": (12.9941, 80.1709, "Chennai"),
    "CCU": (22.6520, 88.4463, "Kolkata"),
    "HYD": (17.2403, 78.4294, "Hyderabad"),
    "NRT": (35.7720, 140.3929, "Tokyo"),
    "HND": (35.5494, 139.7798, "Tokyo Haneda"),
    "LHR": (51.4700, -0.4543,  "London"),
    "CDG": (49.0097, 2.5479,   "Paris"),
    "DXB": (25.2532, 55.3657,  "Dubai"),
    "SIN": (1.3644,  103.9915, "Singapore"),
    "BKK": (13.6900, 100.7501, "Bangkok"),
    "JFK": (40.6413, -73.7781, "New York"),
    "LAX": (33.9425, -118.4081,"Los Angeles"),
    "SYD": (-33.9399, 151.1753,"Sydney"),
    "KUL": (2.7456,  101.7072, "Kuala Lumpur"),
    "ICN": (37.4602, 126.4407, "Seoul"),
    "PEK": (40.0799, 116.6031, "Beijing"),
    "PVG": (31.1443, 121.8083, "Shanghai"),
    "AMS": (52.3086, 4.7639,   "Amsterdam"),
    "FRA": (50.0379, 8.5622,   "Frankfurt"),
    "ZRH": (47.4647, 8.5492,   "Zurich"),
    "DOH": (25.2731, 51.6080,  "Doha"),
    "AUH": (24.4330, 54.6511,  "Abu Dhabi"),
    "MEL": (-37.6690, 144.8410,"Melbourne"),
    "HKG": (22.3080, 113.9185, "Hong Kong"),
    "MNL": (14.5086, 121.0194, "Manila"),
    "CGK": (-6.1275, 106.6537, "Jakarta"),
}


def build_travel_map(
    origin_iata: str,
    destination_iata: str,
    hotels: list = None,
    destination_city: str = "",
) -> str:
    """
    Build an interactive Folium map showing:
    - Flight route arc between origin and destination
    - Origin and destination airport markers
    - Hotel pins at destination

    Args:
        origin_iata:      departure airport IATA code e.g. "BOM"
        destination_iata: arrival airport IATA code e.g. "NRT"
        hotels:           list of hotel dicts (from hotel_tool) with lat/lon
        destination_city: city name for geocoding fallback

    Returns:
        HTML string of the map (embed in Streamlit with streamlit-folium)
    """
    origin_coords      = _resolve_airport(origin_iata)
    destination_coords = _resolve_airport(destination_iata, destination_city)

    if not origin_coords or not destination_coords:
        return None

    # center map between origin and destination
    center_lat = (origin_coords[0] + destination_coords[0]) / 2
    center_lon = (origin_coords[1] + destination_coords[1]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=3,
        tiles="CartoDB positron",
    )

    # origin marker
    folium.Marker(
        location=[origin_coords[0], origin_coords[1]],
        popup=folium.Popup(f"✈️ Departure: {origin_coords[2]}", max_width=200),
        tooltip=f"Departure: {origin_coords[2]}",
        icon=folium.Icon(color="blue", icon="plane", prefix="fa"),
    ).add_to(m)

    # destination marker
    folium.Marker(
        location=[destination_coords[0], destination_coords[1]],
        popup=folium.Popup(f"🏁 Destination: {destination_coords[2]}", max_width=200),
        tooltip=f"Destination: {destination_coords[2]}",
        icon=folium.Icon(color="red", icon="plane", prefix="fa"),
    ).add_to(m)

    # flight route line
    folium.PolyLine(
        locations=[
            [origin_coords[0], origin_coords[1]],
            [destination_coords[0], destination_coords[1]],
        ],
        color="#4A90D9",
        weight=2.5,
        opacity=0.8,
        dash_array="8 4",
        tooltip="Flight Route",
    ).add_to(m)

    # hotel pins
    if hotels:
        for hotel in hotels:
            lat = hotel.get("latitude")
            lon = hotel.get("longitude")
            if lat and lon:
                popup_html = f"""
                    <b>{hotel.get('name', 'Hotel')}</b><br>
                    ⭐ {hotel.get('stars', 'N/A')} |
                    Rating: {hotel.get('rating', 'N/A')}/5<br>
                    💰 {hotel.get('price_per_night', 'N/A')} / night
                """
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=hotel.get("name", "Hotel"),
                    icon=folium.Icon(color="green", icon="home", prefix="fa"),
                ).add_to(m)

    return m._repr_html_()


def _resolve_airport(iata: str, city_fallback: str = "") -> tuple:
    """Returns (lat, lon, name) for an airport IATA code."""
    iata = iata.upper().strip()

    if iata in AIRPORT_COORDS:
        return AIRPORT_COORDS[iata]

    # fallback: geocode the city name
    if city_fallback:
        return _geocode_city(city_fallback)

    return None


def _geocode_city(city: str) -> tuple:
    """Geocode a city name using Open-Meteo (no API key)."""
    try:
        resp = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            r = results[0]
            return (r["latitude"], r["longitude"], r.get("name", city))
    except Exception:
        pass
    return None
