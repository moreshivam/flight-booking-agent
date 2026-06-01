import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def search_flights(origin: str, destination: str, depart_date: str,
                   return_date: str = None, adults: int = 1,
                   travel_class: int = 1, currency: str = "INR") -> dict:
    """
    Search flights using SerpAPI Google Flights.

    Args:
        origin:       IATA airport code e.g. "BOM" (Mumbai)
        destination:  IATA airport code e.g. "NRT" (Tokyo)
        depart_date:  "YYYY-MM-DD"
        return_date:  "YYYY-MM-DD" or None for one-way
        adults:       number of adult passengers
        travel_class: 1=Economy 2=Premium Economy 3=Business 4=First
        currency:     currency code e.g. "INR", "USD"

    Returns:
        dict with keys: best_flights, other_flights, price_insights, error
    """
    params = {
        "engine":         "google_flights",
        "departure_id":   origin.upper(),
        "arrival_id":     destination.upper(),
        "outbound_date":  depart_date,
        "travel_class":   travel_class,
        "adults":         adults,
        "currency":       currency,
        "hl":             "en",
        "api_key":        SERPAPI_KEY,
    }

    if return_date:
        params["return_date"] = return_date
        params["type"] = 1  # round trip
    else:
        params["type"] = 2  # one way

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            return {"error": results["error"], "best_flights": [], "other_flights": []}

        best_flights    = _parse_flights(results.get("best_flights", []))
        other_flights   = _parse_flights(results.get("other_flights", []))
        price_insights  = results.get("price_insights", {})

        return {
            "best_flights":   best_flights,
            "other_flights":  other_flights,
            "price_insights": price_insights,
            "error":          None,
        }

    except Exception as e:
        return {"error": str(e), "best_flights": [], "other_flights": []}


def _parse_flights(flights: list) -> list:
    parsed = []
    for flight in flights:
        legs = flight.get("flights", [])
        if not legs:
            continue

        first_leg = legs[0]
        last_leg  = legs[-1]

        parsed.append({
            "airline":          first_leg.get("airline", "Unknown"),
            "airline_logo":     first_leg.get("airline_logo", ""),
            "departure_airport": first_leg.get("departure_airport", {}).get("name", ""),
            "departure_time":   first_leg.get("departure_airport", {}).get("time", ""),
            "arrival_airport":  last_leg.get("arrival_airport", {}).get("name", ""),
            "arrival_time":     last_leg.get("arrival_airport", {}).get("time", ""),
            "duration_minutes": flight.get("total_duration", 0),
            "stops":            len(legs) - 1,
            "price":            flight.get("price", 0),
            "carbon_emissions": flight.get("carbon_emissions", {}).get("this_flight", 0),
        })

    return parsed


def format_flights_for_llm(flight_data: dict) -> str:
    """Converts flight search results into a readable string for the LLM."""
    if flight_data.get("error"):
        return f"Flight search failed: {flight_data['error']}"

    lines = []

    best = flight_data.get("best_flights", [])
    if best:
        lines.append("=== BEST FLIGHTS ===")
        for i, f in enumerate(best[:3], 1):
            stops = "Non-stop" if f["stops"] == 0 else f"{f['stops']} stop(s)"
            duration_hrs = f['duration_minutes'] // 60
            duration_mins = f['duration_minutes'] % 60
            lines.append(
                f"{i}. {f['airline']} | {stops} | "
                f"{duration_hrs}h {duration_mins}m | "
                f"Departs {f['departure_time']} → Arrives {f['arrival_time']} | "
                f"Price: {f['price']} INR"
            )

    other = flight_data.get("other_flights", [])
    if other:
        lines.append("\n=== OTHER OPTIONS ===")
        for i, f in enumerate(other[:3], 1):
            stops = "Non-stop" if f["stops"] == 0 else f"{f['stops']} stop(s)"
            duration_hrs = f['duration_minutes'] // 60
            duration_mins = f['duration_minutes'] % 60
            lines.append(
                f"{i}. {f['airline']} | {stops} | "
                f"{duration_hrs}h {duration_mins}m | "
                f"Departs {f['departure_time']} → Arrives {f['arrival_time']} | "
                f"Price: {f['price']} INR"
            )

    insights = flight_data.get("price_insights", {})
    if insights:
        lines.append(f"\n💡 Price insight: {insights.get('price_level', 'N/A')} — "
                     f"Typical range: {insights.get('typical_price_range', ['N/A', 'N/A'])}")

    return "\n".join(lines) if lines else "No flights found."
