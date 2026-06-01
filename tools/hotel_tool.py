import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def search_hotels(destination: str, check_in: str, check_out: str,
                  adults: int = 2, currency: str = "INR",
                  max_price: int = None, hotel_class: int = None,
                  sort_by: int = 3) -> dict:
    """
    Search hotels using SerpAPI Google Hotels.

    Args:
        destination:  city name e.g. "Tokyo", "Paris"
        check_in:     "YYYY-MM-DD"
        check_out:    "YYYY-MM-DD"
        adults:       number of guests
        currency:     currency code e.g. "INR", "USD"
        max_price:    maximum price per night (optional)
        hotel_class:  star rating 2-5 (optional)
        sort_by:      3=lowest price, 8=highest rating, 13=most reviewed

    Returns:
        dict with keys: hotels, error
    """
    params = {
        "engine":         "google_hotels",
        "q":              f"hotels in {destination}",
        "check_in_date":  check_in,
        "check_out_date": check_out,
        "adults":         adults,
        "currency":       currency,
        "sort_by":        sort_by,
        "hl":             "en",
        "api_key":        SERPAPI_KEY,
    }

    if max_price:
        params["max_price"] = max_price
    if hotel_class:
        params["hotel_class"] = hotel_class

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            return {"error": results["error"], "hotels": []}

        hotels = _parse_hotels(results.get("properties", []))

        return {
            "hotels": hotels,
            "error":  None,
        }

    except Exception as e:
        return {"error": str(e), "hotels": []}


def _parse_hotels(properties: list) -> list:
    parsed = []
    for prop in properties[:8]:
        parsed.append({
            "name":           prop.get("name", "Unknown"),
            "type":           prop.get("type", "Hotel"),
            "stars":          prop.get("hotel_class", "N/A"),
            "rating":         prop.get("overall_rating", "N/A"),
            "reviews":        prop.get("reviews", 0),
            "price_per_night": prop.get("rate_per_night", {}).get("lowest", "N/A"),
            "total_price":    prop.get("total_rate", {}).get("lowest", "N/A"),
            "description":    prop.get("description", ""),
            "amenities":      prop.get("amenities", [])[:6],
            "latitude":       prop.get("gps_coordinates", {}).get("latitude"),
            "longitude":      prop.get("gps_coordinates", {}).get("longitude"),
            "thumbnail":      prop.get("images", [{}])[0].get("thumbnail", "") if prop.get("images") else "",
        })
    return parsed


def format_hotels_for_llm(hotel_data: dict) -> str:
    """Converts hotel search results into a readable string for the LLM."""
    if hotel_data.get("error"):
        return f"Hotel search failed: {hotel_data['error']}"

    hotels = hotel_data.get("hotels", [])
    if not hotels:
        return "No hotels found."

    lines = ["=== AVAILABLE HOTELS ==="]
    for i, h in enumerate(hotels[:5], 1):
        amenities = ", ".join(h["amenities"]) if h["amenities"] else "N/A"
        lines.append(
            f"{i}. {h['name']} | {h['stars']} | "
            f"Rating: {h['rating']}/5 ({h['reviews']} reviews) | "
            f"Price/night: {h['price_per_night']} | "
            f"Total: {h['total_price']} | "
            f"Amenities: {amenities}"
        )

    return "\n".join(lines)
