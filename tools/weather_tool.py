import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"


def get_weather(city: str, start_date: str, end_date: str) -> dict:
    """
    Fetch weather forecast for a city using Open-Meteo (no API key needed).

    Args:
        city:       city name e.g. "Tokyo", "Paris"
        start_date: "YYYY-MM-DD"
        end_date:   "YYYY-MM-DD"

    Returns:
        dict with keys: city, daily_forecasts, error
    """
    try:
        lat, lon, resolved_city = _get_coordinates(city)
        if lat is None:
            return {"error": f"Could not find coordinates for {city}", "daily_forecasts": []}

        params = {
            "latitude":              lat,
            "longitude":             lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "weather_code",
                "windspeed_10m_max",
            ],
            "timezone":              "auto",
            "start_date":            start_date,
            "end_date":              end_date,
            "temperature_unit":      "celsius",
            "windspeed_unit":        "kmh",
            "precipitation_unit":    "mm",
        }

        response = requests.get(WEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        forecasts = _parse_daily(daily)

        return {
            "city":            resolved_city,
            "latitude":        lat,
            "longitude":       lon,
            "daily_forecasts": forecasts,
            "error":           None,
        }

    except Exception as e:
        return {"error": str(e), "daily_forecasts": []}


def _get_coordinates(city: str):
    """Resolve city name to lat/lon using Open-Meteo geocoding."""
    try:
        resp = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None, None, city
        r = results[0]
        return r["latitude"], r["longitude"], r.get("name", city)
    except Exception:
        return None, None, city


def _parse_daily(daily: dict) -> list:
    dates      = daily.get("time", [])
    temp_max   = daily.get("temperature_2m_max", [])
    temp_min   = daily.get("temperature_2m_min", [])
    precip     = daily.get("precipitation_sum", [])
    codes      = daily.get("weather_code", [])
    wind       = daily.get("windspeed_10m_max", [])

    forecasts = []
    for i, date in enumerate(dates):
        code = codes[i] if i < len(codes) else 0
        forecasts.append({
            "date":        date,
            "temp_max":    temp_max[i] if i < len(temp_max) else None,
            "temp_min":    temp_min[i] if i < len(temp_min) else None,
            "precip_mm":   precip[i]   if i < len(precip)   else 0,
            "wind_kmh":    wind[i]     if i < len(wind)      else 0,
            "condition":   _weather_code_to_text(code),
            "emoji":       _weather_code_to_emoji(code),
        })
    return forecasts


def _weather_code_to_text(code: int) -> str:
    mapping = {
        0:  "Clear sky",
        1:  "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow",
        80: "Light showers", 81: "Showers", 82: "Heavy showers",
        95: "Thunderstorm", 99: "Thunderstorm with hail",
    }
    return mapping.get(code, "Unknown")


def _weather_code_to_emoji(code: int) -> str:
    if code == 0:               return "☀️"
    if code in (1, 2):          return "⛅"
    if code == 3:               return "☁️"
    if code in (45, 48):        return "🌫️"
    if code in (51, 53, 55):    return "🌦️"
    if code in (61, 63, 65):    return "🌧️"
    if code in (71, 73, 75):    return "❄️"
    if code in (80, 81, 82):    return "🌩️"
    if code in (95, 99):        return "⛈️"
    return "🌡️"


def format_weather_for_llm(weather_data: dict) -> str:
    """Converts weather data into a readable string for the LLM."""
    if weather_data.get("error"):
        return f"Weather fetch failed: {weather_data['error']}"

    forecasts = weather_data.get("daily_forecasts", [])
    if not forecasts:
        return "No weather data available."

    lines = [f"=== WEATHER FORECAST: {weather_data.get('city', '').upper()} ==="]
    for f in forecasts:
        lines.append(
            f"{f['date']} {f['emoji']} {f['condition']} | "
            f"🌡️ {f['temp_min']}°C - {f['temp_max']}°C | "
            f"💧 Rain: {f['precip_mm']}mm | "
            f"💨 Wind: {f['wind_kmh']} km/h"
        )
    return "\n".join(lines)
